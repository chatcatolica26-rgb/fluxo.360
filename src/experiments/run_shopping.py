"""Análise de circulação em vídeo real do shopping: YOLO + ByteTrack -> planta -> mapa de calor.

Exemplos (a partir da raiz do projeto)::

    # teste curto: só os 2 primeiros segundos
    python -m src.experiments.run_shopping --fim 2

    # vídeo inteiro com a configuração padrão
    python -m src.experiments.run_shopping

    # outro vídeo / outra calibração
    python -m src.experiments.run_shopping --video data/raw/shopping/outro.mp4 \
        --camera configs/cameras/cam02.yaml --nome corredor_leste

Cada execução cria ``data/processed/shopping/<data>_<nome>/`` (separado do MOT20).
"""
from __future__ import annotations

import argparse
import json
import platform
import sys
import time
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np
import yaml

from ..dataset.mot20_annotations import write_mot_results
from ..flow.acumulador import AcumuladorFluxo
from ..flow.trajetorias import RegistroTrajetorias
from ..flow.visualizacao import AnimacaoPlanta, desenhar_deteccoes, mapas_de_calor, regiao_interesse
from ..projection.homografia import CameraPlanta
from ..video.video_source import VideoSource

DEFAULT_CONFIG = {
    "experimento": {"nome": "shopping"},
    "video": {"arquivo": "data/raw/shopping/praca_eventos.mp4", "inicio_s": 0.0, "fim_s": None, "passo": 1},
    "camera": {"calibracao": "configs/cameras/cam_praca_eventos.yaml"},
    "planta_yaml": "configs/planta.yaml",
    "detector": {"model": "yolov8n.pt", "conf": 0.3, "iou": 0.7, "imgsz": 1280, "device": None},
    "tracker": {"config": "configs/bytetrack_shopping.yaml"},
    "acumulacao": {"celula_m": 0.5, "sigma_m": 0.75},
    "validacao": {"min_pontos_trajetoria": 12, "margem_borda_px": 3},
    "saida": {"pasta": "data/processed/shopping", "video_deteccoes": True, "video_planta": True},
}


def load_config(path: str | Path | None) -> dict:
    cfg = json.loads(json.dumps(DEFAULT_CONFIG))
    if path and Path(path).is_file():
        user = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
        for sec, val in user.items():
            if isinstance(val, dict) and isinstance(cfg.get(sec), dict):
                cfg[sec].update(val)
            else:
                cfg[sec] = val
    return cfg


def build_tracker(cfg: dict):
    from ..tracking.bytetrack_tracker import ByteTrackPersonTracker
    d = cfg["detector"]
    tracker = ByteTrackPersonTracker(model=d["model"], conf=d["conf"], iou=d["iou"], imgsz=d["imgsz"],
                                     tracker_config=cfg["tracker"]["config"], device=d.get("device"))
    tracker.descricao = f"YOLO ({d['model']}) + ByteTrack"
    return tracker


def _writer(caminho: Path, fps: float, tamanho: tuple[int, int]) -> cv2.VideoWriter:
    w = cv2.VideoWriter(str(caminho), cv2.VideoWriter_fourcc(*"mp4v"), fps, tamanho)
    if not w.isOpened():
        raise IOError(f"não consegui criar o vídeo {caminho}")
    return w


def _planta_calibrada(planta, cam_dados: dict, mascara, recorte) -> np.ndarray:
    """Planta recortada com os pontos de calibração e a área válida desenhados."""
    img = planta.copy()
    if mascara is not None:
        cont, _ = cv2.findContours((mascara > 0).astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cv2.drawContours(img, cont, -1, (200, 0, 200), 2)
    for i, p in enumerate(cam_dados.get("pontos", []), 1):
        x, y = (int(round(v)) for v in p["planta_px"])
        cv2.circle(img, (x, y), 6, (0, 0, 220), 2)
        cv2.putText(img, str(i), (x + 7, y - 7), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 220), 1, cv2.LINE_AA)
    x0, y0, x1, y1 = recorte
    return img[y0:y1, x0:x1]


def _calibracao_sobreposta(quadro, referencia, H, mascara=None) -> np.ndarray:
    """Linhas da planta projetadas sobre o vídeo: se a calibração está certa, elas caem nas paredes reais.

    A homografia só vale para o chão; com máscara, as linhas são desenhadas só no piso e na sua borda.
    """
    tam = (quadro.shape[1], quadro.shape[0])
    warp = cv2.warpPerspective(referencia, np.linalg.inv(H), tam, borderValue=(255, 255, 255))
    linhas = cv2.cvtColor(warp, cv2.COLOR_BGR2GRAY) < 110
    if mascara is not None:
        piso = cv2.warpPerspective(mascara, np.linalg.inv(H), tam, flags=cv2.INTER_NEAREST)
        piso = cv2.dilate(piso, np.ones((25, 25), np.uint8)) > 0
        linhas &= piso
    out = quadro.copy()
    out[linhas] = (0, 0, 255)
    contorno = None
    if mascara is not None:
        cont, _ = cv2.findContours((piso > 0).astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        contorno = cont
    if contorno:
        cv2.drawContours(out, contorno, -1, (255, 200, 0), 2)
    return out


def _para_h264(caminho: Path) -> bool:
    """Converte para H.264 (toca no navegador/painel) se o ffmpeg estiver instalado."""
    import shutil
    import subprocess
    if shutil.which("ffmpeg") is None or not caminho.is_file():
        return False
    tmp = caminho.with_suffix(".h264.mp4")
    r = subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(caminho), "-c:v", "libx264",
                        "-preset", "veryfast", "-crf", "23", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
                        str(tmp)], capture_output=True)
    if r.returncode == 0 and tmp.is_file():
        tmp.replace(caminho)
        return True
    tmp.unlink(missing_ok=True)
    return False


def _trajetorias_completas(planta, registro, recorte, escala: float) -> np.ndarray:
    from ..flow.visualizacao import cor_do_id
    x0, y0, x1, y1 = recorte
    img = cv2.addWeighted(planta[y0:y1, x0:x1], 0.6, np.full_like(planta[y0:y1, x0:x1], 255), 0.4, 0)
    for pid, ps in registro.trajetorias(1).items():
        pts = np.int32([[p.planta_x - x0, p.planta_y - y0] for p in ps])
        if len(pts) > 1:
            cv2.polylines(img, [pts], False, cor_do_id(pid), 2, cv2.LINE_AA)
        cv2.circle(img, tuple(pts[-1]), 4, cor_do_id(pid), -1)
    return cv2.resize(img, None, fx=escala, fy=escala, interpolation=cv2.INTER_AREA) if escala != 1 else img


def _localizacao(planta, recorte, largura: int = 1400) -> np.ndarray:
    x0, y0, x1, y1 = recorte
    img = planta.copy()
    destaque = img.copy()
    cv2.rectangle(destaque, (x0, y0), (x1, y1), (0, 0, 220), -1)
    img = cv2.addWeighted(destaque, 0.35, img, 0.65, 0)
    cv2.rectangle(img, (x0, y0), (x1, y1), (0, 0, 220), 14)
    k = largura / img.shape[1]
    return cv2.resize(img, None, fx=k, fy=k, interpolation=cv2.INTER_AREA)


def gerar_mapas_com_rastros(pasta: str | Path, min_pontos: int | None = None) -> list[Path]:
    """Cria ``mapa_*_rastros.png``: o mapa de calor com o caminho de cada pessoa por cima.

    Trabalha só com os arquivos da pasta (trajetorias.csv, run_info.json e os mapas), então
    também serve para análises antigas: ``python tools/gerar_rastros.py <pasta>``.
    """
    import pandas as pd
    from ..flow.visualizacao import desenhar_rastros

    pasta = Path(pasta)
    info = json.loads((pasta / "run_info.json").read_text(encoding="utf-8"))
    recorte, escala = info.get("planta_recorte_px"), info.get("planta_escala_imagens")
    if recorte is None or escala is None:          # análise antiga: recalcula como no processamento
        cfg = yaml.safe_load((pasta / "config.yaml").read_text(encoding="utf-8"))
        cam_yaml = Path(info["calibracao"]["arquivo"])
        camera = CameraPlanta.carregar(cam_yaml, cfg["planta_yaml"])
        piso = yaml.safe_load(Path(cfg["planta_yaml"]).read_text(encoding="utf-8"))["pisos"][camera.piso]
        hp, wp = cv2.imread(piso["imagem"], cv2.IMREAD_GRAYSCALE).shape
        pts = [p["planta_px"] for p in (yaml.safe_load(cam_yaml.read_text(encoding="utf-8")).get("pontos") or [])]
        recorte = regiao_interesse(camera.mascara, (hp, wp), margem_px=int(3 * camera.px_por_metro),
                                   pontos_px=np.array(pts) if pts else None)
        escala = float(np.clip(800 / max(recorte[2] - recorte[0], 1), 1, 4))
    if min_pontos is None:
        min_pontos = int(info.get("contagens", {}).get("min_pontos_por_trajetoria", 12))
    t = pd.read_csv(pasta / "trajetorias.csv")
    t = t[t.valida.astype(str).str.lower() == "true"].sort_values(["id", "quadro"])
    # Corta o caminho onde o ponto "salta" mais do que uma pessoa anda (2,5 m/s, mínimo 1 m):
    # isso é troca de id no rastreador, não deslocamento real.
    traj, n = {}, 0
    for pid, g in t.groupby("id"):
        xy = g[["planta_x_m", "planta_y_m"]].to_numpy()
        tempo = g["tempo_s"].to_numpy()
        passo = np.hypot(*np.diff(xy, axis=0).T) if len(xy) > 1 else np.array([])
        limite = np.maximum(1.0, 2.5 * np.diff(tempo)) if len(xy) > 1 else np.array([])
        cortes = np.where(passo > limite)[0] + 1
        for trecho in np.split(g[["planta_x", "planta_y"]].to_numpy(), cortes):
            if len(trecho) >= min_pontos:
                traj[n] = trecho
                n += 1
    saidas = []
    for nome in ("permanencia", "circulacao"):
        base = cv2.imread(str(pasta / f"mapa_{nome}_sobreposto.png"))
        if base is None:
            continue
        destino = pasta / f"mapa_{nome}_rastros.png"
        cv2.imwrite(str(destino), desenhar_rastros(base, traj, tuple(recorte), float(escala)))
        saidas.append(destino)
    return saidas


def main(argv: list[str] | None = None, runner=None) -> Path:
    ap = argparse.ArgumentParser(description="Fluxo360: mapa de calor a partir de vídeo real")
    ap.add_argument("--config", default="configs/analise_shopping.yaml")
    ap.add_argument("--video", help="arquivo de vídeo (padrão: o do config)")
    ap.add_argument("--camera", help="YAML de calibração da câmera (padrão: o do config)")
    ap.add_argument("--inicio", type=float, help="início do trecho, em segundos")
    ap.add_argument("--fim", type=float, help="fim do trecho, em segundos")
    ap.add_argument("--passo", type=int, help="processa 1 a cada N quadros")
    ap.add_argument("--conf", type=float, help="confiança mínima do YOLO")
    ap.add_argument("--nome", help="nome da execução")
    ap.add_argument("--sem-videos", action="store_true", help="não grava os vídeos de saída (mais rápido)")
    args = ap.parse_args(argv)

    cfg = load_config(args.config)
    v = cfg["video"]
    if args.video: v["arquivo"] = args.video
    if args.inicio is not None: v["inicio_s"] = args.inicio
    if args.fim is not None: v["fim_s"] = args.fim
    if args.passo: v["passo"] = args.passo
    if args.camera: cfg["camera"]["calibracao"] = args.camera
    if args.conf is not None: cfg["detector"]["conf"] = args.conf
    if args.nome: cfg["experimento"]["nome"] = args.nome
    if args.sem_videos:
        cfg["saida"]["video_deteccoes"] = cfg["saida"]["video_planta"] = False

    # ------------------------------------------------------------ preparação
    cam_yaml = Path(cfg["camera"]["calibracao"])
    if not cam_yaml.is_file():
        raise SystemExit(f"Calibração não encontrada: {cam_yaml}\n"
                         "Rode antes: python tools/calibrar_camera.py --camera cam_praca_eventos --piso terreo "
                         f"--fonte {v['arquivo']} --mediana")
    cam_dados = yaml.safe_load(cam_yaml.read_text(encoding="utf-8"))
    camera = CameraPlanta.carregar(cam_yaml, cfg["planta_yaml"])
    piso = yaml.safe_load(Path(cfg["planta_yaml"]).read_text(encoding="utf-8"))["pisos"][camera.piso]
    planta = cv2.imread(piso["imagem"])
    if planta is None:
        raise SystemExit(f"Imagem da planta não encontrada: {piso['imagem']}")
    hp, wp = planta.shape[:2]

    fonte = VideoSource(v["arquivo"], v["inicio_s"], v["fim_s"], v["passo"])
    info = fonte.info
    if cam_dados.get("frame_tamanho") and list(cam_dados["frame_tamanho"]) != [info.largura, info.altura]:
        raise SystemExit(f"A calibração foi feita em {cam_dados['frame_tamanho']}, mas o vídeo tem "
                         f"{[info.largura, info.altura]}. Recalibre para esta resolução.")

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    pasta = Path(cfg["saida"]["pasta"]) / f"{stamp}_{cfg['experimento']['nome']}"
    pasta.mkdir(parents=True, exist_ok=True)
    (pasta / "config.yaml").write_text(yaml.safe_dump(cfg, allow_unicode=True, sort_keys=False), encoding="utf-8")
    log_path = pasta / "processamento.log"
    log_fh = open(log_path, "w", encoding="utf-8")

    def log(msg: str):
        print(msg)
        log_fh.write(msg + "\n")

    log(f"Vídeo: {info.fonte} | {info.largura}x{info.altura} | {info.fps:.2f} FPS | "
        f"{info.total_quadros} quadros | {info.duracao_s:.2f} s")
    log(f"Trecho: {v['inicio_s']} s até {v['fim_s'] if v['fim_s'] is not None else 'o fim'} | passo {v['passo']}")
    log(f"Calibração: {cam_yaml} | {len(cam_dados.get('pontos', []))} pontos | "
        f"erro médio {cam_dados.get('erro_medio_m', '?')} m")

    runner = runner or build_tracker(cfg)
    runner.reset()
    registro = RegistroTrajetorias(camera, info.largura, info.altura, wp, hp,
                                   cfg["validacao"]["margem_borda_px"])
    acc = AcumuladorFluxo(wp, hp, camera.px_por_metro, cfg["acumulacao"]["celula_m"])
    pts_cal = [p["planta_px"] for p in cam_dados.get("pontos", [])]
    recorte = regiao_interesse(camera.mascara, (hp, wp), margem_px=int(3 * camera.px_por_metro),
                               pontos_px=np.array(pts_cal) if pts_cal else None)
    largura_rec = recorte[2] - recorte[0]
    anim = AnimacaoPlanta(planta, recorte, escala=float(np.clip(800 / max(largura_rec, 1), 1, 4)))
    fps_saida = info.fps / v["passo"]
    w_det = _writer(pasta / "video_deteccoes.mp4", fps_saida, (info.largura, info.altura)) \
        if cfg["saida"]["video_deteccoes"] else None
    w_pl = None
    mot_records = []

    # ---------------------------------------------------------- processamento
    inicio = time.perf_counter()
    n = 0
    primeiro_quadro, melhor_quadro, melhor_n = None, None, -1
    for quadro, t, img in fonte:
        if primeiro_quadro is None:
            primeiro_quadro = img.copy()
        tracks = runner.update(img)
        posicoes = registro.adicionar(quadro, t, tracks)
        validas = sum(p.valida for p in posicoes)
        if validas > melhor_n:
            melhor_n, melhor_quadro = validas, desenhar_deteccoes(img, posicoes)
        for p in posicoes:
            mot_records.append((quadro + 1, p.id, p.x1, p.y1, p.x2 - p.x1, p.y2 - p.y1, p.score))
            if p.valida:
                # acumulação temporal: cada posição válida soma o tempo real do quadro (passo / FPS)
                acc.adicionar(p.id, p.planta_x, p.planta_y, fonte.dt)
        acc.registrar_quadro(fonte.dt)
        if w_det is not None:
            w_det.write(desenhar_deteccoes(img, posicoes))
        if cfg["saida"]["video_planta"]:
            qp = anim.quadro(t, posicoes)
            if w_pl is None:
                w_pl = _writer(pasta / "video_trajetorias_planta.mp4", fps_saida, (qp.shape[1], qp.shape[0]))
            w_pl.write(qp)
        n += 1
        if n % 50 == 0:
            log(f"  quadro {quadro} ({t:.1f} s): {len(tracks)} pessoas no quadro")
    tempo_proc = time.perf_counter() - inicio
    for w in (w_det, w_pl):
        if w is not None:
            w.release()
    h264 = [_para_h264(pasta / n) for n in ("video_deteccoes.mp4", "video_trajetorias_planta.mp4")]
    if any(h264):
        log("Vídeos convertidos para H.264 (tocam no navegador).")
    if n == 0:
        raise SystemExit("Nenhum quadro lido: confira o arquivo e o trecho escolhido.")

    # --------------------------------------------------------------- saídas
    registro.salvar_csv(pasta / "trajetorias.csv")
    if mot_records:
        arr = np.array(mot_records, float)
        write_mot_results(pasta / "rastreamento_mot.txt", arr[:, 0], arr[:, 1], arr[:, 2:6], arr[:, 6])
    acc.salvar(pasta)
    sigma_px = cfg["acumulacao"]["sigma_m"] * camera.px_por_metro
    cv2.imwrite(str(pasta / "planta_calibrada.png"), _planta_calibrada(planta, cam_dados, camera.mascara, recorte))
    referencia = cv2.imread(piso.get("referencia") or piso["imagem"])
    if referencia is not None and primeiro_quadro is not None:
        cv2.imwrite(str(pasta / "calibracao_sobreposta.png"),
                    _calibracao_sobreposta(primeiro_quadro, referencia, camera.H, camera.mascara))
    if melhor_quadro is not None:
        cv2.imwrite(str(pasta / "quadro_exemplo_deteccoes.png"), melhor_quadro)
    cv2.imwrite(str(pasta / "trajetorias_planta.png"), _trajetorias_completas(planta, registro, recorte, anim.escala))
    cv2.imwrite(str(pasta / "localizacao_na_planta.png"), _localizacao(planta, recorte))
    vmax = {}
    cel = str(cfg["acumulacao"]["celula_m"]).replace(".", ",")
    for nome, matriz, titulo, unid in (
            ("permanencia", acc.permanencia, f"permanencia: segundos de presenca por celula de {cel} m", "s"),
            ("circulacao", acc.passagens, f"circulacao: pessoas que passaram por celula de {cel} m", "pessoas")):
        mp = mapas_de_calor(acc.em_pixels_da_planta(matriz), planta, sigma_px, recorte, titulo, unid,
                            vmax_rotulo=float(matriz.max()), escala=anim.escala)
        cv2.imwrite(str(pasta / f"mapa_{nome}_sobreposto.png"), mp["sobreposto"])
        cv2.imwrite(str(pasta / f"mapa_{nome}_isolado.png"), mp["isolado"])
        vmax[nome] = mp["vmax"]

    resumo = registro.resumo(cfg["validacao"]["min_pontos_trajetoria"])
    tracker_params = {}
    tp = Path(cfg["tracker"]["config"])
    if tp.is_file():
        tracker_params = yaml.safe_load(tp.read_text(encoding="utf-8"))
    duracao = n * fonte.dt
    run_info = {
        "nome": cfg["experimento"]["nome"], "inicio": stamp, "comando": " ".join(sys.argv),
        "video": info.como_dict(), "trecho": {"inicio_s": v["inicio_s"], "fim_s": v["fim_s"], "passo": v["passo"]},
        "quadros_processados": n, "duracao_analisada_s": round(duracao, 3),
        "tempo_processamento_s": round(tempo_proc, 2), "fps_processamento": round(n / tempo_proc, 2) if tempo_proc else None,
        "contagens": resumo, "detector": cfg["detector"], "tracker": {"arquivo": str(tp), **tracker_params},
        "calibracao": {"arquivo": str(cam_yaml), "piso": camera.piso, "pontos": len(cam_dados.get("pontos", [])),
                       "erro_medio_m": cam_dados.get("erro_medio_m"), "erro_max_m": cam_dados.get("erro_max_m"),
                       "mascara": cam_dados.get("mascara"), "H": cam_dados.get("H"),
                       "status": cam_dados.get("status", "definitiva"), "metodo": cam_dados.get("metodo", "")},
        "detector_usado": getattr(runner, "descricao", type(runner).__name__),
        "acumulacao": {**cfg["acumulacao"], "permanencia_total_s": round(float(acc.permanencia.sum()), 2),
                       "maximo_visual": vmax},
        "planta_recorte_px": [int(v) for v in recorte], "planta_escala_imagens": round(float(anim.escala), 6),
        "versoes": {"python": platform.python_version(), "numpy": np.__version__, "opencv": cv2.__version__},
    }
    try:
        import ultralytics
        run_info["versoes"]["ultralytics"] = ultralytics.__version__
    except ImportError:
        pass
    (pasta / "run_info.json").write_text(json.dumps(run_info, indent=2, ensure_ascii=False, default=str),
                                         encoding="utf-8")
    (pasta / "relatorio.md").write_text(_relatorio(run_info), encoding="utf-8")
    gerar_mapas_com_rastros(pasta)
    log(f"Pessoas únicas na área: {resumo['pessoas_unicas_na_area']} | detecções: {resumo['deteccoes_total']} "
        f"(válidas {resumo['deteccoes_validas']}) | trajetórias: {resumo['trajetorias_registradas']}")
    log(f"{n} quadros em {tempo_proc:.1f} s. Resultados em {pasta}")
    log_fh.close()
    return pasta


def _relatorio(r: dict) -> str:
    c, v, cal, d = r["contagens"], r["video"], r["calibracao"], r["detector"]
    desc = "\n".join(f"| {k} | {n} |" for k, n in c["descartes_por_motivo"].items()) or "| nenhum | 0 |"
    trk = "\n".join(f"| {k} | {val} |" for k, val in r["tracker"].items())
    return f"""# Relatório de processamento — {r['nome']}

Gerado em {r['inicio']}. Fonte: vídeo real do shopping (não misturar com resultados do MOT20).

## Vídeo
| Item | Valor |
|---|---|
| Arquivo | {Path(v['fonte']).name} |
| Resolução | {v['largura']} x {v['altura']} |
| FPS | {v['fps']:.2f} |
| Duração total | {v['duracao_s']:.2f} s ({v['total_quadros']} quadros) |
| Trecho analisado | {r['trecho']['inicio_s']} s a {r['trecho']['fim_s'] if r['trecho']['fim_s'] is not None else 'fim'} (passo {r['trecho']['passo']}) |
| Duração analisada | {r['duracao_analisada_s']:.2f} s |
| Quadros processados | {r['quadros_processados']} |
| Tempo de processamento | {r['tempo_processamento_s']:.1f} s ({r['fps_processamento']} quadros/s) |

## Contagens
| Medida | Valor |
|---|---|
| Detecções (todas as caixas de pessoa, em todos os quadros) | {c['deteccoes_total']} |
| Detecções usadas no mapa | {c['deteccoes_validas']} |
| Ids gerados pelo rastreador | {c['ids_rastreados']} |
| Pessoas únicas na área calibrada | {c['pessoas_unicas_na_area']} |
| Trajetórias registradas (≥ {c['min_pontos_por_trajetoria']} posições) | {c['trajetorias_registradas']} |

Pessoas únicas = ids distintos. Trocas de id fazem uma pessoa contar mais de uma vez: confira no `video_deteccoes.mp4`.

### Posições descartadas
| Motivo | Quantidade |
|---|---|
{desc}

## Detector
Rastreador usado nesta execução: **{r.get('detector_usado', '')}**.

| Parâmetro do YOLO (configuração) | Valor |
|---|---|
| Modelo | {d['model']} |
| Classe | 0 (person), demais descartadas |
| Confiança mínima | {d['conf']} |
| IoU do NMS | {d['iou']} |
| Tamanho da imagem | {d['imgsz']} |
| Dispositivo | {d['device'] or 'automático'} |

## ByteTrack
| Parâmetro | Valor |
|---|---|
{trk}

## Calibração e homografia
| Item | Valor |
|---|---|
| Arquivo | {cal['arquivo']} |
| Piso | {cal['piso']} |
| Pontos usados | {cal['pontos']} |
| Erro médio / máximo | {cal['erro_medio_m']} m / {cal['erro_max_m']} m |
| Máscara da área válida | {cal['mascara'] or 'não definida'} |
| Situação | {cal.get('status', '')} |
| Método | {cal.get('metodo', '')} |

Matriz H (pixel do vídeo -> pixel da planta):

```
{np.array(cal['H']).round(6) if cal['H'] else 'n/d'}
```

## Acumulação
Célula de {r['acumulacao']['celula_m']} m. Permanência em segundos de presença (cada quadro soma passo/FPS, então o
resultado não depende do FPS). Circulação = pessoas diferentes que entraram em cada célula. Suavização gaussiana de
{r['acumulacao']['sigma_m']} m só nas imagens; as matrizes `.npy` guardam os valores sem suavização.
Permanência total somada: {r['acumulacao']['permanencia_total_s']} s.

## Arquivos
`video_deteccoes.mp4`, `video_trajetorias_planta.mp4`, `planta_calibrada.png`, `calibracao_sobreposta.png`,
`quadro_exemplo_deteccoes.png`, `trajetorias_planta.png`, `localizacao_na_planta.png`, `mapa_permanencia_sobreposto.png`,
`mapa_permanencia_rastros.png`, `mapa_circulacao_rastros.png`,
`mapa_permanencia_isolado.png`, `mapa_circulacao_sobreposto.png`, `mapa_circulacao_isolado.png`,
`matriz_permanencia_s.npy`, `matriz_passagens.npy`, `matrizes.npz`, `trajetorias.csv`, `rastreamento_mot.txt`,
`run_info.json`, `config.yaml`, `processamento.log`.
"""


if __name__ == "__main__":
    main()

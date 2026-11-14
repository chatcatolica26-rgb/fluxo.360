"""Gera um vídeo curto para apresentação a partir de uma análise já processada.

    python tools/gerar_video_demo.py                       # usa a análise mais recente
    python tools/gerar_video_demo.py data/processed/shopping/<pasta>

Monta: abertura (2 s) -> vídeo com detecções lado a lado com as pessoas andando na planta
-> mapa de calor final (4 s). Salva ``demo_apresentacao.mp4`` dentro da pasta da análise.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ALTURA = 540
FAIXA = 64
FUNDO = (24, 24, 28)


def _fonte(tam: int, negrito: bool = False):
    nomes = (["DejaVuSans-Bold.ttf", "arialbd.ttf"] if negrito else ["DejaVuSans.ttf", "arial.ttf"])
    for n in nomes:
        for base in ("", "/usr/share/fonts/truetype/dejavu/", "C:/Windows/Fonts/"):
            try:
                return ImageFont.truetype(base + n, tam)
            except OSError:
                continue
    return ImageFont.load_default()


def _texto(img: np.ndarray, linhas: list[tuple[str, int, bool, tuple]], x: int, y: int) -> np.ndarray:
    pil = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    d = ImageDraw.Draw(pil)
    for txt, tam, neg, cor in linhas:
        d.text((x, y), txt, font=_fonte(tam, neg), fill=cor)
        y += int(tam * 1.45)
    return cv2.cvtColor(np.array(pil), cv2.COLOR_RGB2BGR)


def _altura(img: np.ndarray, h: int) -> np.ndarray:
    return cv2.resize(img, (int(round(img.shape[1] * h / img.shape[0])), h), interpolation=cv2.INTER_AREA)


def gerar(pasta: Path) -> Path:
    info = json.loads((pasta / "run_info.json").read_text(encoding="utf-8"))
    c = info["contagens"]
    det = cv2.VideoCapture(str(pasta / "video_deteccoes.mp4"))
    pla = cv2.VideoCapture(str(pasta / "video_trajetorias_planta.mp4"))
    fps = det.get(cv2.CAP_PROP_FPS) or 24
    ok1, f1 = det.read()
    ok2, f2 = pla.read()
    if not (ok1 and ok2):
        raise SystemExit("Vídeos da análise não encontrados.")
    a, b = _altura(f1, ALTURA), _altura(f2, ALTURA)
    W = a.shape[1] + b.shape[1] + 12
    W += W % 2
    H = ALTURA + FAIXA
    tmp = pasta / "_demo_tmp.mp4"
    out = cv2.VideoWriter(str(tmp), cv2.VideoWriter_fourcc(*"mp4v"), fps, (W, H))

    # abertura
    capa = np.full((H, W, 3), FUNDO, np.uint8)
    capa = _texto(capa, [("FLUXO360 · análise de fluxo com visão computacional", 34, True, (255, 255, 255)),
                         ("Capim Dourado Shopping · Praça de Eventos · vídeo real", 24, False, (200, 200, 200)),
                         ("vídeo  →  pessoas  →  posição na planta  →  mapa de calor", 22, False, (150, 190, 255))],
                  60, H // 2 - 80)
    for _ in range(int(2 * fps)):
        out.write(capa)

    # vídeo lado a lado
    rodape = f"ids = trechos rastreados, não pessoas únicas · {info.get('detector_usado', '')}"
    rot_det = "1. Detecção e rastreamento: cada pessoa recebe um id; o ponto verde é o pé"
    rot_pla = "2. Projeção na planta oficial (homografia do chão)"
    while ok1 and ok2:
        quadro = np.full((H, W, 3), FUNDO, np.uint8)
        a, b = _altura(f1, ALTURA), _altura(f2, ALTURA)
        quadro[FAIXA:, :a.shape[1]] = a
        quadro[FAIXA:, a.shape[1] + 12:a.shape[1] + 12 + b.shape[1]] = b
        quadro = _texto(quadro, [(rot_det, 20, True, (255, 255, 255))], 16, 18)
        quadro = _texto(quadro, [(rot_pla, 20, True, (255, 255, 255))], a.shape[1] + 28, 18)
        quadro = _texto(quadro, [(rodape, 13, False, (235, 235, 235))], 12, H - 22)
        out.write(quadro)
        ok1, f1 = det.read()
        ok2, f2 = pla.read()

    # mapa de calor
    mapa = cv2.imread(str(pasta / "mapa_permanencia_rastros.png"))
    if mapa is None:
        mapa = cv2.imread(str(pasta / "mapa_permanencia_sobreposto.png"))
    traj = cv2.imread(str(pasta / "trajetorias_planta.png"))
    if mapa is not None:
        final = np.full((H, W, 3), FUNDO, np.uint8)
        esq = _altura(traj, ALTURA - 40) if traj is not None else None
        dir_ = _altura(mapa, ALTURA - 40)
        x = 16
        if esq is not None:
            final[FAIXA + 10:FAIXA + 10 + esq.shape[0], x:x + esq.shape[1]] = esq
            x += esq.shape[1] + 16
        final[FAIXA + 10:FAIXA + 10 + dir_.shape[0], x:x + dir_.shape[1]] = dir_
        x += dir_.shape[1] + 24
        final = _texto(final, [("3. Acumulação no tempo: mapa de calor com o rastro das pessoas", 20, True, (255, 255, 255))], 16, 18)
        if x < W - 200:
            final = _texto(final, [
                ("Resultado deste trecho", 22, True, (255, 255, 255)),
                (f"{info['duracao_analisada_s']:.0f} s de vídeo · {info['quadros_processados']} quadros", 18, False, (210, 210, 210)),
                (f"{c['deteccoes_validas']} posições na área", 18, False, (210, 210, 210)),
                (f"{c['trajetorias_registradas']} trajetórias", 18, False, (210, 210, 210)),
                ("", 10, False, (0, 0, 0)),
                ("Cor = segundos de presença", 18, False, (210, 210, 210)),
                ("por célula de 0,5 m", 18, False, (210, 210, 210)),
                ("Linhas = caminho de cada pessoa", 18, False, (210, 210, 210)),
            ], x, FAIXA + 40)
        cal = info.get("calibracao", {})
        nota = (f"Detector: {info.get('detector_usado', '')} · calibração "
                f"{'preliminar' if str(cal.get('status', '')).startswith('preliminar') else 'definitiva'} "
                f"(erro médio {cal.get('erro_medio_m', '?')} m)")
        final = _texto(final, [(nota, 15, False, (170, 170, 170))], 16, H - 30)
        for _ in range(int(4 * fps)):
            out.write(final)
    out.release()

    destino = pasta / "demo_apresentacao.mp4"
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        try:
            import imageio_ffmpeg
            ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
        except Exception:
            ffmpeg = None
    if ffmpeg:
        subprocess.run([ffmpeg, "-y", "-loglevel", "error", "-i", str(tmp), "-c:v", "libx264", "-preset",
                        "veryfast", "-crf", "22", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(destino)],
                       check=True)
        tmp.unlink()
    else:
        tmp.replace(destino)
    return destino


if __name__ == "__main__":
    if len(sys.argv) > 1:
        alvo = Path(sys.argv[1])
    else:
        execs = sorted(Path("data/processed/shopping").glob("*/run_info.json"))
        if not execs:
            raise SystemExit("Nenhuma análise encontrada em data/processed/shopping.")
        alvo = execs[-1].parent
    print("Vídeo de demonstração:", gerar(alvo))

"""Ferramenta de calibração câmera -> planta (Fluxo360).

Uso:
  python tools/calibrar_camera.py --camera cam01 --piso terreo --fonte video.mp4
  python tools/calibrar_camera.py --camera cam02 --piso terreo --fonte rtsp://... --quadro 50
  python tools/calibrar_camera.py --camera cam01 --piso terreo --fonte quadro.jpg
  python tools/calibrar_camera.py --camera cam_praca_eventos --piso terreo --fonte video.mp4 --mediana
    (--mediana: usa o fundo do vídeo sem pessoas, melhor para enxergar o piso)

Duas janelas: VIDEO e PLANTA.
  Clique esquerdo   : marca ponto (primeiro no VIDEO, depois o mesmo ponto na PLANTA)
  Roda do mouse     : zoom          | Botão direito arrastando: mover
  z : desfaz o último ponto          | v : liga/desliga sobreposição da planta no vídeo
  m : modo máscara (cliques na PLANTA desenham o polígono da área que a câmera cobre)
  x : apaga a máscara                | s : salva | q / ESC : sai
Use pontos NO CHÃO: base de pilares, quinas de vitrines, juntas de piso. 6 a 10 pontos espalhados.
"""
from __future__ import annotations
import argparse, datetime as dt
from pathlib import Path
import cv2
import numpy as np
import yaml

COR_PAR = [(0, 0, 255), (0, 160, 0), (255, 0, 0), (0, 140, 255), (200, 0, 200),
           (0, 200, 200), (120, 60, 0), (0, 80, 160), (160, 160, 0), (80, 0, 160)]


class Vista:
    def __init__(self, nome, img, tam=(1100, 800)):
        self.nome, self.img = nome, img
        self.vw, self.vh = tam
        h, w = img.shape[:2]
        self.zoom = min(self.vw / w, self.vh / h)
        self.ox = self.oy = 0.0
        self._arrasto = None
        self.clique = None
        cv2.namedWindow(nome, cv2.WINDOW_AUTOSIZE)
        cv2.setMouseCallback(nome, self._mouse)

    def para_img(self, x, y):
        return self.ox + x / self.zoom, self.oy + y / self.zoom

    def para_tela(self, x, y):
        return int((x - self.ox) * self.zoom), int((y - self.oy) * self.zoom)

    def _mouse(self, ev, x, y, flags, _):
        if ev == cv2.EVENT_LBUTTONDOWN:
            self.clique = self.para_img(x, y)
        elif ev == cv2.EVENT_RBUTTONDOWN:
            self._arrasto = (x, y, self.ox, self.oy)
        elif ev == cv2.EVENT_MOUSEMOVE and self._arrasto:
            x0, y0, ox, oy = self._arrasto
            self.ox, self.oy = ox - (x - x0) / self.zoom, oy - (y - y0) / self.zoom
        elif ev == cv2.EVENT_RBUTTONUP:
            self._arrasto = None
        elif ev == cv2.EVENT_MOUSEWHEEL:
            ix, iy = self.para_img(x, y)
            self.zoom *= 1.25 if cv2.getMouseWheelDelta(flags) > 0 else 0.8
            self.ox, self.oy = ix - x / self.zoom, iy - y / self.zoom

    def mostrar(self, desenhar):
        M = np.array([[self.zoom, 0, -self.ox * self.zoom], [0, self.zoom, -self.oy * self.zoom]])
        tela = cv2.warpAffine(self.img, M, (self.vw, self.vh), flags=cv2.INTER_AREA
                              if self.zoom < 1 else cv2.INTER_LINEAR, borderValue=(60, 60, 60))
        desenhar(tela, self)
        cv2.imshow(self.nome, tela)


def ler_quadro(fonte, n):
    p = Path(fonte)
    if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".bmp"}:
        return cv2.imread(str(p))
    cap = cv2.VideoCapture(fonte)
    quadro = None
    for _ in range(n + 1):
        ok, f = cap.read()
        if not ok:
            break
        quadro = f
    cap.release()
    return quadro


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--camera", required=True)
    ap.add_argument("--piso", required=True)
    ap.add_argument("--fonte", required=True, help="vídeo, RTSP ou imagem")
    ap.add_argument("--quadro", type=int, default=0)
    ap.add_argument("--mediana", action="store_true", help="usa o fundo sem pessoas (câmera fixa)")
    ap.add_argument("--planta-yaml", default="configs/planta.yaml")
    ap.add_argument("--saida-dir", default="configs/cameras")
    a = ap.parse_args()

    planta_cfg = yaml.safe_load(Path(a.planta_yaml).read_text(encoding="utf-8"))["pisos"][a.piso]
    ppm = float(planta_cfg["px_por_metro"])
    img_planta = cv2.imread(planta_cfg.get("referencia") or planta_cfg["imagem"])
    if a.mediana:
        import sys
        sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
        from src.video.video_source import fundo_mediana
        frame = fundo_mediana(a.fonte)
    else:
        frame = ler_quadro(a.fonte, a.quadro)
    if frame is None or img_planta is None:
        raise SystemExit("Não consegui abrir o vídeo/imagem ou a planta.")

    saida = Path(a.saida_dir) / f"{a.camera}.yaml"
    pares: list[list[list[float]]] = []      # [[xv, yv], [xp, yp]]
    pendente = None
    poligono: list[tuple[float, float]] = []
    modo_mascara = sobrepor = False
    H = None
    erros = np.array([])

    if saida.exists():  # continua uma calibração anterior
        ant = yaml.safe_load(saida.read_text(encoding="utf-8"))
        pares = [[p["video"], p["planta_px"]] for p in ant.get("pontos", [])]
        poligono = [tuple(p) for p in ant.get("mascara_poligono", [])]
        print(f"Carreguei {len(pares)} pontos de {saida}")

    def recalcular():
        nonlocal H, erros
        H, erros = None, np.array([])
        if len(pares) < 4:
            return
        v = np.float64([p[0] for p in pares]); pl = np.float64([p[1] for p in pares])
        H, _ = cv2.findHomography(v, pl, cv2.RANSAC, 0.5 * ppm)  # tolera 0,5 m
        if H is None:
            return
        proj = cv2.perspectiveTransform(v.reshape(-1, 1, 2), H).reshape(-1, 2)
        erros = np.linalg.norm(proj - pl, axis=1) / ppm
        print(f"{len(pares)} pontos | erro médio {erros.mean():.2f} m | máx {erros.max():.2f} m"
              f" (ponto {int(erros.argmax()) + 1})")

    recalcular()
    vv = Vista("VIDEO", frame)
    vp = Vista("PLANTA", img_planta)

    def marca(tela, vista, xy, cor, rot):
        x, y = vista.para_tela(*xy)
        cv2.circle(tela, (x, y), 7, cor, 2); cv2.circle(tela, (x, y), 2, cor, -1)
        cv2.putText(tela, rot, (x + 9, y - 9), cv2.FONT_HERSHEY_SIMPLEX, 0.6, cor, 2)

    def status(tela, txt):
        cv2.rectangle(tela, (0, 0), (tela.shape[1], 26), (30, 30, 30), -1)
        cv2.putText(tela, txt, (8, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1)

    def desenha_video(tela, vista):
        if sobrepor and H is not None:
            hw = frame.shape[1], frame.shape[0]
            warp = cv2.warpPerspective(img_planta, np.linalg.inv(H), hw, borderValue=(255, 255, 255))
            mix = cv2.addWeighted(frame, 0.5, warp, 0.5, 0)
            M = np.array([[vista.zoom, 0, -vista.ox * vista.zoom], [0, vista.zoom, -vista.oy * vista.zoom]])
            tela[:] = cv2.warpAffine(mix, M, (vista.vw, vista.vh), borderValue=(60, 60, 60))
        for i, (pv, _) in enumerate(pares):
            marca(tela, vista, pv, COR_PAR[i % 10], str(i + 1))
        if pendente:
            marca(tela, vista, pendente, (0, 255, 255), "?")
        e = f" | erro medio {erros.mean():.2f} m" if len(erros) else ""
        status(tela, f"{a.camera}: {len(pares)} pontos{e} | " +
               ("agora clique na PLANTA" if pendente else "clique um ponto do chao"))

    def desenha_planta(tela, vista):
        if len(poligono) >= 2:
            pts = np.int32([vista.para_tela(*p) for p in poligono])
            cv2.polylines(tela, [pts], True, (255, 0, 255), 2)
        for i, (_, pp) in enumerate(pares):
            marca(tela, vista, pp, COR_PAR[i % 10], str(i + 1))
            if H is not None and i < len(erros):
                v = cv2.perspectiveTransform(np.float64([[pares[i][0]]]), H)[0, 0]
                cv2.line(tela, vista.para_tela(*pp), vista.para_tela(*v), (0, 0, 255), 1)
        status(tela, "MODO MASCARA: clique os vertices (m para sair)" if modo_mascara else
               f"piso {a.piso} | z desfaz | v sobrepor | m mascara | s salva | q sai")

    while True:
        if vv.clique:
            if not modo_mascara:
                pendente = vv.clique
            vv.clique = None
        if vp.clique:
            if modo_mascara:
                poligono.append(vp.clique)
            elif pendente:
                pares.append([list(pendente), list(vp.clique)]); pendente = None; recalcular()
            else:
                print("Clique primeiro o ponto no VIDEO.")
            vp.clique = None
        vv.mostrar(desenha_video); vp.mostrar(desenha_planta)
        k = cv2.waitKey(20) & 0xFF
        if k in (27, ord("q")):
            break
        if k == ord("z"):
            if modo_mascara and poligono: poligono.pop()
            elif pendente: pendente = None
            elif pares: pares.pop(); recalcular()
        elif k == ord("v"):
            sobrepor = not sobrepor
        elif k == ord("m"):
            modo_mascara = not modo_mascara
        elif k == ord("x"):
            poligono.clear()
        elif k == ord("s"):
            if H is None:
                print("Preciso de pelo menos 4 pontos."); continue
            saida.parent.mkdir(parents=True, exist_ok=True)
            dados = {
                "camera_id": a.camera, "piso": a.piso, "fonte": str(a.fonte),
                "frame_tamanho": [frame.shape[1], frame.shape[0]],
                "calibrado_em": dt.datetime.now().isoformat(timespec="seconds"),
                "erro_medio_m": round(float(erros.mean()), 3), "erro_max_m": round(float(erros.max()), 3),
                "pontos": [{"video": [round(c, 1) for c in pv], "planta_px": [round(c, 1) for c in pp],
                            "planta_m": [round(c / ppm, 2) for c in pp], "erro_m": round(float(e), 3)}
                           for (pv, pp), e in zip(pares, erros)],
                "H": [[float(c) for c in lin] for lin in H],
            }
            if len(poligono) >= 3:
                h, w = img_planta.shape[:2]
                mask = np.zeros((h, w), np.uint8)
                cv2.fillPoly(mask, [np.int32(poligono)], 255)
                mpath = Path("data/planta/mascaras") / f"{a.camera}.png"
                mpath.parent.mkdir(parents=True, exist_ok=True)
                cv2.imwrite(str(mpath), mask)
                dados["mascara"] = mpath.as_posix()
                dados["mascara_poligono"] = [[round(x, 1), round(y, 1)] for x, y in poligono]
            saida.write_text(yaml.safe_dump(dados, allow_unicode=True, sort_keys=False), encoding="utf-8")
            print(f"Salvo em {saida}")
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()

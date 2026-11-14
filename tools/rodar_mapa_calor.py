"""Vídeo -> detecção + tracking -> projeção na planta -> mapa de calor.

Uso:
  python tools/rodar_mapa_calor.py --camera configs/cameras/cam01.yaml --video video.mp4
  python tools/rodar_mapa_calor.py --camera configs/cameras/cam01.yaml configs/cameras/cam02.yaml \
         --video cam01.mp4 cam02.mp4 --saida saida/terreo_calor.png
Todas as câmeras precisam ser do mesmo piso.
"""
from __future__ import annotations
import argparse, sys
from pathlib import Path
import cv2
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.projection.homografia import CameraPlanta   # noqa: E402
from src.heatmap.mapa_calor import MapaCalor          # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--camera", nargs="+", required=True)
    ap.add_argument("--video", nargs="+", required=True)
    ap.add_argument("--modelo", default="yolov8n.pt")
    ap.add_argument("--tracker", default="configs/bytetrack_mot20.yaml")
    ap.add_argument("--planta-yaml", default="configs/planta.yaml")
    ap.add_argument("--celula", type=float, default=0.5, help="tamanho da célula em metros")
    ap.add_argument("--saida", default="saida/mapa_calor.png")
    ap.add_argument("--mostrar", action="store_true")
    a = ap.parse_args()
    if len(a.camera) != len(a.video):
        raise SystemExit("Informe um vídeo para cada câmera.")

    from ultralytics import YOLO

    cams = [CameraPlanta.carregar(c, a.planta_yaml) for c in a.camera]
    pisos = {c.piso for c in cams}
    if len(pisos) > 1:
        raise SystemExit(f"Câmeras de pisos diferentes: {pisos}")
    piso = yaml.safe_load(Path(a.planta_yaml).read_text(encoding="utf-8"))["pisos"][pisos.pop()]
    fundo = cv2.imread(piso["imagem"])
    h, w = fundo.shape[:2]
    mapa = MapaCalor(w, h, piso["px_por_metro"], a.celula)

    for cam, video in zip(cams, a.video):
        modelo = YOLO(a.modelo)   # um modelo por câmera: o tracker guarda estado
        n = 0
        for r in modelo.track(source=video, classes=[0], tracker=a.tracker, stream=True,
                              persist=True, verbose=False):
            n += 1
            if r.boxes is None or r.boxes.id is None:
                continue
            pts, ok = cam.projetar_caixas(r.boxes.xyxy.cpu().numpy())
            ids = r.boxes.id.int().cpu().tolist()
            mapa.adicionar(pts[ok], [i for i, v in zip(ids, ok) if v], camera=cam.camera_id)
            if a.mostrar and n % 5 == 0:
                cv2.imshow("video", r.plot())
                cv2.imshow("mapa", cv2.resize(mapa.desenhar(fundo), None, fx=0.25, fy=0.25))
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break
        print(f"{cam.camera_id}: {n} quadros processados")

    Path(a.saida).parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(a.saida, mapa.desenhar(fundo))
    print("Mapa de calor salvo em", a.saida)


if __name__ == "__main__":
    main()

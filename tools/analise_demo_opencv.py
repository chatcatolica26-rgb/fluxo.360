"""Análise de DEMONSTRAÇÃO sem YOLO: detector HOG do OpenCV + rastreador simples por sobreposição.

Serve para mostrar o fluxo completo (vídeo -> pessoas -> planta -> mapa de calor) em máquinas
onde o YOLO/PyTorch não está instalado. A qualidade é menor que a do YOLO + ByteTrack:
perde pessoas em grupos e troca mais ids. Para resultados oficiais use:

    python -m src.experiments.run_shopping

Uso:
    python tools/analise_demo_opencv.py                 # vídeo inteiro
    python tools/analise_demo_opencv.py --fim 2         # mesmos argumentos do run_shopping
"""
from __future__ import annotations

import sys
from pathlib import Path

import cv2
import numpy as np
from scipy.optimize import linear_sum_assignment

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.experiments import run_shopping  # noqa: E402
from src.tracking import Track  # noqa: E402
from src.video import fundo_mediana  # noqa: E402

# Caixa do HOG é folgada: os pés ficam em ~86% da altura (medido em 3 pessoas do vídeo da praça).
FRACAO_PES = 0.86


def _iou(a, b):
    ax2, ay2, bx2, by2 = a[0] + a[2], a[1] + a[3], b[0] + b[2], b[1] + b[3]
    iw = max(0.0, min(ax2, bx2) - max(a[0], b[0]))
    ih = max(0.0, min(ay2, by2) - max(a[1], b[1]))
    inter = iw * ih
    return inter / (a[2] * a[3] + b[2] * b[3] - inter + 1e-9)


class DetectorHOG:
    """HOG + SVM de pessoas do OpenCV, com filtro pelo fundo vazio (descarta manequins e objetos parados)."""

    def __init__(self, fundo_bgr: np.ndarray | None, limiar: float = 0.3, min_movel: float = 0.12,
                 faixa: tuple[float, float] = (0.08, 0.55)):
        self.faixa = faixa
        self.hog = cv2.HOGDescriptor()
        self.hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())
        self.fundo = None if fundo_bgr is None else cv2.GaussianBlur(fundo_bgr, (5, 5), 0)
        self.limiar, self.min_movel = limiar, min_movel

    def _detectar(self, img):
        caixas, pesos = self.hog.detectMultiScale(img, winStride=(8, 8), padding=(8, 8), scale=1.05)
        return [list(map(float, c)) for c in caixas], list(np.asarray(pesos).ravel())

    def __call__(self, img):
        caixas, pesos = self._detectar(img)
        # O HOG só acha pessoas com ~128 px ou mais de altura: as do fundo são menores.
        # Por isso a faixa de cima da imagem é ampliada 2x e passa pelo detector de novo.
        y0, y1 = int(img.shape[0] * self.faixa[0]), int(img.shape[0] * self.faixa[1])
        amp = cv2.resize(img[y0:y1], None, fx=2, fy=2, interpolation=cv2.INTER_LINEAR)
        c2, p2 = self._detectar(amp)
        caixas += [[x / 2, y / 2 + y0, w / 2, h / 2] for x, y, w, h in c2]
        pesos += p2
        if not caixas:
            return []
        caixas = np.array(caixas)
        pesos = np.asarray(pesos).ravel()
        idx = cv2.dnn.NMSBoxes([[int(v) for v in c] for c in caixas], pesos.tolist(), self.limiar, 0.4)
        idx = np.array(idx).ravel() if len(idx) else []
        fg = None
        if self.fundo is not None:
            d = cv2.absdiff(cv2.GaussianBlur(img, (5, 5), 0), self.fundo).max(axis=2)
            fg = d > 35
        saida = []
        for i in idx:
            x, y, w, h = map(float, caixas[i])
            if fg is not None:
                reg = fg[int(y + .1 * h):int(y + .85 * h), int(x + .3 * w):int(x + .7 * w)]
                if reg.size == 0 or reg.mean() < self.min_movel:
                    continue                      # nada se mexe ali: manequim, pilar, reflexo fixo
            # caixa ajustada ao corpo: base da caixa = pés
            saida.append((x + .2 * w, y + .08 * h, .6 * w, (FRACAO_PES - .08) * h, float(pesos[i])))
        return saida


class RastreadorSimples:
    """Associa detecções entre quadros por sobreposição (IoU) + distância, com velocidade constante."""

    descricao = "OpenCV HOG + rastreador simples (demonstração, sem YOLO)"

    def __init__(self, detector, iou_min: float = 0.3, dist_max: float = 0.15, espera: int = 24,
                 confirmar: int = 4, alfa: float = 0.5):
        self.det, self.iou_min, self.dist_max = detector, iou_min, dist_max
        self.espera, self.confirmar, self.alfa = espera, confirmar, alfa
        self.reset()

    def reset(self):
        self.tracks, self.prox_id = [], 1

    def update(self, img):
        dets = self.det(img)
        for t in self.tracks:                     # previsão: anda com a última velocidade
            t["prev"] = [t["box"][0] + t["v"][0], t["box"][1] + t["v"][1], t["box"][2], t["box"][3]]
        livres = list(range(len(dets)))
        if self.tracks and dets:
            custo = np.ones((len(self.tracks), len(dets)))
            for i, t in enumerate(self.tracks):
                for j, d in enumerate(dets):
                    iou = _iou(t["prev"], d[:4])
                    dist = np.hypot(t["prev"][0] + t["prev"][2] / 2 - d[0] - d[2] / 2,
                                    t["prev"][1] + t["prev"][3] - d[1] - d[3]) / max(d[3], 1)
                    custo[i, j] = 1 - iou if iou > 0 else (1 + dist)
            lin, col = linear_sum_assignment(custo)
            for i, j in zip(lin, col):
                # aceita se as caixas se sobrepõem bem, ou se o pé andou pouco (< 15% da altura da pessoa)
                if custo[i, j] <= 1 - self.iou_min or 1 < custo[i, j] < 1 + self.dist_max:
                    t, d = self.tracks[i], dets[j]
                    # suavização: o HOG oscila alguns pixels de um quadro para o outro
                    nova = [self.alfa * a + (1 - self.alfa) * b for a, b in zip(d[:4], t["prev"])]
                    t["v"] = [0.7 * t["v"][0] + 0.3 * (nova[0] - t["box"][0]), 0.7 * t["v"][1] + 0.3 * (nova[1] - t["box"][1])]
                    t.update(box=nova, score=d[4], perdido=0, hits=t["hits"] + 1, visto=True)
                    livres.remove(j)
        for j in livres:
            d = dets[j]
            self.tracks.append({"id": None, "box": list(d[:4]), "v": [0.0, 0.0], "score": d[4], "perdido": 0,
                                "hits": 1, "visto": True})
        saida = []
        for t in self.tracks:
            if not t.pop("visto", False):
                t["perdido"] += 1
                continue
            if t["hits"] >= self.confirmar:
                if t["id"] is None:
                    t["id"], self.prox_id = self.prox_id, self.prox_id + 1
                saida.append(Track(t["id"], *t["box"], t["score"]))
        self.tracks = [t for t in self.tracks if t["perdido"] <= self.espera]
        return saida


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    cfg = run_shopping.load_config("configs/analise_shopping.yaml")
    video = argv[argv.index("--video") + 1] if "--video" in argv else cfg["video"]["arquivo"]
    print("Detector de DEMONSTRAÇÃO (OpenCV HOG), não o YOLO. Calculando o fundo vazio do vídeo...")
    try:
        fundo = fundo_mediana(video)
    except Exception as e:  # RTSP ou vídeo sem contagem de quadros
        print("Sem fundo vazio:", e)
        fundo = None
    if "--nome" not in argv:
        argv += ["--nome", "demo_opencv"]
    return run_shopping.main(argv, runner=RastreadorSimples(DetectorHOG(fundo)))


if __name__ == "__main__":
    main()

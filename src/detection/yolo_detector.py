"""Detecção de pessoas com YOLO (Ultralytics).

A biblioteca ``ultralytics`` só é importada quando o detector é criado, então
o restante do projeto (leitura do MOT20, avaliação, testes) funciona sem ela.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

PERSON_CLASS = 0  # classe "person" no COCO


@dataclass
class Detection:
    x: float
    y: float
    w: float
    h: float
    score: float


def _load_yolo(model_path: str):
    try:
        from ultralytics import YOLO
    except ImportError as exc:  # pragma: no cover - depende do ambiente
        raise ImportError("o pacote 'ultralytics' não está instalado. Rode: pip install -r requirements.txt") from exc
    return YOLO(model_path)


class YoloPersonDetector:
    """Detecta apenas pessoas e devolve caixas no formato ``x, y, w, h``."""

    def __init__(self, model: str = "yolov8n.pt", conf: float = 0.25, iou: float = 0.7,
                 imgsz: int = 1280, device: str | None = None, model_obj=None):
        self.model = model_obj if model_obj is not None else _load_yolo(model)
        self.conf, self.iou, self.imgsz, self.device = conf, iou, imgsz, device

    def detect(self, image: np.ndarray) -> list[Detection]:
        results = self.model.predict(image, conf=self.conf, iou=self.iou, imgsz=self.imgsz,
                                     classes=[PERSON_CLASS], device=self.device, verbose=False)
        boxes = results[0].boxes
        if boxes is None or len(boxes) == 0:
            return []
        xyxy = boxes.xyxy.cpu().numpy()
        scores = boxes.conf.cpu().numpy()
        return [Detection(float(x1), float(y1), float(x2 - x1), float(y2 - y1), float(s))
                for (x1, y1, x2, y2), s in zip(xyxy, scores)]

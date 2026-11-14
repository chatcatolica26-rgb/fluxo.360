"""Rastreamento de pessoas com YOLO + ByteTrack (implementação da Ultralytics).

Cada pessoa recebe um identificador temporário que deve se manter enquanto
ela estiver visível. Os ids não identificam ninguém: são números internos da
sequência e recomeçam a cada ``reset()``.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ..detection.yolo_detector import PERSON_CLASS, _load_yolo


@dataclass
class Track:
    track_id: int
    x: float
    y: float
    w: float
    h: float
    score: float


class ByteTrackPersonTracker:
    """Detecta e rastreia pessoas quadro a quadro.

    ``tracker_config`` é o YAML do ByteTrack: ``"bytetrack.yaml"`` usa o padrão
    da Ultralytics; ``configs/bytetrack_mot20.yaml`` traz parâmetros ajustáveis.
    """

    def __init__(self, model: str = "yolov8n.pt", conf: float = 0.1, iou: float = 0.7, imgsz: int = 1280,
                 tracker_config: str = "bytetrack.yaml", device: str | None = None, model_factory=None):
        self.model_name = model
        self.conf, self.iou, self.imgsz, self.device = conf, iou, imgsz, device
        self.tracker_config = tracker_config
        self._factory = model_factory or _load_yolo
        self.model = self._factory(model)

    def reset(self) -> None:
        """Começa uma nova sequência (zera os ids e o histórico do ByteTrack)."""
        self.model = self._factory(self.model_name)

    def update(self, image: np.ndarray) -> list[Track]:
        results = self.model.track(image, persist=True, tracker=self.tracker_config, conf=self.conf,
                                   iou=self.iou, imgsz=self.imgsz, classes=[PERSON_CLASS],
                                   device=self.device, verbose=False)
        boxes = results[0].boxes
        if boxes is None or len(boxes) == 0 or boxes.id is None:
            return []
        xyxy = boxes.xyxy.cpu().numpy()
        ids = boxes.id.cpu().numpy().astype(int)
        scores = boxes.conf.cpu().numpy()
        return [Track(int(i), float(x1), float(y1), float(x2 - x1), float(y2 - y1), float(s))
                for i, (x1, y1, x2, y2), s in zip(ids, xyxy, scores)]

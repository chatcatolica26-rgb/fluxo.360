"""Leitura, interpretação e escrita de anotações no formato MOTChallenge.

Formato das linhas (separadas por vírgula, coordenadas em pixels, origem no
canto superior esquerdo da imagem, quadros numerados a partir de 1):

* ``gt/gt.txt`` (Ground Truth do MOT20):
  ``frame, id, bb_left, bb_top, bb_width, bb_height, flag, classe, visibilidade``
* ``det/det.txt`` (detecções públicas):
  ``frame, -1, bb_left, bb_top, bb_width, bb_height, confiança, -1, -1, -1``
* Resultados de rastreamento (o que o Fluxo360 gera):
  ``frame, id, bb_left, bb_top, bb_width, bb_height, confiança, -1, -1, -1``

No Ground Truth, só contam como pessoas a avaliar as linhas com
``classe == 1`` (pedestre) e ``flag == 1``. As classes 2, 6, 7, 8 e 12 são
"distratores": previsões que caem sobre elas não são contadas nem como acerto
nem como erro (mesma regra do avaliador oficial).

Este módulo não depende de nenhum algoritmo de detecção ou rastreamento.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator

import numpy as np

# Classes do MOT20 (MOT16/17/20 usam a mesma tabela).
PEDESTRIAN = 1
PERSON_ON_VEHICLE = 2
NON_MOT_VEHICLE = 6
STATIC_PERSON = 7
DISTRACTOR = 8
REFLECTION = 12
# No MOT20 o avaliador oficial também trata "veículo não motorizado" (6) como distrator.
DISTRACTOR_CLASSES = frozenset({PERSON_ON_VEHICLE, NON_MOT_VEHICLE, STATIC_PERSON, DISTRACTOR, REFLECTION})

CLASS_NAMES = {
    1: "pedestre", 2: "pessoa em veículo", 3: "carro", 4: "bicicleta", 5: "moto",
    6: "veículo não motorizado", 7: "pessoa parada", 8: "distrator", 9: "oclusor",
    10: "oclusor no chão", 11: "oclusor total", 12: "reflexo", 13: "multidão",
}


class AnnotationFormatError(ValueError):
    """Linha de anotação malformada."""


@dataclass
class MOTAnnotations:
    """Conjunto de caixas no formato MOT, guardado em arrays NumPy alinhados.

    ``boxes`` está em ``[x, y, w, h]`` (canto superior esquerdo + tamanho).
    """

    frames: np.ndarray                      # (N,) int
    ids: np.ndarray                         # (N,) int  (-1 para detecções sem id)
    boxes: np.ndarray                       # (N, 4) float  xywh
    scores: np.ndarray                      # (N,) float  (flag no GT, confiança nas previsões)
    classes: np.ndarray                     # (N,) int   (-1 quando não se aplica)
    visibility: np.ndarray                  # (N,) float (-1 quando não se aplica)
    source: str = field(default="", compare=False)

    # ------------------------------------------------------------------ básicos
    def __len__(self) -> int:
        return int(self.frames.shape[0])

    @classmethod
    def empty(cls, source: str = "") -> "MOTAnnotations":
        return cls(np.zeros(0, int), np.zeros(0, int), np.zeros((0, 4), float),
                   np.zeros(0, float), np.zeros(0, int), np.zeros(0, float), source)

    def subset(self, mask: np.ndarray) -> "MOTAnnotations":
        return MOTAnnotations(self.frames[mask], self.ids[mask], self.boxes[mask],
                              self.scores[mask], self.classes[mask], self.visibility[mask],
                              self.source)

    def frame_numbers(self) -> np.ndarray:
        """Quadros que têm pelo menos uma caixa, em ordem crescente."""
        return np.unique(self.frames)

    def in_frame(self, frame: int) -> "MOTAnnotations":
        return self.subset(self.frames == frame)

    def iter_frames(self) -> Iterator[tuple[int, "MOTAnnotations"]]:
        order = np.argsort(self.frames, kind="stable")
        sorted_frames = self.frames[order]
        starts = np.flatnonzero(np.r_[True, sorted_frames[1:] != sorted_frames[:-1]])
        ends = np.r_[starts[1:], len(order)]
        for s, e in zip(starts, ends):
            yield int(sorted_frames[s]), self.subset(order[s:e])

    def unique_ids(self) -> np.ndarray:
        return np.unique(self.ids[self.ids >= 0])

    def counts_per_frame(self, frames: np.ndarray | None = None) -> np.ndarray:
        """Quantidade de caixas por quadro (na ordem de ``frames``)."""
        if frames is None:
            frames = self.frame_numbers()
        values, counts = np.unique(self.frames, return_counts=True)
        lookup = dict(zip(values.tolist(), counts.tolist()))
        return np.array([lookup.get(int(f), 0) for f in frames], dtype=int)

    # ------------------------------------------------------------- coordenadas
    def boxes_xyxy(self) -> np.ndarray:
        return xywh_to_xyxy(self.boxes)

    def centers(self) -> np.ndarray:
        """Centro de cada caixa (x, y) em pixels."""
        return self.boxes[:, :2] + self.boxes[:, 2:] / 2.0

    def clipped(self, width: int, height: int) -> "MOTAnnotations":
        """Cópia com as caixas recortadas aos limites da imagem."""
        xyxy = self.boxes_xyxy()
        xyxy[:, [0, 2]] = np.clip(xyxy[:, [0, 2]], 0, width)
        xyxy[:, [1, 3]] = np.clip(xyxy[:, [1, 3]], 0, height)
        out = self.subset(np.ones(len(self), bool))
        out.boxes = xyxy_to_xywh(xyxy)
        return out


# ---------------------------------------------------------------- conversões
def xywh_to_xyxy(boxes: np.ndarray) -> np.ndarray:
    boxes = np.asarray(boxes, dtype=float).reshape(-1, 4)
    out = boxes.copy()
    out[:, 2] = boxes[:, 0] + boxes[:, 2]
    out[:, 3] = boxes[:, 1] + boxes[:, 3]
    return out


def xyxy_to_xywh(boxes: np.ndarray) -> np.ndarray:
    boxes = np.asarray(boxes, dtype=float).reshape(-1, 4)
    out = boxes.copy()
    out[:, 2] = boxes[:, 2] - boxes[:, 0]
    out[:, 3] = boxes[:, 3] - boxes[:, 1]
    return out


# ------------------------------------------------------------------- leitura
def read_mot_file(path: str | Path, kind: str = "auto") -> MOTAnnotations:
    """Lê um arquivo MOT (``gt``, ``det`` ou resultados de rastreamento).

    ``kind`` pode ser ``"gt"``, ``"det"``, ``"result"`` ou ``"auto"`` (decide
    pelo nome do arquivo/pasta). Linhas vazias são ignoradas; linhas com menos
    de 6 colunas ou valores não numéricos geram ``AnnotationFormatError``
    indicando o número da linha.
    """
    path = Path(path)
    if kind == "auto":
        kind = "gt" if path.parent.name == "gt" or path.name.startswith("gt") else (
            "det" if path.parent.name == "det" else "result")
    if kind not in {"gt", "det", "result"}:
        raise ValueError(f"tipo de anotação desconhecido: {kind}")

    rows: list[list[float]] = []
    with open(path, encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, start=1):
            line = line.strip()
            if not line:
                continue
            parts = [p.strip() for p in line.split(",")]
            while parts and parts[-1] == "":      # vírgula no fim da linha
                parts.pop()
            if len(parts) < 6:
                raise AnnotationFormatError(f"{path}:{lineno}: esperado ao menos 6 colunas, encontrado {len(parts)}")
            try:
                values = [float(p) for p in parts]
            except ValueError as exc:
                raise AnnotationFormatError(f"{path}:{lineno}: valor não numérico ({exc})") from None
            values += [-1.0] * (9 - len(values))
            rows.append(values[:9])

    if not rows:
        return MOTAnnotations.empty(str(path))
    arr = np.asarray(rows, dtype=float)
    frames = arr[:, 0].astype(int)
    if (frames < 1).any():
        bad = int(np.flatnonzero(frames < 1)[0]) + 1
        raise AnnotationFormatError(f"{path}: quadro menor que 1 na linha de dados {bad}")
    if (arr[:, 4] < 0).any() or (arr[:, 5] < 0).any():
        raise AnnotationFormatError(f"{path}: largura ou altura negativa")

    if kind == "gt":
        classes = arr[:, 7].astype(int)
        visibility = arr[:, 8]
    else:
        classes = np.full(len(arr), -1, int)
        visibility = np.full(len(arr), -1.0)
    return MOTAnnotations(frames=frames, ids=arr[:, 1].astype(int), boxes=arr[:, 2:6].copy(),
                          scores=arr[:, 6].copy(), classes=classes, visibility=visibility,
                          source=str(path))


@dataclass
class GroundTruth:
    """Ground Truth separado entre pessoas avaliadas e distratores."""

    pedestrians: MOTAnnotations
    distractors: MOTAnnotations
    ignored: MOTAnnotations            # demais classes (veículos, oclusores...)


def load_ground_truth(path: str | Path, min_visibility: float = 0.0) -> GroundTruth:
    """Lê ``gt.txt`` e separa pedestres válidos, distratores e o restante.

    ``min_visibility`` permite descartar pedestres muito ocluídos (0 a 1).
    Pedestres abaixo do limite passam a ser tratados como distratores, para
    que uma previsão correta sobre eles não seja punida como falso positivo.
    """
    gt = read_mot_file(path, kind="gt")
    is_ped = (gt.classes == PEDESTRIAN) & (gt.scores > 0)
    visible = gt.visibility >= min_visibility
    ped_mask = is_ped & visible
    distractor_mask = np.isin(gt.classes, list(DISTRACTOR_CLASSES)) | (is_ped & ~visible)
    ignored_mask = ~(ped_mask | distractor_mask)
    return GroundTruth(gt.subset(ped_mask), gt.subset(distractor_mask), gt.subset(ignored_mask))


# -------------------------------------------------------------------- escrita
def write_mot_results(path: str | Path, frames, ids, boxes, scores=None) -> Path:
    """Grava resultados no formato aceito pelo MOTChallenge (10 colunas)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    frames = np.asarray(frames, int).reshape(-1)
    ids = np.asarray(ids, int).reshape(-1)
    boxes = np.asarray(boxes, float).reshape(-1, 4)
    scores = np.ones(len(frames)) if scores is None else np.asarray(scores, float).reshape(-1)
    if not (len(frames) == len(ids) == len(boxes) == len(scores)):
        raise ValueError("frames, ids, boxes e scores precisam ter o mesmo tamanho")
    order = np.lexsort((ids, frames))
    with open(path, "w", encoding="utf-8") as fh:
        for i in order:
            x, y, w, h = boxes[i]
            fh.write(f"{frames[i]},{ids[i]},{x:.2f},{y:.2f},{w:.2f},{h:.2f},{scores[i]:.4f},-1,-1,-1\n")
    return path


def annotations_from_records(records: list[tuple[int, int, float, float, float, float, float]],
                             source: str = "") -> MOTAnnotations:
    """Monta ``MOTAnnotations`` a partir de tuplas ``(frame, id, x, y, w, h, score)``."""
    if not records:
        return MOTAnnotations.empty(source)
    arr = np.asarray(records, dtype=float)
    n = len(arr)
    return MOTAnnotations(arr[:, 0].astype(int), arr[:, 1].astype(int), arr[:, 2:6].copy(),
                          arr[:, 6].copy(), np.full(n, -1, int), np.full(n, -1.0), source)

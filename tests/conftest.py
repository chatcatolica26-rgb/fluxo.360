"""Base MOT20 sintética e pequena, criada em pasta temporária para os testes.

Os testes nunca usam os arquivos reais do MOT20 (que não vão para o GitHub).
"""
from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
import pytest

N_FRAMES = 10
WIDTH, HEIGHT = 64, 48


def gt_rows():
    """Três pedestres andando, um distrator (classe 8) e um carro (classe 3)."""
    rows = []
    for f in range(1, N_FRAMES + 1):
        rows.append((f, 1, 2 + f, 5, 8, 16, 1, 1, 1.0))       # pedestre 1
        rows.append((f, 2, 30, 10 + f, 8, 16, 1, 1, 0.8))     # pedestre 2
        if f <= 5:
            rows.append((f, 3, 45, 20, 8, 16, 1, 1, 0.1))     # pedestre 3 (muito ocluído)
        rows.append((f, 10, 50, 2, 6, 12, 0, 8, 1.0))         # distrator
        rows.append((f, 11, 5, 30, 20, 10, 0, 3, 1.0))        # carro (ignorado)
    return rows


def _write_seq(root: Path, split: str, name: str, with_gt: bool, n_frames: int = N_FRAMES):
    seq = root / split / name
    (seq / "img1").mkdir(parents=True)
    (seq / "det").mkdir()
    (seq / "seqinfo.ini").write_text(
        "[Sequence]\n"
        f"name={name}\nimDir=img1\nframeRate=25\nseqLength={n_frames}\n"
        f"imWidth={WIDTH}\nimHeight={HEIGHT}\nimExt=.jpg\n", encoding="utf-8")
    for f in range(1, n_frames + 1):
        img = np.full((HEIGHT, WIDTH, 3), f * 10, np.uint8)
        cv2.imwrite(str(seq / "img1" / f"{f:06d}.jpg"), img)
    (seq / "det" / "det.txt").write_text(
        "".join(f"{f},-1,{2 + f},5,8,16,0.9,-1,-1,-1\n" for f in range(1, n_frames + 1)), encoding="utf-8")
    if with_gt:
        (seq / "gt").mkdir()
        (seq / "gt" / "gt.txt").write_text(
            "".join(",".join(str(v) for v in r) + "\n" for r in gt_rows()), encoding="utf-8")
    return seq


@pytest.fixture
def mot20_root(tmp_path: Path) -> Path:
    root = tmp_path / "mot20"
    _write_seq(root, "train", "MOT20-01", with_gt=True)
    _write_seq(root, "test", "MOT20-04", with_gt=False)
    return root


class GroundTruthRunner:
    """'Rastreador' perfeito: devolve as caixas de pedestres do próprio GT."""

    def __init__(self, gt_path: Path, id_offset: int = 100):
        from src.dataset import load_ground_truth
        gt = load_ground_truth(gt_path).pedestrians
        self.by_frame = {f: a for f, a in gt.iter_frames()}
        self.frame = 0
        self.id_offset = id_offset

    def reset(self):
        self.frame = 0

    def update(self, image):
        self.frame += 1
        a = self.by_frame.get(self.frame)
        if a is None:
            return []
        return [(int(i) + self.id_offset, *map(float, b), 0.9) for i, b in zip(a.ids, a.boxes)]

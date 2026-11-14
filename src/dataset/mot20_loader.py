"""Localização e carregamento das sequências do MOT20.

Estrutura esperada (a mesma do arquivo ``MOT20.zip`` oficial, extraído em
``data/raw/mot20``)::

    data/raw/mot20/
        train/MOT20-01/{seqinfo.ini, img1/000001.jpg ..., gt/gt.txt, det/det.txt}
        test/MOT20-04/{seqinfo.ini, img1/..., det/det.txt}

Também é aceito um nível extra ``data/raw/mot20/MOT20/train/...``.

As sequências do MOT20 são distribuídas como quadros JPEG, não como arquivos
de vídeo. ``iter_frames`` lê os quadros em ordem com OpenCV e
``export_video`` gera um ``.mp4`` quando for útil (por exemplo, para testar
o pipeline com a mesma entrada de uma câmera).
"""
from __future__ import annotations

import configparser
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

import numpy as np

# Descrição das oito sequências (conforme o MOTChallenge).
SEQUENCES: dict[str, dict[str, str]] = {
    "MOT20-01": {"split": "train", "cena": "estação ferroviária com grande concentração de pessoas"},
    "MOT20-02": {"split": "train", "cena": "estação ferroviária movimentada"},
    "MOT20-03": {"split": "train", "cena": "saída de estádio durante a noite"},
    "MOT20-05": {"split": "train", "cena": "praça com grande concentração de pessoas"},
    "MOT20-04": {"split": "test", "cena": "praça movimentada durante a noite"},
    "MOT20-06": {"split": "test", "cena": "rua de pedestres"},
    "MOT20-07": {"split": "test", "cena": "estação ferroviária movimentada"},
    "MOT20-08": {"split": "test", "cena": "rua de pedestres"},
}
TRAIN_SEQUENCES = [n for n, s in SEQUENCES.items() if s["split"] == "train"]
TEST_SEQUENCES = [n for n, s in SEQUENCES.items() if s["split"] == "test"]
# Ordem sugerida para os primeiros experimentos.
PRIORITY_SEQUENCES = ["MOT20-01", "MOT20-02"]


class DatasetNotFoundError(FileNotFoundError):
    """Base ou sequência não encontrada no disco."""


@dataclass(frozen=True)
class SequenceInfo:
    name: str
    split: str                 # "train" ou "test"
    path: Path
    frame_rate: float
    seq_length: int
    width: int
    height: int
    img_dir: str = "img1"
    img_ext: str = ".jpg"

    @property
    def image_dir(self) -> Path:
        return self.path / self.img_dir

    @property
    def gt_path(self) -> Path:
        return self.path / "gt" / "gt.txt"

    @property
    def det_path(self) -> Path:
        return self.path / "det" / "det.txt"

    @property
    def has_ground_truth(self) -> bool:
        return self.gt_path.is_file()

    @property
    def description(self) -> str:
        return SEQUENCES.get(self.name, {}).get("cena", "")

    def frame_path(self, frame: int) -> Path:
        """Caminho do quadro ``frame`` (numeração a partir de 1)."""
        return self.image_dir / f"{frame:06d}{self.img_ext}"


def read_seqinfo(seq_dir: str | Path) -> dict[str, str]:
    """Lê ``seqinfo.ini`` e devolve a seção ``[Sequence]``."""
    ini = Path(seq_dir) / "seqinfo.ini"
    if not ini.is_file():
        raise DatasetNotFoundError(f"seqinfo.ini não encontrado em {seq_dir}")
    parser = configparser.ConfigParser()
    parser.optionxform = str  # mantém maiúsculas/minúsculas das chaves
    parser.read(ini, encoding="utf-8")
    if "Sequence" not in parser:
        raise ValueError(f"{ini}: seção [Sequence] ausente")
    return dict(parser["Sequence"])


class MOT20Dataset:
    """Acesso às sequências do MOT20 em disco."""

    def __init__(self, root: str | Path = "data/raw/mot20"):
        root = Path(root)
        if (root / "MOT20").is_dir() and not (root / "train").is_dir():
            root = root / "MOT20"
        if not root.is_dir():
            raise DatasetNotFoundError(
                f"pasta da base não encontrada: {root}. Baixe o MOT20 em "
                "https://motchallenge.net/data/MOT20/ e extraia em data/raw/mot20/")
        self.root = root

    # --------------------------------------------------------------- consulta
    def available_sequences(self, split: str | None = None) -> list[str]:
        """Sequências presentes no disco (opcionalmente filtradas por split)."""
        names = []
        for sp in ("train", "test"):
            if split not in (None, sp):
                continue
            folder = self.root / sp
            if folder.is_dir():
                names += sorted(p.name for p in folder.iterdir() if (p / "seqinfo.ini").is_file())
        return names

    def sequence(self, name: str) -> SequenceInfo:
        split = SEQUENCES.get(name, {}).get("split")
        candidates = [self.root / split / name] if split else []
        candidates += [self.root / "train" / name, self.root / "test" / name]
        for cand in candidates:
            if (cand / "seqinfo.ini").is_file():
                info = read_seqinfo(cand)
                return SequenceInfo(
                    name=info.get("name", name),
                    split=cand.parent.name,
                    path=cand,
                    frame_rate=float(info.get("frameRate", 25)),
                    seq_length=int(info["seqLength"]),
                    width=int(info["imWidth"]),
                    height=int(info["imHeight"]),
                    img_dir=info.get("imDir", "img1"),
                    img_ext=info.get("imExt", ".jpg"),
                )
        raise DatasetNotFoundError(f"sequência {name} não encontrada em {self.root}")

    def verify(self, name: str) -> list[str]:
        """Confere se a sequência está completa. Devolve a lista de problemas."""
        seq = self.sequence(name)
        problems = []
        if not seq.image_dir.is_dir():
            return [f"pasta de imagens ausente: {seq.image_dir}"]
        n_images = len(list(seq.image_dir.glob(f"*{seq.img_ext}")))
        if n_images != seq.seq_length:
            problems.append(f"{name}: {n_images} imagens, seqinfo indica {seq.seq_length}")
        if seq.split == "train" and not seq.has_ground_truth:
            problems.append(f"{name}: gt/gt.txt ausente")
        return problems

    # ---------------------------------------------------------------- leitura
    def read_frame(self, seq: SequenceInfo | str, frame: int) -> np.ndarray:
        import cv2  # importação tardia: o resto do módulo não precisa do OpenCV

        if isinstance(seq, str):
            seq = self.sequence(seq)
        path = seq.frame_path(frame)
        image = cv2.imread(str(path))
        if image is None:
            raise DatasetNotFoundError(f"não foi possível ler o quadro {path}")
        return image

    def iter_frames(self, seq: SequenceInfo | str, start: int = 1, end: int | None = None,
                    step: int = 1) -> Iterator[tuple[int, np.ndarray]]:
        """Percorre os quadros ``start..end`` (inclusive) devolvendo ``(nº, imagem BGR)``."""
        if isinstance(seq, str):
            seq = self.sequence(seq)
        end = seq.seq_length if end is None else min(end, seq.seq_length)
        for frame in range(max(1, start), end + 1, step):
            yield frame, self.read_frame(seq, frame)

    def export_video(self, seq: SequenceInfo | str, output: str | Path, max_frames: int | None = None,
                     fourcc: str = "mp4v") -> Path:
        """Gera um arquivo de vídeo a partir dos quadros da sequência."""
        import cv2

        if isinstance(seq, str):
            seq = self.sequence(seq)
        output = Path(output)
        output.parent.mkdir(parents=True, exist_ok=True)
        writer = cv2.VideoWriter(str(output), cv2.VideoWriter_fourcc(*fourcc), seq.frame_rate,
                                 (seq.width, seq.height))
        try:
            end = seq.seq_length if max_frames is None else min(seq.seq_length, max_frames)
            for _, image in self.iter_frames(seq, 1, end):
                writer.write(image)
        finally:
            writer.release()
        return output

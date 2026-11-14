"""Executa detecção/rastreamento nas sequências do MOT20 e avalia os resultados.

Exemplos (a partir da raiz do projeto)::

    # primeiros experimentos: MOT20-01 e MOT20-02, todas as métricas
    python -m src.experiments.run_mot20 --config configs/experimento_padrao.yaml

    # teste rápido com 100 quadros
    python -m src.experiments.run_mot20 --sequences MOT20-01 --max-frames 100

    # só detecção (YOLO), sem rastreamento
    python -m src.experiments.run_mot20 --mode detect

    # reavaliar previsões já salvas
    python -m src.experiments.run_mot20 --evaluate-only data/processed/mot20/experimentos/<pasta>

Sequências de teste (MOT20-04, 06, 07, 08) só geram previsões: o Ground
Truth delas não é público e não deve ser usado para ajustar o sistema.
"""
from __future__ import annotations

import argparse
import json
import platform
import sys
import time
from datetime import datetime
from pathlib import Path

import numpy as np
import yaml

from ..dataset.evaluation import concatenate, evaluate_sequence, markdown_table, save_metrics
from ..dataset.mot20_annotations import (MOTAnnotations, annotations_from_records, load_ground_truth,
                                         read_mot_file, write_mot_results)
from ..dataset.mot20_loader import PRIORITY_SEQUENCES, MOT20Dataset, SequenceInfo

DEFAULT_CONFIG = {
    "experiment": {"name": "yolo_bytetrack"},
    "data": {"root": "data/raw/mot20", "output": "data/processed/mot20/experimentos",
             "sequences": PRIORITY_SEQUENCES},
    "detector": {"model": "yolov8n.pt", "conf": 0.1, "iou": 0.7, "imgsz": 1280, "device": None},
    "tracker": {"config": "bytetrack.yaml"},
    "evaluation": {"iou_threshold": 0.5, "min_visibility": 0.0},
}


# ------------------------------------------------------------------ configuração
def load_config(path: str | Path | None) -> dict:
    cfg = json.loads(json.dumps(DEFAULT_CONFIG))
    if path:
        with open(path, encoding="utf-8") as fh:
            user = yaml.safe_load(fh) or {}
        for section, values in user.items():
            if isinstance(values, dict) and isinstance(cfg.get(section), dict):
                cfg[section].update(values)
            else:
                cfg[section] = values
    return cfg


def build_runner(cfg: dict, mode: str):
    """Cria o objeto que processa cada quadro: rastreador (track) ou detector (detect)."""
    det = cfg["detector"]
    if mode == "track":
        from ..tracking.bytetrack_tracker import ByteTrackPersonTracker
        return ByteTrackPersonTracker(model=det["model"], conf=det["conf"], iou=det["iou"], imgsz=det["imgsz"],
                                      tracker_config=cfg["tracker"]["config"], device=det.get("device"))
    from ..detection.yolo_detector import YoloPersonDetector

    class _DetectRunner:
        def __init__(self):
            self.detector = YoloPersonDetector(model=det["model"], conf=det["conf"], iou=det["iou"],
                                               imgsz=det["imgsz"], device=det.get("device"))

        def reset(self):
            pass

        def update(self, image):
            return [(-1, d.x, d.y, d.w, d.h, d.score) for d in self.detector.detect(image)]

    return _DetectRunner()


def _as_record(frame: int, item) -> tuple:
    """Aceita ``Track``, ``Detection`` ou tupla ``(id, x, y, w, h, score)``."""
    if isinstance(item, tuple):
        tid, x, y, w, h, s = item
    else:
        tid = getattr(item, "track_id", -1)
        x, y, w, h, s = item.x, item.y, item.w, item.h, item.score
    return (frame, int(tid), float(x), float(y), float(w), float(h), float(s))


# ---------------------------------------------------------------------- execução
def run_sequence(dataset: MOT20Dataset, seq: SequenceInfo, runner, max_frames: int | None = None,
                 log=print) -> tuple[MOTAnnotations, dict]:
    """Processa os quadros de uma sequência e devolve as previsões e estatísticas."""
    runner.reset()
    end = seq.seq_length if max_frames is None else min(seq.seq_length, max_frames)
    records = []
    start = time.perf_counter()
    for frame, image in dataset.iter_frames(seq, 1, end):
        records += [_as_record(frame, item) for item in runner.update(image)]
        if log and (frame % 100 == 0 or frame == end):
            log(f"  {seq.name}: quadro {frame}/{end}")
    elapsed = time.perf_counter() - start
    stats = {"frames": end, "seconds": round(elapsed, 2), "fps": round(end / elapsed, 2) if elapsed else None}
    return annotations_from_records(records, source=seq.name), stats


def evaluate_folder(dataset: MOT20Dataset, pred_dir: Path, sequences: list[str], cfg: dict, mode: str,
                    frames_used: dict[str, int] | None = None) -> list[dict]:
    """Compara os arquivos ``<seq>.txt`` de ``pred_dir`` com o Ground Truth."""
    ev = cfg["evaluation"]
    rows, combined = [], []
    for name in sequences:
        seq = dataset.sequence(name)
        if seq.split != "train" or not seq.has_ground_truth:
            print(f"  {name}: sequência de teste, sem avaliação local (envie ao servidor do MOTChallenge)")
            continue
        pred_path = pred_dir / f"{name}.txt"
        if not pred_path.is_file():
            print(f"  {name}: previsões não encontradas em {pred_path}")
            continue
        length = (frames_used or {}).get(name, seq.seq_length)
        gt = load_ground_truth(seq.gt_path, min_visibility=ev["min_visibility"])
        gt.pedestrians = gt.pedestrians.subset(gt.pedestrians.frames <= length)
        gt.distractors = gt.distractors.subset(gt.distractors.frames <= length)
        pred = read_mot_file(pred_path, kind="result")
        row = {"Sequence": name, **evaluate_sequence(gt, pred, ev["iou_threshold"], length, mode)}
        rows.append(row)
        # previsões sem distratores, para a linha combinada
        from ..dataset.evaluation import remove_distractor_matches
        combined.append((gt.pedestrians, remove_distractor_matches(pred, gt, ev["iou_threshold"]), length))
    if len(combined) > 1:
        g, p, total = concatenate(combined)
        rows.append({"Sequence": "COMBINADO", **evaluate_sequence(g, p, ev["iou_threshold"], total, mode)})
    return rows


def _versions() -> dict:
    info = {"python": platform.python_version(), "numpy": np.__version__}
    try:
        import ultralytics
        info["ultralytics"] = ultralytics.__version__
    except ImportError:
        pass
    return info


def main(argv: list[str] | None = None, runner=None) -> Path:
    ap = argparse.ArgumentParser(description="Experimentos do Fluxo360 com o MOT20")
    ap.add_argument("--config", default="configs/experimento_padrao.yaml")
    ap.add_argument("--sequences", nargs="+", help="ex.: MOT20-01 MOT20-02 (padrão: as do config)")
    ap.add_argument("--max-frames", type=int, help="limita os quadros por sequência (teste rápido)")
    ap.add_argument("--mode", choices=["track", "detect"], default="track")
    ap.add_argument("--name", help="nome do experimento (padrão: o do config)")
    ap.add_argument("--data-root", help="pasta do MOT20 (padrão: a do config)")
    ap.add_argument("--output", help="pasta de saída dos experimentos")
    ap.add_argument("--evaluate-only", type=Path, help="pasta de um experimento já executado")
    args = ap.parse_args(argv)

    cfg = load_config(args.config if Path(args.config).is_file() else None)
    dataset = MOT20Dataset(args.data_root or cfg["data"]["root"])

    if args.evaluate_only:
        exp_dir = args.evaluate_only
        info = json.loads((exp_dir / "run_info.json").read_text(encoding="utf-8")) if (exp_dir / "run_info.json").is_file() else {}
        mode = info.get("mode", args.mode)
        sequences = args.sequences or sorted(p.stem for p in (exp_dir / "predictions").glob("*.txt"))
        frames_used = {k: v["frames"] for k, v in info.get("sequences", {}).items()}
        rows = evaluate_folder(dataset, exp_dir / "predictions", sequences, cfg, mode, frames_used)
        save_metrics(rows, exp_dir)
        print(markdown_table(rows))
        return exp_dir

    sequences = args.sequences or cfg["data"]["sequences"]
    name = args.name or cfg["experiment"]["name"]
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    exp_dir = Path(args.output or cfg["data"]["output"]) / f"{stamp}_{name}_{args.mode}"
    pred_dir = exp_dir / "predictions"
    pred_dir.mkdir(parents=True, exist_ok=True)
    (exp_dir / "config.yaml").write_text(yaml.safe_dump(cfg, allow_unicode=True, sort_keys=False), encoding="utf-8")

    runner = runner or build_runner(cfg, args.mode)
    run_info = {"name": name, "mode": args.mode, "started": stamp, "versions": _versions(),
                "command": " ".join(sys.argv), "sequences": {}}
    for seq_name in sequences:
        seq = dataset.sequence(seq_name)
        problems = dataset.verify(seq_name) if args.max_frames is None else []
        for p in problems:
            print(f"  aviso: {p}")
        print(f"Processando {seq.name} ({seq.split}, {seq.description})")
        pred, stats = run_sequence(dataset, seq, runner, args.max_frames)
        write_mot_results(pred_dir / f"{seq.name}.txt", pred.frames, pred.ids, pred.boxes, pred.scores)
        run_info["sequences"][seq.name] = {"split": seq.split, **stats}
    (exp_dir / "run_info.json").write_text(json.dumps(run_info, indent=2, ensure_ascii=False), encoding="utf-8")

    frames_used = {k: v["frames"] for k, v in run_info["sequences"].items()}
    rows = evaluate_folder(dataset, pred_dir, sequences, cfg, args.mode, frames_used)
    if rows:
        save_metrics(rows, exp_dir)
        print(markdown_table(rows))
    print(f"Resultados em {exp_dir}")
    return exp_dir


if __name__ == "__main__":
    main()

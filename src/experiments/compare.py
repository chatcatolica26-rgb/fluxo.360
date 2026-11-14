"""Compara experimentos já executados (tabela ordenada por HOTA).

    python -m src.experiments.compare
    python -m src.experiments.compare --dir data/processed/mot20/experimentos --sequence MOT20-01
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from ..dataset.evaluation import markdown_table, save_metrics

COLUMNS = ["Experimento", "Modo", "Sequence", "HOTA", "DetA", "AssA", "MOTA", "IDF1", "Precision",
           "Recall", "IDSW", "Count_MAE", "ID_Count_Error", "FPS"]


def collect(exp_root: Path, sequence: str | None = None) -> list[dict]:
    rows = []
    for metrics_file in sorted(exp_root.glob("*/metrics.json")):
        exp_dir = metrics_file.parent
        info_file = exp_dir / "run_info.json"
        info = json.loads(info_file.read_text(encoding="utf-8")) if info_file.is_file() else {}
        data = json.loads(metrics_file.read_text(encoding="utf-8"))
        wanted = sequence or ("COMBINADO" if any(r["Sequence"] == "COMBINADO" for r in data) else None)
        for r in data:
            if wanted and r["Sequence"] != wanted:
                continue
            fps = info.get("sequences", {}).get(r["Sequence"], {}).get("fps")
            rows.append({"Experimento": exp_dir.name, "Modo": info.get("mode", ""), **r, "FPS": fps if fps else ""})
    rows.sort(key=lambda r: (r.get("HOTA", -1) if isinstance(r.get("HOTA"), float) else -1), reverse=True)
    return rows


def main(argv: list[str] | None = None) -> list[dict]:
    ap = argparse.ArgumentParser(description="Comparação de experimentos do Fluxo360")
    ap.add_argument("--dir", type=Path, default=Path("data/processed/mot20/experimentos"))
    ap.add_argument("--sequence", help="compara uma sequência específica (padrão: COMBINADO)")
    args = ap.parse_args(argv)
    rows = collect(args.dir, args.sequence)
    if not rows:
        print(f"Nenhum experimento com métricas em {args.dir}")
        return rows
    save_metrics(rows, args.dir, stem="comparativo")
    print(markdown_table(rows, COLUMNS))
    return rows


if __name__ == "__main__":
    main()

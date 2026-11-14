"""Acrescenta o rastro das pessoas aos mapas de calor de uma análise já feita.

    python tools/gerar_rastros.py                      # análise mais recente
    python tools/gerar_rastros.py data/processed/shopping/<pasta>
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.experiments.run_shopping import gerar_mapas_com_rastros  # noqa: E402

if __name__ == "__main__":
    if len(sys.argv) > 1:
        alvo = Path(sys.argv[1])
    else:
        execs = sorted(Path("data/processed/shopping").glob("*/run_info.json"))
        if not execs:
            raise SystemExit("Nenhuma análise encontrada em data/processed/shopping.")
        alvo = execs[-1].parent
    for p in gerar_mapas_com_rastros(alvo):
        print("Gerado:", p)

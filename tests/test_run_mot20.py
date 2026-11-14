"""Execução de ponta a ponta do script de experimentos com um rastreador falso."""
import json

import pytest

from src.experiments import compare, run_mot20
from tests.conftest import GroundTruthRunner


def run(mot20_root, tmp_path, *extra, runner=None):
    runner = runner or GroundTruthRunner(mot20_root / "train/MOT20-01/gt/gt.txt")
    return run_mot20.main(["--config", "nao_existe.yaml", "--data-root", str(mot20_root),
                           "--output", str(tmp_path / "exp"), *extra], runner=runner)


def test_experimento_completo_gera_previsoes_metricas_e_relatorio(mot20_root, tmp_path):
    exp = run(mot20_root, tmp_path, "--sequences", "MOT20-01", "MOT20-04", "--name", "perfeito")
    assert (exp / "predictions/MOT20-01.txt").is_file()
    assert (exp / "predictions/MOT20-04.txt").is_file()       # teste: só previsões
    rows = json.loads((exp / "metrics.json").read_text())
    assert [r["Sequence"] for r in rows] == ["MOT20-01"]      # sequência de teste não é avaliada
    r = rows[0]
    assert r["HOTA"] == pytest.approx(1.0) and r["MOTA"] == pytest.approx(1.0) and r["IDF1"] == pytest.approx(1.0)
    assert (exp / "metrics.csv").is_file() and (exp / "metrics.md").is_file()
    info = json.loads((exp / "run_info.json").read_text())
    assert info["sequences"]["MOT20-01"]["frames"] == 10


def test_max_frames_limita_a_avaliacao(mot20_root, tmp_path):
    exp = run(mot20_root, tmp_path, "--sequences", "MOT20-01", "--max-frames", "4")
    r = json.loads((exp / "metrics.json").read_text())[0]
    assert r["Frames"] == 4 and r["FN"] == 0


def test_reavaliacao_e_comparacao_entre_experimentos(mot20_root, tmp_path):
    good = run(mot20_root, tmp_path, "--sequences", "MOT20-01", "--name", "bom")

    class Ruim(GroundTruthRunner):          # perde todos os ids a cada quadro
        def update(self, image):
            return [(self.frame * 10 + i, *rest) for i, (_, *rest) in enumerate(super().update(image))]
    run(mot20_root, tmp_path, "--sequences", "MOT20-01", "--name", "ruim",
        runner=Ruim(mot20_root / "train/MOT20-01/gt/gt.txt"))

    (good / "metrics.json").unlink()
    run_mot20.main(["--config", "nao_existe.yaml", "--data-root", str(mot20_root), "--evaluate-only", str(good)])
    assert (good / "metrics.json").is_file()

    rows = compare.main(["--dir", str(tmp_path / "exp"), "--sequence", "MOT20-01"])
    assert [r["Experimento"].split("_")[2] for r in rows] == ["bom", "ruim"]
    assert rows[1]["IDSW"] > 0 and rows[1]["ID_Count_Error"] > 0
    assert (tmp_path / "exp" / "comparativo.csv").is_file()

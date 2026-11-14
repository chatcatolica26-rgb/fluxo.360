"""Leitura dos resultados REAIS gerados por ``python -m src.experiments.run_shopping``.

Cada execução fica em ``data/processed/shopping/<data>_<nome>/`` com ``run_info.json``,
mapas de calor, trajetórias e relatório. Aqui só lemos esses arquivos.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

PASTA_PADRAO = Path("data/processed/shopping")


@dataclass
class Execucao:
    pasta: Path
    info: dict

    @property
    def nome(self) -> str:
        return self.pasta.name

    def arquivo(self, nome: str) -> Path | None:
        p = self.pasta / nome
        return p if p.is_file() else None

    @property
    def rotulo(self) -> str:
        v = self.info.get("video", {})
        return f"{self.nome} · {Path(v.get('fonte', '')).name} · {self.info.get('duracao_analisada_s', 0):.0f} s"


def listar_execucoes(base: str | Path = PASTA_PADRAO) -> list[Execucao]:
    """Execuções com ``run_info.json``, da mais recente para a mais antiga."""
    base = Path(base)
    if not base.is_dir():
        return []
    saida = []
    for info_path in sorted(base.glob("*/run_info.json"), reverse=True):
        try:
            saida.append(Execucao(info_path.parent, json.loads(info_path.read_text(encoding="utf-8"))))
        except (OSError, json.JSONDecodeError):
            continue
    return saida

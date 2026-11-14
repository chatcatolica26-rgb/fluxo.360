"""Leitura dos resultados REAIS gerados por ``python -m src.experiments.run_shopping``.

Cada execução fica em ``data/processed/shopping/<data>_<nome>/`` com ``run_info.json``,
mapas de calor, trajetórias e relatório. Aqui só lemos esses arquivos.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

PASTA_PADRAO = Path("data/processed/shopping")
PASTA_DEMO = Path("data/demo")          # análise de demonstração que vai no repositório (e na versão web)


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


def listar_execucoes(base: str | Path | None = None) -> list[Execucao]:
    """Execuções com ``run_info.json``: as novas (data/processed/shopping) primeiro, depois a demonstração."""
    pastas = [Path(base)] if base else [PASTA_PADRAO, PASTA_DEMO]
    saida = []
    for pasta in pastas:
        if not pasta.is_dir():
            continue
        for info_path in sorted(pasta.glob("*/run_info.json"), reverse=True):
            try:
                saida.append(Execucao(info_path.parent, json.loads(info_path.read_text(encoding="utf-8"))))
            except (OSError, json.JSONDecodeError):
                continue
    return saida

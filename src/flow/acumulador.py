"""Acumulação temporal da presença de pessoas na planta.

Duas matrizes, na mesma grade (células de ``celula_m`` metros sobre a planta):

* ``permanencia`` — segundos de presença. Cada posição válida soma ``dt`` (tempo real
  que o quadro representa = passo / FPS). Assim, quem fica parado 10 s soma 10 s,
  com o vídeo a 24 FPS ou a 30 FPS: o resultado não depende da taxa de quadros.
* ``passagens`` — quantas pessoas diferentes passaram por cada célula. Uma pessoa só
  conta de novo numa célula depois de sair dela. Mede circulação, não tempo.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np


class AcumuladorFluxo:
    def __init__(self, largura_planta: int, altura_planta: int, px_por_metro: float, celula_m: float = 0.5):
        self.wp, self.hp = int(largura_planta), int(altura_planta)
        self.px_por_metro = float(px_por_metro)
        self.celula_m = float(celula_m)
        self.px_por_celula = self.px_por_metro * self.celula_m
        forma = (int(np.ceil(self.hp / self.px_por_celula)), int(np.ceil(self.wp / self.px_por_celula)))
        self.permanencia = np.zeros(forma, np.float64)   # segundos
        self.passagens = np.zeros(forma, np.float64)     # pessoas
        self._ultima_celula: dict[int, tuple[int, int]] = {}
        self.tempo_total_s = 0.0

    def celula(self, x_px: float, y_px: float) -> tuple[int, int] | None:
        r, c = int(y_px // self.px_por_celula), int(x_px // self.px_por_celula)
        if 0 <= r < self.permanencia.shape[0] and 0 <= c < self.permanencia.shape[1]:
            return r, c
        return None

    def adicionar(self, pessoa_id: int, x_px: float, y_px: float, dt: float) -> None:
        cel = self.celula(x_px, y_px)
        if cel is None:
            return
        self.permanencia[cel] += dt
        if self._ultima_celula.get(pessoa_id) != cel:      # entrou numa célula nova
            self.passagens[cel] += 1
            self._ultima_celula[pessoa_id] = cel

    def registrar_quadro(self, dt: float) -> None:
        """Chamar uma vez por quadro processado (soma o tempo analisado)."""
        self.tempo_total_s += dt

    def em_pixels_da_planta(self, matriz: np.ndarray) -> np.ndarray:
        """Expande a grade para o tamanho da planta (cada célula vira um bloco)."""
        k = int(round(self.px_por_celula))
        grande = np.kron(matriz, np.ones((k, k), matriz.dtype)) if k > 1 else matriz
        out = np.zeros((self.hp, self.wp), matriz.dtype)
        h, w = min(self.hp, grande.shape[0]), min(self.wp, grande.shape[1])
        out[:h, :w] = grande[:h, :w]
        return out

    def salvar(self, pasta: str | Path) -> dict[str, Path]:
        pasta = Path(pasta)
        pasta.mkdir(parents=True, exist_ok=True)
        meta = {"celula_m": self.celula_m, "px_por_metro": self.px_por_metro,
                "px_por_celula": self.px_por_celula, "tempo_total_s": self.tempo_total_s,
                "unidade_permanencia": "segundos", "unidade_passagens": "pessoas"}
        caminhos = {"permanencia": pasta / "matriz_permanencia_s.npy",
                    "passagens": pasta / "matriz_passagens.npy",
                    "dados": pasta / "matrizes.npz"}
        np.save(caminhos["permanencia"], self.permanencia)
        np.save(caminhos["passagens"], self.passagens)
        np.savez_compressed(caminhos["dados"], permanencia_s=self.permanencia, passagens=self.passagens,
                            **{k: np.array(v) for k, v in meta.items()})
        return caminhos

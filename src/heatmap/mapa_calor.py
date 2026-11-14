"""Acumula posições projetadas na planta e desenha o mapa de calor."""
from __future__ import annotations
import numpy as np
import cv2


class MapaCalor:
    def __init__(self, largura: int, altura: int, px_por_metro: float, celula_m: float = 0.5):
        # grade em células de `celula_m` metros (mais leve que acumular por pixel)
        self.k = px_por_metro * celula_m
        self.celula_m = celula_m
        self.W, self.H = largura, altura
        self.grade = np.zeros((int(np.ceil(altura / self.k)), int(np.ceil(largura / self.k))), np.float32)
        self.vistos: dict[tuple[str, int], tuple[int, int]] = {}

    def adicionar(self, pontos_planta: np.ndarray, ids: list[int] | None = None, camera: str = ""):
        """pontos em pixels da planta. Com ids de tracking, cada pessoa conta 1x por célula
        (evita que alguém parado gere calor proporcional ao FPS)."""
        for i, (x, y) in enumerate(np.asarray(pontos_planta).reshape(-1, 2)):
            cx, cy = int(x // self.k), int(y // self.k)
            if not (0 <= cy < self.grade.shape[0] and 0 <= cx < self.grade.shape[1]):
                continue
            if ids is not None:
                chave = (camera, int(ids[i]))
                if self.vistos.get(chave) == (cx, cy):
                    continue
                self.vistos[chave] = (cx, cy)
            self.grade[cy, cx] += 1

    def desenhar(self, fundo_bgr: np.ndarray, sigma_m: float = 1.5, alpha: float = 0.6,
                 limiar: float = 0.02) -> np.ndarray:
        g = cv2.GaussianBlur(self.grade, (0, 0), sigmaX=max(sigma_m / self.celula_m, 0.1))
        if g.max() > 0:
            g = g / g.max()
        g = cv2.resize(g, (self.W, self.H), interpolation=cv2.INTER_LINEAR)
        cor = cv2.applyColorMap((g * 255).astype(np.uint8), cv2.COLORMAP_JET)
        fundo = fundo_bgr.copy()
        # clareia as linhas da planta para o calor se destacar
        fundo = cv2.addWeighted(fundo, 0.55, np.full_like(fundo, 255), 0.45, 0)
        m = (g > limiar)[..., None]
        a = (alpha * np.clip(g / 0.3, 0, 1))[..., None]
        out = np.where(m, (fundo * (1 - a) + cor * a), fundo).astype(np.uint8)
        return out

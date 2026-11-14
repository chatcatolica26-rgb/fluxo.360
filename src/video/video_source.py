"""Leitura de vídeo real com OpenCV.

Independente do MOT20: aceita arquivo (mp4, avi...) ou endereço RTSP.
Cada quadro sai com seu índice e o instante em segundos, para que a
acumulação do mapa de calor use tempo real, e não número de quadros.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterator

import cv2
import numpy as np


@dataclass(frozen=True)
class VideoInfo:
    fonte: str
    largura: int
    altura: int
    fps: float
    total_quadros: int        # 0 quando desconhecido (ex.: RTSP)
    duracao_s: float          # 0 quando desconhecida

    def como_dict(self) -> dict:
        return asdict(self)


def _abrir(fonte: str) -> cv2.VideoCapture:
    if not str(fonte).lower().startswith(("rtsp://", "http://", "https://")) and not Path(fonte).is_file():
        raise FileNotFoundError(f"vídeo não encontrado: {fonte}")
    cap = cv2.VideoCapture(str(fonte))
    if not cap.isOpened():
        raise IOError(f"o OpenCV não conseguiu abrir o vídeo: {fonte}")
    return cap


class VideoSource:
    """Lê um trecho do vídeo, quadro a quadro.

    ``inicio_s`` / ``fim_s`` selecionam o trecho em segundos; ``passo`` pula quadros
    (passo=2 processa um a cada dois). ``fps_padrao`` só é usado se o arquivo não
    informar o FPS.
    """

    def __init__(self, fonte: str | Path, inicio_s: float = 0.0, fim_s: float | None = None,
                 passo: int = 1, fps_padrao: float = 25.0):
        if passo < 1:
            raise ValueError("passo deve ser >= 1")
        self.fonte = str(fonte)
        self.inicio_s, self.fim_s, self.passo = float(inicio_s), fim_s, int(passo)
        cap = _abrir(self.fonte)
        fps = cap.get(cv2.CAP_PROP_FPS)
        fps = float(fps) if fps and fps > 0 and np.isfinite(fps) else float(fps_padrao)
        n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        self.info = VideoInfo(self.fonte, int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
                              int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)), fps, max(n, 0),
                              round(n / fps, 3) if n > 0 else 0.0)
        cap.release()
        if self.fim_s is not None and self.fim_s <= self.inicio_s:
            raise ValueError("fim_s deve ser maior que inicio_s")

    @property
    def primeiro_quadro(self) -> int:
        return int(round(self.inicio_s * self.info.fps))

    @property
    def ultimo_quadro(self) -> int | None:
        """Índice (exclusivo) onde o trecho termina; None = até o fim do vídeo."""
        fim = None if self.fim_s is None else int(round(self.fim_s * self.info.fps))
        if self.info.total_quadros:
            fim = self.info.total_quadros if fim is None else min(fim, self.info.total_quadros)
        return fim

    @property
    def dt(self) -> float:
        """Tempo real representado por cada quadro processado (s)."""
        return self.passo / self.info.fps

    def __iter__(self) -> Iterator[tuple[int, float, np.ndarray]]:
        """Gera ``(indice_do_quadro, tempo_em_segundos, imagem_BGR)``."""
        cap = _abrir(self.fonte)
        try:
            i = self.primeiro_quadro
            if i > 0:
                cap.set(cv2.CAP_PROP_POS_FRAMES, i)
            fim = self.ultimo_quadro
            while fim is None or i < fim:
                ok, img = cap.read()
                if not ok:
                    break
                if (i - self.primeiro_quadro) % self.passo == 0:
                    yield i, i / self.info.fps, img
                i += 1
        finally:
            cap.release()


def ler_quadro(fonte: str | Path, tempo_s: float = 0.0) -> np.ndarray:
    """Um quadro do vídeo no instante pedido."""
    for _, _, img in VideoSource(fonte, inicio_s=tempo_s):
        return img
    raise IOError(f"não há quadro em {tempo_s}s de {fonte}")


def fundo_mediana(fonte: str | Path, amostras: int = 40) -> np.ndarray:
    """Imagem do fundo sem pessoas: mediana de quadros espalhados pelo vídeo.

    Funciona com câmera fixa e pessoas em movimento; é a melhor imagem para
    marcar os pontos de calibração no chão.
    """
    src = VideoSource(fonte)
    total = src.info.total_quadros
    if total <= 0:
        raise ValueError("vídeo sem contagem de quadros (RTSP?): use ler_quadro")
    alvo = set(np.linspace(0, total - 1, min(amostras, total)).astype(int).tolist())
    quadros = [img for i, _, img in src if i in alvo]
    return np.median(np.stack(quadros), axis=0).astype(np.uint8)

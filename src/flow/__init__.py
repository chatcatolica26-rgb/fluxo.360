"""Análise de fluxo em vídeo real: trajetórias na planta, acumulação e mapas de calor."""
from .acumulador import AcumuladorFluxo
from .trajetorias import Posicao, RegistroTrajetorias, ponto_dos_pes

__all__ = ["AcumuladorFluxo", "Posicao", "RegistroTrajetorias", "ponto_dos_pes"]

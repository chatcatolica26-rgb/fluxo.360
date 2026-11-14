"""Leitura de vídeos reais (arquivos mp4/avi ou câmeras RTSP)."""
from .video_source import VideoInfo, VideoSource, fundo_mediana, ler_quadro

__all__ = ["VideoInfo", "VideoSource", "fundo_mediana", "ler_quadro"]

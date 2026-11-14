"""Análise do vídeo real: leitura, pés, projeção, acumulação temporal e execução completa.

Usa vídeo e planta sintéticos e um rastreador falso: não precisa do YOLO nem do vídeo real.
"""
from __future__ import annotations

import json

import cv2
import numpy as np
import pytest
import yaml

from src.experiments import run_shopping
from src.flow import AcumuladorFluxo, RegistroTrajetorias, ponto_dos_pes
from src.flow.trajetorias import FORA_DA_MASCARA, TOCA_BORDA
from src.projection.homografia import CameraPlanta
from src.tracking import Track
from src.video import VideoSource, fundo_mediana

W, H, FPS, N = 160, 120, 10, 30


@pytest.fixture
def video(tmp_path):
    path = tmp_path / "video.avi"
    wr = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"MJPG"), FPS, (W, H))
    for i in range(N):
        img = np.full((H, W, 3), 120, np.uint8)
        cv2.rectangle(img, (10 + 4 * i, 40), (20 + 4 * i, 80), (0, 0, 255), -1)   # "pessoa" andando
        wr.write(img)
    wr.release()
    return path


def _camera(mascara=None, ppm=10.0):
    return CameraPlanta("cam", "teste", np.eye(3), ppm, mascara)


# ------------------------------------------------------------------ vídeo
def test_video_metadados_e_trecho(video):
    src = VideoSource(video)
    assert (src.info.largura, src.info.altura, src.info.total_quadros) == (W, H, N)
    assert src.info.fps == pytest.approx(FPS)
    assert src.info.duracao_s == pytest.approx(3.0)
    trecho = list(VideoSource(video, inicio_s=1.0, fim_s=2.0))
    assert [q for q, _, _ in trecho] == list(range(10, 20))
    assert trecho[0][1] == pytest.approx(1.0)


def test_video_passo_e_dt(video):
    src = VideoSource(video, passo=3)
    assert len(list(src)) == 10
    assert src.dt == pytest.approx(0.3)


def test_fundo_mediana_remove_objeto_em_movimento(video):
    fundo = fundo_mediana(video, amostras=30)
    assert np.abs(fundo.astype(int) - 120).mean() < 6


def test_video_inexistente(tmp_path):
    with pytest.raises(FileNotFoundError):
        VideoSource(tmp_path / "nao_existe.mp4")


# --------------------------------------------------------- pés e projeção
def test_ponto_dos_pes_e_centro_da_base():
    assert ponto_dos_pes(10, 20, 30, 100) == (20, 100)


def test_registro_valida_e_descarta():
    mascara = np.zeros((200, 200), np.uint8)
    mascara[:, :100] = 255
    reg = RegistroTrajetorias(_camera(mascara), W, H, 200, 200)
    tracks = [Track(1, 10, 10, 20, 50, 0.9),      # pés em (20, 60): dentro
              Track(2, 110, 10, 20, 50, 0.9),     # pés em (120, 60): fora da máscara
              Track(3, 10, 70, 20, 50, 0.9)]      # pés em y=120 = borda inferior do quadro
    ps = reg.adicionar(5, 0.5, tracks)
    assert [p.valida for p in ps] == [True, False, False]
    assert ps[1].motivo_descarte == FORA_DA_MASCARA and ps[2].motivo_descarte == TOCA_BORDA
    assert (ps[0].planta_x, ps[0].planta_y) == (20, 60)
    assert ps[0].planta_x_m == pytest.approx(2.0)
    r = reg.resumo(min_pontos_trajetoria=1)
    assert r["deteccoes_total"] == 3 and r["deteccoes_validas"] == 1
    assert r["ids_rastreados"] == 3 and r["pessoas_unicas_na_area"] == 1


def test_homografia_projeta_pontos_de_calibracao():
    src = np.float32([[0, 0], [100, 0], [100, 50], [0, 50]])
    dst = np.float32([[200, 300], [400, 300], [400, 400], [200, 400]])
    cam = CameraPlanta("c", "p", cv2.getPerspectiveTransform(src, dst), 10.0)
    assert np.allclose(cam.projetar(src), dst, atol=1e-6)


# ---------------------------------------------------- acumulação temporal
@pytest.mark.parametrize("fps", [10, 24, 30])
def test_permanencia_nao_depende_do_fps(fps):
    acc = AcumuladorFluxo(100, 100, px_por_metro=10, celula_m=0.5)
    for _ in range(2 * fps):                        # parada 2 s no mesmo lugar
        acc.adicionar(7, 12, 12, 1 / fps)
    assert acc.permanencia.sum() == pytest.approx(2.0)
    assert acc.passagens.sum() == 1                 # uma pessoa, uma passagem


def test_passagens_contam_pessoas_diferentes():
    acc = AcumuladorFluxo(100, 100, px_por_metro=10, celula_m=1.0)
    for pid in (1, 2, 3):
        for _ in range(5):
            acc.adicionar(pid, 15, 15, 0.1)
    acc.adicionar(1, 55, 15, 0.1)                   # pessoa 1 muda de célula
    acc.adicionar(1, 15, 15, 0.1)                   # e volta: nova passagem
    assert acc.passagens[1, 1] == 4
    assert acc.permanencia[1, 1] == pytest.approx(1.6)


def test_matriz_em_pixels_da_planta():
    acc = AcumuladorFluxo(100, 60, px_por_metro=10, celula_m=1.0)
    acc.adicionar(1, 25, 35, 1.0)
    px = acc.em_pixels_da_planta(acc.permanencia)
    assert px.shape == (60, 100)
    assert px[35, 25] == 1.0 and px[5, 5] == 0.0


# ------------------------------------------------------ execução completa
class _FakeTracker:
    """Duas pessoas: uma atravessa o quadro, outra fica parada."""

    def __init__(self):
        self.i = 0

    def reset(self):
        self.i = 0

    def update(self, img):
        self.i += 1
        return [Track(1, 10 + 4 * self.i, 60, 12, 40, 0.9), Track(2, 120, 30, 12, 40, 0.8)]


def test_run_shopping_completo(tmp_path, video):
    planta = np.full((200, 300, 3), 255, np.uint8)
    cv2.imwrite(str(tmp_path / "planta.png"), planta)
    mascara = np.full((200, 300), 255, np.uint8)
    cv2.imwrite(str(tmp_path / "mascara.png"), mascara)
    (tmp_path / "planta.yaml").write_text(yaml.safe_dump(
        {"pisos": {"teste": {"imagem": str(tmp_path / "planta.png"), "px_por_metro": 10}}}), encoding="utf-8")
    (tmp_path / "cam.yaml").write_text(yaml.safe_dump(
        {"camera_id": "cam", "piso": "teste", "frame_tamanho": [W, H], "H": np.eye(3).tolist(),
         "mascara": str(tmp_path / "mascara.png"), "erro_medio_m": 0.1, "erro_max_m": 0.2,
         "pontos": [{"planta_px": [10, 10]}, {"planta_px": [150, 110]}]}), encoding="utf-8")
    (tmp_path / "tracker.yaml").write_text("tracker_type: bytetrack\ntrack_buffer: 48\n", encoding="utf-8")
    cfg = {"experimento": {"nome": "teste"}, "video": {"arquivo": str(video)},
           "camera": {"calibracao": str(tmp_path / "cam.yaml")}, "planta_yaml": str(tmp_path / "planta.yaml"),
           "tracker": {"config": str(tmp_path / "tracker.yaml")}, "validacao": {"min_pontos_trajetoria": 5},
           "saida": {"pasta": str(tmp_path / "saida")}}
    (tmp_path / "cfg.yaml").write_text(yaml.safe_dump(cfg), encoding="utf-8")

    pasta = run_shopping.main(["--config", str(tmp_path / "cfg.yaml")], runner=_FakeTracker())

    for nome in ("video_deteccoes.mp4", "video_trajetorias_planta.mp4", "planta_calibrada.png",
                 "mapa_permanencia_sobreposto.png", "mapa_permanencia_isolado.png",
                 "mapa_circulacao_sobreposto.png", "mapa_circulacao_isolado.png", "matriz_permanencia_s.npy",
                 "matriz_passagens.npy", "trajetorias.csv", "rastreamento_mot.txt", "relatorio.md",
                 "run_info.json", "config.yaml", "processamento.log"):
        assert (pasta / nome).is_file(), nome
    info = json.loads((pasta / "run_info.json").read_text(encoding="utf-8"))
    assert info["quadros_processados"] == N
    assert info["contagens"]["pessoas_unicas_na_area"] == 2
    assert info["contagens"]["deteccoes_total"] == 2 * N
    # 2 pessoas x 3 s de vídeo = 6 s de permanência somada
    assert np.load(pasta / "matriz_permanencia_s.npy").sum() == pytest.approx(6.0)
    # a pessoa parada concentra mais tempo que qualquer célula do caminho da outra
    perm = np.load(pasta / "matriz_permanencia_s.npy")
    assert perm.max() == pytest.approx(3.0)


def test_run_shopping_sem_calibracao(tmp_path, video):
    with pytest.raises(SystemExit, match="Calibração não encontrada"):
        run_shopping.main(["--video", str(video), "--camera", str(tmp_path / "nao.yaml")], runner=_FakeTracker())

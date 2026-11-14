import pytest

from src.dataset import (PRIORITY_SEQUENCES, SEQUENCES, TEST_SEQUENCES, TRAIN_SEQUENCES,
                         DatasetNotFoundError, MOT20Dataset)
from tests.conftest import HEIGHT, N_FRAMES, WIDTH


def test_catalogo_das_oito_sequencias():
    assert len(SEQUENCES) == 8
    assert TRAIN_SEQUENCES == ["MOT20-01", "MOT20-02", "MOT20-03", "MOT20-05"]
    assert TEST_SEQUENCES == ["MOT20-04", "MOT20-06", "MOT20-07", "MOT20-08"]
    assert PRIORITY_SEQUENCES == ["MOT20-01", "MOT20-02"]


def test_localiza_sequencias_e_le_seqinfo(mot20_root):
    ds = MOT20Dataset(mot20_root)
    assert ds.available_sequences() == ["MOT20-01", "MOT20-04"]
    assert ds.available_sequences("train") == ["MOT20-01"]
    seq = ds.sequence("MOT20-01")
    assert (seq.split, seq.seq_length, seq.width, seq.height, seq.frame_rate) == ("train", N_FRAMES, WIDTH, HEIGHT, 25.0)
    assert seq.has_ground_truth
    assert seq.frame_path(7).name == "000007.jpg"
    assert "estação" in seq.description
    assert not ds.sequence("MOT20-04").has_ground_truth


def test_aceita_pasta_mot20_aninhada(tmp_path, mot20_root):
    nested = tmp_path / "outra"
    nested.mkdir()
    mot20_root.rename(nested / "MOT20")
    assert MOT20Dataset(nested).available_sequences("train") == ["MOT20-01"]


def test_erros_de_base_e_sequencia_ausentes(tmp_path, mot20_root):
    with pytest.raises(DatasetNotFoundError):
        MOT20Dataset(tmp_path / "nao_existe")
    with pytest.raises(DatasetNotFoundError):
        MOT20Dataset(mot20_root).sequence("MOT20-02")


def test_le_quadros_em_ordem(mot20_root):
    ds = MOT20Dataset(mot20_root)
    frames = list(ds.iter_frames("MOT20-01", start=3, end=6))
    assert [f for f, _ in frames] == [3, 4, 5, 6]
    assert frames[0][1].shape == (HEIGHT, WIDTH, 3)
    assert abs(int(frames[0][1].mean()) - 30) <= 2   # imagem do quadro 3 tem valor 30


def test_verificacao_aponta_imagem_faltando(mot20_root):
    ds = MOT20Dataset(mot20_root)
    assert ds.verify("MOT20-01") == []
    (mot20_root / "train" / "MOT20-01" / "img1" / "000004.jpg").unlink()
    assert any("9 imagens" in p for p in ds.verify("MOT20-01"))
    with pytest.raises(DatasetNotFoundError):
        ds.read_frame("MOT20-01", 4)


def test_exporta_video(tmp_path, mot20_root):
    import cv2
    out = MOT20Dataset(mot20_root).export_video("MOT20-01", tmp_path / "v.mp4")
    cap = cv2.VideoCapture(str(out))
    if not cap.isOpened():
        pytest.skip("OpenCV sem codec de vídeo neste ambiente")
    assert int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) == N_FRAMES

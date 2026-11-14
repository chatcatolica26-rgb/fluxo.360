import numpy as np
import pytest

from src.dataset import (AnnotationFormatError, load_ground_truth, read_mot_file, write_mot_results,
                         xywh_to_xyxy, xyxy_to_xywh)


def test_le_gt_com_todas_as_colunas(mot20_root):
    gt = read_mot_file(mot20_root / "train/MOT20-01/gt/gt.txt")
    assert len(gt) == 10 * 4 + 5
    first = gt.subset(np.arange(len(gt)) == 0)
    assert first.frames[0] == 1 and first.ids[0] == 1
    np.testing.assert_allclose(first.boxes[0], [3, 5, 8, 16])
    assert first.classes[0] == 1 and first.visibility[0] == 1.0


def test_separa_pedestres_distratores_e_outras_classes(mot20_root):
    gt = load_ground_truth(mot20_root / "train/MOT20-01/gt/gt.txt")
    assert set(gt.pedestrians.unique_ids()) == {1, 2, 3}
    assert set(gt.distractors.unique_ids()) == {10}
    assert set(gt.ignored.unique_ids()) == {11}
    # visibilidade mínima: o pedestre 3 (0,1) vira distrator
    gt2 = load_ground_truth(mot20_root / "train/MOT20-01/gt/gt.txt", min_visibility=0.5)
    assert set(gt2.pedestrians.unique_ids()) == {1, 2}
    assert set(gt2.distractors.unique_ids()) == {3, 10}


def test_le_deteccoes_publicas(mot20_root):
    det = read_mot_file(mot20_root / "train/MOT20-01/det/det.txt")
    assert len(det) == 10 and (det.ids == -1).all()
    assert det.scores[0] == pytest.approx(0.9)


def test_linha_malformada_indica_numero(tmp_path):
    p = tmp_path / "r.txt"
    p.write_text("1,1,0,0,10,10,1\n2,1,0,0\n", encoding="utf-8")
    with pytest.raises(AnnotationFormatError, match=":2:"):
        read_mot_file(p, kind="result")
    p.write_text("1,1,abc,0,10,10,1\n", encoding="utf-8")
    with pytest.raises(AnnotationFormatError, match="não numérico"):
        read_mot_file(p, kind="result")
    p.write_text("0,1,0,0,10,10,1\n", encoding="utf-8")
    with pytest.raises(AnnotationFormatError, match="quadro"):
        read_mot_file(p, kind="result")


def test_escrita_e_leitura_ida_e_volta(tmp_path):
    path = write_mot_results(tmp_path / "out" / "MOT20-01.txt", [2, 1, 1], [5, 7, 3],
                             [[1, 2, 3, 4], [5.5, 6, 7, 8], [0, 0, 1, 1]], [0.5, 0.6, 0.7])
    lines = path.read_text().splitlines()
    assert lines[0].startswith("1,3,") and lines[-1].endswith(",-1,-1,-1")
    back = read_mot_file(path, kind="result")
    np.testing.assert_array_equal(back.frames, [1, 1, 2])
    np.testing.assert_array_equal(back.ids, [3, 7, 5])
    np.testing.assert_allclose(back.boxes[1], [5.5, 6, 7, 8])


def test_conversao_e_interpretacao_das_coordenadas(mot20_root):
    xywh = np.array([[10, 20, 30, 40]])
    np.testing.assert_allclose(xywh_to_xyxy(xywh), [[10, 20, 40, 60]])
    np.testing.assert_allclose(xyxy_to_xywh(xywh_to_xyxy(xywh)), xywh)
    gt = load_ground_truth(mot20_root / "train/MOT20-01/gt/gt.txt").pedestrians
    f1 = gt.in_frame(1)
    np.testing.assert_allclose(f1.centers()[f1.ids == 1][0], [3 + 4, 5 + 8])
    clipped = gt.in_frame(10).clipped(width=40, height=48)
    assert (clipped.boxes_xyxy()[:, 2] <= 40).all()
    assert gt.counts_per_frame([1, 6, 99]).tolist() == [3, 2, 0]

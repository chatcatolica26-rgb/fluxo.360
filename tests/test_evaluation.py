"""Métricas com valores calculados à mão em cenários pequenos."""
import numpy as np
import pytest

from src.dataset import (annotations_from_records, clear_metrics, detection_metrics, evaluate_sequence,
                         hota_metrics, identity_metrics, iou_matrix, load_ground_truth,
                         remove_distractor_matches)


def track(id_, frames, box=(0, 0, 10, 10), score=1.0):
    return [(f, id_, *box, score) for f in frames]


def ann(records):
    return annotations_from_records(records)


def test_iou():
    a = np.array([[0, 0, 10, 10]])
    b = np.array([[0, 0, 10, 10], [5, 0, 10, 10], [20, 20, 5, 5], [0, 0, 10, 6.2]])
    np.testing.assert_allclose(iou_matrix(a, b), [[1.0, 50 / 150, 0.0, 0.62]])
    assert iou_matrix(np.zeros((0, 4)), b).shape == (0, 4)


def test_previsao_perfeita_tem_todas_as_metricas_maximas():
    gt = ann(track(1, range(1, 11)) + track(2, range(1, 11), (30, 0, 10, 10)))
    pred = ann(track(7, range(1, 11)) + track(8, range(1, 11), (30, 0, 10, 10)))
    r = evaluate_sequence(gt, pred)
    for k in ("MOTA", "IDF1", "HOTA", "DetA", "AssA", "Precision", "Recall", "MOTP"):
        assert r[k] == pytest.approx(1.0), k
    assert (r["IDSW"], r["FP"], r["FN"], r["Frag"], r["MT"], r["ML"]) == (0, 0, 0, 0, 2, 0)
    assert r["Count_MAE"] == 0 and r["ID_Count_Error"] == 0


def test_troca_de_identidade_no_meio_da_trajetoria():
    gt = ann(track(1, range(1, 11)))
    pred = ann(track(5, range(1, 6)) + track(6, range(6, 11)))
    c = clear_metrics(gt, pred)
    assert c["IDSW"] == 1
    assert c["MOTA"] == pytest.approx((10 - 0 - 1) / 10)
    i = identity_metrics(gt, pred)
    assert (i["IDTP"], i["IDFP"], i["IDFN"]) == (5, 5, 5)
    assert i["IDF1"] == pytest.approx(0.5)
    h = hota_metrics(gt, pred)
    assert h["DetA"] == pytest.approx(1.0)
    assert h["AssA"] == pytest.approx(0.5)          # cada metade: 5 / (10 + 5 - 5)
    assert h["HOTA"] == pytest.approx(np.sqrt(0.5))


def test_falsos_positivos_e_negativos():
    gt = ann(track(1, range(1, 11)) + track(2, range(1, 11), (30, 0, 10, 10)))
    pred = ann(track(1, range(1, 11)) + track(3, range(1, 5), (60, 60, 10, 10)))   # perde o 2, inventa o 3
    d = detection_metrics(gt, pred)
    assert (d["TP"], d["FP"], d["FN"]) == (10, 4, 10)
    assert d["Precision"] == pytest.approx(10 / 14)
    assert d["Recall"] == pytest.approx(0.5)
    c = clear_metrics(gt, pred)
    assert c["MOTA"] == pytest.approx((10 - 4 - 0) / 20)
    assert (c["MT"], c["ML"]) == (1, 1)


def test_limiar_de_iou_e_hota_com_localizacao_parcial():
    gt = ann(track(1, range(1, 11)))
    pred = ann(track(1, range(1, 11), (0, 0, 10, 6.2)))       # IoU = 0,62 em todos os quadros
    assert detection_metrics(gt, pred, 0.5)["TP"] == 10
    assert detection_metrics(gt, pred, 0.7)["TP"] == 0
    h = hota_metrics(gt, pred)
    assert h["DetA"] == pytest.approx(12 / 19)                # limiares 0,05 a 0,60
    assert h["HOTA"] == pytest.approx(12 / 19)
    # como no TrackEval, limiares sem nenhum acerto contam LocA = 1
    assert h["LocA"] == pytest.approx((12 * 0.62 + 7 * 1.0) / 19)


def test_fragmentacao_quando_o_rastreamento_e_perdido_e_retomado():
    gt = ann(track(1, range(1, 11)))
    # o id 4 some nos quadros 4 a 6 e volta; outra pessoa, longe, segue sendo prevista
    pred = ann(track(4, [1, 2, 3, 7, 8, 9, 10]) + track(9, range(1, 11), (50, 50, 10, 10)))
    c = clear_metrics(gt, pred)
    assert (c["Frag"], c["IDSW"], c["CLR_FN"], c["CLR_FP"]) == (1, 0, 3, 10)


def test_sem_previsoes():
    gt = ann(track(1, range(1, 4)))
    r = evaluate_sequence(gt, ann([]))
    assert r["Recall"] == 0 and r["HOTA"] == 0 and r["MOTA"] == 0 and r["FN"] == 3


def test_previsoes_sobre_distratores_sao_ignoradas(mot20_root):
    gt = load_ground_truth(mot20_root / "train/MOT20-01/gt/gt.txt")
    peds = [(int(f), int(i), *map(float, b), 1.0) for f, i, b in zip(gt.pedestrians.frames, gt.pedestrians.ids, gt.pedestrians.boxes)]
    on_distractor = [(f, 99, 50, 2, 6, 12, 1.0) for f in range(1, 11)]
    on_nothing = [(1, 98, 60, 40, 3, 3, 1.0)]
    pred = ann(peds + on_distractor + on_nothing)
    filtered = remove_distractor_matches(pred, gt)
    assert 99 not in filtered.ids and 98 in filtered.ids
    r = evaluate_sequence(gt, pred, seq_length=10)
    assert r["FP"] == 1 and r["FN"] == 0 and r["IDSW"] == 0

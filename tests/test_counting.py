import pytest

from src.dataset import annotations_from_records, counting_metrics


def track(id_, frames, x=0):
    return [(f, id_, x, 0, 10, 10, 1.0) for f in frames]


def test_pessoa_contada_duas_vezes_por_perda_de_rastreamento():
    gt = annotations_from_records(track(1, range(1, 11)))
    pred = annotations_from_records(track(1, range(1, 5)) + track(2, range(6, 11)))
    r = counting_metrics(gt, pred)
    assert (r["GT_IDs"], r["Pred_IDs"], r["ID_Count_Error"]) == (1, 2, 1)
    assert r["ID_Ratio"] == pytest.approx(2.0)
    assert r["Count_MAE"] == pytest.approx(0.1)        # só o quadro 5 ficou sem pessoa
    assert r["Count_Bias"] == pytest.approx(-0.1)


def test_erro_de_contagem_por_quadro():
    gt = annotations_from_records(track(1, range(1, 5)) + track(2, range(1, 5), 20))
    pred = annotations_from_records(track(1, range(1, 5)) + track(2, range(1, 5), 20) + track(3, [1, 2], 40))
    r = counting_metrics(gt, pred, frames=[1, 2, 3, 4, 5])
    assert r["Frames"] == 5
    assert r["Count_MAE"] == pytest.approx(2 / 5)
    assert r["Count_Bias"] == pytest.approx(2 / 5)
    assert r["Count_MaxAbs"] == 1
    assert r["Count_RMSE"] == pytest.approx((2 / 5) ** 0.5)
    assert (r["GT_People_Total"], r["Pred_People_Total"]) == (8, 10)

"""Detector e rastreador testados com um modelo falso (sem baixar o YOLO)."""
import numpy as np

from src.detection import YoloPersonDetector
from src.tracking import ByteTrackPersonTracker


class _T:
    def __init__(self, a):
        self.a = np.asarray(a, float)

    def cpu(self):
        return self

    def numpy(self):
        return self.a


class _Boxes:
    def __init__(self, xyxy, conf, ids=None):
        self.xyxy, self.conf = _T(xyxy), _T(conf)
        self.id = None if ids is None else _T(ids)

    def __len__(self):
        return len(self.xyxy.a)


class _Result:
    def __init__(self, boxes):
        self.boxes = boxes


class FakeYolo:
    def __init__(self):
        self.calls = []

    def predict(self, image, **kw):
        self.calls.append(kw)
        return [_Result(_Boxes([[10, 20, 40, 80]], [0.9]))]

    def track(self, image, **kw):
        self.calls.append(kw)
        return [_Result(_Boxes([[0, 0, 10, 30], [5, 5, 15, 25]], [0.8, 0.4], [3, 7]))]


def test_detector_converte_para_xywh_e_filtra_pessoas():
    model = FakeYolo()
    dets = YoloPersonDetector(model_obj=model, conf=0.3).detect(np.zeros((8, 8, 3), np.uint8))
    assert len(dets) == 1
    d = dets[0]
    assert (d.x, d.y, d.w, d.h, d.score) == (10, 20, 30, 60, 0.9)
    assert model.calls[0]["classes"] == [0] and model.calls[0]["conf"] == 0.3


def test_rastreador_mantem_persistencia_e_devolve_ids():
    created = []

    def factory(name):
        created.append(name)
        return FakeYolo()

    tr = ByteTrackPersonTracker(model="m.pt", tracker_config="configs/bytetrack_mot20.yaml", model_factory=factory)
    tracks = tr.update(np.zeros((8, 8, 3), np.uint8))
    assert [t.track_id for t in tracks] == [3, 7]
    assert (tracks[1].w, tracks[1].h) == (10, 20)
    kw = tr.model.calls[0]
    assert kw["persist"] is True and kw["tracker"] == "configs/bytetrack_mot20.yaml"
    tr.reset()
    assert created == ["m.pt", "m.pt"]     # nova sequência = modelo e ids novos

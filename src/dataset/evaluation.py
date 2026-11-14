"""Comparação das previsões do Fluxo360 com o Ground Truth do MOT20.

Métricas implementadas (mesmas definições do avaliador oficial TrackEval):

* **Detecção**: Precision, Recall, F1, falsos positivos e falsos negativos.
* **CLEAR MOT**: MOTA, MOTP, trocas de identidade (IDSW), fragmentações,
  trajetórias majoritariamente rastreadas (MT), parcialmente (PT) e perdidas (ML).
* **Identidade**: IDF1, IDP, IDR.
* **HOTA**: HOTA, DetA, AssA e LocA (média sobre limiares de IoU de 0,05 a 0,95).
* **Contagem**: erro absoluto médio de pessoas por quadro, viés, RMSE e
  diferença entre a quantidade de identidades contadas e a de referência
  (indicador de duplicação de pessoas).

O módulo só recebe caixas (``MOTAnnotations``); não depende de YOLO,
ByteTrack nem de qualquer outro algoritmo, então serve para outras bases.
"""
from __future__ import annotations

import csv
import json
import math
from pathlib import Path
from typing import Iterable, Sequence

import numpy as np
from scipy.optimize import linear_sum_assignment

from .mot20_annotations import GroundTruth, MOTAnnotations

EPS = np.finfo(float).eps
HOTA_ALPHAS = np.arange(0.05, 0.99, 0.05)


# ---------------------------------------------------------------- geometria
def iou_matrix(boxes_a: np.ndarray, boxes_b: np.ndarray) -> np.ndarray:
    """IoU entre todas as caixas de ``a`` e ``b`` (ambas em ``x, y, w, h``)."""
    a = np.asarray(boxes_a, float).reshape(-1, 4)
    b = np.asarray(boxes_b, float).reshape(-1, 4)
    if len(a) == 0 or len(b) == 0:
        return np.zeros((len(a), len(b)))
    ax1, ay1, ax2, ay2 = a[:, 0], a[:, 1], a[:, 0] + a[:, 2], a[:, 1] + a[:, 3]
    bx1, by1, bx2, by2 = b[:, 0], b[:, 1], b[:, 0] + b[:, 2], b[:, 1] + b[:, 3]
    iw = np.clip(np.minimum(ax2[:, None], bx2[None]) - np.maximum(ax1[:, None], bx1[None]), 0, None)
    ih = np.clip(np.minimum(ay2[:, None], by2[None]) - np.maximum(ay1[:, None], by1[None]), 0, None)
    inter = iw * ih
    union = (a[:, 2] * a[:, 3])[:, None] + (b[:, 2] * b[:, 3])[None] - inter
    return np.where(union > 0, inter / np.maximum(union, EPS), 0.0)


def _match(similarity: np.ndarray, threshold: float) -> tuple[np.ndarray, np.ndarray]:
    """Associação ótima (Húngaro) mantendo só pares com similaridade >= limiar."""
    if similarity.size == 0:
        return np.zeros(0, int), np.zeros(0, int)
    score = np.where(similarity >= threshold - EPS, similarity, 0.0)
    rows, cols = linear_sum_assignment(-score)
    keep = score[rows, cols] > EPS
    return rows[keep], cols[keep]


# ----------------------------------------------------------- pré-processamento
def remove_distractor_matches(pred: MOTAnnotations, gt: GroundTruth,
                              iou_threshold: float = 0.5) -> MOTAnnotations:
    """Descarta previsões que correspondem a distratores do Ground Truth.

    Em cada quadro, as previsões são associadas a todas as caixas de referência
    (pedestres + distratores). As que ficam com um distrator são removidas,
    como faz o avaliador oficial: não contam como acerto nem como erro.
    """
    if len(pred) == 0 or len(gt.distractors) == 0:
        return pred
    keep = np.ones(len(pred), bool)
    pred_idx_by_frame = _indices_by_frame(pred.frames)
    ped_by_frame = _indices_by_frame(gt.pedestrians.frames)
    dis_by_frame = _indices_by_frame(gt.distractors.frames)
    for frame, d_idx in dis_by_frame.items():
        p_idx = pred_idx_by_frame.get(frame)
        if p_idx is None:
            continue
        g_idx = ped_by_frame.get(frame, np.zeros(0, int))
        ref = np.vstack([gt.pedestrians.boxes[g_idx], gt.distractors.boxes[d_idx]])
        rows, cols = _match(iou_matrix(ref, pred.boxes[p_idx]), iou_threshold)
        is_distractor = rows >= len(g_idx)
        keep[p_idx[cols[is_distractor]]] = False
    return pred.subset(keep)


def _indices_by_frame(frames: np.ndarray) -> dict[int, np.ndarray]:
    out: dict[int, list[int]] = {}
    for i, f in enumerate(frames.tolist()):
        out.setdefault(f, []).append(i)
    return {k: np.asarray(v, int) for k, v in out.items()}


def _prepare(gt: MOTAnnotations, pred: MOTAnnotations, frames: Iterable[int] | None = None):
    """Lista por quadro: (ids GT, ids previsão, matriz IoU), com ids reindexados 0..n-1."""
    gt_ids, gt_inv = np.unique(gt.ids, return_inverse=True)
    pr_ids, pr_inv = np.unique(pred.ids, return_inverse=True)
    if frames is None:
        frames = np.union1d(gt.frames, pred.frames)
    gt_by_frame = _indices_by_frame(gt.frames)
    pr_by_frame = _indices_by_frame(pred.frames)
    data = []
    empty = np.zeros(0, int)
    for f in frames:
        gi = gt_by_frame.get(int(f), empty)
        pi = pr_by_frame.get(int(f), empty)
        data.append((gt_inv[gi], pr_inv[pi], iou_matrix(gt.boxes[gi], pred.boxes[pi])))
    return data, len(gt_ids), len(pr_ids)


# ------------------------------------------------------------------- métricas
def detection_metrics(gt: MOTAnnotations, pred: MOTAnnotations, iou_threshold: float = 0.5) -> dict:
    """Precision/Recall de detecção quadro a quadro, sem considerar identidades."""
    tp = fp = fn = 0
    for gt_ids, pr_ids, sim in _prepare(gt, pred)[0]:
        rows, _ = _match(sim, iou_threshold)
        tp += len(rows)
        fp += len(pr_ids) - len(rows)
        fn += len(gt_ids) - len(rows)
    precision = tp / max(1, tp + fp)
    recall = tp / max(1, tp + fn)
    f1 = 2 * precision * recall / max(EPS, precision + recall)
    return {"TP": tp, "FP": fp, "FN": fn, "Precision": precision, "Recall": recall, "F1": f1}


def clear_metrics(gt: MOTAnnotations, pred: MOTAnnotations, iou_threshold: float = 0.5) -> dict:
    """MOTA, MOTP, IDSW, Frag, MT/PT/ML (CLEAR MOT)."""
    data, n_gt, n_pr = _prepare(gt, pred)
    tp = fp = fn = idsw = 0
    motp_sum = 0.0
    gt_count = np.zeros(n_gt)
    gt_matched = np.zeros(n_gt)
    gt_frag = np.zeros(n_gt)
    prev_tracker = np.full(n_gt, np.nan)        # último id associado (com lacunas)
    prev_step_tracker = np.full(n_gt, np.nan)   # id associado no quadro anterior
    for gt_ids, pr_ids, sim in data:
        # quadros sem referência ou sem previsão não alteram o histórico de
        # associações (mesmo comportamento do TrackEval)
        if len(gt_ids) == 0:
            fp += len(pr_ids)
            continue
        gt_count[gt_ids] += 1
        if len(pr_ids) == 0:
            fn += len(gt_ids)
            continue
        # prioriza manter a associação do quadro anterior (regra do CLEAR MOT)
        continuing = pr_ids[None, :] == prev_step_tracker[gt_ids][:, None]
        score = 1000.0 * continuing + sim
        score[sim < iou_threshold - EPS] = 0
        rows, cols = linear_sum_assignment(-score)
        ok = score[rows, cols] > EPS
        rows, cols = rows[ok], cols[ok]
        m_gt, m_pr = gt_ids[rows], pr_ids[cols]
        last = prev_tracker[m_gt]
        idsw += int(np.sum(~np.isnan(last) & (m_pr != last)))
        not_tracked_before = np.isnan(prev_step_tracker)
        prev_tracker[m_gt] = m_pr
        prev_step_tracker[:] = np.nan
        prev_step_tracker[m_gt] = m_pr
        gt_frag += not_tracked_before & ~np.isnan(prev_step_tracker)
        gt_matched[m_gt] += 1
        tp += len(rows)
        fn += len(gt_ids) - len(rows)
        fp += len(pr_ids) - len(rows)
        motp_sum += float(sim[rows, cols].sum())
    present = gt_count > 0
    ratio = gt_matched[present] / gt_count[present]
    mt = int(np.sum(ratio > 0.8))
    ml = int(np.sum(ratio < 0.2))
    frag = int(np.sum(gt_frag[gt_frag > 0] - 1))
    n_ref = tp + fn
    return {
        "MOTA": (tp - fp - idsw) / max(1, n_ref),
        "MOTP": motp_sum / max(1, tp),
        "IDSW": idsw, "Frag": frag,
        "MT": mt, "PT": int(present.sum()) - mt - ml, "ML": ml,
        "CLR_TP": tp, "CLR_FP": fp, "CLR_FN": fn,
        "CLR_Precision": tp / max(1, tp + fp), "CLR_Recall": tp / max(1, n_ref),
    }


def identity_metrics(gt: MOTAnnotations, pred: MOTAnnotations, iou_threshold: float = 0.5) -> dict:
    """IDF1, IDP e IDR (associação global entre identidades)."""
    data, n_gt, n_pr = _prepare(gt, pred)
    potential = np.zeros((n_gt, n_pr))
    total_gt = total_pr = 0
    for gt_ids, pr_ids, sim in data:
        total_gt += len(gt_ids)
        total_pr += len(pr_ids)
        r, c = np.nonzero(sim >= iou_threshold - EPS)
        np.add.at(potential, (gt_ids[r], pr_ids[c]), 1)
    if potential.size:
        rows, cols = linear_sum_assignment(-potential)
        idtp = int(potential[rows, cols].sum())
    else:
        idtp = 0
    idfn, idfp = total_gt - idtp, total_pr - idtp
    return {
        "IDF1": idtp / max(1.0, idtp + 0.5 * idfp + 0.5 * idfn),
        "IDP": idtp / max(1, idtp + idfp), "IDR": idtp / max(1, idtp + idfn),
        "IDTP": idtp, "IDFP": idfp, "IDFN": idfn,
    }


def hota_metrics(gt: MOTAnnotations, pred: MOTAnnotations) -> dict:
    """HOTA, DetA, AssA e LocA (média dos 19 limiares de IoU)."""
    data, n_gt, n_pr = _prepare(gt, pred)
    n_a = len(HOTA_ALPHAS)
    tp = np.zeros(n_a); fn = np.zeros(n_a); fp = np.zeros(n_a); loc = np.zeros(n_a)
    if n_gt == 0 or n_pr == 0:
        total_gt = sum(len(g) for g, _, _ in data)
        total_pr = sum(len(p) for _, p, _ in data)
        det = 0.0 if (total_gt or total_pr) else 1.0
        return {"HOTA": det, "DetA": det, "AssA": det, "LocA": 1.0, "HOTA_TP": 0,
                "HOTA_FN": total_gt, "HOTA_FP": total_pr}
    potential = np.zeros((n_gt, n_pr))
    gt_count = np.zeros((n_gt, 1))
    pr_count = np.zeros((1, n_pr))
    for gt_ids, pr_ids, sim in data:
        if len(gt_ids) and len(pr_ids):
            denom = sim.sum(0)[None, :] + sim.sum(1)[:, None] - sim
            sim_iou = np.zeros_like(sim)
            mask = denom > EPS
            sim_iou[mask] = sim[mask] / denom[mask]
            potential[gt_ids[:, None], pr_ids[None, :]] += sim_iou
        gt_count[gt_ids] += 1
        pr_count[0, pr_ids] += 1
    global_align = potential / (gt_count + pr_count - potential)
    matches = np.zeros((n_a, n_gt, n_pr))
    for gt_ids, pr_ids, sim in data:
        if len(gt_ids) == 0:
            fp += len(pr_ids)
            continue
        if len(pr_ids) == 0:
            fn += len(gt_ids)
            continue
        score = global_align[gt_ids[:, None], pr_ids[None, :]] * sim
        rows, cols = linear_sum_assignment(-score)
        for a, alpha in enumerate(HOTA_ALPHAS):
            ok = sim[rows, cols] >= alpha - EPS
            r, c = rows[ok], cols[ok]
            n = len(r)
            tp[a] += n
            fn[a] += len(gt_ids) - n
            fp[a] += len(pr_ids) - n
            if n:
                loc[a] += sim[r, c].sum()
                matches[a, gt_ids[r], pr_ids[c]] += 1
    det_a = tp / np.maximum(1, tp + fn + fp)
    ass_a = np.zeros(n_a)
    for a in range(n_a):
        m = matches[a]
        ass_iou = m / np.maximum(1, gt_count + pr_count - m)
        ass_a[a] = (m * ass_iou).sum() / max(1, tp[a])
    loc_a = np.where(tp > 0, loc / np.maximum(1, tp), 1.0)
    hota = np.sqrt(det_a * ass_a)
    return {"HOTA": float(hota.mean()), "DetA": float(det_a.mean()), "AssA": float(ass_a.mean()),
            "LocA": float(loc_a.mean()), "HOTA_TP": float(tp.mean()), "HOTA_FN": float(fn.mean()),
            "HOTA_FP": float(fp.mean())}


def counting_metrics(gt: MOTAnnotations, pred: MOTAnnotations, frames: Sequence[int] | None = None) -> dict:
    """Erros de contagem por quadro e de identidades únicas.

    * ``Count_MAE``: média de |pessoas contadas − pessoas de referência| por quadro.
    * ``Count_Bias``: média de (contadas − referência); positivo = conta a mais.
    * ``ID_Count_Error``: identidades distintas geradas − pessoas distintas de
      referência. Valores altos indicam a mesma pessoa contada várias vezes
      (perda de rastreamento seguida de um novo id).
    """
    if frames is None:
        frames = np.union1d(gt.frames, pred.frames)
    frames = np.asarray(frames, int)
    g = gt.counts_per_frame(frames)
    p = pred.counts_per_frame(frames)
    err = p - g if len(frames) else np.zeros(0)
    n_gt_ids = len(gt.unique_ids())
    n_pr_ids = len(pred.unique_ids())
    track_lengths = np.unique(pred.ids[pred.ids >= 0], return_counts=True)[1]
    return {
        "Frames": int(len(frames)),
        "Count_MAE": float(np.abs(err).mean()) if len(err) else 0.0,
        "Count_RMSE": float(np.sqrt((err ** 2).mean())) if len(err) else 0.0,
        "Count_Bias": float(err.mean()) if len(err) else 0.0,
        "Count_MaxAbs": int(np.abs(err).max()) if len(err) else 0,
        "GT_People_Total": int(g.sum()), "Pred_People_Total": int(p.sum()),
        "GT_IDs": n_gt_ids, "Pred_IDs": n_pr_ids,
        "ID_Count_Error": n_pr_ids - n_gt_ids,
        "ID_Ratio": n_pr_ids / n_gt_ids if n_gt_ids else float("nan"),
        "Mean_Track_Length": float(track_lengths.mean()) if len(track_lengths) else 0.0,
    }


# --------------------------------------------------------------- avaliação
def evaluate_sequence(gt: GroundTruth | MOTAnnotations, pred: MOTAnnotations, iou_threshold: float = 0.5,
                      seq_length: int | None = None, mode: str = "track") -> dict:
    """Avalia uma sequência inteira.

    ``mode="track"`` calcula todas as métricas; ``mode="detect"`` ignora as
    identidades e calcula só detecção e contagem por quadro.
    """
    if isinstance(gt, GroundTruth):
        pred = remove_distractor_matches(pred, gt, iou_threshold)
        gt_ped = gt.pedestrians
    else:
        gt_ped = gt
    frames = np.arange(1, seq_length + 1) if seq_length else None
    if frames is not None:
        pred = pred.subset((pred.frames >= 1) & (pred.frames <= seq_length))
    result = detection_metrics(gt_ped, pred, iou_threshold)
    result.update(counting_metrics(gt_ped, pred, frames))
    if mode == "track":
        result.update(clear_metrics(gt_ped, pred, iou_threshold))
        result.update(identity_metrics(gt_ped, pred, iou_threshold))
        result.update(hota_metrics(gt_ped, pred))
    elif mode != "detect":
        raise ValueError("mode deve ser 'track' ou 'detect'")
    return result


def concatenate(items: Sequence[tuple[MOTAnnotations, MOTAnnotations, int]]):
    """Junta várias sequências numa só (quadros e ids deslocados) para o resultado geral."""
    gts, preds = [], []
    frame_offset = 0
    id_offset = 0
    for gt, pred, length in items:
        span = max(int(gt.ids.max(initial=0)), int(pred.ids.max(initial=0))) + 1
        g = gt.subset(np.ones(len(gt), bool)); p = pred.subset(np.ones(len(pred), bool))
        g.frames = g.frames + frame_offset; p.frames = p.frames + frame_offset
        g.ids = np.where(g.ids >= 0, g.ids + id_offset, g.ids)
        p.ids = np.where(p.ids >= 0, p.ids + id_offset, p.ids)
        gts.append(g); preds.append(p)
        frame_offset += length
        id_offset += span
    def cat(parts):
        return MOTAnnotations(*(np.concatenate([getattr(x, a) for x in parts]) for a in
                                ("frames", "ids", "boxes", "scores", "classes", "visibility")))
    return cat(gts), cat(preds), frame_offset


# ------------------------------------------------------------------ relatórios
MAIN_COLUMNS = ["Sequence", "HOTA", "DetA", "AssA", "MOTA", "IDF1", "Precision", "Recall",
                "IDSW", "Frag", "FP", "FN", "Count_MAE", "Count_Bias", "GT_IDs", "Pred_IDs", "ID_Count_Error"]


def save_metrics(rows: list[dict], out_dir: str | Path, stem: str = "metrics") -> dict[str, Path]:
    """Grava as métricas em JSON, CSV e Markdown."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = {"json": out_dir / f"{stem}.json", "csv": out_dir / f"{stem}.csv", "md": out_dir / f"{stem}.md"}
    paths["json"].write_text(json.dumps(rows, indent=2, ensure_ascii=False, default=_json_default), encoding="utf-8")
    keys = list(dict.fromkeys(k for r in rows for k in r))
    with open(paths["csv"], "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)
    paths["md"].write_text(markdown_table(rows), encoding="utf-8")
    return paths


def markdown_table(rows: list[dict], columns: Sequence[str] = MAIN_COLUMNS) -> str:
    cols = [c for c in columns if any(c in r for r in rows)]
    lines = ["| " + " | ".join(cols) + " |", "|" + "|".join("---" for _ in cols) + "|"]
    for r in rows:
        lines.append("| " + " | ".join(_fmt(r.get(c, "")) for c in cols) + " |")
    return "\n".join(lines) + "\n"


def _fmt(v) -> str:
    if isinstance(v, float):
        if math.isnan(v):
            return "-"
        return f"{v:.3f}"
    return str(v)


def _json_default(v):
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (np.floating,)):
        return float(v)
    raise TypeError(type(v))

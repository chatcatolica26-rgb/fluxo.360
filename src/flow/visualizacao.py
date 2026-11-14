"""Imagens e vídeos de saída: caixas com ids, trajetórias na planta e mapas de calor."""
from __future__ import annotations

import colorsys

import cv2
import numpy as np

VERDE, VERMELHO, BRANCO, PRETO = (60, 180, 75), (40, 40, 220), (255, 255, 255), (0, 0, 0)


def cor_do_id(i: int) -> tuple[int, int, int]:
    """Cor fixa por id (a mesma pessoa tem sempre a mesma cor)."""
    r, g, b = colorsys.hsv_to_rgb((i * 0.61803) % 1.0, 0.75, 0.95)
    return int(b * 255), int(g * 255), int(r * 255)


def desenhar_deteccoes(img: np.ndarray, posicoes) -> np.ndarray:
    """Caixa + id de cada pessoa; ponto dos pés verde (usado) ou vermelho (descartado)."""
    out = img.copy()
    for p in posicoes:
        cor = cor_do_id(p.id)
        cv2.rectangle(out, (int(p.x1), int(p.y1)), (int(p.x2), int(p.y2)), cor, 2)
        txt = f"id {p.id}"
        (tw, th), _ = cv2.getTextSize(txt, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
        cv2.rectangle(out, (int(p.x1), int(p.y1) - th - 6), (int(p.x1) + tw + 6, int(p.y1)), cor, -1)
        cv2.putText(out, txt, (int(p.x1) + 3, int(p.y1) - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.5, PRETO, 1, cv2.LINE_AA)
        cv2.circle(out, (int(p.pe_x), int(p.pe_y)), 5, VERDE if p.valida else VERMELHO, -1)
    return out


def regiao_interesse(mascara: np.ndarray | None, forma_planta: tuple[int, int], margem_px: int = 80,
                     pontos_px: np.ndarray | None = None) -> tuple[int, int, int, int]:
    """Retângulo (x0, y0, x1, y1) da planta em volta da área calibrada."""
    h, w = forma_planta
    if mascara is not None and mascara.any():
        ys, xs = np.nonzero(mascara)
        x0, y0, x1, y1 = xs.min(), ys.min(), xs.max(), ys.max()
    elif pontos_px is not None and len(pontos_px):
        x0, y0 = np.min(pontos_px, axis=0)
        x1, y1 = np.max(pontos_px, axis=0)
    else:
        return 0, 0, w, h
    return (int(max(0, x0 - margem_px)), int(max(0, y0 - margem_px)),
            int(min(w, x1 + margem_px)), int(min(h, y1 + margem_px)))


def suavizar(matriz_px: np.ndarray, sigma_px: float) -> np.ndarray:
    """Filtro gaussiano só para leitura visual; os números salvos não são suavizados."""
    if sigma_px <= 0:
        return matriz_px.astype(np.float32)
    return cv2.GaussianBlur(matriz_px.astype(np.float32), (0, 0), sigmaX=sigma_px)


def colorir(norm: np.ndarray) -> np.ndarray:
    """0..1 -> azul (baixo), verde, amarelo, vermelho (alto)."""
    return cv2.applyColorMap((np.clip(norm, 0, 1) * 255).astype(np.uint8), cv2.COLORMAP_JET)


def _legenda(img: np.ndarray, titulo: str, vmax: float, unidade: str) -> np.ndarray:
    h, w = img.shape[:2]
    barra_h, pad = 18, 10
    faixa = np.full((barra_h + 44, w, 3), 255, np.uint8)
    largura = max(w - 2 * pad, 10)
    grad = colorir(np.tile(np.linspace(0, 1, largura), (barra_h, 1)))
    faixa[24:24 + barra_h, pad:pad + largura] = grad
    esc = 0.5
    while esc > 0.3 and cv2.getTextSize(titulo, cv2.FONT_HERSHEY_SIMPLEX, esc, 1)[0][0] > w - 2 * pad:
        esc -= 0.02                                     # título cabe na largura da imagem
    cv2.putText(faixa, titulo, (pad, 17), cv2.FONT_HERSHEY_SIMPLEX, esc, PRETO, 1, cv2.LINE_AA)
    cv2.putText(faixa, "0", (pad, 24 + barra_h + 15), cv2.FONT_HERSHEY_SIMPLEX, 0.45, PRETO, 1, cv2.LINE_AA)
    txt = f"{vmax:.1f} {unidade}"
    (tw, _), _ = cv2.getTextSize(txt, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
    cv2.putText(faixa, txt, (pad + largura - tw, 24 + barra_h + 15), cv2.FONT_HERSHEY_SIMPLEX, 0.45, PRETO, 1,
                cv2.LINE_AA)
    return np.vstack([img, faixa])


def mapas_de_calor(matriz_px: np.ndarray, planta_bgr: np.ndarray, sigma_px: float, recorte: tuple,
                   titulo: str, unidade: str, alpha: float = 0.65, limiar: float = 0.03,
                   vmax_rotulo: float | None = None, escala: float = 1.0) -> dict[str, np.ndarray]:
    """Gera o mapa isolado e o sobreposto à planta, ambos recortados na área analisada.

    As cores vão de 0 ao maior valor da matriz suavizada. A legenda mostra ``vmax_rotulo``
    (o maior valor real de uma célula, sem suavização) quando informado.
    """
    x0, y0, x1, y1 = recorte
    m = suavizar(matriz_px, sigma_px)[y0:y1, x0:x1]
    vmax = float(m.max())
    norm = m / vmax if vmax > 0 else m
    cor = colorir(norm)
    fundo = planta_bgr[y0:y1, x0:x1]
    # planta clareada para o calor se destacar
    fundo = cv2.addWeighted(fundo, 0.55, np.full_like(fundo, 255), 0.45, 0)
    peso = (alpha * np.clip(norm / 0.25, 0, 1))[..., None]
    sobreposto = np.where((norm > limiar)[..., None], fundo * (1 - peso) + cor * peso, fundo).astype(np.uint8)
    isolado = np.where((norm > limiar)[..., None], cor, np.full_like(cor, 255)).astype(np.uint8)
    if escala != 1.0:                                   # amplia áreas pequenas para leitura
        sobreposto = cv2.resize(sobreposto, None, fx=escala, fy=escala, interpolation=cv2.INTER_LINEAR)
        isolado = cv2.resize(isolado, None, fx=escala, fy=escala, interpolation=cv2.INTER_LINEAR)
    rot = vmax if vmax_rotulo is None else float(vmax_rotulo)
    return {"sobreposto": _legenda(sobreposto, titulo, rot, unidade),
            "isolado": _legenda(isolado, titulo, rot, unidade), "vmax": rot}


class AnimacaoPlanta:
    """Quadros da planta (recortada) com o rastro recente de cada pessoa."""

    def __init__(self, planta_bgr: np.ndarray, recorte: tuple, rastro_s: float = 3.0, escala: float = 1.0):
        x0, y0, x1, y1 = recorte
        self.x0, self.y0 = x0, y0
        base = planta_bgr[y0:y1, x0:x1]
        self.base = cv2.addWeighted(base, 0.6, np.full_like(base, 255), 0.4, 0)
        self.escala = escala
        self.rastro_s = rastro_s
        self.hist: dict[int, list[tuple[float, float, float]]] = {}

    def quadro(self, tempo_s: float, posicoes) -> np.ndarray:
        for p in posicoes:
            if p.valida:
                self.hist.setdefault(p.id, []).append((tempo_s, p.planta_x - self.x0, p.planta_y - self.y0))
        img = self.base.copy()
        for pid, pts in self.hist.items():
            recentes = [(x, y) for t, x, y in pts if tempo_s - t <= self.rastro_s]
            if len(recentes) >= 2:
                cv2.polylines(img, [np.int32(recentes)], False, cor_do_id(pid), 2, cv2.LINE_AA)
        for p in posicoes:
            if p.valida:
                c = (int(p.planta_x - self.x0), int(p.planta_y - self.y0))
                cv2.circle(img, c, 6, cor_do_id(p.id), -1)
                cv2.putText(img, str(p.id), (c[0] + 7, c[1] - 7), cv2.FONT_HERSHEY_SIMPLEX, 0.45, PRETO, 1,
                            cv2.LINE_AA)
        cv2.putText(img, f"t = {tempo_s:5.1f} s", (10, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.6, PRETO, 1, cv2.LINE_AA)
        if self.escala != 1.0:
            img = cv2.resize(img, None, fx=self.escala, fy=self.escala, interpolation=cv2.INTER_AREA)
        return img


def desenhar_rastros(img: np.ndarray, trajetorias: dict, recorte: tuple, escala: float,
                     suavizar_pontos: int = 7) -> np.ndarray:
    """Desenha o caminho de cada pessoa sobre uma imagem recortada da planta (ex.: o mapa de calor).

    ``trajetorias``: {id: [(x_planta, y_planta), ...]} em ordem de tempo. Cada caminho é suavizado
    (média móvel), desenhado como linha fina escura com contorno claro, com um ponto no início e
    uma seta no fim indicando a direção.
    """
    out = img.copy()
    x0, y0 = recorte[0], recorte[1]
    camada = out.copy()
    k = max(1, int(suavizar_pontos))
    for pts in trajetorias.values():
        p = np.asarray(pts, dtype=np.float64)
        if len(p) < 2:
            continue
        if len(p) >= k:                              # média móvel: tira o tremor da detecção
            ker = np.ones(k) / k
            p = np.stack([np.convolve(p[:, 0], ker, mode="valid"), np.convolve(p[:, 1], ker, mode="valid")], 1)
        q = np.int32(np.round((p - [x0, y0]) * escala))
        cv2.polylines(camada, [q], False, (255, 255, 255), 4, cv2.LINE_AA)   # contorno claro
        cv2.polylines(camada, [q], False, (40, 40, 40), 2, cv2.LINE_AA)
        cv2.circle(camada, tuple(q[0]), 3, (40, 40, 40), -1, cv2.LINE_AA)
        a, b = q[max(0, len(q) - 6)], q[-1]
        if np.hypot(*(b - a)) > 4:
            cv2.arrowedLine(camada, tuple(a), tuple(b), (40, 40, 40), 2, cv2.LINE_AA, tipLength=0.9)
    return cv2.addWeighted(camada, 0.8, out, 0.2, 0)


def pixelar(img: np.ndarray, fator: int = 8) -> np.ndarray:
    """Anonimiza o quadro: reduz e amplia em blocos. As pessoas viram silhuetas, sem rosto reconhecível."""
    h, w = img.shape[:2]
    pequeno = cv2.resize(img, (max(1, w // fator), max(1, h // fator)), interpolation=cv2.INTER_AREA)
    return cv2.resize(pequeno, (w, h), interpolation=cv2.INTER_NEAREST)

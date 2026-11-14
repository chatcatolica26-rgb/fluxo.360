"""Ponto dos pés, projeção na planta e registro das trajetórias.

Para cada pessoa rastreada em cada quadro:
  1. ponto dos pés = centro da base da caixa: x_pe = (x1 + x2) / 2, y_pe = y2
     (o centro da caixa ficaria na altura da cintura e cairia no lugar errado da planta);
  2. projeção na planta com a homografia da câmera;
  3. validação: a posição só é usada se o pé estiver visível e dentro da área calibrada.
Toda posição descartada fica registrada com o motivo.
"""
from __future__ import annotations

import csv
from collections import Counter, defaultdict
from dataclasses import dataclass, fields
from pathlib import Path

import numpy as np

# motivos de descarte
TOCA_BORDA = "pe_na_borda_do_quadro"      # pé provavelmente cortado: posição incerta
FORA_DA_MASCARA = "fora_da_area_calibrada"
FORA_DA_PLANTA = "fora_da_imagem_da_planta"
PROJECAO_INVALIDA = "projecao_invalida"


@dataclass
class Posicao:
    quadro: int
    tempo_s: float
    id: int
    score: float
    x1: float
    y1: float
    x2: float
    y2: float
    pe_x: float
    pe_y: float
    planta_x: float
    planta_y: float
    planta_x_m: float
    planta_y_m: float
    valida: bool
    motivo_descarte: str


def ponto_dos_pes(x1: float, y1: float, x2: float, y2: float) -> tuple[float, float]:
    """Centro da base da caixa (contato aproximado dos pés com o chão)."""
    return (x1 + x2) / 2.0, y2


class RegistroTrajetorias:
    """Acumula as posições de todas as pessoas, válidas e descartadas."""

    def __init__(self, camera, largura_quadro: int, altura_quadro: int,
                 largura_planta: int, altura_planta: int, margem_borda_px: int = 3):
        self.camera = camera
        self.wq, self.hq = largura_quadro, altura_quadro
        self.wp, self.hp = largura_planta, altura_planta
        self.margem = margem_borda_px
        self.posicoes: list[Posicao] = []

    def adicionar(self, quadro: int, tempo_s: float, tracks) -> list[Posicao]:
        """``tracks``: objetos com ``track_id, x, y, w, h, score`` (src.tracking.Track)."""
        if not tracks:
            return []
        caixas = np.array([[t.x, t.y, t.x + t.w, t.y + t.h] for t in tracks], dtype=np.float64)
        pes = np.stack([(caixas[:, 0] + caixas[:, 2]) / 2.0, caixas[:, 3]], axis=1)
        planta = self.camera.projetar(pes)                     # homografia: vídeo -> planta
        dentro = self.camera.dentro(planta)
        novas = []
        for t, c, pe, p, ok_mask in zip(tracks, caixas, pes, planta, dentro):
            motivo = ""
            if not np.all(np.isfinite(p)):
                motivo = PROJECAO_INVALIDA
            elif pe[1] >= self.hq - self.margem:
                motivo = TOCA_BORDA
            elif not (0 <= p[0] < self.wp and 0 <= p[1] < self.hp):
                motivo = FORA_DA_PLANTA
            elif not ok_mask:
                motivo = FORA_DA_MASCARA
            pm = p / self.camera.px_por_metro if np.all(np.isfinite(p)) else (np.nan, np.nan)
            novas.append(Posicao(int(quadro), round(float(tempo_s), 4), int(t.track_id), round(float(t.score), 4),
                                 *[round(float(v), 2) for v in c], round(float(pe[0]), 2), round(float(pe[1]), 2),
                                 round(float(p[0]), 2), round(float(p[1]), 2),
                                 round(float(pm[0]), 3), round(float(pm[1]), 3), motivo == "", motivo))
        self.posicoes += novas
        return novas

    # ------------------------------------------------------------ resumos
    def validas(self) -> list[Posicao]:
        return [p for p in self.posicoes if p.valida]

    def trajetorias(self, min_pontos: int = 1) -> dict[int, list[Posicao]]:
        por_id: dict[int, list[Posicao]] = defaultdict(list)
        for p in self.validas():
            por_id[p.id].append(p)
        return {i: ps for i, ps in por_id.items() if len(ps) >= min_pontos}

    def resumo(self, min_pontos_trajetoria: int = 5) -> dict:
        ids_todos = {p.id for p in self.posicoes}
        ids_validos = {p.id for p in self.validas()}
        return {
            "deteccoes_total": len(self.posicoes),
            "deteccoes_validas": len(self.validas()),
            "descartes_por_motivo": dict(Counter(p.motivo_descarte for p in self.posicoes if not p.valida)),
            "ids_rastreados": len(ids_todos),
            "pessoas_unicas_na_area": len(ids_validos),
            "trajetorias_registradas": len(self.trajetorias(min_pontos_trajetoria)),
            "min_pontos_por_trajetoria": min_pontos_trajetoria,
        }

    def salvar_csv(self, caminho: str | Path) -> Path:
        caminho = Path(caminho)
        caminho.parent.mkdir(parents=True, exist_ok=True)
        nomes = [f.name for f in fields(Posicao)]
        with open(caminho, "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(nomes)
            for p in self.posicoes:
                w.writerow([getattr(p, n) for n in nomes])
        return caminho

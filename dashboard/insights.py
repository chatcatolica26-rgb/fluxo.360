"""Recomendações automáticas do FLUXO360 para o lojista e para a administração do shopping.

São regras analíticas sobre os dados de fluxo (horários, regiões, trajetos, permanência):
cada recomendação traz a evidência (o número que a sustenta), a ação e como medir o resultado.
Com os dados simulados das telas, os números também são simulados.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import yaml

import dados_simulados as sim


def _n(v: float, casas: int = 0) -> str:
    s = f"{v:,.{casas}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def _pct(v: float) -> str:
    return _n(100 * v, 0 if v >= 0.1 else 1) + "%"


# De onde as pessoas chegam e para onde seguem em cada ambiente (lido das setas de fluxo do mapa)
ORIGEM_DESTINO = {
    "Entrada Principal": ("da rua e do estacionamento", "para a Junção, rumo aos corredores"),
    "Corredor A": ("da Entrada (pela Junção)", "para a Praça de Alimentação"),
    "Corredor B": ("da Entrada (pela Junção)", "para a Área de Convivência"),
    "Praça de Alimentação": ("do Corredor A", "de volta pelo Corredor A"),
    "Área de Convivência": ("do Corredor B", "de volta pelo Corredor B"),
}
ARTIGO = {"Entrada Principal": "a", "Corredor A": "o", "Corredor B": "o", "Praça de Alimentação": "a",
          "Área de Convivência": "a"}


def _com(prep: str, ambiente: str) -> str:
    """'pelo Corredor B', 'na Praça de Alimentação'..."""
    art = ARTIGO.get(ambiente, "o")
    formas = {"por": {"o": "pelo", "a": "pela"}, "em": {"o": "no", "a": "na"}, "de": {"o": "do", "a": "da"}}
    return f"{formas[prep][art]} {ambiente}"


def janela_de_pico(serie: pd.Series) -> tuple[int, int, float]:
    """Horas seguidas com fluxo >= 80% do máximo: (início, fim, fração do dia nessa janela)."""
    v = serie.to_numpy(float)
    i = int(v.argmax())
    ini = fim = i
    while ini > 0 and v[ini - 1] >= 0.8 * v[i]:
        ini -= 1
    while fim < len(v) - 1 and v[fim + 1] >= 0.8 * v[i]:
        fim += 1
    return sim.HORAS[ini], sim.HORAS[fim], float(v[ini:fim + 1].sum() / v.sum())


# ------------------------------------------------------------------------- lojista
def lojista(ambiente: str, periodo: str = "Hoje") -> list[dict]:
    amb = sim.ambientes(periodo).set_index("ambiente")
    r = amb.loc[ambiente]
    total = amb.passagens.sum()
    hora = sim.fluxo_por_hora(periodo, ambiente)["Período selecionado"]
    ini, fim, frac = janela_de_pico(hora)
    vale = sim.HORAS[int(hora.to_numpy().argmin())]
    origem, destino = ORIGEM_DESTINO[ambiente]
    frio = r.passagens / total < 0.08
    saida = []

    saida.append({
        "tema": "Equipe e caixas", "cor": "#3b82f6",
        "titulo": f"Reforce atendimento e caixas das {ini}h às {fim + 1}h",
        "evidencia": f"Essa janela concentra {_pct(frac)} do movimento do dia em frente à sua loja; "
                     f"o pico é às {int(r.pico_h)}h e o menor movimento, às {vale}h.",
        "acao": f"Escale mais vendedores e abra todos os caixas das {ini}h às {fim + 1}h. Use as {vale}h para "
                "reposição, intervalos e treinamento.",
        "medir": "Tempo de fila e vendas por hora, antes e depois da nova escala.",
    })
    isca = (f"Coloque o produto isca (oferta forte, lançamento) na vitrine voltada para quem vem {origem}, "
            "e os produtos de maior procura no fundo da loja, para o cliente atravessar o espaço.")
    if frio:
        isca += (" Como seu ambiente recebe pouco fluxo, leve também a isca para fora: um totem ou degustação "
                 "na Junção, por onde todos passam antes de escolher o corredor.")
    saida.append({
        "tema": "Produto isca", "cor": "#d64541",
        "titulo": "Use o produto isca para puxar o cliente para dentro",
        "evidencia": f"A maior parte de quem passa {_com('por', ambiente)} vem {origem} e segue {destino}.",
        "acao": isca,
        "medir": "Taxa de entrada na loja (pessoas que entram ÷ pessoas que passam) e vendas do item isca.",
    })
    if r.permanencia_min >= 15:
        vitrine = (f"Aqui as pessoas ficam em média {int(r.permanencia_min)} min: há tempo para ler. Use ofertas "
                   "de impulso, degustação e QR code com cupom.")
        tit = "Aproveite o tempo de permanência"
    else:
        vitrine = (f"Aqui a passagem é rápida (cerca de {int(r.permanencia_min)} min no ambiente): mensagem curta, "
                   "preço grande e uma oferta só na vitrine.")
        tit = "Vitrine para quem está de passagem"
    saida.append({
        "tema": "Vitrine e ofertas", "cor": "#4fb39a", "titulo": tit,
        "evidencia": f"Permanência média de {int(r.permanencia_min)} min {_com('em', ambiente)}.",
        "acao": vitrine + f" Troque a vitrine e as ofertas antes do pico (até as {max(ini - 1, 10)}h).",
        "medir": "Vendas da oferta em destaque e taxa de entrada, comparando semanas equivalentes.",
    })
    if frio:
        saida.append({
            "tema": "Negociar com o shopping", "cor": "#f2994a",
            "titulo": "Peça ações de aquecimento do corredor",
            "evidencia": f"{ARTIGO.get(ambiente, 'o').upper()} {ambiente} recebe {_pct(r.passagens / total)} das passagens e caiu "
                         f"{_n(abs(r.variacao_pct), 1)}% em relação ao período anterior.",
            "acao": "Leve os números à administração e proponha, junto com os vizinhos, sinalização na Junção, "
                    "evento no corredor ou condição especial de aluguel enquanto o fluxo não sobe.",
            "medir": "Passagens no corredor e vendas da loja durante e depois da ação.",
        })
    return saida


# -------------------------------------------------------------------- administração
def valor_do_ponto(periodo: str = "Hoje") -> pd.DataFrame:
    """Índice de fluxo por região (1,0 = média) e faixa de preço sugerida para o espaço."""
    reg = sim.regioes(periodo)
    indice = reg.passagens / reg.passagens.mean()
    faixa = np.where(indice >= 1.5, "Premium", np.where(indice >= 0.7, "Padrão", "Incentivo"))
    mult = indice.clip(0.5, 2.0).round(1)
    return pd.DataFrame({"Região": reg.regiao, "Passagens": reg.passagens, "Participação": reg.passagens / reg.passagens.sum(),
                         "Índice de fluxo": indice.round(2), "Faixa": faixa, "Multiplicador sugerido": mult}
                        ).sort_values("Índice de fluxo", ascending=False).reset_index(drop=True)


def pontos_mortos(periodo: str = "Hoje", limite: float = 0.02) -> pd.DataFrame:
    reg = sim.regioes(periodo)
    reg = reg.assign(participacao=reg.passagens / reg.passagens.sum())
    return reg[reg.participacao < limite].sort_values("participacao")


def administracao(periodo: str = "Hoje") -> list[dict]:
    reg = sim.regioes(periodo).assign(participacao=lambda d: d.passagens / d.passagens.sum())
    mortos = pontos_mortos(periodo)
    amb = sim.ambientes(periodo).set_index("ambiente")
    saida = []

    if not mortos.empty:
        nomes = " e ".join(mortos.regiao)
        saida.append({
            "tema": "Pontos mortos", "cor": "#3b6fb6",
            "titulo": f"{len(mortos)} ponto(s) morto(s): {nomes}",
            "evidencia": "Juntos recebem " + _pct(mortos.participacao.sum()) + " das passagens do piso, contra "
                         + _pct(reg.participacao.max()) + " da região mais movimentada.",
            "acao": "Trate essas áreas como prioridade comercial: lojas ali vendem menos e tendem a sair.",
            "medir": "Passagens por semana em cada ponto e ocupação das lojas próximas.",
        })
        saida.append({
            "tema": "Aquecer pontos frios", "cor": "#f2994a",
            "titulo": "Plano para aquecer o fim do Corredor B",
            "evidencia": f"O Corredor B caiu {_n(abs(amb.loc['Corredor B', 'variacao_pct']), 1)}% e só "
                         f"{_pct(sim.transicoes(periodo)[2][2] / sim.transicoes(periodo)[0][2])} de quem passa pela Junção entra nele.",
            "acao": "1) Sinalização e piso direcional na Junção apontando para o Corredor B; "
                    "2) um quiosque ou ativação temática no fim do corredor, como destino; "
                    "3) evento ou promoção relâmpago no horário de pico do shopping (18h); "
                    "4) serviços de visita obrigatória (caixa eletrônico, conserto, lotérica) no trecho final; "
                    "5) aluguel com desconto temporário para atrair lojistas.",
            "medir": "Testar uma ação por vez por 2 a 4 semanas e comparar as passagens com o mesmo período anterior.",
        })

    candidatos = reg[(reg.intensidade.isin(["Elevada", "Muito elevada"])) & (reg.ambiente.str.startswith("Corredor"))]
    if not candidatos.empty:
        top = candidatos.sort_values("passagens", ascending=False).head(2)
        saida.append({
            "tema": "Quiosques", "cor": "#4fb39a",
            "titulo": "Melhores pontos para quiosques: " + " e ".join(top.regiao),
            "evidencia": "Fluxo alto e contínuo (" + ", ".join(_n(v) + " passagens" for v in top.passagens)
                         + "), sem a lotação da Praça de Alimentação.",
            "acao": "Instale ou realoque quiosques nesses trechos, deixando a faixa de circulação livre. Evite a "
                    "Praça de Alimentação no almoço e a porta da Entrada, onde o quiosque atrapalha o acesso.",
            "medir": "Vendas por m² do quiosque e passagens no trecho, antes e depois.",
        })

    vp = valor_do_ponto(periodo)
    premium = vp[vp.Faixa == "Premium"]["Região"].tolist()
    incentivo = vp[vp.Faixa == "Incentivo"]["Região"].tolist()
    saida.append({
        "tema": "Preço do espaço", "cor": "#8b5cf6",
        "titulo": "Preço de locação e mídia de acordo com o fluxo de cada ponto",
        "evidencia": f"O ponto mais movimentado recebe {_n(vp['Índice de fluxo'].max(), 1)} vezes a média; "
                     f"o menos movimentado, {_n(vp['Índice de fluxo'].min(), 2)} vez.",
        "acao": ("Faixa Premium (" + ", ".join(premium) + ") justifica valor acima da tabela para quiosques, "
                 "mídia e ativações; faixa Incentivo (" + ", ".join(incentivo) + ") pede desconto para atrair "
                 "ocupação. Use o multiplicador da tabela abaixo como referência."),
        "medir": "Ocupação, inadimplência e receita por m² por faixa, a cada trimestre.",
    })

    pico_alim = int(amb.loc["Praça de Alimentação", "pico_h"])
    pico_ent = int(amb.loc["Entrada Principal", "pico_h"])
    saida.append({
        "tema": "Equipe do shopping", "cor": "#64748b",
        "titulo": "Limpeza e segurança onde e quando o movimento pede",
        "evidencia": f"Praça de Alimentação com pico às {pico_alim}h (região mais cheia do piso); "
                     f"Entrada Principal com pico às {pico_ent}h.",
        "acao": f"Reforce a limpeza na Praça de Alimentação das {pico_alim - 1}h às {pico_alim + 2}h e a segurança "
                f"e orientação na Entrada das {pico_ent - 1}h às {pico_ent + 1}h.",
        "medir": "Reclamações, tempo de limpeza das mesas e ocorrências por horário.",
    })
    return saida


# --------------------------------------------------------------- vídeo real (demo)
def achados_video(execucao) -> list[dict]:
    """Achados da análise de vídeo real: quanto do tempo de permanência fica perto de cada ponto de interesse."""
    if execucao is None:
        return []
    npz = execucao.arquivo("matrizes.npz")
    cam_arq = Path(execucao.info.get("calibracao", {}).get("arquivo", ""))
    if npz is None or not cam_arq.is_file():
        return []
    cam = yaml.safe_load(cam_arq.read_text(encoding="utf-8")) or {}
    pontos = cam.get("pontos_de_interesse") or {}
    if not pontos:
        return []
    d = np.load(npz)
    perm = d["permanencia_s"]
    k = float(d["px_por_celula"])
    total = perm.sum()
    if total <= 0:
        return []
    ys, xs = np.indices(perm.shape)
    cx, cy = (xs + 0.5) * k, (ys + 0.5) * k
    ppm = k / float(d["celula_m"])
    raio = 3.0 * ppm
    parte = {}
    for nome, p in pontos.items():
        dentro = (cx - p["px"][0]) ** 2 + (cy - p["px"][1]) ** 2 <= raio ** 2
        parte[nome] = (p.get("descricao", nome), float(perm[dentro].sum() / total))
    ordem = sorted(parte.items(), key=lambda kv: kv[1][1], reverse=True)
    (n1, (d1, v1)), (n2, (d2, v2)) = ordem[0], ordem[-1]
    return [{
        "tema": "Vídeo real · Praça de Eventos", "cor": "#d64541",
        "titulo": f"O movimento se concentra junto à {d1}",
        "evidencia": f"{_pct(v1)} do tempo de permanência medido fica a até 3 m da {d1}; "
                     f"a {d2} concentra {_pct(v2)}.",
        "acao": f"A {d1} é o ponto de maior visibilidade da praça: bom lugar para sinalização, mídia e "
                f"ativações. A {d2}, pouco ocupada, pode receber um quiosque ou atração para ser aproveitada.",
        "medir": "Repetir a análise com algumas horas de vídeo, em dias e horários diferentes, antes de decidir.",
    }]

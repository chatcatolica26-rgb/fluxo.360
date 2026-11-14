"""Dados SIMULADOS do painel (mesmos números da apresentação no Lovable).

Tudo aqui é demonstrativo: não vem de câmeras. Os resultados reais do vídeo
são lidos separadamente em ``dados_reais.py``.
A curva por horário não estava na apresentação: é gerada aqui (pico no horário
de cada ambiente), escalada para bater com o total de passagens.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

SHOPPING = "Shopping Central"
CIDADE = "São Paulo, SP"
HORAS = list(range(10, 22))                     # 10h a 21h
PERIODOS = {"Hoje": 1, "Semana": 7, "Mês": 30}   # multiplicador simulado
JANELAS = {"Período completo": (10, 21), "Manhã": (10, 11), "Horário de almoço": (12, 13),
           "Tarde": (14, 17), "Noite": (18, 21)}

AMBIENTES = pd.DataFrame([
    # nome, passagens (hoje), variação %, intensidade, pico (h), permanência (min)
    ("Entrada Principal", 3280, 12.4, "elevado", 18, 4),
    ("Corredor A", 2940, 8.2, "intermediário", 18, 8),
    ("Corredor B", 640, -18.6, "baixo", 15, 5),
    ("Praça de Alimentação", 4260, 24.8, "muito elevado", 12, 32),
    ("Área de Convivência", 1360, 6.1, "intermediário", 20, 18),
], columns=["ambiente", "passagens", "variacao_pct", "intensidade", "pico_h", "permanencia_min"])

# 9 regiões de análise do mapa (passagens no período completo de hoje)
REGIOES = pd.DataFrame([
    ("entrada", "Entrada Principal", "Entrada Principal", 3280),
    ("a_inicio", "Corredor A · início", "Corredor A", 1176),
    ("a_centro", "Corredor A · trecho central", "Corredor A", 1029),
    ("a_final", "Corredor A · final", "Corredor A", 735),
    ("b_inicio", "Corredor B · início", "Corredor B", 320),
    ("b_centro", "Corredor B · trecho central", "Corredor B", 192),
    ("b_final", "Corredor B · final", "Corredor B", 128),
    ("alimentacao", "Praça de Alimentação", "Praça de Alimentação", 4260),
    ("convivencia", "Área de Convivência", "Área de Convivência", 1360),
], columns=["id", "regiao", "ambiente", "passagens"])

TRANSICOES = [
    ("entrada", "juncao", 3280), ("juncao", "corredor_a", 2380), ("juncao", "corredor_b", 900),
    ("corredor_a", "alimentacao", 1800), ("corredor_b", "convivencia", 600),
    ("corredor_a", "saida_oeste", 260), ("corredor_b", "saida_leste", 100),
]

# escala de intensidade: limites em passagens (período completo, hoje)
NIVEIS = [("Baixa", 0), ("Moderada", 150), ("Elevada", 500), ("Muito elevada", 900),
          ("Concentração crítica", 4000)]
CORES_NIVEL = {"Baixa": "#3b6fb6", "Moderada": "#4fb39a", "Elevada": "#f2c94c",
               "Muito elevada": "#f2994a", "Concentração crítica": "#d64541"}

KPIS = {"passagens": 12480, "passagens_var": 14.2, "ambientes": 5, "oportunidades": 3, "alertas": 2}

DIAGNOSTICOS = [
    {"n": "01", "nivel": "Prioridade alta", "cor": "#d64541", "ambiente": "Corredor B",
     "titulo": "Corredor B, baixa circulação", "ancora": "plano-corredor-b",
     "resumo": "Recebe menos circulação que a referência simulada.",
     "metricas": [("Passagens simuladas", "640"), ("Hoje vs. referência", "−18,6%")],
     "recomendacao": "Testar uma ativação comercial temporária e avaliar melhorias na sinalização de acesso.",
     "hipoteses": "Sinalização insuficiente, disposição dos acessos ou baixa atratividade comercial, "
                  "a confirmar no local.",
     "potencial": "Cenário de 80 para 110 passagens por hora (estimativa simulada, sem garantia)."},
    {"n": "02", "nivel": "Atenção", "cor": "#f2994a", "ambiente": "Praça de Alimentação",
     "titulo": "Alimentação, concentração no almoço", "ancora": "plano-alimentacao",
     "resumo": "A Praça de Alimentação concentra o maior volume, com pico às 12h.",
     "metricas": [("Passagens simuladas", "4.260"), ("Pico de circulação", "12h")],
     "recomendacao": "Observar os acessos no almoço e testar uma organização temporária dos trajetos de entrada.",
     "hipoteses": "Distribuição dos acessos e concentração de atividades. Os dados não comprovam "
                  "congestionamento nem sua causa.",
     "potencial": "Circulação mais distribuída, sem tratar redução de fluxo como melhora automática."},
    {"n": "03", "nivel": "Oportunidade", "cor": "#4fb39a", "ambiente": "Área de Convivência",
     "titulo": "Convivência, potencial para experiências", "ancora": "plano-convivencia",
     "resumo": "Combina circulação e tempo de permanência favoráveis a novas experiências.",
     "metricas": [("Passagens simuladas", "1.360"), ("Permanência simulada", "18 min")],
     "recomendacao": "Testar uma programação cultural temporária e acompanhar circulação e permanência.",
     "hipoteses": "A programação pode ampliar o interesse pelo espaço: hipótese a testar, não causa.",
     "potencial": "Investigar maior interesse e permanência, sem promessa de aumento."},
]

PLANOS = [
    {"n": "01", "nivel": "Prioridade alta", "tema": "Corredor B — baixa circulação",
     "acao": "Testar ativação comercial temporária e avaliar melhorias na sinalização de acesso.",
     "indicador": "Passagens por hora", "referencia": 80, "unidade": "passagens/h",
     "comparar": "Comparar com dias e horários equivalentes antes e depois da ação."},
    {"n": "02", "nivel": "Atenção", "tema": "Alimentação — concentração no almoço",
     "acao": "Observar os acessos no almoço e testar a organização temporária dos trajetos de entrada.",
     "indicador": "Passagens por hora no acesso observado", "referencia": 355, "unidade": "passagens/h",
     "comparar": "Incluir filas e distribuição: menos fluxo, isolado, não indica melhora."},
    {"n": "03", "nivel": "Oportunidade", "tema": "Convivência — potencial para experiências",
     "acao": "Experimentar programação cultural temporária e acompanhar circulação e permanência.",
     "indicador": "Permanência média", "referencia": 18, "unidade": "min",
     "comparar": "Comparar períodos com e sem programação."},
]


def curva_horaria(pico_h: int, largura: float = 2.2, base: float = 0.25) -> np.ndarray:
    """Formato do dia (soma 1): base constante + pico gaussiano no horário de pico."""
    h = np.array(HORAS, float)
    c = base + np.exp(-0.5 * ((h - pico_h) / largura) ** 2)
    return c / c.sum()


def fluxo_por_hora(periodo: str = "Hoje", ambiente: str | None = None) -> pd.DataFrame:
    """Passagens por hora (período selecionado e anterior), simuladas."""
    mult = PERIODOS[periodo]
    amb = AMBIENTES if not ambiente or ambiente == "Todos" else AMBIENTES[AMBIENTES.ambiente == ambiente]
    atual = np.zeros(len(HORAS))
    anterior = np.zeros(len(HORAS))
    for _, r in amb.iterrows():
        c = curva_horaria(int(r.pico_h)) * r.passagens * mult
        atual += c
        anterior += c / (1 + r.variacao_pct / 100)
    return pd.DataFrame({"hora": [f"{h}h" for h in HORAS], "Período selecionado": atual.round(0),
                         "Período anterior": anterior.round(0)})


def fracao_janela(ambiente: str, janela: str) -> float:
    """Parte do dia (0 a 1) que cai na janela de horário, para o ambiente."""
    ini, fim = JANELAS[janela]
    pico = int(AMBIENTES.set_index("ambiente").loc[ambiente, "pico_h"])
    c = curva_horaria(pico)
    return float(sum(v for h, v in zip(HORAS, c) if ini <= h <= fim))


def nivel(passagens: float, escala: float = 1.0) -> str:
    atual = NIVEIS[0][0]
    for nome, limite in NIVEIS:
        if passagens >= limite * escala:
            atual = nome
    return atual


def regioes(periodo: str = "Hoje", janela: str = "Período completo") -> pd.DataFrame:
    """Passagens e nível de intensidade por região, no período e na janela."""
    mult = PERIODOS[periodo]
    df = REGIOES.copy()
    frac = df.ambiente.map(lambda a: fracao_janela(a, janela))
    df["passagens"] = (df.passagens * frac * mult).round(0).astype(int)
    escala_media = float(np.mean([fracao_janela(a, janela) for a in AMBIENTES.ambiente])) * mult
    df["intensidade"] = df.passagens.map(lambda v: nivel(v, escala_media))
    return df


def ambientes(periodo: str = "Hoje") -> pd.DataFrame:
    df = AMBIENTES.copy()
    df["passagens"] = df.passagens * PERIODOS[periodo]
    return df


def kpis(periodo: str = "Hoje") -> dict:
    k = dict(KPIS)
    k["passagens"] = KPIS["passagens"] * PERIODOS[periodo]
    return k


_AMB_ORIGEM = {"entrada": "Entrada Principal", "juncao": "Entrada Principal", "corredor_a": "Corredor A",
               "corredor_b": "Corredor B"}


def transicoes(periodo: str = "Hoje", janela: str = "Período completo") -> list[tuple[str, str, int]]:
    """Fluxos entre ambientes, escalados pelo horário do ambiente de origem."""
    mult = PERIODOS[periodo]
    return [(a, b, int(round(v * mult * fracao_janela(_AMB_ORIGEM[a], janela)))) for a, b, v in TRANSICOES]

"""Gráficos Plotly do painel."""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

AZUL, CINZA = "#3b82f6", "#9aa4b2"   # legíveis no tema claro e no escuro
CORES_AMBIENTE = {"Praça de Alimentação": "#d64541", "Entrada Principal": "#f2994a", "Corredor A": "#f2c94c",
                  "Área de Convivência": "#4fb39a", "Corredor B": "#3b6fb6"}


def _layout(fig: go.Figure, altura: int = 340) -> go.Figure:
    fig.update_layout(height=altura, margin=dict(l=10, r=10, t=30, b=10), plot_bgcolor="rgba(0,0,0,0)",
                      paper_bgcolor="rgba(0,0,0,0)",
                      legend=dict(orientation="h", y=1.12, x=0), font=dict(size=13))
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(gridcolor="rgba(128,128,128,.25)", separatethousands=True)
    return fig


def fluxo_horario(df: pd.DataFrame) -> go.Figure:
    """Linhas: período selecionado (forte) x período anterior (cinza tracejado), com o pico marcado."""
    fig = go.Figure()
    fig.add_scatter(x=df.hora, y=df["Período anterior"], name="Período anterior", mode="lines",
                    line=dict(color=CINZA, width=2, dash="dash"))
    fig.add_scatter(x=df.hora, y=df["Período selecionado"], name="Período selecionado", mode="lines+markers",
                    line=dict(color=AZUL, width=3))
    pico = df.loc[df["Período selecionado"].idxmax()]
    fig.add_annotation(x=pico.hora, y=pico["Período selecionado"], text=f"Pico às {pico.hora}", showarrow=True,
                       arrowhead=2, ay=-35)
    fig.update_yaxes(title="passagens")
    return _layout(fig)


def fluxo_por_ambiente(df: pd.DataFrame) -> go.Figure:
    d = df.sort_values("passagens")
    fig = px.bar(d, x="passagens", y="ambiente", orientation="h", text="passagens",
                 color="ambiente", color_discrete_map=CORES_AMBIENTE)
    fig.update_traces(texttemplate="%{text:,.0f}", textposition="outside", cliponaxis=False)
    fig.update_layout(showlegend=False, yaxis_title=None, xaxis_title="passagens")
    return _layout(fig, 300)


def participacao(df: pd.DataFrame) -> go.Figure:
    fig = px.pie(df, names="ambiente", values="passagens", hole=0.6, color="ambiente",
                 color_discrete_map=CORES_AMBIENTE)
    fig.update_traces(textinfo="percent", sort=False)
    total = f"{int(df.passagens.sum()):,}".replace(",", ".")
    fig.add_annotation(text=f"<b>{total}</b><br>passagens", showarrow=False, font=dict(size=14))
    return _layout(fig, 320)


def simulador(antes: float, depois: float, unidade: str) -> go.Figure:
    d = pd.DataFrame({"Fase": ["Antes da intervenção", "Após a intervenção"], "valor": [antes, depois]})
    fig = px.bar(d, x="Fase", y="valor", text="valor", color="Fase",
                 color_discrete_sequence=[CINZA, AZUL])
    fig.update_traces(textposition="outside", cliponaxis=False)
    fig.update_layout(showlegend=False, xaxis_title=None, yaxis_title=unidade)
    fig.update_yaxes(range=[0, max(200, depois * 1.2, antes * 1.2)])
    return _layout(fig, 300)


def pessoas_no_tempo(df: pd.DataFrame) -> go.Figure:
    """Pessoas na área calibrada a cada segundo do vídeo real."""
    fig = px.area(df, x="segundo", y="pessoas")
    fig.update_traces(line_color=AZUL, fillcolor="rgba(59,130,246,.2)")
    fig.update_layout(xaxis_title="tempo do vídeo (s)", yaxis_title="pessoas na área")
    return _layout(fig, 260)

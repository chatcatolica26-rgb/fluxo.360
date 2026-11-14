"""01 · Visão geral — responde em segundos: como estamos, o que pede ação e onde.

Os detalhes ficam nas outras telas; aqui só o essencial e os caminhos para aprofundar.
"""
import streamlit as st

import componentes as ui
import dados_reais
import dados_simulados as sim

def _resumo(periodo: str) -> None:
    k = sim.kpis(periodo)
    amb = sim.ambientes(periodo)
    pior = amb.loc[amb.variacao_pct.idxmin()]
    st.markdown(
        f"<div style='font-size:1.35rem; line-height:1.5; margin:.6rem 0 1rem 0'>"
        f"{ui.numero(k['passagens'])} passagens, <b>{ui.numero(k['passagens_var'], 1)}% a mais</b> que no período "
        f"anterior. <b>Um ponto pede ação:</b> o {pior.ambiente}, com "
        f"{ui.numero(abs(pior.variacao_pct), 1)}% menos circulação.</div>",
        unsafe_allow_html=True)


def _numeros(periodo: str) -> None:
    k = sim.kpis(periodo)
    amb = sim.ambientes(periodo)
    maior = amb.loc[amb.passagens.idxmax()]
    pior = amb.loc[amb.variacao_pct.idxmin()]
    c1, c2, c3 = st.columns(3)
    with c1.container(border=True):
        st.metric("Passagens no período", ui.numero(k["passagens"]), f"+{ui.numero(k['passagens_var'], 1)}%")
    with c2.container(border=True):
        st.metric("Pede ação", pior.ambiente, f"{ui.numero(pior.variacao_pct, 1)}% de circulação")
    with c3.container(border=True):
        st.metric("Maior movimento", maior.ambiente, f"{ui.numero(maior.passagens)} passagens", delta_color="off")


def _o_que_fazer() -> None:
    st.markdown("#### O que fazer agora")
    for d in sim.DIAGNOSTICOS:
        with st.container(border=True):
            c1, c2 = st.columns([4, 1.3])
            with c1:
                st.markdown(f"{ui.chip(d['nivel'], d['cor'])} **{d['titulo']}**", unsafe_allow_html=True)
                st.caption(d["recomendacao"])
            with c2:
                rot, val = d["metricas"][1]
                st.markdown(f"<div style='text-align:right'><div style='font-size:1.4rem;font-weight:700'>{val}"
                            f"</div><div style='font-size:.75rem;opacity:.7'>{rot}</div></div>",
                            unsafe_allow_html=True)
    ui.link_pagina("diagnosticos", "Ver diagnósticos e planos de ação →")


def _onde(periodo: str) -> None:
    st.markdown("#### Onde está o movimento")
    ui.mostrar_planta(sim.regioes(periodo), [], "Somente mapa de calor", compacto=True)
    st.markdown("<div class='f360-grad-mini'></div><div style='display:flex;justify-content:space-between;"
                "font-size:.8rem;opacity:.75'><span>pouco movimento</span><span>muito movimento</span></div>",
                unsafe_allow_html=True)
    ui.link_pagina("mapa", "Abrir o mapa completo (horários e trajetos) →")


def render():
    periodo = ui.cabecalho("Central de decisões", "Do movimento à decisão.",
                           "Como está o movimento, o que pede ação e onde.")
    st.markdown("<style>.f360-grad-mini{height:10px;border-radius:5px;margin-top:.3rem;"
                "background:linear-gradient(90deg,#3b6fb6,#4fb39a,#f2c94c,#f2994a,#d64541);}</style>",
                unsafe_allow_html=True)
    _resumo(periodo)
    _numeros(periodo)
    st.markdown("")
    esq, dir_ = st.columns([3, 2], gap="large")
    with esq:
        _o_que_fazer()
    with dir_:
        _onde(periodo)

    st.divider()
    execucoes = dados_reais.listar_execucoes()
    if execucoes:
        c1, c2 = st.columns([3, 2])
        c1.caption("Dados simulados para demonstração. Hipóteses não comprovam causas. "
                   "Há também uma análise de vídeo real da Praça de Eventos do Capim Dourado.")
        with c2:
            ui.link_pagina("como_funciona", "Ver a análise do vídeo real →")
    else:
        st.caption("Dados simulados para demonstração. Hipóteses não comprovam causas.")

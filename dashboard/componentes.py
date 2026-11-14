"""Peças visuais reutilizadas pelas páginas: estilo, cabeçalho, KPIs, cartões, mapa e gráficos."""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyArrowPatch, Rectangle  # noqa: E402
import streamlit as st  # noqa: E402

import dados_simulados as sim  # noqa: E402

CSS = """
<style>
.block-container {padding-top: 2rem; max-width: 1200px;}
.f360-rotulo {font-size: .75rem; letter-spacing: .12em; text-transform: uppercase; opacity: .65;}
.f360-titulo {font-size: 2.3rem; font-weight: 700; line-height: 1.15; margin: .2rem 0 .6rem 0;}
.f360-sub {font-size: 1.05rem; opacity: .8; max-width: 760px;}
.f360-marca {font-size: .8rem; opacity: .5; text-align: right;}
.f360-aviso {font-size: .8rem; opacity: .75; border-left: 3px solid rgba(128,128,128,.5); padding: .3rem .7rem; margin: .8rem 0;}
.f360-chip {display: inline-block; font-size: .72rem; font-weight: 600; padding: .15rem .55rem;
            border-radius: 999px; color: #fff; margin-right: .4rem;}
.f360-kpi-valor {font-size: 2rem; font-weight: 700; line-height: 1.1;}
.f360-kpi-rotulo {font-size: .8rem; opacity: .65; text-transform: uppercase; letter-spacing: .06em;}
.f360-kpi-delta {font-size: .85rem; opacity: .8;}
.f360-legenda span {display: inline-block; width: 14px; height: 14px; border-radius: 3px;
                    vertical-align: middle; margin: 0 .3rem 0 .9rem;}
</style>
"""


def estilo() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


def cabecalho(rotulo: str, titulo: str, texto: str, chave_periodo: str = "periodo") -> str:
    """Título da página + seletor de período (compartilhado entre as páginas)."""
    estilo()
    tour_guiado()
    c1, c2 = st.columns([4, 1])
    with c1:
        st.markdown(f"<div class='f360-rotulo'>{rotulo} · {sim.SHOPPING}</div>"
                    f"<div class='f360-titulo'>{titulo}</div><div class='f360-sub'>{texto}</div>",
                    unsafe_allow_html=True)
    with c2:
        st.markdown("<div class='f360-marca'>SC / 01</div>", unsafe_allow_html=True)
    if rotulo in _CHAVE_PAGINA:
        import onboarding
        onboarding.ajuda_da_pagina(_CHAVE_PAGINA[rotulo])
    opcoes = list(sim.PERIODOS)
    atual = st.session_state.get(chave_periodo, "Hoje")
    periodo = st.radio("Período analisado · dados simulados", opcoes, index=opcoes.index(atual),
                       horizontal=True, key=f"_{chave_periodo}_{rotulo}")
    st.session_state[chave_periodo] = periodo
    return periodo


def tour_guiado() -> None:
    """Tour guiado de onboarding (ver onboarding.py)."""
    return                          # o tour abre em janela (onboarding.mostrar_se_preciso)


_CHAVE_PAGINA = {"Central de decisões": "visao_geral", "Mapa de movimentação": "mapa",
                 "Análise de ambientes": "ambientes", "Diagnósticos e oportunidades": "diagnosticos",
                 "Recomendações · Plano de ação": "recomendacoes", "Relatórios": "relatorios"}


def numero(v: float, casas: int = 0) -> str:
    """Formato brasileiro: 12.480 / 18,6."""
    s = f"{v:,.{casas}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def kpi_cartoes(periodo: str) -> None:
    k = sim.kpis(periodo)
    itens = [("Passagens detectadas", numero(k["passagens"]), f"+{numero(k['passagens_var'], 1)}% vs. período anterior"),
             ("Ambientes monitorados", f"{k['ambientes']:02d}", "100% de cobertura simulada"),
             ("Oportunidades identificadas", f"{k['oportunidades']:02d}", "potencial de melhoria"),
             ("Alertas ativos", f"{k['alertas']:02d}", "precisam de atenção")]
    for col, (rot, val, delta) in zip(st.columns(4), itens):
        with col:
            with st.container(border=True):
                st.markdown(f"<div class='f360-kpi-rotulo'>{rot}</div><div class='f360-kpi-valor'>{val}</div>"
                            f"<div class='f360-kpi-delta'>{delta}</div>", unsafe_allow_html=True)


def aviso(texto: str) -> None:
    st.markdown(f"<div class='f360-aviso'>{texto}</div>", unsafe_allow_html=True)


def chip(texto: str, cor: str) -> str:
    return f"<span class='f360-chip' style='background:{cor}'>{texto}</span>"


def link_pagina(chave: str, rotulo: str) -> None:
    """Link para outra página do painel (as páginas ficam em session_state['paginas'])."""
    pagina = st.session_state.get("paginas", {}).get(chave)
    if pagina is not None:
        st.page_link(pagina, label=rotulo)


def cartao_diagnostico(d: dict, completo: bool = True) -> None:
    with st.container(border=True):
        st.markdown(f"{chip(d['nivel'], d['cor'])}<span class='f360-rotulo'>{d['n']} · análise demonstrativa</span>",
                    unsafe_allow_html=True)
        st.markdown(f"#### {d['titulo']}")
        st.write(d["resumo"])
        for col, (rot, val) in zip(st.columns(len(d["metricas"])), d["metricas"]):
            col.metric(rot, val)
        st.markdown(f"**Recomendação:** {d['recomendacao']}")
        if completo:
            with st.expander("Hipóteses e potencial"):
                st.markdown(f"**Hipóteses a verificar no local:** {d['hipoteses']}")
                st.markdown(f"**Potencial:** {d['potencial']}")
        c1, c2 = st.columns(2)
        with c1:
            link_pagina("recomendacoes", "Ver plano de ação →")
        with c2:
            link_pagina("ambientes", "Investigar dados →")


def grafico(fig) -> None:
    """``st.plotly_chart`` ocupando a largura, em versões novas e antigas do Streamlit."""
    try:
        st.plotly_chart(fig, width="stretch")
    except TypeError:
        st.plotly_chart(fig, use_container_width=True)


# ------------------------------------------------------------- planta esquemática
# coordenadas (x0, y0, x1, y1) numa planta de 100 x 62; os trajetos correm na faixa y = 30,5
_RET = {
    "entrada": (44, 2, 56, 16), "juncao": (42, 16, 58, 32),
    "a_final": (8, 18, 20, 28), "a_centro": (20, 18, 31, 28), "a_inicio": (31, 18, 42, 28),
    "b_inicio": (58, 18, 69, 28), "b_centro": (69, 18, 80, 28), "b_final": (80, 18, 92, 28),
    "alimentacao": (8, 38, 38, 58), "convivencia": (62, 38, 92, 58),
}
_TRAJETOS = {
    ("entrada", "juncao"): ((50, 16.3), (50, 28.8)),
    ("juncao", "corredor_a"): ((43, 30.5), (27, 30.5)),
    ("juncao", "corredor_b"): ((57, 30.5), (73, 30.5)),
    ("corredor_a", "alimentacao"): ((22, 30.5), (22, 37.6)),
    ("corredor_b", "convivencia"): ((78, 30.5), (78, 37.6)),
    ("corredor_a", "saida_oeste"): ((9, 30.5), (2.2, 30.5)),
    ("corredor_b", "saida_leste"): ((91, 30.5), (97.8, 30.5)),
}
# lojas, com aberturas (acessos) onde os trajetos sobem para alimentação e convivência
_LOJAS = [(8, 33, 18, 36), (26, 33, 38, 36), (62, 33, 74, 36), (82, 33, 92, 36),
          (8, 4, 42, 16), (58, 4, 92, 16), (40, 34, 60, 58)]


def figura_planta(regioes_df, transicoes_lista, modo: str = "Mapa de calor + trajetos", compacto: bool = False):
    """Planta esquemática do piso térreo com regiões coloridas por intensidade e setas de fluxo.

    ``compacto``: versão para miniatura (Visão geral): só as cores e os nomes dos ambientes, letras maiores.
    """
    if compacto:
        return _planta_compacta(regioes_df)
    fig, ax = plt.subplots(figsize=(10, 6.2), dpi=120)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 62)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.add_patch(Rectangle((1, 1), 98, 60, fill=False, ec="#9ca3af", lw=1.2))
    for x0, y0, x1, y1 in _LOJAS:
        ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fc="#eef0f3", ec="#c9ced6", lw=0.8))
    ax.text(50, 46, "Lojas", ha="center", va="center", fontsize=8, color="#9ca3af")
    calor = modo != "Somente trajetos"
    trajetos = modo != "Somente mapa de calor"
    info = regioes_df.set_index("id")
    for rid, (x0, y0, x1, y1) in _RET.items():
        xm, ym = (x0 + x1) / 2, (y0 + y1) / 2
        if rid == "juncao":
            ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fc="#ffffff", ec="#9ca3af", lw=0.8, ls="--"))
            ax.text(45.6, 22, "Junção", ha="center", fontsize=7, color="#6b7280")
            continue
        r = info.loc[rid]
        cor = sim.CORES_NIVEL[r.intensidade] if calor else "#ffffff"
        ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fc=cor, alpha=0.85 if calor else 1, ec="#4b5563", lw=0.8))
        nome = (r.regiao.replace("Corredor A · ", "A · ").replace("Corredor B · ", "B · ")
                .replace("trecho central", "centro").replace("Praça de ", "Praça de\n")
                .replace("Área de ", "Área de\n").replace("Entrada Principal", "Entrada\nPrincipal"))
        ax.text(xm, ym + 1.8, nome, ha="center", va="center", fontsize=6.8, color="#111827")
        ax.text(xm, ym - 2.2, numero(r.passagens), ha="center", va="center", fontsize=8.5,
                fontweight="bold", color="#111827")
    ax.text(3, 25, "Saída\noeste", ha="center", fontsize=6.5, color="#6b7280")
    ax.text(97, 25, "Saída\nleste", ha="center", fontsize=6.5, color="#6b7280")
    if trajetos and transicoes_lista:
        vmax = max(v for _, _, v in transicoes_lista)
        for a, b, v in transicoes_lista:
            (xa, ya), (xb, yb) = _TRAJETOS[(a, b)]
            ax.add_patch(FancyArrowPatch((xa, ya), (xb, yb), arrowstyle="-|>", mutation_scale=11,
                                         lw=0.8 + 4 * v / vmax, color="#111827", alpha=0.6))
            if ya == yb:
                pos, ha = ((xa + xb) / 2, ya + 2.1), "center"
            else:
                pos, ha = (xa + 1.6, (ya + yb) / 2 + (3 if a == "entrada" else 0)), "left"
            ax.text(*pos, numero(v), fontsize=6.8, ha=ha, va="center", color="#111827",
                    bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="none", alpha=0.85))
    fig.tight_layout()
    return fig


def _planta_compacta(regioes_df):
    fig, ax = plt.subplots(figsize=(6.4, 4.0), dpi=150)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 62)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.add_patch(Rectangle((1, 1), 98, 60, fill=False, ec="#9ca3af", lw=1))
    for x0, y0, x1, y1 in _LOJAS:
        ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fc="#eef0f3", ec="#d5d9df", lw=0.6))
    info = regioes_df.set_index("id")
    for rid, (x0, y0, x1, y1) in _RET.items():
        if rid == "juncao":
            continue
        cor = sim.CORES_NIVEL[info.loc[rid].intensidade]
        ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fc=cor, alpha=0.9, ec="white", lw=1.2))
    rotulos = [(50, 9, "Entrada"), (23, 48, "Alimentação"), (77, 48, "Convivência"),
               (25, 23, "Corredor A"), (75, 23, "Corredor B")]
    for x, y, t in rotulos:
        ax.text(x, y, t, ha="center", va="center", fontsize=9.5, fontweight="bold", color="#111827")
    fig.tight_layout(pad=0.2)
    return fig


def mostrar_planta(regioes_df, transicoes_lista, modo: str, compacto: bool = False) -> None:
    fig = figura_planta(regioes_df, transicoes_lista, modo, compacto)
    st.pyplot(fig)
    plt.close(fig)          # libera a memória a cada atualização da página


def legenda_niveis() -> None:
    itens = "".join(f"<span style='background:{c}'></span>{n}" for n, c in sim.CORES_NIVEL.items())
    st.markdown(f"<div class='f360-legenda' style='font-size:.85rem'>{itens}</div>", unsafe_allow_html=True)

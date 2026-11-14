"""05 · Recomendações — planos de ação, acompanhamento e simulador."""
from datetime import date
from pathlib import Path

import pandas as pd
import streamlit as st

import componentes as ui
import dados_simulados as sim
import graficos

ARQ_ACOMPANHAMENTO = Path("data/acompanhamento/planos.csv")
CORES = {"Prioridade alta": "#d64541", "Atenção": "#f2994a", "Oportunidade": "#4fb39a"}


def _carregar() -> pd.DataFrame:
    if ARQ_ACOMPANHAMENTO.is_file():
        try:
            return pd.read_csv(ARQ_ACOMPANHAMENTO)
        except (OSError, pd.errors.ParserError, pd.errors.EmptyDataError):
            pass
    return pd.DataFrame()


def _salvar(registro: dict) -> None:
    ARQ_ACOMPANHAMENTO.parent.mkdir(parents=True, exist_ok=True)
    df = pd.concat([_carregar(), pd.DataFrame([registro])], ignore_index=True)
    df.to_csv(ARQ_ACOMPANHAMENTO, index=False)


def _plano(p: dict, historico: pd.DataFrame):
    with st.container(border=True):
        st.markdown(f"{ui.chip(p['nivel'], CORES[p['nivel']])}<span class='f360-rotulo'>Plano {p['n']}</span>",
                    unsafe_allow_html=True)
        st.markdown(f"#### {p['tema']}")
        st.markdown(f"**Ação sugerida:** {p['acao']}")
        c1, c2 = st.columns(2)
        c1.metric(p["indicador"], f"{p['referencia']} {p['unidade']}", help="Referência simulada")
        c2.markdown(f"**Como comparar:** {p['comparar']}")
        with st.form(f"form_{p['n']}", clear_on_submit=True):
            st.markdown("**Acompanhamento**")
            f1, f2, f3 = st.columns(3)
            situacao = f1.selectbox("Situação", ["Planejada", "Em andamento", "Executada"])
            data_exec = f2.date_input("Data de execução", value=date.today())
            antes = f3.number_input(f"Antes ({p['unidade']})", min_value=0.0, value=float(p["referencia"]))
            g1, g2, g3 = st.columns(3)
            depois = g1.number_input(f"Depois ({p['unidade']})", min_value=0.0, value=0.0)
            inicio = g2.date_input("Início da comparação", value=date.today())
            fim = g3.date_input("Fim da comparação", value=date.today())
            obs = st.text_area("Observações e condições da comparação", height=70)
            if st.form_submit_button("Salvar acompanhamento"):
                _salvar({"plano": p["n"], "tema": p["tema"], "situacao": situacao, "data_execucao": data_exec,
                         "antes": antes, "depois": depois, "unidade": p["unidade"], "inicio": inicio,
                         "fim": fim, "observacoes": obs})
                st.success("Acompanhamento salvo em data/acompanhamento/planos.csv")
        if not historico.empty and "plano" in historico:
            reg = historico[historico.plano.astype(str).str.zfill(2) == p["n"]]
            if not reg.empty:
                st.dataframe(reg.drop(columns=["plano", "tema"], errors="ignore"), hide_index=True)
        st.caption("Valores informados pelo gestor, sem medição automática.")


def render():
    ui.cabecalho("Recomendações · Plano de ação", "O próximo movimento começa com uma decisão.",
                 "Explore ações estratégicas e compare cenários para o aproveitamento dos espaços.")
    historico = _carregar()
    st.markdown("### Planos de ação")
    for p in sim.PLANOS:
        _plano(p, historico)

    st.markdown("### Explorar cenários simulados · Corredor B")
    st.markdown("**Oportunidade 01: aumentar a atratividade do Corredor B.**")
    c1, c2 = st.columns([2, 3])
    with c1:
        st.selectbox("Ação sugerida", ["Ativação comercial temporária", "Melhoria da sinalização",
                                       "Evento e experiência de marca"], key="sim_acao")
        antes = st.slider("Antes da intervenção (passagens/h)", 0, 200, 80, key="sim_antes")
        depois = st.slider("Após a intervenção (passagens/h)", 0, 200, 110, key="sim_depois")
        var = (depois - antes) / antes * 100 if antes else 0.0
        st.metric("Variação", f"{'+' if var >= 0 else '−'}{ui.numero(abs(var))}%",
                  f"{depois - antes:+d} passagens por hora")
    with c2:
        ui.grafico(graficos.simulador(antes, depois, "passagens/h"))
    ui.aviso("Cenário fictício: os números não constituem previsão, promessa ou evidência de impacto real.")
    st.markdown("**Uma ação. Novas possibilidades.** Teste a ativação num período delimitado e compare com uma "
                "referência equivalente. Acompanhe: passagens por hora, permanência, distribuição entre ambientes e "
                "dias equivalentes.")
    st.warning("Antes de decidir: valide as hipóteses com observação no local. O fluxo, sozinho, não explica a causa.")
    ui.link_pagina("mapa", "Explorar o ambiente →")

    st.markdown("### Outras ações para explorar")
    st.markdown("- **Reorganizar os acessos à Praça de Alimentação** — avaliar a concentração no almoço\n"
                "- **Programação cultural na Área de Convivência** — investigar experiências e eventos temporários")
    ui.link_pagina("diagnosticos", "Ver diagnósticos →")

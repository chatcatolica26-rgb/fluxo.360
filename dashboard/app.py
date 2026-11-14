"""FLUXO360 — painel de decisões (Streamlit).

Rode a partir da raiz do projeto:
    streamlit run dashboard/app.py

Os números das páginas são SIMULADOS (iguais à apresentação). A aba "Vídeo real"
do Mapa de movimentação mostra os resultados de ``python -m src.experiments.run_shopping``.
"""
import streamlit as st

st.set_page_config(page_title="FLUXO360 — Do movimento à decisão", layout="wide",
                   initial_sidebar_state="expanded")

import onboarding  # noqa: E402
from paginas import ambientes, como_funciona, diagnosticos, mapa, recomendacoes, relatorios, visao_geral  # noqa: E402

paginas = {
    "visao_geral": st.Page(visao_geral.render, title="01  Visão geral", url_path="visao-geral", default=True),
    "mapa": st.Page(mapa.render, title="02  Mapa de movimentação", url_path="mapa"),
    "ambientes": st.Page(ambientes.render, title="03  Análise de ambientes", url_path="ambientes"),
    "diagnosticos": st.Page(diagnosticos.render, title="04  Diagnósticos e oportunidades", url_path="diagnosticos"),
    "recomendacoes": st.Page(recomendacoes.render, title="05  Recomendações", url_path="recomendacoes"),
    "relatorios": st.Page(relatorios.render, title="06  Relatórios", url_path="relatorios"),
    "como_funciona": st.Page(como_funciona.render, title="07  Como funciona", url_path="como-funciona"),
}
st.session_state["paginas"] = paginas
onboarding.iniciar()

with st.sidebar:
    st.markdown("### FLUXO360")
    st.caption("Do movimento à decisão · Inteligência espacial e fluxo de visitantes")

navegacao = st.navigation(list(paginas.values()), position="sidebar")

with st.sidebar:
    st.divider()
    st.button("Guia rápido", type="primary", help="Explica a plataforma em 5 passos",
              on_click=onboarding.abrir_tour)
    st.markdown("**Gestor do Shopping**  \nAdministrador")
    st.caption("Shopping Central · São Paulo, SP  \nEmpreendimento demonstrativo · Estudo espacial / 2026")
    st.caption("PROTÓTIPO · HACKATHON — dados simulados para demonstração")

destino = st.session_state.pop("ir_para", None)          # atalho escolhido no tour
if destino in paginas:
    st.switch_page(paginas[destino])
onboarding.mostrar_se_preciso()
navegacao.run()

with st.sidebar:
    st.divider()
    onboarding.barra_lateral()

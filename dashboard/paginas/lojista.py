"""Para o lojista: o que fazer na loja com base no movimento em frente a ela."""
import streamlit as st

import componentes as ui
import dados_simulados as sim
import graficos
import insights


def render():
    periodo = ui.cabecalho("Para o lojista", "Venda mais com o mesmo espaço.",
                           "Saiba quando e por onde o cliente passa em frente à sua loja, e o que fazer com isso.")
    ambiente = st.selectbox("Onde fica a sua loja?", list(sim.AMBIENTES.ambiente), index=2, key="loj_amb")
    recs = insights.lojista(ambiente, periodo)

    st.markdown(f"#### {len(recs)} recomendações para a sua loja")
    c1, c2 = st.columns(2)
    for k, r in enumerate(recs):
        with (c1 if k % 2 == 0 else c2):
            ui.cartao_insight(r)

    st.markdown("#### Movimento em frente à sua loja ao longo do dia")
    serie = sim.fluxo_por_hora(periodo, ambiente)
    ini, fim, _ = insights.janela_de_pico(serie["Período selecionado"])
    ui.grafico(graficos.fluxo_horario_destaque(serie, ini, fim, "reforçar equipe e caixas"))
    st.caption("Recomendações geradas automaticamente pelo FLUXO360 a partir do fluxo de pessoas. "
               "Nesta demonstração, os números são simulados.")

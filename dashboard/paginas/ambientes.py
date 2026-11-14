"""03 · Análise de ambientes."""
import streamlit as st

import componentes as ui
import dados_simulados as sim
import graficos


def render():
    periodo = ui.cabecalho("Análise de ambientes", "Um olhar mais próximo de cada ambiente.",
                           "Compare padrões de circulação e o papel de cada espaço na jornada dos visitantes.")
    df = sim.ambientes(periodo)
    st.markdown(f"**Ambientes monitorados: {len(df):02d}**")
    filtro = st.radio("Ambiente", ["Todos"] + list(df.ambiente), horizontal=True, key="amb_filtro")
    vis = df if filtro == "Todos" else df[df.ambiente == filtro]

    tabela = vis.assign(
        **{"#": [f"{i:02d}" for i in vis.index + 1],
           "Passagens": vis.passagens.map(ui.numero),
           "Variação": vis.variacao_pct.map(lambda v: f"{'+' if v > 0 else '−'}{ui.numero(abs(v), 1)}%"),
           "Pico": vis.pico_h.map(lambda h: f"{h}h"),
           "Permanência": vis.permanencia_min.map(lambda m: f"{m} min")}
    ).rename(columns={"ambiente": "Ambiente", "intensidade": "Intensidade"})
    st.dataframe(tabela[["#", "Ambiente", "Passagens", "Variação", "Intensidade", "Pico", "Permanência"]],
                 hide_index=True)

    st.markdown("#### Comportamento ao longo do dia")
    st.caption("Evolução do fluxo por horário · dados simulados")
    ui.grafico(graficos.fluxo_horario(sim.fluxo_por_hora(periodo, filtro)))

    st.markdown("#### Distribuição espacial")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Fluxo por ambiente**")
        ui.grafico(graficos.fluxo_por_ambiente(df))
    with c2:
        st.markdown("**Participação dos ambientes**")
        ui.grafico(graficos.participacao(df))
    ui.aviso("Dados simulados para demonstração. Passagens não equivalem a visitantes únicos.")

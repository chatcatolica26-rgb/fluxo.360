"""06 · Relatórios — visão consolidada e exportação."""
from datetime import date

import pandas as pd
import streamlit as st

import componentes as ui
import dados_reais
import dados_simulados as sim
import graficos


def _csv(periodo: str) -> bytes:
    amb = sim.ambientes(periodo).assign(tipo="ambiente")
    reg = sim.regioes(periodo).rename(columns={"regiao": "nome"}).assign(tipo="regiao")
    hora = sim.fluxo_por_hora(periodo).assign(tipo="hora")
    df = pd.concat([amb.rename(columns={"ambiente": "nome"}), reg, hora], ignore_index=True)
    df.insert(0, "periodo", periodo)
    df.insert(1, "fonte", "simulado")
    return df.to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig")


def render():
    periodo = ui.cabecalho("Relatórios", "Inteligência pronta para compartilhar.",
                           "Visão consolidada do movimento, dos sinais e das oportunidades.")
    c1, c2 = st.columns([3, 1])
    c1.markdown(f"**Período:** {periodo} · {date.today():%d/%m/%Y}")
    c2.download_button("Exportar relatório CSV", _csv(periodo), file_name=f"fluxo360_{periodo.lower()}.csv",
                       mime="text/csv")
    ui.kpi_cartoes(periodo)

    df = sim.ambientes(periodo)
    maior = df.loc[df.passagens.idxmax(), "ambiente"]
    st.markdown("### Resumo executivo")
    st.write(f"Os cinco ambientes somaram {ui.numero(int(df.passagens.sum()))} passagens na simulação. "
             f"A {maior} tem o maior fluxo, e o Corredor B mostra oportunidade de ativação.")
    for t, d in (("1. Oportunidade de ativação", "investigar a baixa circulação do Corredor B."),
                 ("2. Atenção aos acessos", "avaliar a concentração na Praça de Alimentação."),
                 ("3. Potencial de experiências", "explorar ações na Área de Convivência.")):
        st.markdown(f"**{t}:** {d}")

    c1, c2 = st.columns([3, 2])
    with c1:
        st.markdown("#### Evolução do fluxo por horário")
        amb = st.selectbox("Ambiente", ["Todos"] + list(sim.AMBIENTES.ambiente), key="rel_amb")
        ui.grafico(graficos.fluxo_horario(sim.fluxo_por_hora(periodo, amb)))
    with c2:
        st.markdown("#### Fluxo por ambiente")
        ui.grafico(graficos.fluxo_por_ambiente(df))

    execucoes = dados_reais.listar_execucoes()
    if execucoes:
        st.markdown("### Análises de vídeo real")
        linhas = []
        for e in execucoes:
            c = e.info.get("contagens", {})
            linhas.append({"Análise": e.nome, "Duração (s)": e.info.get("duracao_analisada_s"),
                           "Ids rastreados": c.get("pessoas_unicas_na_area"),
                           "Trajetórias": c.get("trajetorias_registradas"),
                           "Detecções": c.get("deteccoes_total"),
                           "Erro calibração (m)": e.info.get("calibracao", {}).get("erro_medio_m")})
        tab = pd.DataFrame(linhas)
        st.dataframe(tab, hide_index=True)
        st.download_button("Exportar análises de vídeo (CSV)",
                           tab.to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig"),
                           file_name="fluxo360_videos.csv", mime="text/csv")
    ui.aviso("Relatório de um protótipo. Os dados de ambientes e diagnósticos são demonstrativos; só a seção "
             "\"Análises de vídeo real\" vem de processamento de vídeo.")

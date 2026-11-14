"""01 · Visão geral — central de decisões."""
import streamlit as st

import componentes as ui
import dados_reais
import dados_simulados as sim


def render():
    periodo = ui.cabecalho("Central de decisões", "Do movimento à decisão.",
                           "O Corredor B pede ação. A alimentação merece acompanhamento. "
                           "A convivência abre novas possibilidades.")

    execucoes = dados_reais.listar_execucoes()
    if execucoes:
        e = execucoes[0]
        c = e.info.get("contagens", {})
        st.success(f"**Análise de vídeo real disponível:** Praça de Eventos, Capim Dourado Shopping — "
                   f"{e.info.get('duracao_analisada_s', 0):.0f} s de vídeo, {c.get('trajetorias_registradas', '?')} "
                   "trajetórias projetadas na planta oficial.")
        c1, c2 = st.columns(2)
        with c1:
            ui.link_pagina("mapa", "Ver mapa de calor do vídeo →")
        with c2:
            ui.link_pagina("como_funciona", "Ver como a análise foi feita →")

    st.markdown("### Resultados da inteligência FLUXO360")
    st.caption("3 situações priorizadas")
    for col, d in zip(st.columns(3), sim.DIAGNOSTICOS):
        with col:
            ui.cartao_diagnostico(d, completo=False)
    ui.aviso("Conclusões de um estudo simulado. Hipóteses não comprovam causas; projeções não garantem resultados.")

    st.markdown("### Evidências da análise")
    st.caption("O movimento que sustenta as decisões")
    ui.kpi_cartoes(periodo)
    ui.link_pagina("ambientes", "Análise detalhada →")

    st.markdown("### Inteligência espacial — Cartografia do movimento")
    c1, c2 = st.columns(2)
    janela = c1.radio("Horário", list(sim.JANELAS), horizontal=True, key="vg_janela")
    modo = c2.radio("Visualização", ["Somente mapa de calor", "Somente trajetos", "Mapa de calor + trajetos"],
                    index=2, horizontal=True, key="vg_modo")
    reg = sim.regioes(periodo, janela)
    ui.mostrar_planta(reg, sim.transicoes(periodo, janela), modo)
    ui.legenda_niveis()
    st.markdown(f"**{ui.numero(int(reg.passagens.sum()))} passagens** acumuladas em 9 regiões de 5 ambientes "
                f"· piso térreo · {janela.lower()}")
    ui.aviso("A cor representa a intensidade relativa, não pessoas por m². Dados simulados, sem câmeras nem planta "
             "calibrada; não representam lotação real. Passagens não equivalem a visitantes únicos.")

"""Para a administração do shopping: quiosques, preço do espaço, pontos mortos e como aquecê-los."""
import streamlit as st

import componentes as ui
import dados_reais
import dados_simulados as sim
import insights


def render():
    periodo = ui.cabecalho("Para a administração", "Cada metro do shopping rendendo mais.",
                           "Onde colocar quiosques, quanto vale cada ponto, onde estão os pontos mortos e "
                           "como aquecê-los.")
    mortos = insights.pontos_mortos(periodo)
    vp = insights.valor_do_ponto(periodo)
    recs = insights.administracao(periodo)
    quiosque = next((r for r in recs if r["tema"] == "Quiosques"), None)

    c1, c2, c3 = st.columns(3)
    with c1.container(border=True):
        st.metric("Pontos mortos", len(mortos), help="Regiões com menos de 2% das passagens do piso")
    with c2.container(border=True):
        st.metric("Melhor ponto para quiosque",
                  quiosque["titulo"].split(": ")[1].split(" e ")[0] if quiosque else "—")
    with c3.container(border=True):
        st.metric("Faixa de preço Premium", f"{(vp.Faixa == 'Premium').sum()} regiões",
                  help="Regiões com fluxo 1,5 vez acima da média ou mais")

    esq, dir_ = st.columns([3, 2], gap="large")
    with esq:
        st.markdown(f"#### {len(recs)} recomendações para a administração")
        for r in recs:
            ui.cartao_insight(r)
    with dir_:
        st.markdown("#### Pontos quentes e frios do piso")
        ui.mostrar_planta(sim.regioes(periodo), [], "Somente mapa de calor", compacto=True)
        st.caption("Azul = ponto frio · vermelho = ponto quente")
        st.markdown("#### Quanto vale cada ponto")
        tabela = vp.assign(**{"Participação": vp["Participação"].map(lambda v: f"{100 * v:.1f}%".replace(".", ",")),
                              "Multiplicador sugerido": vp["Multiplicador sugerido"].map(lambda v: f"{v:.1f}×".replace(".", ","))})
        st.dataframe(tabela[["Região", "Participação", "Faixa", "Multiplicador sugerido"]], hide_index=True)
        st.caption("Multiplicador sobre o valor-base de locação ou mídia. Referência inicial: combine com o "
                   "mercado e o mix de lojas.")

    execs = dados_reais.listar_execucoes()
    achados = insights.achados_video(execs[0]) if execs else []
    if achados:
        st.markdown("#### No vídeo real da Praça de Eventos")
        c1, c2 = st.columns([3, 2])
        with c1:
            for a in achados:
                ui.cartao_insight(a)
        with c2:
            arq = execs[0].arquivo("mapa_permanencia_rastros.png") or execs[0].arquivo("mapa_permanencia_sobreposto.png")
            if arq:
                st.image(str(arq), caption="Mapa de calor com o rastro das pessoas (10 s de vídeo)")
    st.caption("Recomendações geradas automaticamente pelo FLUXO360 a partir do fluxo de pessoas. "
               "Nas regiões, os números são simulados; o bloco do vídeo usa a análise real.")

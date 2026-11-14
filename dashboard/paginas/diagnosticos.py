"""04 · Diagnósticos e oportunidades."""
import streamlit as st

import componentes as ui
import dados_simulados as sim


def render():
    ui.cabecalho("Diagnósticos e oportunidades", "Onde agir. O que investigar.",
                 "Situações priorizadas, com as evidências e as recomendações de cada uma.")
    for d in sim.DIAGNOSTICOS:
        ui.cartao_diagnostico(d, completo=True)
    ui.aviso("Conclusões de um estudo simulado. Hipóteses não comprovam causas; projeções não garantem resultados.")

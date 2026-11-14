"""07 · Como funciona — demonstração do método, com as imagens da análise real mais recente."""
from pathlib import Path

import streamlit as st

import componentes as ui
import dados_reais


def _img(execucao, nome: str, legenda: str | None = None) -> None:
    arq = execucao.arquivo(nome)
    if arq:
        st.image(str(arq), caption=legenda)
    else:
        st.caption(f"({nome} não encontrado nesta análise)")


def _passo(n: int, titulo: str, texto: str) -> None:
    st.markdown(f"<div class='f360-rotulo'>Etapa {n:02d}</div>", unsafe_allow_html=True)
    st.markdown(f"#### {titulo}")
    st.write(texto)


def render():
    ui.estilo()
    ui.tour_guiado()
    st.markdown("<div class='f360-rotulo'>Como funciona · método</div>"
                "<div class='f360-titulo'>Do vídeo ao mapa de calor.</div>"
                "<div class='f360-sub'>As seis etapas da análise de fluxo, mostradas com o vídeo real da "
                "Praça de Eventos do Capim Dourado Shopping e a planta oficial do piso térreo.</div>",
                unsafe_allow_html=True)
    import onboarding
    onboarding.ajuda_da_pagina("como_funciona")
    execucoes = dados_reais.listar_execucoes()
    if not execucoes:
        st.info("Nenhuma análise de vídeo encontrada em data/processed/shopping. "
                "Rode `python -m src.experiments.run_shopping` (ou `python tools/analise_demo_opencv.py`).")
        return
    e = st.selectbox("Análise usada na demonstração", execucoes, format_func=lambda x: x.rotulo, key="cf_exec")
    info, c = e.info, e.info.get("contagens", {})
    cal = info.get("calibracao", {})

    demo = e.arquivo("demo_apresentacao.mp4")
    if demo:
        st.markdown("### Resumo em 16 segundos")
        st.video(str(demo))
    st.divider()

    _passo(1, "Vídeo real como fonte",
           f"Câmera fixa, {info['video']['largura']}×{info['video']['altura']}, {info['video']['fps']:.0f} quadros por "
           f"segundo. Foram analisados {info['duracao_analisada_s']:.0f} s ({info['quadros_processados']} quadros). "
           "Cada quadro tem seu instante em segundos, usado depois na acumulação.")
    c1, c2 = st.columns([3, 2])
    with c1:
        _img(e, "calibracao_sobreposta.png", "Quadro do vídeo")
    with c2:
        _img(e, "localizacao_na_planta.png", "Onde fica a área filmada no piso térreo")

    _passo(2, "Calibração: o chão do vídeo ligado ao chão da planta",
           "Uma homografia (matriz 3×3) leva cada ponto do piso no vídeo para o mesmo ponto na planta oficial. "
           "Ela é calculada com pontos que aparecem nas duas imagens: vitrines, degraus, escada rolante e placas do "
           "piso. Para conferir, as linhas da planta são projetadas de volta no vídeo e precisam cair nas paredes "
           "reais (vermelho). Em azul, a área do piso analisada.")
    st.caption(f"Erro médio da calibração: {cal.get('erro_medio_m', '?')} m · "
               f"{'preliminar' if str(cal.get('status', '')).startswith('preliminar') else 'definitiva'}"
               + (f" · {cal.get('metodo')}" if cal.get("metodo") else ""))
    c1, c2 = st.columns([3, 2])
    with c1:
        _img(e, "calibracao_sobreposta.png", "Planta projetada no vídeo")
    with c2:
        _img(e, "planta_calibrada.png", "Pontos de calibração e área válida na planta")

    _passo(3, "Detecção e rastreamento de pessoas",
           "O detector encontra só pessoas (manequins e objetos parados são descartados) e o rastreador dá um "
           "número (id) a cada uma, mantendo-o enquanto ela é vista. O ponto verde é o pé: o centro da base da caixa, "
           "que é o ponto que toca o chão.")
    _img(e, "quadro_exemplo_deteccoes.png", f"Detector usado: {info.get('detector_usado', '')}")

    _passo(4, "Projeção na planta: as trajetórias",
           "O ponto dos pés de cada pessoa passa pela homografia e vira uma posição na planta, em metros. "
           "Ligando as posições de cada id ao longo do tempo, surgem as trajetórias.")
    c1, c2 = st.columns(2)
    with c1:
        _img(e, "trajetorias_planta.png", f"{c.get('trajetorias_registradas', '?')} trajetórias")
    with c2:
        v = e.arquivo("video_trajetorias_planta.mp4")
        if v:
            st.video(str(v))

    _passo(5, "Acumulação no tempo",
           "A planta é dividida em células de 0,5 m. A cada quadro, cada pessoa soma à sua célula o tempo que o quadro "
           "representa (1 / FPS). Assim, quem fica parado acumula mais, e o resultado não depende da taxa de quadros "
           "do vídeo. Uma segunda matriz conta quantas pessoas diferentes passaram por cada célula.")
    m = st.columns(4)
    m[0].metric("Posições na área", c.get("deteccoes_validas", "—"))
    m[1].metric("Trajetórias", c.get("trajetorias_registradas", "—"))
    m[2].metric("Tempo somado", f"{info.get('acumulacao', {}).get('permanencia_total_s', 0):.0f} s")
    m[3].metric("Célula", f"{info.get('acumulacao', {}).get('celula_m', 0.5)} m")

    _passo(6, "Mapa de calor e rastros",
           "As matrizes viram cores: azul onde houve pouca presença, vermelho onde houve mais. Por cima, as linhas "
           "finas são o caminho de cada pessoa, com uma seta para onde ela foi. A suavização é só visual; os números "
           "originais ficam salvos para outras análises.")
    rastros = st.toggle("Mostrar o rastro das pessoas", value=True, key="cf_rastros")
    c1, c2 = st.columns(2)
    for col, nome, legenda in ((c1, "permanencia", "Permanência (onde as pessoas ficaram)"),
                               (c2, "circulacao", "Circulação (por onde passaram)")):
        arquivo = f"mapa_{nome}_rastros.png" if rastros and e.arquivo(f"mapa_{nome}_rastros.png") \
            else f"mapa_{nome}_sobreposto.png"
        with col:
            _img(e, arquivo, legenda)

    st.divider()
    st.markdown("### Limites desta demonstração")
    limites = [f"Trecho curto ({info['duracao_analisada_s']:.0f} s): mostra o método, não o padrão de circulação "
               "do shopping. Conclusões pedem horas de vídeo, em dias e horários diferentes.",
               "Ids não são pessoas únicas: quando alguém some atrás de outra pessoa, pode voltar com outro número."]
    if "HOG" in str(info.get("detector_usado", "")):
        limites.append("Detector de demonstração (OpenCV HOG), usado por não haver YOLO no ambiente onde a análise "
                       "foi gerada. Ele perde pessoas em grupo e troca mais ids; a versão do projeto usa YOLO + "
                       "ByteTrack.")
    if str(cal.get("status", "")).startswith("preliminar"):
        limites.append(f"Calibração preliminar, feita a distância (erro médio de {cal.get('erro_medio_m')} m). "
                       "Deve ser refeita no local com a ferramenta de calibração.")
    for item in limites:
        st.markdown(f"- {item}")
    ui.link_pagina("mapa", "Ver os resultados no Mapa de movimentação →")

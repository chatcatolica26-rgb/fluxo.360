"""02 · Mapa de movimentação — cenário simulado e resultados reais do vídeo."""
from pathlib import Path

import pandas as pd
import streamlit as st

import componentes as ui
import dados_reais
import dados_simulados as sim
import graficos


def _simulado(periodo: str):
    ui.kpi_cartoes(periodo)
    st.markdown("#### Cartografia do movimento")
    c1, c2 = st.columns(2)
    janela = c1.radio("Horário", list(sim.JANELAS), horizontal=True, key="mp_janela")
    modo = c2.radio("Visualização", ["Somente mapa de calor", "Somente trajetos", "Mapa de calor + trajetos"],
                    index=2, horizontal=True, key="mp_modo")
    reg = sim.regioes(periodo, janela)
    ui.mostrar_planta(reg, sim.transicoes(periodo, janela), modo)
    ui.legenda_niveis()
    ui.aviso("Dados simulados, sem câmeras ou sensores; a planta não é calibrada. Passagens não equivalem a "
             "visitantes únicos.")

    st.markdown("#### O movimento tem pontos de atenção")
    st.caption(f"{ui.numero(int(reg.passagens.sum()))} passagens acumuladas · {janela}")
    tabela = reg[["regiao", "intensidade", "passagens"]].rename(
        columns={"regiao": "Região", "intensidade": "Intensidade", "passagens": "Passagens"})
    st.dataframe(tabela, hide_index=True)

    c1, c2 = st.columns([3, 2])
    with c1:
        st.markdown("#### Evolução do fluxo por horário")
        amb = st.selectbox("Ambiente", ["Todos"] + list(sim.AMBIENTES.ambiente), key="mp_amb")
        ui.grafico(graficos.fluxo_horario(sim.fluxo_por_hora(periodo, amb)))
    with c2:
        st.markdown("#### Fluxo por ambiente")
        ui.grafico(graficos.fluxo_por_ambiente(sim.ambientes(periodo)))
        ui.link_pagina("ambientes", "Ver análise de ambientes →")


def _pessoas_por_segundo(csv_path: Path) -> pd.DataFrame | None:
    try:
        t = pd.read_csv(csv_path)
    except (OSError, pd.errors.ParserError, pd.errors.EmptyDataError):
        return None
    if t.empty or "valida" not in t:
        return None
    t = t[t.valida.astype(str).str.lower() == "true"].copy()
    t["segundo"] = t.tempo_s.astype(float).astype(int)
    return t.groupby("segundo").id.nunique().rename("pessoas").reset_index()


def _video_real():
    execucoes = dados_reais.listar_execucoes()
    if not execucoes:
        st.info("Ainda não há análises de vídeo. Depois de calibrar a câmera, rode na raiz do projeto:\n\n"
                "`python -m src.experiments.run_shopping --fim 2` (teste curto) ou "
                "`python -m src.experiments.run_shopping` (vídeo inteiro).\n\n"
                "Os resultados aparecem aqui automaticamente.")
        return
    escolha = st.selectbox("Análise", execucoes, format_func=lambda e: e.rotulo, key="mp_exec")
    info = escolha.info
    c, cal, v = info.get("contagens", {}), info.get("calibracao", {}), info.get("video", {})
    m = st.columns(5)
    m[0].metric("Duração analisada", f"{info.get('duracao_analisada_s', 0):.1f} s")
    m[1].metric("Ids rastreados na área", c.get("pessoas_unicas_na_area", "—"),
                help="Cada trecho rastreado recebe um id; uma pessoa pode ter mais de um.")
    m[2].metric("Trajetórias", c.get("trajetorias_registradas", "—"))
    m[3].metric("Detecções usadas", f"{c.get('deteccoes_validas', '—')} de {c.get('deteccoes_total', '—')}")
    m[4].metric("Erro da calibração", f"{cal.get('erro_medio_m', '—')} m")
    st.caption(f"Vídeo {Path(v.get('fonte', '')).name} · {v.get('largura')}×{v.get('altura')} · "
               f"{v.get('fps', 0):.0f} FPS · piso {cal.get('piso', '—')} · {cal.get('pontos', '—')} pontos de calibração")
    avisos = []
    if "HOG" in str(info.get("detector_usado", "")):
        avisos.append("detector de demonstração (OpenCV HOG), não o YOLO")
    if str(cal.get("status", "")).startswith("preliminar"):
        avisos.append("calibração preliminar, a conferir no local")
    if avisos:
        st.warning("Atenção: " + "; ".join(avisos) + ". Ids gerados pelo rastreador não equivalem a pessoas únicas.")

    c1, c2 = st.columns(2)
    for col, nome, titulo in ((c1, "video_deteccoes.mp4", "Vídeo com detecções e ids"),
                              (c2, "video_trajetorias_planta.mp4", "Trajetórias na planta")):
        arq = escolha.arquivo(nome)
        if arq:
            with col:
                st.markdown(f"**{titulo}**")
                st.video(str(arq))

    tipo = st.radio("Mapa", ["Permanência (onde as pessoas ficaram)", "Circulação (por onde passaram)"],
                    horizontal=True, key="mp_tipo")
    chave = "permanencia" if tipo.startswith("Perman") else "circulacao"
    rastros = st.toggle("Mostrar o rastro das pessoas", value=True, key="mp_rastros",
                        help="Linha fina = caminho de cada pessoa; a seta mostra para onde ela foi.")
    c1, c2 = st.columns(2)
    sufixo_planta = "rastros" if rastros and escolha.arquivo(f"mapa_{chave}_rastros.png") else "sobreposto"
    for col, sufixo, titulo in ((c1, sufixo_planta, "Sobre a planta"), (c2, "isolado", "Mapa isolado")):
        arq = escolha.arquivo(f"mapa_{chave}_{sufixo}.png")
        with col:
            st.markdown(f"**{titulo}**")
            if arq:
                st.image(str(arq))
            else:
                st.caption("imagem não encontrada")
    if rastros and sufixo_planta == "sobreposto":
        st.caption("Esta análise ainda não tem os rastros. Gere com: `python tools/gerar_rastros.py`")

    serie = _pessoas_por_segundo(escolha.pasta / "trajetorias.csv")
    if serie is not None and not serie.empty:
        st.markdown("**Pessoas na área ao longo do vídeo**")
        ui.grafico(graficos.pessoas_no_tempo(serie))

    c1, c2 = st.columns(2)
    with c1:
        for nome, titulo in (("localizacao_na_planta.png", "Localização no piso térreo"),
                             ("calibracao_sobreposta.png", "Calibração: planta projetada no vídeo"),
                             ("planta_calibrada.png", "Pontos de calibração e área válida")):
            arq = escolha.arquivo(nome)
            if arq:
                st.markdown(f"**{titulo}**")
                st.image(str(arq))
    with c2:
        st.markdown("**Arquivos da análise**")
        for nome, rotulo in (("trajetorias.csv", "Trajetórias (CSV)"), ("relatorio.md", "Relatório"),
                             ("video_deteccoes.mp4", "Vídeo com detecções e ids"),
                             ("video_trajetorias_planta.mp4", "Vídeo das trajetórias na planta"),
                             ("demo_apresentacao.mp4", "Vídeo de demonstração (apresentação)"),
                             ("matrizes.npz", "Matrizes numéricas")):
            arq = escolha.arquivo(nome)
            if arq:
                st.download_button(rotulo, arq.read_bytes(), file_name=nome, key=f"dl_{escolha.nome}_{nome}")
        st.caption("Se um vídeo não tocar no navegador, baixe e abra no VLC (sem o ffmpeg instalado, "
                   "o vídeo fica no formato mp4v).")
    rel = escolha.arquivo("relatorio.md")
    if rel:
        with st.expander("Relatório completo"):
            st.markdown(rel.read_text(encoding="utf-8"))


def render():
    periodo = ui.cabecalho("Mapa de movimentação", "Cada movimento revela uma possibilidade.",
                           "Veja como os visitantes se distribuem e onde o fluxo se concentra.")
    aba_sim, aba_real = st.tabs(["Cenário simulado", "Vídeo real"])
    with aba_sim:
        _simulado(periodo)
    with aba_real:
        _video_real()

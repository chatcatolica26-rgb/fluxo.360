"""Onboarding para quem nunca usou a plataforma.

* Sempre que o sistema é aberto, uma janela de boas-vindas pergunta se a pessoa quer um tour
  rápido ("Começar o tour" ou "Agora não"). Quem marcar "Não mostrar ao abrir o sistema" deixa de
  ver a janela automaticamente. O tour roda dentro da janela, em 5 passos curtos, e pode ser
  fechado a qualquer momento (X ou "Fechar").
* O botão "Guia rápido" da barra lateral reabre a janela.
* Cada página tem a ajuda "Como ler esta tela"; a barra lateral tem "Primeiros passos" e glossário.
A opção "Não mostrar ao abrir o sistema" fica salva em data/preferencias/onboarding.json.
"""
from __future__ import annotations

import inspect
import json
from pathlib import Path

import streamlit as st

import dados_reais

ARQ_PREFS = Path("data/preferencias/onboarding.json")

# Os passos do tour (o passo 0 é a boas-vindas com a escolha)
PASSOS = [
    {"titulo": "Bem-vindo ao FLUXO360",
     "texto": "O FLUXO360 mostra **por onde os visitantes andam** e **onde eles param** no shopping.\n\n"
              "É a sua primeira vez aqui? Em **1 minuto** mostramos como usar.",
     "visual": None},
    {"titulo": "1. O que a plataforma faz",
     "texto": "Ela transforma o vídeo das câmeras em um **mapa do shopping** que mostra o movimento das pessoas. "
              "Com isso, você decide o que fazer em cada espaço.",
     "visual": "tres_ideias"},
    {"titulo": "2. De onde vêm os dados",
     "texto": "O computador reconhece as pessoas no vídeo e marca **onde cada uma pisa** na planta do shopping.",
     "visual": "fluxo_dados",
     "nota": "Privacidade: não guardamos rostos nem nomes. Cada pessoa vira só um ponto no chão."},
    {"titulo": "3. Como ler o mapa de calor",
     "texto": "**Azul = pouco movimento. Vermelho = muito movimento.**",
     "visual": "mapa_calor"},
    {"titulo": "4. O que fazer com o mapa",
     "texto": "A plataforma aponta situações por cor de urgência e sugere uma ação para testar.",
     "visual": "decisao"},
    {"titulo": "5. Onde encontrar cada coisa",
     "texto": "Use o **menu à esquerda**. Cada tela tem a ajuda **Como ler esta tela** no topo, e o botão "
              "**Guia rápido** reabre este guia quando quiser.",
     "visual": "menu"},
]

MENU = [("01", "Visão geral", "visao_geral", "o resumo: o que pede decisão agora"),
        ("02", "Mapa de movimentação", "mapa", "onde o movimento se concentra (inclui o vídeo real)"),
        ("03", "Análise de ambientes", "ambientes", "comparar corredores, praça e entrada"),
        ("04", "Diagnósticos", "diagnosticos", "situações por urgência"),
        ("05", "Recomendações", "recomendacoes", "ações sugeridas e registro do antes e depois"),
        ("06", "Relatórios", "relatorios", "resumo para compartilhar e exportar"),
        ("07", "Como funciona", "como_funciona", "como o vídeo vira mapa, passo a passo")]

CSS = """
<style>
.f360-pontos {display:flex; gap:6px; margin:.2rem 0 .6rem 0;}
.f360-pontos span {width:28px; height:6px; border-radius:3px; background:rgba(128,128,128,.3);}
.f360-pontos span.ativo {background:#3b82f6;}
.f360-caixa {border:1px solid rgba(128,128,128,.35); border-radius:10px; padding:.8rem 1rem; height:100%;}
.f360-caixa b {font-size:1.05rem;}
.f360-fluxo {display:flex; flex-wrap:wrap; align-items:center; gap:.5rem; margin:.4rem 0 .8rem 0;}
.f360-fluxo span.etapa {border:1px solid rgba(128,128,128,.45); border-radius:999px; padding:.35rem .9rem;}
.f360-fluxo span.seta {opacity:.6;}
.f360-grad {height:18px; border-radius:9px; background:linear-gradient(90deg,#00007f,#0050ff,#00d5ff,#7dff7a,#ffe600,#ff6a00,#b40000);}
.f360-grad-rot {display:flex; justify-content:space-between; font-size:.85rem; opacity:.8; margin-bottom:.6rem;}
.f360-chip {display:inline-block; font-size:.72rem; font-weight:600; padding:.15rem .55rem; border-radius:999px; color:#fff;}
</style>
"""


# ------------------------------------------------------------- estado salvo
def _prefs() -> dict:
    try:
        return json.loads(ARQ_PREFS.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _salvar_prefs(**valores) -> None:
    dados = _prefs() | valores
    try:
        ARQ_PREFS.parent.mkdir(parents=True, exist_ok=True)
        ARQ_PREFS.write_text(json.dumps(dados, ensure_ascii=False), encoding="utf-8")
    except OSError:
        pass                       # sem permissão de escrita: a escolha só não fica lembrada


def iniciar() -> None:
    """Uma vez por sessão (cada vez que o sistema é aberto): abre a boas-vindas."""
    if "tour_iniciado" not in st.session_state:
        st.session_state.tour_iniciado = True
        st.session_state.tour_aberto = not _prefs().get("nao_mostrar_ao_abrir", False)
        st.session_state.tour_passo = 0
    st.session_state.setdefault("visitadas", set(_prefs().get("visitadas", [])))
    if _prefs().get("tour_concluido"):
        st.session_state.visitadas.add("tour")


def abrir_tour() -> None:
    """Callback do botão "Guia rápido" da barra lateral: vai direto ao primeiro passo."""
    st.session_state.tour_aberto = True
    st.session_state.tour_passo = 1


def _ir_para_passo(i: int) -> None:
    st.session_state.tour_passo = i


def _salvar_opcao_abrir() -> None:
    _salvar_prefs(nao_mostrar_ao_abrir=bool(st.session_state.get("tour_nao_mostrar", False)))


def _encerrar(concluido: bool) -> None:
    st.session_state.tour_aberto = False
    st.session_state.tour_passo = 0
    if concluido:
        st.session_state.visitadas.add("tour")
        _salvar_prefs(tour_concluido=True, visitadas=sorted(st.session_state.visitadas))


def _fechou_no_x() -> None:
    st.session_state.tour_aberto = False


def registrar_visita(chave: str) -> None:
    v = st.session_state.setdefault("visitadas", set())
    if chave not in v:
        v.add(chave)
        _salvar_prefs(visitadas=sorted(v))


# ------------------------------------------------------------------ visuais
def _imagem_real(nome: str) -> Path | None:
    execs = dados_reais.listar_execucoes()
    return execs[0].arquivo(nome) if execs else None


def _fluxo(etapas: list[str]) -> None:
    html = "<span class='seta'>→</span>".join(f"<span class='etapa'>{e}</span>" for e in etapas)
    st.markdown(f"<div class='f360-fluxo'>{html}</div>", unsafe_allow_html=True)


def _visual(tipo: str | None) -> None:
    if tipo == "tres_ideias":
        for col, (t, d) in zip(st.columns(3), [("Ver", "por onde as pessoas andam e onde param"),
                                               ("Entender", "quais espaços pedem atenção"),
                                               ("Agir", "testar uma ação e medir o resultado")]):
            col.markdown(f"<div class='f360-caixa'><b>{t}</b><br>{d}</div>", unsafe_allow_html=True)
    elif tipo == "fluxo_dados":
        _fluxo(["Câmera filma", "Pessoas reconhecidas", "Posição na planta", "Mapa de calor"])
        img = _imagem_real("quadro_exemplo_deteccoes.png")
        if img:
            st.image(str(img), caption="Vídeo real do Capim Dourado: cada caixa é uma pessoa reconhecida.",
                     width=440)
    elif tipo == "mapa_calor":
        st.markdown("<div class='f360-grad'></div><div class='f360-grad-rot'><span>pouco movimento</span>"
                    "<span>muito movimento</span></div>", unsafe_allow_html=True)
        c1, c2 = st.columns([1, 1])
        img = _imagem_real("mapa_permanencia_rastros.png") or _imagem_real("mapa_permanencia_sobreposto.png")
        if img:
            c1.image(str(img), caption="Exemplo real: Praça de Eventos.", width=260)
        c2.markdown("- **Permanência:** onde as pessoas **ficam** mais tempo.\n"
                    "- **Circulação:** por onde **mais gente passa**.\n"
                    "- **Linhas finas:** o caminho de cada pessoa; a seta mostra para onde ela foi.")
    elif tipo == "decisao":
        for col, (n, cor, d) in zip(st.columns(3), [("Prioridade alta", "#d64541", "agir primeiro"),
                                                    ("Atenção", "#f2994a", "acompanhar de perto"),
                                                    ("Oportunidade", "#4fb39a", "espaço com potencial")]):
            col.markdown(f"<div class='f360-caixa'><span class='f360-chip' style='background:{cor}'>{n}</span>"
                         f"<br>{d}</div>", unsafe_allow_html=True)
        st.markdown("")
        _fluxo(["Diagnóstico", "Ação no local", "Medir antes e depois", "Manter ou ajustar"])
        st.caption("Os diagnósticos são hipóteses: confirme no local antes de decidir.")
    elif tipo == "menu":
        st.markdown("\n".join(f"- **{n} {nome}** — {d}" for n, nome, _, d in MENU))


# ---------------------------------------------------------------- janela
def _conteudo_janela() -> None:
    st.markdown(CSS, unsafe_allow_html=True)
    n = len(PASSOS) - 1
    i = min(max(st.session_state.get("tour_passo", 0), 0), n)
    p = PASSOS[i]
    if i > 0:
        pontos = "".join(f"<span class='{'ativo' if k <= i else ''}'></span>" for k in range(1, n + 1))
        st.markdown(f"<div class='f360-pontos'>{pontos}</div>", unsafe_allow_html=True)
        _botoes(i, n)                              # sempre visíveis, sem precisar rolar
    st.markdown(f"### {p['titulo']}")
    st.markdown(p["texto"])
    _visual(p.get("visual"))
    if p.get("nota"):
        st.caption(p["nota"])

    if i == 0:                                     # boas-vindas: a pessoa escolhe
        c1, c2, _ = st.columns([1.3, 1, 2])
        c1.button("Começar o tour", type="primary", on_click=_ir_para_passo, args=(1,), key="tour_comecar")
        if c2.button("Agora não", key="tour_agora_nao"):
            _encerrar(concluido=False)
            st.rerun()
        st.checkbox("Não mostrar ao abrir o sistema", key="tour_nao_mostrar",
                    value=_prefs().get("nao_mostrar_ao_abrir", False), on_change=_salvar_opcao_abrir)
        st.caption("O guia também abre pelo botão **Guia rápido**, na barra lateral.")


def _botoes(i: int, n: int) -> None:
    c1, c2, c3, c4 = st.columns([1, 1.2, 1, 1.3])
    c4.caption(f"Passo {i} de {n}")
    c1.button("← Voltar", on_click=_ir_para_passo, args=(i - 1,), key=f"tour_voltar_{i}", disabled=i == 1)
    if i < n:
        c2.button("Próximo →", type="primary", on_click=_ir_para_passo, args=(i + 1,), key=f"tour_proximo_{i}")
        if c3.button("Fechar", key=f"tour_fechar_{i}"):
            _encerrar(concluido=False)
            st.rerun()
    else:
        if c2.button("Concluir", type="primary", key="tour_concluir"):
            _encerrar(concluido=True)
            st.rerun()
        if c3.button("Ver o Mapa", key="tour_ir_mapa"):
            _encerrar(concluido=True)
            st.session_state.ir_para = "mapa"
            st.rerun()


def mostrar_se_preciso() -> None:
    """Chamar no app.py antes de ``navegacao.run()``.

    Enquanto o guia está aberto, a janela é desenhada em toda execução; ela só fecha quando a pessoa
    escolhe (Agora não, Fechar, Concluir ou o X). Em versões antigas do Streamlit, sem aviso de
    fechamento pelo X, a janela abre uma vez por pedido.
    """
    if not st.session_state.get("tour_aberto"):
        return
    if not hasattr(st, "dialog"):                  # Streamlit muito antigo: mostra no topo da página
        with st.container(border=True):
            _conteudo_janela()
        return
    janela = None
    if "on_dismiss" in inspect.signature(st.dialog).parameters:
        try:
            janela = st.dialog("Guia rápido do FLUXO360", width="large", on_dismiss=_fechou_no_x)
        except Exception:                          # versão que não aceita função no on_dismiss
            janela = None
    if janela is None:
        st.session_state.tour_aberto = False       # sem aviso do X: abre uma vez por pedido
        janela = st.dialog("Guia rápido do FLUXO360", width="large")
    janela(_conteudo_janela)()


def tour_guiado() -> None:
    """Mantido por compatibilidade: o tour agora abre em janela (ver mostrar_se_preciso)."""
    return



AJUDA = {
    "visao_geral": ["Os **3 cartões** são as situações que mais pedem decisão, da mais urgente para a menos urgente.",
                    "**Evidências** são os números que sustentam os cartões.",
                    "No **mapa**, mude o horário para ver como o movimento muda ao longo do dia."],
    "mapa": ["Cada bloco colorido é uma região do piso; o número é quantas vezes passaram por ali.",
             "As **setas** mostram para onde as pessoas seguem; quanto mais grossa, mais gente.",
             "Na aba **Vídeo real**, o mapa vem de um vídeo de verdade, sobre a planta oficial."],
    "ambientes": ["A **tabela** compara os ambientes; variação negativa (−) quer dizer menos movimento que antes.",
                  "No **gráfico de linhas**, a linha forte é o período escolhido e a tracejada, o anterior.",
                  "**Pico** é o horário de maior movimento; **permanência**, quanto tempo as pessoas ficam."],
    "diagnosticos": ["Vermelho = **agir primeiro**; laranja = **acompanhar**; verde = **oportunidade**.",
                     "Abra **Hipóteses e potencial** para ver o que conferir no local.",
                     "Use **Ver plano de ação** para ir direto à recomendação."],
    "recomendacoes": ["Cada plano tem uma **ação**, um **indicador** e um **valor de referência**.",
                      "Depois de executar a ação, preencha **Acompanhamento** com os números de antes e depois.",
                      "O **simulador** mostra cenários; ele não é previsão."],
    "relatorios": ["Resumo para compartilhar com a equipe.",
                   "**Exportar relatório CSV** baixa os números para abrir no Excel."],
    "como_funciona": ["Esta tela mostra, passo a passo, como o vídeo vira mapa de calor.",
                      "Comece pelo **vídeo de 16 segundos**, depois desça pelas etapas."],
}

GLOSSARIO = {
    "Passagem": "uma pessoa passando por um lugar. A mesma pessoa pode gerar várias passagens.",
    "Permanência": "quanto tempo as pessoas ficam num lugar.",
    "Circulação": "quantas pessoas diferentes passam por um lugar.",
    "Intensidade": "comparação do movimento entre as regiões (de baixa a crítica).",
    "Mapa de calor": "planta colorida: azul = pouco movimento, vermelho = muito.",
    "Id": "número que o sistema dá a cada pessoa rastreada. Não é identificação pessoal.",
    "Calibração": "ajuste que liga o chão do vídeo ao chão da planta, para cada posição cair no lugar certo.",
    "Dados simulados": "números de demonstração, não medidos por câmera.",
}

PRIMEIROS_PASSOS = [("tour", "Fazer o tour guiado"), ("mapa", "Ver o mapa de movimentação"),
                    ("diagnosticos", "Ler os diagnósticos"), ("recomendacoes", "Abrir um plano de ação"),
                    ("como_funciona", "Ver como a análise é feita")]

def ajuda_da_pagina(chave: str) -> None:
    """Expansor "Como ler esta tela"; vem aberto na primeira visita à página."""
    itens = AJUDA.get(chave)
    primeira = chave not in st.session_state.get("visitadas", set())
    registrar_visita(chave)
    if not itens:
        return
    with st.expander("Como ler esta tela", expanded=primeira):
        for item in itens:
            st.markdown(f"- {item}")


def barra_lateral() -> None:
    """Primeiros passos (progresso) e glossário."""
    v = st.session_state.get("visitadas", set())
    feitos = sum(1 for k, _ in PRIMEIROS_PASSOS if k in v)
    st.markdown(f"**Primeiros passos · {feitos} de {len(PRIMEIROS_PASSOS)}**")
    st.progress(feitos / len(PRIMEIROS_PASSOS))
    linhas = [f"{'✔' if k in v else '○'} {rot}" for k, rot in PRIMEIROS_PASSOS]
    st.caption("  \n".join(linhas))
    with st.expander("Glossário"):
        for termo, d in GLOSSARIO.items():
            st.markdown(f"**{termo}:** {d}")

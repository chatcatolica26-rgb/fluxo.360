import streamlit as st
import pandas as pd
import plotly.express as px

# Configuração da Página
st.set_page_config(
    page_title="ZonexIA - Inteligência de Fluxo",
    page_icon="??",
    layout="wide"
)

# --- CONTROLE DE ESTADO DO ONBOARDING (Tecnologia da Roleta) ---
if 'onboarding_concluido' not in st.session_state:
    st.session_state.onboarding_concluido = False

# Modal / Bloco de Onboarding (Primeiros passos guiados para o usuário novo)
if not st.session_state.onboarding_concluido:
    st.markdown("---")
    st.info("Bem-vindo ao ZonexIA! Este e o seu guia rapido de primeiros passos (Onboarding).")
    col_ob1, col_ob2, col_ob3 = st.columns(3)
    
    with col_ob1:
        st.markdown("### 1. Mapa Espacial")
        st.write("Acompanhe a intensidade de fluxo dividida por zonas (Entrada, Corredores e Alimentacao).")
    with col_ob2:
        st.markdown("### 2. Leitura de Alertas")
        st.write("O sistema detecta automaticamente areas com circulacao abaixo do esperado (ex: Corredor B).")
    with col_ob3:
        st.markdown("### 3. Acao e Medicao")
        st.write("Aplique recomendacoes comerciais e valide o impacto comparando o antes e depois.")
        
    if st.button("Entendi, comecar a usar o sistema!", type="primary"):
        st.session_state.onboarding_concluido = True
        st.rerun()
    st.markdown("---")

# --- HEADER PRINCIPAL ---
st.title("ZonexIA: Inteligencia Espacial e Fluxo de Visitantes")
st.markdown("*Transformando dados de movimentacao em decisoes estrategicas para shopping centers.*")

# Botão para reabrir o onboarding se quiser mostrar aos jurados
if st.session_state.onboarding_concluido:
    if st.sidebar.button("Reabrir Tour Guiado (Onboarding)"):
        st.session_state.onboarding_concluido = False
        st.rerun()

# --- DADOS SIMULADOS (MOCKUP PARA O MVP) ---
dados_fluxo = pd.DataFrame({
    'Horario': ['12h', '15h', '18h', '20h', '12h', '15h', '18h', '20h', '12h', '15h', '18h', '20h', '12h', '15h', '18h', '20h', '12h', '15h', '18h', '20h'],
    'Ambiente': [
        'Entrada Principal', 'Entrada Principal', 'Entrada Principal', 'Entrada Principal',
        'Corredor A', 'Corredor A', 'Corredor A', 'Corredor A',
        'Corredor B', 'Corredor B', 'Corredor B', 'Corredor B',
        'Alimentacao', 'Alimentacao', 'Alimentacao', 'Alimentacao',
        'Convivencia', 'Convivencia', 'Convivencia', 'Convivencia'
    ],
    'Passagens': [420, 350, 580, 620, 310, 270, 490, 510, 65, 80, 110, 95, 380, 520, 680, 590, 90, 150, 240, 280],
    'Tipo': ['Entrada', 'Entrada', 'Entrada', 'Entrada', 'Passagem', 'Passagem', 'Passagem', 'Passagem', 'Passagem (Alerta)', 'Passagem (Alerta)', 'Passagem (Alerta)', 'Passagem (Alerta)', 'Permanencia', 'Permanencia', 'Permanencia', 'Permanencia', 'Permanencia', 'Permanencia', 'Permanencia', 'Permanencia']
})

# --- KPIS SUPERIORES ---
kpi1, kpi2, kpi3, kpi4 = st.columns(4)
kpi1.metric("Deteccoes Agregadas", "2.825", "+12% vs ontem")
kpi2.metric("Ambientes Monitorados", "5 Zonas", "100% Cobertura")
kpi3.metric("Oportunidades Prioritarias", "1 Alerta", "Corredor B")
kpi4.metric("Recomendadores Ativos", "3 Acoes", "Prontas para teste")

st.markdown("---")

# --- SEÇÃO DE GRÁFICOS E MAPA DE CALOR ---
col_graf1, col_graf2 = st.columns([2, 1])

with col_graf1:
    st.subheader("Comportamento do Fluxo ao Longo do Dia")
    fig = px.line(
        dados_fluxo, x='Horario', y='Passagens', color='Ambiente',
        markers=True, title="Passagens por Horario e Ambiente"
    )
    st.plotly_chart(fig, use_container_width=True)

with col_graf2:
    st.subheader("Diagnostico Automatico")
    st.warning("Alerta Prioritario: Corredor B\n\nCirculacao 60% abaixo da media dos demais corredores.")
    st.markdown("""
    **Hipoteses a Investigar:**
    * Baixa visibilidade ou sinalizacao deficiente.
    * Ausencia de pontos de atracao comercial no trecho.
    """)
    if st.button("Ver Recomendacao da IA"):
        st.success("Sugestao: Realizar ativacao temporaria ou exposicao de quiosque no local. **Impacto esperado estimado: +52.6% no fluxo.**")

# --- SIMULADOR ANTES VS DEPOIS ---
st.markdown("---")
st.subheader("Validacao de Intervencao Comercial (Antes vs. Depois - Corredor B)")
col_sim1, col_sim2 = st.columns(2)

with col_sim1:
    st.write("Simulacao de fluxo medio por hora no mesmo horario:")
    df_intervencao = pd.DataFrame({
        'Fase': ['Antes da Acao', 'Depois da Acao (+52.6%)'],
        'Passagens Medias': [95, 145]
    })
    fig_bar = px.bar(df_intervencao, x='Fase', y='Passagens Medias', color='Fase', text='Passagens Medias')
    st.plotly_chart(fig_bar, use_container_width=True)

with col_sim2:
    st.info("Nota de Transparencia do Sistema:")
    st.write("O sistema registra a evolucao temporal e correlaciona a intervencao ao aumento de fluxo. Os dados exibidos no prototipo sao simulados para fins de demonstracao no Hackarun, mantendo arquitetura pronta para CFTV real e LGPD compliant.")
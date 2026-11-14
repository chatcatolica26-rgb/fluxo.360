# FLUXO360 — Do movimento à decisão

Plataforma de **análise de fluxo de pessoas em shopping centers** com visão computacional:
o vídeo das câmeras vira **trajetórias e mapas de calor sobre a planta do shopping**, e o painel
transforma isso em **diagnósticos e planos de ação**.

## Acesso rápido

| O quê | Link |
|---|---|
| **Aplicação web (painel)** | **https://fluxo360.streamlit.app** ← *trocar pelo endereço gerado na publicação* |
| Código-fonte | https://github.com/chatcatolica26-rgb/fluxo.360 |
| Vídeo de demonstração (16 s) | [`data/demo/.../demo_apresentacao.mp4`](data/demo/20261114_112950_praca_eventos_demo/demo_apresentacao.mp4) |
| Relatório da análise do vídeo real | [`data/demo/.../relatorio.md`](data/demo/20261114_112950_praca_eventos_demo/relatorio.md) |

Na aplicação, comece pelo **Guia rápido** (abre sozinho) e depois veja **07 Como funciona**.

## O que tem no painel

| Tela | Para que serve |
|---|---|
| 01 Visão geral | o resumo: o que pede decisão agora e onde está o movimento |
| 02 Mapa de movimentação | mapa por região e horário; aba **Vídeo real** com o mapa de calor e o rastro das pessoas |
| 03 Análise de ambientes | comparação entre entrada, corredores, alimentação e convivência |
| 04 Diagnósticos | situações por urgência, com hipóteses a verificar |
| 05 Recomendações | planos de ação, simulador e acompanhamento antes e depois |
| 06 Relatórios | resumo e exportação em CSV |
| 07 Como funciona | o método, passo a passo, com o vídeo real da Praça de Eventos |

> **Sobre os dados.** As telas 01 a 06 usam números **simulados** para demonstração. A aba *Vídeo real* e a
> tela 07 mostram uma análise **real** de 10 s de vídeo da Praça de Eventos do Capim Dourado Shopping,
> projetada na planta oficial. Pessoas aparecem **pixeladas** (LGPD). A análise publicada usa um detector
> de demonstração (OpenCV HOG) e calibração preliminar; o sistema completo usa YOLO + ByteTrack.

## Como funciona

```
vídeo da câmera ─► detecção de pessoas (YOLO) ─► rastreamento com ids (ByteTrack)
   ─► ponto dos pés ─► homografia (chão do vídeo → planta oficial)
   ─► acumulação no tempo (permanência e circulação, células de 0,5 m) ─► mapa de calor + rastros ─► painel
```

## Três formas de usar

| Forma | Para quem | Como |
|---|---|---|
| **Web** | avaliadores, demonstração | abrir o link acima |
| **Instalado no Windows** | cliente (uso local, com análise de vídeo) | ver [`instalador/GERAR_INSTALADOR.md`](instalador/GERAR_INSTALADOR.md) |
| **Desenvolvimento** | equipe | `uv pip install -r requirements.txt -r dashboard/requirements-dashboard.txt` e `streamlit run dashboard/app.py` |

Analisar um vídeo (no computador): calibrar a câmera com `python tools/calibrar_camera.py ...` e rodar
`python -m src.experiments.run_shopping` (detalhes em [`COMO_TESTAR.md`](COMO_TESTAR.md)).

## Estrutura

```
dashboard/          painel Streamlit (7 telas, guia rápido, modo web)
src/                visão computacional: vídeo, detecção, rastreamento, projeção, acumulação, mapas
  experiments/run_shopping.py   análise completa de um vídeo do shopping
  experiments/run_mot20.py      avaliação técnica com a base MOT20 (ver docs/MOT20.md)
tools/              calibração da câmera, análise de demonstração, rastros, vídeo de demonstração
configs/            parâmetros da análise, ByteTrack, planta e calibração das câmeras
data/planta/        plantas do piso (base do mapa de calor)
data/demo/          análise de demonstração publicada (vídeo real anonimizado)
instalador/         instalador para Windows (Setup.exe com Inno Setup ou .zip)
tests/              42 testes automatizados (pytest)
```

## Documentação
- [`PUBLICAR_NA_WEB.md`](PUBLICAR_NA_WEB.md) — como gerar e manter o link da aplicação web
- [`instalador/GERAR_INSTALADOR.md`](instalador/GERAR_INSTALADOR.md) — instalador para o cliente
- [`COMO_TESTAR.md`](COMO_TESTAR.md) — análise do vídeo real passo a passo
- [`LEIA-ME_PLANTA.md`](LEIA-ME_PLANTA.md) — plantas, escala e calibração
- [`docs/MOT20.md`](docs/MOT20.md) — avaliação técnica de detecção e rastreamento com o MOT20

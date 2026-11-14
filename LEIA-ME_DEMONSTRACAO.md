# Demonstração: vídeo real + planta oficial do Capim Dourado

## O que vem neste pacote
| Item | Onde |
|---|---|
| Análise pronta do vídeo da Praça de Eventos (mapas, trajetórias, vídeos, relatório) | `data/processed/shopping/<data>_demo_opencv/` |
| Vídeo de 16 s para a apresentação | `.../demo_apresentacao.mp4` (mesma pasta) |
| Calibração da câmera (preliminar) e área do piso | `configs/cameras/cam_praca_eventos.yaml`, `data/planta/mascaras/` |
| Vídeo original no lugar certo para rodar de novo | `data/raw/shopping/praca_eventos.mp4` |
| Painel atualizado, com a página **07 Como funciona** | `dashboard/` |
| Análise sem YOLO (para demonstração) e gerador do vídeo de demonstração | `tools/analise_demo_opencv.py`, `tools/gerar_video_demo.py` |

Descompacte na pasta `C:\Users\giuli\Fluxo360` e escolha mesclar/substituir. Depois: `streamlit run dashboard/app.py`.

## Roteiro de apresentação (cerca de 3 minutos)
1. **Visão geral (30 s)** — o problema: entender onde as pessoas circulam e ficam, para decidir ações nos espaços.
2. **07 Como funciona (90 s)** — passe o vídeo de 16 s e depois desça pelas etapas:
   vídeo real → calibração (a planta oficial cai sobre o vídeo) → detecção com ids → trajetórias na planta → acumulação no tempo → mapa de calor.
3. **02 Mapa de movimentação, aba Vídeo real (30 s)** — o resultado na planta oficial: permanência e circulação.
4. **04 e 05, Diagnósticos e Recomendações (30 s)** — como o mapa vira decisão (cenário demonstrativo).

## O que dizer sobre os limites (e é importante dizer)
- São **10 segundos** de vídeo: a demonstração mostra o **método**, não o padrão de circulação do shopping.
- Esta análise usou um **detector de demonstração (OpenCV HOG)**, porque o ambiente onde ela foi gerada não tinha YOLO.
  Rodando no computador do projeto, com YOLO + ByteTrack, a detecção é melhor:
  `python -m src.experiments.run_shopping` (e depois `python tools/gerar_video_demo.py`).
- **Ids não são pessoas únicas**: o rastreador de demonstração perde as pessoas em grupos e cria ids novos.
- A **calibração é preliminar** (erro médio de 0,49 m), feita a distância com vitrines, degraus, escada rolante e
  placas do piso. Ela foi conferida pela borda curva da Praça de Eventos, que não entrou no cálculo e mesmo assim
  caiu sobre a borda real. Para a versão definitiva, refaça no local:
  `python tools/calibrar_camera.py --camera cam_praca_eventos --piso terreo --fonte data/raw/shopping/praca_eventos.mp4 --mediana`

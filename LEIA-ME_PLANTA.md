# Planta do Capim Dourado no Fluxo360

Copie as pastas deste pacote para a raiz do projeto `Fluxo360`. Nenhum arquivo existente é substituído.

```
configs/planta.yaml                 escala e imagens de cada piso
configs/cameras/                    um .yaml por câmera (gerado pela calibração)
data/planta/*_limpa.png             fundo do mapa de calor (sem textos, logos, cotas e vagas)
data/planta/*_original.png          com nomes das lojas, para achar os pontos de calibração
src/projection/homografia.py        câmera -> planta (usa o ponto dos pés)
src/heatmap/mapa_calor.py           acumula as posições e desenha o calor
tools/calibrar_camera.py            calibração por cliques (vídeo x planta)
tools/rodar_mapa_calor.py           fluxo completo: YOLO + ByteTrack -> planta -> calor
tools/gerar_bases.py                regenera os PNGs a partir do PDF (precisa de pdftoppm)
```

Dependências: `opencv-python numpy pyyaml ultralytics`

## Passo a passo
1. **Calibrar cada câmera** (rode a partir da raiz do projeto):
   `python tools/calibrar_camera.py --camera cam01 --piso terreo --fonte cam01.mp4`
   Clique o ponto no VÍDEO e depois o mesmo ponto na PLANTA. Use de 6 a 10 pontos **no chão**:
   base de pilares, quinas de vitrines, cantos de quiosques. Aperte `v` para ver a planta sobreposta ao vídeo,
   `m` para desenhar a área que a câmera cobre e `s` para salvar. Erro médio abaixo de 0,3 m é bom.
2. **Gerar o mapa de calor**:
   `python tools/rodar_mapa_calor.py --camera configs/cameras/cam01.yaml --video cam01.mp4 --mostrar`

## Escala
- Térreo: 10 px = 1 m. A escala saiu das cotas do desenho e confere com a Praça de Eventos (21,60 m).
- Praça de alimentação: 40 px = 1 m. É uma estimativa, porque essa folha tem poucas cotas.
- Antes de usar as medidas em relatórios (m², distância, velocidade), confira uma ou duas medidas no local com trena.

## Observações
- Câmeras com lente olho de peixe precisam ter a distorção corrigida (`cv2.undistort`) antes da calibração.
- Cada pessoa conta uma vez por célula de 0,5 m. Quem fica parado não infla o mapa.
- Áreas vistas por duas câmeras somam as duas contagens. Se isso pesar, defina as máscaras sem sobreposição.

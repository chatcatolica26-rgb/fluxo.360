# Relatório de processamento — praca_eventos_demo

Gerado em 20261114_112950. Fonte: vídeo real do shopping (não misturar com resultados do MOT20).

## Vídeo
| Item | Valor |
|---|---|
| Arquivo | praca_eventos.mp4 |
| Resolução | 1280 x 720 |
| FPS | 24.00 |
| Duração total | 10.00 s (240 quadros) |
| Trecho analisado | 0 s a fim (passo 1) |
| Duração analisada | 10.00 s |
| Quadros processados | 240 |
| Tempo de processamento | 132.4 s (1.81 quadros/s) |

## Contagens
| Medida | Valor |
|---|---|
| Detecções (todas as caixas de pessoa, em todos os quadros) | 4139 |
| Detecções usadas no mapa | 3960 |
| Ids gerados pelo rastreador | 114 |
| Pessoas únicas na área calibrada | 113 |
| Trajetórias registradas (≥ 12 posições) | 59 |

Pessoas únicas = ids distintos. Trocas de id fazem uma pessoa contar mais de uma vez: confira no `video_deteccoes.mp4`.

### Posições descartadas
| Motivo | Quantidade |
|---|---|
| fora_da_area_calibrada | 179 |

## Detector
Rastreador usado nesta execução: **OpenCV HOG + rastreador simples (demonstração, sem YOLO)**.

| Parâmetro do YOLO (configuração) | Valor |
|---|---|
| Modelo | yolov8n.pt |
| Classe | 0 (person), demais descartadas |
| Confiança mínima | 0.3 |
| IoU do NMS | 0.7 |
| Tamanho da imagem | 1280 |
| Dispositivo | automático |

## ByteTrack
| Parâmetro | Valor |
|---|---|
| arquivo | configs/bytetrack_shopping.yaml |
| tracker_type | bytetrack |
| track_high_thresh | 0.3 |
| track_low_thresh | 0.1 |
| new_track_thresh | 0.4 |
| track_buffer | 48 |
| match_thresh | 0.8 |
| fuse_score | True |

## Calibração e homografia
| Item | Valor |
|---|---|
| Arquivo | configs/cameras/cam_praca_eventos.yaml |
| Piso | terreo |
| Pontos usados | 4 |
| Erro médio / máximo | 0.486 m / 1.214 m |
| Máscara da área válida | data/planta/mascaras/cam_praca_eventos.png |
| Situação | preliminar - feita a distancia, sem medidas no local; conferir no shopping com calibrar_camera.py |
| Método | minimos quadrados com 4 pontos, 3 linhas (vitrines norte e sul, base dos degraus) e 13 placas pretas do piso (devem virar quadrados); validado pela borda curva da Praca de Eventos, nao usada no ajuste |

Matriz H (pixel do vídeo -> pixel da planta):

```
[[-3.71024388e+05 -1.92368676e+06 -4.87090128e+07]
 [-7.76076919e+05 -4.69285726e+06  6.14809211e+07]
 [-2.61111070e+02 -1.75439897e+03  1.00000000e+00]]
```

## Acumulação
Célula de 0.5 m. Permanência em segundos de presença (cada quadro soma passo/FPS, então o
resultado não depende do FPS). Circulação = pessoas diferentes que entraram em cada célula. Suavização gaussiana de
0.75 m só nas imagens; as matrizes `.npy` guardam os valores sem suavização.
Permanência total somada: 165.0 s.

## Arquivos
`video_deteccoes.mp4`, `video_trajetorias_planta.mp4`, `planta_calibrada.png`, `calibracao_sobreposta.png`,
`quadro_exemplo_deteccoes.png`, `trajetorias_planta.png`, `localizacao_na_planta.png`, `mapa_permanencia_sobreposto.png`,
`mapa_permanencia_rastros.png`, `mapa_circulacao_rastros.png`,
`mapa_permanencia_isolado.png`, `mapa_circulacao_sobreposto.png`, `mapa_circulacao_isolado.png`,
`matriz_permanencia_s.npy`, `matriz_passagens.npy`, `matrizes.npz`, `trajetorias.csv`, `rastreamento_mot.txt`,
`run_info.json`, `config.yaml`, `processamento.log`.

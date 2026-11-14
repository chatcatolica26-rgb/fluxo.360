# Fluxo360 — integração com o MOT20

Protótipo de análise de fluxo de pessoas com visão computacional. Esta parte do projeto usa a base **MOT20** para desenvolver e avaliar a **detecção (YOLO)** e o **rastreamento (ByteTrack)** de pessoas em cenas lotadas, comparando os resultados com as anotações oficiais.

> Resultados no MOT20 medem o desempenho técnico dos algoritmos. Eles **não** validam o sistema em shopping centers (veja *Restrições*).

## Estrutura

```
fluxo360/
├── configs/
│   ├── experimento_padrao.yaml   # modelo, limiares, sequências, avaliação
│   └── bytetrack_mot20.yaml      # parâmetros ajustáveis do ByteTrack
├── data/
│   ├── raw/mot20/                # MOT20 original (fora do Git)
│   ├── processed/mot20/          # previsões e métricas dos experimentos (fora do Git)
│   └── samples/
├── docs/DADOS_MOT20.md           # origem, licença, sequências e regras
├── src/
│   ├── dataset/                  # independente dos algoritmos
│   │   ├── mot20_loader.py       # localiza sequências, lê quadros, exporta vídeo
│   │   ├── mot20_annotations.py  # lê/escreve anotações MOT, classes, coordenadas
│   │   └── evaluation.py         # MOTA, IDF1, HOTA, Precision, Recall, contagem
│   ├── detection/yolo_detector.py
│   ├── tracking/bytetrack_tracker.py
│   └── experiments/
│       ├── run_mot20.py          # executa e avalia experimentos
│       └── compare.py            # compara configurações
└── tests/                        # pytest com uma base MOT20 sintética
```

## Instalação

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Os pesos do YOLO (ex.: `yolov8n.pt`) são baixados automaticamente na primeira execução.

## Preparar o MOT20 (Fase 2)

1. Acesse <https://motchallenge.net/data/MOT20/>, aceite os termos e baixe o `MOT20.zip`.
2. Extraia em `data/raw/mot20/`, ficando assim:

```
data/raw/mot20/train/MOT20-01/{seqinfo.ini, img1/, gt/gt.txt, det/det.txt}
data/raw/mot20/test/MOT20-04/{seqinfo.ini, img1/, det/det.txt}
```

3. Confira se está tudo no lugar:

```bash
python -c "from src.dataset import MOT20Dataset as D; d=D(); print(d.available_sequences()); print(d.verify('MOT20-01'))"
```

As sequências vêm como quadros JPEG. Para ter um vídeo (por exemplo, para testar a leitura com OpenCV como se fosse uma câmera):

```bash
python -c "from src.dataset import MOT20Dataset as D; D().export_video('MOT20-01', 'data/samples/MOT20-01.mp4', max_frames=250)"
```

## Executar experimentos

```bash
# primeiros experimentos: MOT20-01 e MOT20-02 (padrão do config)
python -m src.experiments.run_mot20

# teste rápido
python -m src.experiments.run_mot20 --sequences MOT20-01 --max-frames 100

# só detecção (YOLO), sem rastreamento: Precision, Recall e contagem por quadro
python -m src.experiments.run_mot20 --mode detect

# outra configuração
python -m src.experiments.run_mot20 --config configs/meu_teste.yaml --name yolov8s_conf02

# reavaliar previsões já salvas
python -m src.experiments.run_mot20 --evaluate-only data/processed/mot20/experimentos/<pasta>

# comparar todos os experimentos (ordenado por HOTA)
python -m src.experiments.compare
```

Cada execução cria `data/processed/mot20/experimentos/<data>_<nome>_<modo>/` com:

| Arquivo | Conteúdo |
|---|---|
| `predictions/<seq>.txt` | previsões no formato oficial do MOTChallenge |
| `metrics.json / .csv / .md` | métricas por sequência e a linha `COMBINADO` |
| `config.yaml` | configuração usada (para reproduzir) |
| `run_info.json` | quadros processados, tempo, FPS e versões das bibliotecas |

Sequências de **teste** só geram previsões: o Ground Truth delas não é público. A avaliação delas é feita pelo servidor do MOTChallenge.

## Métricas

| Métrica | O que mede |
|---|---|
| **HOTA** (DetA, AssA, LocA) | equilíbrio entre detectar bem e manter a identidade certa |
| **MOTA** | erros gerais: falsos positivos, falsos negativos e trocas de id |
| **IDF1** | consistência das identidades ao longo da trajetória |
| **Precision** | das caixas previstas, quantas são pessoas de verdade |
| **Recall** | das pessoas de referência, quantas foram detectadas |
| IDSW, Frag, MT/PT/ML | trocas de id, trajetórias interrompidas, trajetórias bem/mal rastreadas |
| **Count_MAE / Count_Bias** | erro médio na quantidade de pessoas por quadro (viés > 0 = conta a mais) |
| **ID_Count_Error / ID_Ratio** | identidades geradas × pessoas reais; valores altos indicam a mesma pessoa contada várias vezes |

As definições seguem o avaliador oficial (TrackEval): associação com IoU ≥ 0,5, previsões sobre distratores ignoradas e HOTA calculado em 19 limiares de IoU (0,05 a 0,95).

## Testes

```bash
pytest
```

Os testes criam uma base MOT20 pequena e falsa em pasta temporária e cobrem: carregamento das sequências, leitura das anotações, interpretação das coordenadas, comparação com o Ground Truth, cálculo das métricas (com valores conferidos à mão), erros de contagem e rastreamento e a execução completa de um experimento. Não é preciso baixar o MOT20 nem o YOLO para rodá-los.

## Fases de desenvolvimento

| Fase | Entrega | Situação nesta etapa |
|---|---|---|
| 1. Estrutura e ambiente | pastas, dependências, configs | ✅ |
| 2. Preparação dos dados MOT20 | download, organização, `verify` | ✅ (código pronto; download manual) |
| 3. Captura e leitura dos vídeos | leitura de quadros com OpenCV, exportação de vídeo | ✅ |
| 4. Detecção de pessoas | `YoloPersonDetector`, `--mode detect` | ✅ |
| 5. Rastreamento | `ByteTrackPersonTracker`, `--mode track` | ✅ |
| 6. Avaliação dos algoritmos | `evaluation.py`, relatórios, comparação | ✅ |
| 7. Análise de fluxo | contagem, ocupação, mapas de calor | a fazer |
| 8. Banco de dados | armazenar experimentos e análises | a fazer |
| 9. Dashboard | indicadores e gráficos | a fazer |
| 10. Validação e documentação | testes finais, limitações | em andamento |

## Restrições

- MOT20 sob licença **CC BY-NC-SA 3.0**: uso não comercial, com atribuição. Não usar em atividade comercial sem licença adequada.
- Os arquivos da base e os resultados não vão para o GitHub (`.gitignore`).
- Ajustes só com sequências de treinamento; nunca usar anotações de teste para treinar ou ajustar.
- Bons resultados no MOT20 não significam que o sistema está validado para shopping centers. Isso exige testes com vídeos reais do ambiente, com autorização e respeito à LGPD.
- Os ids do rastreamento são temporários e não identificam pessoas.

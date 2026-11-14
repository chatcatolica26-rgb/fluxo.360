# Base de dados MOT20

## Origem

- **Base:** MOT20 — *Multiple Object Tracking Benchmark*, cenas com muitas pessoas.
- **Disponível em:** <https://motchallenge.net/data/MOT20/>
- **Referência:** DENDORFER, P. et al. *MOT20: A benchmark for multi object tracking in crowded scenes*. arXiv:2003.09003, 2020.
- **Licença:** Creative Commons Atribuição-NãoComercial-CompartilhaIgual 3.0 (CC BY-NC-SA 3.0), além das condições de uso das fontes originais publicadas pelo MOTChallenge.

## Como o Fluxo360 usa a base

O MOT20 é o **ambiente de experimentação e avaliação técnica** do protótipo. Ele serve para:

1. testar a detecção de pessoas com YOLO;
2. avaliar o rastreamento com ByteTrack e a manutenção dos identificadores temporários;
3. analisar oclusão, sobreposição e aglomeração;
4. identificar falhas de detecção e perdas de rastreamento;
5. medir se a contagem de pessoas tem duplicações;
6. comparar os resultados com as anotações oficiais (Ground Truth).

## Sequências

| Sequência | Conjunto | Cena |
|---|---|---|
| MOT20-01 | treinamento | estação ferroviária com grande concentração de pessoas |
| MOT20-02 | treinamento | estação ferroviária movimentada |
| MOT20-03 | treinamento | saída de estádio durante a noite |
| MOT20-05 | treinamento | praça com grande concentração de pessoas |
| MOT20-04 | teste | praça movimentada durante a noite |
| MOT20-06 | teste | rua de pedestres |
| MOT20-07 | teste | estação ferroviária movimentada |
| MOT20-08 | teste | rua de pedestres |

Ordem de uso: **MOT20-01 e MOT20-02** primeiro; depois as demais de treinamento; por último as de teste, para medir generalização.

## Separação entre treinamento, ajuste e avaliação

- Ajustes de parâmetros (confiança, NMS, ByteTrack, tamanho de imagem) só com sequências de **treinamento**.
- Uma prática recomendada é ajustar em MOT20-01/02/03 e confirmar em MOT20-05, que não participou do ajuste.
- As sequências de **teste** não têm Ground Truth público. O script gera as previsões no formato oficial; a avaliação delas é feita pelo servidor do MOTChallenge, respeitando o protocolo do benchmark (inclusive o limite de envios).
- O código nunca lê anotações de teste para treinar ou ajustar modelos.

## Formato das anotações (`gt/gt.txt`)

```
quadro, id, x, y, largura, altura, flag, classe, visibilidade
```

- Coordenadas em pixels, a partir do canto superior esquerdo; quadros começam em 1.
- Só contam como pessoas avaliadas as linhas com `classe = 1` e `flag = 1`.
- As classes 2 (pessoa em veículo), 6 (veículo não motorizado), 7 (pessoa parada), 8 (distrator) e 12 (reflexo) são **distratores**, como no avaliador oficial (TrackEval): uma previsão sobre elas não conta como acerto nem como erro.
- `visibilidade` vai de 0 (totalmente oculto) a 1 (totalmente visível).

## Regras

- Não usar o MOT20 em atividades comerciais sem autorização ou licença adequada.
- Não enviar os arquivos da base para o GitHub (`.gitignore` já bloqueia `data/raw/` e `data/processed/`).
- Citar a origem dos dados em relatórios e apresentações.
- Resultados no MOT20 **não** são validação em shopping centers: câmeras, ângulos, iluminação e comportamento das pessoas são diferentes. Um bom resultado no benchmark não permite afirmar que o sistema está validado para ambientes comerciais.

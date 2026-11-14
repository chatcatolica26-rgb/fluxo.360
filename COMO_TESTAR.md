# Como testar o mapa de calor com o vídeo do shopping

Este pacote **só acrescenta arquivos**. Nenhum arquivo que já existe no Fluxo360 é alterado.

## 1. Copiar os arquivos
Descompacte o pacote **dentro de** `C:\Users\giuli\Fluxo360`. Se o Windows perguntar, escolha mesclar as pastas.

## 2. Preparar o Python (só na primeira vez)
O YOLO não instala no Python 3.16 alfa. Use o 3.12. No terminal do VS Code, na pasta do projeto:

```powershell
uv venv --python 3.12
.venv\Scripts\activate
uv pip install -r requirements.txt
```
Depois, no VS Code: `Ctrl+Shift+P` > **Python: Select Interpreter** > `.venv`.

## 3. Conferir se está tudo certo
```powershell
pytest
```
O resultado esperado é **42 passed**.

## 4. Colocar o vídeo
Crie a pasta `data\raw\shopping` e copie o vídeo para lá com o nome `praca_eventos.mp4`.

## 5. Calibrar a câmera (uma vez por câmera)
```powershell
python tools/calibrar_camera.py --camera cam_praca_eventos --piso terreo --fonte data/raw/shopping/praca_eventos.mp4 --mediana
```
Abrem duas janelas: o **vídeo sem pessoas** e a **planta**. Use a roda do mouse para dar zoom e o botão direito para mover.

- Na planta, a área do vídeo é a **Praça de Eventos de 110,10 m²**, entre a FMW (Loja 76), a Ri Happy (Loja 75) e a escada rolante do Bistrô 81.
- Clique **um ponto no vídeo** e depois **o mesmo ponto na planta**. Repita com **6 a 10 pontos no chão**, espalhados: quinas das vitrines junto ao chão, pontas da borda da praça, cantos do patamar com degraus, base de pilares.
- Aperte `v` para ver a planta sobreposta ao vídeo: as linhas do piso precisam bater.
- Aperte `m` e clique em volta da área do piso que será analisada (a máscara). Aperte `m` de novo para sair.
- Aperte `s` para salvar e `q` para sair. O terminal mostra o **erro médio**: abaixo de 0,3 m está bom.

## 6. Rodar
Teste curto, com 2 segundos:
```powershell
python -m src.experiments.run_shopping --fim 2
```
Se der certo, rode o vídeo inteiro:
```powershell
python -m src.experiments.run_shopping
```
Na primeira execução o YOLO baixa o arquivo `yolov8n.pt`, então é preciso internet.

## 7. Onde ficam os resultados
Em `data\processed\shopping\<data>_praca_eventos\`:

| Arquivo | O que é |
|---|---|
| `video_deteccoes.mp4` | vídeo com caixas, ids e ponto dos pés (verde = usado, vermelho = descartado) |
| `video_trajetorias_planta.mp4` | as pessoas andando na planta |
| `planta_calibrada.png` | planta com os pontos de calibração e a área válida |
| `mapa_permanencia_sobreposto.png` / `_isolado.png` | onde as pessoas **ficaram** (segundos) |
| `mapa_circulacao_sobreposto.png` / `_isolado.png` | por onde as pessoas **passaram** (quantidade) |
| `matriz_permanencia_s.npy`, `matriz_passagens.npy` | os números do mapa |
| `trajetorias.csv` | cada posição: id, quadro, tempo, x e y no vídeo e na planta, e se foi usada |
| `relatorio.md` | resumo: vídeo, contagens, parâmetros, calibração, tempo |

## O que conferir
1. No `video_deteccoes.mp4`: só pessoas têm caixa (manequins não), e cada pessoa mantém o mesmo id.
2. Os pontos dos pés ficam no chão, entre os pés.
3. No `video_trajetorias_planta.mp4`: as pessoas andam no lugar certo da praça.
4. Os mapas mostram calor onde você viu gente no vídeo.

Se a posição na planta estiver deslocada ou torta, o problema é a calibração: refaça o passo 5 com outros pontos.

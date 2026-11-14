# Como publicar o FLUXO360 na web (link público, grátis, sem domínio)

Usamos o **Streamlit Community Cloud**: ele lê o código direto do GitHub e gera um endereço
`https://<nome>.streamlit.app`. Não precisa de domínio, servidor nem VPN, e o link funciona com o
computador de vocês desligado.

## Antes de publicar
1. Envie para o GitHub todos os arquivos desta versão (em especial `dashboard/`, `data/demo/`,
   `data/planta/`, `.streamlit/config.toml` e `dashboard/requirements.txt`):
   ```powershell
   git rm --cached -r data/preferencias      # preferência local que não deve ir para o GitHub
   git add -A
   git commit -m "Versão web do FLUXO360"
   git push
   ```
2. **Decidam a visibilidade** (o repositório tem a planta interna do Capim Dourado):
   - **Repositório público:** qualquer pessoa vê o código e a planta.
   - **Repositório privado (recomendado):** GitHub > Settings > General > *Change visibility*.
     O Streamlit Cloud também publica apps de repositórios privados; nesse caso, confiram na etapa
     *Compartilhar* se o app ficou público ou se é preciso convidar o e-mail do professor.

## Publicar (cerca de 10 minutos)
1. Acesse **https://share.streamlit.io** e clique em **Continue with GitHub**. Autorize o acesso
   (inclusive a repositórios privados, se for o caso).
2. Clique em **Create app** > **Deploy a public app from GitHub** (ou *Yup, I have an app*).
3. Preencha:
   | Campo | Valor |
   |---|---|
   | Repository | `chatcatolica26-rgb/fluxo.360` |
   | Branch | `main` |
   | Main file path | `dashboard/app.py` |
   | App URL | `fluxo360` (se estiver livre: vira `https://fluxo360.streamlit.app`) |
4. Em **Advanced settings**, escolha **Python 3.12**. Não precisa de *Secrets*.
5. Clique em **Deploy**. A primeira publicação leva de 3 a 5 minutos.
6. Abra o link, confira o **Guia rápido**, a aba **Vídeo real** e a tela **07 Como funciona**.
7. Coloque o link no `README.md` (tabela *Acesso rápido*) e envie ao professor.

## Compartilhar
- No app, menu **⋮ > Share** (ou em share.streamlit.io > **Settings > Sharing**):
  *This app is public* = qualquer um com o link; ou convide e-mails específicos.

## Manter
- **Atualizar:** todo `git push` na branch `main` atualiza o app sozinho em 1 ou 2 minutos.
- **"App dormindo":** sem visitas por alguns dias, o app hiberna e mostra *"This app has gone to sleep"*.
  Basta clicar em **Yes, get this app back up!** (leva ~1 minuto). **Abram o link antes da apresentação.**
- **Erros:** em share.streamlit.io, no app, **Manage app** mostra os registros.

## O que muda na versão web
- Roda só o **painel**. A análise de vídeo (YOLO) é pesada para o servidor gratuito e fica na versão
  instalada; a web mostra a análise já processada em `data/demo/`.
- Cada visitante tem a sua sessão: o "Não mostrar ao abrir" do guia e os formulários de acompanhamento
  valem só durante a visita e **não ficam salvos no servidor** (aviso na barra lateral).
- Imagens e vídeos publicados estão **anonimizados** (pessoas pixeladas). Para novas análises que forem
  publicadas, use `python -m src.experiments.run_shopping --anonimizar`.

## Alternativas
| Opção | Quando usar |
|---|---|
| **Hugging Face Spaces** (grátis) | se o Streamlit Cloud não estiver disponível; criar um Space "Streamlit" ligado ao repositório |
| **Link temporário do próprio computador**: `cloudflared tunnel --url http://localhost:8501` | demonstração ao vivo; o link só funciona enquanto o computador e o painel estiverem ligados |

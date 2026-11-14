# Como gerar e testar o instalador do FLUXO360

O cliente recebe **um** destes dois formatos:

| Formato | Para quem | Como gerar |
|---|---|---|
| `FLUXO360-Setup-1.0.1.exe` | cliente final (assistente "Avançar > Instalar") | passos 1 e 2 abaixo |
| `FLUXO360-Instalador-1.0.1.zip` | quando não der para usar o Setup.exe | só o passo 1 |

Os dois instalam em `%LOCALAPPDATA%\FLUXO360`, **sem pedir administrador**, e baixam o Python 3.12 e as
bibliotecas para dentro dessa pasta (com o `uv`). Nada é instalado no resto do Windows.

## 1. Montar o pacote (qualquer computador com o projeto)
```powershell
python instalador/gerar_pacote.py --versao 1.0.1
```
Cria `dist/FLUXO360/` e `dist/FLUXO360-Instalador-1.0.1.zip`. Por padrão leva a análise de demonstração
de `data/demo` (anonimizada) e o vídeo `data/raw/shopping/praca_eventos.mp4` (use `--sem-demo` para não levar).

## 2. Gerar o Setup.exe (Windows)
1. Instale o [Inno Setup 6](https://jrsoftware.org/isdl.php) (gratuito).
2. Abra `instalador/FLUXO360.iss` e clique em **Build > Compile**.
3. O arquivo sai em `dist/FLUXO360-Setup-1.0.1.exe`.

Para uma versão nova, mude `#define Versao` no `.iss` e o `--versao` do passo 1.

## 3. Testar antes de entregar (num Windows "limpo", de preferência outro usuário ou máquina virtual)
- [ ] O Setup abre, mostra os tipos "Painel" e "Completo" e termina sem erro.
- [ ] O atalho **FLUXO360** aparece na área de trabalho e no menu Iniciar.
- [ ] O atalho abre a página "Abrindo o FLUXO360..." e, em até 30 s, o painel.
- [ ] Na primeira abertura aparece o **Guia rápido**.
- [ ] A aba **Vídeo real** e a tela **07 Como funciona** mostram a análise de demonstração.
- [ ] **Encerrar FLUXO360** fecha o painel (o endereço http://localhost:8360 para de responder).
- [ ] Perfil Completo: `".venv\Scripts\python.exe" -m src.experiments.run_shopping --fim 2` roda na pasta do programa.
- [ ] **Desinstalar** remove os atalhos e a pasta (ficam só análises criadas pelo usuário).

## Avisos para a entrega
- **SmartScreen:** o Setup.exe não tem assinatura digital, então o Windows mostra "O Windows protegeu o computador".
  O cliente clica em "Mais informações > Executar assim mesmo". Para tirar o aviso, é preciso um certificado
  de assinatura de código.
- **Internet:** necessária durante a instalação (Python e bibliotecas). Em redes com proxy ou firewall, o
  download de `astral.sh`, `github.com` e `pypi.org` precisa estar liberado.
- **Antivírus:** alguns bloqueiam scripts do PowerShell; se a instalação parar, o registro fica em
  `%LOCALAPPDATA%\FLUXO360\logs\instalacao.log`.
- **Porta:** o painel instalado usa `http://localhost:8360`, para não conflitar com o painel de desenvolvimento (8501).
- **Dados sensíveis:** o pacote leva a planta interna do Capim Dourado. Entregue só a quem pode recebê-la.

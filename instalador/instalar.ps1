<#
  Instalador do FLUXO360 para Windows (uso local, sem precisar de administrador).

  O que faz:
    1. Copia o programa para %LOCALAPPDATA%\FLUXO360 (ou -Destino).
    2. Baixa o "uv" (gerenciador de Python) para dentro da pasta do programa.
    3. Baixa o Python 3.12 e as bibliotecas, também dentro da pasta do programa.
    4. Cria os atalhos "FLUXO360" (área de trabalho e menu Iniciar), "Encerrar FLUXO360" e "Desinstalar FLUXO360".

  Precisa de internet durante a instalação. Depois disso o FLUXO360 funciona sem internet
  (o modelo YOLO do perfil "completo" é baixado na primeira análise de vídeo).

  Uso:
    instalar.ps1                          # pergunta o perfil
    instalar.ps1 -Perfil painel           # só o painel (+ análise de demonstração)
    instalar.ps1 -Perfil completo         # painel + análise de vídeo com YOLO
  Parâmetros usados pelo Setup.exe (Inno Setup): -Destino, -SemCopia, -SemAtalhos, -Silencioso
#>
param(
    [ValidateSet("perguntar", "painel", "completo")][string]$Perfil = "perguntar",
    [string]$Destino = (Join-Path $env:LOCALAPPDATA "FLUXO360"),
    [switch]$SemCopia,
    [switch]$SemAtalhos,
    [switch]$Silencioso
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"          # downloads bem mais rápidos no PowerShell 5
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

$Origem = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$PORTA = 8360

function Etapa([string]$texto) { Write-Host ""; Write-Host ">> $texto" -ForegroundColor Cyan }
function Ok([string]$texto) { Write-Host "   $texto" -ForegroundColor Green }
function Pausar { if (-not $Silencioso) { Write-Host ""; Read-Host "Pressione ENTER para fechar" | Out-Null } }

function Executar([string]$exe, [string[]]$argumentos, [string]$falha) {
    & $exe @argumentos
    if ($LASTEXITCODE -ne 0) { throw "$falha (código $LASTEXITCODE)" }
}

function Criar-Atalho([string]$caminho, [string]$alvo, [string]$argumentos, [string]$icone, [string]$descricao) {
    $shell = New-Object -ComObject WScript.Shell
    $lnk = $shell.CreateShortcut($caminho)
    $lnk.TargetPath = $alvo
    $lnk.Arguments = $argumentos
    $lnk.WorkingDirectory = $Destino
    $lnk.IconLocation = $icone
    $lnk.Description = $descricao
    $lnk.Save()
}

Clear-Host
Write-Host "==============================================" -ForegroundColor White
Write-Host "   FLUXO360 - Instalação"                       -ForegroundColor White
Write-Host "   Do movimento à decisão"                      -ForegroundColor Gray
Write-Host "==============================================" -ForegroundColor White

# ----------------------------------------------------------------- perfil
if ($Perfil -eq "perguntar") {
    if ($Silencioso) { $Perfil = "painel" }
    else {
        Write-Host ""
        Write-Host "Escolha o tipo de instalação:"
        Write-Host "  [1] Painel (recomendado)  - cerca de 500 MB, 5 a 10 minutos"
        Write-Host "      painel completo e análise de vídeo de demonstração"
        Write-Host "  [2] Completo              - cerca de 2 GB, 10 a 25 minutos"
        Write-Host "      painel + análise de vídeo com YOLO (inteligência artificial)"
        $resp = Read-Host "Digite 1 ou 2 e pressione ENTER"
        $Perfil = if ($resp.Trim() -eq "2") { "completo" } else { "painel" }
    }
}
Write-Host ""
Write-Host "Perfil: $Perfil   |   Pasta: $Destino"

try {
    New-Item -ItemType Directory -Force -Path $Destino | Out-Null
    New-Item -ItemType Directory -Force -Path (Join-Path $Destino "logs") | Out-Null
    try { Start-Transcript -Path (Join-Path $Destino "logs\instalacao.log") -Force | Out-Null } catch { }

    # ------------------------------------------------------------ 1. arquivos
    if (-not $SemCopia -and ((Resolve-Path $Origem).Path.TrimEnd('\') -ne (Resolve-Path $Destino).Path.TrimEnd('\'))) {
        Etapa "1/5  Copiando o programa"
        Get-ChildItem -Path $Origem -Force | Where-Object { $_.Name -notin @(".venv", "ferramentas", "logs") } |
            ForEach-Object { Copy-Item -Path $_.FullName -Destination $Destino -Recurse -Force }
        Ok "arquivos copiados"
    } else {
        Etapa "1/5  Arquivos do programa já estão na pasta"
    }
    # arquivos baixados da internet vêm "bloqueados" pelo Windows: libera
    Get-ChildItem -Path $Destino -Recurse -File -ErrorAction SilentlyContinue | Unblock-File -ErrorAction SilentlyContinue

    # ------------------------------------------------------------ 2. uv
    Etapa "2/5  Preparando o gerenciador de Python (uv)"
    $Ferr = Join-Path $Destino "ferramentas"
    New-Item -ItemType Directory -Force -Path $Ferr | Out-Null
    $env:UV_INSTALL_DIR = $Ferr
    $env:UV_NO_MODIFY_PATH = "1"
    $env:UV_UNMANAGED_INSTALL = $Ferr                  # instala só nesta pasta, sem mexer no PATH
    $env:UV_PYTHON_INSTALL_DIR = Join-Path $Ferr "python"
    $env:UV_CACHE_DIR = Join-Path $Ferr "cache"
    $env:UV_LINK_MODE = "copy"
    $uv = Get-ChildItem -Path $Ferr -Filter "uv.exe" -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1
    if (-not $uv) {
        # roda o instalador oficial do uv em outro processo (as variáveis UV_* acima são herdadas)
        $ps = Join-Path $env:WINDIR "System32\WindowsPowerShell\v1.0\powershell.exe"
        & $ps -NoProfile -ExecutionPolicy Bypass -Command "[Net.ServicePointManager]::SecurityProtocol = 'Tls12'; irm https://astral.sh/uv/install.ps1 | iex"
        $uv = Get-ChildItem -Path $Ferr -Filter "uv.exe" -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1
    }
    if (-not $uv) { throw "Não foi possível baixar o uv. Verifique a conexão com a internet." }
    $uv = $uv.FullName
    Ok "uv pronto"

    # ------------------------------------------------------------ 3. Python
    Etapa "3/5  Baixando o Python 3.12 (só na primeira vez)"
    $venv = Join-Path $Destino ".venv"
    $py = Join-Path $venv "Scripts\python.exe"
    if (-not (Test-Path $py)) {
        if (Test-Path $venv) { Remove-Item -Path $venv -Recurse -Force }   # sobra de instalação interrompida
        Executar $uv @("venv", $venv, "--python", "3.12") "Falha ao criar o ambiente Python"
    }
    Ok "Python pronto"

    # ------------------------------------------------------------ 4. bibliotecas
    Etapa "4/5  Instalando as bibliotecas (esta é a etapa mais demorada)"
    $req = @("-r", (Join-Path $Destino "instalador\requirements-painel.txt"))
    if ($Perfil -eq "completo") { $req += @("-r", (Join-Path $Destino "instalador\requirements-analise.txt")) }
    Executar $uv (@("pip", "install", "--python", $py) + $req) "Falha ao instalar as bibliotecas"
    $teste = "import streamlit, pandas, plotly, matplotlib, cv2, yaml, scipy; print('ok')"
    if ($Perfil -eq "completo") { $teste = "import ultralytics; " + $teste }
    Executar $py @("-c", $teste) "As bibliotecas foram instaladas, mas não abriram corretamente"
    try { & $uv cache clean | Out-Null } catch { }      # libera espaço do download
    Ok "bibliotecas instaladas"

    # ------------------------------------------------------------ 5. atalhos
    Etapa "5/5  Configurando o painel e os atalhos"
    $cfgDir = Join-Path $Destino ".streamlit"
    New-Item -ItemType Directory -Force -Path $cfgDir | Out-Null
    Copy-Item (Join-Path $Destino "instalador\config.toml") (Join-Path $cfgDir "config.toml") -Force
    Set-Content -Path (Join-Path $Destino "instalador\perfil.txt") -Value $Perfil -Encoding ASCII

    if (-not $SemAtalhos) {
        $wscript = Join-Path $env:WINDIR "System32\wscript.exe"
        $pwsh = Join-Path $env:WINDIR "System32\WindowsPowerShell\v1.0\powershell.exe"
        $icone = Join-Path $Destino "instalador\fluxo360.ico"
        $vbs = '"' + (Join-Path $Destino "instalador\iniciar.vbs") + '"'
        $menu = Join-Path ([Environment]::GetFolderPath("Programs")) "FLUXO360"
        New-Item -ItemType Directory -Force -Path $menu | Out-Null
        Criar-Atalho (Join-Path ([Environment]::GetFolderPath("Desktop")) "FLUXO360.lnk") $wscript $vbs $icone "Abrir o FLUXO360"
        Criar-Atalho (Join-Path $menu "FLUXO360.lnk") $wscript $vbs $icone "Abrir o FLUXO360"
        Criar-Atalho (Join-Path $menu "Encerrar FLUXO360.lnk") $pwsh ('-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "' + (Join-Path $Destino "instalador\encerrar.ps1") + '"') $icone "Fechar o FLUXO360"
        Criar-Atalho (Join-Path $menu "Desinstalar FLUXO360.lnk") $pwsh ('-NoProfile -ExecutionPolicy Bypass -File "' + (Join-Path $Destino "instalador\desinstalar.ps1") + '"') $icone "Remover o FLUXO360"
        Ok "atalhos criados na área de trabalho e no menu Iniciar"
    }
    Set-Content -Path (Join-Path $Destino "instalador\instalacao_ok.txt") -Value (Get-Date -Format s) -Encoding ASCII

    Write-Host ""
    Write-Host "==============================================" -ForegroundColor Green
    Write-Host "   Instalação concluída!"                       -ForegroundColor Green
    Write-Host "   Abra pelo atalho FLUXO360 na área de trabalho." -ForegroundColor Green
    Write-Host "==============================================" -ForegroundColor Green
    try { Stop-Transcript | Out-Null } catch { }
    if (-not $Silencioso -and $SemAtalhos) { Pausar }        # reparo: mostra o resultado antes de fechar
    if (-not $Silencioso -and -not $SemAtalhos) {
        $abrir = Read-Host "Abrir o FLUXO360 agora? (S/N)"
        if ($abrir.Trim().ToUpper() -ne "N") {
            Start-Process -FilePath (Join-Path $env:WINDIR "System32\wscript.exe") -ArgumentList ('"' + (Join-Path $Destino "instalador\iniciar.vbs") + '"')
        }
    }
    exit 0
}
catch {
    Write-Host ""
    Write-Host "A instalação não foi concluída." -ForegroundColor Red
    Write-Host ("Motivo: " + $_.Exception.Message) -ForegroundColor Red
    Write-Host ("Detalhes em: " + (Join-Path $Destino "logs\instalacao.log")) -ForegroundColor Yellow
    Write-Host "Dica: confira a internet e rode o instalador de novo; ele continua de onde parou." -ForegroundColor Yellow
    try { Stop-Transcript | Out-Null } catch { }
    Pausar
    exit 1
}

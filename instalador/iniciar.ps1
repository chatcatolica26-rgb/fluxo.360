# Abre o FLUXO360: inicia o painel (se ainda não estiver rodando) e abre o navegador.
# Chamado pelo atalho "FLUXO360" (via iniciar.vbs, sem janela preta).
$ErrorActionPreference = "Stop"
$app = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$py = Join-Path $app ".venv\Scripts\python.exe"
$porta = 8360
$url = "http://localhost:$porta"

function Ativo {
    try { $c = New-Object System.Net.Sockets.TcpClient; $c.Connect("127.0.0.1", $porta); $c.Close(); return $true }
    catch { return $false }
}
function Aviso([string]$msg) {
    Add-Type -AssemblyName PresentationFramework
    [System.Windows.MessageBox]::Show($msg, "FLUXO360") | Out-Null
}

if (-not (Test-Path $py)) {
    Aviso "O FLUXO360 não está instalado corretamente. Rode o instalador de novo."
    exit 1
}
if (Ativo) { Start-Process $url; exit 0 }          # já está aberto: só mostra no navegador

# Página "Abrindo o FLUXO360..." enquanto o painel carrega; ela troca sozinha para o painel.
Start-Process (Join-Path $app "instalador\abrindo.html")

$logs = Join-Path $app "logs"
New-Item -ItemType Directory -Force -Path $logs | Out-Null
$comando = '/c ""' + $py + '" -m streamlit run dashboard\app.py > "' + (Join-Path $logs "painel.log") + '" 2>&1"'
Start-Process -FilePath "cmd.exe" -ArgumentList $comando -WorkingDirectory $app -WindowStyle Hidden

for ($i = 0; $i -lt 120; $i++) {                  # espera até 60 s
    Start-Sleep -Milliseconds 500
    if (Ativo) { exit 0 }
}
Aviso ("O painel demorou para abrir. Tente de novo pelo atalho FLUXO360.`n`n" +
       "Se continuar, use 'FLUXO360 - diagnostico' na pasta instalador e envie a mensagem ao suporte.`n" +
       "Registro: " + (Join-Path $logs "painel.log"))
exit 1

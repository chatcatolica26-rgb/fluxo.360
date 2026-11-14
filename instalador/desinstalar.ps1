# Remove o FLUXO360 instalado pelo "Instalar FLUXO360.bat".
# (Se foi instalado pelo FLUXO360-Setup.exe, use "Adicionar ou remover programas" do Windows.)
$app = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Add-Type -AssemblyName PresentationFramework

$unins = Get-ChildItem -Path $app -Filter "unins*.exe" -ErrorAction SilentlyContinue | Select-Object -First 1
if ($unins) { Start-Process $unins.FullName; exit 0 }

$r = [System.Windows.MessageBox]::Show("Remover o FLUXO360 deste computador?`n`nSuas análises e acompanhamentos serão guardados em Documentos\FLUXO360 - dados salvos.", "FLUXO360", "YesNo", "Question")
if ($r -ne "Yes") { exit 0 }

& (Join-Path $app "instalador\encerrar.ps1") -Silencioso
Start-Sleep -Seconds 1

# guarda o que o usuário produziu
$backup = Join-Path ([Environment]::GetFolderPath("MyDocuments")) "FLUXO360 - dados salvos"
foreach ($sub in @("data\processed", "data\acompanhamento")) {
    $p = Join-Path $app $sub
    if ((Test-Path $p) -and (Get-ChildItem $p -Recurse -File -ErrorAction SilentlyContinue)) {
        New-Item -ItemType Directory -Force -Path $backup | Out-Null
        Copy-Item -Path $p -Destination $backup -Recurse -Force
    }
}

# atalhos
Remove-Item (Join-Path ([Environment]::GetFolderPath("Desktop")) "FLUXO360.lnk") -Force -ErrorAction SilentlyContinue
Remove-Item (Join-Path ([Environment]::GetFolderPath("Programs")) "FLUXO360") -Recurse -Force -ErrorAction SilentlyContinue

# programa
Set-Location $env:TEMP
Remove-Item -Path $app -Recurse -Force -ErrorAction SilentlyContinue
$msg = "O FLUXO360 foi removido."
if (Test-Path $backup) { $msg += "`n`nSeus dados foram guardados em:`n$backup" }
if (Test-Path $app) { $msg += "`n`nAlguns arquivos estavam em uso. Apague a pasta manualmente:`n$app" }
[System.Windows.MessageBox]::Show($msg, "FLUXO360") | Out-Null

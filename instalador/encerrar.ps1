# Fecha o FLUXO360 (encerra o painel que roda em segundo plano).
$porta = 8360
$conexoes = Get-NetTCPConnection -LocalPort $porta -State Listen -ErrorAction SilentlyContinue
foreach ($c in $conexoes) { Stop-Process -Id $c.OwningProcess -Force -ErrorAction SilentlyContinue }
if (-not $args -or $args[0] -ne "-Silencioso") {
    Add-Type -AssemblyName PresentationFramework
    $texto = if ($conexoes) { "O FLUXO360 foi encerrado." } else { "O FLUXO360 já estava fechado." }
    [System.Windows.MessageBox]::Show($texto, "FLUXO360") | Out-Null
}

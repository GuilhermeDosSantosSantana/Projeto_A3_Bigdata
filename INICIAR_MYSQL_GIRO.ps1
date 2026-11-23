$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
$server = 'C:\Program Files\MySQL\MySQL Server 8.4\bin\mysqld.exe'
$client = 'C:\Program Files\MySQL\MySQL Server 8.4\bin\mysql.exe'
$workbench = Join-Path $env:LOCALAPPDATA 'Programs\MySQL\MySQL Workbench\MySQL Workbench.exe'
$options = Join-Path $root 'mysql\runtime\demo.cnf'
$config = Join-Path $root 'mysql\my.ini'

foreach ($file in @($server, $client, $workbench, $options, $config)) {
    if (-not (Test-Path -LiteralPath $file)) { throw "Arquivo ausente: $file" }
}

& $client "--defaults-extra-file=$options" --batch --skip-column-names --execute='SELECT 1' *> $null
if ($LASTEXITCODE -ne 0) {
    Start-Process -FilePath $server -ArgumentList "--defaults-file=$config" -WindowStyle Hidden
    $ready = $false
    for ($i = 0; $i -lt 30; $i++) {
        Start-Sleep -Seconds 1
        & $client "--defaults-extra-file=$options" --batch --skip-column-names --execute='SELECT 1' *> $null
        if ($LASTEXITCODE -eq 0) { $ready = $true; break }
    }
    if (-not $ready) { throw 'O MySQL nao respondeu em 30 segundos. Veja mysql/runtime/mysql-error.log.' }
}

$count = & $client "--defaults-extra-file=$options" --batch --skip-column-names --execute='SELECT COUNT(*) FROM giro_a3.sale;'
if ($LASTEXITCODE -ne 0) { throw 'O esquema giro_a3 nao respondeu.' }
Write-Host "MySQL pronto. Vendas na base: $count. Abrindo o Workbench..."
Start-Process -FilePath $workbench

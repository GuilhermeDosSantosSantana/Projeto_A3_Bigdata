$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
$mysql = 'C:\Program Files\MySQL\MySQL Server 8.4\bin\mysql.exe'
$mysqld = 'C:\Program Files\MySQL\MySQL Server 8.4\bin\mysqld.exe'
$config = Join-Path $root 'mysql\my.ini'
$rootCredentials = Join-Path $root 'mysql\runtime\root.cnf'
$appCredentials = Join-Path $root 'mysql\runtime\app.cnf'
$python = Join-Path $root '.venv\Scripts\python.exe'
$url = 'http://127.0.0.1:3000'

if (-not (Test-Path -LiteralPath $python)) { $python = (Get-Command python -ErrorAction Stop).Source }
foreach ($file in @($mysql, $rootCredentials)) {
    if (-not (Test-Path -LiteralPath $file)) { throw "Arquivo ausente: $file" }
}

function Test-MySQL {
    $ErrorActionPreference = 'Continue'
    & $mysql "--defaults-extra-file=$rootCredentials" --batch --skip-column-names --execute='SELECT 1' 2>$null | Out-Null
    return ($LASTEXITCODE -eq 0)
}

if (-not (Test-MySQL)) {
    $service = Get-Service -Name 'MySQL*' -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($service) {
        if ($service.Status -ne 'Running') { Start-Service -Name $service.Name }
    } elseif ((Test-Path -LiteralPath $mysqld) -and (Test-Path -LiteralPath (Join-Path $root 'mysql\runtime\data'))) {
        Start-Process -FilePath $mysqld -ArgumentList "--defaults-file=$config" -WindowStyle Hidden
    } else {
        throw 'MySQL nao configurado. Execute INSTALAR_GIRO.bat e finalize o MySQL Configurator.'
    }
    $ready = $false
    for ($i = 0; $i -lt 30; $i++) {
        Start-Sleep -Seconds 1
        if (Test-MySQL) { $ready = $true; break }
    }
    if (-not $ready) { throw 'O MySQL nao respondeu. Veja mysql/runtime/mysql-error.log.' }
}

if (-not (Test-Path -LiteralPath $appCredentials)) {
    Push-Location $root
    try { & $python -m scripts.configurar_app_mysql } finally { Pop-Location }
}

$redisReady = $false
try {
    $socket = New-Object System.Net.Sockets.TcpClient('127.0.0.1', 6379)
    $socket.Close()
    $redisReady = $true
} catch { }
if (-not $redisReady -and (Get-Command wsl.exe -ErrorAction SilentlyContinue)) {
    $ErrorActionPreference = 'Continue'
    try { & wsl.exe --user root --exec systemctl start redis-server 2>$null | Out-Null } catch { }
    $ErrorActionPreference = 'Stop'
}

try { $health = Invoke-RestMethod -Uri "$url/api/health" -TimeoutSec 3 } catch { $health = $null }
if (-not $health -or -not $health.ok -or $health.database -ne 'MySQL') {
    New-Item -ItemType Directory -Force -Path (Join-Path $root 'storage') | Out-Null
    Start-Process -FilePath $python -ArgumentList '-m giro.server' -WorkingDirectory $root -WindowStyle Hidden -RedirectStandardOutput (Join-Path $root 'storage/server.log') -RedirectStandardError (Join-Path $root 'storage/server-error.log')
    $ready = $false
    for ($i = 0; $i -lt 30; $i++) {
        Start-Sleep -Seconds 1
        try {
            $health = Invoke-RestMethod -Uri "$url/api/health" -TimeoutSec 3
            if ($health.ok -and $health.database -eq 'MySQL') { $ready = $true; break }
        } catch { }
    }
    if (-not $ready) { throw 'O servidor web nao respondeu. Veja storage/server-error.log.' }
}

Write-Host "GIRO pronto: $url (MySQL conectado; cache: $($health.cache))"
Start-Process $url

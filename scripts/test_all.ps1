$ErrorActionPreference = "Stop"
$Utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[Console]::InputEncoding = $Utf8NoBom
[Console]::OutputEncoding = $Utf8NoBom
$OutputEncoding = $Utf8NoBom
try { chcp 65001 | Out-Null } catch { }
$Project = "actas_tests"
$EnvFile = ".env.test"
$ComposeBase = @(
    "-p", $Project,
    "--env-file", $EnvFile,
    "-f", "docker-compose.yml",
    "-f", "docker-compose.test.yml"
)

function Invoke-Compose {
    param(
        [Parameter(Mandatory = $true)]
        [string[]]$Arguments,
        [switch]$AllowFailure,
        [switch]$Quiet
    )

    # Windows PowerShell 5 convierte stderr de programas nativos en NativeCommandError
    # cuando ErrorActionPreference es Stop. Se captura todo y se valida el código real.
    $previousPreference = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        $output = & docker compose @ComposeBase @Arguments 2>&1
        $exitCode = $LASTEXITCODE
    }
    finally {
        $ErrorActionPreference = $previousPreference
    }

    if (-not $Quiet -and $null -ne $output) {
        $output | ForEach-Object { Write-Host $_ }
    }

    if ($exitCode -ne 0 -and -not $AllowFailure) {
        throw "docker compose falló con código ${exitCode}: $($Arguments -join ' ')"
    }

    return @{ ExitCode = $exitCode; Output = $output }
}

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw "Docker no está instalado o no está disponible en PATH."
}

if (-not (Test-Path $EnvFile)) {
    Copy-Item ".env.test.example" $EnvFile
    Write-Host "Se creó .env.test con credenciales exclusivas de prueba." -ForegroundColor Cyan
}

New-Item -ItemType Directory -Force -Path "test-artifacts" | Out-Null

# Verificación de seguridad: las pruebas nunca deben apuntar al volumen real.
$configResult = Invoke-Compose -Arguments @("config") -Quiet
$configText = ($configResult.Output | Out-String)
if ($configText -notmatch "actas_tests_pgdata") {
    throw "Configuración insegura: el entorno de pruebas no usa actas_tests_pgdata. No se ejecutó ningún borrado."
}
if ($configText -match "name:\s*actas_microservices_pgdata") {
    throw "Configuración insegura: el entorno de pruebas intenta usar el volumen real actas_microservices_pgdata."
}

$testsPassed = $false
try {
    Write-Host "Limpiando únicamente el entorno aislado de pruebas..." -ForegroundColor Cyan
    Invoke-Compose -Arguments @("down", "-v", "--remove-orphans") -AllowFailure | Out-Null

    Write-Host "Construyendo y levantando microservicios de prueba..." -ForegroundColor Cyan
    Invoke-Compose -Arguments @("up", "-d", "--build") | Out-Null

    Write-Host "Construyendo ejecutor de pruebas..." -ForegroundColor Cyan
    Invoke-Compose -Arguments @("--profile", "tests", "build", "test-runner") | Out-Null

    Write-Host "Ejecutando pruebas unitarias, integración, interfaz y restauración..." -ForegroundColor Cyan
    Invoke-Compose -Arguments @("--profile", "tests", "run", "--rm", "test-runner") | Out-Null

    $testsPassed = $true
    Write-Host "Todas las pruebas terminaron correctamente." -ForegroundColor Green
}
finally {
    Write-Host "Guardando evidencias..." -ForegroundColor Cyan

    $psResult = Invoke-Compose -Arguments @("ps", "-a") -AllowFailure -Quiet
    $psResult.Output | Out-File "test-artifacts/compose-ps.txt" -Encoding utf8

    $logsResult = Invoke-Compose -Arguments @("logs", "--no-color") -AllowFailure -Quiet
    $logsResult.Output | Out-File "test-artifacts/docker.log" -Encoding utf8

    Write-Host "Eliminando únicamente contenedores y volúmenes de actas_tests..." -ForegroundColor Cyan
    Invoke-Compose -Arguments @("down", "-v", "--remove-orphans") -AllowFailure | Out-Null
}

if (-not $testsPassed) {
    throw "Una o más pruebas fallaron. Revise la carpeta test-artifacts."
}

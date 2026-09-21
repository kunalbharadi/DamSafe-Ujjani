param([switch]$Preview)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath (Split-Path -Parent $PSScriptRoot)
if (-not (Test-Path -LiteralPath '.env')) { Copy-Item -LiteralPath '.env.example' -Destination '.env' }
if (-not $Preview) {
    docker compose up --build
    if ($LASTEXITCODE -ne 0) { throw 'Docker stack did not start. Start Docker Desktop, or use -Preview for an explicit SQLite setup preview.' }
    exit
}
$pythonPath = Join-Path (Get-Location) '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pythonPath)) { py -3.12 -m venv .venv; & $pythonPath -m pip install uv }
& $pythonPath -m uv sync --locked
if ($LASTEXITCODE -ne 0) { throw 'Dependency setup failed' }
Push-Location frontend
try {
    npm.cmd ci
    if ($LASTEXITCODE -ne 0) { throw 'Frontend installation failed' }
    npm.cmd run build
    if ($LASTEXITCODE -ne 0) { throw 'Frontend build failed' }
} finally { Pop-Location }
$env:DAMSAFE_DATABASE_URL = 'sqlite:///' + ((Join-Path (Get-Location) '.local\damsafe.db') -replace '\\','/')
$env:DAMSAFE_STORAGE_ROOT = Join-Path (Get-Location) '.local\objects'
& $pythonPath -m alembic upgrade head
if ($LASTEXITCODE -ne 0) { throw 'Migration failed' }
& $pythonPath scripts\bootstrap.py
if ($LASTEXITCODE -ne 0) { throw 'Bootstrap failed' }
& $pythonPath scripts\register_phase2_examples.py
if ($LASTEXITCODE -ne 0) { throw 'Pinned Phase 2 evidence registration failed' }
Write-Host 'DamSafe preview: http://127.0.0.1:8000 (SQLite; numerical examples require their installed Docker images)'
$workerProcess = Start-Process -FilePath $pythonPath -ArgumentList '-m','damsafe.worker' -WindowStyle Hidden -PassThru
$numericalProcess = Start-Process -FilePath $pythonPath -ArgumentList '-m','damsafe.numerics.worker' -WindowStyle Hidden -PassThru
try { & $pythonPath -m uvicorn damsafe.api:create_app --factory --host 127.0.0.1 --port 8000 }
finally {
    if (-not $workerProcess.HasExited) { Stop-Process -Id $workerProcess.Id }
    if (-not $numericalProcess.HasExited) { Stop-Process -Id $numericalProcess.Id }
}

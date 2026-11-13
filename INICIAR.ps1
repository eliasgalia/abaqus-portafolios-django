$ErrorActionPreference = 'Stop'
Push-Location $PSScriptRoot
try {
    if (-not (Test-Path -LiteralPath '.venv\Scripts\python.exe')) {
        python -m venv .venv
        if ($LASTEXITCODE -ne 0) { throw 'No se pudo crear el entorno virtual.' }
        & '.\.venv\Scripts\python.exe' -m pip install -r requirements.txt
        if ($LASTEXITCODE -ne 0) { throw 'No se pudieron instalar las dependencias.' }
    }
    & '.\.venv\Scripts\python.exe' manage.py migrate
    if ($LASTEXITCODE -ne 0) { throw 'Fallo de migraciones.' }
    & '.\.venv\Scripts\python.exe' manage.py import_portfolios data/datos.xlsx
    if ($LASTEXITCODE -ne 0) { throw 'Fallo de importacion. Revisar datos.' }
    Write-Host 'Abre http://127.0.0.1:8000/ en el navegador. Ctrl+C para detener.'
    & '.\.venv\Scripts\python.exe' manage.py runserver 127.0.0.1:8000 --noreload
} finally {
    Pop-Location
}

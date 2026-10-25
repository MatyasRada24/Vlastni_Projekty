$ErrorActionPreference = 'Stop'
Push-Location $PSScriptRoot
try {
    $env:PYINSTALLER_CONFIG_DIR = Join-Path $PSScriptRoot 'build\pyinstaller-cache'
    python -m PyInstaller --noconfirm --clean --onefile --windowed --name Kontrola_SEO_1.0 --manifest windows.manifest main.py
    if ($LASTEXITCODE -ne 0) { throw 'Sestaveni aplikace selhalo.' }
} finally {
    Pop-Location
}

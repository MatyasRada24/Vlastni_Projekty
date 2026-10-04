@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    python -m venv .venv
    if errorlevel 1 goto fail
)
".venv\Scripts\python.exe" -c "import PySide6" >nul 2>&1
if errorlevel 1 (
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt
    if errorlevel 1 goto fail
)
".venv\Scripts\python.exe" app.py
if errorlevel 1 goto fail
exit /b 0
:fail
echo.
echo Spusteni se nezdarilo. Viz chyba vyse a navod v README.md.
pause
exit /b 1

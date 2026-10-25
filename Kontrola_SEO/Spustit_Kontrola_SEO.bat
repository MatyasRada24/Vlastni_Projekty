@echo off
cd /d "%~dp0"
if exist "dist\Kontrola_SEO_1.0.exe" (
    start "" "dist\Kontrola_SEO_1.0.exe"
    exit /b
)
python main.py
if errorlevel 1 pause

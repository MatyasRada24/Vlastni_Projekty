@echo off
setlocal
cd /d "%~dp0"
echo Pulse Player - sestaveni aplikace
if not exist ".venv\Scripts\python.exe" (
    python -m venv .venv
    if errorlevel 1 goto error
)
.venv\Scripts\python.exe -m ensurepip --upgrade
if errorlevel 1 goto error
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 goto error
.venv\Scripts\python.exe tools\setup_ffmpeg.py
if errorlevel 1 goto error
.venv\Scripts\python.exe -m unittest discover -s tests -v
if errorlevel 1 goto error
.venv\Scripts\python.exe -m PyInstaller --clean --noconfirm "Pulse Music Player.spec"
if errorlevel 1 goto error
echo Hotovo: dist\Pulse Music Player.exe
pause
exit /b 0
:error
echo Sestaveni selhalo. Podrobnosti jsou vyse.
pause
exit /b 1

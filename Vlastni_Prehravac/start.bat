@echo off
cd /d "%~dp0"
if exist "dist\Pulse Music Player.exe" (
    start "" "dist\Pulse Music Player.exe" %*
) else (
    .venv\Scripts\pythonw.exe app.py %*
)

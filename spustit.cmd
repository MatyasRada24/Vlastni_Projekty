@echo off
cd /d "%~dp0"
if not exist node_modules (
  echo Nejprve v teto slozce spustte npm.cmd install
  pause
  exit /b 1
)
echo Otevrete http://127.0.0.1:3210 v prohlizeci.
node --env-file-if-exists=.env server.js
pause

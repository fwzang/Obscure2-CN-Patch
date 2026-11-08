@echo off
setlocal
set "GD=D:\SteamLibrary\steamapps\common\Obscure2"

set O2_WIN=0

echo ===== run with O2_WIN=0 (exclusive fullscreen) =====

tasklist /fi "imagename eq Obscure2.exe" 2>nul | findstr /i "Obscure2.exe" >nul
if not errorlevel 1 (
  echo [ERROR] Game is running. Exit it completely first.
  pause
  exit /b 1
)

start "" "%GD%\Obscure2.exe"

echo WARNING: this reproduces the Alt+Tab freeze on purpose. Control only.

pause

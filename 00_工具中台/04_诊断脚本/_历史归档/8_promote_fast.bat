@echo off
setlocal
set "GD=D:\SteamLibrary\steamapps\common\Obscure2"

set O2_PROMOTE_N=5

echo ===== run with O2_PROMOTE_N=5 (faster font promotion) =====
echo Use this if you see a brief garbled flash at startup.
echo Lower threshold = font recognised sooner, flash shorter.

tasklist /fi "imagename eq Obscure2.exe" 2>nul | findstr /i "Obscure2.exe" >nul
if not errorlevel 1 (
  echo [ERROR] Game is running. Exit it completely first.
  pause
  exit /b 1
)

start "" "%GD%\Obscure2.exe"

pause

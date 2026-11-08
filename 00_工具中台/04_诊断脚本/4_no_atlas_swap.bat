@echo off
setlocal
set "GD=D:\SteamLibrary\steamapps\common\Obscure2"

set O2_NO_SWAP=1

echo ===== run with O2_NO_SWAP=1 (atlas swap OFF) =====

tasklist /fi "imagename eq Obscure2.exe" 2>nul | findstr /i "Obscure2.exe" >nul
if not errorlevel 1 (
  echo [ERROR] Game is running. Exit it completely first.
  pause
  exit /b 1
)

start "" "%GD%\Obscure2.exe"

echo Chinese text will look broken - EXPECTED. Tells you if a texture was eaten by the swap.

pause

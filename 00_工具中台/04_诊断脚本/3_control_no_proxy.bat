@echo off
setlocal
set "GD=D:\SteamLibrary\steamapps\common\Obscure2"

echo ===== control: run WITHOUT proxy d3d9.dll =====

tasklist /fi "imagename eq Obscure2.exe" 2>nul | findstr /i "Obscure2.exe" >nul
if not errorlevel 1 (
  echo [ERROR] Game is running. Exit it completely first.
  pause
  exit /b 1
)

if exist "%GD%\d3d9.dll" move /y "%GD%\d3d9.dll" "%GD%\d3d9_off.bak" >nul
if exist "%GD%\d3d9proxy.log" move /y "%GD%\d3d9proxy.log" "%GD%\d3d9proxy_prev.log" >nul
echo Proxy removed. Chinese text will look broken - EXPECTED.
echo Use it to separate "our DLL" from "the game itself".
start "" "%GD%\Obscure2.exe"

pause

@echo off
setlocal
set "GD=D:\SteamLibrary\steamapps\common\Obscure2"

echo ===== remove d3d9.dll (vanilla rendering) =====

tasklist /fi "imagename eq Obscure2.exe" 2>nul | findstr /i "Obscure2.exe" >nul
if not errorlevel 1 (
  echo [ERROR] Game is running. Exit it completely first.
  pause
  exit /b 1
)

if exist "%GD%\d3d9.dll" del /q "%GD%\d3d9.dll"
echo Done. Chinese text gone; game uses system d3d9.dll.

pause

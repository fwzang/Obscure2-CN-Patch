@echo off
setlocal
set "GD=D:\SteamLibrary\steamapps\common\Obscure2"

echo ===== install release d3d9.dll (V1.03.2) =====

tasklist /fi "imagename eq Obscure2.exe" 2>nul | findstr /i "Obscure2.exe" >nul
if not errorlevel 1 (
  echo [ERROR] Game is running. Exit it completely first.
  pause
  exit /b 1
)

ver >nul
copy /v /y "%~dp0d3d9_release.dll" "%GD%\d3d9.dll" >nul
if errorlevel 1 (
  echo [ERROR] copy failed - d3d9.dll locked
  pause
  exit /b 1
)
echo Installed:
certutil -hashfile "%GD%\d3d9.dll" MD5 | findstr /v ":"
echo Expect: 6326d10ca1d7c760becc1c4b6e0442a8

pause

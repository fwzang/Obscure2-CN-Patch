@echo off
setlocal
set "GD=D:\SteamLibrary\steamapps\common\Obscure2"

echo ===== collect d3d9proxy.log =====

if not exist "%GD%\d3d9proxy.log" (
  echo [ERROR] no log found. Run the game once first.
  pause
  exit /b 1
)
set "TS=%DATE:~0,4%%DATE:~5,2%%DATE:~8,2%_%TIME:~0,2%%TIME:~3,2%%TIME:~6,2%"
set "TS=%TS: =0%"
copy /y "%GD%\d3d9proxy.log" "%~dp0log_%TS%.log" >nul
echo Saved: %~dp0log_%TS%.log

pause

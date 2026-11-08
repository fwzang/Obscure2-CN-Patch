@echo off
rem ============================================================
rem  8b_promote_texture_first.bat
rem  Launch Obscure II in "texture-first" font-promotion mode.
rem
rem  Why: V69_PROD promotes a stage0-bound 512x256 texture to "font"
rem       after O2_PROMOTE_N bindings (default 1). With threshold 1,
rem       one-off UI / message textures (bound only 2-8 times) are
rem       promoted too and get swapped to the Chinese atlas ->
rem       that texture disappears (observed at 2560x1440).
rem       Threshold 5 keeps them (bound < 5) while the real font
rem       atlas (bound 100+ times) is still promoted almost at once.
rem
rem  This script changes NO file. It only sets an env var for the
rem  launched process and starts the game.
rem  (8_promote_fast.bat does the same but hardcodes a D: path and
rem   sets 5 with an inverted comment - this one auto-detects.)
rem ============================================================
setlocal

set "O2_PROMOTE_N=5"

set "GD="
if exist "E:\SteamLibrary\steamapps\common\Obscure2\Obscure2.exe" set "GD=E:\SteamLibrary\steamapps\common\Obscure2"
if not defined GD if exist "D:\SteamLibrary\steamapps\common\Obscure2\Obscure2.exe" set "GD=D:\SteamLibrary\steamapps\common\Obscure2"
if not defined GD if exist "C:\SteamLibrary\steamapps\common\Obscure2\Obscure2.exe" set "GD=C:\SteamLibrary\steamapps\common\Obscure2"
if not defined GD if exist "C:\Program Files (x86)\Steam\steamapps\common\Obscure2\Obscure2.exe" set "GD=C:\Program Files (x86)\Steam\steamapps\common\Obscure2"

if not defined GD (
  echo [ERROR] Obscure2.exe not found in the usual Steam paths.
  echo         Drag the game folder into this window and press Enter:
  set /p "GD="
  set "GD=%GD:"=%"
)
if not exist "%GD%\Obscure2.exe" (
  echo [ERROR] Obscure2.exe not found under: %GD%
  pause
  exit /b 1
)

tasklist /fi "imagename eq Obscure2.exe" 2>nul | findstr /i "Obscure2.exe" >nul
if not errorlevel 1 (
  echo [ERROR] Game is already running. Exit it first.
  pause
  exit /b 1
)

echo ============================================================
echo  O2_PROMOTE_N = %O2_PROMOTE_N%   (texture-first mode)
echo  Game dir     = %GD%
echo ============================================================
echo  Expected log lines after launch:
echo    [FSTRICT] binding-promote threshold = 5
echo    [FSTRICT] promote tex=... (stage0 bind x5)
echo  If a texture is STILL missing, edit the line above to 9 and retry.
echo.

start "" "%GD%\Obscure2.exe"
endlocal
exit /b 0

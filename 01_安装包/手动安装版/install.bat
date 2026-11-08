@echo off
rem ============================================================
rem  install.bat - manual install (scheme B / live-kai)
rem  Requires: python (with the same interpreter used to build),
rem            vanilla game datapack.hvp, and this folder's files.
rem  Steps: verify vanilla -> backup -> rebuild CN pack -> install d3d9.dll
rem ============================================================
setlocal enableextensions enabledelayedexpansion
cd /d "%~dp0"

set "MD5_DLL=b42417bd2a51ff5d95d3a84970b8a20f"

echo ============================================================
echo  Manual install (scheme B) - Obscure II CN patch
echo ============================================================

set "PY="
where py >nul 2>&1 && set "PY=py -3"
if not defined PY where python >nul 2>&1 && set "PY=python"
if not defined PY (
  echo [ERROR] python not found. Install Python 3.8+ and add it to PATH.
  pause
  exit /b 1
)

echo [..] Drag the game folder (containing Obscure2.exe) here and press Enter:
set /p "GD="
set "GD=%GD:"=%"
if not exist "%GD%\Obscure2.exe" (
  echo [ERROR] Obscure2.exe not found in: %GD%
  pause
  exit /b 1
)
if not exist "%GD%\datapack.hvp" (
  echo [ERROR] datapack.hvp not found in: %GD%
  pause
  exit /b 1
)

tasklist /fi "imagename eq Obscure2.exe" 2>nul | findstr /i "Obscure2.exe" >nul
if not errorlevel 1 (
  echo [ERROR] Game is running. Exit it completely first.
  pause
  exit /b 1
)

echo [..] Rebuilding the Chinese data pack from the delta ...
%PY% "%~dp0apply_delta.py" --delta "%~dp0datapack.delta" --game-dir "%GD%"
if errorlevel 1 (
  echo [ERROR] data pack rebuild failed. Nothing else was changed.
  pause
  exit /b 1
)

echo [..] Installing the font proxy d3d9.dll ...
copy /v /y "%~dp0d3d9.dll" "%GD%\d3d9.dll" >nul
if errorlevel 1 (
  echo [ERROR] could not write d3d9.dll
  pause
  exit /b 1
)
for /f "usebackq skip=1 delims=" %%L in (`certutil -hashfile "%GD%\d3d9.dll" MD5`) do if not defined __H set "__H=%%L"
set "__H=%__H: =%"
echo      installed d3d9.dll md5 = %__H%
if /i not "%__H%"=="%MD5_DLL%" (
  echo [WARN] md5 differs from expected %MD5_DLL%
)

echo.
echo ============================================================
echo  INSTALL DONE.
echo   data pack : rebuilt from vanilla via delta
echo   proxy     : %GD%\d3d9.dll
echo   backup    : %GD%\datapack.hvp.o2bak
echo  Start the game now. Log: %GD%\d3d9proxy.log
echo  To restore: run restore.bat in this folder
echo ============================================================
pause
endlocal
exit /b 0

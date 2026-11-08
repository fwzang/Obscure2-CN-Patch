@echo off
rem ============================================================
rem  restore.bat - restore the original game data pack
rem  Removes our d3d9.dll (only if its md5 matches ours) and
rem  restores datapack.hvp from the backup made at install time.
rem ============================================================
setlocal enableextensions enabledelayedexpansion
cd /d "%~dp0"

set "MD5_OURS_B=b42417bd2a51ff5d95d3a84970b8a20f"
set "MD5_OURS_A=1e2a38adac855179119ff4f4fd567622"
set "MD5_OURS_B_OLD=6326d10ca1d7c760becc1c4b6e0442a8"
set "MD5_OURS_A_OLD=d0295c8726721c20274ae8a8dc13b109"
set "MD5_VANILLA=04a96eff7978cf31e66e9354421f1516"

echo ============================================================
echo  Restore to vanilla
echo ============================================================
echo [..] Drag the game folder here and press Enter:
set /p "GD="
set "GD=%GD:"=%"
if not exist "%GD%\Obscure2.exe" (
  echo [ERROR] Obscure2.exe not found in: %GD%
  pause
  exit /b 1
)
tasklist /fi "imagename eq Obscure2.exe" 2>nul | findstr /i "Obscure2.exe" >nul
if not errorlevel 1 (
  echo [ERROR] Game is running. Exit it first.
  pause
  exit /b 1
)

if exist "%GD%\d3d9.dll" (
  for /f "usebackq skip=1 delims=" %%L in (`certutil -hashfile "%GD%\d3d9.dll" MD5`) do if not defined __H set "__H=%%L"
  set "__H=%__H: =%"
  if /i "%__H%"=="%MD5_OURS_B%" (
    del "%GD%\d3d9.dll"
    echo [OK] removed our d3d9.dll
  ) else if /i "%__H%"=="%MD5_OURS_A%" (
    del "%GD%\d3d9.dll"
    echo [OK] removed our d3d9.dll (scheme A build)
  ) else (
    echo [WARN] d3d9.dll md5 %__H% is not ours - left untouched
  )
)

if exist "%GD%\datapack.hvp.o2bak" (
  for /f "usebackq skip=1 delims=" %%L in (`certutil -hashfile "%GD%\datapack.hvp.o2bak" MD5`) do if not defined __B set "__B=%%L"
  set "__B=%__B: =%"
  if /i "%__B%"=="%MD5_VANILLA%" (
    copy /v /y "%GD%\datapack.hvp.o2bak" "%GD%\datapack.hvp" >nul
    echo [OK] datapack.hvp restored to vanilla
  ) else (
    echo [ERROR] backup is not the vanilla pack (md5 %__B%) - NOT restored
  )
) else (
  echo [WARN] no backup datapack.hvp.o2bak found - data pack left as is
)

echo.
echo [DONE] Restore finished.
pause
endlocal
exit /b 0

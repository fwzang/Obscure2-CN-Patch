@echo off
rem ============================================================
rem  R_restore_plain.bat
rem  Remove our proxy so the game goes back to the stock
rem  SysWOW64\d3d9.dll (pure vanilla, no wrapper at all).
rem ============================================================
setlocal
set "G=E:\SteamLibrary\steamapps\common\Obscure2"
set "ARC=%~dp0_removed"

if not exist "%G%\Obscure2.exe" ( echo [ERROR] game not found: %G% & pause & exit /b 1 )
tasklist /fi "imagename eq Obscure2.exe" 2>nul | findstr /i "Obscure2.exe" >nul
if not errorlevel 1 ( echo [ERROR] game is running. Exit it first. & pause & exit /b 1 )

if not exist "%ARC%" mkdir "%ARC%"

for %%F in ("%G%\d3d9.dll") do (
  if exist "%%~fF" (
    echo   moving d3d9.dll to archive...
    move /y "%%~fF" "%ARC%\d3d9.dll" >nul
  )
)
if exist "%G%\dxvk.conf"          move /y "%G%\dxvk.conf"          "%ARC%\dxvk.conf" >nul
if exist "%G%\D3D9.dll"           move /y "%G%\D3D9.dll"           "%ARC%\D3D9_upper.dll" >nul
if exist "%G%\dgVoodoo.conf"      move /y "%G%\dgVoodoo.conf"      "%ARC%\dgVoodoo.conf" >nul

echo.
echo  Done. The game now uses the stock system d3d9.dll.
echo  Scripts / zips in the game folder are left untouched.
echo.
pause
endlocal
exit /b 0

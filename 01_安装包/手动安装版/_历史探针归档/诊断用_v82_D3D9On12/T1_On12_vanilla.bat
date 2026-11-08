@echo off
rem ============================================================
rem  T1_On12_vanilla.bat
rem  Test: D3D9On12 (D3D9 over D3D12) on the VANILLA game data.
rem
rem  Single variable: d3d9.dll = our proxy in On12 mode.
rem  Font replacement is DISABLED and the vertex tampering (v79)
rem  is DISABLED, so the picture is plain English -> the only thing
rem  that can change the bathroom decal is the D3D12 backend.
rem ============================================================
setlocal
set "G=E:\SteamLibrary\steamapps\common\Obscure2"

if not exist "%G%\Obscure2.exe" ( echo [ERROR] game not found: %G% & pause & exit /b 1 )
tasklist /fi "imagename eq Obscure2.exe" 2>nul | findstr /i "Obscure2.exe" >nul
if not errorlevel 1 ( echo [ERROR] game is running. Exit it first. & pause & exit /b 1 )

rem --- the only switches that matter ---
set "O2_D3D9ON12=1"
set "O2_NO_SWAP=1"
set "O2_NO_V79=0"

cd /d "%G%"
echo ============================================================
echo   d3d9.dll  = proxy v82 (md5 e1b360fb...)  On12 mode
echo   datapack  = vanilla
echo   O2_D3D9ON12=1   O2_NO_SWAP=1   O2_NO_V79=0
echo.
echo   Starting the game from THIS script so the env vars
echo   are inherited. Do NOT double-click Obscure2.exe.
echo ============================================================
start "" "%G%\Obscure2.exe"
echo.
echo  What to check after playing:
echo    1) d3d9proxy.log should contain:
echo         [ON12] Direct3DCreate9On12 sdk=32 -^> obj=...
echo       If it says "returned NULL" or "not exported", On12 did
echo       NOT engage and this run proves nothing.
echo    2) In the bathroom: is the prompt decal visible?
echo.
pause
endlocal
exit /b 0

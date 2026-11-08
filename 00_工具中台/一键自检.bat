@echo off
setlocal
cd /d "%~dp0.."

echo ============================================
echo   Obscure II  Package Self-Check
echo ============================================
echo
where python >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Python not found in PATH. Install Python 3.8+ first.
  pause
  exit /b 1
)
python "%~dp0selfcheck.py"
echo
pause

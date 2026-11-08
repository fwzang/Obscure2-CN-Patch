@echo off
setlocal
cd /d "%~dp0"

echo ===== extract w64devkit toolchain =====

if exist "w64devkit\bin\i686-w64-mingw32-gcc.exe" (
  echo Toolchain already extracted. Nothing to do.
  goto :done
)

if not exist "w64devkit-2.10.1-gcc16.2.0.zip" (
  echo [ERROR] zip not found next to this bat.
  pause
  exit /b 1
)

echo Verifying zip md5 ...
certutil -hashfile "w64devkit-2.10.1-gcc16.2.0.zip" MD5 | findstr /v ":"
echo Expect: 781b59607b1969805986de9b29a634f0

echo Extracting (about 160 MB, may take a minute) ...
tar -xf "w64devkit-2.10.1-gcc16.2.0.zip" -C "%~dp0"
if errorlevel 1 (
  echo [ERROR] extract failed. Try right-click - Extract All.
  pause
  exit /b 1
)

if exist "w64devkit\bin\i686-w64-mingw32-gcc.exe" (
  echo OK: toolchain ready.
  echo Next: run  02_build\build_from_package.py
) else (
  echo [ERROR] gcc not found after extract.
)

:done
pause

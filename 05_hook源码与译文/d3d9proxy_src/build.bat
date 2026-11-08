@echo off
chcp 65001 >nul
rem ============================================================
rem  build.bat - d3d9.dll 字体代理构建（x86 32 位，w64devkit gcc 16.2.0）
rem  产出：d3d9_diag.dll（诊断版） / d3d9.dll（生产版）
rem  逐字节复现 V1.03.2 发布版（v69）的三个关键参数（缺一不可）：
rem    参数一：FORCE_POINT_SAMPLER=0（源码默认 1=强制点采样，漏传会字体发糊）
rem    参数二：PRESENT_RESTORE=0（V1.02 起关闭帧末还原）
rem    参数三：image-base 固定为 0x6BE00000（ld 的 auto-image-base 按文件名哈希定基址）
rem ============================================================
setlocal
set PY=C:/Users/fwzang/.workbuddy/binaries/python/envs/default/Scripts/python.exe
set GCC=..\_toolchain\w64devkit\bin\i686-w64-mingw32-gcc.exe
cd /d %~dp0

if not exist "%GCC%" (
  echo [错误] 找不到 %GCC%
  echo        请把 w64devkit 放到交付包根目录 _toolchain\w64devkit  exit /b 1
)

echo [1/4] 生成图集头文件 atlas_png.h ...
"%PY%" gen_atlas_header.py
if errorlevel 1 goto :err

echo [2/4] 编译诊断版 d3d9_diag.dll ...
"%GCC%" -O2 -fno-sanitize=undefined -shared -DFORCE_POINT_SAMPLER=0 -DPRESENT_RESTORE=0 -Wl,--image-base=0x6BE00000 -DG3_DIAG=1 -o d3d9_diag.dll d3d9_proxy.c d3d9.def
if errorlevel 1 goto :err

echo [3/4] 编译生产版 d3d9.dll ...
"%GCC%" -O2 -fno-sanitize=undefined -shared -DFORCE_POINT_SAMPLER=0 -DPRESENT_RESTORE=0 -Wl,--image-base=0x6BE00000 -o d3d9.dll d3d9_proxy.c d3d9.def
if errorlevel 1 goto :err

echo [4/4] 校验导出表 ...
"%PY%" check_exports.py d3d9_diag.dll
if errorlevel 1 goto :err
"%PY%" check_exports.py d3d9.dll
if errorlevel 1 goto :err

echo.
echo ==== BUILD OK ====
for %%f in (d3d9_diag.dll d3d9.dll) do echo   %%f
echo   本脚本用 d3d9_proxy.c 原名编译，产物功能相同但 md5 与发布版不同（差 STT_FILE 一项）
echo   逐字节复现 V1.03.2 发布版(6326d10ca1d7c760becc1c4b6e0442a8) 请用:
echo     00_工具中台\02_构建脚本\build_from_package.py
endlocal
exit /b 0

:err
echo.
echo ==== BUILD FAILED ====
endlocal
exit /b 1


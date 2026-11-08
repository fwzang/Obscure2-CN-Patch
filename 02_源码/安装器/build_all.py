# -*- coding: utf-8 -*-
"""build_all.py — 一键重建安装包（资源 → 编译 → 打包）。

用法（在交付包根目录或本目录执行均可）：
    python 02_源码/安装器/build_all.py

依赖：交付包内 00_工具中台/01_编译链/w64devkit（先运行 解压工具链.bat）

流程：
    1. gen_info.py  info_o2.txt -> info_o2.h
    2. windres      setup.rc    -> setup.res
    3. gcc          setup.c     -> setup.exe
    4. build_installer.py       追加载荷 -> Obscure2_汉化补丁_V1.04.exe
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))          # 02_源码/安装器
PKG = os.path.dirname(os.path.dirname(HERE))                # 交付包根
PY = sys.executable

GCC_CANDIDATES = [
    os.path.join(PKG, r"00_工具中台\01_编译链\w64devkit\bin"),
    os.path.join(PKG, r"_toolchain\w64devkit\bin"),
]
LIBS = ["-lcomctl32", "-lole32", "-lshell32", "-lgdi32", "-luser32", "-ladvapi32"]


def find_tc():
    for d in GCC_CANDIDATES:
        if os.path.exists(os.path.join(d, "gcc.exe")):
            return d
    return None


def run(cmd, **kw):
    print(">", " ".join(os.path.basename(c) if i == 0 else c for i, c in enumerate(cmd)))
    r = subprocess.run(cmd, **kw)
    if r.returncode != 0:
        raise SystemExit("FAILED: %s" % cmd[0])
    return r


def main():
    tc = find_tc()
    if not tc:
        print("[ERROR] 找不到编译器。先运行 00_工具中台/01_编译链/解压工具链.bat")
        return 1
    gcc = os.path.join(tc, "gcc.exe")
    windres = os.path.join(tc, "windres.exe")

    run([PY, "gen_info.py", "info_o2.txt", "info_o2.h"], cwd=HERE)
    run([windres, "--codepage=65001", "-O", "coff", "-i", "setup.rc", "-o", "setup.res"], cwd=HERE)
    run([gcc, "-O2", "-municode", "-mwindows", "-o", "setup.exe", "setup.c", "setup.res"] + LIBS, cwd=HERE)
    run([PY, "build_installer.py"], cwd=HERE)
    print("\n完成：02_源码/安装器/Obscure2_汉化补丁_V1.04.exe")
    print("把它复制到 01_安装包/ 覆盖同名文件，然后重跑 00_工具中台/03_校验脚本/regen_md5_v101.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())

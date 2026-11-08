# -*- coding: utf-8 -*-
"""build_from_package.py — 从交付包直接重建 d3d9.dll（一条命令，无需改路径）。

用法（在交付包根目录执行）：
    python 00_工具中台/02_构建脚本/build_from_package.py

前置：
    00_工具中台/01_编译链/w64devkit/ 存在（运行 解压工具链.bat 生成），
    或把 w64devkit 放到交付包根目录 `_toolchain/w64devkit/`。

产出：
    _build_out/d3d9.dll   （方案 B 图集）
    _build_out/d3d9_A.dll （方案 A 图集，需先替换 atlas_png.h）

自检：
    编译后自动比对发布 md5，不一致会打印警告（通常是源码被改过，属预期）。
"""
import hashlib
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))          # 00_工具中台/02_构建脚本
PKGROOT = os.path.dirname(os.path.dirname(HERE))            # 交付包根

SRCDIR = os.path.join(PKGROOT, '05_hook源码与译文', 'd3d9proxy_src')
OUTDIR = os.path.join(PKGROOT, '_build_out')

GCC_CANDIDATES = [
    os.path.join(PKGROOT, '00_工具中台', '01_编译链', 'w64devkit', 'bin', 'i686-w64-mingw32-gcc.exe'),
    os.path.join(PKGROOT, '_toolchain', 'w64devkit', 'bin', 'i686-w64-mingw32-gcc.exe'),
]

# 发布版指纹（V1.04 / V87_PROD 方案B）
RELEASE_MD5 = 'b42417bd2a51ff5d95d3a84970b8a20f'

FLAGS = [
    '-O2', '-fno-sanitize=undefined', '-shared',
    '-DFORCE_POINT_SAMPLER=0',      # 漏传 → 字体发糊
    '-DPRESENT_RESTORE=0',          # V1.02 起关闭帧末还原
    '-Wl,--image-base=0x6BE00000',  # 锁死基址，否则无法复现
]


def md5(p):
    return hashlib.md5(open(p, 'rb').read()).hexdigest()


def find_gcc():
    for p in GCC_CANDIDATES:
        if os.path.exists(p):
            return p
    return None


def main():
    gcc = find_gcc()
    if not gcc:
        print('[ERROR] 找不到编译器。请先运行 00_工具中台/01_编译链/解压工具链.bat')
        return 1
    if not os.path.exists(os.path.join(SRCDIR, 'd3d9_proxy.c')):
        print('[ERROR] 找不到源码：%s' % SRCDIR)
        return 1

    os.makedirs(OUTDIR, exist_ok=True)
    # 用发布时的源文件名编译，才能逐字节复现（文件名会进 COFF 符号表）
    work = os.path.join(OUTDIR, '_src')
    if os.path.isdir(work):
        shutil.rmtree(work)
    os.makedirs(work)
    shutil.copy2(os.path.join(SRCDIR, 'd3d9_proxy.c'), os.path.join(work, 'd3d9_proxy_v69.c'))
    shutil.copy2(os.path.join(SRCDIR, 'atlas_png.h'), work)
    shutil.copy2(os.path.join(SRCDIR, 'd3d9.def'), work)

    out = os.path.join(OUTDIR, 'd3d9.dll')
    cmd = [gcc] + FLAGS + ['-o', out, 'd3d9_proxy_v69.c', 'd3d9.def']
    print('> %s' % ' '.join(os.path.basename(c) if i == 0 else c for i, c in enumerate(cmd)))
    r = subprocess.run(cmd, cwd=work, capture_output=True, text=True)
    if r.returncode != 0:
        print((r.stdout + r.stderr)[-3000:])
        return 1
    for line in (r.stderr or '').splitlines():
        if 'warning' in line:
            print('  ' + line)

    h = md5(out)
    print()
    print('产出 : %s' % out)
    print('大小 : %d B' % os.path.getsize(out))
    print('md5  : %s' % h)
    if h == RELEASE_MD5:
        print('状态 : 与 V1.04 发布版逐字节一致 ✅')
    else:
        print('状态 : 与发布版不同（源码有改动则属预期）')
        print('       发布版 md5 = %s' % RELEASE_MD5)
    return 0


if __name__ == '__main__':
    sys.exit(main())

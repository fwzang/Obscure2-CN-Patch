# -*- coding: utf-8 -*-
"""build_installer.py — 把载荷追加到 setup.exe 之后，生成单文件安装包。

【包内相对路径版】不依赖任何开发机绝对路径，在交付包里可直接跑。

载荷布局：[setup.exe][6 个载荷][400B Footer]
Footer = magic(8) + ver(4) + n(4) + n*{name[32], off(u64), size(u64)}（固定 8 槽 = 400 字节）

载荷来源（全部取自交付包内）：
    datapack.delta    01_安装包/手动安装版/datapack.delta
    d3d9.dll          01_安装包/手动安装版/d3d9.dll                 （方案B）
    datapack_a.delta  06_独有资产/方案A_字体产物/datapack_a.delta
    d3d9_a.dll        01_安装包/手动安装版/方案A_寒蝉端黑体/d3d9.dll （方案A）
    dinput8.dll       02_源码/安装器/payload/dinput8.dll            （宽屏补丁）
    main.patch        02_源码/安装器/payload/main.patch             （宽屏补丁）
"""
import hashlib
import io
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))                 # 02_源码/安装器
PKG = r"E:\ObsCure2汉化项目_v1.04_完整交付包"        # 交付包根（V1.03.3 构建工作区）

EXE = os.path.join(HERE, "setup.exe")
OUT = os.path.join(HERE, "Obscure2_汉化补丁_V1.04.exe")
MAGIC = b"O2SETUP1"

PAYLOAD = [
    ("datapack.delta",   os.path.join(PKG, r"01_安装包\手动安装版\datapack.delta")),
    ("d3d9.dll",         os.path.join(PKG, r"01_安装包\手动安装版\d3d9.dll")),
    ("datapack_a.delta", os.path.join(PKG, r"06_独有资产\方案A_字体产物\datapack_a.delta")),
    ("d3d9_a.dll",       os.path.join(PKG, r"01_安装包\手动安装版\方案A_寒蝉端黑体\d3d9.dll")),
    ("dinput8.dll",      os.path.join(HERE, r"payload\dinput8.dll")),
    ("main.patch",       os.path.join(HERE, r"payload\main.patch")),
]


def main():
    if not os.path.exists(EXE):
        print("[ERROR] 先编译 setup.exe（运行 build_all.py）")
        return 1
    for name, src in PAYLOAD:
        if not os.path.exists(src):
            print("[MISS] %s -> %s" % (name, src))
            return 1

    base = open(EXE, "rb").read()
    out = io.open(OUT, "wb")
    out.write(base)
    off = len(base)
    ents = []
    for name, src in PAYLOAD:
        data = open(src, "rb").read()
        out.write(data)
        ents.append((name, off, len(data)))
        print("  + %-16s off=0x%08X size=%-8d md5=%s"
              % (name, off, len(data), hashlib.md5(data).hexdigest()))
        off += len(data)

    SLOTS = 8
    footer = MAGIC + struct.pack("<II", 1, len(ents))
    for name, o, sz in ents:
        nm = name.encode("ascii")
        footer += nm + b"\x00" * (32 - len(nm)) + struct.pack("<QQ", o, sz)
    footer += b"\x00" * ((SLOTS - len(ents)) * 48)
    out.write(footer)
    out.close()

    size = os.path.getsize(OUT)
    print()
    print("安装包 : %s" % OUT)
    print("大小   : %.2f MB (%d 字节)" % (size / 1048576.0, size))
    print("footer : %d 字节, %d 条目" % (len(footer), len(ents)))
    with open(OUT, "rb") as f:
        f.seek(size - len(footer))
        assert f.read(len(footer)) == footer, "footer 回读不一致"
    print("回读校验: OK")
    print("md5    :", hashlib.md5(open(OUT, "rb").read()).hexdigest())
    return 0


if __name__ == "__main__":
    sys.exit(main())

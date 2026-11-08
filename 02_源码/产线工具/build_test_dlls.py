# -*- coding: utf-8 -*-
"""build_test_dlls.py — 编译字体对比测试 DLL。

流程：
  1) 对照构建：用基线图集(_work/g4/g3_atlas.png)重新生成 atlas_png.h 并编译，
     与出厂 v49(47060c4b) 比对 md5 —— 一致才证明工具链/flag 与 v49 相同，
     后续测试 DLL 与 v49 的差异被隔离在「图集像素」这一个变量上。
  2) 方案 A：内嵌 _work/g4_A/g3_atlas.png（寒蝉端黑体 Bold）
  3) 方案 B：内嵌 _work/g4_B/g3_atlas.png（活楷 SSAA4 LANCZOS）

编译命令复刻 v49：i686-w64-mingw32-gcc -O2 -fno-sanitize=undefined -shared
                  -DFORCE_POINT_SAMPLER=0 -o out.dll d3d9_proxy.c d3d9.def
"""
import hashlib
import os
import shutil
import subprocess
import sys

ROOT = r"D:\SteamLibrary\steamapps\common\Obscure2\Obscure2_Handover"
SRC = os.path.join(ROOT, "d3d9proxy_src")
WORK = os.path.join(ROOT, "_work", "_fonttest")
GCC = os.path.join(ROOT, "_toolchain", "w64devkit", "bin", "i686-w64-mingw32-gcc.exe")
V49_MD5 = "47060c4b0ef5592e5e7f08ee473446e5"


def md5(p):
    h = hashlib.md5()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def gen_atlas_header(png_path, out_h):
    """复刻 d3d9proxy_src/gen_atlas_header.py 的算法（字节级一致的头文件格式）。"""
    data = open(png_path, "rb").read()
    lines = ["/* atlas_png.h - 自动生成, 勿手改",
             " * 源: %s (%d bytes, md5 %s)" % (png_path, len(data), hashlib.md5(data).hexdigest()),
             " * 生成: build_test_dlls.py (复刻 gen_atlas_header.py)",
             " */",
             "static const unsigned char g_atlasPng[] = {"]
    for i in range(0, len(data), 20):
        lines.append("  " + ",".join("0x%02X" % b for b in data[i:i + 20]) + ",")
    lines.append("};")
    lines.append("static const unsigned int g_atlasPngLen = %d;" % len(data))
    with open(out_h, "w", newline="\n") as f:
        f.write("\n".join(lines) + "\n")
    return len(data)


def build(tag, png, out_dll):
    bdir = os.path.join(WORK, "build_%s" % tag)
    if os.path.isdir(bdir):
        shutil.rmtree(bdir)
    os.makedirs(bdir)
    shutil.copy2(os.path.join(SRC, "d3d9_proxy.c"), bdir)
    shutil.copy2(os.path.join(SRC, "d3d9.def"), bdir)
    n = gen_atlas_header(png, os.path.join(bdir, "atlas_png.h"))
    cmd = [GCC, "-O2", "-fno-sanitize=undefined", "-shared",
           "-DFORCE_POINT_SAMPLER=0",
           "-Wl,--image-base=0x6BE00000",   # v49 实测基址；auto-image-base 会按文件名哈希，必须显式钉住
           "-o", out_dll, "d3d9_proxy.c", "d3d9.def"]
    r = subprocess.run(cmd, cwd=bdir, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stdout); print(r.stderr)
        raise SystemExit("[FAIL] %s 编译失败" % tag)
    # 内嵌 PNG 尺寸核对（verify_pack 同款逻辑）
    d = open(out_dll, "rb").read()
    i = d.find(b"\x89PNG\r\n\x1a\n")
    assert i >= 0, "DLL 内未找到 PNG"
    w = int.from_bytes(d[i + 16:i + 20], "big"); h = int.from_bytes(d[i + 20:i + 24], "big")
    print("[OK] %-14s %s (%d B)  内嵌 PNG %dx%d  png_md5=%s  dll_md5=%s"
          % (tag, os.path.basename(out_dll), os.path.getsize(out_dll), w, h,
             md5(png), md5(out_dll)))
    return md5(out_dll)


def main():
    assert os.path.isfile(GCC), "gcc 不存在: %s" % GCC

    # 1) 对照构建（基线图集 → 应复现 v49）
    # 注意：ld 的 auto-image-base 按输出文件名哈希定 ImageBase，
    # 必须用 v49 的原文件名 d3d9_v49.dll 才能逐字节复现
    ctrl = build("ctrl", os.path.join(ROOT, "_work", "g4", "g3_atlas.png"),
                 os.path.join(WORK, "d3d9_v49.dll"))
    if ctrl == V49_MD5:
        print("\n[PASS] 对照构建与出厂 v49 逐字节一致 —— 工具链与 flag 复刻成功，"
              "测试 DLL 与 v49 的唯一差异就是图集像素\n")
    else:
        print("\n[WARN] 对照构建 md5 %s != v49 %s（未逐字节复现）\n" % (ctrl, V49_MD5))

    # 2) 方案 A / B
    build("A", os.path.join(ROOT, "_work", "g4_A", "g3_atlas.png"),
          os.path.join(WORK, "d3d9_test_A.dll"))
    build("B", os.path.join(ROOT, "_work", "g4_B", "g3_atlas.png"),
          os.path.join(WORK, "d3d9_test_B.dll"))
    return 0


if __name__ == "__main__":
    sys.exit(main())

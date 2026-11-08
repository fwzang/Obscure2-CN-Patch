# -*- coding: utf-8 -*-
"""build_v66_prod.py — v66_PROD = v65 R2 + 字体替换总开关（O2_NO_SWAP）。

为什么需要：
  02:54 的日志显示，这一局有 **17 个不同的 512x256 A8R8G8B8 纹理**被登记成"字体"，
  字体绑定 9742 次、替换 120 次。游戏的 512x256 纹理远不止字体——UI 图、提示图
  都可能是这个规格。一旦被误判成字体，就会被换成中文图集，画面上就"没图了"。

  这可以解释"切屏回来贴图就没了"：切屏后纹理重新绑定，替换再次生效。

本版只加一个运行期开关，不动任何已有逻辑：
  O2_NO_SWAP=1 → Hook_SetTexture 里只登记、不替换（tex 保持游戏原图）
  默认 0 = 维持现有行为
"""
import os
import shutil
import subprocess

import build_v64_prod as b64
import build_v65_prod as b65

ROOT = b64.ROOT
SRC = b64.SRC
GCC = b64.GCC
OUTDIR = b64.OUTDIR
PKG = b64.PKG
WORK = os.path.join(ROOT, r"_verify\_v66_prod")

TARGETS = [
    ("A", os.path.join(PKG, r"06_独有资产\方案A_字体产物\g3_atlas.png"),
     "22ffed606c669be5043668d8b29ae2ef", "v66_PROD_A.dll"),
    ("B", os.path.join(PKG, r"04_基线与回滚\g3_atlas.png"),
     "e172a188651c68464ff3946683c3f5c9", "v66_PROD.dll"),
]


def patch_swap(s):
    # 1) 开关变量
    a = "static int   g_uiOn = 1, g_uiInited = 0, g_uiLogN = 0;"
    assert a in s, "ui 全局锚点丢失"
    s = s.replace(a, a + "\nstatic int   g_noSwap = 0;   /* O2_NO_SWAP=1: 只登记不替换 */", 1)

    # 2) 读环境变量
    a = '    if (GetEnvironmentVariableA("O2_FIX_LOCKMAX", b, sizeof(b)) > 0) {'
    assert a in s, "lockmax 锚点丢失"
    s = s.replace(a,
                  '    if (GetEnvironmentVariableA("O2_NO_SWAP", b, sizeof(b)) > 0)\n'
                  '        g_noSwap = (b[0] != \'0\');\n' + a, 1)

    # 3) 替换处加门（只登记、不换图）
    a = """            if (g_bigTex) {
                g_swapN++;"""
    assert a in s, "g_bigTex 替换块锚点丢失"
    s = s.replace(a, """            if (g_bigTex && !g_noSwap) {
                g_swapN++;""", 1)

    # 4) 版本标记
    a = '    LOGB("[INIT] ===== V65_PROD R2 1080p安全区+2K拉回 =====");'
    assert a in s, "V65 标记锚点丢失"
    s = s.replace(a, '    LOGB("[INIT] ===== V66_PROD 字体替换开关版 =====");', 1)

    # 5) 启动日志补一行
    a = '    LOGB("[FIX] v65 R2 %s 安全区<=%d refH=%d scale=%d/1000 lockmax=%d",'
    assert a in s, "FIX 启动日志锚点丢失"
    s = s.replace(a, '    LOGB("[FIX] noSwap=%d (O2_NO_SWAP=1 只登记不替换)", g_noSwap);\n' + a, 1)
    return s


def main():
    src = open(os.path.join(SRC, "d3d9_proxy.c"), "rb").read().decode("utf-8")
    s = b64.patch(src)          # v64 全部补丁
    s = b65.patch_ui(s)         # v65 R2 的 UI 逻辑
    s = patch_swap(s)           # v66 的替换开关
    os.makedirs(OUTDIR, exist_ok=True)
    for tag, png, want, name in TARGETS:
        assert b64.md5(png) == want, "图集 md5 不符: %s" % png
        d = os.path.join(WORK, tag)
        if os.path.isdir(d):
            shutil.rmtree(d)
        os.makedirs(d)
        open(os.path.join(d, "d3d9_proxy_v66.c"), "wb").write(s.encode("utf-8"))
        shutil.copy2(os.path.join(SRC, "d3d9.def"), d)
        b64.gen_header(png, os.path.join(d, "atlas_png.h"))
        out = os.path.join(OUTDIR, name)
        r = subprocess.run([GCC, "-O2", "-fno-sanitize=undefined", "-shared",
                            "-DFORCE_POINT_SAMPLER=0", "-DPRESENT_RESTORE=0",
                            "-Wl,--image-base=0x6BE00000",
                            "-o", out, "d3d9_proxy_v66.c", "d3d9.def"],
                           cwd=d, capture_output=True, text=True)
        if r.returncode != 0:
            print((r.stdout + r.stderr)[-3000:])
            raise SystemExit("[FAIL] %s" % tag)
        warn = [l for l in (r.stderr or "").splitlines() if "warning" in l]
        print("[%s] %s  %d B  md5 %s  warn=%d" % (tag, name, os.path.getsize(out), b64.md5(out), len(warn)))
        for l in warn[:10]:
            print("    " + l)


if __name__ == "__main__":
    main()

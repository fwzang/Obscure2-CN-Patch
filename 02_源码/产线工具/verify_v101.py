# -*- coding: utf-8 -*-
"""verify_v101.py — V1.01 双方案安装包交付前验证。

1) 载荷核对：footer 6 条目 md5 与源一致
2) 版本串核对：1.0.1.0 / V1.01 / V101 / 字体方案文案
3) 沙箱静默安装：/test（方案B）与 /testA（方案A）各一次，核对落盘 md5 与无杂散文件
"""
import hashlib
import os
import shutil
import struct
import subprocess
import sys

ROOT = r"D:\SteamLibrary\steamapps\common\Obscure2\Obscure2_Handover"
EXE = os.path.join(ROOT, r"installer\Obscure2_汉化补丁_V1.01.exe")
SB = r"D:\_o2test_v101"
VANILLA = os.path.join(ROOT, r"基线_原版\datapack.hvp.gate3_orig")

WANT = {
    "datapack.delta":   "ce74adb362a7593385713cb5f9e1c23e",
    "d3d9.dll":         "47060c4b0ef5592e5e7f08ee473446e5",
    "datapack_a.delta": "?",   # 运行时打印
    "d3d9_a.dll":       "0e504ff0fa4d44cd291e2cbed19d52aa",
    "dinput8.dll":      "4d25503a50bbf5345a7a86e19c373e1a",
    "main.patch":       "a7838aa538e75b28cf0e4500c755a7a4",
}


def md5(p):
    h = hashlib.md5()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def main():
    d = open(EXE, "rb").read()
    foot = d[-400:]
    assert foot[:8] == b"O2SETUP1"
    ver, n = struct.unpack_from("<II", foot, 8)
    print("exe = %d B, md5 %s, footer ver=%d n=%d" % (len(d), md5(EXE), ver, n))
    ok = True
    for i in range(n):
        base = 16 + 48 * i
        nm = foot[base:base + 32].split(b"\x00")[0].decode()
        off, sz = struct.unpack_from("<QQ", foot, base + 32)
        got = hashlib.md5(d[off:off + sz]).hexdigest()
        want = WANT.get(nm, "?")
        flag = "OK" if want in ("?", got) else "!!"
        if flag == "!!":
            ok = False
        print("  %s %-16s off=0x%08X size=%-9d %s" % (flag, nm, off, sz, got))

    # 版本串
    for s in ("1.0.1.0", "V1.01", "Obscure2_HanHua_V101.exe", "方案 A", "方案 B"):
        found = s.encode("utf-16le") in d or s.encode("utf-8") in d or s.encode("ascii", "ignore") in d
        print("  串 %-28s %s" % (s, "OK" if found else "!! 缺失"))
        ok &= found

    # ---- 沙箱：方案 B ----
    def fresh():
        if os.path.isdir(SB):
            shutil.rmtree(SB)
        os.makedirs(SB)
        open(os.path.join(SB, "Obscure2.exe"), "wb").close()
        shutil.copy2(VANILLA, os.path.join(SB, "datapack.hvp"))

    fresh()
    r = subprocess.run([EXE, "/test:" + SB], capture_output=True, timeout=300)
    print("\n[/test 方案B] rc=%d" % r.returncode)
    b_pack = md5(os.path.join(SB, "datapack.hvp"))
    b_dll = md5(os.path.join(SB, "d3d9.dll"))
    b_ws = os.path.exists(os.path.join(SB, "dinput8.dll")) and os.path.exists(os.path.join(SB, "patches", "main.patch"))
    stray = [f for f in os.listdir(SB) if f.startswith("d3d9_a") or f.startswith("datapack_a")]
    print("   datapack=%s(应 d25123d2) d3d9=%s(应 47060c4b) 宽屏=%s 杂散=%s"
          % (b_pack[:8], b_dll[:8], b_ws, stray))
    ok &= (r.returncode == 0 and b_pack == "d25123d226ebd1dfae39c053717db808"
           and b_dll == "47060c4b0ef5592e5e7f08ee473446e5" and b_ws and not stray)

    # ---- 沙箱：方案 A ----
    fresh()
    r = subprocess.run([EXE, "/testA:" + SB], capture_output=True, timeout=300)
    print("[/testA 方案A] rc=%d" % r.returncode)
    a_pack = md5(os.path.join(SB, "datapack.hvp"))
    a_dll = md5(os.path.join(SB, "d3d9.dll"))
    stray = [f for f in os.listdir(SB) if f.startswith("d3d9_a") or f.startswith("datapack_a")]
    print("   datapack=%s(应 e657e90d) d3d9=%s(应 0e504ff0) 杂散=%s"
          % (a_pack[:8], a_dll[:8], stray))
    ok &= (r.returncode == 0 and a_pack == "e657e90dcfe225da3af5b19e394f5622"
           and a_dll == "0e504ff0fa4d44cd291e2cbed19d52aa" and not stray)

    shutil.rmtree(SB, ignore_errors=True)
    print("\n[%s] V1.01 双方案安装包验证" % ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

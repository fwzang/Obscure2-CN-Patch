# -*- coding: utf-8 -*-
"""沙箱实跑 release_v49_full18 的 apply.bat / 还原原版.bat（V1.00 交付前复检）"""
import hashlib, os, shutil, subprocess, sys

PACK = r"D:\SteamLibrary\steamapps\common\Obscure2\Obscure2_Handover\release_v49_full18"
VANILLA = r"D:\SteamLibrary\steamapps\common\Obscure2\Obscure2_Handover\基线_原版\datapack.hvp.gate3_orig"
SB = r"D:\_o2test_v100"

def md5(p):
    h = hashlib.md5()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()

def run(bat, gamedir):
    r = subprocess.run([os.path.join(PACK, bat)], input=(gamedir + "\r\n").encode("utf-8"),
                       capture_output=True, cwd=PACK, timeout=300)
    out = (r.stdout + r.stderr).decode("utf-8", "replace")
    tail = [l for l in out.splitlines() if l.strip()][-8:]
    print("--- %s rc=%d ---" % (bat, r.returncode))
    for l in tail:
        print("   " + l)
    return r.returncode

if os.path.isdir(SB):
    shutil.rmtree(SB)
os.makedirs(SB)
open(os.path.join(SB, "Obscure2.exe"), "wb").close()
shutil.copy2(VANILLA, os.path.join(SB, "datapack.hvp"))
vanilla_md5 = md5(os.path.join(SB, "datapack.hvp"))
print("沙箱就绪，原版 datapack.hvp md5=%s" % vanilla_md5)

rc1 = run("apply.bat", SB)
installed_pack = md5(os.path.join(SB, "datapack.hvp"))
installed_dll = md5(os.path.join(SB, "d3d9.dll"))
print("安装后: datapack.hvp=%s  d3d9.dll=%s  备份存在=%s" % (
    installed_pack, installed_dll, os.path.exists(os.path.join(SB, "datapack.hvp.gate3_orig"))))

rc2 = run("还原原版.bat", SB)
restored = md5(os.path.join(SB, "datapack.hvp"))
dll_gone = not os.path.exists(os.path.join(SB, "d3d9.dll"))
print("还原后: datapack.hvp=%s (vanilla=%s) d3d9.dll 已删=%s" % (restored, vanilla_md5, dll_gone))

ok = (rc1 == 0 and rc2 == 0
      and installed_pack == "d25123d226ebd1dfae39c053717db808"
      and installed_dll == "47060c4b0ef5592e5e7f08ee473446e5"
      and restored == vanilla_md5 and dll_gone)
print("\n[%s] V1.00 手动三件套沙箱复检" % ("PASS" if ok else "FAIL"))
shutil.rmtree(SB, ignore_errors=True)
sys.exit(0 if ok else 1)

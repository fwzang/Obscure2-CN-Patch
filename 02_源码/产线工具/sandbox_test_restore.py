# -*- coding: utf-8 -*-
"""sandbox_test_restore.py — 沙箱验证「原版还原包」的两个 bat（不碰真实游戏目录）。"""
import os
import shutil
import subprocess
import sys

SB = r"D:\_o2test_restore"
PKG_SRC = r"D:\Obscure2_原版还原_2026-10-22"
GAME = os.path.join(SB, "game")
PKG = os.path.join(SB, "pkg")

VANILLA_SZ = 885836666
FULL18_SZ = 885935908
V49_SZ = 890298


def sparse(path, size):
    with open(path, "wb") as f:
        if size > 0:
            f.truncate(size)


def run(bat, gamedir):
    r = subprocess.run([os.path.join(PKG, bat)], input=b"", capture_output=True,
                       cwd=PKG, timeout=120)
    out = (r.stdout + r.stderr).decode("utf-8", "replace")
    tail = [l for l in out.splitlines() if l.strip()][-6:]
    print("--- %s rc=%d ---" % (bat, r.returncode))
    for l in tail:
        print("   " + l)
    return r.returncode


def main():
    if os.path.isdir(SB):
        shutil.rmtree(SB)
    os.makedirs(GAME)
    os.makedirs(PKG)
    # 沙箱游戏目录：模拟 full18+v49 在装
    open(os.path.join(GAME, "Obscure2.exe"), "wb").close()
    sparse(os.path.join(GAME, "datapack.hvp"), FULL18_SZ)
    sparse(os.path.join(GAME, "d3d9.dll"), V49_SZ)
    # 沙箱包：假原版 + 假备份 + 改写 GD 路径的两个 bat
    sparse(os.path.join(PKG, "datapack.hvp.vanilla"), VANILLA_SZ)
    bak = os.path.join(PKG, "_汉化态备份_V100")
    os.makedirs(bak)
    sparse(os.path.join(bak, "datapack.hvp"), FULL18_SZ)
    sparse(os.path.join(bak, "d3d9.dll"), V49_SZ)
    for name in ("还原为原版.bat", "恢复汉化V1.00.bat"):
        data = open(os.path.join(PKG_SRC, name), "rb").read()
        data = data.replace(
            "D:\\SteamLibrary\\steamapps\\common\\Obscure2".encode("ascii"),
            GAME.encode("ascii"))
        open(os.path.join(PKG, name), "wb").write(data)
    print("沙箱就绪（game=%s）\n" % GAME)

    rc1 = run("还原为原版.bat", GAME)
    s1 = os.path.getsize(os.path.join(GAME, "datapack.hvp"))
    dll_gone = not os.path.exists(os.path.join(GAME, "d3d9.dll"))
    bak_exist = os.path.exists(os.path.join(PKG, "_测后态备份", "datapack.hvp"))
    print("还原后: datapack.hvp=%d B(应%d) d3d9.dll 已删=%s 测后备份存在=%s\n"
          % (s1, VANILLA_SZ, dll_gone, bak_exist))

    rc2 = run("恢复汉化V1.00.bat", GAME)
    s2 = os.path.getsize(os.path.join(GAME, "datapack.hvp"))
    s3 = os.path.getsize(os.path.join(GAME, "d3d9.dll"))
    print("恢复后: datapack.hvp=%d B(应%d) d3d9.dll=%d B(应%d)\n"
          % (s2, FULL18_SZ, s3, V49_SZ))

    ok = (rc1 == 0 and rc2 == 0 and s1 == VANILLA_SZ and dll_gone and bak_exist
          and s2 == FULL18_SZ and s3 == V49_SZ)
    print("[%s] 原版还原包沙箱验证" % ("PASS" if ok else "FAIL"))
    shutil.rmtree(SB, ignore_errors=True)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    sys.exit(main())

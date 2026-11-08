# -*- coding: utf-8 -*-
"""build_restore_pkg.py — 组装「原版还原包」。

内容：
  datapack.hvp.vanilla   原版数据包（04a96eff，取自基线_原版）
  还原为原版.bat         一键：备份当前态 → 装原版 → 删 d3d9.dll
  恢复汉化V1.00.bat      一键：从预置备份恢复 full18+v49
  _汉化态备份_V100/      当前游戏目录的 V1.00 态（full18+v49，复制时校验 md5）
  README.md

bat 一律用 Python 字节级写 CRLF+UTF-8（sed 剥行尾事故的教训）。
"""
import hashlib
import os
import shutil

ROOT = r"D:\SteamLibrary\steamapps\common\Obscure2\Obscure2_Handover"
GAME = r"D:\SteamLibrary\steamapps\common\Obscure2"
PKG = r"D:\Obscure2_原版还原_2026-10-22"
VANILLA_SRC = os.path.join(ROOT, "基线_原版", "datapack.hvp.gate3_orig")

VANILLA_MD5 = "04a96eff7978cf31e66e9354421f1516"
FULL18_MD5 = "d25123d226ebd1dfae39c053717db808"
V49_MD5 = "47060c4b0ef5592e5e7f08ee473446e5"


def md5(p):
    h = hashlib.md5()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def write_bat(path, lines):
    data = b"\r\n".join(l.encode("utf-8") for l in lines) + b"\r\n"
    with open(path, "wb") as f:
        f.write(data)
    print("[OK] %s (%d B, CRLF %d/%d)" % (
        os.path.basename(path), len(data),
        data.count(b"\r\n"), data.count(b"\n")))


def main():
    if os.path.isdir(PKG):
        shutil.rmtree(PKG)
    os.makedirs(PKG)

    # ---- 1. 原版数据包 ----
    dst = os.path.join(PKG, "datapack.hvp.vanilla")
    shutil.copy2(VANILLA_SRC, dst)
    got = md5(dst)
    assert got == VANILLA_MD5, "原版包 md5 不符: %s" % got
    print("[OK] datapack.hvp.vanilla %d B md5 %s" % (os.path.getsize(dst), got))

    # ---- 2. 预置 V1.00 汉化态备份（从当前游戏目录，V1.00 已验证在装） ----
    bak = os.path.join(PKG, "_汉化态备份_V100")
    os.makedirs(bak)
    shutil.copy2(os.path.join(GAME, "datapack.hvp"), os.path.join(bak, "datapack.hvp"))
    shutil.copy2(os.path.join(GAME, "d3d9.dll"), os.path.join(bak, "d3d9.dll"))
    assert md5(os.path.join(bak, "datapack.hvp")) == FULL18_MD5, "full18 不符"
    assert md5(os.path.join(bak, "d3d9.dll")) == V49_MD5, "v49 不符"
    print("[OK] _汉化态备份_V100: full18 %s + v49 %s（已校验）" % (FULL18_MD5, V49_MD5))

    # ---- 3. 还原为原版.bat ----
    write_bat(os.path.join(PKG, "还原为原版.bat"), [
        "@echo off",
        "chcp 65001 >nul",
        "setlocal enabledelayedexpansion",
        "rem ============================================================",
        "rem  一键还原为英文原版",
        "rem  1) 先把当前汉化态备份到本目录 _测后态备份\\",
        "rem  2) 用原版数据包覆盖游戏目录 datapack.hvp",
        "rem  3) 删除字体代理 d3d9.dll（游戏回到原版英文）",
        "rem ============================================================",
        'set "PKG=%~dp0"',
        'set "GD=D:\\SteamLibrary\\steamapps\\common\\Obscure2"',
        'if not exist "%GD%\\Obscure2.exe" (',
        '  set /p "GD=请输入游戏根目录（含有 Obscure2.exe 的文件夹）: "',
        ")",
        'if not exist "%GD%\\Obscure2.exe" (',
        "  echo [错误] 未找到游戏目录，已取消。",
        "  exit /b 1",
        ")",
        "rem ---------- 游戏必须已退出 ----------",
        'tasklist /fi "imagename eq Obscure2.exe" 2>nul | findstr /i "Obscure2.exe" >nul',
        "if not errorlevel 1 (",
        "  echo [错误] 游戏正在运行，请先完全退出游戏，再运行本脚本。",
        "  exit /b 1",
        ")",
        "rem ---------- 1. 备份当前汉化态 ----------",
        'if exist "%GD%\\datapack.hvp" (',
        '  if not exist "%PKG%_测后态备份" md "%PKG%_测后态备份"',
        '  copy /v /y "%GD%\\datapack.hvp" "%PKG%_测后态备份\\datapack.hvp" >nul',
        '  if exist "%GD%\\d3d9.dll" copy /v /y "%GD%\\d3d9.dll" "%PKG%_测后态备份\\d3d9.dll" >nul',
        "  echo [1/3] 当前汉化态已备份到 _测后态备份\\",
        ") else (",
        "  echo [1/3] 游戏目录没有 datapack.hvp，跳过备份",
        ")",
        "rem ---------- 2. 覆盖原版数据包 ----------",
        'copy /v /y "%PKG%datapack.hvp.vanilla" "%GD%\\datapack.hvp" >nul',
        "if errorlevel 1 (",
        "  echo [错误] 原版数据包复制失败。",
        "  exit /b 1",
        ")",
        'for %%I in ("%GD%\\datapack.hvp") do set SZ=%%~zI',
        'if not "%SZ%"=="885836666" (',
        "  echo [错误] 数据包尺寸校验失败（%SZ%，应为 885836666），已中止。",
        "  exit /b 1",
        ")",
        "echo [2/3] 原版数据包已就位（885836666 B 校验通过）",
        "rem ---------- 3. 删除字体代理 ----------",
        'if exist "%GD%\\d3d9.dll" del "%GD%\\d3d9.dll"',
        "echo [3/3] 字体代理 d3d9.dll 已移除",
        "echo.",
        "echo [OK] 已还原为英文原版。想恢复汉化：运行本目录的 恢复汉化V1.00.bat",
        "exit /b 0",
    ])

    # ---- 4. 恢复汉化V1.00.bat ----
    write_bat(os.path.join(PKG, "恢复汉化V1.00.bat"), [
        "@echo off",
        "chcp 65001 >nul",
        "setlocal enabledelayedexpansion",
        "rem ============================================================",
        "rem  一键恢复汉化 V1.00（full18 + v49，从预置备份）",
        "rem ============================================================",
        'set "PKG=%~dp0"',
        'set "GD=D:\\SteamLibrary\\steamapps\\common\\Obscure2"',
        'if not exist "%GD%\\Obscure2.exe" (',
        '  set /p "GD=请输入游戏根目录（含有 Obscure2.exe 的文件夹）: "',
        ")",
        'if not exist "%GD%\\Obscure2.exe" (',
        "  echo [错误] 未找到游戏目录，已取消。",
        "  exit /b 1",
        ")",
        'tasklist /fi "imagename eq Obscure2.exe" 2>nul | findstr /i "Obscure2.exe" >nul',
        "if not errorlevel 1 (",
        "  echo [错误] 游戏正在运行，请先完全退出游戏，再运行本脚本。",
        "  exit /b 1",
        ")",
        'if not exist "%PKG%_汉化态备份_V100\\datapack.hvp" (',
        "  echo [错误] 找不到预置备份 _汉化态备份_V100\\datapack.hvp",
        "  exit /b 1",
        ")",
        'copy /v /y "%PKG%_汉化态备份_V100\\datapack.hvp" "%GD%\\datapack.hvp" >nul',
        'copy /v /y "%PKG%_汉化态备份_V100\\d3d9.dll" "%GD%\\d3d9.dll" >nul',
        'for %%I in ("%GD%\\datapack.hvp") do set SZ1=%%~zI',
        'for %%I in ("%GD%\\d3d9.dll") do set SZ2=%%~zI',
        'if not "%SZ1%"=="885935908" (',
        "  echo [错误] 汉化数据包尺寸校验失败（%SZ1%）。",
        "  exit /b 1",
        ")",
        'if not "%SZ2%"=="890298" (',
        "  echo [错误] 字体代理尺寸校验失败（%SZ2%）。",
        "  exit /b 1",
        ")",
        "echo [OK] 已恢复汉化 V1.00（full18 885935908 B + v49 890298 B 校验通过）",
        "exit /b 0",
    ])
    print("\n原版还原包已生成：%s" % PKG)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

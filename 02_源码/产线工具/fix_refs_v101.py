# -*- coding: utf-8 -*-
"""fix_refs_v101.py — 修复 D 盘配套包的 V1.01 引用（脚本文件执行，避免 bash 反引号问题）。"""
import io
import os

RESTORE = r"D:\Obscure2_原版还原_2026-10-22"
CMP = r"D:\Obscure2_字体对比测试_2026-10-22"

# ---------- 1. 还原包：改 bat 文件名 ----------
old_bat = os.path.join(RESTORE, "恢复汉化V1.00.bat")
new_bat = os.path.join(RESTORE, "恢复汉化V1.01.bat")
if os.path.exists(old_bat):
    os.replace(old_bat, new_bat)
    print("[OK] 重命名为 恢复汉化V1.01.bat")

# ---------- 2. 两个 bat 内的文字（字节级，保留 CRLF） ----------
for name in ("还原为原版.bat", "恢复汉化V1.01.bat"):
    p = os.path.join(RESTORE, name)
    b = open(p, "rb").read()
    n0 = len(b)
    b = b.replace("恢复汉化V1.00.bat".encode("utf-8"), "恢复汉化V1.01.bat".encode("utf-8"))
    b = b.replace("一键恢复汉化 V1.00".encode("utf-8"), "一键恢复汉化 V1.01".encode("utf-8"))
    b = b.replace("已恢复汉化 V1.00".encode("utf-8"), "已恢复汉化 V1.01".encode("utf-8"))
    open(p, "wb").write(b)
    print("[OK] %s (%d -> %d B)" % (name, n0, len(b)))

# ---------- 3. 还原包 README ----------
p = os.path.join(RESTORE, "README.md")
s = io.open(p, encoding="utf-8").read()
s = s.replace(
    "| `Obscure2_汉化补丁_V1.00.exe` | 2,062,839 | `8391340e7e9e5e62b13b24deed0cbab5` | **汉化补丁安装包**（图形化，可装可还原） |",
    "| `Obscure2_汉化补丁_V1.01.exe` | 3,603,537 | `8b6abd18dfb7b2bd9c9ce5564066ca36` | **汉化补丁安装包 V1.01**（图形化，双字体方案，可装可还原） |")
s = s.replace("恢复汉化V1.00.bat", "恢复汉化V1.01.bat")
s = s.replace("运行 `Obscure2_汉化补丁_V1.00.exe`。", "运行 `Obscure2_汉化补丁_V1.01.exe`（可选字体方案）。")
s = s.replace("现在是 V1.00 完整态", "现在是 V1.01 完整态")
s = s.replace("想回 V1.00", "想回 V1.01")
io.open(p, "w", encoding="utf-8", newline="").write(s)
print("[OK] 还原包 README 已更新")

# ---------- 4. 对比说明 ----------
p2 = os.path.join(CMP, "对比说明.md")
t = io.open(p2, encoding="utf-8").read()
t = t.replace("运行 V1.00 安装器装到", "运行 V1.01 安装器装到")
t = t.replace("顺便拿到 V1.00 基线截图", "顺便拿到 V1.01 基线截图")
t = t.replace("任何时候想回到封盘状态：重装 `Obscure2_汉化补丁_V1.00.exe` 即可。",
              "任何时候想回到发布状态：重装 `Obscure2_汉化补丁_V1.01.exe`（在交付包 01_安装包 内）即可。")
io.open(p2, "w", encoding="utf-8", newline="").write(t)
print("[OK] 对比说明 已更新")

# ---------- 5. 复核 ----------
print("\n--- 复核 ---")
for path in (os.path.join(RESTORE, "README.md"), p2):
    txt = io.open(path, encoding="utf-8").read()
    bad = [l.strip() for l in txt.splitlines() if "V1.00.exe" in l]
    print(os.path.basename(path), "残留 V1.00.exe 引用:", bad if bad else "无")
print(os.listdir(RESTORE))

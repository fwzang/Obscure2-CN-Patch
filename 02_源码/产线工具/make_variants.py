# -*- coding: utf-8 -*-
"""make_variants.py — 生成方案 A / 方案 B 的 gate3 变体脚本（字节级改写，不用 sed）。

方案 A: 寒蝉端黑体 Bold 替代活楷体（其余参数与基线一致：SSAA=3 / BOX / 盒19x25）
方案 B: 活楷体 + SSAA=4 + LANCZOS 降采样（几何不变，只改像素）
"""
import os

ROOT = r"D:\SteamLibrary\steamapps\common\Obscure2\Obscure2_Handover"
SG = os.path.join(ROOT, "scripts_gate3")
WORK = os.path.join(ROOT, "_work", "_fonttest")

os.makedirs(WORK, exist_ok=True)
os.makedirs(os.path.join(ROOT, "_work", "g4_A"), exist_ok=True)
os.makedirs(os.path.join(ROOT, "_work", "g4_B"), exist_ok=True)


def patch(src, dst, subs):
    data = open(src, "rb").read()
    # 变体脚本不在 scripts_gate3/ 下，先把 RECON 钉成绝对项目根
    data = data.replace(
        b"RECON = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))",
        b"RECON = r'D:\\SteamLibrary\\steamapps\\common\\Obscure2\\Obscure2_Handover'")
    # FONT_PATH 也按 __file__ 推断，一并钉到 RECON
    data = data.replace(
        b"FONT_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),",
        b"FONT_PATH = os.path.join(RECON,")
    # RECON 原定义在 CONFIG 之后，提前插一份（后面原位置仍是同一绝对值，无害）
    marker = "# ==================== CONFIG（改字号只动这里）====================".encode("utf-8")
    if marker in data:
        data = data.replace(
            marker,
            b"RECON = r'D:\\SteamLibrary\\steamapps\\common\\Obscure2\\Obscure2_Handover'\n\n" + marker)
    for old, new in subs:
        ob, nb = old.encode("utf-8"), new.encode("utf-8")
        if ob not in data:
            raise SystemExit("[FAIL] 未找到待替换串: %r" % old[:60])
        n = data.count(ob)
        data = data.replace(ob, nb)
        print("  x%d  %s" % (n, old[:40].replace("\n", " ")))
    open(dst, "wb").write(data)
    print("[OK] %s (%d B)\n" % (os.path.basename(dst), len(data)))


# ---------- 方案 A：换字体（寒蝉端黑体 Bold） ----------
patch(os.path.join(SG, "gate3_atlas.py"), os.path.join(WORK, "gate3_atlas_A.py"), [
    ("'_work', 'fonts', 'ChillHuoKai_Regular.otf'",
     "'_work', 'fonts', 'ChillDuanSans_Bold.otf'"),
    ("OUT = os.path.join(RECON, '_work', 'g4')",
     "OUT = os.path.join(RECON, '_work', 'g4_A')"),
    ("字体为寒蝉活楷体 ChillHuoKai_Regular.otf",
     "字体为寒蝉端黑体 Bold ChillDuanSans_Bold.otf"),
    ("T3: 全量图集生成（CONFIG:", "T3: 全量图集生成【方案A 寒蝉端黑体 Bold】（CONFIG:"),
])

# ---------- 方案 B：SSAA=4 + LANCZOS ----------
patch(os.path.join(SG, "gate3_atlas.py"), os.path.join(WORK, "gate3_atlas_B.py"), [
    ("SSAA = 3               #", "SSAA = 4               #"),
    ("# 3 => 20px 字形按 60px 渲染后 BOX(面积平均) 缩到 19x25",
     "# 4 => 20px 字形按 80px 渲染后 LANCZOS 缩到 19x25"),
    ("# 实测 BOX 墨量与 1x 基准一致(-0.0%); LANCZOS 会 +5.6% 墨像素、显胖",
     "# 方案B实验: LANCZOS 缩回（用户要求对比清晰度）"),
    ("tile = big.resize((bw, BOX_H), Image.BOX)   # BOX=面积平均, 墨量与1x基准一致(实测-0.0%); LANCZOS会向外晕(+5.6%墨像素)",
     "tile = big.resize((bw, BOX_H), Image.LANCZOS)   # 方案B实验: LANCZOS 缩回"),
    ("OUT = os.path.join(RECON, '_work', 'g4')",
     "OUT = os.path.join(RECON, '_work', 'g4_B')"),
    ("Gate 3 T3 全量图集构建报告（20px @ 盒 19x25, SSAA=3）",
     "Gate 3 T3 全量图集构建报告（20px @ 盒 19x25, SSAA=4/LANCZOS 方案B）"),
    ("T3: 全量图集生成（CONFIG:", "T3: 全量图集生成【方案B SSAA=4 LANCZOS】（CONFIG:"),
])

# ---------- T4 def 变体 ----------
for tag in ("A", "B"):
    patch(os.path.join(SG, "gate3_def.py"), os.path.join(WORK, "gate3_def_%s.py" % tag), [
        ("LAYOUT = os.path.join(RECON, '_work', 'g4', 'g3_layout.tsv')",
         "LAYOUT = os.path.join(RECON, '_work', 'g4_%s', 'g3_layout.tsv')" % tag),
        ("ATLAS_PNG = os.path.join(RECON, '_work', 'g4', 'g3_atlas.png')",
         "ATLAS_PNG = os.path.join(RECON, '_work', 'g4_%s', 'g3_atlas.png')" % tag),
        ("OUT = os.path.join(RECON, '_work', 'g4')",
         "OUT = os.path.join(RECON, '_work', 'g4_%s')" % tag),
        ("T4: 全量字体 def 生成", "T4: 全量字体 def 生成【方案%s】" % tag),
    ])
print("全部变体脚本已生成于", WORK)

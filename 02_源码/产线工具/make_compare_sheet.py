# -*- coding: utf-8 -*-
"""make_compare_sheet.py — 基线 / 方案A / 方案B 三版图集静态对比图。

从三张图集里抠同一批代表性字形，6 倍放大并排，供不进游戏快速预览。
"""
import csv
import os

from PIL import Image

ROOT = r"D:\SteamLibrary\steamapps\common\Obscure2\Obscure2_Handover"
ZOOM = 6
PICKS = [
    (0x56FD, "国"), (0x4E16, "世"), (0x754C, "界"), (0x4F60, "你"),
    (0x597D, "好"), (0x6E38, "戏"), (0x5F00, "开"), (0x59CB, "始"),
    (0x83B7, "获"), (0x5F97, "得"), (0x6B66, "武"), (0x5668, "器"),
    (0x4EA7, "产"), (0x54C1, "品"), (0x8BF4, "说"), (0x660E, "明"),
    (0x3002, "。"), (0xFF0C, "，"), (0xFF1A, "："), (0x0025, "%"),
]

SRC = [
    ("基线 V1.00（活楷 SSAA3 BOX）", os.path.join(ROOT, "_work", "g4", "g3_layout.tsv"),
     os.path.join(ROOT, "_work", "g4", "g3_atlas.png")),
    ("方案A 寒蝉端黑体 Bold", os.path.join(ROOT, "_work", "g4_A", "g3_layout.tsv"),
     os.path.join(ROOT, "_work", "g4_A", "g3_atlas.png")),
    ("方案B 活楷 SSAA4 LANCZOS", os.path.join(ROOT, "_work", "g4_B", "g3_layout.tsv"),
     os.path.join(ROOT, "_work", "g4_B", "g3_atlas.png")),
]


def load(layout_path):
    box = {}
    with open(layout_path, encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f, delimiter="\t"):
            box[int(row["cp"])] = (int(row["x"]), int(row["y"]),
                                   int(row["w"]), int(row["h"]))
    return box


def main():
    from PIL import ImageDraw
    cols = len(PICKS)
    cell_w, cell_h = 19 * ZOOM + 16, 25 * ZOOM + 34
    rows = len(SRC)
    LBL = 260
    W = LBL + cols * cell_w + 8
    H = rows * cell_h + 8
    sheet = Image.new("RGBA", (W, H), (24, 24, 28, 255))
    gd = ImageDraw.Draw(sheet)
    for r, (title, lay, png) in enumerate(SRC):
        box = load(lay)
        img = Image.open(png).convert("RGBA")
        y0 = 8 + r * cell_h
        gd.text((10, y0 + 30), title, fill=(255, 214, 120, 255))
        for c, (cp, ch) in enumerate(PICKS):
            x, y, w, h = box[cp]
            tile = img.crop((x - 1, y - 1, x + w + 1, y + h + 1))
            tile = tile.resize((tile.width * ZOOM, tile.height * ZOOM), Image.NEAREST)
            px, py = LBL + c * cell_w, y0
            sheet.alpha_composite(tile, (px, py + 24))
    out = os.path.join(ROOT, "_work", "_fonttest", "字体三版对比.png")
    sheet.save(out)
    print("[OK] %s (%dx%d)" % (out, sheet.width, sheet.height))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

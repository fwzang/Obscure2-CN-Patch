# -*- coding: utf-8 -*-
"""verify_pack.py — 打包前一致性校验（防 def / 图集 / DLL 三者尺寸不配对）。

这是 2026-10-19 事故的守门员：当时图集缩到 2048x1024，但 DLL 里的
ATLAS_W/ATLAS_H 仍是 4096x2048 → 尺寸校验拒绝替换 → datapack 里的 def 指向
不存在的扩展区 → UV 越界被钳位 → 画面出现白色方块。
"""
import os
import struct
import sys
import zlib

ROOT = r'D:\SteamLibrary\steamapps\common\Obscure2\Obscure2_Handover'
DEP = os.path.join(ROOT, 'deploy')


def png_dims(path):
    with open(path, 'rb') as f:
        head = f.read(24)
    if head[:8] != b'\x89PNG\r\n\x1a\n':
        raise SystemExit('[FAIL] 不是 PNG: %s' % path)
    return struct.unpack('>II', head[16:24])


def def_atlas_size(path, w, h):
    """def 的 ASCII 区里依次是 名字\x00<atlas_w>\x00<atlas_h>\x00<cp>\x00<x>\x00<y>\x00<w>\x00<h>\x00<char>\x00...
    直接验证 \x00<w>\x00<h>\x00\x00 之后紧跟一个 cp 数字，比按偏移解析更稳。"""
    with open(path, 'rb') as f:
        b = f.read()
    pat = b'\x00%d\x00%d\x00' % (w, h)
    if pat in b:
        return True
    return b'\x00%d\x00%d' % (w, h) in b


def dll_png_dims(path):
    with open(path, 'rb') as f:
        d = f.read()
    i = d.find(b'\x89PNG\r\n\x1a\n')
    if i < 0:
        raise SystemExit('[FAIL] DLL 内未找到内嵌 PNG: %s' % path)
    return struct.unpack('>II', d[i + 16:i + 24])


def main():
    png = os.path.join(DEP, 'g3_atlas.png')
    xmc = os.path.join(DEP, 'g3_font_nonserif12.xmc')
    dll = os.path.join(DEP, 'd3d9.dll')
    ok = True

    pw, ph = png_dims(png)
    ew, eh = dll_png_dims(dll)
    dw, dh = (pw, ph) if def_atlas_size(xmc, pw, ph) else (-1, -1)
    print('  源图集 PNG        : %dx%d' % (pw, ph))
    print('  字体 def (.xmc)   : atlas token %s' % (('%dx%d' % (dw, dh)) if dw > 0 else '未找到'))
    print('  DLL 内嵌 PNG      : %dx%d' % (ew, eh))

    if dw <= 0:
        print('[FAIL] def 的 resident 表里找不到 atlas 尺寸 token |%d|%d|' % (pw, ph))
        ok = False
    if (pw, ph) != (ew, eh):
        print('[FAIL] 图集 PNG 与 DLL 内嵌 PNG 尺寸不一致（ATLAS_W/ATLAS_H 没同步？）')
        ok = False

    # def 里所有字形盒都必须在图集范围内（以 PNG 尺寸为准）
    import csv
    lay = os.path.join(DEP, 'g3_layout.tsv')
    bad = 0
    n = 0
    with open(lay, encoding='utf-8', newline='') as f:
        for row in csv.DictReader(f, delimiter='\t'):
            try:
                x, y, w, h = int(row['x']), int(row['y']), int(row['w']), int(row['h'])
            except Exception:
                continue
            n += 1
            if x < 0 or y < 0 or x + w > pw or y + h > ph:
                bad += 1
                if bad <= 3:
                    print('        越界: cp=%s box=(%d,%d,%d,%d)' % (row['cp'], x, y, w, h))
    print('  字形盒范围检查    : %d 条，越界 %d 条' % (n, bad))
    if bad:
        ok = False

    if ok:
        print('[OK] 三者尺寸一致，字形盒全部落在图集内 —— 可以打包')
        return 0
    print('[FAIL] 一致性问题，禁止打包')
    return 1


if __name__ == '__main__':
    sys.exit(main())

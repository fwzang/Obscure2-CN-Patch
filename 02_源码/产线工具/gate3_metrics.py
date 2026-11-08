# -*- coding: utf-8 -*-
"""gate3_metrics.py — T2b: 原版 nonserif12 字形墨迹基线测量

目的: 测出原版字体在 25px 盒内的墨迹分布（cap height / x-height / baseline /
descender / 垂直位置约定），为全量 CJK 字形渲染确定尺寸与对齐参数。
"""
import struct, os, sys

RECON = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIC = os.path.join(RECON, 'x_data', 'unk_file_1507403136.dat')
FONT = os.path.join(RECON, 'x_data', 'unk_folder_1920272591', 'unk_file_3530817756.dat')

import re
d = open(DIC, 'rb').read()
doff = None
for m in re.finditer(rb'[\x20-\x7e]{2,64}', d):
    s, e = m.start(), m.end()
    if s < 4 or struct.unpack_from('>I', d, s - 4)[0] != e - s:
        continue
    if m.group() != b'font_nonserif12':
        continue
    mip, b, c, w, h, fmt, size = struct.unpack_from('>IIIIIII', d, e)
    if size == w * h * 4:
        doff = e + 28
        break
assert doff, 'atlas not found'
AW, AH = 512, 256
atlas = d[doff:doff + AW * AH * 4]

fd = open(FONT, 'rb').read()
f2 = struct.unpack_from('<I', fd, 8)[0]
ng = struct.unpack_from('<H', fd, 0x12)[0]
asc = len(fd) - f2
toks = []
i = asc
while i < len(fd):
    j = fd.find(b'\x00', i)
    if j < 0:
        toks.append(fd[i:]); break
    toks.append(fd[i:j]); i = j + 1
toks = toks[:3 + 6 * (ng - 1)]
glyphs = []
for k in range(ng - 1):
    p = 3 + 6 * k
    glyphs.append((int(toks[p]), int(toks[p + 1]), int(toks[p + 2]),
                   int(toks[p + 3]), int(toks[p + 4]), toks[p + 5]))
by_cp = {g[0]: g for g in glyphs}


def ink_bbox(cp):
    g = by_cp.get(cp)
    if not g:
        return None
    _, x, y, w, h, _ = g
    x0, y0, x1, y1 = w, h, -1, -1
    for yy in range(h):
        for xx in range(w):
            a = atlas[((y + yy) * AW + x + xx) * 4 + 3]
            r = atlas[((y + yy) * AW + x + xx) * 4]
            if a or r:
                x0 = min(x0, xx); x1 = max(x1, xx)
                y0 = min(y0, yy); y1 = max(y1, yy)
    if x1 < 0:
        return (x, y, w, h, None)
    return (x, y, w, h, (x0, y0, x1, y1))


print('=' * 74)
print('T2b: 原版字形墨迹测量（盒内相对坐标, 盒高恒 25）')
print('=' * 74)
PROBE = [('A', 65), ('H', 72), ('x', 120), ('o', 111), ('p', 112), ('g', 103),
         ('j', 106), ('i', 73), ('0', 48), ('8', 56), ('%', 37), ('W', 87),
         ('逗号式引号’', 8217), ('空格', 32), ('M', 77)]
for label, cp in PROBE:
    r = ink_bbox(cp)
    if not r:
        print('  %-12s cp=%-5d 无此字形' % (label, cp)); continue
    x, y, w, h, bb = r
    if bb is None:
        print('  %-12s cp=%-5d box=(%d,%d,%d,%d) 无墨迹' % (label, cp, x, y, w, h))
    else:
        print('  %-12s cp=%-5d box=(%3d,%3d,%2d,%2d) ink=(x%d..%d y%d..%d) '
              'ink_w=%d ink_h=%d 上边距=%d 下边距=%d' % (
                  label, cp, x, y, w, h, bb[0], bb[1 + 0] if False else bb[2],
                  bb[1], bb[3], bb[2] - bb[0] + 1, bb[3] - bb[1] + 1,
                  bb[1], h - 1 - bb[3]))

# 统计全部有墨迹字形的 ink 顶/底分布
tops, bots, hs, ws = [], [], [], []
for g in glyphs:
    r = ink_bbox(g[0])
    if r and r[4]:
        bb = r[4]
        tops.append(bb[1]); bots.append(bb[3]); hs.append(bb[3] - bb[1] + 1)
        ws.append(bb[2] - bb[0] + 1)
print('\n全部 %d 字形中 %d 个有墨迹:' % (len(glyphs), len(tops)))
import collections
print('  ink_top 分布: %s' % dict(sorted(collections.Counter(tops).items())))
print('  ink_bot 分布: %s' % dict(sorted(collections.Counter(bots).items())))
print('  ink_h 范围: %d..%d' % (min(hs), max(hs)))
print('  ink_w 范围: %d..%d' % (min(ws), max(ws)))

# y 行聚簇
ys = collections.Counter(g[2] for g in glyphs)
print('  盒 y 行聚簇: %s' % dict(sorted(ys.items())))
# x 最大
print('  盒 x 范围: %d..%d' % (min(g[1] for g in glyphs), max(g[1] + g[3] for g in glyphs)))

# 检查 RGB 通道: 原版是否也是 RGB=灰度/alpha=coverage 的双通道
print('\n[双通道核验] 抽样字形 RGB vs alpha 关系:')
for label, cp in [('A', 65), ('o', 111), ('M', 77)]:
    g = by_cp[cp]
    _, x, y, w, h, _ = g
    pairs = set()
    for yy in range(h):
        for xx in range(w):
            o = ((y + yy) * AW + x + xx) * 4
            a = atlas[o + 3]; r = atlas[o]
            if a:
                pairs.add((r, a))
    lst = sorted(pairs)[:6]
    print('  %s: (R,alpha) 样本 %s' % (label, lst))

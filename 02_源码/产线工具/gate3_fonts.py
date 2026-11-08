# -*- coding: utf-8 -*-
"""gate3_fonts.py — T2a: 四字体 def inventory + dic 全条目 + 字符串→字体归属线索

回答 Q4: mkabel12 / Arial / Lucida 是否承载可见文本（各自 glyph inventory 与
'%' '·' '_' 等字符的覆盖情况）。
"""
import struct, os, re, sys

RECON = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONT_DIR = os.path.join(RECON, 'x_data', 'unk_folder_1920272591')
DIC = os.path.join(RECON, 'x_data', 'unk_file_1507403136.dat')

FONTS = {
    'unk_file_1075623915.dat': 'Arial?',
    'unk_file_2405740849.dat': 'mkabel12',
    'unk_file_2848500833.dat': 'Lucida?',
    'unk_file_3530817756.dat': 'nonserif12',
}


def parse_font(path):
    d = open(path, 'rb').read()
    f0, f1, f2 = struct.unpack_from('<III', d, 0)
    ng = struct.unpack_from('<H', d, 0x12)[0]
    asc = len(d) - f2
    toks = []
    i = asc
    while i < len(d):
        j = d.find(b'\x00', i)
        if j < 0:
            toks.append(d[i:]); break
        toks.append(d[i:j]); i = j + 1
    toks = toks[:3 + 6 * (ng - 1)]
    name = toks[0].decode('latin1')
    aw, ah = int(toks[1]), int(toks[2])
    glyphs = []
    for k in range(ng - 1):
        p = 3 + 6 * k
        glyphs.append((int(toks[p]), int(toks[p + 1]), int(toks[p + 2]),
                       int(toks[p + 3]), int(toks[p + 4]), toks[p + 5]))
    return dict(size=len(d), f0=f0, f1=f1, f2=f2, ng=ng, asc=asc,
                name=name, aw=aw, ah=ah, glyphs=glyphs)


print('=' * 78)
print('T2a: 四字体 def inventory')
print('=' * 78)
allglyphs = {}
for fn, label in FONTS.items():
    p = os.path.join(FONT_DIR, fn)
    if not os.path.exists(p):
        print('%s: 不存在' % fn); continue
    info = parse_font(p)
    allglyphs[label] = info
    cps = [g[0] for g in info['glyphs']]
    chars = ''.join(g[5].decode('latin1') for g in info['glyphs'] if g[5])
    print('\n[%s] %s' % (label, fn))
    print('  name=%r atlas=%dx%d ng=%d size=%d f0=%d f1=%d f2=%d' % (
        info['name'], info['aw'], info['ah'], info['ng'], info['size'],
        info['f0'], info['f1'], info['f2']))
    print('  cp 范围: %d..%d' % (min(cps), max(cps)))
    print('  chars: %r' % chars[:120])
    for probe in ['%', '_', '·', '’', ' ']:
        hit = probe in chars
        print('    含 %r: %s' % (probe, '是' if hit else '否'))

print()
print('=' * 78)
print('T2a: dic 全条目（unk_file_1507403136.dat）')
print('=' * 78)
d = open(DIC, 'rb').read()
print('dic size = %d (0x%X)' % (len(d), len(d)))
ents = []
for m in re.finditer(rb'[\x20-\x7e]{2,64}', d):
    s, e = m.start(), m.end()
    if s < 4:
        continue
    ln = struct.unpack_from('>I', d, s - 4)[0]
    if ln != e - s:
        continue
    nm = m.group().decode('latin1')
    if not re.fullmatch(r'[A-Za-z0-9_\\/\-\.]{2,64}', nm):
        continue
    base = e
    if base + 28 > len(d):
        continue
    mip, b, c, w, h, fmt, size = struct.unpack_from('>IIIIIII', d, base)
    if size > len(d) or w > 4096 or h > 4096 or size != w * h * 4:
        continue
    ents.append((nm, mip, b, c, w, h, fmt, size, base + 28))
for nm, mip, b, c, w, h, fmt, size, off in ents:
    print('  %-24s mip=%d b=%d c=%d %dx%d fmt=%d size=%d data@0x%X' % (
        nm, mip, b, c, w, h, fmt, size, off))
print('共 %d 个 RGBA 条目' % len(ents))

# 全局头
print('\ndic 头 16B: %s' % d[:16].hex())

# -*- coding: utf-8 -*-
"""gate3_atlas.py — T3: 生成全量图集（v1: 4096x2048 @ 25px 盒）

==================== 版布与参数设计 ====================
容量冗余（用户 2026-10-18 要求）:
  图集开到 4096x2048（而非最低所需的 2048x1024），为后期字号放大
  （28px/30px 盒）预留槽位，避免推倒重来。当前 25px 盒仅用 ~14% 槽位。
  改字号只需改下面 CONFIG 区的 FONT_SIZE/BOX_W/BOX_H/PITCH_* 重跑本脚本
  （图集尺寸不变、def/代理架构不变）。

版布方案（Option A 保留+扩展，两种 UV 归一化解释下均正确）:
  - 新图集 4096x2048 RGBA，左上 512x256 = 原版图集字节级复制
    → 现有 155 字形盒不变，其内容原位保留
  - 扩展区 x∈[512,4096): 槽位 pitch 18(x) x 27(y) @25px 盒
  - def 的 atlas_w/h 同步改 4096/2048（T4 负责），D3D9 代理在运行时
    把原版 512x256 纹理替换为本图集

字形渲染参数（与 Gate 2 实证一致, one-variable-at-a-time）:
  - 字体 msyh.ttc; 双通道 RGB=232*g//255, alpha=g
  - CJK 表意字: 墨迹居中于盒（Gate 2 同款算法）
  - 全角/CJK 标点: 基线对齐（'la' 锚点，基线落在盒内 y+21 = 原版拉丁基线）
  - 窄补充符: '·' 盒宽8 基线对齐; '_' 盒宽=墨迹宽 墨迹底 y+23; '%' 墨迹宽居中

输入:
  recon/x_data/unk_file_1507403136.dat        原版 dic（md5 782349852c9ba7aa93ddba74016cee35）
  recon/x_data/unk_folder_1920272591/unk_file_3530817756.dat  原版 def（md5 4ba16736d1cad89b02cd208de0bd020e）
  recon/gate3/g3_charset.tsv                  T1 定稿字形集

输出:
  g3_atlas.png          4096x2048 RGBA 全量图集（供 DLL 内嵌）
  g3_atlas_preview.png  已用区域 2x 预览 + 样例放大条
  g3_layout.tsv         全量字形盒位清单（T4 输入）
  g3_atlas_report.txt   构建报告
"""
import struct, os, sys, re, csv, zlib, unicodedata
from PIL import Image, ImageDraw, ImageFont

# ==================== CONFIG（改字号只动这里）====================
NEW_W, NEW_H = 4096, 2048      # 图集尺寸（冗余容量, 勿低于 2048x1024）
FONT_PATH = r'C:\Windows\Fonts\msyh.ttc'
FONT_SIZE = 16                 # 渲染字号（v1=16, 墨迹~14px; v2 可试 19/21）
BOX_W, BOX_H = 16, 25          # 标准盒（v1=16x25 与原版字体 em 盒一致）
PITCH_X, PITCH_Y = 18, 27      # 槽位步距 = 盒 + 2px gutter
EXT_X0 = 512                   # 扩展区起点（左侧保留原版 512x256）
TARGET_GRAY = 232              # 双通道可见灰度（Gate 1/2 实证）
BASE_Y = 21                    # 原版拉丁基线（盒内 y+21, T2b 实测）
# ================================================================

SRC_W, SRC_H = 512, 256
RECON = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIC = os.path.join(RECON, 'x_data', 'unk_file_1507403136.dat')
FONT_DEF = os.path.join(RECON, 'x_data', 'unk_folder_1920272591', 'unk_file_3530817756.dat')
CHARSET = os.path.join(RECON, 'gate3', 'g3_charset.tsv')
OUT = RECON + r'\gate3'

CJK_RANGES = [(0x3400, 0x4DBF), (0x4E00, 0x9FFF), (0xF900, 0xFAFF)]
FULLWIDTH_PUNCT = {0x3001, 0x3002, 0x300A, 0x300B, 0x3010, 0x3011,
                   0xFF01, 0xFF08, 0xFF09, 0xFF0C, 0xFF1A, 0xFF1B, 0xFF1F,
                   0x2014, 0x201C, 0x201D, 0x2026}
NARROW = {0x00B7: 'dot', 0x005F: 'uscore', 0x0025: 'percent'}


def in_ranges(cp, ranges):
    return any(a <= cp <= b for a, b in ranges)


def parse_font_def(path):
    d = open(path, 'rb').read()
    f2 = struct.unpack_from('<I', d, 8)[0]
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
    glyphs = []
    for k in range(ng - 1):
        p = 3 + 6 * k
        glyphs.append((int(toks[p]), int(toks[p + 1]), int(toks[p + 2]),
                       int(toks[p + 3]), int(toks[p + 4]), toks[p + 5]))
    return glyphs


def extract_original_atlas():
    d = open(DIC, 'rb').read()
    for m in re.finditer(rb'[\x20-\x7e]{2,64}', d):
        s, e = m.start(), m.end()
        if s < 4 or struct.unpack_from('>I', d, s - 4)[0] != e - s:
            continue
        if m.group() != b'font_nonserif12':
            continue
        mip, b, c, w, h, fmt, size = struct.unpack_from('>IIIIIII', d, e)
        if size == w * h * 4 and w == SRC_W and h == SRC_H:
            return d[e + 28:e + 28 + size], (w, h, fmt, mip, e + 28)
    raise AssertionError('font_nonserif12 atlas not found in dic')


def write_png(path, w, h, rgba):
    def chunk(tag, data):
        c = struct.pack('>I', len(data)) + tag + data
        return c + struct.pack('>I', zlib.crc32(tag + data) & 0xFFFFFFFF)
    raw = b''.join(b'\x00' + rgba[y * w * 4:(y + 1) * w * 4] for y in range(h))
    png = b'\x89PNG\r\n\x1a\n'
    png += chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 6, 0, 0, 0))
    png += chunk(b'IDAT', zlib.compress(raw, 9))
    png += chunk(b'IEND', b'')
    open(path, 'wb').write(png)


def capacity(box_w, box_h, pitch_x, pitch_y):
    cols = (NEW_W - EXT_X0 - box_w) // pitch_x + 1
    rows = (NEW_H - box_h) // pitch_y + 1
    return cols, rows, cols * rows


def main():
    print('=' * 78)
    print('T3: 全量图集生成（CONFIG: %dx%d @ 盒 %dx%d pitch %dx%d, %s size %d）'
          % (NEW_W, NEW_H, BOX_W, BOX_H, PITCH_X, PITCH_Y,
             os.path.basename(FONT_PATH), FONT_SIZE))
    print('=' * 78)

    # ---- 0. 未来字号容量预测（冗余验证）----
    print('[冗余] 当前图集 %dx%d 对未来字号的槽位容量:' % (NEW_W, NEW_H))
    for fs, bw, bh, px, py in [(16, 16, 25, 18, 27), (19, 19, 29, 21, 31),
                               (21, 21, 32, 23, 34), (24, 24, 36, 26, 38),
                               (28, 28, 42, 30, 44)]:
        c, r, cap = capacity(bw, bh, px, py)
        print('   字号~%2dpx(盒%2dx%2d): %3d列x%2d行 = %5d 槽 %s'
              % (fs, bw, bh, c, r, cap, 'OK' if cap >= 2150 else '不足!'))

    # ---- 1. 原版图集 + def ----
    orig_rgba, (w0, h0, fmt0, mip0, doff) = extract_original_atlas()
    print('\n[原版] dic font_nonserif12: %dx%d fmt=%d mip=%d data@0x%X (%d B)'
          % (w0, h0, fmt0, mip0, doff, len(orig_rgba)))
    assert (w0, h0) == (SRC_W, SRC_H) and len(orig_rgba) == SRC_W * SRC_H * 4
    exist = parse_font_def(FONT_DEF)
    print('[原版] def: %d 字形' % len(exist))

    # ---- 2. 新字形集 ----
    newg = []
    with open(CHARSET, encoding='utf-8', newline='') as f:
        r = csv.reader(f, delimiter='\t'); next(r)
        for row in r:
            cp, cl, isnew = int(row[0]), row[2], row[4]
            if isnew != '1':
                continue
            if cp < 0x20 or cp == 0x7F:
                print('  [跳过] 控制字符 cp=%d' % cp); continue
            if unicodedata.category(chr(cp)).startswith('C'):
                print('  [跳过] 控制/格式字符 cp=%d' % cp); continue
            newg.append((cp, cl))
    print('[字形] 新增 %d / 现有 %d / 全量 %d' % (
        len(newg), len(exist), len(newg) + len(exist)))

    # ---- 3. 槽位 ----
    cols, rows, cap = capacity(BOX_W, BOX_H, PITCH_X, PITCH_Y)
    print('[槽位] 扩展区 x>=%d: %d 列 x %d 行 = %d 槽（需 %d，余 %d）'
          % (EXT_X0, cols, rows, cap, len(newg), cap - len(newg)))
    assert cap >= len(newg), '槽位不足'

    # ---- 4. 建图集 ----
    atlas = bytearray(NEW_W * NEW_H * 4)
    for yy in range(SRC_H):
        atlas[yy * NEW_W * 4: yy * NEW_W * 4 + SRC_W * 4] = \
            orig_rgba[yy * SRC_W * 4: (yy + 1) * SRC_W * 4]
    ok_copy = all(atlas[yy * NEW_W * 4 + xx * 4: yy * NEW_W * 4 + xx * 4 + 4]
                  == orig_rgba[(yy * SRC_W + xx) * 4: (yy * SRC_W + xx) * 4 + 4]
                  for yy in range(SRC_H) for xx in range(SRC_W))
    print('[复制] 原版 512x256 区域字节级一致: %s' % ok_copy)
    assert ok_copy

    font = ImageFont.truetype(FONT_PATH, FONT_SIZE)
    ascent, descent = font.getmetrics()
    print('[字体] %s size=%d ascent=%d descent=%d'
          % (os.path.basename(FONT_PATH), FONT_SIZE, ascent, descent))

    # ---- 5. 逐字形渲染落位 ----
    layout = []
    slot = 0
    n_by_kind = {}
    for cp, cl in sorted(newg, key=lambda t: (t[1], t[0])):
        col, row = slot % cols, slot // cols
        slot += 1
        cx, cy = EXT_X0 + col * PITCH_X, row * PITCH_Y
        char = chr(cp)
        if cp in NARROW:
            kind = NARROW[cp]
        elif in_ranges(cp, CJK_RANGES):
            kind = 'cjk'
        elif cp in FULLWIDTH_PUNCT or cl == 'PUNCT':
            kind = 'punct_fw'
        else:
            kind = 'other'

        probe = Image.new('L', (48, 56), 0)
        pd = ImageDraw.Draw(probe)
        bb = pd.textbbox((0, 0), char, font=font)
        iw, ih = bb[2] - bb[0], bb[3] - bb[1]

        if kind == 'dot':
            bw = 8
        elif kind == 'uscore':
            bw = max(4, min(16, iw))
        elif kind in ('cjk', 'punct_fw'):
            bw = BOX_W
        else:
            bw = max(4, min(BOX_W, iw + 1))

        tile = Image.new('L', (bw, BOX_H), 0)
        td = ImageDraw.Draw(tile)
        if kind in ('cjk', 'other', 'percent'):
            # 墨迹居中（Gate 2 同款算法; percent 亦按墨迹居中）
            ox = (bw - iw) // 2 - bb[0]
            oy = (BOX_H - ih) // 2 - bb[1]
            td.text((ox, oy), char, fill=255, font=font)
        elif kind == 'punct_fw':
            td.text((0, BASE_Y - ascent), char, fill=255, font=font)
        elif kind == 'dot':
            ox = (bw - iw) // 2 - bb[0]
            td.text((ox, BASE_Y - ascent), char, fill=255, font=font)
        elif kind == 'uscore':
            ox = (bw - iw) // 2 - bb[0]
            oy = (BASE_Y + 2) - bb[3]
            td.text((ox, oy), char, fill=255, font=font)

        # 双通道落墨
        tp = tile.load()
        n_ink = 0
        for yy in range(BOX_H):
            for xx in range(bw):
                g = tp[xx, yy]
                if g:
                    n_ink += 1
                    v = TARGET_GRAY * g // 255
                    o = ((cy + yy) * NEW_W + cx + xx) * 4
                    atlas[o] = v; atlas[o + 1] = v; atlas[o + 2] = v; atlas[o + 3] = g
        assert n_ink > 0, '字形 %r(cp=%d) 无墨迹' % (char, cp)
        ix0, iy0, ix1, iy1 = bw, BOX_H, -1, -1
        for yy in range(BOX_H):
            for xx in range(bw):
                if tp[xx, yy]:
                    ix0 = min(ix0, xx); ix1 = max(ix1, xx)
                    iy0 = min(iy0, yy); iy1 = max(iy1, yy)
        layout.append((cp, char, cl, cx, cy, bw, BOX_H, kind,
                       ix1 - ix0 + 1, iy1 - iy0 + 1, iy0, BOX_H - 1 - iy1, n_ink))
        n_by_kind[kind] = n_by_kind.get(kind, 0) + 1

    print('[渲染] 各类: %s' % n_by_kind)
    print('[渲染] 使用槽位 %d / %d' % (slot, cap))

    # ---- 6. 写出 PNG ----
    p_atlas = os.path.join(OUT, 'g3_atlas.png')
    write_png(p_atlas, NEW_W, NEW_H, bytes(atlas))
    print('[输出] %s (%d B)' % (p_atlas, os.path.getsize(p_atlas)))

    # ---- 7. 预览: 原版区+扩展区首用区 2x + 样例放大 ----
    img = Image.frombytes('RGBA', (NEW_W, NEW_H), bytes(atlas))
    used_rows = (slot + cols - 1) // cols
    crop_h = min(NEW_H, used_rows * PITCH_Y + 4)
    crop_w = min(NEW_W, EXT_X0 + min(cols, 60) * PITCH_X + 4)
    ext = img.crop((0, 0, crop_w, crop_h)).resize((crop_w * 2, crop_h * 2),
                                                  Image.NEAREST)
    bg = Image.new('RGBA', ext.size, (24, 24, 28, 255))
    bg.alpha_composite(ext)
    gd = ImageDraw.Draw(bg)
    for rr in range(used_rows + 1):
        y = rr * PITCH_Y * 2
        gd.line([(EXT_X0 * 2, y), (bg.width, y)], fill=(255, 60, 60, 80))
    for cc in range(0, min(cols, 60) + 1, 10):
        x = (EXT_X0 + cc * PITCH_X) * 2
        gd.line([(x, 0), (x, bg.height)], fill=(255, 60, 60, 80))
    gd.line([(EXT_X0 * 2, 0), (EXT_X0 * 2, bg.height)], fill=(0, 200, 255, 160))
    # 样例条: 同样参数渲染混合文本（含 CJK/标点/拉丁/补充符）
    sample = '你好，世界。测试ABC ghip123%·_'
    fsz = 48
    strip = Image.new('RGBA', (len(sample) * (fsz + 8), fsz + 24), (24, 24, 28, 255))
    sd = ImageDraw.Draw(strip)
    sd.text((6, 8), sample, font=ImageFont.truetype(FONT_PATH, fsz),
            fill=(232, 232, 232, 255))
    # 单字放大阵列: 抽 24 个代表性新字形 4x 展示
    picks = [c for c in layout if c[7] == 'cjk'][:8] + \
            [c for c in layout if c[7] == 'punct_fw'][:10] + \
            [c for c in layout if c[7] != 'cjk' and c[7] != 'punct_fw']
    cell = 100
    grid = Image.new('RGBA', (8 * cell, ((len(picks) + 7) // 8) * cell),
                     (24, 24, 28, 255))
    gdd = ImageDraw.Draw(grid)
    for i, g in enumerate(picks):
        cp, char, cl, cx, cy, bw, bh, kind = g[:8]
        sub = img.crop((cx - 2, cy - 2, cx + bw + 2, cy + bh + 2))
        sub = sub.resize((sub.width * 3, sub.height * 3), Image.NEAREST)
        px, py = (i % 8) * cell + 8, (i // 8) * cell + 8
        grid.alpha_composite(sub, (px, py))
        gdd.text((px, py + 84), 'U+%04X %s' % (cp, kind), fill=(160, 200, 255, 255))
    W = max(bg.width, strip.width, grid.width)
    H = bg.height + strip.height + grid.height + 24
    canvas = Image.new('RGBA', (W, H), (16, 16, 20, 255))
    canvas.paste(bg, (0, 0))
    canvas.paste(strip, (0, bg.height + 8))
    canvas.paste(grid, (0, bg.height + strip.height + 16))
    p_prev = os.path.join(OUT, 'g3_atlas_preview.png')
    canvas.save(p_prev)
    print('[输出] %s (%dx%d)' % (p_prev, canvas.width, canvas.height))

    # ---- 8. 布局清单 ----
    p_layout = os.path.join(OUT, 'g3_layout.tsv')
    with open(p_layout, 'w', encoding='utf-8', newline='') as f:
        w = csv.writer(f, delimiter='\t')
        w.writerow(['cp', 'char', 'cls', 'x', 'y', 'w', 'h', 'kind',
                    'ink_w', 'ink_h', 'ink_top', 'ink_bot_margin', 'ink_px', 'new'])
        for cp, x, y, bw, bh, chb in exist:
            w.writerow([cp, chb.decode('latin1'), 'EXIST', x, y, bw, bh,
                        'exist', '', '', '', '', '', 0])
        for row in layout:
            w.writerow(list(row[:13]) + [1])
    print('[输出] %s（%d 行）' % (p_layout, len(exist) + len(layout)))

    # ---- 9. 报告 ----
    rep = os.path.join(OUT, 'g3_atlas_report.txt')
    with open(rep, 'w', encoding='utf-8') as f:
        f.write('Gate 3 T3 全量图集构建报告（v1 @ 25px 盒）\n')
        f.write('=' * 60 + '\n')
        f.write('图集: %dx%d RGBA（左上 512x256=原版字节级复制；扩展区 x>=512）\n'
                % (NEW_W, NEW_H))
        f.write('CONFIG: FONT_SIZE=%d BOX=%dx%d PITCH=%dx%d GRAY=%d BASE_Y=%d\n'
                % (FONT_SIZE, BOX_W, BOX_H, PITCH_X, PITCH_Y, TARGET_GRAY, BASE_Y))
        f.write('槽位: %d 列 x %d 行 = %d, 使用 %d（余 %d = %.0f%% 冗余）\n'
                % (cols, rows, cap, slot, cap - slot, 100.0 * (cap - slot) / cap))
        f.write('字形: 现有 %d（盒不变）+ 新增 %d = %d\n'
                % (len(exist), len(layout), len(exist) + len(layout)))
        f.write('字体: %s size %d; 双通道 RGB=%d*g//255, alpha=g\n'
                % (FONT_PATH, FONT_SIZE, TARGET_GRAY))
        f.write('分类: %s\n' % n_by_kind)
        f.write('\n未来字号容量预测:\n')
        for fs, bw, bh, px, py in [(19, 19, 29, 21, 31), (21, 21, 32, 23, 34),
                                   (24, 24, 36, 26, 38), (28, 28, 42, 30, 44)]:
            c, r, cp_ = capacity(bw, bh, px, py)
            f.write('  字号~%2dpx(盒%2dx%2d): %d 槽 %s\n'
                    % (fs, bw, bh, cp_, 'OK' if cp_ >= 2150 else '不足'))
        f.write('\n基线约定（T2b 实测原版）: 盒高 25, cap 顶 y+6, 基线 y+21, '
                '降部 y+24; advance=盒宽\n')
        f.write('渲染规则: CJK/窄符=墨迹居中(Gate2 同款); 全角标点=基线对齐(la 锚点)\n')
        f.write('\n注意: 本图集由 D3D9 代理在运行时替换显存纹理; 代理缺位时游戏'
                '将渲染错乱（预期 FAIL 行为，属正常）\n')
        f.write('授权注记: v1 用 msyh.ttc(微软雅黑) 与 Gate 2 保持一致; '
                '发布版应换 Noto Sans SC(OFL) 重渲并复验\n')
    print('[输出] %s' % rep)
    print('\n★ T3 完成: 图集 %dx%d, 全量字形 %d, 槽位余 %d'
          % (NEW_W, NEW_H, len(exist) + len(layout), cap - slot))
    return 0


if __name__ == '__main__':
    sys.exit(main())

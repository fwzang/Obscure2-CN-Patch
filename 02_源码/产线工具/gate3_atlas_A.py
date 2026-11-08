# -*- coding: utf-8 -*-
"""gate3_atlas.py — T3: 生成全量图集（20px @ 盒 19x25, 2048x1024）

==================== 版布与参数设计 ====================
图集尺寸（2026-10-19 定稿；参数复现验证见 _verify/CONFIG复现验证_图集20px.md）:
  2048x1024（**不是** 4096x2048：43MB+13 级 mip 会让设备 Reset 返回
  0x8876086C）。改字号必须同时改 CONFIG 的 FONT_SIZE/BOX_W/BOX_H/PITCH_*
  并重跑本脚本，**且必须三处同步**：d3d9_proxy.c 的 ATLAS_W/ATLAS_H、
  T4 重生成 def、以及 DLL 内嵌图集(atlas_png.h)重新生成。少改一处 →
  尺寸自检拒绝替换 → def 与纹理不配对 → 画面白块/错位。

版布方案（Option A 保留+扩展）:
  - 新图集 2048x1024 RGBA，左上 512x256 = 原版图集字节级复制
    → 现有 155 字形中 65 个盒不变原位保留（含 19 个空 char 手柄图标槽）；
      90 个可打印 ASCII 用同一字体重渲染后搬到扩展区（cp/char 不动，只改坐标）
  - 扩展区 x∈[512,2048): 槽位 pitch 21(x) x 27(y) @ 盒 19x25
    → 73 列 x 38 行 = 2774 槽，使用 2261（余 513 ≈ 19% 冗余）
  - def 的 atlas_w/h 同步 2048/1024（T4 负责），D3D9 代理在运行时
    把原版 512x256 纹理替换为本图集

字形渲染参数（与 Gate 2 实证一致, one-variable-at-a-time）:
  - 字体 msyh.ttc; 双通道 RGB=232*g//255, alpha=g
  - CJK 表意字: 墨迹居中于盒（Gate 2 同款算法）
  - 全角/CJK 标点: 基线对齐（'la' 锚点，基线落在盒内 y+21 = 原版拉丁基线）
  - 窄补充符: '·' 盒宽8 基线对齐; '_' 盒宽=墨迹宽 墨迹底 y+23; '%' 墨迹宽居中

输入:
  _work/x_orig/unk_file_1507403136.dat                        原版 dic（含 font_nonserif12 512x256 图集）
  _work/x_orig/unk_folder_1920272591/unk_file_3530817756.dat  原版 def（只读基线, 勿覆盖）
  _work/g4/g3_charset.tsv                                     T1 定稿字形集（2171 新增）

输出:
  g3_atlas.png          4096x2048 RGBA 全量图集（供 DLL 内嵌）
  g3_atlas_preview.png  已用区域 2x 预览 + 样例放大条
  g3_layout.tsv         全量字形盒位清单（T4 输入）
  g3_atlas_report.txt   构建报告
"""
import struct, os, sys, re, csv, zlib, unicodedata
from PIL import Image, ImageDraw, ImageFont

RECON = r'D:\SteamLibrary\steamapps\common\Obscure2\Obscure2_Handover'

# ==================== CONFIG（改字号只动这里）====================
NEW_W, NEW_H = 2048, 1024      # 图集尺寸（20px 紧凑；4096x2048 的 43MB+13级mip 会让 Reset 失败）
FONT_PATH = os.path.join(RECON,
                         '_work', 'fonts', 'ChillDuanSans_Bold.otf')
FONT_SIZE = 20                 # 渲染字号（2026-10-19 定稿；md5 复现验证 = 出厂图集 e172a188）
BOX_W, BOX_H = 19, 25          # 20px 活楷体 advance=19；盒高 25 == 原版行高
PITCH_X, PITCH_Y = 21, 27      # 槽位步距（PITCH_X 运行时按最宽 ASCII 自动放大）
EXT_X0 = 512                   # 扩展区起点（左侧保留原版 512x256）
TARGET_GRAY = 232              # 双通道可见灰度（Gate 1/2 实证）
BASE_Y = 20                    # 基线（无描边：汉字墨迹 2..21，ASCII 2..16，'_' 19..20，零裁切）
# --- P0 中西文统一（2026-10-18）---
# 原版 155 个 ASCII 来自 font_nonserif12（粗体压缩）, 与中文风格完全不同
# -> 全部用同一字体重渲染。拉丁字号 = FONT_SIZE * ASCII_SCALE,
# 使数字 cap 高 ≈ 汉字墨高（活楷体 20px: 汉字墨高 16, ASCII cap 14）。
ASCII_SCALE = 1.0
# --- 边缘锐化（点采样下 AA 灰边会被固化，需在图集端削掉）---
ALPHA_THRESH = 0     # 0 = 关闭（用户定：保留原始平滑抗锯齿）
ALPHA_BINARIZE = 0   # 0 = 不二值化
STROKE_W = 0         # 0 = 无描边（用户定：描边太脏，回归原样）
SSAA = 3               # 超采样倍率：>1 时用 FONT_SIZE*SSAA 渲染再缩回盒内（边缘更平滑）
                        # 3 => 20px 字形按 60px 渲染后 BOX(面积平均) 缩到 19x25
                        # 实测 BOX 墨量与 1x 基准一致(-0.0%); LANCZOS 会 +5.6% 墨像素、显胖
# ================================================================

SRC_W, SRC_H = 512, 256
RECON = r'D:\SteamLibrary\steamapps\common\Obscure2\Obscure2_Handover'
DIC = os.path.join(RECON, '_work', 'x_orig', 'unk_file_1507403136.dat')
FONT_DEF = os.path.join(RECON, '_work', 'x_orig', 'unk_folder_1920272591', 'unk_file_3530817756.dat')
CHARSET = os.path.join(RECON, '_work', 'g4', 'g3_charset.tsv')
OUT = os.path.join(RECON, '_work', 'g4_A')

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
    print('T3: 全量图集生成【方案A 寒蝉端黑体 Bold】（CONFIG: %dx%d @ 盒 %dx%d pitch %dx%d, %s size %d）'
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

    # ---- 1b. 需要重渲染的原版 ASCII（P0 中西文统一）----
    # 只挑「char token 非空 且 正好等于 cp 的可打印 ASCII」。
    # 那 19 个空 char 的手柄图标槽（cp 8743/8744/9889 等）必须原样保留, 绝不能重画。
    rerender = []
    for cp, x, y, w, h, chb in exist:
        if not chb or len(chb) != 1:
            continue
        if not (0x20 <= cp <= 0x7E) or chb[0] != cp:
            continue
        rerender.append((cp, chr(cp)))
    print('[P0] 重渲染原版 ASCII: %d 个；原样保留 %d 个（含空 char 图标槽）'
          % (len(rerender), len(exist) - len(rerender)))

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

    # ---- 3. 字体与度量（必须先于槽位计算：PITCH_X 取决于最宽 ASCII）----
    font = ImageFont.truetype(FONT_PATH, FONT_SIZE)
    ss_font = ImageFont.truetype(FONT_PATH, FONT_SIZE * SSAA) if SSAA > 1 else font
    ascent, descent = font.getmetrics()
    ASCII_SIZE = int(round(FONT_SIZE * ASCII_SCALE))
    ascii_font = ImageFont.truetype(FONT_PATH, ASCII_SIZE)
    ss_ascii_font = (ImageFont.truetype(FONT_PATH, ASCII_SIZE * SSAA)
                    if SSAA > 1 else ascii_font)
    a_asc, a_desc = ascii_font.getmetrics()
    # 汉字: 让参考字形 '国' 的墨迹底正好落在 BASE_Y
    #   （原来用「墨迹居中」, 实测会整体浮高 1-2px, 这是混排不对齐的根因）
    cjk_oy = BASE_Y - font.getbbox('国')[3]
    # 拉丁: 让 '0' 的墨迹底正好落在 BASE_Y（与汉字墨迹底逐像素重合）
    ascii_oy = BASE_Y - ascii_font.getbbox('0')[3]
    print('[字体] CJK   %s size=%d asc/desc=%d/%d  oy=%d  墨高(国)=%d'
          % (os.path.basename(FONT_PATH), FONT_SIZE, ascent, descent, cjk_oy,
             font.getbbox('国')[3] - font.getbbox('国')[1]))
    print('[字体] ASCII %s size=%d asc/desc=%d/%d  oy=%d  cap(0)=%d'
          % (os.path.basename(FONT_PATH), ASCII_SIZE, a_asc, a_desc, ascii_oy,
             ascii_font.getbbox('0')[3] - ascii_font.getbbox('0')[1]))

    max_adv = 0
    for cp, ch in rerender:
        max_adv = max(max_adv, int(round(ascii_font.getlength(ch))))
    pitch_x = max(PITCH_X, BOX_W, max_adv + 2)
    print('[槽位] PITCH_X=%d（BOX_W=%d，最宽 ASCII advance=%d）'
          % (pitch_x, BOX_W, max_adv))

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

    # ---- 4b. 槽位 ----
    n_items = len(rerender) + len(newg)
    cols, rows, cap = capacity(BOX_W, BOX_H, pitch_x, PITCH_Y)
    print('[槽位] 扩展区 x>=%d: %d 列 x %d 行 = %d 槽（ASCII %d + 新增 %d = %d，余 %d）'
          % (EXT_X0, cols, rows, cap, len(rerender), len(newg), n_items, cap - n_items))
    assert cap >= n_items, '槽位不足'

    # ---- 5. 逐字形渲染落位 ----
    # 统一条目表: (cp, char, kind, font, oy, cls)。ASCII 与新增字形共用同一渲染器。
    items = [(cp, ch, 'ascii', ascii_font, ascii_oy, 'EXIST') for cp, ch in rerender]
    for cp, cl in sorted(newg, key=lambda t: (t[1], t[0])):
        c = chr(cp)
        if cp in NARROW:
            k = NARROW[cp]
        elif in_ranges(cp, CJK_RANGES):
            k = 'cjk'
        elif cp in FULLWIDTH_PUNCT or cl == 'PUNCT':
            k = 'punct_fw'
        else:
            k = 'other'
        items.append((cp, c, k, font, cjk_oy, cl))

    layout, layout_ascii = [], []
    slot = 0
    n_by_kind = {}
    for cp, char, kind, fnt, oy, cls in items:
        col, row = slot % cols, slot // cols
        slot += 1
        cx, cy = EXT_X0 + col * pitch_x, row * PITCH_Y

        probe = Image.new('L', (96, 96), 0)
        pd = ImageDraw.Draw(probe)
        bb = pd.textbbox((0, 0), char, font=fnt, stroke_width=STROKE_W)
        iw, ih = bb[2] - bb[0], bb[3] - bb[1]

        if kind == 'ascii':
            # 盒宽 = 该字符 advance（引擎 advance=盒宽, 西文必须保持比例宽度）
            bw = max(3, int(round(fnt.getlength(char))), bb[2] - bb[0])
        elif kind == 'dot':
            bw = 8
        elif kind == 'uscore':
            bw = max(4, min(BOX_W, iw))
        elif kind in ('cjk', 'punct_fw'):
            bw = BOX_W
        else:
            bw = max(4, min(BOX_W, iw + 1))
        bw = min(bw, BOX_W * 2)

        # ---- 绘制（可选 SSAA 超采样：大字号渲染后 LANCZOS 缩回盒内）----
        S = SSAA if SSAA > 1 else 1
        if S > 1:
            fd = ss_ascii_font if kind == 'ascii' else ss_font
            sw = STROKE_W * S
            big = Image.new('L', (bw * S, BOX_H * S), 0)
            bd = ImageDraw.Draw(big)
            if kind == 'ascii':
                ax = max(0, -bb[0])      # 描边会让左边承为负，补回来避免左侧被裁
                bd.text((ax * S, oy * S), char, fill=255, font=fd,
                        stroke_width=sw, stroke_fill=255)
            elif kind == 'uscore':
                ox = (bw - iw) // 2 - bb[0]
                bd.text((ox * S, ((BASE_Y + 2) - bb[3]) * S), char, fill=255,
                        font=fd, stroke_width=sw, stroke_fill=255)
            elif kind == 'punct_fw':
                bd.text((0, cjk_oy * S), char, fill=255, font=fd,      # 全角标点按 em 原点
                        stroke_width=sw, stroke_fill=255)
            else:
                ox = (bw - iw) // 2 - bb[0]                            # 汉字: 水平墨迹居中
                bd.text((ox * S, cjk_oy * S), char, fill=255, font=fd,
                        stroke_width=sw, stroke_fill=255)
            tile = big.resize((bw, BOX_H), Image.BOX)   # BOX=面积平均, 墨量与1x基准一致(实测-0.0%); LANCZOS会向外晕(+5.6%墨像素)
        else:
            tile = Image.new('L', (bw, BOX_H), 0)
            td = ImageDraw.Draw(tile)
            if kind == 'ascii':
                ax = max(0, -bb[0])      # 描边会让左边承为负，补回来避免左侧被裁
                td.text((ax, oy), char, fill=255, font=fnt, stroke_width=STROKE_W, stroke_fill=255)
            elif kind == 'uscore':
                ox = (bw - iw) // 2 - bb[0]
                td.text((ox, (BASE_Y + 2) - bb[3]), char, fill=255, font=fnt, stroke_width=STROKE_W, stroke_fill=255)
            elif kind == 'punct_fw':
                td.text((0, cjk_oy), char, fill=255, font=fnt, stroke_width=STROKE_W, stroke_fill=255)
            else:
                ox = (bw - iw) // 2 - bb[0]                  # 汉字: 水平墨迹居中
                td.text((ox, cjk_oy), char, fill=255, font=fnt, stroke_width=STROKE_W, stroke_fill=255)

        # 边缘锐化（点采样下 AA 灰边会被固化，这里直接削掉）
        if ALPHA_THRESH > 0:
            tq = tile.load()
            for yy in range(BOX_H):
                for xx in range(bw):
                    g = tq[xx, yy]
                    if g < ALPHA_THRESH:
                        tq[xx, yy] = 0
                    elif ALPHA_BINARIZE:
                        tq[xx, yy] = 255

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
        # 空白字符（空格等）本来就没有墨迹, 但仍需一条记录来承载 advance
        is_blank = (n_ink == 0 and (cp == 0x20 or
                    unicodedata.category(char).startswith('Z')))
        assert n_ink > 0 or is_blank, '字形 %r(cp=%d) 无墨迹' % (char, cp)
        ix0, iy0, ix1, iy1 = bw, BOX_H, -1, -1
        for yy in range(BOX_H):
            for xx in range(bw):
                if tp[xx, yy]:
                    ix0 = min(ix0, xx); ix1 = max(ix1, xx)
                    iy0 = min(iy0, yy); iy1 = max(iy1, yy)
        if ix1 < 0:
            ink_w = ink_h = ink_top = ink_bot = 0
        else:
            ink_w, ink_h, ink_top, ink_bot = (ix1 - ix0 + 1, iy1 - iy0 + 1,
                                              iy0, BOX_H - 1 - iy1)
        layout.append((cp, char, cls, cx, cy, bw, BOX_H, kind,
                       ink_w, ink_h, ink_top, ink_bot, n_ink))
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
    crop_w = min(NEW_W, EXT_X0 + min(cols, 60) * pitch_x + 4)
    ext = img.crop((0, 0, crop_w, crop_h)).resize((crop_w * 2, crop_h * 2),
                                                  Image.NEAREST)
    bg = Image.new('RGBA', ext.size, (24, 24, 28, 255))
    bg.alpha_composite(ext)
    gd = ImageDraw.Draw(bg)
    for rr in range(used_rows + 1):
        y = rr * PITCH_Y * 2
        gd.line([(EXT_X0 * 2, y), (bg.width, y)], fill=(255, 60, 60, 80))
    for cc in range(0, min(cols, 60) + 1, 10):
        x = (EXT_X0 + cc * pitch_x) * 2
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
    # ASCII 重渲染行不新增记录：它们占据原 155 条里的同名 cp，只是把盒换到扩展区，
    # 所以写成 new=0 + kind='ascii'，让 T4 原地改 token（cp/char 不动）。
    ascii_box = {}
    for row in layout:
        if row[7] == 'ascii':
            ascii_box[row[0]] = (row[3], row[4], row[5], row[6])
    n_ascii = len(ascii_box)
    p_layout = os.path.join(OUT, 'g3_layout.tsv')
    with open(p_layout, 'w', encoding='utf-8', newline='') as f:
        w = csv.writer(f, delimiter='\t')
        w.writerow(['cp', 'char', 'cls', 'x', 'y', 'w', 'h', 'kind',
                    'ink_w', 'ink_h', 'ink_top', 'ink_bot_margin', 'ink_px', 'new'])
        for cp, x, y, bw, bh, chb in exist:
            if cp in ascii_box:
                nx, ny, nw, nh = ascii_box[cp]
                w.writerow([cp, chb.decode('latin1'), 'EXIST', nx, ny, nw, nh,
                            'ascii', '', '', '', '', '', 0])
            else:
                w.writerow([cp, chb.decode('latin1'), 'EXIST', x, y, bw, bh,
                            'exist', '', '', '', '', '', 0])
        for row in layout:
            if row[7] == 'ascii':
                continue
            w.writerow(list(row[:13]) + [1])
    print('[输出] %s（%d 行 = 现有 %d[其中重渲染 ASCII %d] + 新增 %d）'
          % (p_layout, len(exist) + len(layout) - n_ascii, len(exist), n_ascii,
             len(layout) - n_ascii))

    # ---- 9. 报告 ----
    rep = os.path.join(OUT, 'g3_atlas_report.txt')
    with open(rep, 'w', encoding='utf-8') as f:
        f.write('Gate 3 T3 全量图集构建报告（20px @ 盒 19x25, SSAA=3）\n')
        f.write('=' * 60 + '\n')
        f.write('图集: %dx%d RGBA（左上 512x256=原版字节级复制；扩展区 x>=512）\n'
                % (NEW_W, NEW_H))
        f.write('CONFIG: FONT_SIZE=%d BOX=%dx%d PITCH=%dx%d GRAY=%d BASE_Y=%d\n'
                % (FONT_SIZE, BOX_W, BOX_H, pitch_x, PITCH_Y, TARGET_GRAY, BASE_Y))
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
        f.write('渲染规则: CJK/全角标点=基线对齐(BASE_Y=%d 墨底锚定); '
                'ASCII 同字体重渲染同基线\n' % BASE_Y)
        f.write('\n注意: 本图集由 D3D9 代理在运行时替换显存纹理; 代理缺位时游戏'
                '将渲染错乱（预期 FAIL 行为，属正常）\n')
        f.write('授权注记: 字体为寒蝉端黑体 Bold ChillDuanSans_Bold.otf（SIL OFL 1.1，'
                '可随补丁再分发）；替代掉 Gate 2 时期的 msyh.ttc（微软雅黑, 不可分发）\n')
    print('[输出] %s' % rep)
    print('\n★ T3 完成: 图集 %dx%d, 全量字形 %d, 槽位余 %d'
          % (NEW_W, NEW_H, len(exist) + len(layout), cap - slot))
    return 0


if __name__ == '__main__':
    sys.exit(main())

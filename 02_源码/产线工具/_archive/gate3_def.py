# -*- coding: utf-8 -*-
"""gate3_def.py — T4: 生成全量字体定义文件（2305 字形, atlas 4096x2048）

结构（Gate 2 实证协议的全量化应用）:
  头部 32B: f0=ng+1, f1=ntok+1, f2=ASCII区字节数, magic@0x0C,
            ng(u16)@0x12, hdr[0x1C]=0xE545A0C5 常量
  条目表: ent[0]=(0,0,3,0,T_NORM) 头部3token; ent[k]=(0,0,6,3+6*(k-1),t)
          ent[1..155] 原版逐字节保留（盒不变）; ent[156..2305] 新增
          末条目 ent[2305].t=T_LAST=0x5E237E06（标记由原 ent[155] 移交）
  驻留表: pair[i]=(token i 偏移, tag); tag: [0]=NAME, [1]=ATLAS_W,
          [2..n-2]=CYCLE[(i-2)%6], [n-1]=0（位置性终止, 指向最后 token）
  ASCII 区: token0=name, token1=atlas_w(4096), token2=atlas_h(2048),
          然后 2305 条字形记录 [cp][x][y][w][h][char(UTF-8)] + 6B 尾零
  文件 = head + entries + pairs + 4B零 + asc

关键不变量（与原版/Gate 2 一致）:
  - ent[k].tokoff == 3+6*(k-1); pair[i].off == token i 实际字节偏移
  - 现有 155 字形 token 逐字节保留（含那些 char token 与 cp 不符的历史 glyph）
  - f0=ng+1, f1=ntok+1, f2=len(zone)

输入:
  recon/x_data/unk_folder_1920272591/unk_file_3530817756.dat  原版 def
  recon/gate3/g3_layout.tsv        T3 布局（155 现有 + 2150 新增）
  recon/gate3/g3_atlas.png         T3 图集（取其 IHDR 尺寸交叉验证）

输出:
  g3_font_nonserif12.xmc   全量字体 def
  g3_def_report.txt        构建+自验证报告
"""
import struct, os, sys, csv, zlib

RECON = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONT0 = os.path.join(RECON, 'x_data', 'unk_folder_1920272591', 'unk_file_3530817756.dat')
LAYOUT = os.path.join(RECON, 'gate3', 'g3_layout.tsv')
ATLAS_PNG = os.path.join(RECON, 'gate3', 'g3_atlas.png')
OUT = RECON + r'\gate3'

TAG_NAME = 0x44A4A6F9
TAG_ATLAS_W = 0x9A352C0D
T_NORM = 0x8CFE579F
T_LAST = 0x5E237E06
CYCLE = [0x77153098, 0x8CDC1683, 0xFBDB2615, 0x1C630B12, 0x916B06E7, 0x0BB5AC54]
HDR_CONST = 0xE545A0C5

SIZE0 = 12684          # 原版 def 大小
NG0 = 156              # 原版条目数（= 155 glyph + 1 头部条目）
NTOK0 = 933            # 原版 token 数（3 + 6*155）
F00, F10, F20 = 157, 934, 2688
ASC0 = SIZE0 - F20     # 0x270C


def parse_font(d):
    f0, f1, f2 = struct.unpack_from('<III', d, 0)
    ng = struct.unpack_from('<H', d, 0x12)[0]
    asc = len(d) - f2
    ents = [struct.unpack_from('<IHHII', d, 0x20 + 16 * k) for k in range(ng)]
    pairs = []
    q = 0x20 + 16 * ng
    while q + 8 <= asc:
        off, tag = struct.unpack_from('<II', d, q)
        pairs.append((off, tag))
        if tag == 0:
            break
        q += 8
    toks = []
    i = asc
    while i < len(d):
        j = d.find(b'\x00', i)
        if j < 0:
            toks.append(d[i:]); break
        toks.append(d[i:j]); i = j + 1
    toks = toks[:3 + 6 * (ng - 1)]
    return f0, f1, f2, ng, asc, ents, pairs, toks


def png_size(path):
    with open(path, 'rb') as f:
        sig = f.read(8)
        assert sig == b'\x89PNG\r\n\x1a\n', 'not png'
        f.read(4)
        assert f.read(4) == b'IHDR'
        w, h = struct.unpack('>II', f.read(8))
    return w, h


def main():
    print('=' * 78)
    print('T4: 全量字体 def 生成')
    print('=' * 78)
    d0 = open(FONT0, 'rb').read()
    f0, f1, f2, ng, asc, ents, pairs, toks = parse_font(d0)
    print('[原版] size=%d f0=%d f1=%d f2=%d ng=%d asc=0x%X ents=%d pairs=%d toks=%d'
          % (len(d0), f0, f1, f2, ng, asc, len(ents), len(pairs), len(toks)))
    assert (f0, f1, f2, ng, len(d0)) == (F00, F10, F20, NG0, SIZE0)
    assert len(ents) == NG0 and len(pairs) == NTOK0 and len(toks) == NTOK0
    # 原版自洽性
    acc = 0
    exp_offs = []
    for t in toks:
        exp_offs.append(acc); acc += len(t) + 1
    assert [p[0] for p in pairs] == exp_offs
    assert ents[0][2] == 3 and ents[0][3] == 0
    assert all(e[2] == 6 and e[3] == 3 + 6 * (i - 1)
               for i, e in enumerate(ents) if i >= 1)
    assert ents[-1][4] == T_LAST and all(e[4] == T_NORM for e in ents[:-1])
    assert struct.unpack_from('<I', d0, 0x1C)[0] == HDR_CONST
    assert pairs[0][1] == TAG_NAME and pairs[1][1] == TAG_ATLAS_W
    assert all(pairs[i][1] == CYCLE[(i - 2) % 6] for i in range(2, NTOK0 - 1))
    assert pairs[NTOK0 - 1][1] == 0
    assert asc - (0x20 + 16 * NG0 + 8 * NTOK0) == 4
    assert d0[asc - 4:asc] == b'\x00' * 4
    print('[原版] 自洽性全部通过（条目/驻留/tag 方案/尾部结构）')

    # ---- 图集尺寸（从 PNG IHDR 交叉验证）----
    aw_new, ah_new = png_size(ATLAS_PNG)
    print('[图集] g3_atlas.png = %dx%d' % (aw_new, ah_new))

    # ---- 布局清单 ----
    exist_rows, new_rows = [], []
    with open(LAYOUT, encoding='utf-8', newline='') as f:
        r = csv.reader(f, delimiter='\t'); next(r)
        for row in r:
            cp = int(row[0]); x, y, w, h = int(row[3]), int(row[4]), int(row[5]), int(row[6])
            if row[13] == '1':
                new_rows.append((cp, x, y, w, h, row[1]))
            else:
                exist_rows.append((cp, x, y, w, h, row[1]))
    print('[布局] 现有 %d + 新增 %d' % (len(exist_rows), len(new_rows)))
    assert len(exist_rows) == 155 and len(new_rows) == 2150
    # 现有盒必须与原版 token 完全一致
    for k, (cp, x, y, w, h, ch) in enumerate(exist_rows):
        p = 3 + 6 * k
        assert (int(toks[p]), int(toks[p + 1]), int(toks[p + 2]),
                int(toks[p + 3]), int(toks[p + 4])) == (cp, x, y, w, h), \
            '现有字形 %d 盒与布局不符' % k
    print('[布局] 现有 155 字形盒与原版 token 逐项一致')
    # 新盒边界检查
    for cp, x, y, w, h, ch in new_rows:
        assert x >= 512 and x + w <= aw_new and y + h <= ah_new, \
            '新字形 cp=%d 盒越界 (%d,%d,%d,%d)' % (cp, x, y, w, h)
    print('[布局] 新增 2150 盒全部位于扩展区且不越界')

    # ---- 组装 token 流 ----
    # 0..932 原样; token1/2 改图集尺寸; 933.. 追加 2150 条记录
    new_toks = [bytes(t) for t in toks]
    new_toks[1] = str(aw_new).encode()
    new_toks[2] = str(ah_new).encode()
    for cp, x, y, w, h, ch in new_rows:
        new_toks += [str(cp).encode(), str(x).encode(), str(y).encode(),
                     str(w).encode(), str(h).encode(), chr(cp).encode('utf-8')]
    ntok = len(new_toks)
    nglyph = ntok - 3 // 6 - 3 // 6  # placeholder, 下面正经算
    n_records = (ntok - 3) // 6
    ng_new = n_records + 1          # 条目数 = 记录数 + 1（头部条目）
    print('[token] %d -> %d（+%d）; 字形记录 155 -> %d; 条目数 ng %d -> %d'
          % (NTOK0, ntok, ntok - NTOK0, n_records, NG0, ng_new))
    assert n_records == 2305 and ng_new == 2306

    zone = bytearray()
    offs = []
    for t in new_toks:
        offs.append(len(zone))
        zone += t + b'\x00'
    zone += b'\x00' * 6
    f2_new = len(zone)
    print('[ASCII 区] %d -> %d B' % (f2, f2_new))

    # ---- 驻留表 ----
    new_pairs = bytearray()
    for i, o in enumerate(offs):
        if i == 0:
            tag = TAG_NAME
        elif i == 1:
            tag = TAG_ATLAS_W
        elif i == ntok - 1:
            tag = 0
        else:
            tag = CYCLE[(i - 2) % 6]
        new_pairs += struct.pack('<II', o, tag)
    new_pairs += b'\x00' * 4
    f1_new = ntok + 1
    f0_new = ng_new + 1
    print('[驻留] %d -> %d 对; f0=%d f1=%d' % (NTOK0, ntok, f0_new, f1_new))

    # ---- 条目表 ----
    new_ets = bytearray(d0[0x20:0x20 + 16 * NG0])
    struct.pack_into('<I', new_ets, 16 * 155 + 12, T_NORM)   # 末条目标记移交
    for j in range(len(new_rows)):
        k = 156 + j
        tokoff = NTOK0 + 6 * j
        t = T_LAST if k == ng_new - 1 else T_NORM
        new_ets += struct.pack('<IHHII', 0, 0, 6, tokoff, t)
    assert len(new_ets) == 16 * ng_new

    # ---- 头部 ----
    head = bytearray(d0[:0x20])
    struct.pack_into('<I', head, 0, f0_new)
    struct.pack_into('<I', head, 4, f1_new)
    struct.pack_into('<I', head, 8, f2_new)
    struct.pack_into('<H', head, 0x12, ng_new)

    new_font = bytes(head) + bytes(new_ets) + bytes(new_pairs) + bytes(zone)
    print('[文件] %d -> %d B' % (len(d0), len(new_font)))
    p_out = os.path.join(OUT, 'g3_font_nonserif12.xmc')
    open(p_out, 'wb').write(new_font)

    # ================= 自验证 =================
    print()
    print('=' * 78)
    print('自验证（重新解析生成文件）')
    print('=' * 78)
    ok = True
    d2 = open(p_out, 'rb').read()
    f0b, f1b, f2b, ngb, ascb, entsb, pairsb, toksb = parse_font(d2)
    print('[计数] f0=%d(须%d) f1=%d(须%d) f2=%d ng=%d(须%d) ents=%d pairs=%d toks=%d'
          % (f0b, f0_new, f1b, f1_new, f2b, ngb, ng_new,
             len(entsb), len(pairsb), len(toksb)))
    ok &= (f0b, f1b, f2b, ngb) == (f0_new, f1_new, f2_new, ng_new)
    ok &= len(entsb) == ng_new and len(pairsb) == ntok and len(toksb) == ntok
    # 头部常量与 magic 保留（0x0C..0x20 = magic + 0 + ng + flags + const）
    hdr_expect = (d0[0x0C:0x12] + struct.pack('<H', ng_new)
                  + d0[0x14:0x20])
    hdr_ok = d2[0x0C:0x20] == hdr_expect
    print('[头部] 0x0C..0x20 逐字节符合预期(magic/ng/flags/const): %s' % hdr_ok)
    ok &= struct.unpack_from('<I', d2, 0x1C)[0] == HDR_CONST and hdr_ok
    print('[头部] 0x1C 常量保留: %s ; magic/flags/0x14-0x1B 保留: %s'
          % (struct.unpack_from('<I', d2, 0x1C)[0] == HDR_CONST,
             d2[0x0C:0x12] == d0[0x0C:0x12] and d2[0x14:0x1C] == d0[0x14:0x1C]))
    # 条目表
    same_155 = d2[0x20:0x20 + 16 * 155] == new_ets[:16 * 155]
    print('[条目] ent[0..154] 逐字节一致: %s ; ent[155].t=0x%08X(须 0x8CFE579F)'
          % (same_155, entsb[155][4]))
    ok &= same_155 and entsb[155][4] == T_NORM
    print('[条目] ent[2305].t=0x%08X(须 0x5E237E06 末条目标记)' % entsb[2305][4])
    ok &= entsb[2305][4] == T_LAST
    bad = 0
    for j in range(len(new_rows)):
        e = entsb[156 + j]
        if not (e[0] == 0 and e[1] == 0 and e[2] == 6 and e[3] == NTOK0 + 6 * j
                and e[4] == (T_LAST if 156 + j == 2305 else T_NORM)):
            bad += 1
    print('[条目] 新增 2150 条格式校验: %s' % ('OK' if bad == 0 else '%d 条异常' % bad))
    ok &= bad == 0
    # 驻留表
    exp_offs, acc = [], 0
    for t in toksb:
        exp_offs.append(acc); acc += len(t) + 1
    off_ok = [p[0] for p in pairsb] == exp_offs
    tag_ok = (pairsb[0][1] == TAG_NAME and pairsb[1][1] == TAG_ATLAS_W
              and all(pairsb[i][1] == CYCLE[(i - 2) % 6]
                      for i in range(2, ntok - 1))
              and pairsb[ntok - 1][1] == 0)
    print('[驻留] off==token 偏移: %s ; tag 方案: %s ; 终止对=(%d, 0) 指最后 token'
          % (off_ok, tag_ok, pairsb[ntok - 1][0]))
    ok &= off_ok and tag_ok
    ok &= pairsb[ntok - 1][0] == offs[ntok - 1]
    # 尾部
    tail_ok = (d2[0x20 + 16 * ng_new + 8 * ntok: ascb] == b'\x00' * 4
               and ascb == len(d2) - f2b)
    print('[尾部] RT_end+4B零+asc: %s ; 尾零 6B: %s'
          % (tail_ok, d2[-6:] == b'\x00' * 6))
    ok &= tail_ok and d2[-6:] == b'\x00' * 6
    # token 内容（token1/2 为图集尺寸, 故意修改; 其余须逐字节一致）
    same_932 = all(bytes(new_toks[i]) == bytes(toks[i]) for i in range(NTOK0)
                   if i not in (1, 2))
    print('[token] 现有 931 个内容一致(除尺寸 token1/2): %s ; token1/2 = %r/%r'
          '(须 b\'4096\'/b\'2048\')' % (same_932, toksb[1], toksb[2]))
    ok &= same_932 and toksb[1] == b'4096' and toksb[2] == b'2048'
    # 新字形记录回读
    bad2 = 0
    for j, (cp, x, y, w, h, ch) in enumerate(new_rows):
        p = NTOK0 + 6 * j
        g = (int(toksb[p]), int(toksb[p + 1]), int(toksb[p + 2]),
             int(toksb[p + 3]), int(toksb[p + 4]), toksb[p + 5])
        if g != (cp, x, y, w, h, chr(cp).encode('utf-8')):
            bad2 += 1
            if bad2 <= 3:
                print('  !! 记录 %d: %s != (%d,%d,%d,%d,%d,%r)'
                      % (j, g, cp, x, y, w, h, chr(cp)))
    print('[token] 新增 2150 条记录回读一致: %s' % ('OK' if bad2 == 0 else '%d 条异常' % bad2))
    ok &= bad2 == 0
    # 与图集尺寸一致
    print('[图集] def atlas_w/h=%d/%d == PNG %dx%d: %s'
          % (int(toksb[1]), int(toksb[2]), aw_new, ah_new,
             int(toksb[1]) == aw_new and int(toksb[2]) == ah_new))
    ok &= int(toksb[1]) == aw_new and int(toksb[2]) == ah_new

    # ---- 报告 ----
    rep = os.path.join(OUT, 'g3_def_report.txt')
    with open(rep, 'w', encoding='utf-8') as f:
        f.write('Gate 3 T4 全量字体 def 构建报告\n')
        f.write('=' * 60 + '\n')
        f.write('输入: 原版 def %d B (ng=%d, 155 glyph)\n' % (len(d0), NG0))
        f.write('输出: %s %d B\n' % (os.path.basename(p_out), len(d2)))
        f.write('字形: %d 记录 (155 现有 + 2150 新增); 条目 ng=%d\n' % (n_records, ng_new))
        f.write('图集: %dx%d (def token1/2 已更新)\n' % (aw_new, ah_new))
        f.write('token: %d -> %d; 驻留对: %d; f0/f1/f2 = %d/%d/%d\n'
                % (NTOK0, ntok, ntok, f0_new, f1_new, f2_new))
        f.write('结构改动（vs 原版）:\n')
        f.write('  1. token1/2: 512/256 -> %d/%d\n' % (aw_new, ah_new))
        f.write('  2. ent[155].t 标记 0x5E237E06 -> 0x8CFE579F（移交 ent[2305]）\n')
        f.write('  3. 条目表 +2150 条; 驻留表 +2150 对; ASCII 区 +2150x6 token\n')
        f.write('  4. 现有 155 字形条目/token 逐字节保留（盒不变）\n')
        f.write('自验证: %s\n' % ('全部通过' if ok else '存在问题'))
    print('[输出] %s' % rep)
    print()
    print('★ T4 %s: %s (%d B)' % ('完成' if ok else '失败', p_out, len(d2)))
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())

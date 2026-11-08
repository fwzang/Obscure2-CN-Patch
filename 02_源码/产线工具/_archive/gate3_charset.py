# -*- coding: utf-8 -*-
"""gate3_charset.py — T1 语料清点：定稿 Gate 3 全量字形集

输入:
  recon/o2_text_zh.tsv        中文译语料（3844 条，csv QUOTE_MINIMAL 写出的 TSV）
  recon/x_data/.../3530817756.dat  原版 nonserif12 字体 def（md5 4ba16736，155 字形）

输出:
  recon/gate3/g3_charset.tsv   新字形清单（cp / char / class / 来源计数）
  recon/gate3/g3_charset_report.txt  清点报告

分类规则:
  CJK    U+3400-4DBF(ExtA) / U+4E00-9FFF(基本区)
  PUNCT  U+3000-303F(CJK符号标点) / U+FF00-FFEF(全角形式) /
         U+2010-2027(通用标点: 引号/省略号/连接号等) / U+2030-205E
  OTHER  其余可见字符（拉丁/数字/符号）——须在现有 155 字形内，否则列为缺失
"""
import csv, os, struct, sys, unicodedata
from collections import Counter

RECON = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ZH_TSV = os.path.join(RECON, 'o2_text_zh.tsv')
FONT = os.path.join(RECON, 'x_data', 'unk_folder_1920272591', 'unk_file_3530817756.dat')
OUT_DIR = os.path.join(RECON, 'gate3')

CJK_RANGES = [(0x3400, 0x4DBF), (0x4E00, 0x9FFF), (0xF900, 0xFAFF)]
PUNCT_RANGES = [(0x2010, 0x2027), (0x2030, 0x205E), (0x3000, 0x303F), (0xFF00, 0xFFEF)]


def in_ranges(cp, ranges):
    return any(a <= cp <= b for a, b in ranges)


def classify(ch):
    cp = ord(ch)
    if in_ranges(cp, CJK_RANGES):
        return 'CJK'
    if in_ranges(cp, PUNCT_RANGES):
        return 'PUNCT'
    if cp < 0x80 and (ch.isalnum() or ch == ' '):
        return 'ASCII'
    if cp < 0x80:
        return 'ASCII_SYM'   # ASCII 标点/符号
    return 'OTHER'


def parse_font_cps(path):
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
    return ng, glyphs


def main():
    # ---- 1. 解析译语料 ----
    rows = []
    with open(ZH_TSV, encoding='utf-8', newline='') as f:
        r = csv.reader(f, delimiter='\t')
        hdr = next(r)
        for row in r:
            rows.append(row)
    print('[语料] 表头: %s' % hdr)
    print('[语料] 逻辑行数 = %d（期望 3844）' % len(rows))
    assert hdr[:8] == ['hdr', 'key', 'type', 'f1', 'f3', 'len', 'off', 'en'], hdr[:8]
    assert len(rows) == 3844, '语料行数不符'

    n_zh_empty = sum(1 for row in rows if len(row) < 9 or not row[8].strip())
    n_zh = sum(1 for row in rows if len(row) >= 9 and row[8].strip())
    print('[语料] 有译文 %d 条 / 空译文 %d 条（空译文=保留英文，含 47 条人工队列）' % (n_zh, n_zh_empty))

    # ---- 2. 现有 155 字形 ----
    ng, glyphs = parse_font_cps(FONT)
    exist_cps = set(g[0] for g in glyphs)
    print('[字体] 原版 def: ng=%d 现字形 cp 数=%d' % (ng, len(exist_cps)))

    # ---- 3. 译文字符清点 ----
    cnt = Counter()
    zh_only = Counter()
    for row in rows:
        zh = row[8] if len(row) >= 9 else ''
        for ch in zh:
            cnt[ch] += 1
            if classify(ch) in ('CJK', 'PUNCT'):
                zh_only[ch] += 1
    cjk = {ch: n for ch, n in cnt.items() if classify(ch) == 'CJK'}
    punct = {ch: n for ch, n in cnt.items() if classify(ch) == 'PUNCT'}
    print('[清点] 译文 distinct 字符 = %d' % len(cnt))
    print('  CJK   distinct = %d（期望 2129）' % len(cjk))
    print('  PUNCT distinct = %d（期望 16）' % len(punct))

    # ---- 4. 非 CJK/标点字符 vs 现有字形 ----
    # 控制字符(\n\r\t 等)不是字形: 换行由引擎排版处理, 跳过
    need_other, have_other, missing_other = {}, {}, {}
    for ch, n in cnt.items():
        cp = ord(ch)
        if cp < 0x20 or cp == 0x7F:
            continue
        cl = classify(ch)
        if cl in ('CJK', 'PUNCT'):
            continue
        if ord(ch) in exist_cps:
            have_other[ch] = n
        else:
            missing_other[ch] = n
    print('  OTHER: 现有字形覆盖 %d 种 / 缺失 %d 种' % (len(have_other), len(missing_other)))
    if missing_other:
        print('  !! 缺失的非 CJK 字符: %s' %
              ', '.join('%r(U+%04X)x%d' % (c, ord(c), n) for c, n in
                        sorted(missing_other.items(), key=lambda kv: -kv[1])[:40]))

    # ---- 5. 定稿新字形集 ----
    new_chars = {}
    for ch, n in cjk.items():
        new_chars[ch] = ('CJK', n)
    for ch, n in punct.items():
        if ord(ch) not in exist_cps:
            new_chars[ch] = ('PUNCT', n)
        else:
            print('  注: 标点 %r 已在现有 155 字形中，不新增' % ch)
    for ch, n in missing_other.items():
        new_chars[ch] = (classify(ch), n)
    total_new = len(new_chars)
    print('[定稿] 新字形 = %d（CJK %d + PUNCT %d + 缺失OTHER %d）' % (
        total_new, sum(1 for v in new_chars.values() if v[0] == 'CJK'),
        sum(1 for v in new_chars.values() if v[0] == 'PUNCT'),
        sum(1 for v in new_chars.values() if v[0] not in ('CJK', 'PUNCT'))))
    print('[定稿] 合计字形 = 155 + %d = %d' % (total_new, 155 + total_new))

    # ---- 6. 标点明细（人工核对用）----
    print('\n[标点明细] %d 种:' % len(punct))
    for ch, n in sorted(punct.items(), key=lambda kv: -kv[1]):
        cp = ord(ch)
        try:
            uname = unicodedata.name(ch)
        except ValueError:
            uname = '?'
        print('  U+%04X %r x%-5d %s  %s' % (cp, ch, n, uname[:38],
              '已在现有字形' if cp in exist_cps else '需新增'))

    # ---- 7. 输出清单 ----
    os.makedirs(OUT_DIR, exist_ok=True)
    out = os.path.join(OUT_DIR, 'g3_charset.tsv')
    with open(out, 'w', encoding='utf-8', newline='') as f:
        w = csv.writer(f, delimiter='\t')
        w.writerow(['cp', 'char', 'class', 'count', 'new'])
        for ch, (cl, n) in sorted(new_chars.items(), key=lambda kv: (kv[1][0], ord(kv[0]))):
            w.writerow([ord(ch), ch, cl, n, 1])
        # 现有 155 也全量列入（class=EXIST），供 def 生成使用
        for g in sorted(glyphs, key=lambda g: g[0]):
            cp = g[0]
            if chr(cp) not in new_chars:
                w.writerow([cp, repr(g[5].decode('latin1')), 'EXIST', '', 0])
    print('\n[输出] %s（新字形 %d 行 + 现有 %d 行）' % (out, total_new, ng))

    # ---- 8. 报告 ----
    rep = os.path.join(OUT_DIR, 'g3_charset_report.txt')
    with open(rep, 'w', encoding='utf-8') as f:
        f.write('Gate 3 T1 语料清点报告\n')
        f.write('=' * 60 + '\n')
        f.write('语料: %s (%d 条, 空译文 %d)\n' % (os.path.basename(ZH_TSV), len(rows), n_zh_empty))
        f.write('原版 def: ng=%d, 现字形 cp=%d\n' % (ng, len(exist_cps)))
        f.write('CJK distinct=%d, PUNCT distinct=%d, 缺失OTHER=%d\n' % (len(cjk), len(punct), len(missing_other)))
        f.write('新字形合计=%d, 全量字形=155+%d=%d\n' % (total_new, total_new, 155 + total_new))
        f.write('\n标点明细:\n')
        for ch, n in sorted(punct.items(), key=lambda kv: -kv[1]):
            f.write('  U+%04X %r x%d %s\n' % (ord(ch), ch, n,
                    '已在现有' if ord(ch) in exist_cps else '需新增'))
        if missing_other:
            f.write('\n缺失 OTHER（需新增字形）:\n')
            for ch, n in sorted(missing_other.items(), key=lambda kv: -kv[1]):
                f.write('  U+%04X %r x%d\n' % (ord(ch), ch, n))
    print('[输出] %s' % rep)
    return 0


if __name__ == '__main__':
    sys.exit(main())

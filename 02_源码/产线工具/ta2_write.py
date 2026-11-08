# -*- coding: utf-8 -*-
"""线程 A 第 2 步：二代文本容器回写器 ta2_write.py
==================================================
背景（第 1 步已实证）：
  - 容器 = [u32 LE h0=记录总数][u32 LE h1=16B头记录数] + 顺序记录流，无偏移表
  - 16B 头: [u32 BE key][u16 BE type][u16 LE f1][u32 LE 0][u32 LE len] + body
    8B  头: [u32 BE key][u32 LE len] + body
  - 长度变化只需 patch 各记录 len 字段（顺序解析自然重排），h0/h1 不随长度变化
  - 原版 3844 条 body 全部合法 UTF-8 且往返无损 → 字节级 no-op 守卫安全

用法：
  # 单文件模式（探针/单语种）
  python ta2_write.py --src <容器.dat> --zh <语料.tsv> --out <输出.dat> [--log <日志.tsv>]
  # 多语种模式（全量包：同一语料按索引应用到 5 个容器）
  python ta2_write.py --src-dir <x_data/unk_folder_3030018805> --zh <语料.tsv> \
      --out-dir <工作目录> --langs en,de,es,fr,it [--log <日志.tsv>]

安全设计：
  1. 只写 --out/--out-dir，绝不触碰游戏目录
  2. 逐记录保留原 header 字节，仅 patch len 字段（key/type/f1/零字段/头尺寸不动）
  3. 索引对齐断言：语料每行的 en 列必须能编码回原 body（否则报错退出）
  4. 新 body 安全校验：非空、无 NUL、无非常规控制字符、printable score > 0.95
  5. 自验证：重新解析输出，逐条核对 (头尺寸,key,type,f1,len,body) + 闭合性
"""
import os, sys, struct, csv, argparse, collections

CTRL = set([0x0a, 0x0d, 0x09])
LANG_FILES = {'en': 'unk_file_3866210045.dat', 'de': 'unk_file_1526549577.dat',
              'es': 'unk_file_3962463896.dat', 'fr': 'unk_file_3321210576.dat',
              'it': 'unk_file_3152273829.dat'}

def score(b):
    if not b: return 0.0
    good = sum(1 for c in b if 0x20 <= c <= 0xff or c in CTRL)
    return good / len(b)

def parse(raw):
    """顺序解析容器 → (h0, h1, recs, end, n, sizes)
    recs[i] = (hs, off, key, type, f1, L, header_bytes, body_bytes)"""
    n = len(raw)
    h0 = struct.unpack_from('<I', raw, 0)[0]
    h1 = struct.unpack_from('<I', raw, 4)[0]
    p = 8
    recs = []
    sizes = collections.Counter()
    while p + 8 <= n:
        L = struct.unpack_from('<I', raw, p + 12)[0]
        if p + 16 + L <= n and L > 0 and score(raw[p + 16:p + 16 + L]) > 0.95 \
                and b'\x00' not in raw[p + 16:p + 16 + L]:
            hs = 16
        else:
            L = struct.unpack_from('<I', raw, p + 4)[0]
            if not (p + 8 + L <= n and L > 0 and score(raw[p + 8:p + 8 + L]) > 0.95
                    and b'\x00' not in raw[p + 8:p + 8 + L]):
                raise ValueError('解析失败 @0x%X（容器损坏或格式异常）' % p)
            hs = 8
        sizes[hs] += 1
        if hs == 16:
            key = struct.unpack_from('>I', raw, p)[0]
            typ = struct.unpack_from('>H', raw, p + 4)[0]
            f1 = struct.unpack_from('<H', raw, p + 6)[0]
            hdr = raw[p:p + 16]
            body = raw[p + 16:p + 16 + L]
        else:
            key = struct.unpack_from('>I', raw, p)[0]
            typ = f1 = None
            hdr = raw[p:p + 8]
            body = raw[p + 8:p + 8 + L]
        recs.append((hs, p, key, typ, f1, L, hdr, body))
        p += hs + L
    return h0, h1, recs, p, n, sizes

def load_zh(path):
    """读语料 TSV → [(idx, key, off, en, zh), ...]（按行序即记录索引）"""
    rows = []
    with open(path, encoding='utf-8', newline='') as f:
        rd = csv.reader(f, delimiter='\t')
        hdr = next(rd)
        # 兼容 8 列(en TSV: ...off,text) 与 9 列(zh TSV: ...off,en,zh)
        for row in rd:
            if len(row) >= 9:
                rows.append((int(row[1]), row[6], row[7], row[8]))
            elif len(row) == 8:
                rows.append((int(row[1]), row[6], row[7], ''))
    return rows

def body_safe(b):
    """新 body 必须满足与解析器相同的可解析性约束"""
    if not b: return 'empty'
    if b'\x00' in b: return 'NUL'
    if any((c < 0x20 and c not in CTRL) or c == 0x7f for c in b): return 'ctrl'
    if score(b) <= 0.95: return 'score'
    return None

def write_container(src_path, zh_path, out_path, log_path=None, tag='', lang=None):
    """lang: 'en' 时执行 off+en 列全量对齐断言；其他语种仅断言 key 序列
    （TSV 的 off/en 列由 en 容器生成，对其他语种不适用——已实证五语种 key 序列一致）"""
    raw = open(src_path, 'rb').read()
    h0, h1, recs, end, n, sizes = parse(raw)
    if end != n:
        print('  ✗ %s 原版容器解析不闭合（end=0x%X n=0x%X）' % (tag, end, n))
        return False
    zh_rows = load_zh(zh_path)

    # ---- 索引对齐断言 ----
    if len(zh_rows) != len(recs):
        print('  ✗ %s 语料行数 %d != 容器记录数 %d（索引不对齐，语料可能生成自不同容器）'
              % (tag, len(zh_rows), len(recs)))
        return False
    if lang is None:
        # 单文件模式自动判定：首行 en 列是否编码回首条 body
        lang = 'en' if (zh_rows and zh_rows[0][2].encode('utf-8') == recs[0][7]) else 'other'
        print('  (%s 自动判定语种模式: %s)' % (tag, lang))
    full_check = (lang == 'en')
    for i, (key, off, en, zh) in enumerate(zh_rows):
        hs, poff, rkey, typ, f1, L, hdr, body = recs[i]
        if key != rkey:
            print('  ✗ %s 第 %d 行 key 与容器不符（语料与容器不同源）' % (tag, i))
            return False
        if full_check:
            if int(off, 16) != poff:
                print('  ✗ %s 第 %d 行 off 与容器不符（语料与容器不同源）' % (tag, i))
                return False
            if en.encode('utf-8') != body:
                print('  ✗ %s 第 %d 行 en 列编码后与原 body 不一致（语料与容器不同源）' % (tag, i))
                return False

    # ---- 逐记录决策 + 重建 ----
    out = bytearray(raw[0:8])          # h0/h1 原样保留（计数不随长度变化）
    changed, identical, kept = [], 0, 0
    old_text_bytes = new_text_bytes = 0
    expected = []                      # (hs, key, typ, f1, newbody) 供自验证
    for i, (key, off, en, zh) in enumerate(zh_rows):
        hs, poff, rkey, typ, f1, L, hdr, body = recs[i]
        old_text_bytes += L
        newbody = body
        if zh.strip() == '':
            kept += 1                   # 人工队列/B 类：保留英文
        else:
            nb = zh.encode('utf-8')
            if nb == body:
                identical += 1          # 译文与英文相同（no-op）
            else:
                bad = body_safe(nb)
                if bad:
                    print('  ✗ %s 第 %d 行新 body 安全校验失败(%s)，已保留英文' % (tag, i, bad))
                    kept += 1
                else:
                    newbody = nb
                    changed.append((i, poff, rkey, L, len(nb), en, zh))
        new_text_bytes += len(newbody)
        expected.append((hs, rkey, typ, f1, newbody))
        # header：原字节仅 patch len 字段
        if hs == 16:
            nh = bytearray(hdr); struct.pack_into('<I', nh, 12, len(newbody))
        else:
            nh = bytearray(hdr); struct.pack_into('<I', nh, 4, len(newbody))
        out += nh + newbody

    # ---- 自验证：重新解析输出，与预期逐条核对 ----
    try:
        h0b, h1b, recsb, endb, nb_, sizesb = parse(bytes(out))
    except ValueError as e:
        print('  ✗ %s 输出重新解析失败: %s' % (tag, e))
        return False
    ok = (endb == nb_ and len(recsb) == len(expected) and h0b == h0 and h1b == h1)
    for i in range(len(expected)):
        e_hs, e_key, e_typ, e_f1, e_body = expected[i]
        b = recsb[i]
        if b[0] != e_hs or b[2] != e_key or b[3] != e_typ or b[4] != e_f1 or b[7] != e_body:
            ok = False
            print('  ✗ %s 自验证第 %d 条不一致: 预期(hs=%s key=0x%X len=%d) 实际(hs=%s key=0x%X len=%d)'
                  % (tag, i, e_hs, e_key, len(e_body), b[0], b[2], b[6]))
            break
    if not ok:
        print('  ✗ %s 自验证失败' % tag)
        return False

    with open(out_path, 'wb') as f:
        f.write(out)
    print('  ✓ %s 写入 %s（%d B，原 %d B，%+d B）' % (tag, os.path.basename(out_path), len(out), n, len(out) - n))
    print('     改写=%d 译文同英文(no-op)=%d 保留英文=%d；正文 %d→%d B（%+d）'
          % (len(changed), identical, kept, old_text_bytes, new_text_bytes,
             new_text_bytes - old_text_bytes))
    print('     自验证: 重解析闭合=%s 记录数=%d(h0=%d h1=%d) 逐条一致=True'
          % (endb == nb_, len(recsb), h0b, h1b))

    if log_path and changed:
        with open(log_path, 'w', encoding='utf-8', newline='') as f:
            w = csv.writer(f, delimiter='\t')
            w.writerow(['idx', 'off', 'key', 'oldlen', 'newlen', 'delta', 'en', 'zh'])
            for i, poff, rkey, oL, nL, en, zh in changed:
                w.writerow([i, hex(poff), rkey, oL, nL, nL - oL, en, zh])
        print('     改写日志: %s（%d 行）' % (log_path, len(changed)))
    return True

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--src', help='单文件模式：原版容器 .dat')
    ap.add_argument('--zh', required=True, help='语料 TSV（9 列 schema）')
    ap.add_argument('--out', help='单文件模式：输出 .dat')
    ap.add_argument('--src-dir', help='多语种模式：x_data/unk_folder_3030018805')
    ap.add_argument('--out-dir', help='多语种模式：输出目录')
    ap.add_argument('--langs', default='en', help='逗号分隔语种（多语种模式）')
    ap.add_argument('--log', help='改写日志 TSV 路径')
    ap.add_argument('--log-suffix', default='', help='日志文件名后缀（区分语种）')
    args = ap.parse_args()

    ok_all = True
    if args.src:
        if not args.out:
            print('单文件模式需要 --out'); sys.exit(2)
        # 单文件模式：按首行 en 列是否匹配自动判定是否 en 容器
        ok_all &= write_container(args.src, args.zh, args.out, args.log, tag='', lang=None)
    elif args.src_dir:
        if not args.out_dir:
            print('多语种模式需要 --out-dir'); sys.exit(2)
        os.makedirs(args.out_dir, exist_ok=True)
        for lg in [x.strip() for x in args.langs.split(',') if x.strip()]:
            fn = LANG_FILES.get(lg)
            if not fn:
                print('未知语种: %s' % lg); ok_all = False; continue
            src = os.path.join(args.src_dir, fn)
            dst = os.path.join(args.out_dir, fn)
            log = None
            if args.log:
                base, ext = os.path.splitext(args.log)
                log = '%s_%s%s' % (base, lg, ext)
            ok_all &= write_container(src, args.zh, dst, log, tag='[%s]' % lg, lang=lg)
    else:
        print('需要 --src 或 --src-dir'); sys.exit(2)
    print()
    print('★ 回写完成' if ok_all else '✗ 回写失败')
    sys.exit(0 if ok_all else 1)

if __name__ == '__main__':
    main()

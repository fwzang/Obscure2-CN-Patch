# -*- coding: utf-8 -*-
"""make_delta.py — 生成 原版 datapack.hvp -> 汉化 datapack.hvp 的二进制差分补丁。

算法：单遍线性扫描 + 位移跟踪（copy / add 两种 op）
  * 对齐时用 1MB 块指数扩展，找到最长相同段 → COPY(srcOff, len)
  * 失配时在 ±1MB 窗口内用 mmap.find 重新定位锚点（处理插入/删除造成的整体位移）
  * 连续失配超过阈值则改用全局 find，避免"一处大改导致后面全变字面量"
  * 新内容 → ADD(literal)

输出 datapack.delta:
  Header(40B): magic[8]="O2DLT1\0\0" ver:u32 opCount:u32 srcSize:u64 dstSize:u64 srcCrc:u32 dstCrc:u32
  Op: ctrl:u32 = (len<<1)|0 → COPY + u64 srcOff
               = (len<<1)|1 → ADD  + len 字节
"""
import mmap
import os
import struct
import sys
import time
import zlib

SRC = r'D:\SteamLibrary\steamapps\common\Obscure2\Obscure2_Handover\基线_原版\datapack.hvp.gate3_orig'
DST = r'D:\SteamLibrary\steamapps\common\Obscure2\Obscure2_Handover\deploy\datapack_zh_full18.hvp'
OUT = r'D:\SteamLibrary\steamapps\common\Obscure2\Obscure2_Handover\deploy\datapack.delta'

if len(sys.argv) >= 4:          # 可选：python make_delta.py <src> <dst> <out>
    SRC, DST, OUT = sys.argv[1], sys.argv[2], sys.argv[3]

MINK = 64          # 锚点键长
VERI = 1024        # 锚点验证长度
WIN = 1 << 20      # 初始搜索窗口 ±1MB
WIN_MAX = 32 << 20
LIT_SOFT = 2 << 20  # 字面量累计超过此值则放大窗口/全局搜索
STEP = 1 << 14      # 新内容区向前探测步长


def crc32_mmap(m):
    c = 0
    for o in range(0, len(m), 1 << 22):
        c = zlib.crc32(m[o:o + (1 << 22)], c)
    return c & 0xFFFFFFFF


def extend(ma, mb, a, b):
    """从 (a,b) 起的最长相同长度。"""
    lim = min(len(ma) - a, len(mb) - b)
    L = 0
    step = 1 << 20
    while L < lim:
        n = min(step, lim - L)
        if ma[a + L:a + L + n] == mb[b + L:b + L + n]:
            L += n
            if step < (4 << 20):
                step *= 2
        else:
            if n <= MINK:
                break
            step = max(MINK, n // 8)
    return L


def anchor(ma, mb, b, shift, win):
    """在 A 的 [b+shift-win, b+shift+win] 内寻找与 B[b:] 匹配的锚点，返回 A 偏移或 -1。"""
    sa, sb = len(ma), len(mb)
    if b + MINK > sb:
        return -1
    key = mb[b:b + MINK]
    a = b + shift
    if 0 <= a and a + VERI <= sa and ma[a:a + MINK] == key:
        return a
    lo = max(0, a - win)
    hi = min(sa, a + win + MINK)
    q = ma.find(key, lo, hi)
    while q >= 0:
        if q + VERI <= sa and b + VERI <= sb and ma[q:q + VERI] == mb[b:b + VERI]:
            return q
        q = ma.find(key, q + 1, hi)
    return -1


def build():
    fa = open(SRC, 'rb'); fb = open(DST, 'rb')
    ma = mmap.mmap(fa.fileno(), 0, access=mmap.ACCESS_READ)
    mb = mmap.mmap(fb.fileno(), 0, access=mmap.ACCESS_READ)
    sa, sb = len(ma), len(mb)
    print('src=%d dst=%d delta=%+d' % (sa, sb, sb - sa))

    t0 = time.time()
    src_crc = crc32_mmap(ma)
    dst_crc = crc32_mmap(mb)
    print('crc32 src=%08X dst=%08X  (%.1fs)' % (src_crc, dst_crc, time.time() - t0))

    ops = []          # (0, srcOff, len) / (1, bytes, len)
    pos = 0
    shift = 0
    lit_start = 0
    win = WIN
    ncopy = nadd = 0
    copy_bytes = add_bytes = 0

    while pos < sb:
        q = anchor(ma, mb, pos, shift, win)
        if q >= 0:
            shift = q - pos
            L = extend(ma, mb, q, pos)
            if pos > lit_start:
                lit = mb[lit_start:pos]
                ops.append((1, lit, len(lit)))
                nadd += 1; add_bytes += len(lit)
            ops.append((0, q, L))
            ncopy += 1; copy_bytes += L
            pos += L
            lit_start = pos
            win = WIN
            continue

        # 新内容区：向前探测下一个锚点
        k = pos + STEP
        found = -1
        while k < sb:
            kk = min(k, sb - MINK)
            q2 = anchor(ma, mb, kk, shift, win)
            if q2 >= 0:
                found = kk
                break
            k += STEP
            if k - pos > LIT_SOFT and win < WIN_MAX:
                win = min(win * 4, WIN_MAX)
                print('  [widen] win=%dMB at 0x%08X' % (win >> 20, pos))
        if found < 0:
            lit = mb[lit_start:sb]
            ops.append((1, lit, len(lit)))
            nadd += 1; add_bytes += len(lit)
            lit_start = sb
            pos = sb
            break
        pos = found

    if lit_start < sb:
        lit = mb[lit_start:sb]
        ops.append((1, lit, len(lit)))
        nadd += 1; add_bytes += len(lit)

    print('ops: copy=%d (%d B, %.2f%%)  add=%d (%d B, %.3f%%)  %.1fs'
          % (ncopy, copy_bytes, 100.0 * copy_bytes / sb, nadd, add_bytes,
             100.0 * add_bytes / sb, time.time() - t0))
    # 覆盖校验
    assert copy_bytes + add_bytes == sb, (copy_bytes, add_bytes, sb)

    hdr = b'O2DLT1\x00\x00' + struct.pack('<IIQQII', 1, len(ops), sa, sb, src_crc, dst_crc)
    assert len(hdr) == 40
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'wb') as f:
        f.write(hdr)
        for op in ops:
            if op[0] == 0:
                f.write(struct.pack('<IQ', (op[2] << 1) | 0, op[1]))
            else:
                f.write(struct.pack('<I', (op[2] << 1) | 1))
                f.write(op[1])
    sz = os.path.getsize(OUT)
    print('delta = %s  %.2f MB (%d B)' % (OUT, sz / 1048576.0, sz))
    ma.close(); mb.close(); fa.close(); fb.close()
    return 0


if __name__ == '__main__':
    sys.exit(build())

# -*- coding: utf-8 -*-
"""apply_delta_check.py — 用 apply_delta.py 的同一套 op 逻辑，校验新差分可 100% 重建目标包。
用法：python apply_delta_check.py [fullNN]  （默认 full18）"""
import hashlib, mmap, os, struct, sys, zlib

ROOT = r'D:\SteamLibrary\steamapps\common\Obscure2\Obscure2_Handover'
FULL = sys.argv[1] if len(sys.argv) > 1 else 'full18'
SRC = os.path.join(ROOT, r'基线_原版\datapack.hvp.gate3_orig')
DLT = os.path.join(ROOT, r'deploy\datapack.delta')
REF = os.path.join(ROOT, r'deploy\datapack_zh_%s.hvp' % FULL)
OUT = os.path.join(ROOT, r'_verify\rebuilt_%s.hvp' % FULL)

p = open(DLT, 'rb').read()
magic, ver, nops, ssz, dsz, scrc, dcrc = struct.unpack('<8sIIQQII', p[:40])
assert magic == b'O2DLT1\x00\x00' and ver == 1
print('ops=%d src=%d dst=%d srcCrc=%08X dstCrc=%08X' % (nops, ssz, dsz, scrc, dcrc))

fs = open(SRC, 'rb'); ms = mmap.mmap(fs.fileno(), 0, access=mmap.ACCESS_READ)
assert len(ms) == ssz, 'src size mismatch'
c = 0
for o in range(0, len(ms), 1 << 22):
    c = zlib.crc32(ms[o:o + (1 << 22)], c)
assert (c & 0xFFFFFFFF) == scrc, 'src crc mismatch'
print('src crc OK (基线原版包)')

off = 40
out = open(OUT, 'wb')
ocrc = 0
written = 0
for i in range(nops):
    ctrl, = struct.unpack('<I', p[off:off + 4]); off += 4
    L = ctrl >> 1
    if ctrl & 1:
        data = p[off:off + L]; off += L
    else:
        so, = struct.unpack('<Q', p[off:off + 8]); off += 8
        data = ms[so:so + L]
    out.write(data)
    ocrc = zlib.crc32(data, ocrc)
    written += len(data)
out.close()
ocrc &= 0xFFFFFFFF
print('written=%d  crc=%08X  (expect %08X)' % (written, ocrc, dcrc))
assert written == dsz and ocrc == dcrc, 'REBUILD MISMATCH'

m1 = hashlib.md5(open(OUT, 'rb').read()).hexdigest()
m2 = hashlib.md5(open(REF, 'rb').read()).hexdigest()
print('rebuilt md5 =', m1)
print('full17  md5 =', m2)
print('RESULT:', 'IDENTICAL OK' if m1 == m2 else 'DIFF FAIL')
ms.close(); fs.close()
sys.exit(0 if m1 == m2 else 1)

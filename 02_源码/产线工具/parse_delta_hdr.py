# -*- coding: utf-8 -*-
"""parse_delta_hdr.py — 解析 datapack.delta 头并列出候选原版 datapack.hvp。"""
import os
import struct

DELTA = r'D:\SteamLibrary\steamapps\common\Obscure2\Obscure2_Handover\deploy\datapack.delta'
ROOTS = [
    r'D:\SteamLibrary\steamapps\common\Obscure2',
    r'D:\SteamLibrary\steamapps\common\Obscure2\Obscure2_Handover',
    r'D:\SteamLibrary\steamapps\common\Obscure2\Obscure2_Handover\基线_原版',
    r'D:\SteamLibrary\steamapps\common\Obscure2\Obscure2_Handover\_work',
    r'D:\SteamLibrary\steamapps\common\Obscure2\Obscure2_Handover\release_v49_full17',
]


def main():
    d = open(DELTA, 'rb').read()
    magic, ver, nops, srcSize, dstSize, srcCrc, dstCrc = struct.unpack('<8sIIQQII', d[:40])
    print('delta hdr: ver={} nops={} srcSize={} dstSize={} srcCrc={:08x} dstCrc={:08x}'.format(
        ver, nops, srcSize, dstSize, srcCrc, dstCrc))
    print('')
    cands = []
    seen = set()
    for root in ROOTS:
        for dp, dn, fn in os.walk(root):
            for f in fn:
                if 'datapack' in f.lower() and f.lower().endswith('.hvp'):
                    p = os.path.join(dp, f)
                    if p in seen:
                        continue
                    seen.add(p)
                    try:
                        sz = os.path.getsize(p)
                    except OSError:
                        continue
                    cands.append((sz, p))
    for sz, p in sorted(cands):
        mark = ''
        if sz == srcSize:
            mark = '  <== SIZE==src'
        elif sz == dstSize:
            mark = '  <== SIZE==dst'
        print('{:>10}  {}{}'.format(sz, p, mark))


if __name__ == '__main__':
    main()

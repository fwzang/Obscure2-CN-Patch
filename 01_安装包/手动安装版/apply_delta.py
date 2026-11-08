# -*- coding: utf-8 -*-
"""apply_delta.py — 差分重建安装器（与图形安装器同一套 op 逻辑）

用法:
    python apply_delta.py --delta <delta文件> --game-dir <游戏目录> [--backup]

流程:
  1. 校验 delta 头 (magic=O2DLT1, ver=1)
  2. 校验游戏目录 datapack.hvp 的 size/crc 与 delta 记录的 src 完全一致
     （不一致即拒绝 —— 该机不是原版包，必须先"还原原版"）
  3. 先备份原版为 datapack.hvp.o2bak（已存在则不覆盖）
  4. 按 op 序列重建到临时文件，校验 size/crc
  5. 原子替换 datapack.hvp
"""
import argparse
import hashlib
import mmap
import os
import shutil
import struct
import sys
import tempfile
import zlib

MAGIC = b'O2DLT1\x00\x00'


def crc32_of(path):
    c = 0
    with open(path, 'rb') as f:
        mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
        for o in range(0, len(mm), 1 << 22):
            c = zlib.crc32(mm[o:o + (1 << 22)], c)
        mm.close()
    return c & 0xFFFFFFFF


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--delta', required=True)
    ap.add_argument('--game-dir', required=True)
    ap.add_argument('--no-backup', action='store_true')
    a = ap.parse_args()

    pack = os.path.join(a.game_dir, 'datapack.hvp')
    if not os.path.exists(pack):
        print('[ERROR] not found: %s' % pack)
        return 2

    p = open(a.delta, 'rb').read()
    if len(p) < 40:
        print('[ERROR] delta too small')
        return 2
    magic, ver, nops, ssz, dsz, scrc, dcrc = struct.unpack('<8sIIQQII', p[:40])
    if magic != MAGIC or ver != 1:
        print('[ERROR] bad delta header')
        return 2
    print('[DELTA] ops=%d src=%d dst=%d srcCrc=%08X dstCrc=%08X'
          % (nops, ssz, dsz, scrc, dcrc))

    size = os.path.getsize(pack)
    if size != ssz:
        print('[ERROR] game datapack.hvp size %d != delta src %d' % (size, ssz))
        print('        The game data pack is not the vanilla one.')
        print('        Restore vanilla first (Steam > Verify integrity), then retry.')
        return 3
    c = crc32_of(pack)
    if c != scrc:
        print('[ERROR] game datapack.hvp crc %08X != delta srcCrc %08X' % (c, scrc))
        print('        Restore vanilla first (Steam > Verify integrity), then retry.')
        return 3
    print('[OK] vanilla datapack verified (size + crc)')

    bak = os.path.join(a.game_dir, 'datapack.hvp.o2bak')
    if not a.no_backup and not os.path.exists(bak):
        shutil.copy2(pack, bak)
        print('[OK] backup written: %s' % bak)
    elif os.path.exists(bak):
        print('[..] backup already exists, keep it: %s' % bak)

    fd, tmp = tempfile.mkstemp(dir=a.game_dir, prefix='dp_rebuild_')
    os.close(fd)
    try:
        fs = open(pack, 'rb')
        ms = mmap.mmap(fs.fileno(), 0, access=mmap.ACCESS_READ)
        off = 40
        ocrc = 0
        written = 0
        with open(tmp, 'wb') as out:
            for i in range(nops):
                ctrl, = struct.unpack('<I', p[off:off + 4])
                off += 4
                L = ctrl >> 1
                if ctrl & 1:
                    data = p[off:off + L]
                    off += L
                else:
                    so, = struct.unpack('<Q', p[off:off + 8])
                    off += 8
                    data = ms[so:so + L]
                out.write(data)
                ocrc = zlib.crc32(data, ocrc)
                written += len(data)
        ocrc &= 0xFFFFFFFF
        ms.close()
        fs.close()
        if written != dsz or ocrc != dcrc:
            print('[ERROR] rebuild mismatch (size %d/%d crc %08X/%08X)'
                  % (written, dsz, ocrc, dcrc))
            return 4
        h = hashlib.md5(open(tmp, 'rb').read()).hexdigest()
        print('[OK] rebuilt %d B  md5=%s' % (written, h))
        shutil.move(tmp, pack)
        print('[OK] installed: %s' % pack)
        print('     d3d9.dll (proxy) must be copied separately.')
        return 0
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


if __name__ == '__main__':
    sys.exit(main())

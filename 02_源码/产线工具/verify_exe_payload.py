# -*- coding: utf-8 -*-
"""verify_exe_payload.py — 解析安装包 footer，逐一核对内嵌载荷 md5。

用法：python verify_exe_payload.py <安装包.exe>
期望值来源：D:\\Obscure2.zip（dinput8/main.patch）+ deploy\\datapack.delta + deploy\\d3d9_v49.dll
"""
import hashlib
import os
import struct
import sys
import zipfile

HERE = r'D:\SteamLibrary\steamapps\common\Obscure2\Obscure2_Handover'
ZIP = r'D:\Obscure2.zip'
MAGIC = b'O2SETUP1'


def md5b(b):
    return hashlib.md5(b).hexdigest()


def main():
    if len(sys.argv) < 2:
        print('usage: verify_exe_payload.py <exe>')
        return 2
    EXE = sys.argv[1]
    if not os.path.isabs(EXE):
        EXE = os.path.join(HERE, 'installer', EXE)

    with zipfile.ZipFile(ZIP) as z:
        exp = {
            'dinput8.dll': md5b(z.read('dinput8.dll')),
            'main.patch': md5b(z.read('patches/main.patch')),
        }
    with open(os.path.join(HERE, r'deploy\datapack.delta'), 'rb') as f:
        exp['datapack.delta'] = md5b(f.read())
    with open(os.path.join(HERE, r'deploy\d3d9_v49.dll'), 'rb') as f:
        exp['d3d9.dll'] = md5b(f.read())

    size = os.path.getsize(EXE)
    with open(EXE, 'rb') as f:
        f.seek(size - 400)
        footer = f.read(400)
    assert footer[:8] == MAGIC, 'magic 不符'
    ver, n = struct.unpack('<II', footer[8:16])
    print('%s: ver=%d entries=%d size=%d' % (os.path.basename(EXE), ver, n, size))
    ok = True
    for i in range(n):
        base = 16 + i * 48
        nm = footer[base:base + 32].split(b'\x00')[0].decode('ascii')
        off, sz = struct.unpack('<QQ', footer[base + 32:base + 48])
        with open(EXE, 'rb') as f:
            f.seek(off)
            data = f.read(sz)
        m = md5b(data)
        e = exp.get(nm, '')
        good = (m == e)
        ok = ok and good
        print('  %-15s size=%7d md5=%s  %s' % (nm, sz, m, 'OK' if good else 'FAIL 期望 ' + e))
    print('')
    print('[OK] 内嵌载荷与 deploy/zip 源逐一相符' if ok else '[FAIL] 载荷不一致')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())

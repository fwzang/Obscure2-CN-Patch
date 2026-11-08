# -*- coding: utf-8 -*-
"""check_exports.py — 校验代理 DLL 的导出表（Gen-1 铁律: 编后必校验）。

用法: python check_exports.py <dll路径>
判据: 必须恰有 17 个命名导出, 且名单与真实 d3d9.dll 一致
      （Direct3DCreate9 必须在列 —— 游戏唯一导入的函数）。
"""
import struct
import sys

EXPECT = [
    'Direct3DCreate9', 'Direct3DCreate9Ex', 'Direct3DCreate9On12',
    'Direct3DCreate9On12Ex', 'Direct3DShaderValidatorCreate9', 'PSGPError',
    'PSGPSampleTexture', 'D3DPERF_BeginEvent', 'D3DPERF_EndEvent',
    'D3DPERF_GetStatus', 'D3DPERF_QueryRepeatFrame', 'D3DPERF_SetMarker',
    'D3DPERF_SetOptions', 'D3DPERF_SetRegion', 'DebugSetLevel', 'DebugSetMute',
    'Direct3D9EnableMaximizedWindowedModeShim',
]


def get_exports(path):
    d = open(path, 'rb').read()
    pe = struct.unpack_from('<I', d, 0x3C)[0]
    nsec = struct.unpack_from('<H', d, pe + 6)[0]
    optsz = struct.unpack_from('<H', d, pe + 20)[0]
    opt = pe + 24
    machine = struct.unpack_from('<H', d, pe + 4)[0]
    exp_rva, exp_sz = struct.unpack_from('<II', d, opt + 96)
    secs = []
    for i in range(nsec):
        s = opt + optsz + i * 40
        vsz, va, rsz, ro = struct.unpack_from('<IIII', d, s + 8)
        secs.append((va, vsz, ro))

    def r2o(rva):
        for va, vsz, ro in secs:
            if va <= rva < va + vsz:
                return ro + (rva - va)
        return None
    if not exp_rva:
        return None, machine, 0
    o = r2o(exp_rva)
    ch, td, mj, mi, nm_rva, base, nfunc, nname, afunc, aname, aord = \
        struct.unpack_from('<IIHHIIIIIII', d, o)
    names = []
    for i in range(nname):
        nr = struct.unpack_from('<I', d, r2o(aname) + i * 4)[0]
        no = r2o(nr)
        nm = d[no:d.find(b'\x00', no)].decode('latin1')
        names.append(nm)
    return names, machine, nfunc


def main():
    if len(sys.argv) < 2:
        print('usage: check_exports.py <dll>')
        return 2
    names, machine, nfunc = get_exports(sys.argv[1])
    if names is None:
        print('[FAIL] 无导出表: %s' % sys.argv[1])
        return 1
    if machine != 0x14c:
        print('[FAIL] 非 i386 (machine=0x%x): %s' % (machine, sys.argv[1]))
        return 1
    names_sorted = sorted(names)
    expect_sorted = sorted(EXPECT)
    ok = True
    if len(names) != len(EXPECT):
        print('[FAIL] 导出数 %d != %d' % (len(names), len(EXPECT)))
        ok = False
    if names_sorted != expect_sorted:
        miss = [n for n in expect_sorted if n not in names_sorted]
        extra = [n for n in names_sorted if n not in expect_sorted]
        print('[FAIL] 名单不符: 缺 %s 多 %s' % (miss, extra))
        ok = False
    if 'Direct3DCreate9' not in names:
        print('[FAIL] 缺 Direct3DCreate9 (游戏唯一导入函数!)')
        ok = False
    if ok:
        print('[PASS] %s: %d 个导出, 名单与真实 d3d9.dll 一致, '
              'Direct3DCreate9 在列, machine=i386' % (sys.argv[1], len(names)))
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())

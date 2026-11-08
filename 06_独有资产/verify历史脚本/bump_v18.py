# -*- coding: utf-8 -*-
"""bump_v18.py — 升级到 full11 / v18：图集 2048x1024 + 无 mip 链。"""
import os
import sys

D = r'D:\SteamLibrary\steamapps\common\Obscure2\Obscure2_Handover\deploy'
PACK = 'c6faced4f4f60d5b2eb099e1688cc1ca'
PACK_P = 'fb5f2f87d3b69f0dd936b9ddee95cc68'
PROD = '34c64083b1b5c0884302a977d921ac55'
PROD_P = 'e72f170fb8d02700fcbd52c948a8b05a'
DIAG = '13d6504694cc12e69293bd166825d396'
DIAG_P = 'a3cdb8693a2c1ed71484a4798beb6cf8'


def patch(name, reps):
    p = os.path.join(D, name)
    s = open(p, 'rb').read().decode('ascii')
    for a, b in reps:
        if a not in s:
            print('  [MISS] %s : %s' % (name, a[:75]))
            return False
        s = s.replace(a, b, 1)
    s = s.replace('\r\n', '\n').replace('\r', '\n').replace('\n', '\r\n')
    open(p, 'wb').write(s.encode('ascii'))
    print('  [OK] %-20s %d B' % (name, os.path.getsize(p)))
    return True


APPLY = [
    ('set "PACKSRC=datapack_zh_full10.hvp"', 'set "PACKSRC=datapack_zh_full11.hvp"'),
    ('set "MD5_PACK_ZH=fb5f2f87d3b69f0dd936b9ddee95cc68"',
     'set "MD5_PACK_ZH=%s"\nset "MD5_PACK_ZH_P8=%s"' % (PACK, PACK_P)),
    ('if /i "!H3!"=="!MD5_PACK_ZH_P7!" set "STATE=LEGACY_CN"',
     'if /i "!H3!"=="!MD5_PACK_ZH_P8!" set "STATE=LEGACY_CN"\n'
     'if /i "!H3!"=="!MD5_PACK_ZH_P7!" set "STATE=LEGACY_CN"'),
    ('set "MD5_DLL_PROD=e72f170fb8d02700fcbd52c948a8b05a"',
     'set "MD5_DLL_PROD=%s"\nset "MD5_DLL_PROD_P18=%s"' % (PROD, PROD_P)),
    ('set "MD5_DLL_DIAG=a3cdb8693a2c1ed71484a4798beb6cf8"',
     'set "MD5_DLL_DIAG=%s"\nset "MD5_DLL_DIAG_P18=%s"' % (DIAG, DIAG_P)),
    ('if /i "!H7!"=="!MD5_DLL_PROD_P17!" set "CURDLL=OURS_PROD"',
     'if /i "!H7!"=="!MD5_DLL_PROD_P18!" set "CURDLL=OURS_PROD"\n'
     'if /i "!H7!"=="!MD5_DLL_DIAG_P18!" set "CURDLL=OURS_DIAG"\n'
     'if /i "!H7!"=="!MD5_DLL_PROD_P17!" set "CURDLL=OURS_PROD"'),
    ('set "VER_PACK=full10"', 'set "VER_PACK=full11"'),
    ('set "VER_DLL=v17"', 'set "VER_DLL=v18"'),
    ('set "VER_NOTE=20px no-stroke/no-binarize + no point sampling + no Reset hook + checkpoints"',
     'set "VER_NOTE=20px atlas 2048x1024 MipLevels=1 + no point sampling + no Reset hook"'),
]

RESTORE = [
    ('set "MD5_DLL_PROD=e72f170fb8d02700fcbd52c948a8b05a"',
     'set "MD5_DLL_PROD=%s"\nset "MD5_DLL_PROD_P18=%s"' % (PROD, PROD_P)),
    ('set "MD5_DLL_DIAG=a3cdb8693a2c1ed71484a4798beb6cf8"',
     'set "MD5_DLL_DIAG=%s"\nset "MD5_DLL_DIAG_P18=%s"' % (DIAG, DIAG_P)),
    ('if /i "!HD!"=="!MD5_DLL_PROD_P17!" set "OWNOURS=1"',
     'if /i "!HD!"=="!MD5_DLL_PROD_P18!" set "OWNOURS=1"\n'
     'if /i "!HD!"=="!MD5_DLL_DIAG_P18!" set "OWNOURS=1"\n'
     'if /i "!HD!"=="!MD5_DLL_PROD_P17!" set "OWNOURS=1"'),
    ('set "VER_DLL=v17"', 'set "VER_DLL=v18"'),
    ('set "VER_PACK=full10"', 'set "VER_PACK=full11"'),
]


def main():
    ok = patch('gate3_apply.bat', APPLY)
    ok &= patch('gate3_restore.bat', RESTORE)
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())

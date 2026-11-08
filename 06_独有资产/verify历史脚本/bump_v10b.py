# -*- coding: utf-8 -*-
"""bump_v10b.py — deploy 两个 bat 升级到 full9 / v10。"""
import os
import sys

D = r'D:\SteamLibrary\steamapps\common\Obscure2\Obscure2_Handover\deploy'
PACK = '083550dcba1557b19bc548ec15243b80'
PACK_P = 'b2b46244a3efce805cc22c6d8dbc3c3a'
PROD = 'd0399063d7fe000d546d477091910abf'
PROD_P = 'fbc9c7a9d2fc42806d9265c5ccd5c477'
DIAG = 'a16116b5fcffd6aae9ea0ed2407fb9b4'
DIAG_P = '525589c19d97ebef08cc55c7f8ef7d0e'


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
    ('set "PACKSRC=datapack_zh_full8.hvp"', 'set "PACKSRC=datapack_zh_full9.hvp"'),
    ('set "MD5_PACK_ZH=b2b46244a3efce805cc22c6d8dbc3c3a"',
     'set "MD5_PACK_ZH=%s"\nset "MD5_PACK_ZH_P6=%s"' % (PACK, PACK_P)),
    ('if /i "!H3!"=="!MD5_PACK_ZH_P5!" set "STATE=LEGACY_CN"',
     'if /i "!H3!"=="!MD5_PACK_ZH_P6!" set "STATE=LEGACY_CN"\n'
     'if /i "!H3!"=="!MD5_PACK_ZH_P5!" set "STATE=LEGACY_CN"'),
    ('set "MD5_DLL_PROD=fbc9c7a9d2fc42806d9265c5ccd5c477"',
     'set "MD5_DLL_PROD=%s"\nset "MD5_DLL_PROD_P10=%s"' % (PROD, PROD_P)),
    ('set "MD5_DLL_DIAG=525589c19d97ebef08cc55c7f8ef7d0e"',
     'set "MD5_DLL_DIAG=%s"\nset "MD5_DLL_DIAG_P10=%s"' % (DIAG, DIAG_P)),
    ('if /i "!H7!"=="!MD5_DLL_PROD_P9!" set "CURDLL=OURS_PROD"',
     'if /i "!H7!"=="!MD5_DLL_PROD_P10!" set "CURDLL=OURS_PROD"\n'
     'if /i "!H7!"=="!MD5_DLL_DIAG_P10!" set "CURDLL=OURS_DIAG"\n'
     'if /i "!H7!"=="!MD5_DLL_PROD_P9!" set "CURDLL=OURS_PROD"'),
]

RESTORE = [
    ('set "MD5_DLL_PROD=fbc9c7a9d2fc42806d9265c5ccd5c477"',
     'set "MD5_DLL_PROD=%s"\nset "MD5_DLL_PROD_P10=%s"' % (PROD, PROD_P)),
    ('set "MD5_DLL_DIAG=525589c19d97ebef08cc55c7f8ef7d0e"',
     'set "MD5_DLL_DIAG=%s"\nset "MD5_DLL_DIAG_P10=%s"' % (DIAG, DIAG_P)),
    ('if /i "!HD!"=="!MD5_DLL_PROD_P9!" set "OWNOURS=1"',
     'if /i "!HD!"=="!MD5_DLL_PROD_P10!" set "OWNOURS=1"\n'
     'if /i "!HD!"=="!MD5_DLL_DIAG_P10!" set "OWNOURS=1"\n'
     'if /i "!HD!"=="!MD5_DLL_PROD_P9!" set "OWNOURS=1"'),
]


def main():
    ok = patch('gate3_apply.bat', APPLY)
    ok &= patch('gate3_restore.bat', RESTORE)
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())

# -*- coding: utf-8 -*-
"""bump_v15.py — DLL 升级到 v15（Reset 不再释放大图集），包仍是 full10。"""
import os
import sys

D = r'D:\SteamLibrary\steamapps\common\Obscure2\Obscure2_Handover\deploy'
PROD = '9871de6285b82d2d14e9435c7bf8a561'
PROD_P = 'ef09e5f6ce9a914efbc24c1f00a3d565'
DIAG = 'b6f0de8b391506a729d8664dcea924d4'
DIAG_P = '9e7e24787c6e79b30f72a7bbe5a2a9e4'


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
    ('set "MD5_DLL_PROD=ef09e5f6ce9a914efbc24c1f00a3d565"',
     'set "MD5_DLL_PROD=%s"\nset "MD5_DLL_PROD_P15=%s"' % (PROD, PROD_P)),
    ('set "MD5_DLL_DIAG=9e7e24787c6e79b30f72a7bbe5a2a9e4"',
     'set "MD5_DLL_DIAG=%s"\nset "MD5_DLL_DIAG_P15=%s"' % (DIAG, DIAG_P)),
    ('if /i "!H7!"=="!MD5_DLL_PROD_P14!" set "CURDLL=OURS_PROD"',
     'if /i "!H7!"=="!MD5_DLL_PROD_P15!" set "CURDLL=OURS_PROD"\n'
     'if /i "!H7!"=="!MD5_DLL_DIAG_P15!" set "CURDLL=OURS_DIAG"\n'
     'if /i "!H7!"=="!MD5_DLL_PROD_P14!" set "CURDLL=OURS_PROD"'),
]

RESTORE = [
    ('set "MD5_DLL_PROD=ef09e5f6ce9a914efbc24c1f00a3d565"',
     'set "MD5_DLL_PROD=%s"\nset "MD5_DLL_PROD_P15=%s"' % (PROD, PROD_P)),
    ('set "MD5_DLL_DIAG=9e7e24787c6e79b30f72a7bbe5a2a9e4"',
     'set "MD5_DLL_DIAG=%s"\nset "MD5_DLL_DIAG_P15=%s"' % (DIAG, DIAG_P)),
    ('if /i "!HD!"=="!MD5_DLL_PROD_P14!" set "OWNOURS=1"',
     'if /i "!HD!"=="!MD5_DLL_PROD_P15!" set "OWNOURS=1"\n'
     'if /i "!HD!"=="!MD5_DLL_DIAG_P15!" set "OWNOURS=1"\n'
     'if /i "!HD!"=="!MD5_DLL_PROD_P14!" set "OWNOURS=1"'),
]


def main():
    ok = patch('gate3_apply.bat', APPLY)
    ok &= patch('gate3_restore.bat', RESTORE)
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())

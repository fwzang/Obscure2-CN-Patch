# -*- coding: utf-8 -*-
"""bump_v16.py — DLL 升级到 v16（不拦 Reset + Present 异常作废），包仍 full10。"""
import os
import sys

D = r'D:\SteamLibrary\steamapps\common\Obscure2\Obscure2_Handover\deploy'
PROD = 'b25816a894d437251743d86bfa148980'
PROD_P = '9871de6285b82d2d14e9435c7bf8a561'
DIAG = '547ee9d0449ffe99c0a362b91dfe492e'
DIAG_P = 'b6f0de8b391506a729d8664dcea924d4'


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
    ('set "MD5_DLL_PROD=9871de6285b82d2d14e9435c7bf8a561"',
     'set "MD5_DLL_PROD=%s"\nset "MD5_DLL_PROD_P16=%s"' % (PROD, PROD_P)),
    ('set "MD5_DLL_DIAG=b6f0de8b391506a729d8664dcea924d4"',
     'set "MD5_DLL_DIAG=%s"\nset "MD5_DLL_DIAG_P16=%s"' % (DIAG, DIAG_P)),
    ('if /i "!H7!"=="!MD5_DLL_PROD_P15!" set "CURDLL=OURS_PROD"',
     'if /i "!H7!"=="!MD5_DLL_PROD_P16!" set "CURDLL=OURS_PROD"\n'
     'if /i "!H7!"=="!MD5_DLL_DIAG_P16!" set "CURDLL=OURS_DIAG"\n'
     'if /i "!H7!"=="!MD5_DLL_PROD_P15!" set "CURDLL=OURS_PROD"'),
]

RESTORE = [
    ('set "MD5_DLL_PROD=9871de6285b82d2d14e9435c7bf8a561"',
     'set "MD5_DLL_PROD=%s"\nset "MD5_DLL_PROD_P16=%s"' % (PROD, PROD_P)),
    ('set "MD5_DLL_DIAG=b6f0de8b391506a729d8664dcea924d4"',
     'set "MD5_DLL_DIAG=%s"\nset "MD5_DLL_DIAG_P16=%s"' % (DIAG, DIAG_P)),
    ('if /i "!HD!"=="!MD5_DLL_PROD_P15!" set "OWNOURS=1"',
     'if /i "!HD!"=="!MD5_DLL_PROD_P16!" set "OWNOURS=1"\n'
     'if /i "!HD!"=="!MD5_DLL_DIAG_P16!" set "OWNOURS=1"\n'
     'if /i "!HD!"=="!MD5_DLL_PROD_P15!" set "OWNOURS=1"'),
]


def main():
    ok = patch('gate3_apply.bat', APPLY)
    ok &= patch('gate3_restore.bat', RESTORE)
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())

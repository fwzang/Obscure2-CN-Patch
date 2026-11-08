# -*- coding: utf-8 -*-
"""bump_v9.py — 只升级 DLL md5 到 v9（图集与文本包未变，仍为 full8）。"""
import os
import sys

D = r'D:\SteamLibrary\steamapps\common\Obscure2\Obscure2_Handover\deploy'
PROD = 'd0399063d7fe000d546d477091910abf'
PROD_P = 'fbc9c7a9d2fc42806d9265c5ccd5c477'
DIAG = 'a16116b5fcffd6aae9ea0ed2407fb9b4'
DIAG_P = '525589c19d97ebef08cc55c7f8ef7d0e'


def patch(name, reps):
    p = os.path.join(D, name)
    s = open(p, 'rb').read().decode('ascii')
    for a, b in reps:
        if a not in s:
            print('  [MISS] %s : %s' % (name, a[:70]))
            return False
        s = s.replace(a, b, 1)
    s = s.replace('\r\n', '\n').replace('\r', '\n').replace('\n', '\r\n')
    open(p, 'wb').write(s.encode('ascii'))
    print('  [OK] %-20s %d B' % (name, os.path.getsize(p)))
    return True


APPLY = [
    ('set "MD5_DLL_PROD=bbbd00675bf32649d3e198f40daebcdc"',
     'set "MD5_DLL_PROD=%s"\nset "MD5_DLL_PROD_P10=%s"' % (PROD, PROD_P)),
    ('set "MD5_DLL_DIAG=6b1ef418cb6609f3abbe9b833aea94ca"',
     'set "MD5_DLL_DIAG=%s"\nset "MD5_DLL_DIAG_P10=%s"' % (DIAG, DIAG_P)),
    ('if /i "!H7!"=="!MD5_DLL_PROD_P9!" set "CURDLL=OURS_PROD"',
     'if /i "!H7!"=="!MD5_DLL_PROD_P10!" set "CURDLL=OURS_PROD"\n'
     'if /i "!H7!"=="!MD5_DLL_DIAG_P10!" set "CURDLL=OURS_DIAG"\n'
     'if /i "!H7!"=="!MD5_DLL_PROD_P9!" set "CURDLL=OURS_PROD"'),
]

RESTORE = [
    ('set "MD5_DLL_PROD=bbbd00675bf32649d3e198f40daebcdc"',
     'set "MD5_DLL_PROD=%s"\nset "MD5_DLL_PROD_P10=%s"' % (PROD, PROD_P)),
    ('set "MD5_DLL_DIAG=6b1ef418cb6609f3abbe9b833aea94ca"',
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

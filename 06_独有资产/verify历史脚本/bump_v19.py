# -*- coding: utf-8 -*-
"""bump_v19.py — DLL 升级到 v19（修正 ATLAS_W/H 常量），包仍 full11。"""
import os
import sys

D = r'D:\SteamLibrary\steamapps\common\Obscure2\Obscure2_Handover\deploy'
PROD = 'bc12c6b1807272c8e9c858c7f3d97535'
PROD_P = '34c64083b1b5c0884302a977d921ac55'
DIAG = '6259de67aaaa48378fbfe93b78a14390'
DIAG_P = '13d6504694cc12e69293bd166825d396'


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
    ('set "MD5_DLL_PROD=34c64083b1b5c0884302a977d921ac55"',
     'set "MD5_DLL_PROD=%s"\nset "MD5_DLL_PROD_P19=%s"' % (PROD, PROD_P)),
    ('set "MD5_DLL_DIAG=13d6504694cc12e69293bd166825d396"',
     'set "MD5_DLL_DIAG=%s"\nset "MD5_DLL_DIAG_P19=%s"' % (DIAG, DIAG_P)),
    ('if /i "!H7!"=="!MD5_DLL_PROD_P18!" set "CURDLL=OURS_PROD"',
     'if /i "!H7!"=="!MD5_DLL_PROD_P19!" set "CURDLL=OURS_PROD"\n'
     'if /i "!H7!"=="!MD5_DLL_DIAG_P19!" set "CURDLL=OURS_DIAG"\n'
     'if /i "!H7!"=="!MD5_DLL_PROD_P18!" set "CURDLL=OURS_PROD"'),
    ('set "VER_DLL=v18"', 'set "VER_DLL=v19"'),
]

RESTORE = [
    ('set "MD5_DLL_PROD=34c64083b1b5c0884302a977d921ac55"',
     'set "MD5_DLL_PROD=%s"\nset "MD5_DLL_PROD_P19=%s"' % (PROD, PROD_P)),
    ('set "MD5_DLL_DIAG=13d6504694cc12e69293bd166825d396"',
     'set "MD5_DLL_DIAG=%s"\nset "MD5_DLL_DIAG_P19=%s"' % (DIAG, DIAG_P)),
    ('if /i "!HD!"=="!MD5_DLL_PROD_P18!" set "OWNOURS=1"',
     'if /i "!HD!"=="!MD5_DLL_PROD_P19!" set "OWNOURS=1"\n'
     'if /i "!HD!"=="!MD5_DLL_DIAG_P19!" set "OWNOURS=1"\n'
     'if /i "!HD!"=="!MD5_DLL_PROD_P18!" set "OWNOURS=1"'),
    ('set "VER_DLL=v18"', 'set "VER_DLL=v19"'),
]


def main():
    ok = patch('gate3_apply.bat', APPLY)
    ok &= patch('gate3_restore.bat', RESTORE)
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())

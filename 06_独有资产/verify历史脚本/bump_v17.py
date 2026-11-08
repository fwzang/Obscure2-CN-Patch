# -*- coding: utf-8 -*-
"""bump_v17.py — PROD/DIAG 双双升级到 v17（含检查点日志），包仍 full10。"""
import os
import sys

D = r'D:\SteamLibrary\steamapps\common\Obscure2\Obscure2_Handover\deploy'
PROD = 'e72f170fb8d02700fcbd52c948a8b05a'
PROD_P = 'b25816a894d437251743d86bfa148980'
DIAG = 'a3cdb8693a2c1ed71484a4798beb6cf8'
DIAG_P = '547ee9d0449ffe99c0a362b91dfe492e'


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
    ('set "MD5_DLL_PROD=b25816a894d437251743d86bfa148980"',
     'set "MD5_DLL_PROD=%s"\nset "MD5_DLL_PROD_P17=%s"' % (PROD, PROD_P)),
    ('set "MD5_DLL_DIAG=547ee9d0449ffe99c0a362b91dfe492e"',
     'set "MD5_DLL_DIAG=%s"\nset "MD5_DLL_DIAG_P17=%s"' % (DIAG, DIAG_P)),
    ('if /i "!H7!"=="!MD5_DLL_PROD_P16!" set "CURDLL=OURS_PROD"',
     'if /i "!H7!"=="!MD5_DLL_PROD_P17!" set "CURDLL=OURS_PROD"\n'
     'if /i "!H7!"=="!MD5_DLL_DIAG_P17!" set "CURDLL=OURS_DIAG"\n'
     'if /i "!H7!"=="!MD5_DLL_PROD_P16!" set "CURDLL=OURS_PROD"'),
]

RESTORE = [
    ('set "MD5_DLL_PROD=b25816a894d437251743d86bfa148980"',
     'set "MD5_DLL_PROD=%s"\nset "MD5_DLL_PROD_P17=%s"' % (PROD, PROD_P)),
    ('set "MD5_DLL_DIAG=547ee9d0449ffe99c0a362b91dfe492e"',
     'set "MD5_DLL_DIAG=%s"\nset "MD5_DLL_DIAG_P17=%s"' % (DIAG, DIAG_P)),
    ('if /i "!HD!"=="!MD5_DLL_PROD_P16!" set "OWNOURS=1"',
     'if /i "!HD!"=="!MD5_DLL_PROD_P17!" set "OWNOURS=1"\n'
     'if /i "!HD!"=="!MD5_DLL_DIAG_P17!" set "OWNOURS=1"\n'
     'if /i "!HD!"=="!MD5_DLL_PROD_P16!" set "OWNOURS=1"'),
]


def main():
    ok = patch('gate3_apply.bat', APPLY)
    ok &= patch('gate3_restore.bat', RESTORE)
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())

# -*- coding: utf-8 -*-
"""bump_v12.py — 只升级 DLL 到 v12（关闭点采样），包仍是 full10。"""
import os
import sys

D = r'D:\SteamLibrary\steamapps\common\Obscure2\Obscure2_Handover\deploy'
PROD = 'f75a2eec50ad5752c7fe45d4a34f6ab9'
PROD_P = 'e8300eba7910e5c4398a8268316011fa'
DIAG = '0b66d7356c611867eb53b4576d948581'
DIAG_P = '8f8c668b4a7f89f7c7d45f9e995a0490'


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
    ('set "MD5_DLL_PROD=e8300eba7910e5c4398a8268316011fa"',
     'set "MD5_DLL_PROD=%s"\nset "MD5_DLL_PROD_P12=%s"' % (PROD, PROD_P)),
    ('set "MD5_DLL_DIAG=8f8c668b4a7f89f7c7d45f9e995a0490"',
     'set "MD5_DLL_DIAG=%s"\nset "MD5_DLL_DIAG_P12=%s"' % (DIAG, DIAG_P)),
    ('if /i "!H7!"=="!MD5_DLL_PROD_P11!" set "CURDLL=OURS_PROD"',
     'if /i "!H7!"=="!MD5_DLL_PROD_P12!" set "CURDLL=OURS_PROD"\n'
     'if /i "!H7!"=="!MD5_DLL_DIAG_P12!" set "CURDLL=OURS_DIAG"\n'
     'if /i "!H7!"=="!MD5_DLL_PROD_P11!" set "CURDLL=OURS_PROD"'),
]

RESTORE = [
    ('set "MD5_DLL_PROD=e8300eba7910e5c4398a8268316011fa"',
     'set "MD5_DLL_PROD=%s"\nset "MD5_DLL_PROD_P12=%s"' % (PROD, PROD_P)),
    ('set "MD5_DLL_DIAG=8f8c668b4a7f89f7c7d45f9e995a0490"',
     'set "MD5_DLL_DIAG=%s"\nset "MD5_DLL_DIAG_P12=%s"' % (DIAG, DIAG_P)),
    ('if /i "!HD!"=="!MD5_DLL_PROD_P11!" set "OWNOURS=1"',
     'if /i "!HD!"=="!MD5_DLL_PROD_P12!" set "OWNOURS=1"\n'
     'if /i "!HD!"=="!MD5_DLL_DIAG_P12!" set "OWNOURS=1"\n'
     'if /i "!HD!"=="!MD5_DLL_PROD_P11!" set "OWNOURS=1"'),
]


def main():
    ok = patch('gate3_apply.bat', APPLY)
    ok &= patch('gate3_restore.bat', RESTORE)
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())

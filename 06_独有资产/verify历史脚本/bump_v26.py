# -*- coding: utf-8 -*-
"""bump_v26.py — DLL 升级到 v26（UT src 内容哈希识别）。"""
import os
import sys

D = r'D:\SteamLibrary\steamapps\common\Obscure2\Obscure2_Handover\deploy'
PROD = '2a4d88656f663cc38a906e532486e1db'
PROD_P = 'c7090c591087bed054e3f1879d56ec71'
DIAG = '792704cad345413e66b93fc029126a15'
DIAG_P = '4547dd7f493fdb08bd842959d3a1f4d8'

OLD_NOTE = 'set "VER_NOTE=20px smooth + vertex-count gate(100) + c47 unbind + dev-lost guard"'
NEW_NOTE = 'set "VER_NOTE=20px smooth + UT-src FNV1a font identity + c47 unbind + draw passthrough"'


def patch(name, reps):
    p = os.path.join(D, name)
    s = open(p, 'rb').read().decode('ascii')
    for a, b in reps:
        if a not in s:
            print('  [MISS] %s : %s' % (name, a[:70]))
            return False
        s = s.replace(a, b, 1)
    s = s.replace('\r\n', '\n').replace('\r', '\n').replace('\n', '\r\n')
    try:
        data = s.encode('ascii')
    except UnicodeEncodeError as e:
        print('  [ABORT] 非 ASCII，未写入: %s' % e)
        return False
    open(p, 'wb').write(data)
    print('  [OK] %-20s %d B' % (name, os.path.getsize(p)))
    return True


APPLY = [
    ('set "MD5_DLL_PROD=%s"' % PROD_P,
     'set "MD5_DLL_PROD=%s"\nset "MD5_DLL_PROD_P26=%s"' % (PROD, PROD_P)),
    ('set "MD5_DLL_DIAG=%s"' % DIAG_P,
     'set "MD5_DLL_DIAG=%s"\nset "MD5_DLL_DIAG_P26=%s"' % (DIAG, DIAG_P)),
    ('if /i "!H7!"=="!MD5_DLL_PROD_P25!" set "CURDLL=OURS_PROD"',
     'if /i "!H7!"=="!MD5_DLL_PROD_P26!" set "CURDLL=OURS_PROD"\n'
     'if /i "!H7!"=="!MD5_DLL_DIAG_P26!" set "CURDLL=OURS_DIAG"\n'
     'if /i "!H7!"=="!MD5_DLL_PROD_P25!" set "CURDLL=OURS_PROD"'),
    ('set "VER_DLL=v25"', 'set "VER_DLL=v26"'),
    (OLD_NOTE, NEW_NOTE),
    ('set "DV=v25 PROD (this script\'s version)"', 'set "DV=v26 PROD (this script\'s version)"'),
    ('set "DV=v25 DIAG (this script\'s version)"', 'set "DV=v26 DIAG (this script\'s version)"'),
]

RESTORE = [
    ('set "MD5_DLL_PROD=%s"' % PROD_P,
     'set "MD5_DLL_PROD=%s"\nset "MD5_DLL_PROD_P26=%s"' % (PROD, PROD_P)),
    ('set "MD5_DLL_DIAG=%s"' % DIAG_P,
     'set "MD5_DLL_DIAG=%s"\nset "MD5_DLL_DIAG_P26=%s"' % (DIAG, DIAG_P)),
    ('if /i "!HD!"=="!MD5_DLL_PROD_P25!" set "OWNOURS=1"',
     'if /i "!HD!"=="!MD5_DLL_PROD_P26!" set "OWNOURS=1"\n'
     'if /i "!HD!"=="!MD5_DLL_DIAG_P26!" set "OWNOURS=1"\n'
     'if /i "!HD!"=="!MD5_DLL_PROD_P25!" set "OWNOURS=1"'),
    ('set "VER_DLL=v25"', 'set "VER_DLL=v26"'),
]


def main():
    ok = patch('gate3_apply.bat', APPLY)
    ok &= patch('gate3_restore.bat', RESTORE)
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())

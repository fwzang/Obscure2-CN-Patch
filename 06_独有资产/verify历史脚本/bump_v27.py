# -*- coding: utf-8 -*-
"""bump_v27.py — DLL 升级到 v27（v21 行为 + 诊断日志）。"""
import os
import sys

D = r'D:\SteamLibrary\steamapps\common\Obscure2\Obscure2_Handover\deploy'
PROD = '59746a87fb5e8e9a61f6fc5ae28442b4'
PROD_P = '2a4d88656f663cc38a906e532486e1db'
DIAG = '037756cb819c45ce84e4a0f6ac4e8d2a'
DIAG_P = '792704cad345413e66b93fc029126a15'

OLD_NOTE = 'set "VER_NOTE=20px smooth + UT-src FNV1a font identity + c47 unbind + draw passthrough"'
NEW_NOTE = 'set "VER_NOTE=20px smooth + v21 swap behaviour + SetTexture diagnostics + c47 + draw passthrough"'


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
     'set "MD5_DLL_PROD=%s"\nset "MD5_DLL_PROD_P27=%s"' % (PROD, PROD_P)),
    ('set "MD5_DLL_DIAG=%s"' % DIAG_P,
     'set "MD5_DLL_DIAG=%s"\nset "MD5_DLL_DIAG_P27=%s"' % (DIAG, DIAG_P)),
    ('if /i "!H7!"=="!MD5_DLL_PROD_P26!" set "CURDLL=OURS_PROD"',
     'if /i "!H7!"=="!MD5_DLL_PROD_P27!" set "CURDLL=OURS_PROD"\n'
     'if /i "!H7!"=="!MD5_DLL_DIAG_P27!" set "CURDLL=OURS_DIAG"\n'
     'if /i "!H7!"=="!MD5_DLL_PROD_P26!" set "CURDLL=OURS_PROD"'),
    ('set "VER_DLL=v26"', 'set "VER_DLL=v27"'),
    (OLD_NOTE, NEW_NOTE),
    ('set "DV=v26 PROD (this script\'s version)"', 'set "DV=v27 PROD (this script\'s version)"'),
    ('set "DV=v26 DIAG (this script\'s version)"', 'set "DV=v27 DIAG (this script\'s version)"'),
]

RESTORE = [
    ('set "MD5_DLL_PROD=%s"' % PROD_P,
     'set "MD5_DLL_PROD=%s"\nset "MD5_DLL_PROD_P27=%s"' % (PROD, PROD_P)),
    ('set "MD5_DLL_DIAG=%s"' % DIAG_P,
     'set "MD5_DLL_DIAG=%s"\nset "MD5_DLL_DIAG_P27=%s"' % (DIAG, DIAG_P)),
    ('if /i "!HD!"=="!MD5_DLL_PROD_P26!" set "OWNOURS=1"',
     'if /i "!HD!"=="!MD5_DLL_PROD_P27!" set "OWNOURS=1"\n'
     'if /i "!HD!"=="!MD5_DLL_DIAG_P27!" set "OWNOURS=1"\n'
     'if /i "!HD!"=="!MD5_DLL_PROD_P26!" set "OWNOURS=1"'),
    ('set "VER_DLL=v26"', 'set "VER_DLL=v27"'),
]


def main():
    ok = patch('gate3_apply.bat', APPLY)
    ok &= patch('gate3_restore.bat', RESTORE)
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())

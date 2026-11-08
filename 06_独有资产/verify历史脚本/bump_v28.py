# -*- coding: utf-8 -*-
"""bump_v28.py — DLL 升级到 v28（尺寸白名单 + 哈希黑名单）。"""
import os
import sys

D = r'D:\SteamLibrary\steamapps\common\Obscure2\Obscure2_Handover\deploy'
PROD = '411658c1453e6c8c7c4d15a011b7fd23'
PROD_P = '59746a87fb5e8e9a61f6fc5ae28442b4'
DIAG = '1bf95692faaaa899301dce453137602b'
DIAG_P = '037756cb819c45ce84e4a0f6ac4e8d2a'

OLD_NOTE = 'set "VER_NOTE=20px smooth + v21 swap behaviour + SetTexture diagnostics + c47 + draw passthrough"'
NEW_NOTE = 'set "VER_NOTE=20px smooth + size allowlist AND hash blacklist + c47 + draw passthrough"'


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
     'set "MD5_DLL_PROD=%s"\nset "MD5_DLL_PROD_P28=%s"' % (PROD, PROD_P)),
    ('set "MD5_DLL_DIAG=%s"' % DIAG_P,
     'set "MD5_DLL_DIAG=%s"\nset "MD5_DLL_DIAG_P28=%s"' % (DIAG, DIAG_P)),
    ('if /i "!H7!"=="!MD5_DLL_PROD_P27!" set "CURDLL=OURS_PROD"',
     'if /i "!H7!"=="!MD5_DLL_PROD_P28!" set "CURDLL=OURS_PROD"\n'
     'if /i "!H7!"=="!MD5_DLL_DIAG_P28!" set "CURDLL=OURS_DIAG"\n'
     'if /i "!H7!"=="!MD5_DLL_PROD_P27!" set "CURDLL=OURS_PROD"'),
    ('set "VER_DLL=v27"', 'set "VER_DLL=v28"'),
    (OLD_NOTE, NEW_NOTE),
    ('set "DV=v27 PROD (this script\'s version)"', 'set "DV=v28 PROD (this script\'s version)"'),
    ('set "DV=v27 DIAG (this script\'s version)"', 'set "DV=v28 DIAG (this script\'s version)"'),
]

RESTORE = [
    ('set "MD5_DLL_PROD=%s"' % PROD_P,
     'set "MD5_DLL_PROD=%s"\nset "MD5_DLL_PROD_P28=%s"' % (PROD, PROD_P)),
    ('set "MD5_DLL_DIAG=%s"' % DIAG_P,
     'set "MD5_DLL_DIAG=%s"\nset "MD5_DLL_DIAG_P28=%s"' % (DIAG, DIAG_P)),
    ('if /i "!HD!"=="!MD5_DLL_PROD_P27!" set "OWNOURS=1"',
     'if /i "!HD!"=="!MD5_DLL_PROD_P28!" set "OWNOURS=1"\n'
     'if /i "!HD!"=="!MD5_DLL_DIAG_P28!" set "OWNOURS=1"\n'
     'if /i "!HD!"=="!MD5_DLL_PROD_P27!" set "OWNOURS=1"'),
    ('set "VER_DLL=v27"', 'set "VER_DLL=v28"'),
]


def main():
    ok = patch('gate3_apply.bat', APPLY)
    ok &= patch('gate3_restore.bat', RESTORE)
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())

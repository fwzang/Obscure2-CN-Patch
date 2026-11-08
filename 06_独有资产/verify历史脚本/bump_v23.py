# -*- coding: utf-8 -*-
"""bump_v23.py — DLL 升级到 v23（Draw 钩子零干预的稳定版），包仍 full11。"""
import os
import sys

D = r'D:\SteamLibrary\steamapps\common\Obscure2\Obscure2_Handover\deploy'
PROD = '9440a8fccb6b070f3d926d24ee76500e'
PROD_P = '6d29aa6ae3872886121a2a6955228bcd'
DIAG = '74bf1789fc21c229588ad23bb769b8c7'
DIAG_P = '16a5e94bbbe7c2b8d90fc5babcc34668'

OLD_NOTE = 'set "VER_NOTE=20px smooth + Z-first 3D gate + c47 unbind + dev-lost guard"'
NEW_NOTE = 'set "VER_NOTE=20px smooth STABLE: draw hooks passive, Reset unbind + dev-lost guard only"'


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
     'set "MD5_DLL_PROD=%s"\nset "MD5_DLL_PROD_P23=%s"' % (PROD, PROD_P)),
    ('set "MD5_DLL_DIAG=%s"' % DIAG_P,
     'set "MD5_DLL_DIAG=%s"\nset "MD5_DLL_DIAG_P23=%s"' % (DIAG, DIAG_P)),
    ('if /i "!H7!"=="!MD5_DLL_PROD_P22!" set "CURDLL=OURS_PROD"',
     'if /i "!H7!"=="!MD5_DLL_PROD_P23!" set "CURDLL=OURS_PROD"\n'
     'if /i "!H7!"=="!MD5_DLL_DIAG_P23!" set "CURDLL=OURS_DIAG"\n'
     'if /i "!H7!"=="!MD5_DLL_PROD_P22!" set "CURDLL=OURS_PROD"'),
    ('set "VER_DLL=v22"', 'set "VER_DLL=v23"'),
    (OLD_NOTE, NEW_NOTE),
    ('set "DV=v22 PROD (this script\'s version)"', 'set "DV=v23 PROD (this script\'s version)"'),
    ('set "DV=v22 DIAG (this script\'s version)"', 'set "DV=v23 DIAG (this script\'s version)"'),
]

RESTORE = [
    ('set "MD5_DLL_PROD=%s"' % PROD_P,
     'set "MD5_DLL_PROD=%s"\nset "MD5_DLL_PROD_P23=%s"' % (PROD, PROD_P)),
    ('set "MD5_DLL_DIAG=%s"' % DIAG_P,
     'set "MD5_DLL_DIAG=%s"\nset "MD5_DLL_DIAG_P23=%s"' % (DIAG, DIAG_P)),
    ('if /i "!HD!"=="!MD5_DLL_PROD_P22!" set "OWNOURS=1"',
     'if /i "!HD!"=="!MD5_DLL_PROD_P23!" set "OWNOURS=1"\n'
     'if /i "!HD!"=="!MD5_DLL_DIAG_P23!" set "OWNOURS=1"\n'
     'if /i "!HD!"=="!MD5_DLL_PROD_P22!" set "OWNOURS=1"'),
    ('set "VER_DLL=v22"', 'set "VER_DLL=v23"'),
]


def main():
    ok = patch('gate3_apply.bat', APPLY)
    ok &= patch('gate3_restore.bat', RESTORE)
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())

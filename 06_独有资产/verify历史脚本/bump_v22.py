# -*- coding: utf-8 -*-
"""bump_v22.py — DLL 升级到 v22（修账本 bug），包仍 full11。"""
import os
import sys

D = r'D:\SteamLibrary\steamapps\common\Obscure2\Obscure2_Handover\deploy'
PROD = '6d29aa6ae3872886121a2a6955228bcd'
PROD_P = '6c0bb7777ce05371c98d6742e4df607c'
DIAG = '16a5e94bbbe7c2b8d90fc5babcc34668'
DIAG_P = '4df858be253383980b04502f0e8262db'


def patch(name, reps):
    p = os.path.join(D, name)
    s = open(p, 'rb').read().decode('ascii')
    for a, b in reps:
        if a not in s:
            print('  [MISS] %s : %s' % (name, a[:75]))
            return False
        s = s.replace(a, b, 1)
    s = s.replace('\r\n', '\n').replace('\r', '\n').replace('\n', '\r\n')
    try:
        data = s.encode('ascii')
    except UnicodeEncodeError as e:
        print('  [ABORT] %s 含非 ASCII，未写入: %s' % (name, e))
        return False
    if any(b > 127 for b in data):
        print('  [ABORT] %s 含非 ASCII 字节，未写入' % name)
        return False
    open(p, 'wb').write(data)
    print('  [OK] %-20s %d B' % (name, os.path.getsize(p)))
    return True


APPLY = [
    ('set "MD5_DLL_PROD=6c0bb7777ce05371c98d6742e4df607c"',
     'set "MD5_DLL_PROD=%s"\nset "MD5_DLL_PROD_P22=%s"' % (PROD, PROD_P)),
    ('set "MD5_DLL_DIAG=4df858be253383980b04502f0e8262db"',
     'set "MD5_DLL_DIAG=%s"\nset "MD5_DLL_DIAG_P22=%s"' % (DIAG, DIAG_P)),
    ('if /i "!H7!"=="!MD5_DLL_PROD_P20!" set "CURDLL=OURS_PROD"',
     'if /i "!H7!"=="!MD5_DLL_PROD_P22!" set "CURDLL=OURS_PROD"\n'
     'if /i "!H7!"=="!MD5_DLL_DIAG_P22!" set "CURDLL=OURS_DIAG"\n'
     'if /i "!H7!"=="!MD5_DLL_PROD_P20!" set "CURDLL=OURS_PROD"'),
    ('set "VER_DLL=v21"', 'set "VER_DLL=v22"'),
    ('set "VER_NOTE=20px SSAA(3x,BOX) + c47 unbind-before-Reset + dev-lost guard + bookkeeping leak fix"',
     'set "VER_NOTE=20px smooth + Z-first 3D gate + c47 unbind + dev-lost guard"'),
]

RESTORE = [
    ('set "MD5_DLL_PROD=6c0bb7777ce05371c98d6742e4df607c"',
     'set "MD5_DLL_PROD=%s"\nset "MD5_DLL_PROD_P22=%s"' % (PROD, PROD_P)),
    ('set "MD5_DLL_DIAG=4df858be253383980b04502f0e8262db"',
     'set "MD5_DLL_DIAG=%s"\nset "MD5_DLL_DIAG_P22=%s"' % (DIAG, DIAG_P)),
    ('if /i "!HD!"=="!MD5_DLL_PROD_P20!" set "OWNOURS=1"',
     'if /i "!HD!"=="!MD5_DLL_PROD_P22!" set "OWNOURS=1"\n'
     'if /i "!HD!"=="!MD5_DLL_DIAG_P22!" set "OWNOURS=1"\n'
     'if /i "!HD!"=="!MD5_DLL_PROD_P20!" set "OWNOURS=1"'),
    ('set "VER_DLL=v21"', 'set "VER_DLL=v22"'),
]


def main():
    ok = patch('gate3_apply.bat', APPLY)
    ok &= patch('gate3_restore.bat', RESTORE)
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())

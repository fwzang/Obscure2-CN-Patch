# -*- coding: utf-8 -*-
"""bump_v20.py — DLL 升级到 v20（一代 Reset 防御移植 + SSAA 图集），包仍 full11。"""
import os
import sys

D = r'D:\SteamLibrary\steamapps\common\Obscure2\Obscure2_Handover\deploy'
PROD = '5935534929c09f896c21c1baafffb42b'
PROD_P = 'bc12c6b1807272c8e9c858c7f3d97535'
DIAG = 'd3c6629b29fc7305000edd2d244de37f'
DIAG_P = '6259de67aaaa48378fbfe93b78a14390'


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
    ('set "MD5_DLL_PROD=bc12c6b1807272c8e9c858c7f3d97535"',
     'set "MD5_DLL_PROD=%s"\nset "MD5_DLL_PROD_P20=%s"' % (PROD, PROD_P)),
    ('set "MD5_DLL_DIAG=6259de67aaaa48378fbfe93b78a14390"',
     'set "MD5_DLL_DIAG=%s"\nset "MD5_DLL_DIAG_P20=%s"' % (DIAG, DIAG_P)),
    ('if /i "!H7!"=="!MD5_DLL_PROD_P19!" set "CURDLL=OURS_PROD"',
     'if /i "!H7!"=="!MD5_DLL_PROD_P20!" set "CURDLL=OURS_PROD"\n'
     'if /i "!H7!"=="!MD5_DLL_DIAG_P20!" set "CURDLL=OURS_DIAG"\n'
     'if /i "!H7!"=="!MD5_DLL_PROD_P19!" set "CURDLL=OURS_PROD"'),
    ('set "VER_DLL=v19"', 'set "VER_DLL=v20"'),
    ('set "VER_NOTE=20px atlas 2048x1024 MipLevels=1 + no point sampling + no Reset hook"',
     'set "VER_NOTE=20px SSAA(3x,BOX) atlas 2048x1024 MipLevels=1 + c47 unbind-before-Reset + dev-lost guard"'),
]

RESTORE = [
    ('set "MD5_DLL_PROD=bc12c6b1807272c8e9c858c7f3d97535"',
     'set "MD5_DLL_PROD=%s"\nset "MD5_DLL_PROD_P20=%s"' % (PROD, PROD_P)),
    ('set "MD5_DLL_DIAG=6259de67aaaa48378fbfe93b78a14390"',
     'set "MD5_DLL_DIAG=%s"\nset "MD5_DLL_DIAG_P20=%s"' % (DIAG, DIAG_P)),
    ('if /i "!HD!"=="!MD5_DLL_PROD_P19!" set "OWNOURS=1"',
     'if /i "!HD!"=="!MD5_DLL_PROD_P20!" set "OWNOURS=1"\n'
     'if /i "!HD!"=="!MD5_DLL_DIAG_P20!" set "OWNOURS=1"\n'
     'if /i "!HD!"=="!MD5_DLL_PROD_P19!" set "OWNOURS=1"'),
    ('set "VER_DLL=v19"', 'set "VER_DLL=v20"'),
]


def main():
    ok = patch('gate3_apply.bat', APPLY)
    ok &= patch('gate3_restore.bat', RESTORE)
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())

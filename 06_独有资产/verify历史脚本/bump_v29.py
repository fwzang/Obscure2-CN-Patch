# -*- coding: utf-8 -*-
"""bump_v29.py — DLL 升级到 v29（v21 判定 + RA/进出图集诊断）+ 包升级 full12（断行语料）。"""
import os
import sys

D = r'D:\SteamLibrary\steamapps\common\Obscure2\Obscure2_Handover\deploy'
PROD = 'df101b3e887e7fc9f9f7d9a4d3343d9a'
PROD_P = '6c0bb7777ce05371c98d6742e4df607c'      # v21（当前装机）
DIAG = '38f4981992cbac3309a3672eefb2be05'
DIAG_P = '4df858be253383980b04502f0e8262db'      # v21 diag
PACK = '2e07909f26bf6374592cd4ee5f866a2f'        # full12（断行语料）
PACK_P = 'c6faced4f4f60d5b2eb099e1688cc1ca'      # full11（当前装机）

OLD_NOTE = 'set "VER_NOTE=20px smooth + size allowlist AND hash blacklist + c47 + draw passthrough"'
NEW_NOTE = ('set "VER_NOTE=20px smooth + v21 swap behaviour + RA/diag logging '
            '+ c47 + draw passthrough"')


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
    ('set "MD5_DLL_PROD=411658c1453e6c8c7c4d15a011b7fd23"',
     'set "MD5_DLL_PROD=%s"\nset "MD5_DLL_PROD_P29=%s"' % (PROD, PROD_P)),
    ('set "MD5_DLL_DIAG=1bf95692faaaa899301dce453137602b"',
     'set "MD5_DLL_DIAG=%s"\nset "MD5_DLL_DIAG_P29=%s"' % (DIAG, DIAG_P)),
    ('set "PACKSRC=datapack_zh_full11.hvp"', 'set "PACKSRC=datapack_zh_full12.hvp"'),
    ('set "MD5_PACK_ZH=%s"' % PACK_P, 'set "MD5_PACK_ZH=%s"' % PACK),
    ('if /i "!H7!"=="!MD5_DLL_PROD_P28!" set "CURDLL=OURS_PROD"',
     'if /i "!H7!"=="!MD5_DLL_PROD_P29!" set "CURDLL=OURS_PROD"\n'
     'if /i "!H7!"=="!MD5_DLL_DIAG_P29!" set "CURDLL=OURS_DIAG"\n'
     'if /i "!H7!"=="!MD5_DLL_PROD_P28!" set "CURDLL=OURS_PROD"'),
    ('if /i "!H3!"=="!MD5_PACK_ZH_VB!" set "STATE=LEGACY_CN"',
     'if /i "!H3!"=="!MD5_PACK_ZH_P12!" set "STATE=LEGACY_CN"\n'
     'if /i "!H3!"=="!MD5_PACK_ZH_VB!" set "STATE=LEGACY_CN"'),
    ('set "MD5_PACK_ZH_VA=de85623a865f75c6bab55e495f8197f6"',
     'set "MD5_PACK_ZH_VA=de85623a865f75c6bab55e495f8197f6"\n'
     'set "MD5_PACK_ZH_P12=%s"' % PACK_P),
    ('set "VER_DLL=v28"', 'set "VER_DLL=v29"'),
    (OLD_NOTE, NEW_NOTE),
    ('set "DV=v28 PROD (this script\'s version)"', 'set "DV=v29 PROD (this script\'s version)"'),
    ('set "DV=v28 DIAG (this script\'s version)"', 'set "DV=v29 DIAG (this script\'s version)"'),
]

RESTORE = [
    ('set "MD5_DLL_PROD=411658c1453e6c8c7c4d15a011b7fd23"',
     'set "MD5_DLL_PROD=%s"\nset "MD5_DLL_PROD_P29=%s"' % (PROD, PROD_P)),
    ('set "MD5_DLL_DIAG=1bf95692faaaa899301dce453137602b"',
     'set "MD5_DLL_DIAG=%s"\nset "MD5_DLL_DIAG_P29=%s"' % (DIAG, DIAG_P)),
    # restore.bat 只从 gate3_orig 还原原版包，不含包 md5 变量
    ('if /i "!HD!"=="!MD5_DLL_PROD_P28!" set "OWNOURS=1"',
     'if /i "!HD!"=="!MD5_DLL_PROD_P29!" set "OWNOURS=1"\n'
     'if /i "!HD!"=="!MD5_DLL_DIAG_P28!" set "OWNOURS=1"\n'
     'if /i "!HD!"=="!MD5_DLL_PROD_P28!" set "OWNOURS=1"'),
    ('set "VER_DLL=v28"', 'set "VER_DLL=v29"'),
]


def main():
    ok = patch('gate3_apply.bat', APPLY)
    ok &= patch('gate3_restore.bat', RESTORE)
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())

# -*- coding: utf-8 -*-
"""backup_now.py — 保存现场：源码 / DLL / 构建脚本 / hvp 包 -> E:\\handover\\backups\\<ts>\\

绝不让一代 c93e 源码丢失的悲剧重演。同时产出 MANIFEST.md（含每个文件的 md5 与字节数）。
"""
import hashlib
import io
import os
import shutil
import sys
import time

ROOT = r'D:\SteamLibrary\steamapps\common\Obscure2\Obscure2_Handover'
GAME = r'D:\SteamLibrary\steamapps\common\Obscure2'
DEST_ROOT = r'E:\handover\backups'

TS = time.strftime('%Y%m%d_%H%M%S')
DEST = os.path.join(DEST_ROOT, TS)

# (子目录名, [(源路径, 目标相对名或 None)] 或 ('dir', 源目录, 目标子目录)
ITEMS = [
    ('src', [
        (os.path.join(ROOT, 'd3d9proxy_src', 'd3d9_proxy.c'), 'd3d9_proxy.c'),
        (os.path.join(ROOT, 'd3d9proxy_src', 'd3d9.def'), 'd3d9.def'),
        (os.path.join(ROOT, 'd3d9proxy_src', 'check_exports.py'), 'check_exports.py'),
        (os.path.join(ROOT, 'd3d9proxy_src', 'gen_atlas_header.py'), 'gen_atlas_header.py'),
    ]),
    ('src_header', [
        (os.path.join(ROOT, 'd3d9proxy_src', 'atlas_png.h'), 'atlas_png.h'),
    ]),
    ('dll', 'dir', os.path.join(ROOT, 'd3d9proxy_src'), '.dll'),
    ('scripts_gate3', 'dir', os.path.join(ROOT, 'scripts_gate3'), '.py'),
    ('verify', 'dir', os.path.join(ROOT, '_verify'), '.py'),
    ('packs', 'dir', os.path.join(ROOT, 'deploy'), '.hvp'),
    ('bat', 'dir', os.path.join(ROOT, 'deploy'), '.bat'),
    ('atlas', [
        (os.path.join(ROOT, '_work', 'g4', 'g3_atlas.png'), 'g3_atlas.png'),
        (os.path.join(ROOT, '_work', 'g4', 'g3_font_nonserif12.xmc'), 'g3_font_nonserif12.xmc'),
        (os.path.join(ROOT, '_work', 'g4', 'g3_layout.tsv'), 'g3_layout.tsv'),
        (os.path.join(ROOT, '_work', 'g4', 'atlas_A.png'), 'atlas_A.png'),
        (os.path.join(ROOT, '_work', 'g4', 'atlas_B.png'), 'atlas_B.png'),
        (os.path.join(ROOT, '_work', 'g4', 'atlas_FINAL20.png'), 'atlas_FINAL20.png'),
        (os.path.join(ROOT, '_work', 'g4', 'atlas_ALT22.png'), 'atlas_ALT22.png'),
        (os.path.join(ROOT, '_work', 'g4', 'def_ALT22.xmc'), 'def_ALT22.xmc'),
    ]),
    ('text', [
        (os.path.join(ROOT, '_work', 'o2_text_zh_full13.tsv'), 'o2_text_zh_full13.tsv'),
        (os.path.join(ROOT, 'deploy', 'README_TEST.md'), 'README_TEST.md'),
    ]),
    ('memory', 'dir', os.path.join(GAME, '.workbuddy', 'memory'), '.md'),
    ('fonts', 'dir', os.path.join(ROOT, '_work', 'fonts'), ''),
    ('orig_baseline', [
        (os.path.join(ROOT, '基线_原版', 'datapack.hvp.gate3_orig'), 'datapack.hvp.gate3_orig'),
        (os.path.join(GAME, 'options.xml'), 'options.xml'),
    ]),
]


def md5_of(path):
    h = hashlib.md5()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def main():
    os.makedirs(DEST, exist_ok=True)
    manifest = ['# 备份清单 MANIFEST', '',
                '生成时间: %s' % time.strftime('%Y-%m-%d %H:%M:%S'),
                '来源工程: %s' % ROOT,
                '游戏目录: %s' % GAME, '',
                '| 分类 | 文件 | 字节 | md5 |', '|---|---|---|---|']

    for item in ITEMS:
        if item[1] == 'dir':
            _, _, srcdir, ext = item
            sub = os.path.join(DEST, item[0])
            os.makedirs(sub, exist_ok=True)
            if not os.path.isdir(srcdir):
                continue
            for name in sorted(os.listdir(srcdir)):
                if not name.lower().endswith(ext):
                    continue
                src = os.path.join(srcdir, name)
                if not os.path.isfile(src):
                    continue
                dst = os.path.join(sub, name)
                shutil.copy2(src, dst)
                manifest.append('| %s | %s | %d | `%s` |' % (item[0], name, os.path.getsize(dst),
                                                             md5_of(dst)))
                print('  + %s/%s' % (item[0], name))
        else:
            sub = os.path.join(DEST, item[0])
            os.makedirs(sub, exist_ok=True)
            for src, name in item[1]:
                if not os.path.isfile(src):
                    print('  - 跳过(不存在): %s' % src)
                    continue
                dst = os.path.join(sub, name)
                shutil.copy2(src, dst)
                manifest.append('| %s | %s | %d | `%s` |' % (item[0], name, os.path.getsize(dst),
                                                             md5_of(dst)))
                print('  + %s/%s' % (item[0], name))

    mp = os.path.join(DEST, 'MANIFEST.md')
    io.open(mp, 'w', encoding='utf-8', newline='\n').write('\n'.join(manifest) + '\n')
    print('[OK] 备份完成: %s' % DEST)
    return 0


if __name__ == '__main__':
    sys.exit(main())

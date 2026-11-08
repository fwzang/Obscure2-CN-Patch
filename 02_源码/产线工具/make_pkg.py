# -*- coding: utf-8 -*-
"""make_pkg.py — 打包 full4 一键测试包（ZIP_STORED, 不压缩, 最快）"""
import hashlib
import os
import sys
import zipfile

DEPLOY = r'D:\SteamLibrary\steamapps\common\Obscure2\Obscure2_Handover\deploy'
OUT = r'D:\SteamLibrary\steamapps\common\Obscure2\Obscure2_Handover\Obscure2_Gate3_full11_v28_BLACKLIST.zip'

FILES = [
    ('gate3_apply.bat', True),
    ('gate3_restore.bat', True),
    ('gate3_check.bat', True),
    ('gate3_diag.bat', True),
    ('gate3_prod.bat', True),
    ('gate3_vanilla.bat', True),
    ('d3d9.dll', True),
    ('d3d9_diag.dll', True),
    ('datapack_zh_full11.hvp', True),
    ('README_TEST.md', False),
    ('实机测试_操作清单.md', False),
    ('g3_atlas.png', False),
    ('g3_font_nonserif12.xmc', False),
    ('g3_atlas_report.txt', False),
    ('g3_def_report.txt', False),
    ('simline.png', False),
    ('compare_AB_2.7x.png', False),
    ('d3d9_v21_fallback.dll', False),
    ('sharpen_compare.png', False),
]

MANIFEST = []


def md5(p):
    h = hashlib.md5()
    with open(p, 'rb') as f:
        while True:
            b = f.read(1 << 20)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def consistency_gate():
    """打包前强制一致性校验：图集 PNG / def atlas token / DLL 内嵌 PNG / 字形盒范围。"""
    import subprocess, sys
    r = subprocess.run([sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        'verify_pack.py')], capture_output=True, text=True)
    sys.stdout.write(r.stdout)
    if r.returncode != 0:
        raise SystemExit('[ABORT] 一致性校验未通过，已中止打包')


def main():
    miss = [n for n, _ in FILES if not os.path.exists(os.path.join(DEPLOY, n))]
    if miss:
        print('[ERR] 缺少文件: %s' % miss)
        return 1
    consistency_gate()
    tmp = OUT + '.part'
    with zipfile.ZipFile(tmp, 'w', zipfile.ZIP_STORED, allowZip64=True) as z:
        for name, _ in FILES:
            p = os.path.join(DEPLOY, name)
            sz = os.path.getsize(p)
            d = md5(p)
            MANIFEST.append((name, sz, d))
            print('  + %-32s %12d  %s' % (name, sz, d))
            z.write(p, name)
        m = '手册与校验值.txt'
        lines = ['Obscure II 汉化 Gate3 full4 测试包', '=' * 60, '']
        lines.append('字体: 寒蝉活楷体 20px 原样AA  盒 19x25  DLL v20 c47防线+SSAA + 版本自检 + 一致性校验')
        lines.append('译文: 无妥协完整版, 原始文本注入 (无自动换行)')
        lines.append('')
        lines.append('%-34s %12s  %s' % ('文件', '字节', 'md5'))
        for name, sz, d in MANIFEST:
            lines.append('%-34s %12d  %s' % (name, sz, d))
        lines.append('')
        lines.append('安装: 双击 gate3_apply.bat   (首次建议先 .\\gate3_apply.bat DIAG)')
        lines.append('还原: 双击 gate3_vanilla.bat')
        lines.append('查询: 双击 gate3_check.bat   (只读, 报告装的是哪一版)')
        z.writestr(m, ('\r\n'.join(lines) + '\r\n').encode('utf-8-sig'))
    os.replace(tmp, OUT)
    print()
    print('[OK] %s' % OUT)
    print('     %d B (%.1f MB)' % (os.path.getsize(OUT), os.path.getsize(OUT) / 1048576.0))
    return 0


if __name__ == '__main__':
    sys.exit(main())

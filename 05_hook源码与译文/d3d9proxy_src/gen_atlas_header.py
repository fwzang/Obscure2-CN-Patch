# -*- coding: utf-8 -*-
"""gen_atlas_header.py — 把 g3_atlas.png 转成 C 数组(atlas_png.h)供 DLL 内嵌。

用法: python gen_atlas_header.py
输入: ../_work/g4/g3_atlas.png  (gate3_atlas.py 产物, 4096x2048 RGBA PNG)
输出: atlas_png.h                (g_atlasPng[] / g_atlasPngLen)
"""
import hashlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..'))
SRC = os.path.join(ROOT, '_work', 'g4', 'g3_atlas.png')
DST = os.path.join(HERE, 'atlas_png.h')


def main():
    if not os.path.exists(SRC):
        print('[ERR] 找不到 %s' % SRC)
        return 1
    data = open(SRC, 'rb').read()
    md5 = hashlib.md5(data).hexdigest()
    with open(DST, 'w', newline='\n') as f:
        f.write('/* atlas_png.h - 自动生成, 勿手改\n')
        f.write(' * 源: recon/gate3/g3_atlas.png (%d bytes, md5 %s)\n' % (len(data), md5))
        f.write(' * 生成: gen_atlas_header.py\n')
        f.write(' * 注意: PNG 为 RGBA 预乘双通道( RGB=232*alpha/255 ),\n')
        f.write(' *       D3DX 解码后直接得到引擎期望的 A8R8G8B8 显存格式。\n')
        f.write(' */\n')
        f.write('static const unsigned char g_atlasPng[] = {\n')
        for i in range(0, len(data), 20):
            chunk = data[i:i + 20]
            f.write('  ' + ','.join('0x%02X' % b for b in chunk) + ',\n')
        f.write('};\n')
        f.write('static const unsigned int g_atlasPngLen = %d;\n' % len(data))
    print('[OK] %s (%d B -> %d B, md5 %s)' % (DST, len(data),
          os.path.getsize(DST), md5))
    return 0


if __name__ == '__main__':
    sys.exit(main())

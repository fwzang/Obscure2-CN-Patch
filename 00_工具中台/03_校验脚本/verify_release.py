# -*- coding: utf-8 -*-
"""verify_release.py — 交付包开工完整性核验

用途：确认「后续能直接开工」所需的全部资源都在，且关键产物指纹正确。
用法：python 00_工具中台/03_校验脚本/verify_release.py [交付包根目录]
      不给参数时自动按本脚本位置向上两级推断包根。
"""
import hashlib
import os
import sys

EXE_MD5 = 'dd987884b3cfa2a585073f7d1f6859a9'
DLL_A = '1e2a38adac855179119ff4f4fd567622'
DLL_B = 'b42417bd2a51ff5d95d3a84970b8a20f'
DLT_B = 'ce74adb362a7593385713cb5f9e1c23e'
DLT_A = '249aa200089dcb67ff1a7fcdc6d9acf9'

CHECKS = [
    ('发布物', '01_安装包/Obscure2_汉化补丁_V1.04.exe', EXE_MD5, '安装包'),
    ('发布物', '01_安装包/免责声明与说明.txt', None, '玩家说明'),
    ('发布物', '01_安装包/手动安装版/d3d9.dll', DLL_B, '方案B 代理'),
    ('发布物', '01_安装包/手动安装版/方案A_寒蝉端黑体/d3d9.dll', DLL_A, '方案A 代理'),
    ('发布物', '01_安装包/手动安装版/datapack.delta', DLT_B, '方案B 差分'),
    ('发布物', '01_安装包/手动安装版/方案A_寒蝉端黑体/datapack_a.delta', DLT_A, '方案A 差分'),
    ('发布物', '01_安装包/手动安装版/apply_delta.py', None, '差分应用器'),
    ('发布物', '01_安装包/手动安装版/install.bat', None, '手动装 B'),
    ('发布物', '01_安装包/手动安装版/方案A_寒蝉端黑体/install_A.bat', None, '手动装 A'),
    ('发布物', '01_安装包/手动安装版/restore.bat', None, '手动还原'),
    ('编译链', '00_工具中台/01_编译链/w64devkit-2.10.1-gcc16.2.0.zip', None, '编译器'),
    ('构建脚本', '00_工具中台/02_构建脚本/build_from_package.py', None, '一条命令重建 DLL'),
    ('校验脚本', '00_工具中台/03_校验脚本/check_exports.py', None, '导出校验'),
    ('诊断工具', '00_工具中台/04_诊断脚本/probe_on12.exe', None, 'On12 探针'),
    ('诊断工具', '00_工具中台/04_诊断脚本/probe_proxy_dev.exe', None, '全链路探针'),
    ('诊断工具', '00_工具中台/04_诊断脚本/2_remove_dll.bat', None, '卸代理'),
    ('诊断工具', '00_工具中台/04_诊断脚本/7_collect_log.bat', None, '收日志'),
    ('hook 源码', '05_hook源码与译文/d3d9proxy_src/d3d9_proxy.c', None, 'V87_PROD 源码'),
    ('hook 源码', '05_hook源码与译文/d3d9proxy_src/d3d9.def', None, '导出定义'),
    ('hook 源码', '05_hook源码与译文/d3d9proxy_src/atlas_png.h', None, '内嵌图集头'),
    ('安装器源码', '02_源码/安装器/setup.c', None, 'UI + 安装逻辑'),
    ('安装器源码', '02_源码/安装器/info_o2.txt', None, '首屏文案'),
    ('安装器源码', '02_源码/安装器/build_installer.py', None, '打包脚本'),
    ('安装器源码', '02_源码/安装器/gen_info.py', None, '文案→头文件'),
    ('基线', '04_基线与回滚/datapack.hvp.vanilla', None, '原版数据包'),
    ('素材', '06_独有资产/方案A_字体产物/g3_atlas.png', None, '方案A 图集'),
    ('素材', '06_独有资产/方案A_字体产物/g3_font_nonserif12.xmc', None, '方案A def'),
    ('素材', '06_独有资产/方案A_字体产物/datapack_a.delta', None, '方案A 差分'),
    ('译文', '05_hook源码与译文/译文真源/o2_text_zh_full13.tsv', None, '译文真源'),
    ('文档', 'README.md', None, '开工总入口'),
    ('文档', '新手接手指南.md', None, '三条动作'),
    ('文档', '03_文档/V1.04_发版说明.md', None, '本版全记录'),
    ('文档', '03_文档/排障手册.md', None, '排障'),
    ('文档', '03_文档/汉化补丁V1.00_总结与流程报告.md', None, '六层流程图'),
    ('文档', '03_文档/字体方案AB_生成与验证报告.md', None, '字体复现'),
    ('文档', '03_文档/方案A_B_数据一致性核验报告.md', None, 'A/B 一致性'),
    ('文档', 'MD5.txt', None, '全包台账'),
]


def md5(p):
    h = hashlib.md5()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def main():
    if len(sys.argv) > 1:
        pkg = sys.argv[1]
    else:
        here = os.path.dirname(os.path.abspath(__file__))
        pkg = os.path.dirname(os.path.dirname(here))
    if not os.path.isdir(pkg):
        print('[ERROR] 交付包根目录不存在: %s' % pkg)
        return 1

    fails = []
    print('=' * 76)
    print('交付包开工完整性核验  |  %s' % pkg)
    print('=' * 76)
    cur = ''
    for grp, rel, exp, desc in CHECKS:
        if grp != cur:
            cur = grp
            print('\n[%s]' % grp)
        p = os.path.join(pkg, rel.replace('/', os.sep))
        if not os.path.exists(p):
            print('  X 缺失  %-50s %s' % (rel, desc))
            fails.append((rel, 'MISSING'))
            continue
        sz = os.path.getsize(p)
        if exp:
            h = md5(p)
            if h != exp:
                print('  X md5错 %-50s %s' % (rel, desc))
                fails.append((rel, 'MD5 %s' % h[:12]))
                continue
            print('  OK %-50s %9d B  md5 已核对' % (rel, sz))
        else:
            print('  OK %-50s %9d B  %s' % (rel, sz, desc))

    tot = fn = 0
    for base, dirs, files in os.walk(pkg):
        dirs[:] = [d for d in dirs if d != '__pycache__']
        for f in files:
            fn += 1
            tot += os.path.getsize(os.path.join(base, f))
    print('\n' + '=' * 76)
    print('包体: %d 个文件 / %.2f GB' % (fn, tot / (1 << 30)))
    if fails:
        print('结果: %d 项未通过' % len(fails))
        for rel, why in fails:
            print('   - %s (%s)' % (rel, why))
        return 1
    print('结果: 全部通过 —— 后续可直接开工')
    print('=' * 76)
    return 0


if __name__ == '__main__':
    sys.exit(main())

# -*- coding: utf-8 -*-
"""自检.py — 一条命令确认「开工要用的东西一样不缺」。

用法（在交付包根目录）：
    python 00_工具中台/自检.py

检查四类：
  1. 发布物        —— 安装包（当前版 + 历史版本）/ 两套 DLL / 数据包，校验 md5
  2. 开工工具链    —— 编译器 zip、构建脚本、安装器源码与载荷、校验脚本、诊断 bat
  3. 资料与源文件  —— 字体源、产线脚本、文档、源码
  4. 历史留档      —— hook快照 / 每版产物 / 补丁脚本 / 源码快照（回溯用，不参与构建）

输出 PASS/FAIL 清单；有任何 MISS/MISMATCH 都会在末尾汇总。
"""
import hashlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))          # 00_工具中台
PKG = os.path.dirname(HERE)                                # 交付包根


def md5(p):
    h = hashlib.md5()
    with open(p, 'rb') as f:
        for c in iter(lambda: f.read(1 << 20), b''):
            h.update(c)
    return h.hexdigest()


# (相对路径, 期望 md5 或 None 只查存在, 分组)
ITEMS = [
    # ---------- 发布物 ----------
    (r"01_安装包\Obscure2_汉化补丁_V1.04.exe", "7146f4ec97258de8f554ea610809a902", "发布物"),
    (r"01_安装包\历史版本安装包\Obscure2_汉化补丁_V1.03.1.exe", "d22f6d5cc255f90f349cbf46bc6d7db5", "发布物"),
    (r"01_安装包\历史版本安装包\Obscure2_汉化补丁_V1.03.exe", "103ce34df142ad2247d252379381b57d", "发布物"),
    (r"01_安装包\历史版本安装包\Obscure2_汉化补丁_V1.02.exe", "1867f08aa805316c3607251897bae202", "发布物"),
    (r"01_安装包\历史版本安装包\Obscure2_汉化补丁_V1.01.exe", "05042f145a4bf8d151cdc371b316a928", "发布物"),
    (r"01_安装包\手动安装版\d3d9.dll", "b42417bd2a51ff5d95d3a84970b8a20f", "发布物"),
    (r"01_安装包\手动安装版\方案A_寒蝉端黑体\d3d9.dll", "1e2a38adac855179119ff4f4fd567622", "发布物"),
    (r"01_安装包\手动安装版\datapack.delta", "ce74adb362a7593385713cb5f9e1c23e", "发布物"),
    (r"01_安装包\手动安装版\datapack_zh_full18.hvp", "d25123d226ebd1dfae39c053717db808", "发布物"),
    (r"01_安装包\手动安装版\方案A_寒蝉端黑体\datapack.hvp", "e657e90dcfe225da3af5b19e394f5622", "发布物"),
    (r"01_安装包\免责声明与说明.txt", None, "发布物"),

    # ---------- 开工：编译 ----------
    (r"00_工具中台\01_编译链\w64devkit-2.10.1-gcc16.2.0.zip", "781b59607b1969805986de9b29a634f0", "开工·编译"),
    (r"00_工具中台\01_编译链\解压工具链.bat", None, "开工·编译"),
    (r"00_工具中台\一键自检.bat", None, "开工·编译"),
    (r"00_工具中台\selfcheck.py", None, "开工·编译"),
    (r"00_工具中台\02_构建脚本\build_from_package.py", None, "开工·编译"),

    # ---------- 开工：DLL 源码 ----------
    (r"05_hook源码与译文\d3d9proxy_src\d3d9_proxy.c", None, "开工·源码"),
    (r"05_hook源码与译文\d3d9proxy_src\atlas_png.h", None, "开工·源码"),
    (r"05_hook源码与译文\d3d9proxy_src\d3d9.def", None, "开工·源码"),

    # ---------- 开工：安装器 ----------
    (r"02_源码\安装器\setup.c", None, "开工·安装器"),
    (r"02_源码\安装器\setup.rc", None, "开工·安装器"),
    (r"02_源码\安装器\info_o2.txt", None, "开工·安装器"),
    (r"02_源码\安装器\gen_info.py", None, "开工·安装器"),
    (r"02_源码\安装器\build_all.py", None, "开工·安装器"),
    (r"02_源码\安装器\build_installer.py", None, "开工·安装器"),
    (r"02_源码\安装器\payload\dinput8.dll", "4d25503a50bbf5345a7a86e19c373e1a", "开工·安装器"),
    (r"02_源码\安装器\payload\main.patch", "a7838aa538e75b28cf0e4500c755a7a4", "开工·安装器"),

    # ---------- 开工：校验 ----------
    (r"00_工具中台\03_校验脚本\check_exports.py", None, "开工·校验"),
    (r"00_工具中台\03_校验脚本\regen_md5_v101.py", None, "开工·校验"),

    # ---------- 开工：诊断 ----------
    (r"00_工具中台\04_诊断脚本\1_install_release.bat", None, "开工·诊断"),
    (r"00_工具中台\04_诊断脚本\2_remove_dll.bat", None, "开工·诊断"),
    (r"00_工具中台\04_诊断脚本\3_control_no_proxy.bat", None, "开工·诊断"),
    (r"00_工具中台\04_诊断脚本\4_no_atlas_swap.bat", None, "开工·诊断"),
    (r"00_工具中台\04_诊断脚本\5_no_ui_fix.bat", None, "开工·诊断"),
    (r"00_工具中台\04_诊断脚本\6_exclusive_fullscreen.bat", None, "开工·诊断"),
    (r"00_工具中台\04_诊断脚本\7_collect_log.bat", None, "开工·诊断"),
    (r"00_工具中台\04_诊断脚本\8_promote_fast.bat", None, "开工·诊断"),
    (r"00_工具中台\04_诊断脚本\d3d9_release.dll", "b42417bd2a51ff5d95d3a84970b8a20f", "开工·诊断"),

    # ---------- 开工：产线 ----------
    (r"02_源码\产线工具\gate3_atlas.py", None, "开工·产线"),
    (r"02_源码\产线工具\gate3_atlas_A.py", None, "开工·产线"),
    (r"02_源码\产线工具\gate3_atlas_B.py", None, "开工·产线"),
    (r"02_源码\产线工具\gate3_def.py", None, "开工·产线"),
    (r"02_源码\产线工具\gate3_def_A.py", None, "开工·产线"),
    (r"02_源码\产线工具\gate3_def_B.py", None, "开工·产线"),
    (r"02_源码\产线工具\ta2_write.py", None, "开工·产线"),
    (r"02_源码\产线工具\verify_pack.py", None, "开工·产线"),
    (r"02_源码\安装器\make_delta.py", None, "开工·产线"),

    # ---------- 资料 ----------
    (r"05_hook源码与译文\字体源\ChillDuanSans_Bold.otf", None, "资料·字体"),
    (r"05_hook源码与译文\字体源\ChillHuoKai_Regular.otf", None, "资料·字体"),
    (r"06_独有资产\方案A_字体产物\g3_atlas.png", "22ffed606c669be5043668d8b29ae2ef", "资料·产物"),
    (r"06_独有资产\方案A_字体产物\g3_font_nonserif12.xmc", "89e4e7a41ab470258b8f44fea96f901e", "资料·产物"),
    (r"04_基线与回滚\datapack.hvp.vanilla", "04a96eff7978cf31e66e9354421f1516", "资料·基线"),
    (r"05_hook源码与译文\译文真源\o2_text_zh_full13.tsv", "0072ced4a462cecc45734cc9119da104", "资料·译文"),

    # ---------- 历史留档（回溯用，不参与构建） ----------
    (r"06_独有资产\hook快照\README.md", None, "历史·版本DLL"),
    (r"06_独有资产\hook快照\d3d9_v49.dll", None, "历史·版本DLL"),
    (r"06_独有资产\out历史\out_B", None, "历史·每版产物"),
    (r"06_独有资产\verify历史脚本", None, "历史·补丁脚本"),
    (r"06_独有资产\历史文档_归档.zip", None, "历史·阶段报告"),
    (r"05_hook源码与译文\d3d9proxy_src\_archive\d3d9_v28_blacklist.dll", None, "历史·源码快照"),
    (r"05_hook源码与译文\d3d9proxy_src\_archive\d3d9_proxy_v49_package.c", None, "历史·源码快照"),
    (r"05_hook源码与译文\d3d9proxy_src\d3d9_proxy.c.bak_v47", None, "历史·源码快照"),
    (r"02_源码\产线工具\_archive\gate3_atlas.py", None, "历史·产线脚本"),

    # ---------- 文档 ----------
    (r"README.md", None, "文档"),
    (r"新手接手指南.md", None, "文档"),
    (r"03_文档\排障手册.md", None, "文档"),
    (r"03_文档\V1.04_发版说明.md", None, "文档"),
    (r"07_项目记忆\MEMORY.md", None, "文档"),
    (r"06_独有资产\历史资料索引.md", None, "文档"),
    (r"00_工具中台\README.md", None, "文档"),
]


def main():
    print("交付包自检：%s" % PKG)
    print("=" * 78)
    fails, groups = [], {}
    for rel, want, grp in ITEMS:
        p = os.path.join(PKG, rel)
        ok = os.path.exists(p)
        note = ""
        if not ok:
            note = "MISS 文件不存在"
            fails.append((rel, note))
        elif want:
            got = md5(p)
            if got != want:
                note = "MISMATCH %s (期望 %s)" % (got, want)
                fails.append((rel, note))
            else:
                note = "ok"
        else:
            note = "ok"
        groups.setdefault(grp, []).append((rel, note))

    for grp in ["发布物", "开工·编译", "开工·源码", "开工·安装器", "开工·校验",
                "开工·诊断", "开工·产线", "资料·字体", "资料·产物", "资料·基线",
                "资料·译文", "历史·版本DLL", "历史·每版产物", "历史·补丁脚本",
                "历史·阶段报告", "历史·源码快照", "历史·产线脚本", "文档"]:
        if grp not in groups:
            continue
        items = groups[grp]
        bad = sum(1 for _, n in items if n != "ok")
        print("\n[%s]  %d 项%s" % (grp, len(items), "" if bad == 0 else "  ← %d 项异常" % bad))
        for rel, note in items:
            mark = "  OK  " if note == "ok" else "  !!  "
            print("%s%-58s %s" % (mark, rel, "" if note == "ok" else note))

    print("\n" + "=" * 78)
    if not fails:
        print("结果：全部齐备 ✅  可以直接开工")
        print("\n下一步：")
        print("  改 DLL      → 00_工具中台\\01_编译链\\解压工具链.bat")
        print("                 python 00_工具中台\\02_构建脚本\\build_from_package.py")
        print("  重出安装包  → python 02_源码\\安装器\\build_all.py")
        print("  校验        → python 00_工具中台\\03_校验脚本\\regen_md5_v101.py")
        print("  排障        → 03_文档\\排障手册.md")
        return 0
    print("结果：%d 项异常 ❌" % len(fails))
    for rel, note in fails:
        print("  - %s : %s" % (rel, note))
    return 1


if __name__ == "__main__":
    sys.exit(main())

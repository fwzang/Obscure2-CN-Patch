# -*- coding: utf-8 -*-
"""cleanup_pkg_v101.py — 交付包文档清理：保留有用工具/流程/报告，过程性旧文档归档打包后删除。"""
import os
import zipfile

PKG = r"E:\ObsCure2汉化项目_v1.01_完整交付包_2026-10-22"
DOC = os.path.join(PKG, "03_文档")
ZIP = os.path.join(PKG, r"06_独有资产\历史文档_归档.zip")

ARCHIVE = [
    "v40_DIAG_调用栈诊断交付报告.md",
    "分页写入UT方案_可行性报告_2026-10-20.md",
    "阶段复盘报告_2026-10-19.md",
    "清理后_剩余空间报告.md",
    "流程文件盘点与删减判定表.md",
    r"技术分析\交接跟进_状态报告.md",
    r"技术分析\Obscure II 汉化可行性初步报告.md",
    r"技术分析\全量汉字图集生成方案评估.md",
]

NOTE = """历史文档归档说明（2026-10-22）
=====================================
本包收录 V1.00/V1.01 开发过程中的过程性文档：阶段性诊断、被证伪方案评估、
复盘与空间清理报告等。它们不影响当前使用与二次开发，仅作历史留档。

当前有效的工具、流程与报告请见 03_文档/ 与 02_源码/：
  · 流程：中台资源与流程报告、装配树_使用说明、V1.01_修改说明
  · 技术：汉化补丁V1.00_总结与流程报告、字体方案AB_生成与验证报告、
          V1.01_修复说明、文本完整性最终验收报告、break_word_report、
          CONFIG复现验证
  · 工具：02_源码/产线工具（gate3 五件套 + 打包器 + 校验关卡 + 字体方案变体）

归档清单：
"""


def main():
    files = [f for f in ARCHIVE if os.path.exists(os.path.join(DOC, f))]
    missing = [f for f in ARCHIVE if not os.path.exists(os.path.join(DOC, f))]
    print("待归档 %d 个；缺失 %s" % (len(files), missing or "无"))

    with zipfile.ZipFile(ZIP, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("归档说明.txt", NOTE + "\n".join("  " + f for f in files) + "\n")
        total = 0
        for f in files:
            p = os.path.join(DOC, f)
            z.write(p, f.replace(os.sep, "/"))
            total += os.path.getsize(p)
            print("  + %-42s %7d B" % (f, os.path.getsize(p)))
    print("[OK] %s (%d B, 压缩前合计 %d B)" % (ZIP, os.path.getsize(ZIP), total))

    for f in files:
        os.remove(os.path.join(DOC, f))
    print("[OK] 已从 03_文档 删除 %d 个旧文档" % len(files))

    n = 0
    tot = 0
    for root, dirs, fs in os.walk(PKG):
        for f in fs:
            p = os.path.join(root, f)
            n += 1
            tot += os.path.getsize(p)
    print("包内现在：%d 文件，%.2f GB" % (n, tot / 1073741824.0))


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""构建 V1.00 完整交付包（七区结构，对齐 V1.01 交付包；合并原 patch2 补装逻辑）。

V1.00 基线：exe 8391340e / full18 d25123d2 / delta ce74adb3 / dll v49 47060c4b
"""
import os, shutil, hashlib, io

SRC = r"D:\SteamLibrary\steamapps\common\Obscure2\Obscure2_Handover"
GAME = r"D:\SteamLibrary\steamapps\common\Obscure2"
DST = r"D:\ObsCure2汉化项目_v1.00_完整交付包_2026-10-21"
PKG = os.path.join(SRC, r"_verify\_pkg_v100")

n = [0]; bytes_moved = [0]

def md5(p):
    h = hashlib.md5()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()

def cp(src, dst):
    if not os.path.exists(src):
        print("  [MISS] %s" % src); return
    d = os.path.dirname(dst)
    if d and not os.path.isdir(d):
        os.makedirs(d)
    shutil.copy2(src, dst)
    n[0] += 1
    bytes_moved[0] += os.path.getsize(dst)

def cpdir(srcdir, dstdir, pattern=None, skip=()):
    if not os.path.isdir(srcdir):
        print("  [MISS DIR] %s" % srcdir); return
    for root, dirs, files in os.walk(srcdir):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        rel = os.path.relpath(root, srcdir)
        for f in files:
            if pattern and not pattern(f):
                continue
            if f in skip or f.endswith((".pyc", ".bak")):
                continue
            s = os.path.join(root, f)
            d = os.path.join(dstdir, rel, f) if rel != "." else os.path.join(dstdir, f)
            cp(s, d)

print("=== 01_安装包 ===")
cp(os.path.join(SRC, r"installer\Obscure2_汉化补丁_V1.00.exe"),
   os.path.join(DST, r"01_安装包\Obscure2_汉化补丁_V1.00.exe"))
# 手动安装版（v49 / full18，已沙箱验证）
cp(os.path.join(SRC, r"release_v49_full18\d3d9.dll"),
   os.path.join(DST, r"01_安装包\手动安装版\d3d9.dll"))
cp(os.path.join(SRC, r"deploy\datapack.delta"),
   os.path.join(DST, r"01_安装包\手动安装版\datapack.delta"))
cp(os.path.join(SRC, r"deploy\datapack_zh_full18.hvp"),
   os.path.join(DST, r"01_安装包\手动安装版\datapack_zh_full18.hvp"))
cp(os.path.join(SRC, r"release_v49_full18\apply.bat"),
   os.path.join(DST, r"01_安装包\手动安装版\apply.bat"))
cp(os.path.join(SRC, r"release_v49_full18\还原原版.bat"),
   os.path.join(DST, r"01_安装包\手动安装版\还原原版.bat"))
cp(os.path.join(PKG, "manual_README.md"),
   os.path.join(DST, r"01_安装包\手动安装版\README.md"))
# 免责声明（安装器弹窗文案的纯文本版，与安装包内一致）
cp(os.path.join(SRC, r"installer\info_o2.txt"),
   os.path.join(DST, r"01_安装包\免责声明与说明.txt"))

print("=== 02_源码 ===")
cpdir(os.path.join(SRC, "scripts_gate3"), os.path.join(DST, r"02_源码\产线工具"),
      pattern=lambda f: f.endswith(".py"))
cp(os.path.join(SRC, r"tools\obscure-hvp.exe"),
   os.path.join(DST, r"02_源码\产线工具\obscure-hvp.exe"))
for f in ["verify_pack.py", "make_pkg.py", "backup_now.py", "fix_break_words.py",
          "verify_exe_payload.py", "apply_delta_check.py", "parse_delta_hdr.py",
          "sandbox_test_v100_manual.py", "build_deliverable_v100.py", "regen_md5_v100.py"]:
    cp(os.path.join(SRC, "_verify", f), os.path.join(DST, r"02_源码\产线工具", f))
cpdir(os.path.join(SRC, "installer"), os.path.join(DST, r"02_源码\安装器"),
      pattern=lambda f: f.endswith((".c", ".py", ".rc", ".ico", ".txt", ".h", ".md", ".bat"))
                        or f == "app.ico",
      skip=("Obscure2_汉化补丁_V1.00.exe", "Obscure2_汉化补丁_V1.02.exe",
            "Obscure2_汉化补丁_V1.02_字体修复.exe", "setup.exe"))

print("=== 03_文档 ===")
docs = [
    "汉化补丁V1.00_总结与流程报告.md",
    "中台资源与流程报告.md",
    "V1.01_修复说明_移除调试导出代码.md",
    "文本完整性最终验收报告.md",
    "v45_残余风险评估与兜底流程.md",
    "v40_DIAG_调用栈诊断交付报告.md",
    "分页写入UT方案_可行性报告_2026-10-20.md",
    "阶段复盘报告_2026-10-19.md",
    "清理后_剩余空间报告.md",
    "流程文件盘点与删减判定表.md",
]
for d in docs:
    cp(os.path.join(SRC, d), os.path.join(DST, "03_文档", d))
cp(os.path.join(PKG, "V1.00_修改说明.md"),
   os.path.join(DST, r"03_文档\V1.00_修改说明.md"))
cp(os.path.join(SRC, r"_verify\CONFIG复现验证_图集20px.md"),
   os.path.join(DST, r"03_文档\CONFIG复现验证_图集20px.md"))
cp(os.path.join(SRC, r"_verify\break_word_report.md"),
   os.path.join(DST, r"03_文档\break_word_report.md"))
cpdir(os.path.join(SRC, "docs"), os.path.join(DST, r"03_文档\技术分析"))

print("=== 04_基线与回滚 ===")
cp(os.path.join(SRC, r"基线_原版\datapack.hvp.gate3_orig"),
   os.path.join(DST, r"04_基线与回滚\datapack.hvp.vanilla"))
cp(os.path.join(SRC, r"deploy\g3_atlas.png"),
   os.path.join(DST, r"04_基线与回滚\g3_atlas.png"))

print("=== 05_hook源码与译文 ===")
for f in ["d3d9_proxy.c", "d3d9.def", "atlas_png.h", "gen_atlas_header.py",
          "check_exports.py", "build.bat", "d3d9_proxy.c.bak_v47", "README.md"]:
    cp(os.path.join(SRC, "d3d9proxy_src", f),
       os.path.join(DST, r"05_hook源码与译文\d3d9proxy_src", f))
cpdir(os.path.join(SRC, r"d3d9proxy_src\_archive"),
      os.path.join(DST, r"05_hook源码与译文\d3d9proxy_src\_archive"))
# 译文真源 + 迭代链
cp(os.path.join(SRC, r"_work\o2_text_zh_full13.tsv"),
   os.path.join(DST, r"05_hook源码与译文\译文真源\o2_text_zh_full13.tsv"))
cpdir(os.path.join(SRC, r"_archive_小件\语料_历史"),
      os.path.join(DST, r"05_hook源码与译文\译文真源\历史迭代"))
# 图集 / 字形表 / 字体源
cp(os.path.join(SRC, r"deploy\g3_font_nonserif12.xmc"),
   os.path.join(DST, r"05_hook源码与译文\g3_font_nonserif12.xmc"))
cp(os.path.join(SRC, r"deploy\g3_charset.tsv"),
   os.path.join(DST, r"05_hook源码与译文\g3_charset.tsv"))
cp(os.path.join(SRC, r"deploy\g3_layout.tsv"),
   os.path.join(DST, r"05_hook源码与译文\g3_layout.tsv"))
cpdir(os.path.join(SRC, r"_work\fonts"),
      os.path.join(DST, r"05_hook源码与译文\字体源"))

print("=== 06_独有资产 ===")
# hook 全迭代历史（闪帧/漏图治理的实验依据）
cpdir(os.path.join(SRC, "deploy"), os.path.join(DST, r"06_独有资产\hook快照"),
      pattern=lambda f: f.lower().endswith(".dll"), skip=("d3d9.dll",))
cp(os.path.join(SRC, r"d3d9proxy_src\d3d9_v47_installed.dll"),
   os.path.join(DST, r"06_独有资产\hook快照\d3d9_v47_installed.dll"))
# 实机日志（排查同类问题的第一手依据）
cpdir(os.path.join(SRC, "_logs_archive"), os.path.join(DST, r"06_独有资产\实机日志"))
# 装配树（重新打包 datapack 的起点）
cpdir(os.path.join(SRC, r"_work\x_pristine"), os.path.join(DST, r"06_独有资产\装配树_x_pristine"))
cpdir(os.path.join(SRC, r"_work\x_orig"), os.path.join(DST, r"06_独有资产\装配树_x_orig"))
# 一次性的验证/分析脚本（有历史价值）
cpdir(os.path.join(SRC, r"_archive_小件\verify_历史"),
      os.path.join(DST, r"06_独有资产\verify历史脚本"))
cpdir(os.path.join(SRC, r"_archive_小件\out_历史"),
      os.path.join(DST, r"06_独有资产\out历史"))

# 装配树使用说明（full18 版）
txt = """# 装配树使用说明

`装配树_x_pristine/` 是**已注入中文文本与字形的解包态数据包**，
`装配树_x_orig/` 是**只读原版基线**（从 datapack.hvp.vanilla 解出，勿覆盖）。

## 重新打包成汉化 datapack.hvp

```
..\\..\\02_源码\\产线工具\\obscure-hvp.exe -g obscure2 create -s no \\
    ..\\..\\04_基线与回滚\\datapack.hvp.vanilla \\
    装配树_x_pristine \\
    datapack_zh_full18.hvp
```

打包器靠 mtime 判改动；产物 md5 应为
`d25123d226ebd1dfae39c053717db808`（与 V1.00 交付的一致）。

## 改译文后重建

1. 编辑 `05_hook源码与译文/译文真源/o2_text_zh_full13.tsv`
2. 跑 `02_源码/产线工具/ta2_write.py` 重新注入到装配树
3. 若字形集有变，先跑 `02_源码/产线工具/gate3_charset.py` → `gate3_def.py`
   → `gate3_atlas.py` 出新图集与字形表
4. 重新打包（见上）

## 图集尺寸铁律

`gate3_atlas.py` 的 `NEW_W/NEW_H`、`d3d9_proxy.c` 的 `ATLAS_W/ATLAS_H`、
以及重新生成的 def，**三处必须同步**。少改一处 → 尺寸自检拒绝替换 →
def 与纹理不配对 → 画面出现白块。

## 两个容易踩的坑

- **比对两个 hvp 包不能直接字节 diff**：数据区是逐文件压缩存储，
  压缩流长度变化会让尾部整段看似不同。正确做法是抽包后比对 hashes.json，
  或抽取后与装配树逐文件 md5。
- **重新编译 d3d9.dll 必须显式传 `-DFORCE_POINT_SAMPLER=0`**：
  源码默认 1 = 强制点采样（V1.01/V1.02 的发糊回归即漏传此开关所致）。
"""
with io.open(os.path.join(DST, r"06_独有资产\装配树_使用说明.md"), "w", encoding="utf-8") as f:
    f.write(txt)

print("=== 07_项目记忆 ===")
cpdir(os.path.join(GAME, r".workbuddy\memory"), os.path.join(DST, "07_项目记忆"))

print()
print("复制完成：%d 个文件，%.2f GB" % (n[0], bytes_moved[0] / 1073741824.0))

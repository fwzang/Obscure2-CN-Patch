# -*- coding: utf-8 -*-
"""regen_md5_v101.py — 重新生成交付包 MD5.txt（E 盘）并核对关键指纹。"""
import os
import hashlib
import io
import datetime

DST = r"E:\ObsCure2汉化项目_v1.04_完整交付包"


def md5(p):
    h = hashlib.md5()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


rows = []
total = 0
for root, dirs, files in os.walk(DST):
    dirs.sort()
    files.sort()
    for f in files:
        if f == "MD5.txt":
            continue
        p = os.path.join(root, f)
        rel = os.path.relpath(p, DST).replace("\\", "/")
        sz = os.path.getsize(p)
        total += sz
        if sz > 200 * 1024 * 1024:
            rows.append("%-52s %8.0f MB  (体积过大，未算 md5)" % (rel, sz / 1048576.0))
        else:
            rows.append("%-52s %s" % (rel, md5(p)))

L = ["# ObsCure 2 汉化项目 v1.03.2 交付包 · 文件 MD5 清单", "",
     "生成时间：%s" % datetime.date.today().isoformat(),
     "文件总数：%d　总体积：%.2f GB" % (len(rows) + 1, total / 1073741824.0), "",
     "> 200 MB 的文件仅记录体积（md5 见下方关键指纹核对）。", ""]
L += rows
io.open(os.path.join(DST, "MD5.txt"), "w", encoding="utf-8").write("\n".join(L) + "\n")
print("MD5.txt：%d 行，%.2f GB" % (len(L), total / 1073741824.0))

KEY = [
    ("01_安装包/Obscure2_汉化补丁_V1.04.exe",                 "dd987884b3cfa2a585073f7d1f6859a9"),
    ("01_安装包/手动安装版/d3d9.dll",                         "b42417bd2a51ff5d95d3a84970b8a20f"),
    ("01_安装包/手动安装版/datapack.delta",                   "ce74adb362a7593385713cb5f9e1c23e"),
    ("01_安装包/手动安装版/方案A_寒蝉端黑体/d3d9.dll",         "1e2a38adac855179119ff4f4fd567622"),
    ("01_安装包/手动安装版/方案A_寒蝉端黑体/datapack_a.delta", "249aa200089dcb67ff1a7fcdc6d9acf9"),
    ("04_基线与回滚/datapack.hvp.vanilla",                    "04a96eff7978cf31e66e9354421f1516"),
    ("05_hook源码与译文/d3d9proxy_src/d3d9_proxy.c",          "940c6f48782850b4038279c549955385"),
    ("05_hook源码与译文/译文真源/o2_text_zh_full13.tsv",       "0072ced4a462cecc45734cc9119da104"),
]
print()
ok = True
for rel, want in KEY:
    p = os.path.join(DST, rel.replace("/", os.sep))
    if not os.path.exists(p):
        print("  !! 缺失 %s" % rel); ok = False; continue
    got = md5(p)
    flag = "OK " if got == want else "!! "
    if got != want:
        ok = False
    print("  %s%-52s %s" % (flag, rel, got))
print()
print("关键指纹全部一致" if ok else "!! 有不一致，需检查")

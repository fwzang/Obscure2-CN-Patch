# 03_校验脚本

## check_exports.py

```bat
python 00_工具中台\03_校验脚本\check_exports.py 01_安装包\手动安装版\d3d9.dll
```

校验 17 个导出名与真实 `d3d9.dll` 完全一致、`Direct3DCreate9` 在列、`machine=i386`。
**任何新编的 DLL 都要过这一关**，否则游戏可能直接起不来。

## regen_md5_v101.py

```bat
python 00_工具中台\03_校验脚本\regen_md5_v101.py
```

重算全包 MD5 清单（写入根目录 `MD5.txt`），并比对 16 项关键指纹。
输出末尾应是「关键指纹全部一致」。

改过包内任何文件后都要重跑一次，否则 `MD5.txt` 与实际不符。

> 脚本顶部 `DST` 是交付包路径，改名/换盘后需同步改这一行。

# Obscure II 汉化补丁 V1.03.2 · 安装器说明

> 本目录可在**交付包内**独立重建安装包，不依赖任何开发机路径。

---

## 一、一条命令重建

```bat
:: ① 只做一次：解压编译器
00_工具中台\01_编译链\解压工具链.bat

:: ② 重建安装包
python 02_源码\安装器\build_all.py
```

产出 `02_源码/安装器/Obscure2_汉化补丁_V1.04.exe`，把它复制到 `01_安装包/` 覆盖同名文件，
再跑 `python 00_工具中台\03_校验脚本\regen_md5_v101.py` 更新清单。

> **已验证**：用本目录源码重建，产物 md5 = `7146f4ec97258de8f554ea610809a902`，
> 与 `01_安装包/` 里的发布版**逐字节一致**。

---

## 二、文件说明

| 文件 | 说明 |
|---|---|
| `setup.c` | 安装器源码（Win32 原生，无第三方依赖），版本串在此 |
| `setup.rc` | 版本信息资源（FILEVERSION 1,0,3,1） |
| `info_o2.txt` | 安装器弹窗里的「使用前必读」全文，**改文案只改这个** |
| `gen_info.py` | `info_o2.txt` → `info_o2.h`（自动转义，勿手改 .h） |
| `build_all.py` | 一键：gen_info → windres → gcc → 打包 |
| `build_installer.py` | 载荷追加打包器（6 载荷 + 400B Footer） |
| `make_delta.py` | 差分补丁生成器（原版 → 汉化版） |
| `payload/` | 宽屏补丁载荷：`dinput8.dll` + `main.patch`（不随 datapack 走） |

---

## 三、载荷来源（全部在包内）

| 载荷名 | 来源 |
|---|---|
| `datapack.delta` | `01_安装包/手动安装版/datapack.delta` |
| `d3d9.dll` | `01_安装包/手动安装版/d3d9.dll`（方案B） |
| `datapack_a.delta` | `06_独有资产/方案A_字体产物/datapack_a.delta` |
| `d3d9_a.dll` | `01_安装包/手动安装版/方案A_寒蝉端黑体/d3d9.dll`（方案A） |
| `dinput8.dll` | `02_源码/安装器/payload/dinput8.dll` |
| `main.patch` | `02_源码/安装器/payload/main.patch` |

> 换 DLL 时**不要改这里**——直接替换 `01_安装包/手动安装版/` 下的两个 d3d9.dll，
> 再跑 `build_all.py`，载荷会自动跟着换。

---

## 四、载荷布局

```
[setup.exe][datapack.delta][d3d9.dll][datapack_a.delta][d3d9_a.dll]
[dinput8.dll][main.patch][Footer]

Footer = magic(8) + ver(4) + n(4) + n*{name[32], off(u64), size(u64)}   固定 8 槽 = 400 字节
```

`build_installer.py` 末尾会做 Footer 回读校验；也可用 Python 解析 Footer 单独核对每个载荷的 md5。

---

## 五、改版本号

三处必须同步：

1. `setup.c` — `kSub` 副标题、窗口标题、文件头注释
2. `setup.rc` — `FILEVERSION` / `PRODUCTVERSION`
3. `build_installer.py` — `OUT` 文件名

漏一处会出现"文件名 V1.03.2、窗口显示 V1.03.1"这种尴尬情况。
**V1.03.1 就是这么翻车的**：只改了 setup.rc 和 info，忘了 setup.c，窗口标题还停在 V1.01。

# 00_工具中台 — 编译 / 构建 / 校验 / 诊断 四件套

> 目的：接手的人**不需要重建环境**。解压工具链 → 跑一条命令 → 得到与发布版逐字节一致的 DLL。
> 出问题时按 `03_文档/排障手册.md` 的表格选一个 bat，直接开跑。

---

## 一、目录

```
00_工具中台/
├── 01_编译链/
│   ├── w64devkit-2.10.1-gcc16.2.0.zip   160.8 MB  编译器（含 i686-w64-mingw32-gcc 16.2.0）
│   ├── w64devkit-2.10.1-gcc16.2.0.zip.md5
│   └── 解压工具链.bat                    一键解压到本目录 w64devkit/
├── 02_构建脚本/
│   ├── build_from_package.py             ★ 一条命令重建 d3d9.dll（推荐）
│   ├── build_v64_prod.py                 分层构建：基座（窗口化 + 看门狗 + PRESENT_RESTORE=0）
│   ├── build_v65_prod.py                 分层构建：+ 通用 UI 越界纠正
│   └── build_v66_prod.py                 历史脚本（V1.02 时代），已不用于当前版本
├── 03_校验脚本/
│   ├── check_exports.py                  17 个导出名 + machine=i386 校验
│   └── regen_md5_v101.py                 全包 MD5 清单 + 16 项关键指纹比对
└── 04_诊断脚本/
    ├── d3d9_release.dll                  V1.04 发布版 DLL（供 bat 调用）
    ├── 1_install_release.bat             装发布 DLL 并打印 md5
    ├── 2_remove_dll.bat                  移除 DLL（回原版渲染）
    ├── 3_control_no_proxy.bat            对照组：不用代理 DLL 启动
    ├── 4_no_atlas_swap.bat               O2_NO_SWAP=1，关字体图集替换
    ├── 5_no_ui_fix.bat                   O2_FIX_UI_ANY=0，关 UI 越界纠正
    ├── 6_exclusive_fullscreen.bat        O2_WIN=0，回全屏独占（**会复现卡死，仅对照**）
    └── 7_collect_log.bat                 收集 d3d9proxy.log 到本目录（带时间戳）
```

---

## 二、第 0 步：先自检

**双击** `00_工具中台\一键自检.bat`（推荐），或命令行：

```bat
python 00_工具中台\selfcheck.py
```

一条命令确认「发布物 / 编译器 / 源码 / 安装器 / 校验 / 诊断 / 产线 / 字体 / 历史留档 / 文档」
共 69 项是否齐备，关键文件还会校验 md5。全部 OK 才算具备开工条件。

输出末尾应看到：

```
结果：全部齐备 ✅  可以直接开工
```

任何 `MISS` / `MISMATCH` 都会在末尾汇总，按提示补文件即可。

## 三、最常用动作

### A. 改完源码，重新出 DLL

```bat
:: ① 只做一次
00_工具中台\01_编译链\解压工具链.bat

:: ② 每次改完源码
python 00_工具中台\02_构建脚本\build_from_package.py
```

产出 `_build_out/d3d9.dll`，脚本会自动比对发布 md5：

```
md5  : b42417bd2a51ff5d95d3a84970b8a20f
状态 : 与 V1.04 发布版逐字节一致 ✅
```

### B. 改完包装，校验一遍

```bat
python 00_工具中台\03_校验脚本\check_exports.py 01_安装包\手动安装版\d3d9.dll
python 00_工具中台\03_校验脚本\regen_md5_v101.py
```

### C. 改完安装器文案 / 换完 DLL，重出安装包

```bat
python 02_源码\安装器\build_all.py
```

产出 `02_源码/安装器/Obscure2_汉化补丁_V1.04.exe`，复制到 `01_安装包/` 覆盖，再跑一次 regen_md5。
详见 `02_源码/安装器/README.md`（含载荷来源表与版本号三处同步提醒）。

> 已验证：用包内源码重建的安装包与发布版**逐字节一致**（`7146f4ec…`）。

### D. 玩家报问题，先做三件事

```bat
00_工具中台\04_诊断脚本\7_collect_log.bat     :: 收日志
00_工具中台\04_诊断脚本\3_control_no_proxy.bat :: 对照组：不用代理跑一次
00_工具中台\04_诊断脚本\1_install_release.bat  :: 确认装的是发布版
```

---

> **回溯历史**：想看"某版为什么这么改""哪个版本引入的回归"，
> 见 `06_独有资产/历史资料索引.md`（25 个历史 DLL / 63 个补丁脚本 / 每版产物 / 12 份阶段报告，
> 现均在包内 `06_独有资产/`）。

## 四、版本锁定

| 组件 | 版本 | 说明 |
|---|---|---|
| w64devkit | 2.10.1 | gcc 16.2.0，i686 目标 |
| Python | 3.8+ | 脚本用标准库，无第三方依赖 |
| Windows | 10 1803+ | 自带 `tar.exe`（bsdtar），用于解压 zip |

> `解压工具链.bat` 用的是系统 `tar.exe`。若在 Git Bash 里手动解压，
> 注意 Git Bash 自带的 GNU tar **不认 zip**，会报 "does not look like a tar archive"，
> 需显式调用 `C:\Windows\System32\tar.exe`。

---

## 五、编译参数（一个都不能漏）

```
-O2 -fno-sanitize=undefined -shared
-DFORCE_POINT_SAMPLER=0      漏传 → 字体发糊（v48 事故）
-DPRESENT_RESTORE=0          V1.02 起关闭帧末还原
-Wl,--image-base=0x6BE00000  锁死基址，否则 ld 按文件名哈希定基址，无法复现
```

> 源文件名会进 COFF 符号表。发布版是用 `d3d9_proxy_v66.c` 编的，
> 用别的文件名编出来功能相同但 md5 不同（差 `STT_FILE` 一项）。
> `build_from_package.py` 已自动按发布时的文件名编译。

---

## 六、路径约定

- 脚本一律以**交付包根目录**为基准，用相对路径推导，不写死盘符。
- 诊断 bat 里有一个变量 `GD`（游戏目录），换机器时改这一行即可：
  ```bat
  set "GD=D:\SteamLibrary\steamapps\common\Obscure2"
  ```
- `02_构建脚本/build_v6x_prod.py` 是从开发机原样带过来的，里面 `ROOT` 是绝对路径，
  **仅供追溯构建层次**；日常重编请用 `build_from_package.py`。

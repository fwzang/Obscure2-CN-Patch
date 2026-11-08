# Gate 3 — d3d9.dll 代理（Obscure II 汉化）

> ## ★ 本目录源码 = V1.04 发布版（2026-10-25，v69）
> `d3d9_proxy.c` 已同步为**发布 DLL 的同一份源码**（含窗口化防卡死、看门狗、
> `O2_NO_SWAP` 开关、通用 UI 纠正）。`atlas_png.h` 为方案 B 图集（2048×1024）。
>
> **可复现性已验证**：用下列参数编译，产物与发布 DLL **逐字节一致**：
> ```
> i686-w64-mingw32-gcc -O2 -fno-sanitize=undefined -shared \
>   -DFORCE_POINT_SAMPLER=0 -DPRESENT_RESTORE=0 \
>   -Wl,--image-base=0x6BE00000 -o d3d9.dll d3d9_proxy_v69.c d3d9.def
> ```
> md5 = `b42417bd2a51ff5d95d3a84970b8a20f`（903,272 B）。
>
> ⚠️ **注意**：源码文件名会进 COFF 符号表。用 `build.bat` 直接编 `d3d9_proxy.c`
> 得到的是**功能完全相同但 md5 不同**的产物（差在 STT_FILE 一项）。
> 要逐字节复现，请先复制为 `d3d9_proxy_v69.c` 再编译
> （`00_工具中台/02_构建脚本/build_from_package.py` 已自动处理此事）。
>
> ⚠️ **不要为了"恢复全屏独占"删掉 `pp->Windowed=TRUE`** —— 那是修 Alt+Tab 卡死的
> 关键；需要对照时用环境变量 `O2_WIN=0`。

> 把游戏静态导入的 `d3d9.dll` 换成「透明代理 + 字体图集替换」版 DLL，

> **注意**：本文档为开发期记录，个别示例仍写 4096×2048（早期方案）。当前正式图集为 **2048×1024**，
> 以 d3d9_proxy.c 的 ATLAS_W/ATLAS_H 与 g3_atlas.png 为准。

> 在 `SetTexture` 时把引擎绑定的原版 512×256 字体图集换成 4096×2048 中文大图集。
>
> **本 DLL 必须与 `datapack_zh_full3.hvp` 联合使用**（两者单独安装都会渲染错乱，见下文「依赖关系」）。

---

## 1. 文件清单

| 文件 | 说明 |
|---|---|
| `d3d9_proxy.c` | 代理主源码（单文件，约 800 行） |
| `d3d9.def` | 导出表：17 个命名导出，与真实 `SysWOW64\d3d9.dll` 一致 |
| `gen_atlas_header.py` | 把 `g3_atlas.png` 转成 C 数组 `atlas_png.h` |
| `atlas_png.h` | 生成物：4096×2048 图集 PNG 字节流（613,905 B，md5 `0746d12c…`） |
| `check_exports.py` | 编后必校验：导出数=17、名单一致、`Direct3DCreate9` 在列、machine=i386 |
| `build.bat` | 一键构建诊断版 + 生产版并校验 |
| `d3d9_diag.dll` | 诊断版产物（`-DG3_DIAG=1`） |
| `d3d9.dll` | 生产版产物 |
| `selftest32.c / .exe` | 32 位自测 harness：`selftest32.exe <dll> <DIAG|PROD>`（12 项） |
| `resetbase32.c / .exe` | **无代理基线**：同一套 CreateDevice→Present→Reset 直连系统 d3d9，用于崩溃归因隔离 |

---

## 2. 构建

```bat
cd /d D:\SteamLibrary\steamapps\common\Obscure2\Obscure2_Handover\d3d9proxy_src
build.bat
```
> 构建脚本用 **w64devkit 的 i686-w64-mingw32-gcc 16.2.0**（`..\_toolchain\w64devkit\bin`），
> 完整版本清单见交付包 `02_源码/环境依赖说明.md`。

等价命令（与 build.bat 完全一致，逐字节复现出厂 v49）：

```bat
..\_toolchain\w64devkit\bin\i686-w64-mingw32-gcc.exe -O2 -fno-sanitize=undefined -shared ^
   -DFORCE_POINT_SAMPLER=0 -Wl,--image-base=0x6BE00000 ^
   -DG3_DIAG=1 -o d3d9_diag.dll d3d9_proxy.c d3d9.def
..\_toolchain\w64devkit\bin\i686-w64-mingw32-gcc.exe -O2 -fno-sanitize=undefined -shared ^
   -DFORCE_POINT_SAMPLER=0 -Wl,--image-base=0x6BE00000 ^
   -o d3d9.dll d3d9_proxy.c d3d9.def
```

**两条铁律（Gen-1 血泪教训）**
1. `.def` 绝对不能漏 —— 漏了会导出全部非 static 符号，游戏加载期导入失败、日志一行不写。
2. 编后必须跑 `check_exports.py`，输出 `[PASS] … 17 个导出` 才允许装机。

**两个不能漏的编译参数（缺一不可）**
- `-DFORCE_POINT_SAMPLER=0`：源码默认 1＝强制点采样，漏传则字体发糊（V1.01/V1.02 回归事故根因）。
- `-Wl,--image-base=0x6BE00000`：ld 的 auto-image-base 按输出文件名哈希定基址，不钉住无法逐字节复现。

> 说明：早期文档写的是 `python -m ziglang cc`（ziglang 0.16.0）。该路线在 2026-10-22 起
> 已被 w64devkit gcc 取代——只有 gcc 16.2.0 + 上述参数能产出与出厂逐字节一致的 DLL。

---

## 3. 依赖关系（为什么必须成对）

| 组件 | 内容 | 作用 |
|---|---|---|
| `datapack_zh_full18.hvp` | 字体 def（`nonserif12`）引用 **2048×1024**；5 语种文本容器全中文 | 提供 **UV 坐标**（按 2048×1024 归一化） |
| `d3d9.dll`（本代理） | `SetTexture` 时替换显存纹理 | 提供 **显存像素**（2048×1024） |

二者必须一致：
- **只装汉化包、不装代理** → def 说 4096 宽，实际绑定 512×256 纹理采样坐标越界 → **中文渲染错乱（预期 FAIL）**
- **只装代理、不装汉化包** → 原版 def 仍按 512 归一化，绑到 4096 大图集 → 字形偏到一个极小角落
- **成对安装** → UV 与纹理解释一致，渲染正确

---

## 4. 工作模式

| 开关 | 模式 | 行为 |
|---|---|---|
| `-DG3_DIAG=1` | 诊断（首发实机） | 全量日志，**不替换、不建纹理**，零渲染风险 |
| 无 | 生产 | 识别字体图集后懒创建 4096×2048 大纹理，`SetTexture` 命中即替换 |

### 判据（生产版）
```
CreateTexture(w==512, h==256, fmt==21 A8R8G8B8)  -> 登记为字体图集指针
SetTexture(tex ∈ 字体图集指针集合)               -> 换成 g_bigTex
```
> Gen-1 c44 教训：游戏可能**反复重建**字体图集（指针每次都变），故登记上限 8 个指针，
> `SetTexture` 用指针集合匹配而非单一 g_fontTex。

---

## 5. 部署步骤（实机测试）

**第一步：诊断版（必先做，零风险）**

1. 备份：确认游戏目录 `datapack.hvp` 为原版 md5 `04a96eff7978cf31e66e9354421f1516`
2. 把 `d3d9_diag.dll` 复制到游戏目录，**重命名为 `d3d9.dll`**
3. 装 `datapack_zh_full3.hvp` → 重命名为 `datapack.hvp` 覆盖（先备份原版！）
4. 启动游戏 → 进主菜单 → 存档/读档 → Alt-Tab 切出切回一次 → 退出游戏
5. 回收游戏目录下 `d3d9proxy.log`（与 dll 同目录）
6. **回滚**：删掉 `d3d9.dll`，恢复原版 `datapack.hvp`

**第二步：诊断日志达标后才能换生产版** `d3d9.dll`

### 诊断判据（Gate 3 通过标准）
- `[INIT] real d3d9 导出解析=17/17`
- `[D3DC9] obj=<非0]` + `[D3D9] clone … patch vt[16]=CreateDevice`
- `[CD] hr=0x0 dev=<非0>` + `[DEV] device=… 已挂 5 个 hook`（**未出现 `[SELF] … 索引可疑`**）
- `[CAPS] MaxTextureWidth/Height >= 4096/2048`
- `[CT] … 512x256 … <<< 字体候选` 至少 1 条
- `[FONT] 字体图集登记 #1 tex=…`
- `[ST] … <<< FONT bind#1`（**证明 SetTexture 路径命中**）
- `[STAT] f=…` 帧计数在增长 → Present hook 正常
- 无 `[FATAL]`、无崩溃

---

## 6. 日志字段速查

| 前缀 | 含义 |
|---|---|
| `[INIT]` | 加载/模式/导出解析/常量 |
| `[D3DC9]` | `Direct3DCreate9` 调用（sdk、对象、vtable 归属模块） |
| `[D3D9]` | IDirect3D9 vtable 克隆 |
| `[CD]` | `CreateDevice`（adapter/type/flags/pp/hr） |
| `[CAPS]` | 设备能力：最大纹理尺寸（决定 4096×2048 能否创建） |
| `[SELF]` | SetTexture/GetTexture 索引功能自检（失败则不挂 hook，安全失败） |
| `[DEV]` | 设备 vtable 挂载明细 + 各 hook 所属模块 |
| `[HEAL]` | vtable 被还原后自愈（应长期为 0） |
| `[CT]` | `CreateTexture`（w/h/levels/usage/fmt/pool） |
| `[FONT]` | 字体图集指针登记 |
| `[UT]` | `UpdateTexture`（确认上传路径） |
| `[ST]` | `SetTexture`（stage/tex/尺寸/格式/池）；`<<< FONT` = 命中字体图集 |
| `[SWAP#]` | 生产版实际替换（记录前 12 次） |
| `[RST]` | `Reset` 次数与返回值 |
| `[STAT]` | 每 250 帧一行统计 |
| `[FATAL]` | 致命失败（含最后检查点 `ckpt=`，用于崩溃定位） |

---

## 7. 关键设计（继承 Gen-1 教训）

| Gen-1 教训 | 本代理对策 |
|---|---|
| per-frame 还原导致菜单白屏（c44） | **持续替换**，不做帧末还原（c45 正确思路） |
| 游戏反复重建字体图集（c44） | 指针集合 `g_fontTexes[8]` 跟踪 |
| MANAGED + 手工 LockRect 灌数致 Reset 失败（c50） | 经 `d3dx9_42.dll` 的 `D3DXCreateTextureFromFileInMemory` 解码（标准 D3D 可见路径），创建后为 MANAGED，跨 Reset 自动恢复 |
| 索引猜错 | vtable 索引取自 `zig libc …/d3d9.h` 权威声明 + Gen-1 实证双核对；并在挂载时跑 **SetTexture/GetTexture 功能自检**，失败则不挂载（安全失败） |
| COM 引用计数致崩溃 | vtable 克隆法不改 `AddRef/Release/QueryInterface`，全程透传；大纹理由我们创建、持有 1 引用、卸载时释放 |
| `.def` 漏写导致起不来 | 显式 17 导出 + `check_exports.py` 强制校验 |
| Windows 版本差异导致缺导出 | 解析失败的桩**中和**为 `xor eax,eax; ret 0`（安全返回 0/NULL） |

---

## 8. vtable 索引（权威来源）

`C:\Users\fwzang\.workbuddy\binaries\python\envs\default\Lib\site-packages\ziglang\lib\libc\include\any-windows-any\d3d9.h`

| 接口 | 方法 |
|---|---|
| `IDirect3D9`（17 项） | `CreateDevice` = 16 |
| `IDirect3DDevice9`（119 项） | `Reset`=16 `Present`=17 `CreateTexture`=23 `UpdateTexture`=31 `GetDirect3D`=6 `GetDeviceCaps`=7 `GetTexture`=64 **`SetTexture`=65** |
| `IDirect3DTexture9`（22 项） | `GetLevelCount`=13 `GetLevelDesc`=17 |

（与 Gen-1 `version_proxy.c` 实机实证值 16/17/23/31/65 完全吻合）

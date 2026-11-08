# Obscure 1 工具链复用评估（对 Obscure 2 两线程）

> 2026-10-18 ｜ 评估对象：`E:\SteamLibrary\steamapps\common\Obscure\hzp_tools\`（核心 22 脚本 + hook/ + fonts/）、根目录 `hvp_tools_grp.py`、`_废弃归档_2026-10-11/`（165 个一次性探针）。
> 方法：只读通读全部核心脚本源码 + 交叉对照《Obscure II 汉化可行性初步报告》与 Gate 0 实测结论。
> 评估分三类：**可直接复用** / **算法可复用、数据结构须重写** / **不可复用（仅参考）**。

---

## 0. 结论摘要（先行）

| # | 评估对象 | 判定 | 对 Obscure 2 的价值 |
|---|---|---|---|
| 1 | `hook/d3d9proxy.c` + 成品 `d3d9proxy.dll` | **可直接复用（改日志路径）** | ★★★ 二代 Gate 2 挂载层现成基底——二代 exe 导入 d3d9.dll，游戏目录同名 DLL 优先加载，挂载点迁移的最大未知项被消除 |
| 2 | `hook/d3dsettex.c` | **可直接参考（改窗口标题）** | ★★★ dummy device 取址 + vtable dump + D3DPP 56B 结构，二代 SetTexture/CreateTexture 截获原型直接照搬 |
| 3 | `ginput.py` | **可直接复用（改截图目录）** | ★★☆ 扫描码注入 + 窗口枚举（'Obscure' in title 对二代同样命中）+ 截图，Gate 验证环节直接可用 |
| 4 | `fonts/LXGWWenKai-Medium.ttf`（14.5MB） | **可直接复用** | ★★☆ 中文字形 PIL 渲染现成字体（另有系统 msyh/simhei 备选） |
| 5 | `cn_ui.py`（废弃归档） | **算法可复用，数据结构重写** | ★★★ 24px 行带放置算法 + occ 空闲判据 + 整带清空防残影，正是线程 B 排版核心 |
| 6 | `make_atlas_retail.py` | **算法可复用（预乘口径+自检体系）** | ★★☆ 原区一致性/越界/覆盖/墨迹四重自检 + 预乘取整口径，线程 B 图集改写直接沿用 |
| 7 | `FINAL_PARSE_FIXED.py`/`inject_lng.py`/`build_zh_lng.py` | **结构不通用，仅概念参考** | ★☆☆ 一代 lng 格式与二代 0 命中（可行性报告已实证）；借鉴 round-trip 闭环与 L0/L1/L2 验证阶梯思想 |
| 8 | `full_verify.py` | **可直接复用（改路径）** | ★☆☆ 全包逐字节 diff + 区段压缩，回包后校验环节可用 |
| 9 | `fastinject.py` + `hook/inject.exe` | 备选（32 位注入器） | ★☆☆ d3d9 代理路线优先；注入路线作为 Plan B，已知四坑（32 位/自重启轮询/延迟 0.35s/日志句柄） |
| 10 | `write_minimal.py`/`hvp_toc.py`/`hvp_tools/`(19)/`hvp_tools_grp.py`/`version_proxy.c` 系/bink 系 | **不可复用** | 见 §3，一代格式/挂载点专属 |

**一句话结论：一代中台对二代的支撑集中在三处——d3d9 代理挂载层（成品可改）、行带放置与预乘法（算法沿用）、lng 验证契约（概念参考）；其余为一代专属资产。线程 B 不需要等待任何新逆向，可立即开工。**

---

## 1. 可直接复用项（适配量 ≤ 改路径）

### 1.1 `hook/d3d9proxy.c`（6,224B）——二代 Gate 2 挂载层现成基底 ★★★

- **机制**：100% 透明 d3d9 代理。17 个导出（Direct3DCreate9Ex/On12/ShaderValidator/PSGP*/Debug*/D3DPERF_*/MaxWinShim）全部用 x86 尾跳转桩 `jmp [real_addr]` 转发系统 `C:\Windows\System32\d3d9.dll`；仅 `Direct3DCreate9` 是 C 包装，首次调用时记录 real DLL 路径/函数地址/返回值/vtable 指针到日志。
- **为何对二代关键**：可行性报告 §4.2 实证二代 exe 导入 `d3d9.dll`（一代挂载点 version.dll 不存在）。Windows DLL 搜索顺序 = 应用程序目录优先于 System32 → **游戏目录放 d3d9.dll 即被加载，无需注入器、无需改 exe**。这条路线把「Hook 挂载：中-高」降为「低-中」。
- **适配量**：`LOGF` 宏路径 `Obscure` → `Obscure2`；后续在 Direct3DCreate9 包装内追加纹理替换逻辑（一代思路：拦截 CreateTexture/SetTexture，换 grp1 512×128 为更大纹理；二代对应 nonserif12 512×256）。
- **证据**：源码 `hzp_tools/hook/d3d9proxy.c:31-46`（尾跳转桩）、`:83-103`（Create9 包装+日志）；成品 `d3d9proxy.dll` 242,688B（2026-10-06 20:37 构建）。

### 1.2 `hook/d3dsettex.c`（5,659B）——vtable 截获原型 ★★★

- dummy device 创建流程完整可抄：`Direct3DCreate9(32)` → `vt9[16] = CreateDevice` → D3DPP 56 字节结构（14 字段，`hDeviceWindow` 必须）→ dump device vtable 的 CreateTexture 区（vt[18..24]）与 SetTexture 区（vt[58..66]）。
- 内含一条实测结论：d3d9.dll 基址范围内判定 vtable 归属（`in_dll` 标记）。
- **适配量**：`FindWindowW(NULL, L"Obscure")` → 二代窗口标题（若为 "Obscure II" 需改；枚举时 'Obscure' 前缀匹配亦可兼容）；`Sleep(8000)` 等二代 885MB 包加载需重新标定。
- **证据**：源码 `d3dsettex.c:71`（窗口查找）、`:93`（CreateDevice=vt9[16]）、`:115-116`（vtable 区段 dump）。

### 1.3 `ginput.py`（5,686B）——Gate 验证自动化 ★★☆

- DirectInput 读**扫描码状态** → 必须 `SendInput` + `KEYEVENTF_SCANCODE`；方向键等扩展键必须加 `KEYEVENTF_EXTENDEDKEY`（否则 DOWN 0x50 被当小键盘 Num2）。
- `find_game()` 用 `'Obscure' in title` 枚举可见窗口——**对《Obscure II》同样命中**（窗口标题含 Obscure）。
- `shot(tag)` 自动前台化 + ImageGrab 截图 + 返回亮度统计（>100 像素数，可作非黑屏判据）。
- **适配量**：`shot()` 默认 outdir 路径改到 recon/gate1/；键位表 KEYS 对二代主菜单（方向键+Enter）已覆盖。
- **证据**：源码 `ginput.py:86-96`（key 注入）、`:63-71`（窗口枚举）、`:136-148`（截图）。

### 1.4 `fonts/LXGWWenKai-Medium.ttf`（14.5MB）★☆☆

霞鹜文楷 Medium，PIL `ImageFont.truetype` 直接可用。系统另有 `msyh.ttc`（微软雅黑）/`simhei.ttf`。线程 B 渲染「开始」二字时任选其一（一代最终版用的是 `D:\Basic\ChillDuanSans_Bold.otf` 端黑，可作风格备选，但该文件在一代 D 盘路径，需确认存在）。

### 1.5 `full_verify.py`（1,286B）★☆☆

全包 4MB 分块逐字节 diff + 差异区段压缩（间隔 >64B 断段）+ 总量/范围统计。**适配量**：路径改 + 区段标注改（二代按 extract 后目录比对更合适，见线程 B Step 5 方案）。

---

## 2. 算法可复用、数据结构须重写

### 2.1 `cn_ui.py`（废弃归档，2,020B 行内一条龙）——线程 B 排版核心参考 ★★★

一代完整一条龙：读 cachpack 图集（zlib 解压 + TGA y-flip）→ 解析 exe .data 字形表（10B/条）→ 保留策略（ASCII 全保留 + 西语高频 12 重音，其余牺牲）→ **24px 行带放置** → PIL 渲染 → TGA 写回 → lng 五语种注入。

**线程 B 直接沿用的算法**：

| 算法 | 源码位置 | 二代对应 |
|---|---|---|
| occ 占用网格 + `any(occ)` 空闲判据（PROJECT_STATUS 教训 #7：用 any 不是 all） | `cn_ui.py:99-122` | dic 图集 y≥224 空闲区放置，逻辑相同 |
| 24px 行带、字形放行带下半、**整带清空防残影** | `cn_ui.py:106-121,133-135` | nonserif12 字形高 12px、行带概念需重新标定（二代图集 512×256，y=224..255 全空闲） |
| PIL `textbbox` 居中渲染（先渲染独立小图再 paste，防溢出） | `cn_ui.py:127-136` | 完全相同（PROJECT_STATUS 教训 #6） |
| lng 注入契约 `\x01\x00 + UTF-16LE + \x00\x00` | `cn_ui.py:191` | **不适用**（二代正文是 UTF-8 无标记，见 2.3） |

**必须重写的数据结构**：一代图集=cachpack TGA（zlib@0x15B0B43）/ 字形表=exe .data 10B 二进制 / lng=24B 头记录流；二代图集=dic 容器 RGBA（@0x53EA23）/ 字形表=.xmc 三层明文 / 文本=16B/8B 双记录头。这些二代侧均已有完整逆向（recon/ 产物），属于「照着二代格式重写 IO，放置/渲染算法原样搬」。

### 2.2 `make_atlas_retail.py`（13,034B）——预乘口径 + 四重自检 ★★☆

- **预乘口径（中台契约 #1）**：新字 RGB = 色 × alpha/255，取整用 `int()` 截断（非 round，否则每像素差 1）；直通恒定色 → 边缘过亮。二代图集为白字+alpha 格式（recon 已实证：实心 alpha=255、AA 边缘降 alpha、背景全透明）——若二代原版 RGB 是白色常量，则新字按「RGB=白 × alpha/255」同口径写入，保持 AA 边缘一致。
- **四重自检**：① 原区 y<ORIG_H 与参考图集逐字节一致；② 全部新字 y≥ORIG_H（越界 0）；③ 需求字符 100% 被新表覆盖；④ 新字区 RGB 峰值/墨迹范围。线程 B 改写 dic 图集后照此四检。
- **原区双通道完整保留（契约 #2）**：只取 alpha 写回会让功能图标变白圆盘——二代 nonserif12 含 16 个手柄图标字形（空 char），改动时同样只动牺牲槽位与新 box，其余字节零接触。
- **证据**：`make_atlas_retail.py:156-181`（预乘渲染）、`:218-277`（自检组）、`:41-51`（双通道教训注释）。

### 2.3 一代 lng 三件套——仅概念参考 ★☆☆

| 维度 | 一代（`FINAL_PARSE_FIXED.py`） | 二代（`recon/o2_lng4.py` 已冻结） |
|---|---|---|
| 文件头 | 24B 固定 | 8B：`[u32 总数=3844][u32 16B头数=2517]` |
| 记录结构 | `[u16 BE L][body][6B meta]`，末条无 meta | 16B 头 `[u32 BE key][u16 BE type][u16 LE f1][u32 LE 0][u16 LE f3][u32 LE len][len B]` / 8B 头 `[u32 BE key][u32 LE len][len B]` |
| 正文 | body[0]=类型标记（00=8bit / 01=UTF-16LE） | 无类型标记，正文即 UTF-8，无 NUL |
| meta | 6B 必须保留 | 无 meta |

可行性报告 §2.2 已实证一代解析器对二代 **0 命中**。线程 A（文本容器回写器）按二代格式新写——好消息是格式更简单（无 meta、无类型标记、线性记录、`end==n` 闭环已 100% 验证），实现量确实小。**可借鉴的工程契约**：round-trip 往返校验（`inject_lng.py:176-242` 的 L0/L1/L2 阶梯：闭环 + 算式核对 + 编码标记完整性）、KEEP_RAW 哨兵（无译文保留原字节）、统计报告（注入/保留/meta 来源分项计数）。

---

## 3. 不可复用项（仅历史参考）

| 对象 | 原因 |
|---|---|
| `write_minimal.py` / `hvp_toc.py` | 一代 HVP 目录项布局 `[u32 BE nameLen][name][25B meta]`（meta 描述**下一个**资源）与二代定长 24B 二进制条目完全不同构；且二代已确立 `obscure-hvp.exe create -s no` 回包路线（Gate 0 实测闭环），原地最小改动方案被更优路径取代 |
| `hvp_tools_grp.py`（根目录） | 一代 exe .data 段 grp1-5 字形表探测；二代字形表在 .xmc 文件内，格式不同源 |
| `hvp_tools/` 19 脚本（cab3/mz2/split/strm/enimg/bmpx…） | 一代 CD 版 CAB 解包 / 流媒体包 / BMP 贴图相关，二代无对应物 |
| `version_proxy.c`（189KB）+ version_c86..c93e DLL 系列 | 一代 version.dll hook 主体；二代 exe 不导入 version.dll，挂了不加载。**设计思想可参考**：GRP1-FIFO、swap_mode、`__RUNTIME__*.bmp` 快照（RGB=可见层/alpha=shape mask）、D2/D2S 判据零硬编码（首帧登记+跟随） |
| binkhook/binkw32 系列 | 一代 binkw32 视频 hook；二代视频在 kinepack（未检），且一代该路线本身未修通（14 个 _Bink* 导出问题） |
| `_废弃归档_2026-10-11/` 165 个探针 | 一次性诊断脚本，历史价值 |

### 3.1 跨代通用教训（PROJECT_STATUS.md §9，直接继承）

1. 空闲区判断用 `any(occ)` 不是 `all(occ)`；
2. TGA `desc=0x08` 上下翻转，`file_y = H-1-atlas_y`（二代 dic 是 top-down RGBA，不涉及，但采样本着图集时注意）；
3. PIL truetype 文字会溢出指定格子，必须先渲染独立小图再 paste；
4. 改包前备份 + 逐项验证 + 跑一次游戏；`taskkill` 强杀的 mdmp 不是崩溃；
5. 新增 PE 节不能放 BSS（放独立 `.wfont` 节）——二代若走 exe patch 路线时适用。

---

## 4. 对两线程的落地影响

### 线程 B（gate1_visual.hvp，当前优先）

不需要任何新逆向，材料齐备：
- 放置算法 ← `cn_ui.py`（occ 网格 + 行带 + 整带清空）
- 预乘口径 + 四重自检 ← `make_atlas_retail.py`
- 渲染字体 ← `fonts/LXGWWenKai-Medium.ttf`（或系统 msyh/simhei）
- 数据结构 ← recon 已有：glyphlist_ns12.txt（155 字形全清单 + 牺牲槽位 `~`/`^`）+ font 三层格式 + dic 图集格式
- 验证截图 ← `ginput.py`（改 outdir）

### 线程 A（datapack_zh.hvp 全量文本替换）

- 一代 lng 三件套**结构不可用**；按 o2_lng4.py 冻结格式新写回写器（4 步规范：只读偏移重算 → 安全写入 → 闭环验证 → 全量包）。
- 语料已就绪：`recon/o2_text_zh.tsv`（3844 行）+ zh_manual_queue.tsv（47 条人工队列，保留英文并高亮警告）+ zh_tag_review.tsv（9 条）+ zh_nl_review.tsv（408 条待 UI 验证）。
- **独立于线程 B 的额外收益**：文本回写器不依赖字体，可先于线程 B 交付「全量中文文本 + 英文字形回退」包（中文显示为空格/缺字形但结构验证充分），与线程 B 的「开始」视觉包互补。

### Gate 2（未来挂载层）

`d3d9proxy.c/dll` + `d3dsettex.c` 现成，二代挂载层从零变改编。注意反调试（IsDebuggerPresent + Cslh_Debugger RTTI）——一代结论是 RTTI 类运行时才检测，d3d9 代理加载不触发调试器路径，但需 Gate 2 实机验证。

---

## 5. 证据索引

| 结论 | 引用 |
|---|---|
| d3d9 代理透明转发 17 导出 | `Obscure/hzp_tools/hook/d3d9proxy.c:31-79` |
| Create9 包装 + vtable 日志 | `d3d9proxy.c:83-103` |
| dummy device + vtable dump 区段 | `hook/d3dsettex.c:93,115-116` |
| D3DPP 56B 结构 | `d3dsettex.c:18-34` |
| 扫描码注入 + 扩展键 | `hzp_tools/ginput.py:10-18,86-96` |
| 窗口枚举 'Obscure' 匹配 | `ginput.py:63-71` |
| 24px 行带放置 + any(occ) | `_废弃归档/cn_ui.py:99-122` |
| 整带清空防残影 | `cn_ui.py:133-135` |
| PIL textbbox 居中 | `cn_ui.py:127-132` |
| 预乘 int() 截断口径 | `make_atlas_retail.py:156-181`（含 Q1 定性注释） |
| 四重自检 | `make_atlas_retail.py:218-277` |
| 双通道保留教训 | `make_atlas_retail.py:41-51` |
| 一代 lng 格式（对二代 0 命中） | `FINAL_PARSE_FIXED.py:40-98` + 可行性报告 §2.2 |
| round-trip L0/L1/L2 阶梯 | `inject_lng.py:176-242` |
| 全包 diff | `full_verify.py` |
| 二代 exe 导入 d3d9 不导入 version.dll | 可行性报告 §4.2 |
| 挂载点优先级（游戏目录 DLL 优先） | Windows DLL 搜索顺序（应用目录 → System32） |
| 通用九教训 | `Obscure/PROJECT_STATUS.md:257-268` |

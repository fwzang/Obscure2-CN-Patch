# DXVK 与汉化补丁共存方案 · 技术预研（2026-10-28 16:10）

> 前提：DXVK 纯环境测试证明「2K 下浴室贴图在 DXVK 下能显示」。
> 本文档给出把两者合并成**一个 d3d9.dll** 的完整方案（链式代理）。

---

## 一、可行性已验证的两条硬前提

| 前提 | 验证结果 | 意义 |
|---|---|---|
| DXVK 的 `d3d9.dll` 导出表与真实 d3d9.dll **一致** | `check_exports.py` → **PASS：17 个导出，名单一致，machine=i386** | 我们的代理可以**原样转发**给它，不需要任何导出适配 |
| DXVK **不会自加载 "d3d9.dll"** | 二进制里 `d3d9.dll` 字符串 **不存在**（只有 `dxvk.conf` / `d3dx9_43.dll` / 系统 dll） | **无链式递归风险** —— 这是链式代理最常见的死因，此处不存在 |

DXVK 身份确认：含 `DXVK` / `Vulkan` / `DXVK_FORCE_WINDOWED` / `DXVK_SHADER_DUMP_PATH` /
`DXVK: No adapters found...` 等特征串。4,493,326 B，md5 `e8a4ca855429d0e5da4200e87c610fc9`。

---

## 二、方案总图（链式代理）

```
游戏 Obscure2.exe
   │  加载 d3d9.dll
   ▼
【d3d9.dll = 我们的汉化代理】（游戏目录里唯一叫这个名字的文件）
   │  ① LoadLibraryA("d3d9_dxvk.dll")   ← 改名后的 DXVK（同一目录）
   │  ② GetProcAddress 解析 17 个导出
   │  ③ 转发调用（我们现有代码已是转发式代理）
   │  ④ 叠加我们自己的 hook：vtable clone → SetTexture 换图集 / 阈值判定 / 探针
   ▼
【d3d9_dxvk.dll = DXVK】（内部用 Vulkan 驱动 N 卡）
   │
   ▼
   Vulkan → NVIDIA 驱动
```

关键点：**我们的 hook 位于 D3D9 API 层，DXVK 位于其下**。
顶点裁剪由 **Vulkan/DXVK** 决定，不再是 N 卡的 D3D9 驱动路径 → 越界顶点不再被 N 卡裁掉。

---

## 三、需要的代码改动（只有一处，集中在「真实 d3d9 解析」环节）

我们现有代码里有一段「解析真实 d3d9 的 17 个导出」（日志 `[INIT] real d3d9 导出解析=17/17`）。
把它改成**三级查找**：

```c
/* ① 优先 DXVK（同目录，改名后的 d3d9_dxvk.dll） */
hReal = LoadLibraryA("d3d9_dxvk.dll");
/* ② 回退：系统 32 位 d3d9.dll */
if (!hReal) hReal = LoadLibraryA("C:\\Windows\\SysWOW64\\d3d9.dll");
/* ③ 再回退：同目录同名（自反射，只在 DXVK 模式下不可能，保留兜底） */
if (!hReal) hReal = LoadLibraryA("d3d9.dll");
```
再从 `hReal` 解析 17 个导出（逻辑不变，只是模块来源变了）。

**开关**：环境变量 `O2_DXVK=1` 才启用 ①，默认行为完全不变（零风险回退）。

---

## 四、风险清单与对策

| # | 风险 | 评估 | 对策 |
|---|---|---|---|
| 1 | DXVK 的 `IDirect3DDevice9` vtable 长度/布局与微软规范不同 | 低：DXVK 实现了完整 D3D9 API，vtable 顺序必须遵守规范 | 我们已用「300 槽 + 拷贝可读部分 + DummySlot 兜底」，越界槽位不会踩 NULL |
| 2 | 我们索引的 vtable 槽（16/17/23/31/65/47…）在 DXVK 下含义不同 | 中 | 逐个用 `[DEV] vt[65]=… -> hook` 日志核对；DXVK 规范一致时应完全相同 |
| 3 | 我们的 4096/2048 大图集（MANAGED, A8R8G8B8）在 Vulkan 后端被转码 → 颜色/alpha 变化 | 中 | 转码是 DXVK 的标准行为，通常保真；实测看字形是否正常即可。若异常，改用 D3DUSAGE_D3D9COPY? 无——改为直接用 D3DFMT_A8R8G8B8 + D3DPOOL_MANAGED（现状）观察 |
| 4 | DXVK 依赖 `d3dx9_43.dll`（二进制里有该引用） | 低 | Win10/11 通常自带；缺失时 DXVK 会报错 `No adapters found`/加载失败，日志可见 |
| 5 | DXVK 读 `dxvk.conf`（同目录） | 无 | 需要调参时放 `dxvk.conf`（如 `dxgi.maxFrameLatency`）；对我们无影响 |
| 6 | `dinput8.dll`（宽屏补丁）与 DXVK 并存 | 无 | 两者互不相干，dinput8 是输入侧 |
| 7 | DXVK 可能改变窗口/全屏行为（DXVK 对全屏 DX9 有自己的处理） | 中 | 我们已强制无边框窗口化；实测若窗口异常，用 `dxvk.conf` 调 `dxvk.presentFullscreen` 类项 |
| 8 | 性能：DXVK 翻译层开销 | 低 | 2K 老游戏，DXVK 通常反而更快（Vulkan 驱动更高效） |

---

## 五、实施步骤（若 DXVK 测试通过）

1. 把 DXVK 的 `d3d9.dll` 复制到游戏目录并**改名 `d3d9_dxvk.dll`**；
2. 改我们代理的「真实 d3d9 解析」为三级查找（加 `O2_DXVK` 开关）；
3. 编译两套（方案A/B 图集不变）→ 手工装进游戏目录测试；
4. 验收：
   - 日志出现 `[INIT] real d3d9 导出解析=17/17` 且来源是 DXVK（需加一行来源日志）；
   - 中文正常、贴图正常、窗口化正常、切屏不卡；
5. 若通过 → 把 `d3d9_dxvk.dll` 纳入安装包载荷（安装器新增第 7 个载荷），
   由安装器按方案自动放置并改名，安装完成后自动写 `dxvk.conf`（可选）。

---

## 六、当前待办

- ⏳ 等待 **DXVK 纯环境测试**结果（贴图是否出现）：
  - 出现 → 按本章实施共存（预计改动 < 60 行，1～2 小时可出测试版）；
  - 不出现 → 说明裁剪不是驱动层问题，DXVK 路线作废，回到 v79 坐标篡改 / 或接受 1080p 限制。

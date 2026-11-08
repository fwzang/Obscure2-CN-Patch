# HVFilePacker 官方工具分析报告（Obscure II HVP 格式权威规范）

> 来源：游戏目录自带 `HVFilePacker-3-1-0-1731764304/`（cx_Freeze 冻结的 Python 3.12 应用）
> 方法：提取 `lib/library.zip` → `hvfilepacker__main__.pyc` → marshal 加载 + `dis` 全量反汇编 → 对游戏原版 datapack.hvp 逐项校验
> 结论先行：**官方格式已 100% 逆向确认并与原版文件端到端校验通过**；游戏内部真实路径全部解析（文本=`strings/en.lng`，菜单字体=`menus/font_nonserif12.xmc`，图集=`data/texpc_pc.dic`）

---

## 1. 工具构成

| 组件 | 说明 |
|---|---|
| `HVFilePacker.exe` (17KB) | cx_Freeze 启动器 |
| `lib/library.zip` (1.6MB) | 冻结模块库，含主程序 `hvfilepacker__main__.pyc`(16,007B) |
| `hashes.json` (723KB) | **{str(obscureCRC32(名字)): 真名}** 字典，17,748 条 |
| `lib/lzokay/` | LZO 压缩库（证实 HVP 压缩算法 = LZO） |
| `lib/numpy/`, `binary_reader` | 主程序依赖（binary_reader 1.4.3 提供 BrStruct/BinaryReader/Endian） |

用法（反汇编推断）：拖 hvp 文件到 exe = 解包；拖文件夹 = 回包（询问 y/n 是否 LZO 压缩）。

---

## 2. HVP 容器格式（权威版）

### 2.1 文件头（16 字节）

```
偏移  0: [u32 signature]   # 写者固定写 262144(0x40000)；读者先按 LE 读，若得 1024 → 整文件改按 BE 解析
偏移  4: [u32 0]           # 占位（写者先写 0）
偏移  8: [u32 entry_count]
偏移 12: [u32 header_crc]  # zlib.crc32(全部 24B 条目头) ← 已对原版验证 MATCH
偏移 16: 条目头区（24B × count）
       之后: 数据区（各条目 Data 顺序拼接）
```

### 2.2 条目头（24 字节，两种型）

**目录条目（type=4）**：
```
[u32 name_crc][u16 type=4][10B padding][u32 entry_count][u32 first_entry_index]
```

**文件条目（type=0 原始 / 1=LZO）**：
```
[u32 name_crc][u32 type][u32 data_crc][u32 uncompressed_size][u32 offset][u32 compressed_size]
```

- `name_crc` = obscureCRC32(名字 bytes)，**名字本身不在容器内**，靠 hashes.json 反查（回包时从原包保留，不重算）
- `data_crc` = obscureCRC32(**存储态**字节（LZO 条目即压缩后字节））← 已对原版验证 MATCH
- 目录也参与数据区之外的线性条目表；子条目区间 = Entries[first : first+count]

### 2.3 obscureCRC32（官方算法，numpy 实现已复现比对一致）

```python
def obscureCRC32(b):
    checksum = 0
    if len(b) >= 4:
        checksum += np.frombuffer(b, dtype=np.uint32, count=len(b)//4).sum()  # LE u32 求和（32位回绕）
    r = len(b) % 4
    if r:
        for i, byte in enumerate(b[-r:]):
            checksum += byte << (i*8)
    return checksum & 0xFFFFFFFF
```
即「LE u32 字求和 + 尾字节按位权补齐」模 2^32。**不是**标准 CRC32。

### 2.4 解包/回包流程（官方工具行为）

- 解包：读条目 → 目录/文件名 = `hashes.json.get(str(crc), str(crc))`（未知名 → `<crc>` 或 `<crc>.bin`）→ type=1 条目 `lzokay.decompress` 后落盘 → 写 `repack_info.json`（{条目序: [hex(crc), 内部路径]}）
- 回包：读 repack_info.json → 从磁盘读文件 → `UncompressedSize=CompressedSize=len`、`data_crc=obscureCRC32(数据)`、type=0；压缩模式则 `lzokay.compress` 后 type=1 → 重写 16B 头 + 24B 条目头 + 数据
- **条目 name_crc 与目录结构原样保留**；改动文件内容只需保证磁盘文件正确，CRC 由工具重算

---

## 3. 游戏内部真实路径（datapack.hvp 1449 条目 / cachpack.hvp 316 条目，字典 100% 覆盖）

### 3.1 datapack.hvp（885,836,666 B，header_crc=0xE646A27A）

```
data/                                ← 根目录条目[0]
├── characters/  (46)   boy0..gir4/nleo/jedi/ken1-3/moth/npc1-4/homm/fly/aura + skins/
├── fx/         (2)
├── kines/      (1)
├── levels/     (11)
├── menus/      (12)                  ← 旧称 x_data/unk_folder_1920272591
│   ├── debug.xmc
│   ├── font_arial14b.xmc    (usize=10,620)   旧称 unk_file_1075623915.dat
│   ├── font_mkabel12.xmc    (usize=1,052)    旧称 unk_file_2405740849.dat
│   ├── font_nonserif12.xmc  (usize=12,684)   旧称 unk_file_3530817756.dat ★线程B目标
│   ├── font_smallfonts7.xmc (usize=10,380)   旧称 unk_file_2848500833.dat
│   ├── inventory_pc.xmc / inv_live.xmc / mc.xmc
│   ├── menu_pc.xmc / pause_pc.xmc / save.xmc
│   └── texpc/  (216 = 126 bmp + 90 tga)      旧称 unk_folder_1743701727
├── projects/  (7)
├── sounds/    (2)
├── strings/   (5)                   ← 旧称 x_data/unk_folder_3030018805 ★线程A目标
│   ├── de.lng (usize=251,522)
│   ├── en.lng (usize=226,997, lzo csize=90,402, off=879984559, dcrc=0x3BD74265) ★
│   ├── fr.lng (usize=242,038)
│   ├── it.lng (usize=239,299)
│   └── sp.lng (usize=245,240)       ← 注意：西语真名 sp.lng（非 es.lng）
└── texpc_pc.dic (usize=17,012,191, lzo csize=5,477,393)  ← 字体图集容器，旧称 unk_file_1507403136.dat
```

### 3.2 cachpack.hvp（908,374 B，header_crc=0x0B5EB503，316 条目）

```
data/
├── assets/ (10): chain/crank2/cupb/digicode/dispenser/hacking/items(33)/lockpick/puzzle/rowboat
├── levels/ (11): a(3) b(20) c(13) d(4) e(15) f(9) g(6) h(7) i(17) j(7) k(3)
└── sounds/ (24): music_01..12.hoe + sd_01..12.hoe
```

---

## 4. 对两条线程的影响

### 线程 A（文本回写器）
- 目标文件真名 = `strings/en.lng`；de/fr/it/sp 四个容器为同构参照（可做跨语种结构校验）
- en.lng 原包为 LZO 存储（90,402→226,997）；回包器必须保持 type=1 或按官方逻辑改 type=0（游戏两种都认——Gate 0 已实证）
- 偏移基准：原版 en.lng 数据区 off=879,984,559（原版 md5 `04a96eff…` 下的绝对偏移，仅供交叉验证）

### 线程 B（字体视觉原型）
- 菜单字体真名 = `menus/font_nonserif12.xmc`（usize=12,684 与侦察解析的 12,684 B 完全一致，互相印证）
- 图集容器真名 = `data/texpc_pc.dic`（17,012,191 B，fmt=21=32bpp RGBA）
- mkabel12 仅 12 个数字字形（0-9//-）再次被独立证据链确认（usize=1,052 B vs nonserif12 12,684 B）

---

## 5. 未解项（不影响工程）

- **name→crc 正向函数未复现**：hashes.json 的 key 与值之间不是对名字做已试变换（plain/cp932/NUL 结尾/大小写/常见路径前缀/UTF-16/双字节序共 108 种）能命中的关系；但**工程上不需要正向计算**——回包时 name_crc 从原包保留即可（官方工具同样如此）。真名反查（crc→name）已 100% 可用。
- 官方 `hashes.json` 仅覆盖静态资源名；`.lng` 内部记录 key 的语义不在本工具范畴。

---

## 6. 证据索引

- 反汇编产物：`hvfp/hvfilepacker__main__.dis`（1,824 行）、`hvfp/hvfilepacker__init__.dis`
- 校验脚本：`hvfp/verify_crc.py`、`hvfp/dump_tree.py`
- 原版锚点：datapack.hvp md5 `04a96eff7978cf31e66e9354421f1516`；en.lng 条目 dcrc=0x3BD74265 / header_crc=0xE646A27A 均已 MATCH
- texpc/ = 126 bmp + 90 tga = 216（解释早前"126 BMP"口径：当时仅统计了 .bmp）

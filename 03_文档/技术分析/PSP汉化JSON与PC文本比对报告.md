# PSP 汉化 JSON 与 PC 文本可行性比对报告

> 性质：**只读比对**。未修改 `translation_obscure2.json`、未修改任何 TSV/游戏文件、未开始 Gate 0。
> 输入：`E:/SteamLibrary/steamapps/common/Obscure2/translation_obscure2.json`（PSP 版汉化工程文件，984,216 B）
> 对照：`.workbuddy/recon/o2_text_en.tsv`（PC 版英文原稿，3,844 条）
> 分析脚本：`recon/psp_pc_compare.py`、`recon/psp_pc_deep.py`、`recon/psp_pc_deep2.py`、`recon/pc_reuse_profile.py`

---

## 0. 结论（先行）

**翻译工作基于 PSP JSON 转换，不从零开始。**

| 指标 | 数值 |
|---|---|
| PC 3,844 条中**有可用中文译文、可直接复用** | **3,745 条（97.4%）** |
| 需新翻译（PC 有、PSP 无英文对应） | 44 条（1.1%） |
| 需补译（PSP 有英文但未译） | 3 条（0.1%） |
| 人名/符号/按钮字形占位（无需翻译） | 52 条（1.4%） |
| 复用条目中需标签适配 | 9 条（0.2%） |
| 复用条目中需换行重排 | 408 条（10.9%） |

> 精修说明（2026-10-18 转换器落地时）：初版画像 D=3,770 / B=27 采用松定义（译文非空即算可用）；`psp_to_pc.py` 进一步发现其中 25 条为「纯标签译文」——PC 原文本身是空格或 `<PS2_CIRCLE>` 类按钮字形占位，PSP 译文去掉标签后无实际文字，无可复用内容。该 25 条重分类为 B（保留原文、无需翻译），得精修画像 **D=3,745 / B=52**，A/C 不受影响。标签适配存疑也从 31 条降至 9 条（22 条为退化用例）。以 `psp_to_pc.py` 控制台对账（PASS）为准。

PSP 译文质量经 20 条随机抽样语义核对，**全部匹配**（见 §3）。

---

## 1. PSP 汉化 JSON 解析结果

### 1.1 元数据

```json
{
  "description": "Obscure 2 translation file. Fill in \"chinese\" fields and run import.",
  "total_entries": 3116,
  "val1": 4448,        // = 3116 主条目 + 1332 个子条目（subs）
  "val2": 3116,
  "entries": [ ... ]
}
```

### 1.2 总条目数

| 层级 | 数量 |
|---|---|
| 主条目（entries） | **3,116** |
| 子条目（subs，挂在主条目下的变体） | 1,332（356 个主条目携带；仅 73 个去重 id） |
| 翻译单元合计 | **4,448**（= val1，自洽） |

### 1.3 数据结构示例（前 5 条）

```json
{
  "id": 67108865, "flag1": 1, "flag2": 0,
  "english": "Player 2 is joining the game.\n\nDo you want player 2\nto take control of the team member?\n\n<PS2_CROSS> OK          <PS2_TRIANGLE> Cancel",
  "chinese": "玩家2正在加入游戏。\n\n你想让玩家2控制这名队友吗？\n\n <PS2_CROSS> 确定 <PS2_TRIANGLE> 取消",
  "subs": []
}
{
  "id": 67108866, "flag1": 1, "flag2": 0,
  "english": "No team member is available for the \nmoment. \n\n<PS2_TRIANGLE> Cancel",
  "chinese": "目前没有可用的队友。\n\n <PS2_TRIANGLE> 取消", "subs": []
}
{
  "id": 67108867, ... "english": "Player 2 is leaving the game.\n\n<PS2_CROSS> OK          <PS2_TRIANGLE> Cancel",
  "chinese": "玩家2正在离开游戏。\n\n <PS2_CROSS> 确定 <PS2_TRIANGLE> 取消", "subs": []
}
{
  "id": 67108868, ... "english": "Are you sure that you want\nplayer 2 to leave the game?\n\n<PS2_CROSS> Yes ...",
  "chinese": "你确定要让玩家2离开游戏吗？\n\n <PS2_CROSS> 是 <PS2_TRIANGLE> 否", "subs": []
}
{
  "id": 67108869, ... "english": "Press <PS2_CROSS>", "chinese": "按 <PS2_CROSS> ", "subs": []
}
```

subs 示例（主条目 id=67108894 下的 2 个变体，各自带 id/english/chinese）：

```json
{"id": 65536,  "english": "Adjust the brightness so that the right square is visible\nand the left square is invisible. Use <PS2_TOP> and <PS2_BOTTOM>.", "chinese": "调整亮度使右侧方块可见，左侧方块不可见。使用 <PS2_TOP> 和 <PS2_BOTTOM>。"}
{"id": 196608, "english": "Adjust the brightness of your television so that the \nright square is visible and the left square is invisible.", "chinese": "调整电视的亮度，使右侧的方块可见，左侧的方块不可见。"}
```

**PSP 侧完备度**：3,116 主条目中 3,109 条（99.8%）有中文；57 条中文==英文（经查全部是人名/符号类：BACH/BELL/DALI/KANT/MOZART/NEWTON/PLANCK/EDISON 等谜题答案与 `\`、`>`、`<`、空格，属正确的不译）。

---

## 2. Key / 索引比对：**不通用，必须按英文原文匹配**

| 维度 | PSP JSON | PC TSV |
|---|---|---|
| 标识字段 | `id`（主条目）/ subs 自带 `id` | `key`（u32） |
| 取值范围 | 0x04000001 ~ 0x88700024 | 0x0 ~ 0xEE003304 |
| 去重数 | 3,116（主）+ 73（subs） | 2,590 |
| **两者交集** | **仅 9 个（0.3%）** | — |

结论：**PSP id 与 PC key 是两套独立编号，不能按 key 对齐**。且 PC 侧 key 本身不唯一——57 个 key 下挂 1,311 条**互不相同**的记录（如 key=256 同时是 "Keystroke configuration"、"You are starting the story in \"1 player\" mode..." 等），说明 PC key 不是文本唯一标识，**按英文原文（归一化）匹配是唯一可靠对齐方式**。

归一化规则：去手柄标签 `<XXX>` + 去全部空白（换行/空格）后精确比对。

---

## 3. 英文原文匹配与抽样语义核对

### 3.1 匹配率

| 匹配对象 | 结果 |
|---|---|
| PSP 主条目 → PC（归一化英文） | 2,493 / 3,116（80.0%） |
| PSP 主+subs（4,448 单元）→ PC | 3,815 / 4,448（85.8%） |
| **PC 3,844 条被 PSP 英文覆盖** | **3,800 / 3,844（98.9%）** |

### 3.2 随机抽样 20 条语义核对（seed=42）

抽样自英文精确匹配的 2,493 对，逐条人工核对「PSP 英文 == PC 英文」且「PSP 中文语义对应」：

| # | 英文原文（两版一致） | PSP 中文 | 语义 |
|---|---|---|---|
| 01 | Then keep your eyes on my face, not anywhere else. | 那你最好看着我的脸，别乱瞟其他地方。 | ✓ |
| 02 | Something has changed in you... | 你身上发生了一些改变… | ✓ |
| 03 | What are these things? | 这些东西到底是什么？ | ✓ |
| 04 | But I served my time without protesting. | 但我老老实实地坐完了牢，没有任何怨言。 | ✓ |
| 05 | Formatting memory card (8MB) (for PlayStation®2)... | 正在格式化插槽2中的记忆卡(8MB)... | ✓ |
| 06 | It's closed, but there's glass in the door... | 门虽然关着，不过门上有块玻璃… | ✓ |
| 07 | Oh no! | 啊不！ | ✓ |
| 08 | \<PS2_STICKL\> | ` <PS2_STICKL> ` | ✓（⚠️ PC 原文该处为空串，标签差异，见 §5） |
| 09 | Impossible to hack that! We have to find another way. Fast! | 根本没办法黑进去！\n我们必须另想办法。快！ | ✓ |
| 10 | Go on land | 上岸 | ✓ |
| 11 | Samples that I would avoid breaking. | 一些我可绝不想碰碎的化验样本。 | ✓ |
| 12 | Come on Sven, it's your turn to get moving now! | 来吧，斯文，轮到你动起来了！ | ✓ |
| 13 | I should have known... | 我早该知道的… | ✓ |
| 14 | Mei? | 梅？ | ✓ |
| 15 | You mean a date without guns? That'll be strange. | 你是说一次不带枪的约会？那感觉可真够奇怪的。 | ✓ |
| 16 | Loading data. Do not remove memory card... | 正在读取数据。\n请勿拔出记忆卡... | ✓ |
| 17 | An old and moldy class photo on the wall. | 墙上挂着一张发霉的旧毕业合影。 | ✓ |
| 18 | Following a recent fire in my room I am looking for... | 鉴于我的房间最近失火，现求购心理学专业课程书籍... | ✓ |
| 19 | What a mess. It looks like a squat. | 这鬼地方太烂了，跟难民营似的。 | ✓ |
| 20 | A President of the United States was part of this fraternity of weirdos? | 美国总统居然也曾是这个由变态组成的兄弟会的成员？ | ✓ |

**20/20 语义匹配，无一错配。** 注：PSP 版标题为 "Obscure: The Aftermath"（欧版），PC 版为 "Obscure 2"（美版），存在系统性标题用词差异（见 §4）。

---

## 4. 未匹配部分分析（623 条 PSP 主条目无 PC 英文对应）

| 类别 | 数量 | 说明 |
|---|---|---|
| PSP 独有内容 | 459 | PSP 版独有的对话/文档变体（如 Stan 开场白、Leafmore 回忆等长文本在 PC 有近似但不同的版本） |
| 疑似措辞变体（模糊 0.75-0.95） | 75 | 如 "HE CRASHED MY BABY!! THE BASTARD!!!!" vs PC "HE CRASHED MY BABY!!! THAT BASTARD!!!!"；"Amy: Don't you think..."（PSP 带说话人名前缀，PC 无） |
| 极短串（<12 字符） | 32 | 标点、单字 |
| PSP/PS2 专属 | 30 | Wii Remote/Nunchuk 提示、Memory Stick Duo 存档提示等（例：'Connect Nunchuk to the (P2) Wii Remote.'） |
| 疑似标题/拼写变体（模糊 ≥0.95） | 22 | 如 'Leonardo Da Vinci' vs PC 'Leonard De Vinci'；'knew it' vs 'knew of it' |
| 标题差异（The Aftermath） | 5 | 版权声明、存档提示等含 "Obscure: The Aftermath" 字样 |

对 PC 侧无影响——这些是 PSP 多余条目，PC 的 3,844 条中已有 98.9% 被覆盖。

**PC 未被覆盖的 44 条**（需新翻译）：9 条 PC 专属菜单短串（Keystroke configuration / Sound / Vibration / Mono / Stereo / Video options / Resolution / Depth / Apply）+ 35 条长文本变体（对话措辞差异、文档变体、PS2 记忆卡提示的 PC 版本）。全清单见 `pc_reuse_profile.py` 输出。

---

## 5. 复用条目的适配需求（3,745 条）

| 适配项 | 数量 | 占比 | 处理方式 |
|---|---|---|---|
| 文本完全一致（英文逐字节相同，中文可直接落位） | 3,728 | 98.9% | 直接用 |
| 标签序列不同（PSP 译文含 PC 原文没有的标签） | 34 | 0.9% | 转换时按 PC 原文标签序列校正（如 PC 空串处删掉 `<PS2_STICKL>`） |
| 换行数不同（PSP 译文换行结构与 PC 原文不一致） | 408 | 10.8% | 转换时以 PC 原文换行为模板重排，或接受译文换行（需 UI 布局验证） |
| 中/英字节比 >1.5× | 409 | 10.8% | 同上，长文本需关注 UI 宽度（沿一代经验） |

标签生态说明：PC 原文中同时存在 `<PS2_*>`（PS2 移植遗留）与 `<PC_RELOAD>/<PC_MOUSE1-3>` 标签；PSP 译文标签分布与 PC 原文高度一致（差异仅 34/3770），标签体系天然兼容。

---

## 6. 结论与转换脚本需求

### 6.1 最终画像（PC 3,844 条）

| 类别 | 条数 | 占比 | 动作 |
|---|---|---|---|
| **D. 有可用中文，直接复用** | **3,745** | **97.4%** | 转换脚本自动完成（含 9 条标签校正 + 408 条换行标记） |
| A. 无英文匹配 | 44 | 1.1% | 人工新译（9 条短菜单 + 35 条长文本） |
| C. 有英文匹配但 PSP 未译 | 3 | 0.1% | 人工补译（硝酸甘油配方 ×2 + 一行 aaaa 占位乱码） |
| B. 人名/符号/按钮字形占位 | 52 | 1.4% | 不译，保留英文 |

### 6.2 转换脚本需求（若决定基于 PSP JSON 转换）

需要新写一个 `psp_to_pc.py`（只读输入、产出 PC 侧译文表，不直接改游戏文件）：

1. **索引构建**：解析 JSON 全部 4,448 个翻译单元，按「归一化英文」建 `text → [chinese...]` 映射（取第一个非空且 ≠ 英文的译文）。
2. **PC 记录遍历**：解析 en TSV 3,844 条（保留 off/key/type/len），逐条查映射：
   - 命中且译文可用 → 产出 `(off, key, type, zh)`；
   - 标签序列不一致 → 按 PC 原文标签序列重写译文标签，无法自动处理的进人工队列；
   - 换行不一致 → 以 PC 原文换行结构重排译文（或标记待 UI 验证）；
   - 未命中/无译文 → 进人工队列（A/C 类共 47 条）。
3. **产出**：PC 侧中文 TSV/JSON（`o2_text_zh.tsv`，字段对齐 en TSV），供后续文本容器回写器（Gate 0 的部署链路）消费。
4. **校验**：转换后统计四类条数，与 §6.1 画像对账（3,745/44/3/52 必须复现）；人工队列清单单独输出。

脚本预估工作量：约 150-200 行，纯文本处理，无二进制风险。**注意：转换产物仍只是工作文件，落地仍需走已实测的 datapack 回包链路（见可行性报告 §1.3）。**

### 6.3 决策建议

**基于 PSP JSON 转换。** 97.4% 直接复用 + 20/20 抽样语义验证通过，人工量从 3,844 条降至 47 条（且其中 9 条是菜单短串）。PSP 工程文件本身的完成度（99.8%）也表明这是一份成熟汉化，非半成品。

---

## 7. 下一步

比对完成，按约定**立刻进入 Gate 0**：用已实测的 datapack 回包链路，对 en 容器做 1 条无害文本替换 → 实机加载 → 验证游戏接受改包（化解可行性报告 R1 风险）。Gate 0 通过后，再写 §6.2 的 `psp_to_pc.py` 转换脚本。

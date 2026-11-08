# 字体方案 A/B · 生成与验证报告（2026-10-22）

本报告记录 V1.01 两套字体方案的生成过程、单变量证明与验证数据，
供后续维护/复现使用。脚本全部在 `02_源码/产线工具/`。

## 一、背景：为什么从生成侧抢救

`options.xml` 的 VideoResolution 为 2560×1440 原生，但引擎把 UI 按 540p 设计分辨率
绘制后拉伸 —— 屏幕汉字 advance ≈42px，而图集里只有 19px 的字形信息量（k≈2.8）。
hook 改投影矩阵的路线已判定不可行（UI 顶点 FVF 全 `0x144`(XYZRHW) 预变换，
绕过投影矩阵），且会破坏 v49 封盘状态。因此在**图集生成侧**做两件事：

- **方案 A**：换用笔画更重的黑体，同等像素预算下拉伸后更保墨；
- **方案 B**：同字形、提高超采样倍率并换 Lanczos 降采样，改善边缘灰阶。

## 二、架构前提：图集在 DLL，def 在 datapack

- datapack 的 dic 内仍是**原版 512×256 英文纹理**（`unk_file_1507403136.dat`，
  与只读基线 x_orig 同字节）——中文图集像素**只存在于 `d3d9.dll`**（`atlas_png.h`，
  hook 运行时替换显存字体纹理）；
- datapack 里的 def（`unk_folder_1920272591/unk_file_3530817756.dat`）保存每个字形的
  cp/坐标/宽高，引擎按它排布；**def 与图集必须成对**。

推论：换字形（A）→ def 几何变 → 数据包必须换；只改渲染质量（B）→ def 逐字节不变 →
数据包就是 full18。

## 三、方案 A：寒蝉端黑体 Bold

- 字体：`_work/fonts/ChillDuanSans_Bold.otf`（寒蝉端黑体系列，OFL 1.1，可再分发）
- 覆盖率：charset 需渲染 2171 新增 + 95 可打印 ASCII，**零缺失**（fontTools 核对）
- 渲染参数与基线一致：20px / SSAA=3 / BOX / 盒 19×25 / 灰度 232 / BASE_Y=20
- 度量差异：`PITCH_X` 21→22（黑体最宽 ASCII advance=20）、汉字墨高 16→19、
  CJK 基线偏移 oy=0（活楷为 2）
- 槽位：2622 可用，使用 2261，余 361
- 产物：`g4_A/g3_atlas.png`（`22ffed60…`，848,993 B）、`g4_A/g3_font_nonserif12.xmc`
  （`89e4e7a4…`，205,079 B）、`g4_A/g3_layout.tsv`、构建/def 自验证报告

数据包：`deploy/datapack_zh_fullA.hvp`（885,935,872 B，`e657e90d…`）；
与 full18 抽包比对 **1240 个文件仅 def 一个不同**。

## 四、方案 B：活楷 + SSAA4 + Lanczos

- 字体：`_work/fonts/ChillHuoKai_Regular.otf`（不变）
- 渲染：SSAA 3→4（80px 渲染）、降采样 BOX→LANCZOS
- 几何：`PITCH_X=21`、槽位 2774 用 2261 —— 与基线**完全一致**；
  **def md5 = `08ac3869…` 与 V1.00 逐字节相同**（几何不变的强证明）
- 产物：`g4_B/g3_atlas.png`（`c1794fa2…`，973,622 B；PNG 变大是因 Lanczos
  带来更丰富的灰阶过渡）、`g4_B/g3_font_nonserif12.xmc`（同 `08ac3869…`）
- 已知代价：Lanczos 有轻微振铃（边缘灰晕），墨量约 +5.6%；是否可接受需实拍判断

## 五、工具链复刻（v49 逐字节复现）

两套测试 DLL 必须与 v49 **只差图集**，因此先证明构建可复现：

1. 直接按文档命令编译，得到的 DLL 与 v49 大小相同（890,298 B）但 md5 不同；
2. 反汇编比对：指令流**完全一致**（仅绝对地址不同）→ 差异来自 **ImageBase**；
3. 根因：ld 的 auto-image-base **按输出文件名哈希**定基址
   （`d3d9_v49.dll`→`0x65D80000`、`d3d9.dll`→`0x6FB40000`，都不是 v49 的 `0x6BE00000`）；
   `--disable-auto-image-base` 得 `0x10000000`，也不对；
4. **正解**：显式钉基址 —— 对照构建 md5 = `47060c4b…` 与出厂 v49 逐字节一致。

最终编译命令（v49 同款）：
```
i686-w64-mingw32-gcc -O2 -fno-sanitize=undefined -shared \
  -DFORCE_POINT_SAMPLER=0 -Wl,--image-base=0x6BE00000 \
  -o d3d9.dll d3d9_proxy.c d3d9.def
```

单变量判定：
- A/B 与 v49 的规范化反汇编**仅差 2 条指令** —— `movl $len`（g_atlasPngLen 立即数
  822706→848993 / 973622）；
- 其余字节差异 = PE 头尺寸字段 + PNG 数组 + 链接器随数组增大改写的 .rdata 指针
  （加载器重定位自动处理）。

## 六、验证汇总

| 项 | 结果 |
|---|---|
| 对照构建 vs 出厂 v49 | md5 `47060c4b` **逐字节一致** |
| A/B vs v49 指令流 | 仅差图集长度立即数 |
| fullA vs full18 抽包 | 1240 文件仅 def 不同 |
| 方案 A def 自验证 | gate3_def 全通过（155 原版条目逐字节保留） |
| 方案 B def | 与 V1.00 **逐字节相同** `08ac3869` |
| 安装器 `/test`（B） | rc=0，落盘 `d25123d2` + `47060c4b` |
| 安装器 `/testA`（A） | rc=0，落盘 `e657e90d` + `0e504ff0` |
| 杂散文件 | 两次安装均无（`d3d9_a.dll`/`datapack_a.hvp` 不会落到游戏目录） |

## 七、复现步骤

```
# 1) 变体脚本（字节级改 CONFIG；注意 RECON 需绝对路径）
python _work/_fonttest/make_variants.py
# 2) 图集 + def
python _work/_fonttest/gate3_atlas_A.py && python _work/_fonttest/gate3_def_A.py
python _work/_fonttest/gate3_atlas_B.py && python _work/_fonttest/gate3_def_B.py
# 3) 测试 DLL（含 v49 对照构建校验）
python _work/_fonttest/build_test_dlls.py
# 4) 数据包：硬链接复制装配树 → 换 def_A → obscure-hvp create
#    （或直接 python -c 见 _work/_fonttest 里的打包命令注释）
# 5) 差分
python installer/make_delta.py 基线_原版/datapack.hvp.gate3_orig \
       deploy/datapack_zh_fullA.hvp deploy/datapack_a.delta
# 6) 安装器（六载荷）
python installer/build_all.py
# 7) 交付前验证
python _verify/verify_v101.py
```

## 八、注意事项

- **改 CONFIG 必须复跑图集比对**：2026-10-21 曾发生 `g3_layout.tsv` 被 22px 实验覆盖，
  导致 2261 处几何错位；
- 方案 A 的字体度量与活楷不同，**def 不能与方案 B 混用**（混用会白块/错位）；
- 寒蝉端黑体本机只有 Bold 单字重可用（字体包 zip 曾为残缺断点下载；
  完整包 `D:\ChillDuanSans.v1.30.zip` 若可用，可再评估 Regular 字重）；
- 图集尺寸仍是 2048×1024（三处同步铁律不变）。

# CONFIG 复现验证：图集 20px / 盒19×25 / SSAA=3（2026-10-21）

## 背景
用户反馈「字体参数感觉有变化，有点模糊」。排查发现
`scripts_gate3/gate3_atlas.py` 的 CONFIG 与出厂产物不符：
代码是 `FONT_SIZE=22 / BOX_W=21 / PITCH_X=23 / BASE_Y=19 / SSAA=1`，
而注释、记忆基线与出厂文件全都指向 20px 版。

## 证据链

### 1. 出厂三件套彼此一致（未漂移）
| 文件 | md5 |
|---|---|
| `deploy/g3_atlas.png`（图集） | `e172a188651c68464ff3946683c3f5c9` |
| `deploy/g3_font_nonserif12.xmc`（def） | `08ac3869562b5dacb3f9a66775cefbd5` |
| `_work/x_pristine/.../unk_file_3530817756.dat`（def 进树） | `08ac3869562b5dacb3f9a66775cefbd5` |
| `d3d9proxy_src/atlas_png.h`（DLL 内嵌图集源） | 同 `e172a188…`（注释标明） |

出厂 def 解析：2326 字形（155 + 2171 新增），atlas 2048×1024，
**CJK 盒宽 = 19**（distinct w = [4..16, 19]），x 最大 2024 → 73 列 → **pitch 21**。
→ 与 22px/21 盒/23 pitch 的脚本 CONFIG 完全不符。

### 2. 像素级验证：出厂图集与出厂 def 几何配对
按 def 盒坐标直接从出厂 PNG 解码 alpha，你/好/游/戏/回 五字墨迹完整居中，
无越界、无错位。

### 3. 决定性复现（md5 逐字节一致）
用假设参数 `FONT_SIZE=20, BOX_W=19, BOX_H=25, PITCH_X=21, PITCH_Y=27,
BASE_Y=20, SSAA=3` 重跑图集脚本：

```
_repro/g3_atlas.png  md5 = e172a188651c68464ff3946683c3f5c9  ← 与出厂完全一致
_repro/g3_layout.tsv 与出厂 def 几何不一致数 = 0（2326 字形全覆盖）
```

## 结论
1. **出厂渲染参数从未变化**，模糊不是参数漂移造成的，
   根因是 UI 层被放大 k≈2.8（屏幕字宽 ≈42px vs 图集 advance 19px），
   纹理信息量不足，属数学必然（见项目记忆「发糊根因」节）。
2. 脚本 CONFIG 曾被改成 22px/SSAA=1，与注释、记忆、出厂产物三方矛盾；
   且 g4 遗留的 `g3_layout.tsv` 是 22px 版，与出厂 def 有 **2261 处几何错位**
   ——谁拿它重跑 `gate3_def.py` 就会产出盒宽 21 的错位 def。

## 已修复
- `scripts_gate3/gate3_atlas.py`：CONFIG 改回 20px/19 盒/21 pitch/BASE_Y=20/SSAA=3，
  同步修正 docstring、注释、报告模板（含 LANCZOS→BOX、msyh.ttc→活楷体 OFL 等过时表述）。
- `_work/g4/g3_layout.tsv`、`g3_atlas_report.txt`：替换为 20px 正确版
  （layout 与出厂 def 几何 0 不一致，复验通过）。
- 修复后脚本再次复现 `e172a188…`，闭环。

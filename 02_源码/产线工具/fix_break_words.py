# -*- coding: utf-8 -*-
"""fix_break_words.py — 扫描并修复译语换行拆词 / 标点避头尾问题（jieba 分词版）
==========================================================================
问题（用户实测反馈）:
  你将以“单人”模式开始故事。
  第二名玩家随时可以按回车键加入游
  戏，并接管你的队友。          ← "游戏" 被拦断拆到两行

判据:
  A. 换行拆词: jieba 对 (行i内容 + 行i+1内容) 连续分词,
     若某个 token 跨越两行边界 → 该词被拦断。
     （2026-10-21 从"统计双字组"升级为 jieba 真分词:
      统计法把"在地球的|各大"误报成词"的各", 又漏掉只出现在断点上的"科学成|果"。）
  B. 标点避头尾: 行首出现不能起行的标点（，。！？；：、）》〉」』”’… 及 ASCII , . ! ? ; : ) ] % }）
     或行尾出现不能收尾的开括号（（《〈“‘【〔［{ 及 ASCII ( [ {）。

修复算法（最小改动, 行数不变, 行宽不增）:
  对每个出问题的换行点, 尝试把断点左右移动 k=±1..±3 个字符
  （只移动非空白内容, 行尾空格原位保留）, 候选须同时满足:
    1. 移动后两行均非空
    2. 该记录所有行宽(全角=1, 半角=0.5) <= 原最大行宽
    3. jieba 复检该记录所有换行点: 当前点已修复且不引入新违规
  按 |k| 从小到大, k>0 优先（词整体流到下一行行首）。
  找不到候选 → 进"待人工"清单, 不改。

用法:
  python fix_break_words.py            # 只扫描, 出报告, 不动文件
  python fix_break_words.py --fix      # 写出 _work/o2_text_zh_full13.tsv
"""
import csv
import os
import sys
import unicodedata

import jieba

jieba.setLogLevel(60)

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SRC = os.path.join(ROOT, '_work', 'o2_text_zh_full12.tsv')
DST = os.path.join(ROOT, '_work', 'o2_text_zh_full13.tsv')
REPORT = os.path.join(HERE, 'break_word_report.md')

MAX_SHIFT = 3         # 最大移动字符数

# 已人工核实的排除项（不进入自动修复, 理由记入报告）
EXCLUDE = {
    564:  'jieba 误合：“服务器上|存了”被切成 token“上存”（词典词，此语境不适用），自然断行',
    1067: 'jieba 误合：“）中|未发现”被切成 token“中未”（法律文本词，此语境不适用），自然断行',
    1068: 'jieba 误合：同 1067',
    2019: '英文原文第 2 行本身以 "..." 开头（The ceiling has collapsed... / ...someone could have been underneath...），中文如实对应，不做改动',
    3757: '调试占位文本（en 与 zh 均为 aaaa 串，无实际显示内容）',
    3780: 'jieba 误合：“还在动|植物”被切成 token“动植物”；动属上句“还在动”，自然断行',
}

NO_LINE_START = set('，。！？；：、）》〉」』”’…、′″℃）】］], .!?;:)]%}')
NO_LINE_END = set('（《〈“‘【〔［{(')


def width(s):
    """全角=1, 半角=0.5（东亚宽 W/F 记 1）"""
    w = 0.0
    for ch in s:
        if unicodedata.east_asian_width(ch) in ('W', 'F'):
            w += 1.0
        else:
            w += 0.5
    return w


def split_ws(line):
    """拆成 (内容, 行尾空白)"""
    core = line.rstrip(' \t')
    return core, line[len(core):]


def load(path):
    with open(path, encoding='utf-8-sig', newline='') as f:
        rd = csv.reader(f, delimiter='\t')
        hdr = next(rd)
        return hdr, list(rd)


def spanning_token(a, b):
    """jieba 分词: 返回跨越 (a|b) 边界的 token, 无则 None。
    a/b 已去首尾空白。"""
    joined = a + b
    cut = len(a)
    off = 0
    for tok in jieba.cut(joined):
        n = len(tok)
        if n >= 2 and off < cut < off + n:
            return tok
        off += n
    return None


def break_violation(lines, i):
    """换行点 i（lines[i] | lines[i+1]）的违规描述, 无则 None"""
    a, b = lines[i], lines[i + 1]
    ca, _ = split_ws(a)
    cb, _ = split_ws(b)
    if not ca or not cb:
        return None                      # 段落间空行, 不是换行点
    c1 = ca[-1]
    c2 = cb.lstrip(' \t')[0]
    if c2 in NO_LINE_START:
        return '行首标点(%s)' % c2
    if c1 in NO_LINE_END:
        return '行尾开括号(%s)' % c1
    tok = spanning_token(ca, cb.lstrip(' \t'))
    if tok:
        return '拆词(%s)' % tok
    return None


def all_violations(lines):
    out = {}
    for i in range(len(lines) - 1):
        v = break_violation(lines, i)
        if v:
            out[i] = v
    return out


def try_shift(lines, i, k):
    """把 k 个字符从 lines[i] 移到 lines[i+1]（k>0）或反向（k<0）。失败返回 None"""
    a, b = lines[i], lines[i + 1]
    ca, ta = split_ws(a)
    cb, tb = split_ws(b)
    if k > 0:
        if len(ca) <= k:
            return None
        moved, ca2 = ca[-k:], ca[:-k]
        if cb.startswith(' '):
            return None                  # 目标行有前导缩排, 交人工
        cb2 = moved + cb
    else:
        k = -k
        if len(cb) <= k:
            return None
        moved, cb2 = cb[:k], cb[k:]
        if not moved.strip():
            return None
        ca2 = ca + moved
    if not ca2 or not cb2:
        return None
    new = list(lines)
    new[i] = ca2 + ta
    new[i + 1] = cb2 + tb
    if max(width(l) for l in new) > max(width(l) for l in lines) + 1e-9:
        return None
    return new


def fix_record(lines):
    """返回 (新 lines, [(换行点, 违规, 采用的 k, 说明)])"""
    changes = []
    lines = list(lines)
    for _round in range(8):
        v = all_violations(lines)
        if not v:
            break
        i = min(v)
        done = False
        for k in [1, -1, 2, -2, 3, -3]:
            cand = try_shift(lines, i, k)
            if cand is None:
                continue
            v2 = all_violations(cand)
            if i not in v2 and not (set(v2) - set(v)):
                lines = cand
                changes.append((i, v[i], k, '…%s ⇄ %s…' % (
                    lines[i][-6:], lines[i + 1][:6])))
                done = True
                break
        if not done:
            changes.append((i, v[i], None, '无可行最小移位, 待人工'))
            break
    return lines, changes


def main():
    fix_mode = '--fix' in sys.argv
    hdr, rows = load(SRC)
    print('语料: %s (%d 行)' % (SRC, len(rows)))
    jieba.initialize()

    n_multi = n_fixed_rec = n_manual = 0
    fixed_detail, manual_detail = [], []
    excluded_detail = []
    out_rows = []
    for idx, row in enumerate(rows):
        if len(row) < 9:
            out_rows.append(row)
            continue
        zh = row[8]
        if '\n' in zh and zh.strip():
            n_multi += 1
        if not zh.strip() or '\n' not in zh:
            out_rows.append(row)
            continue
        lines = zh.split('\n')
        before = all_violations(lines)
        if idx in EXCLUDE:
            if before:
                excluded_detail.append((idx, row[1], row[7], zh, before,
                                        EXCLUDE[idx]))
            out_rows.append(row)
            continue
        if not before:
            out_rows.append(row)
            continue
        if not fix_mode:
            n_manual += 1
            manual_detail.append((idx, row[1], row[7], zh, before))
            out_rows.append(row)
            continue
        new_lines, changes = fix_record(lines)
        if new_lines != lines:
            n_fixed_rec += 1
            new_row = list(row)
            new_row[8] = '\n'.join(new_lines)
            out_rows.append(new_row)
            fixed_detail.append((idx, row[1], row[7], zh, '\n'.join(new_lines),
                                 changes))
        else:
            n_manual += 1
            manual_detail.append((idx, row[1], row[7], zh, before))

    print()
    print('多行译文记录: %d' % n_multi)
    print('违规记录: %d (自动修复 %d, 待人工 %d)'
          % (n_fixed_rec + n_manual, n_fixed_rec, n_manual))

    # ---- 报告 ----
    L = []
    L.append('# 译语换行拆词 / 标点避头尾 扫描修复报告（jieba 分词判据）')
    L.append('')
    L.append('- 语料: `_work/o2_text_zh_full12.tsv`（%d 行）' % len(rows))
    L.append('- 判据 A: jieba 对相邻两行连续分词, token 跨行即拆词')
    L.append('- 判据 B: 标点避头尾（行首禁则 / 行尾禁则）')
    L.append('- 修复: 最小移位 ±1..±3 字符, 行数不变, 行宽不增')
    L.append('- 结果: **修复 %d 条**，待人工 %d 条' % (n_fixed_rec, n_manual))
    L.append('')
    L.append('## 自动修复明细')
    L.append('')
    for idx, key, en, old, new, changes in fixed_detail:
        L.append('### idx=%d key=%s' % (idx, key))
        L.append('```')
        L.append('EN: ' + en.replace('\n', ' ⏎ '))
        L.append('旧: ' + old.replace('\n', ' ⏎ '))
        L.append('新: ' + new.replace('\n', ' ⏎ '))
        for (i, v, k, note) in changes:
            L.append('  换行点%d %s -> 移位 k=%s %s' % (i, v, k, note))
        L.append('```')
    if manual_detail:
        L.append('')
        L.append('## 待人工（无可行最小移位 / 扫描模式全列）')
        L.append('')
        for idx, key, en, zh, before in manual_detail:
            L.append('### idx=%d key=%s 违规=%s' % (idx, key, before))
            L.append('```')
            L.append('EN: ' + en.replace('\n', ' ⏎ '))
            L.append('ZH: ' + zh.replace('\n', ' ⏎ '))
            L.append('```')
    if excluded_detail:
        L.append('')
        L.append('## 已排除（人工核实后不改, 附理由）')
        L.append('')
        for idx, key, en, zh, before, why in excluded_detail:
            L.append('### idx=%d key=%s 违规=%s' % (idx, key, before))
            L.append('- 理由: %s' % why)
            L.append('```')
            L.append('EN: ' + en.replace('\n', ' ⏎ '))
            L.append('ZH: ' + zh.replace('\n', ' ⏎ '))
            L.append('```')
    with open(REPORT, 'w', encoding='utf-8') as f:
        f.write('\n'.join(L) + '\n')
    print('报告: %s' % REPORT)

    if fix_mode:
        with open(DST, 'w', encoding='utf-8-sig', newline='') as f:
            w = csv.writer(f, delimiter='\t', lineterminator='\r\n')
            w.writerow(hdr)
            for row in out_rows:
                w.writerow(row)
        print('写出: %s (%d 行)' % (DST, len(out_rows)))
    return 0


if __name__ == '__main__':
    sys.exit(main())

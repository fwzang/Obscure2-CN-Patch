# -*- coding: utf-8 -*-
"""gate3_packcheck.py — T6: 回包闭环验证

对比:
  A. x_pack_verify(新包解出) vs gate3/x_data(工作树)      -> 必须全等
  B. x_pack_verify vs recon/x_data(原版解出)              -> 只允许 6 个文件不同
     (5 文本容器 + 字体 def); dic 必须字节级不变
"""
import os, sys, hashlib, json

RECON = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PACK = os.path.join(RECON, 'gate3', 'x_pack_verify')
TREE = os.path.join(RECON, 'gate3', 'x_data')
ORIG = os.path.join(RECON, 'x_data')

EXPECT_DIFF = {
    'unk_folder_3030018805/unk_file_3866210045.dat',
    'unk_folder_3030018805/unk_file_1526549577.dat',
    'unk_folder_3030018805/unk_file_3962463896.dat',
    'unk_folder_3030018805/unk_file_3321210576.dat',
    'unk_folder_3030018805/unk_file_3152273829.dat',
    'unk_folder_1920272591/unk_file_3530817756.dat',
}
DIC = 'unk_file_1507403136.dat'


def md5(p):
    h = hashlib.md5()
    with open(p, 'rb') as f:
        while True:
            b = f.read(1 << 20)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def walk(root):
    out = {}
    for r, dirs, files in os.walk(root):
        for f in files:
            p = os.path.join(r, f)
            out[os.path.relpath(p, root).replace('\\', '/')] = p
    return out


def main():
    print('=' * 74)
    print('T6: 回包闭环验证')
    print('=' * 74)
    pk = walk(PACK)
    tr = walk(TREE)
    og = walk(ORIG)
    print('[计数] 包解出 %d / 工作树 %d / 原版树 %d' % (len(pk), len(tr), len(og)))

    # A: 包 vs 工作树（豁免: hashes.json 由解包重生成; .tsv 旁车文件非包内文件）
    only_pk = set(pk) - set(tr)
    only_tr = set(tr) - set(pk)
    diff_a = [k for k in set(pk) & set(tr) if md5(pk[k]) != md5(tr[k])]
    print('\n[A] 包 vs 工作树: 仅包有 %d, 仅树有 %d, 内容不同 %d'
          % (len(only_pk), len(only_tr), len(diff_a)))
    if only_pk:
        print('    仅包有: %s' % sorted(only_pk)[:10])
    if only_tr:
        print('    仅树有: %s' % sorted(only_tr)[:10])
    if diff_a:
        print('    内容不同: %s' % sorted(diff_a)[:10])
    allow_tr = {k for k in only_tr if k.endswith('.tsv') or k == 'hashes.json'}
    allow_diff = {k for k in diff_a if k == 'hashes.json'}
    okA = (not only_pk and only_tr <= allow_tr and set(diff_a) <= allow_diff)
    print('    => %s' % ('全等（打包无损, 豁免项均为解包/旁车预期）' if okA else '存在差异!'))

    # B: 包 vs 原版树（hashes.json 由 obscure-hvp extract 重新生成, 非包内容差异, 豁免）
    only_pk2 = set(pk) - set(og)
    diff_b = [k for k in set(pk) & set(og) if md5(pk[k]) != md5(og[k])]
    print('\n[B] 包 vs 原版树: 仅包有 %d, 内容不同 %d' % (len(only_pk2), len(diff_b)))
    for k in sorted(diff_b):
        print('    差异: %s' % k)
    unexpected = [k for k in diff_b if k not in EXPECT_DIFF and k != 'hashes.json']
    missing = [k for k in EXPECT_DIFF if k not in diff_b]
    dic_same = md5(pk[DIC]) == md5(og[DIC])
    print('    预期外差异: %s ; 预期内未变: %s' % (
        unexpected if unexpected else '无', missing if missing else '无'))
    print('    dic(图集容器) 字节级不变: %s' % dic_same)
    okB = not unexpected and not missing and dic_same and not only_pk2

    print()
    print('★ T6 %s' % ('回包闭环验证通过' if (okA and okB) else '验证失败'))
    return 0 if (okA and okB) else 1


if __name__ == '__main__':
    sys.exit(main())

# -*- coding: utf-8 -*-
"""patch_gate_v22.py — 重排漏图门槛：以 ZENABLE 为主判据。

实机日志证据：
    atlas=487552  skipRhw=487552  skipOrtho=0  skipZoff=0
即 48 万次"图集已绑定时的绘制"**全部**被判成 SKIP(RHW) —— 这个引擎把 3D 顶点
也在 CPU 端变换后以 XYZRHW 提交（RenderWare 老式软 T&L），所以
"FVF 含 XYZRHW ⇒ 2D" 这条判据在本引擎上完全失效，永远放行 → 图集糊到墙上。

新判据：**先看深度测试**。
  ZENABLE == TRUE  -> 3D 场景 -> 换回小图集
  ZENABLE != TRUE  -> 2D UI  -> 保持图集不动
正交投影作为"确定是 2D"的辅助豁免（先判 Z 更稳，故放在 Z 之后只用于放行）。
"""
import io
import sys

P = r'D:\SteamLibrary\steamapps\common\Obscure2\Obscure2_Handover\d3d9proxy_src\d3d9_proxy.c'
s = io.open(P, encoding='utf-8').read()

old = '''    /* 门槛 1: 屏幕空间 2D 顶点 */
    if (fvf & D3DFVF_XYZRHW) {
        g_skipRhwN++;
        if (g_gateLogN < 24) {
            g_gateLogN++;
            LOGB("[GATE] fvf=0x%03lX -> SKIP(RHW) mode=%d f=%ld",
                 (unsigned long)fvf, mode, g_frames);
        }
        return 0;
    }
    if (mode == 1) goto do_revert;

    /* 门槛 2: 正交投影 = UI */
    if (proj_is_ortho(dev, r)) {
        g_skipOrthoN++;
        if (g_gateLogN < 24) {
            g_gateLogN++;
            LOGB("[GATE] fvf=0x%03lX -> SKIP(正交投影) mode=%d f=%ld",
                 (unsigned long)fvf, mode, g_frames);
        }
        return 0;
    }
'''

new = '''    /* ★★ 门槛 1（v22 核心修正）：以【深度测试】区分 2D / 3D ★★
     * 实机日志：atlas=487552 且 skipRhw=487552、skipOrtho=skipZoff=0
     * => 本引擎把 3D 顶点也在 CPU 端变换后以 XYZRHW 提交（RenderWare 软 T&L），
     *    所以"FVF 含 XYZRHW ⇒ 2D"这条判据在本引擎上恒真、等于没有门槛，
     *    图集因此被糊到墙壁/地板/门板上。
     * 正确判据：3D 场景开 ZENABLE，2D UI 关。 */
    if (!r->origVt[IX_DEV_GETRS]) goto do_revert;      /* 拿不到状态就保守还原 */
    if (((PFN_GRS)r->origVt[IX_DEV_GETRS])(dev, D3DRS_ZENABLE, &z) != D3D_OK)
        goto do_revert;
    if (z != D3DZB_TRUE) {
        g_skipZoffN++;
        if (g_gateLogN < 24) {
            g_gateLogN++;
            LOGB("[GATE] fvf=0x%03lX z=%lu -> SKIP(2D:Z off) mode=%d f=%ld",
                 (unsigned long)fvf, (unsigned long)z, mode, g_frames);
        }
        return 0;
    }
    /* Z 已开：判定为 3D。保留正交投影作为"确定 2D"的额外豁免（少数 UI 会开 Z）。 */
    if (proj_is_ortho(dev, r) && !(fvf & D3DFVF_XYZ)) {
        g_skipOrthoN++;
        if (g_gateLogN < 24) {
            g_gateLogN++;
            LOGB("[GATE] fvf=0x%03lX -> SKIP(正交投影且无XYZ) mode=%d f=%ld",
                 (unsigned long)fvf, mode, g_frames);
        }
        return 0;
    }
    /* 保留 RHW 计数用于观测（不再当作 2D 判据） */
    if (fvf & D3DFVF_XYZRHW) g_skipRhwN++;
'''

if old not in s:
    print('[MISS] gate block')
    sys.exit(1)
s = s.replace(old, new, 1)
print('[OK] gate reordered: Z-first')

# 门槛 3 现在会重复取 z，改成不再重复
old2 = '''    /* 门槛 3: 深度测试必须开启 */
    if (!r->origVt[IX_DEV_GETRS]) goto do_revert;
    if (((PFN_GRS)r->origVt[IX_DEV_GETRS])(dev, D3DRS_ZENABLE, &z) != D3D_OK)
        goto do_revert;
    if (z != D3DZB_TRUE) {
        g_skipZoffN++;
        if (g_gateLogN < 24) {
            g_gateLogN++;
            LOGB("[GATE] fvf=0x%03lX z=%lu -> SKIP(Z off) mode=%d f=%ld",
                 (unsigned long)fvf, (unsigned long)z, mode, g_frames);
        }
        return 0;
    }
    if (mode == 2) goto do_revert;
'''
new2 = '''    /* 门槛 3 已并入门槛 1（Z 已确认为 TRUE） */
    if (mode == 2) goto do_revert;
'''
if old2 in s:
    s = s.replace(old2, new2, 1)
    print('[OK] old gate 3 merged')
else:
    print('[WARN] gate 3 anchor not found (maybe already merged)')

io.open(P, 'w', encoding='utf-8', newline='\n').write(s)
print('done, %d chars' % len(s))

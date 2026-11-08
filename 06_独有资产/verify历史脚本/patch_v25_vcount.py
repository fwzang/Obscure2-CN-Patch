# -*- coding: utf-8 -*-
"""patch_v25_vcount.py — 用【顶点数量阈值】替代所有复杂判据（回退哈希 + FVF/ZENABLE）。

用户定调：文字系统彻底崩坏，必须回到"文字正常、偶尔漏图"的底线。
最简判据：
  2D 文字 = 4~几十个顶点；3D 网格 = 几百~几千顶点。
  若 primCount（或 numVtx）超过阈值 VERTEX_THRESHOLD，就临时换回小图集。

本补丁：
  1) 关闭 DRAW_UNBIND 的默认值为 1（启用顶点阈值拦截）
  2) atlas_unbind 签名加 primCount 参数，判据体替换为顶点阈值
  3) 四个 Draw 钩子传 primCount 进去
  4) 保留 SetTexture 替换（用尺寸登记，不是哈希）、Reset 解绑、dev_lost 守卫

注：哈希版（v24）的 tex_hash32 / font_identity_check / g_fontTexIdent 仍留在文件里，
但 SetTexture 的替换已被本补丁改回尺寸登记判定（见 patch 步骤 5），故哈希不再生效。
"""
import io
import sys

P = r'D:\SteamLibrary\steamapps\common\Obscure2\Obscure2_Handover\d3d9proxy_src\d3d9_proxy.c'
s = io.open(P, encoding='utf-8').read()
n = 0


def rep(old, new, tag):
    global s, n
    if old not in s:
        print('[MISS] %s' % tag)
        return False
    s = s.replace(old, new, 1)
    n += 1
    print('[OK] %s' % tag)
    return True


# 1) 阈值常量
rep('#ifndef DRAW_UNBIND',
    '''#ifndef VERTEX_THRESHOLD
#define VERTEX_THRESHOLD 100   /* primCount 超过此值视为 3D 网格，临时换回小图集 */
#endif

#ifndef DRAW_UNBIND''', 'threshold const')

# 2) atlas_unbind 加 primCount 参数 + 阈值判据（整段替换判据体）
old_sig = 'static int atlas_unbind(void* dev, DevRec* r) {'
new_sig = 'static int atlas_unbind(void* dev, DevRec* r, UINT primCount) {'
rep(old_sig, new_sig, 'signature + primCount')

# 把 #if !DRAW_UNBIND 整块 + 后续复杂判据，替换为顶点阈值逻辑
old_body = '''#if !DRAW_UNBIND
    /* v23 止损：Draw 钩子零干预。
     * v22 用 ZENABLE 判 2D/3D，但菜单里 Z 也是开的 -> 文字绘制时被误还原
     * -> stage0 变回 512x256 小图集而 def 指向 2048 扩展区 -> 白色雪花块。
     * 现在宁可在 3D 场景偶尔漏图，也不动引擎的绘制状态。 */
    (void)dev; (void)r; (void)fvf; (void)z; (void)zw; (void)ab; (void)mode;
    return 0;
#endif
    /* ★ c81（一代血泪）：热路径【绝不调 GetTexture】。
     * 每次 GetTexture 都会给 stage0 纹理 +1 引用，而调用方不 Release ->
     * 引用持续泄漏 -> Reset 时运行时回收不掉 -> D3DERR_INVALIDCALL(0x8876086C)。
     * 一代实测：零查询版通过，6 次查询版失败。
     * 这里改为账本式：绑定状态由 Hook_SetTexture 维护的 g_bigAt0 记录。 */
    if (!g_bigAt0) return 0;
    if (!g_bigTex || !g_bigSrc) { g_bigAt0 = 0; return 0; }
    if (!r || !r->origVt[IX_DEV_SETTEXTURE]) { g_bigAt0 = 0; return 0; }
    if (mode == 0) return 0;                        /* 模式 0: 完全不干预 */

    g_atlasBoundN++;
    if (r->origVt[IX_DEV_GETFVF])
        ((PFN_GFVF)r->origVt[IX_DEV_GETFVF])(dev, &fvf);

    /* ★★ 门槛 1（v22 核心修正）：以【深度测试】区分 2D / 3D ★★
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

    /* 门槛 3 已并入门槛 1（Z 已确认为 TRUE） */
    if (mode == 2) goto do_revert;

    /* 模式 3: 再要求写深度 且 未开 alpha 混合 */
    ((PFN_GRS)r->origVt[IX_DEV_GETRS])(dev, D3DRS_ZWRITEENABLE, &zw);
    ((PFN_GRS)r->origVt[IX_DEV_GETRS])(dev, D3DRS_ALPHABLENDENABLE, &ab);
    if (zw != TRUE || ab == TRUE) {
        g_skipZoffN++;
        if (g_gateLogN < 24) {
            g_gateLogN++;
            LOGB("[GATE] fvf=0x%03lX z=%lu zw=%lu ab=%lu -> SKIP(strict) f=%ld",
                 (unsigned long)fvf, (unsigned long)z, (unsigned long)zw,
                 (unsigned long)ab, g_frames);
        }
        return 0;
    }

do_revert:
    if (g_gateLogN < 24) {
        g_gateLogN++;
        LOGB("[GATE] fvf=0x%03lX z=%lu -> REVERT(3D) mode=%d f=%ld",
             (unsigned long)fvf, (unsigned long)z, mode, g_frames);
    }
    ((PFN_ST)r->origVt[IX_DEV_SETTEXTURE])(dev, 0, (IDirect3DBaseTexture9*)g_bigSrc);
    g_bigAt0 = 0;
    return 1;
}'''
new_body = '''#if !DRAW_UNBIND
    (void)dev; (void)r; (void)primCount; (void)fvf; (void)z; (void)zw; (void)ab; (void)mode;
    return 0;
#endif
    /* ★ v25 极简判据：顶点数量阈值。
     * 2D 文字 = 4~几十个 prim；3D 网格 = 几百~几千 prim。
     * 不读 FVF、不读 ZENABLE、不猜投影，只看这次要画多少图元。 */
    if (!g_bigAt0) return 0;
    if (!g_bigTex || !g_bigSrc) { g_bigAt0 = 0; return 0; }
    if (!r || !r->origVt[IX_DEV_SETTEXTURE]) { g_bigAt0 = 0; return 0; }
    if (mode == 0) return 0;

    if ((UINT)primCount <= VERTEX_THRESHOLD) {
        g_skipZoffN++;                 /* 复用这个计数表示"文字级图元，放行" */
        if (g_gateLogN < 24) {
            g_gateLogN++;
            LOGB("[GATE] prim=%u <= %d -> SKIP(2D文字) f=%ld",
                 primCount, VERTEX_THRESHOLD, g_frames);
        }
        return 0;
    }
    /* primCount > 阈值：判定为 3D 网格，临时换回小图集 */
    if (g_gateLogN < 24) {
        g_gateLogN++;
        LOGB("[GATE] prim=%u > %d -> REVERT(3D网格) f=%ld",
             primCount, VERTEX_THRESHOLD, g_frames);
    }
    ((PFN_ST)r->origVt[IX_DEV_SETTEXTURE])(dev, 0, (IDirect3DBaseTexture9*)g_bigSrc);
    g_bigAt0 = 0;
    return 1;
}'''
rep(old_body, new_body, 'vertex-count gate')

# 3) 四个调用点加 primCount
rep('    rev = atlas_unbind(self, r);',
    '    rev = atlas_unbind(self, r, primCount);', 'DrawPrimitive call')
# DIP 用 numVtx 更准（索引绘制实际顶点数）
rep('''    rev = atlas_unbind(self, r);''',
    '''    rev = atlas_unbind(self, r, numVtx);''', 'DrawIndexedPrimitive call')
rep('''    rev = atlas_unbind(self, r);''', '''    rev = atlas_unbind(self, r, primCount);''', 'DPU call')
rep('''    rev = atlas_unbind(self, r);''', '''    rev = atlas_unbind(self, r, numVtx);''', 'DIPU call')

# 4) SetTexture 替换改回尺寸登记（去掉 v24 的身份 gate）
old_st = '''        {
            /* v24：优先按【内容身份】判定；未识别前退回尺寸登记表。
             * 3D 纹理指针不可能等于 g_fontTexIdent，所以 3D 场景天然不受影响。 */
            int isFont = g_fontTexIdent ? ((void*)tex == g_fontTexIdent)
                                        : is_font_tex((void*)tex);
            if (!isFont) goto not_font_tex;
        }
        if (1) {'''
new_st = '''        if (is_font_tex((void*)tex)) {'''
rep(old_st, new_st, 'SetTexture back to size registry')

# 去掉 not_font_tex label 引用（恢复原结构）
rep('''        }
        goto after_font_tex;
not_font_tex:
        if ((int)stage == 0 && g_bigAt0) g_bigAt0 = 0;   /* 非字体纹理绑定 stage0 */
after_font_tex:
        ;
#if G3_DIAG''',
    '''        }
        else if ((int)stage == 0 && g_bigAt0) g_bigAt0 = 0;   /* 非字体纹理绑定 stage0 */
#if G3_DIAG''', 'remove label, restore else-if')

io.open(P, 'w', encoding='utf-8', newline='\n').write(s)
print('applied %d patches, %d chars' % (n, len(s)))
sys.exit(0 if n >= 7 else 1)

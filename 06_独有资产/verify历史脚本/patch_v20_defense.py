# -*- coding: utf-8 -*-
"""patch_v20_defense.py — 把一代(Obscure 1)的 Device Lost / Reset 防御思想移植到二代。

移植的三条思想（一代版本号 c41/c43/c47/c63/c81）：
 1. 设备丢失期绝对静默：TestCooperativeLevel(vt3) 是丢失期唯一允许的调用，
    其它 D3D9 API 一律不调（否则返回 D3DERR_INVALIDCALL 并把设备锁死 -> 白屏）。
 2. Reset 前必须解绑所有 stage（c47）：一代二分实验确证，大纹理仍绑在 stage 上时
    Reset 返回 0x8876086C = D3DERR_INVALIDCALL，而设备本身是健康的。
 3. 热路径零 GetTexture（c81）：每次 GetTexture 都会给 stage0 纹理 +1 引用且不释放，
    泄漏的引用让 Reset 无法回收 -> INVALIDCALL。改为账本式跟踪绑定状态。
另加：帧末(Present)还原 stage0，别让引擎在帧边界看到我们的大图集。
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


# ---------- 1) 账本标志 ----------
rep('static int   g_devLost       = 0;            /* 1 = 设备已丢失, 所有 hook 直通 */',
    'static int   g_devLost       = 0;            /* 1 = 设备已丢失, 所有 hook 直通 */\n'
    'static int   g_bigAt0        = 0;            /* 账本: stage0 当前绑的是我们的大图集 */\n'
    'static long  g_frameRestoreN = 0;            /* 帧末还原次数 */',
    'bookkeeping flag')

# ---------- 2) atlas_unbind: 去掉 GetTexture，改账本式 ----------
old_unbind = '''static int atlas_unbind(void* dev, DevRec* r) {
    IDirect3DBaseTexture9* cur = NULL;
    DWORD fvf = 0, z = 0xFFFFFFFF, zw = 0, ab = 0;
    int mode = gate_mode();
    if (!g_bigTex || !g_bigSrc) return 0;
    if (!r->origVt[IX_DEV_GETTEXTURE] || !r->origVt[IX_DEV_SETTEXTURE]) return 0;
    if (((PFN_GT)r->origVt[IX_DEV_GETTEXTURE])(dev, 0, &cur) != D3D_OK) return 0;
    if ((void*)cur != (void*)g_bigTex) return 0;    /* stage0 不是大图集: 无事可做 */
    if (mode == 0) return 0;                        /* 模式 0: 完全不干预 */
'''
new_unbind = '''static int atlas_unbind(void* dev, DevRec* r) {
    DWORD fvf = 0, z = 0xFFFFFFFF, zw = 0, ab = 0;
    int mode = gate_mode();
    /* ★ c81（一代血泪）：热路径【绝不调 GetTexture】。
     * 每次 GetTexture 都会给 stage0 纹理 +1 引用，而调用方不 Release ->
     * 引用持续泄漏 -> Reset 时运行时回收不掉 -> D3DERR_INVALIDCALL(0x8876086C)。
     * 一代实测：零查询版通过，6 次查询版失败。
     * 这里改为账本式：绑定状态由 Hook_SetTexture 维护的 g_bigAt0 记录。 */
    if (!g_bigAt0) return 0;
    if (!g_bigTex || !g_bigSrc) { g_bigAt0 = 0; return 0; }
    if (!r || !r->origVt[IX_DEV_SETTEXTURE]) { g_bigAt0 = 0; return 0; }
    if (mode == 0) return 0;                        /* 模式 0: 完全不干预 */
'''
rep(old_unbind, new_unbind, 'atlas_unbind: drop GetTexture')

rep('''    ((PFN_ST)r->origVt[IX_DEV_SETTEXTURE])(dev, 0, (IDirect3DBaseTexture9*)g_bigSrc);
    return 1;
}''',
    '''    ((PFN_ST)r->origVt[IX_DEV_SETTEXTURE])(dev, 0, (IDirect3DBaseTexture9*)g_bigSrc);
    g_bigAt0 = 0;
    return 1;
}''', 'atlas_unbind: clear flag on revert')

# ---------- 3) Hook_SetTexture: 维护账本 ----------
rep('''            if (g_bigTex) {
                g_swapN++;
                /* 记住"原版字体纹理", 供 3D 绘制前临时顶回 stage0（防图集泄露） */
                g_bigSrc = (IDirect3DTexture9*)tex;''',
    '''            if (g_bigTex) {
                g_swapN++;
                /* 记住"原版字体纹理", 供 3D 绘制前临时顶回 stage0（防图集泄露） */
                g_bigSrc = (IDirect3DTexture9*)tex;
                g_bigAt0 = ((int)stage == 0);   /* 账本: stage0 现在绑的是大图集 */''',
    'SetTexture: set flag on swap')

# ---------- 4) Hook_Reset: c47 防线（Reset 前解绑全部 stage） ----------
rep('''    hr = ((long (WINAPI *)(void*, D3DPRESENT_PARAMETERS*))
          r->origVt[IX_DEV_RESET])(self, pp);
    g_ckpt = "RST:2-done";''',
    '''    /* ★★★ c47 防线（一代二分实验确证，本项目的真正根因）★★★
     * 一代实测：大纹理仍绑在 stage 上时，Reset 返回 0x8876086C = D3DERR_INVALIDCALL，
     * 而 TestCooperativeLevel 返回 0（设备【完全健康】）。
     * => D3D9 要求 Reset 时【没有任何纹理处于绑定状态】。
     * 做法：Reset 前把 stage0..7 全部设成 NULL，再调真正的 Reset。
     * 铁律：只在设备健康时做（dev_lost 为假），丢失期任何 D3D9 调用都会锁死设备。 */
    if (!dev_lost(self, r) && r->origVt[IX_DEV_SETTEXTURE]) {
        PFN_ST pst = (PFN_ST)r->origVt[IX_DEV_SETTEXTURE];
        int st;
        for (st = 0; st < 8; st++) pst(self, (DWORD)st, NULL);
        g_bigAt0 = 0;
        if (g_resetN <= 8)
            LOGB("[RST] #%ld Reset 前已解绑 stage0..7（c47 防线）", g_resetN);
    } else if (g_resetN <= 8) {
        LOGB("[RST] #%ld 设备不健康，跳过解绑（铁律：丢失期不调任何 D3D9 API）", g_resetN);
    }

    hr = ((long (WINAPI *)(void*, D3DPRESENT_PARAMETERS*))
          r->origVt[IX_DEV_RESET])(self, pp);
    g_ckpt = "RST:2-done";''', 'Reset: c47 unbind-all')

# ---------- 5) Hook_Present: 帧末还原 ----------
rep('''    g_ckpt = "PRESENT:2-callOrig";
    hr = ((long (WINAPI *)(void*, const RECT*, const RECT*, HWND, const RGNDATA*))
          r->origVt[IX_DEV_PRESENT])(self, s, d, h, g);''',
    '''    /* 帧末还原：把 stage0 还回游戏原本的字体纹理，
     * 别让引擎在帧边界/Reset 前看到我们的大图集（c47 的日常版）。 */
    if (g_bigAt0 && g_bigTex && g_bigSrc && !dev_lost(self, r)
        && r->origVt[IX_DEV_SETTEXTURE]) {
        ((PFN_ST)r->origVt[IX_DEV_SETTEXTURE])(self, 0,
                                               (IDirect3DBaseTexture9*)g_bigSrc);
        g_bigAt0 = 0;
        g_frameRestoreN++;
    }
    g_ckpt = "PRESENT:2-callOrig";
    hr = ((long (WINAPI *)(void*, const RECT*, const RECT*, HWND, const RGNDATA*))
          r->origVt[IX_DEV_PRESENT])(self, s, d, h, g);''', 'Present: frame-end restore')

# ---------- 6) STAT 行加帧末还原计数 ----------
rep('"atlas=%ld skipRhw=%ld skipOrtho=%ld skipZoff=%ld up=%ld samp=%ld",',
    '"atlas=%ld skipRhw=%ld skipOrtho=%ld skipZoff=%ld up=%ld samp=%ld rst=%ld",',
    'STAT format')
rep('g_atlasBoundN, g_skipRhwN, g_skipOrthoN, g_skipZoffN, g_upN, g_sampN);',
    'g_atlasBoundN, g_skipRhwN, g_skipOrthoN, g_skipZoffN, g_upN, g_sampN,\n'
    '             g_frameRestoreN);', 'STAT args')

io.open(P, 'w', encoding='utf-8', newline='\n').write(s)
print('applied %d patches, %d chars' % (n, len(s)))
sys.exit(0 if n >= 6 else 1)

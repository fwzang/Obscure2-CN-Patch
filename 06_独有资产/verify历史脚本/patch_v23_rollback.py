# -*- coding: utf-8 -*-
"""patch_v23_rollback.py — 紧急止损：Draw 钩子完全停止干预。

事故：v22 用 ZENABLE 判 2D/3D，但菜单里 Z 也是开的，导致 atlas_unbind
在【文字绘制】时就提前把 stage0 换回原版 512x256 小图集；而 def 指向 2048x1024
扩展区坐标 -> UV 越界 -> 白色雪花块、UI 崩坏。

v23 策略（用户定：稳定压倒一切）：
  DRAW_UNBIND = 0
    - atlas_unbind() 直接返回 0（Draw 钩子零干预）
    - DrawPrimitive / DrawIndexedPrimitive / UP 两个钩子只做 dev_lost 守卫后透传
    - Present 不再做帧末还原
  保留：SetTexture 替换（中文照常）、Reset 前解绑 stage0..7（c47 防闪退）、
        TestCooperativeLevel 守卫、账本 g_bigAt0。
代价：接受 3D 场景可能漏图。
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


# 1) 开关
rep('#ifndef HOOK_RESET', '''#ifndef DRAW_UNBIND
#define DRAW_UNBIND 0   /* 0 = Draw 钩子零干预（稳定优先，接受漏图）; 1 = 启用 3D 防漏图 */
#endif

#ifndef HOOK_RESET''', 'switch DRAW_UNBIND')

# 2) atlas_unbind 直接返回
rep('''static int atlas_unbind(void* dev, DevRec* r) {
    DWORD fvf = 0, z = 0xFFFFFFFF, zw = 0, ab = 0;
    int mode = gate_mode();''',
    '''static int atlas_unbind(void* dev, DevRec* r) {
    DWORD fvf = 0, z = 0xFFFFFFFF, zw = 0, ab = 0;
    int mode = gate_mode();
#if !DRAW_UNBIND
    /* v23 止损：Draw 钩子零干预。
     * v22 用 ZENABLE 判 2D/3D，但菜单里 Z 也是开的 -> 文字绘制时被误还原
     * -> stage0 变回 512x256 小图集而 def 指向 2048 扩展区 -> 白色雪花块。
     * 现在宁可在 3D 场景偶尔漏图，也不动引擎的绘制状态。 */
    (void)dev; (void)r; (void)fvf; (void)z; (void)zw; (void)ab; (void)mode;
    return 0;
#endif''', 'atlas_unbind disabled')

# 3) Present 帧末还原关掉
rep('''    if (g_bigAt0 && g_bigTex && g_bigSrc && !dev_lost(self, r)
        && r->origVt[IX_DEV_SETTEXTURE]) {''',
    '''    if (DRAW_UNBIND && g_bigAt0 && g_bigTex && g_bigSrc && !dev_lost(self, r)
        && r->origVt[IX_DEV_SETTEXTURE]) {''', 'Present restore gated')

# 4) UP 钩子去掉 atlas_unbind
rep('''    g_upN++;
    if (g_bigAt0) g_upAtlasN++;        /* 账本式（零查询）：本调用带图集进来 */
    /* ★ 3D 漏图拦截：UP 路径同样要在画 3D 几何体前把 stage0 换回小图集 */
    atlas_unbind(self, r);''',
    '''    g_upN++;
    if (g_bigAt0) g_upAtlasN++;        /* 账本式（零查询）*/''', 'vt83 no unbind')

rep('''    g_upiN++;
    if (g_bigAt0) g_upiAtlasN++;
    atlas_unbind(self, r);''',
    '''    g_upiN++;
    if (g_bigAt0) g_upiAtlasN++;''', 'vt84 no unbind')

io.open(P, 'w', encoding='utf-8', newline='\n').write(s)
print('applied %d patches, %d chars' % (n, len(s)))
sys.exit(0 if n == 5 else 1)

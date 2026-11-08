# -*- coding: utf-8 -*-
"""patch_v24_identity.py — 重写核心：按纹理身份（内容哈希）替换，抛弃 FVF/ZENABLE 猜谜。

设计要点
1. tex_hash32(): 对纹理 level0 做 FNV-1a 内容哈希（LockRect 只读）。
2. 在 Hook_UpdateTexture / Hook_CreateTexture 里：尺寸命中字体规格时算哈希，
   - 首次见到 -> 记录 g_fontHash 并把该指针记为 g_fontTexIdent
   - 哈希一致 -> 更新 g_fontTexIdent（引擎重建字体后仍能认出）
3. Hook_SetTexture: 只在 tex == g_fontTexIdent 时替换（未识别前退回尺寸登记）。
   3D 场景的纹理指针永远不等于 g_fontTex，因此**天然不会泄漏**。
4. Reset: 记录并解码每次返回值（INVALIDCALL/DEVICELOST/DEVICENOTRESET）。
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


# ---- 1) 身份状态 + 哈希函数 ----
rep('''static void font_tex_add(void* t) {''',
    '''/* ★ v24：按【纹理内容身份】识别原版字体图集（抛弃 FVF / ZENABLE 猜谜） */
static void*        g_fontTexIdent = NULL;   /* 内容哈希命中后的运行时字体纹理指针 */
static unsigned int g_fontHash     = 0;      /* 其内容 FNV-1a 哈希 */
static long         g_resetHrLogN  = 0;

/* FNV-1a 32bit：对纹理 level0 逐字节哈希。只读、不改状态、不 AddRef。
 * 返回 0 表示无法读取（该纹理不参与身份判定）。 */
static unsigned int tex_hash32(void* tex) {
    IDirect3DTexture9* t = (IDirect3DTexture9*)tex;
    D3DLOCKED_RECT lr;
    unsigned int h = 2166136261u;
    unsigned int y, x, rowbytes;
    unsigned char* p;
    if (!t || !t->lpVtbl || !t->lpVtbl->LockRect || !t->lpVtbl->UnlockRect) return 0;
    if (t->lpVtbl->LockRect(t, 0, &lr, NULL, D3DLOCK_READONLY) != D3D_OK) return 0;
    if (!lr.pBits || lr.Pitch <= 0) { t->lpVtbl->UnlockRect(t, 0); return 0; }
    rowbytes = (unsigned int)lr.Pitch;
    if (rowbytes > 4096u) rowbytes = 4096u;      /* 只取前 4KB/行，够区分且快 */
    for (y = 0; y < (unsigned int)FONT_H; y++) {
        p = (unsigned char*)lr.pBits + (size_t)y * (size_t)lr.Pitch;
        for (x = 0; x < rowbytes; x++) {
            h ^= (unsigned int)p[x];
            h *= 16777619u;
        }
    }
    t->lpVtbl->UnlockRect(t, 0);
    return h ? h : 1u;                            /* 0 保留为"无哈希" */
}

/* 尺寸命中后按内容哈希登记/比对身份 */
static void font_identity_check(void* tex, const char* where) {
    unsigned int hh;
    if (!tex) return;
    hh = tex_hash32(tex);
    if (!hh) return;
    if (g_fontHash == 0) {
        g_fontHash = hh;
        g_fontTexIdent = tex;
        LOGB("[IDENT] %s: 首见字体内容 hash=0x%08lX -> tex=%p", where,
             (unsigned long)hh, tex);
    } else if (hh == g_fontHash) {
        if (g_fontTexIdent != tex) {
            g_fontTexIdent = tex;
            LOGB("[IDENT] %s: 内容匹配(hash=0x%08lX) 字体纹理更新为 %p", where,
                 (unsigned long)hh, tex);
        }
    } else {
        LOGB("[IDENT] %s: 尺寸符合但内容不符 hash=0x%08lX(期望 0x%08lX) tex=%p 跳过",
             where, (unsigned long)hh, (unsigned long)g_fontHash, tex);
    }
}

static void font_tex_add(void* t) {''', 'identity state + hash fn')

# ---- 2) CreateTexture 登记处调用身份检查 ----
rep('''            font_tex_add((void*)*out);''',
    '''            font_tex_add((void*)*out);
            font_identity_check((void*)*out, "CreateTexture");''',
    'CreateTexture identity check')

# ---- 3) UpdateTexture 里做身份检查 ----
rep('''#else
    (void)ds; (void)dd;
#endif
    return hr;
}''',
    '''#else
    (void)ds; (void)dd;
    /* 引擎用 UpdateTexture 把系统内存副本灌进显存纹理时，dst 就是运行时字体纹理 */
    if (dst && tex_desc((void*)dst, &dd) && dd.w == FONT_W && dd.h == FONT_H
        && dd.fmt == FONT_FMT)
        font_identity_check((void*)dst, "UpdateTexture");
    if (src && tex_desc((void*)src, &ds) && ds.w == FONT_W && ds.h == FONT_H
        && ds.fmt == FONT_FMT)
        font_identity_check((void*)src, "UpdateTexture(src)");
#endif
    return hr;
}''', 'UpdateTexture identity check')

# ---- 4) SetTexture 改为身份判定 ----
rep('''        if (is_font_tex((void*)tex)) {''',
    '''        {
            /* v24：优先按【内容身份】判定；未识别前退回尺寸登记表。
             * 3D 纹理指针不可能等于 g_fontTexIdent，所以 3D 场景天然不受影响。 */
            int isFont = g_fontTexIdent ? ((void*)tex == g_fontTexIdent)
                                        : is_font_tex((void*)tex);
            if (!isFont) goto not_font_tex;
        }
        if (1) {''', 'SetTexture identity gate')

# 需要在 if(1){} 块结束后提供 not_font_tex 标签：放在 G3_DIAG else-if 之前
rep('''        }
#if G3_DIAG
        else if (g_stLogN < 300 && tex_desc((void*)tex, &d)) {
            /* 非字体纹理: 记录前 300 个不同尺寸的绑定, 供判据复盘 */''',
    '''        }
        goto after_font_tex;
not_font_tex:
        if ((int)stage == 0 && g_bigAt0) g_bigAt0 = 0;   /* 非字体纹理绑定 stage0 */
after_font_tex:
        ;
#if G3_DIAG
        if (g_stLogN < 300 && tex_desc((void*)tex, &d)) {
            /* 非字体纹理: 记录前 300 个不同尺寸的绑定, 供判据复盘 */''',
    'not_font_tex label')

# ---- 5) Reset 返回值解码 ----
rep('''    if (g_resetN <= 8)
        LOGB("[RST] #%ld hr=0x%08lX (大纹理 %s)", g_resetN, (unsigned long)hr,
             g_bigTex ? "保留" : "未创建");''',
    '''    {
        const char* why = "";
        if (hr == 0x88760868UL)      why = " [D3DERR_DEVICELOST 设备丢失]";
        else if (hr == 0x88760869UL) why = " [D3DERR_DEVICENOTRESET 尚未复位]";
        else if (hr == 0x8876086CUL) why = " [D3DERR_INVALIDCALL 参数/状态非法]";
        else if (hr == 0x8876017CUL) why = " [D3DERR_OUTOFVIDEOMEMORY]";
        if (g_resetHrLogN < 40 || hr != 0) {
            g_resetHrLogN++;
            LOGB("[RST] #%ld hr=0x%08lX%s (大纹理 %s, fontTex=%p)",
                 g_resetN, (unsigned long)hr, why,
                 g_bigTex ? "保留" : "未创建", g_fontTexIdent);
        }
    }''', 'Reset hr decode')

io.open(P, 'w', encoding='utf-8', newline='\n').write(s)
print('applied %d patches, %d chars' % (n, len(s)))
sys.exit(0 if n == 5 else 1)

# -*- coding: utf-8 -*-
"""build_v65_prod.py — v65_PROD R2：1080p 安全区 + 2K/4K 几何判定拉回。

用户实测纠正：1080p 正常，2K 才越界（v55 日志 scrY 最高 2022 > 1440）。

执行逻辑（严格按用户要求）：
  1. 视口高 <= 1080 → 立刻 return，连投影矩阵都不读（1080p 绝对安全区）
  2. 视口高 > 1080 且面片 maxY > 视口高 → 判定为"飞出去"
  3. 改投影矩阵：m[1][1] *= s，m[3][1] += dy，画完立刻还原
  4. 保留窗口化防死锁 + TestCooperativeLevel 守卫

关于 s：
  用户公式 1440/H 在 2K 下正好是 1.0（无效）。所以默认取该公式，
  但如果按它缩放后仍然放不进屏幕，就自动退化为"缩到 90% 视口高"。
  2K 实测数据：面片 1950px / 视口 1440px → 需 s ≈ 0.9/1.354 ≈ 0.664。

关于 Lock：
  "算出 maxY" 必须读顶点，读顶点只能 Lock。为把风险压到最低：
    * 只在 vp.Height > 1080 时才可能走到 Lock（1080p 永不 Lock）
    * 每帧 Lock 上限 O2_FIX_LOCKMAX（默认 64）
    * Lock 前先 TestCooperativeLevel
    * Lock 失败立刻透传
"""
import os
import shutil
import subprocess

import build_v64_prod as b64

ROOT = b64.ROOT
SRC = b64.SRC
GCC = b64.GCC
OUTDIR = b64.OUTDIR
WORK = os.path.join(ROOT, r"_verify\_v65_prod")
PKG = b64.PKG

TARGETS = [
    ("A", os.path.join(PKG, r"06_独有资产\方案A_字体产物\g3_atlas.png"),
     "22ffed606c669be5043668d8b29ae2ef", "v65_PROD_A.dll"),
    ("B", os.path.join(PKG, r"04_基线与回滚\g3_atlas.png"),
     "e172a188651c68464ff3946683c3f5c9", "v65_PROD.dll"),
]

UI_DEFS = """
/* ---- v65 R2 用到的 vtable 槽位 ---- */
#define IX_DEV_GETVIEWPORT     48
#define IX_DEV_SETTRANSFORM    44
#define IX_DEV_SETSTREAM      100
#define IX_DEV_GETINDICES     103
#define UI_SAFE_H            1080   /* <= 此高度绝不干预（1080p 安全区） */
typedef HRESULT (WINAPI *PFN_GVP)(void*, D3DVIEWPORT9*);
typedef HRESULT (WINAPI *PFN_STF)(void*, D3DTRANSFORMSTATETYPE, const D3DMATRIX*);
typedef HRESULT (WINAPI *PFN_SSS)(void*, UINT, void*, UINT, UINT);
typedef HRESULT (WINAPI *PFN_GIB)(void*, IDirect3DIndexBuffer9**, D3DFORMAT*);
"""

UI_GLOBALS = """
/* ===== v65 R2 通用 UI 越界纠正 ===== */
static int   g_uiOn = 1, g_uiInited = 0, g_uiLogN = 0;
static int   g_uiLockMax = 64;
static float g_uiRefH = 1440.0f, g_uiScale = 0.0f;
static long  g_uiHit = 0, g_uiSeen = 0, g_uiLockN = 0, g_uiVpN = 0;
static long  g_uiSafeN = 0, g_uiLockBudget = 64;

static void ui_init(void) {
    char b[64];
    if (g_uiInited) return;
    g_uiInited = 1;
    if (GetEnvironmentVariableA("O2_FIX_UI_ANY", b, sizeof(b)) > 0) g_uiOn = (b[0] != '0');
    if (GetEnvironmentVariableA("O2_FIX_REFH", b, sizeof(b)) > 0) {
        int v = atoi(b); if (v > 100) g_uiRefH = (float)v;
    }
    if (GetEnvironmentVariableA("O2_FIX_SCALE", b, sizeof(b)) > 0) {
        int v = atoi(b); if (v > 0) g_uiScale = (float)v / 1000.0f;
    }
    if (GetEnvironmentVariableA("O2_FIX_LOCKMAX", b, sizeof(b)) > 0) {
        int v = atoi(b); if (v > 0) g_uiLockMax = v;
    }
    g_uiLockBudget = g_uiLockMax;
    LOGB("[FIX] v65 R2 %s 安全区<=%d refH=%d scale=%d/1000 lockmax=%d",
         g_uiOn ? "启用" : "关闭", UI_SAFE_H, (int)g_uiRefH,
         (int)(g_uiScale * 1000.0f), g_uiLockMax);
}
"""

UI_HELPERS = """
/* ===== v65 R2：几何判定 + 只改矩阵，不自己画 ===== */
static void ui_mat_mul(const D3DMATRIX* a, const D3DMATRIX* b, D3DMATRIX* o) {
    int i, j, k;
    for (i = 0; i < 4; i++)
        for (j = 0; j < 4; j++) {
            float acc = 0.0f;
            for (k = 0; k < 4; k++) acc += a->m[i][k] * b->m[k][j];
            o->m[i][j] = acc;
        }
}

static void ui_wvp(void* self, DevRec* r, D3DMATRIX* out) {
    D3DMATRIX W, V, P, T;
    int i, j;
    for (i = 0; i < 4; i++)
        for (j = 0; j < 4; j++) { W.m[i][j] = 0.0f; V.m[i][j] = 0.0f; P.m[i][j] = 0.0f; }
    W.m[0][0] = W.m[1][1] = W.m[2][2] = W.m[3][3] = 1.0f;
    V = W; P = W;
    ((PFN_GTF)r->origVt[IX_DEV_GETTRANSFORM])(self, D3DTS_WORLD, &W);
    ((PFN_GTF)r->origVt[IX_DEV_GETTRANSFORM])(self, D3DTS_VIEW, &V);
    ((PFN_GTF)r->origVt[IX_DEV_GETTRANSFORM])(self, D3DTS_PROJECTION, &P);
    ui_mat_mul(&W, &V, &T);
    ui_mat_mul(&T, &P, out);
}

static long WINAPI Hook_SetStreamSource(void* self, UINT StreamNumber,
                                        void* pStreamData, UINT OffsetInBytes, UINT Stride) {
    DevRec* r = dev_find(self);
    if (!r) return D3DERR_INVALIDCALL;
    if (StreamNumber == 0) { r->vb0 = pStreamData; r->vbOfs = OffsetInBytes; r->vbStride = Stride; }
    return ((PFN_SSS)r->origVt[IX_DEV_SETSTREAM])(self, StreamNumber, pStreamData,
                                                  OffsetInBytes, Stride);
}

/* 返回 1 = 已接管（*hrOut 有效） */
static int ui_fix(void* self, DevRec* r, D3DPRIMITIVETYPE pt, INT baseVtx, UINT minIdx,
                  UINT numVtx, UINT startIdx, UINT primCount, long* hrOut) {
    DWORD fvf = 0;
    D3DVIEWPORT9 vp;
    D3DMATRIX M, Pold, Pn;
    IDirect3DVertexBuffer9* vb;
    IDirect3DIndexBuffer9* ib = NULL;
    D3DFORMAT ifmt = D3DFMT_UNKNOWN;
    float px[8], py[8], pz[8], sx[8], sy[8], cwv[8];
    int idx[12];
    void* data = NULL;
    UINT stride, isz, ofs, nIdx, i;
    int bad;
    float mnx, mxx, mny, mxy, w, h, s, cyS, cyNew, hNew, dyPix, wavg;
    RECT cr;

    if (!g_uiOn) return 0;
    if (numVtx == 0 || numVtx > 8 || primCount == 0 || primCount > 4) return 0;
    if (pt != D3DPT_TRIANGLELIST && pt != D3DPT_TRIANGLESTRIP && pt != D3DPT_TRIANGLEFAN) return 0;
    if (!r->origVt[IX_DEV_GETFVF] || !r->origVt[IX_DEV_GETVIEWPORT] ||
        !r->origVt[IX_DEV_GETTRANSFORM] || !r->origVt[IX_DEV_SETTRANSFORM] ||
        !r->origVt[IX_DEV_GETINDICES] || !r->origVt[IX_DEV_DRAWIDXPRIM]) return 0;
    if (((PFN_GVP)r->origVt[IX_DEV_GETVIEWPORT])(self, &vp) != 0) return 0;

    /* ★ 1. 1080p 安全区：连矩阵都不读，直接放行 */
    if (vp.Height <= UI_SAFE_H) { g_uiSafeN++; return 0; }

    if (vp.Width < 16 || vp.Height < 16) return 0;
    /* 只处理主画面：视口 == 窗口客户区（排除阴影贴图/离屏 RT） */
    if (g_hGameWnd && GetClientRect(g_hGameWnd, &cr)) {
        if (vp.Width != (UINT)(cr.right - cr.left) ||
            vp.Height != (UINT)(cr.bottom - cr.top)) { g_uiVpN++; return 0; }
    }
    /* ★ 4. 守卫：改任何东西之前先查设备 */
    if (dev_lost_now(self, r)) return 0;
    if (((PFN_GFVF)r->origVt[IX_DEV_GETFVF])(self, &fvf) != 0) return 0;
    if ((fvf & D3DFVF_POSITION_MASK) != D3DFVF_XYZ) return 0;
    vb = (IDirect3DVertexBuffer9*)r->vb0;
    if (!vb || !vb->lpVtbl) return 0;
    stride = r->vbStride;
    if (stride < 12 || stride > 64) return 0;
    if (baseVtx + (INT)minIdx < 0) return 0;
    if (g_uiLockBudget <= 0) return 0;

    ofs = r->vbOfs + (UINT)(baseVtx + (INT)minIdx) * stride;
    g_uiLockBudget--;
    g_uiLockN++;
    if (vb->lpVtbl->Lock(vb, ofs, numVtx * stride, &data, D3DLOCK_READONLY) != 0) return 0;
    for (i = 0; i < numVtx; i++) {
        const BYTE* b = (const BYTE*)data + (size_t)i * stride;
        px[i] = ((const float*)b)[0];
        py[i] = ((const float*)b)[1];
        pz[i] = ((const float*)b)[2];
    }
    vb->lpVtbl->Unlock(vb);

    nIdx = (pt == D3DPT_TRIANGLELIST) ? primCount * 3 : primCount + 2;
    if (nIdx > 12) return 0;
    if (((PFN_GIB)r->origVt[IX_DEV_GETINDICES])(self, &ib, &ifmt) != 0 || !ib) return 0;
    isz = (ifmt == D3DFMT_INDEX32) ? 4 : 2;
    if (ib->lpVtbl->Lock(ib, startIdx * isz, nIdx * isz, &data, D3DLOCK_READONLY) != 0) {
        ib->lpVtbl->Release(ib); return 0;
    }
    bad = 0;
    for (i = 0; i < nIdx; i++) {
        UINT v = (isz == 4) ? ((const DWORD*)data)[i] : (UINT)((const WORD*)data)[i];
        int rel = (int)v - (int)minIdx;
        if (rel < 0 || rel >= (int)numVtx) { bad = 1; break; }
        idx[i] = rel;
    }
    ib->lpVtbl->Unlock(ib);
    ib->lpVtbl->Release(ib);
    if (bad) return 0;

    ui_wvp(self, r, &M);
    wavg = 0.0f;
    for (i = 0; i < numVtx; i++) {
        float cx4 = px[i]*M.m[0][0] + py[i]*M.m[1][0] + pz[i]*M.m[2][0] + M.m[3][0];
        float cy4 = px[i]*M.m[0][1] + py[i]*M.m[1][1] + pz[i]*M.m[2][1] + M.m[3][1];
        float cw4 = px[i]*M.m[0][3] + py[i]*M.m[1][3] + pz[i]*M.m[2][3] + M.m[3][3];
        if (cw4 <= 0.0001f) return 0;
        sx[i] = (cx4 / cw4 * 0.5f + 0.5f) * (float)vp.Width  + (float)vp.X;
        sy[i] = (-cy4 / cw4 * 0.5f + 0.5f) * (float)vp.Height + (float)vp.Y;
        cwv[i] = cw4;
        wavg += cw4;
    }
    wavg /= (float)numVtx;
    mnx = mxx = sx[0]; mny = mxy = sy[0];
    for (i = 1; i < numVtx; i++) {
        if (sx[i] < mnx) mnx = sx[i];
        if (sx[i] > mxx) mxx = sx[i];
        if (sy[i] < mny) mny = sy[i];
        if (sy[i] > mxy) mxy = sy[i];
    }
    g_uiSeen++;

    /* ★ 2. 越界判定：maxY 超出视口高（或整块跑到上方屏幕外） */
    if (!(mxy > (float)vp.Y + (float)vp.Height || mny < (float)vp.Y)) return 0;

    /* ★ 3. 缩放系数：默认 1440/H；放不下则退化为"缩到 90% 视口高" */
    w = mxx - mnx; h = mxy - mny;
    cyS = (float)vp.Y + (float)vp.Height * 0.5f;
    s = (g_uiScale > 0.001f) ? g_uiScale : (g_uiRefH / (float)vp.Height);
    if (h * s > (float)vp.Height * 0.95f) s = (float)vp.Height * 0.90f / h;
    if (s < 0.02f) s = 0.02f;
    cyNew = cyS + ((mny + mxy) * 0.5f - cyS) * s;
    hNew = h * s;
    if (hNew >= (float)vp.Height) dyPix = cyS - cyNew;
    else {
        float lo = (float)vp.Y + hNew * 0.5f;
        float hi = (float)vp.Y + (float)vp.Height - hNew * 0.5f;
        if (cyNew < lo) dyPix = lo - cyNew;
        else if (cyNew > hi) dyPix = hi - cyNew;
        else dyPix = 0.0f;
    }
    if (s > 0.999f && s < 1.001f && dyPix > -0.5f && dyPix < 0.5f) return 0;

    ((PFN_GTF)r->origVt[IX_DEV_GETTRANSFORM])(self, D3DTS_PROJECTION, &Pold);
    Pn = Pold;
    Pn.m[1][1] *= s;
    if (dyPix > 0.5f || dyPix < -0.5f)
        Pn.m[3][1] += (-2.0f * dyPix / (float)vp.Height) * wavg;
    ((PFN_STF)r->origVt[IX_DEV_SETTRANSFORM])(self, D3DTS_PROJECTION, &Pn);
    *hrOut = ((PFN_DIP)r->origVt[IX_DEV_DRAWIDXPRIM])(self, pt, baseVtx, minIdx, numVtx,
                                                      startIdx, primCount);
    ((PFN_STF)r->origVt[IX_DEV_SETTRANSFORM])(self, D3DTS_PROJECTION, &Pold);

    g_uiHit++;
    if (g_uiLogN < 12) {
        g_uiLogN++;
        LOGB("[FIX] 拉回 f=%ld nv=%u prim=%u s=%d/1000 dy=%d maxY=%d vp=%ux%u",
             g_frames, numVtx, primCount, (int)(s * 1000.0f), (int)dyPix,
             (int)mxy, vp.Width, vp.Height);
    }
    return 1;
}
"""


def patch_ui(s):
    a = "#define IX_DEV_GETFVF          90   /* GetFVF         (判断是否屏幕空间 2D) */"
    assert a in s, "IX_DEV_GETFVF 锚点丢失"
    s = s.replace(a, a + UI_DEFS, 1)

    a = "typedef struct { void* dev; void** origVt; void** cloneVt; } DevRec;"
    assert a in s, "DevRec 锚点丢失"
    s = s.replace(a, "typedef struct { void* dev; void** origVt; void** cloneVt;\n"
                     "    void* vb0; UINT vbOfs; UINT vbStride; } DevRec;", 1)

    a = "static int   g_bigAt0        = 0;            /* 账本: stage0 当前绑的是我们的大图集 */"
    assert a in s, "g_bigAt0 锚点丢失"
    s = s.replace(a, a + UI_GLOBALS, 1)

    a = "static long WINAPI Hook_SetSamplerState(void*, DWORD, D3DSAMPLERSTATETYPE, DWORD);"
    assert a in s, "SetSamplerState 锚点丢失"
    s = s.replace(a, a + "\nstatic long WINAPI Hook_SetStreamSource(void*, UINT, void*, UINT, UINT);", 1)

    a = "static long WINAPI Hook_DrawPrimitive(void* self, D3DPRIMITIVETYPE pt,\n                                      UINT startVtx, UINT primCount) {"
    assert a in s, "Hook_DrawPrimitive 锚点丢失"
    s = s.replace(a, UI_HELPERS + a, 1)

    a = "        clone[IX_DEV_DRAWPRIMUP]    = (void*)Hook_DrawPrimitiveUP;"
    assert a in s, "clone 锚点丢失"
    s = s.replace(a, "        clone[IX_DEV_SETSTREAM]     = (void*)Hook_SetStreamSource;\n" + a, 1)

    a = "    wd_start();"
    assert a in s, "wd_start 锚点丢失"
    s = s.replace(a, """    wd_start();
    ui_init();
    g_uiLockBudget = g_uiLockMax;
    if ((g_frames % 250) == 0)
        LOGB("[FIXS] f=%ld safe1080=%ld seen=%ld lock=%ld hit=%ld vpskip=%ld",
             g_frames, g_uiSafeN, g_uiSeen, g_uiLockN, g_uiHit, g_uiVpN);""", 1)

    a = """    if (dev_lost(self, r))
        return ((PFN_DIP)r->origVt[IX_DEV_DRAWIDXPRIM])(self, pt, baseVtx, minIdx, numVtx,
                                                        startIdx, primCount);
    return ((PFN_DIP)r->origVt[IX_DEV_DRAWIDXPRIM])(self, pt, baseVtx, minIdx, numVtx,
                                                    startIdx, primCount);"""
    assert a in s, "DIP 锚点丢失"
    s = s.replace(a, """    if (dev_lost(self, r))
        return ((PFN_DIP)r->origVt[IX_DEV_DRAWIDXPRIM])(self, pt, baseVtx, minIdx, numVtx,
                                                        startIdx, primCount);
    if (g_uiOn) {
        long hr = D3D_OK;
        if (ui_fix(self, r, pt, baseVtx, minIdx, numVtx, startIdx, primCount, &hr))
            return hr;
    }
    return ((PFN_DIP)r->origVt[IX_DEV_DRAWIDXPRIM])(self, pt, baseVtx, minIdx, numVtx,
                                                    startIdx, primCount);""", 1)

    a = '    LOGB("[INIT] ===== V64_PROD 稳定性优先版 =====");'
    assert a in s, "V64 标记锚点丢失"
    s = s.replace(a, '    LOGB("[INIT] ===== V65_PROD R2 1080p安全区+2K拉回 =====");', 1)
    return s


def main():
    src = open(os.path.join(SRC, "d3d9_proxy.c"), "rb").read().decode("utf-8")
    s = b64.patch(src)          # v64 全部补丁，一字不动
    s = patch_ui(s)
    os.makedirs(OUTDIR, exist_ok=True)
    for tag, png, want, name in TARGETS:
        assert b64.md5(png) == want, "图集 md5 不符: %s" % png
        d = os.path.join(WORK, tag)
        if os.path.isdir(d):
            shutil.rmtree(d)
        os.makedirs(d)
        open(os.path.join(d, "d3d9_proxy_v65.c"), "wb").write(s.encode("utf-8"))
        shutil.copy2(os.path.join(SRC, "d3d9.def"), d)
        b64.gen_header(png, os.path.join(d, "atlas_png.h"))
        out = os.path.join(OUTDIR, name)
        r = subprocess.run([GCC, "-O2", "-fno-sanitize=undefined", "-shared",
                            "-DFORCE_POINT_SAMPLER=0", "-DPRESENT_RESTORE=0",
                            "-Wl,--image-base=0x6BE00000",
                            "-o", out, "d3d9_proxy_v65.c", "d3d9.def"],
                           cwd=d, capture_output=True, text=True)
        if r.returncode != 0:
            print((r.stdout + r.stderr)[-3000:])
            raise SystemExit("[FAIL] %s" % tag)
        warn = [l for l in (r.stderr or "").splitlines() if "warning" in l]
        print("[%s] %s  %d B  md5 %s  warn=%d" % (tag, name, os.path.getsize(out), b64.md5(out), len(warn)))
        for l in warn[:10]:
            print("    " + l)


if __name__ == "__main__":
    main()

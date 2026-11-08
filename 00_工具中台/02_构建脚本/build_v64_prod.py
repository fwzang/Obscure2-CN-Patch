# -*- coding: utf-8 -*-
"""build_v64_prod.py — v64_PROD：修「全屏独占失焦后 Present 无限阻塞」。

02:17 看门狗实测（决定性证据）：
    [WD] ckpt=PRESENT:2-callOrig f=1133   （连续几十条，f 不再增长）
  => 渲染线程卡死在 IDirect3DDevice9::Present 内部，进程还活着、键鼠有响应、
     桌面被全屏表面占住 —— 正是全屏独占窗口失焦后 Present 阻塞的特征。

修法：
  Hook_Present 里，如果游戏窗口不在前台（GetForegroundWindow() != 自己的 HWND），
  直接跳过原 Present 并返回 D3D_OK，让消息循环继续跑。
  窗口回到前台后自动恢复，不再阻塞。
  （帧号 > 60 才开始判断，避开启动瞬间窗口还没抢到前台的阶段）

同时保留 v60 的看门狗与 v59 的丢失跳变清理。
"""
import hashlib
import os
import shutil
import subprocess

ROOT = r"D:\SteamLibrary\steamapps\common\Obscure2\Obscure2_Handover"
SRC = os.path.join(ROOT, "d3d9proxy_src")
GCC = os.path.join(ROOT, r"_toolchain\w64devkit\bin\i686-w64-mingw32-gcc.exe")
PKG = r"E:\ObsCure2汉化项目_v1.01_完整交付包_2026-10-22"
OUTDIR = r"D:\O2_浴室提示排查\修复版"
WORK = os.path.join(ROOT, r"_verify\_v64_prod")

TARGETS = [
    ("A", os.path.join(PKG, r"06_独有资产\方案A_字体产物\g3_atlas.png"),
     "22ffed606c669be5043668d8b29ae2ef", "v64_PROD_A.dll"),
    ("B", os.path.join(PKG, r"04_基线与回滚\g3_atlas.png"),
     "e172a188651c68464ff3946683c3f5c9", "v64_PROD.dll"),
]

GLOBALS = """
/* ===== v59 设备丢失加固 / v64 失焦跳过 Present ===== */
static int  g_devLostPrev = 0;
static long g_lostN = 0, g_recovN = 0;
static HWND g_hGameWnd = NULL;
static int  g_forceWin = 0;
static long g_topClearN = 0;
static long g_presSkipN = 0, g_presSkipLogN = 0;
"""

NEW_DEVLOST = """
/* v59: 不走每帧缓存，真实查询。只用在真正碰纹理的还原点（每帧 1~2 次） */
static int dev_lost_now(void* self, DevRec* r) {
    HRESULT hr;
    if (!r || !r->origVt || !r->origVt[IX_DEV_TESTCOOP]) return 0;
    hr = ((PFN_TCL)r->origVt[IX_DEV_TESTCOOP])(self);
    return (hr != D3D_OK);
}

static int dev_lost(void* self, DevRec* r) {"""

TRANSITION = """    g_devLost = (hr != D3D_OK);
    if (g_devLost != g_devLostPrev) {
        g_devLostPrev = g_devLost;
        if (g_devLost) {
            g_lostN++;
            g_bigSrc = NULL;
            g_bigAt0 = 0;
            g_fontStage = -1;
            g_last3D0 = NULL;
            g_prev0 = NULL;
            g_beforeSwap = NULL;
            LOGB("[LOSS] #%ld f=%ld 设备丢失 -> 作废裸指针", g_lostN, g_frames);
        } else {
            g_recovN++;
            LOGB("[LOSS] #%ld f=%ld 设备恢复 -> 指针缓存已清空", g_recovN, g_frames);
        }
    }"""

WATCHDOG = """
/* v60 看门狗：每 1.5s 把当前钩子位置写进日志 */
static int g_wdStarted = 0;
static DWORD WINAPI wd_thread(LPVOID p) {
    (void)p;
    for (;;) {
        Sleep(1500);
        LOGB("[WD] ckpt=%s f=%ld", g_ckpt ? g_ckpt : "?", g_frames);
    }
    return 0;
}
static void wd_start(void) {
    if (g_wdStarted) return;
    g_wdStarted = 1;
    if (CreateThread(NULL, 0, wd_thread, NULL, 0, NULL))
        LOGB("[WD] 看门狗已启动（每 1.5s 记录一次当前钩子位置）");
}

"""


FORCEWIN = """
    /* ★ v64：强制窗口化。
     * 全屏独占下 Alt+Tab 回来后 Present 会无限阻塞（实测 [WD] ckpt=PRESENT:2-callOrig
     * 冻结在 f=1057，而 TestCooperativeLevel 全程返回健康）。窗口化没有独占显示模式，
     * 切屏不再阻塞。O2_WIN=0 可关闭。 */
    if (pp && !pp->Windowed) {
        char wb[8];
        int on = 1;
        if (GetEnvironmentVariableA("O2_WIN", wb, sizeof(wb)) > 0) on = (wb[0] != '0');
        if (on) {
            pp->Windowed = TRUE;
            pp->FullScreen_RefreshRateInHz = 0;
            g_forceWin = 1;
            LOGB("[WIN] 强制窗口化 %ux%u fmt=%d（原为全屏独占）",
                 pp->BackBufferWidth, pp->BackBufferHeight, (int)pp->BackBufferFormat);
        }
    }
"""


def patch(s):
    a = "static int   g_bigAt0        = 0;            /* 账本: stage0 当前绑的是我们的大图集 */"
    assert a in s
    s = s.replace(a, a + GLOBALS, 1)

    a = "static int dev_lost(void* self, DevRec* r) {"
    assert a in s
    s = s.replace(a, NEW_DEVLOST, 1)

    a = "    g_devLost = (hr != D3D_OK);"
    assert a in s
    s = s.replace(a, TRANSITION, 1)

    a = """    if (g_bigAt0 && !dev_lost(self, r) && r->origVt[IX_DEV_SETTEXTURE]) {"""
    assert a in s
    s = s.replace(a, """    if (g_bigAt0 && !dev_lost_now(self, r) && r->origVt[IX_DEV_SETTEXTURE]) {""", 1)

    a = """    if (PRESENT_RESTORE && g_bigAt0 && g_bigTex && g_bigSrc && !dev_lost(self, r)
        && r->origVt[IX_DEV_SETTEXTURE]) {"""
    assert a in s
    s = s.replace(a, """    if (PRESENT_RESTORE && g_bigAt0 && g_bigTex && g_bigSrc && !dev_lost_now(self, r)
        && r->origVt[IX_DEV_SETTEXTURE]) {""", 1)

    # 记录游戏窗口句柄 + 强制窗口化
    a = """    hr = (g_d3d9OrigVt && g_d3d9OrigVt[IX_D3D9_CREATEDEVICE])"""
    assert a in s
    s = s.replace(a, FORCEWIN + a, 1)

    a = """    if (hr == D3D_OK && outDev && *outDev) {
        if (logN < 4) {"""
    assert a in s
    s = s.replace(a, """    if (hr == D3D_OK && outDev && *outDev) {
        g_hGameWnd = (pp && pp->hDeviceWindow) ? pp->hDeviceWindow : focus;
        if (g_forceWin && g_hGameWnd) {
            LONG st = GetWindowLongA(g_hGameWnd, GWL_STYLE);
            LONG ex = GetWindowLongA(g_hGameWnd, GWL_EXSTYLE);
            /* 无边框全屏：WS_POPUP 铺满，但必须让它参与 Alt+Tab、且不是置顶窗口 */
            SetWindowLongA(g_hGameWnd, GWL_STYLE,
                           WS_POPUP | WS_VISIBLE | WS_CLIPSIBLINGS | WS_CLIPCHILDREN);
            ex |= WS_EX_APPWINDOW;
            ex &= ~(WS_EX_TOPMOST | WS_EX_TOOLWINDOW);
            SetWindowLongA(g_hGameWnd, GWL_EXSTYLE, ex);
            SetWindowPos(g_hGameWnd, HWND_NOTOPMOST, 0, 0,
                         (int)pp->BackBufferWidth, (int)pp->BackBufferHeight,
                         SWP_FRAMECHANGED | SWP_SHOWWINDOW);
            LOGB("[WIN] 无边框窗口 %ux%u style=0x%08lX ex=0x%08lX (APPWINDOW, 非TOPWINDOW)",
                 pp->BackBufferWidth, pp->BackBufferHeight,
                 (unsigned long)GetWindowLongA(g_hGameWnd, GWL_STYLE),
                 (unsigned long)GetWindowLongA(g_hGameWnd, GWL_EXSTYLE));
        }
        if (logN < 4) {""", 1)

    # 看门狗
    a = """/* ============================================================================
 * Hook: IDirect3DDevice9::Present (vt17)"""
    assert a in s
    s = s.replace(a, WATCHDOG + a, 1)

    # 失焦跳过 Present
    a = """    if (!r) return D3D_OK;
    /* 设备丢失守卫：DEVICELOST 期间原样透传（连 heal 都不做） */"""
    assert a in s
    s = s.replace(a, """    if (!r) return D3D_OK;
    wd_start();
    /* ★ v61：全屏独占下窗口失焦时，原 Present 会无限阻塞（实测卡在 f=1133）。
     * 直接跳过 Present 返回 D3D_OK，让消息循环继续跑；窗口回到前台后自动恢复。 */
    if (g_hGameWnd && g_frames > 60 && GetForegroundWindow() != g_hGameWnd) {
        /* ★ v64：只在窗口不在前台时才清 TOPMOST。
         * v63 是每 8 帧无条件清，会和游戏抢 z-order（实测 f=624/672 各抢一次），
         * 可能造成窗口闪烁/层级抖动。 */
        if (g_forceWin && (GetWindowLongA(g_hGameWnd, GWL_EXSTYLE) & WS_EX_TOPMOST)) {
            SetWindowPos(g_hGameWnd, HWND_NOTOPMOST, 0, 0, 0, 0,
                         SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE);
            if (g_topClearN < 6) {
                g_topClearN++;
                LOGB("[WIN] 清除 TOPMOST (f=%ld)", g_frames);
            }
        }
        g_presSkipN++;
        if (g_presSkipLogN < 10) {
            g_presSkipLogN++;
            LOGB("[PRES] 窗口不在前台 -> 跳过 Present (f=%ld)", g_frames);
        }
        Sleep(10);
        return D3D_OK;
    }
    /* 设备丢失守卫：DEVICELOST 期间原样透传（连 heal 都不做） */""", 1)

    a = '    LOGB("[INIT] 图集常量: %dx%d, 字体判据 %dx%d fmt=%d",'
    assert a in s
    s = s.replace(a, '    LOGB("[INIT] ===== V64_PROD 稳定性优先版 =====");\n' + a, 1)
    return s


def gen_header(png, out_h):
    data = open(png, "rb").read()
    lines = ["/* atlas_png.h - v64_prod */",
             "/* 源: %s (%d B, md5 %s) */"
             % (os.path.basename(png), len(data), hashlib.md5(data).hexdigest()),
             "static const unsigned char g_atlasPng[] = {"]
    for i in range(0, len(data), 20):
        lines.append("  " + ",".join("0x%02X" % b for b in data[i:i + 20]) + ",")
    lines.append("};")
    lines.append("static const unsigned int g_atlasPngLen = %d;" % len(data))
    open(out_h, "w", newline="\n").write("\n".join(lines) + "\n")


def md5(p):
    return hashlib.md5(open(p, "rb").read()).hexdigest()


def main():
    src = open(os.path.join(SRC, "d3d9_proxy.c"), "rb").read().decode("utf-8")
    patched = patch(src)
    os.makedirs(OUTDIR, exist_ok=True)
    for tag, png, want, name in TARGETS:
        assert md5(png) == want, "图集 md5 不符: %s" % png
        d = os.path.join(WORK, tag)
        if os.path.isdir(d):
            shutil.rmtree(d)
        os.makedirs(d)
        open(os.path.join(d, "d3d9_proxy_v64.c"), "wb").write(patched.encode("utf-8"))
        shutil.copy2(os.path.join(SRC, "d3d9.def"), d)
        gen_header(png, os.path.join(d, "atlas_png.h"))
        out = os.path.join(OUTDIR, name)
        r = subprocess.run([GCC, "-O2", "-fno-sanitize=undefined", "-shared",
                            "-DFORCE_POINT_SAMPLER=0", "-DPRESENT_RESTORE=0", "-Wl,--image-base=0x6BE00000",
                            "-o", out, "d3d9_proxy_v64.c", "d3d9.def"],
                           cwd=d, capture_output=True, text=True)
        if r.returncode != 0:
            print((r.stdout + r.stderr)[-3000:])
            raise SystemExit("[FAIL] %s" % tag)
        warn = [l for l in (r.stderr or "").splitlines() if "warning" in l]
        print("[%s] %s  %d B  md5 %s  warn=%d" % (tag, name, os.path.getsize(out), md5(out), len(warn)))
        for l in warn[:10]:
            print("    " + l)


if __name__ == "__main__":
    main()

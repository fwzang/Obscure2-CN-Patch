/* ============================================================================
 * d3d9_proxy.c — 《Obscure II》(Steam) 汉化项目 Gate 3
 *                d3d9.dll 透明代理 + 字体图集显存替换（x86 / 32-bit）
 *
 * ---------------------------------------------------------------------------
 * 【架构总览】（与 Gen-1 version.dll 代理同族，导出层挂载而非 IAT 挂载）
 *
 *   Obscure2.exe --静态导入--> d3d9.dll(本代理, 游戏目录)
 *        |
 *        +-- 导出 Direct3DCreate9 = Proxy_Direct3DCreate9
 *        |     调真实 SysWOW64\d3d9.dll 的 Direct3DCreate9 得 IDirect3D9*
 *        |     -> attach_d3d9(): 克隆其 vtable(17 项), patch vt[16] CreateDevice
 *        |
 *        +-- Hook_CreateDevice: 调原始 CreateDevice 得 IDirect3DDevice9*
 *              -> attach_dev(): 克隆设备 vtable(300 槽), patch 10 个:
 *                   vt[16] Reset / vt[17] Present / vt[23] CreateTexture
 *                   vt[31] UpdateTexture / vt[65] SetTexture / vt[6] GetDirect3D
 *                   vt[81] DrawPrimitive / vt[82] DrawIndexedPrimitive
 *                   vt[83] DrawPrimitiveUP / vt[84] DrawIndexedPrimitiveUP
 *                   （+ 运行期功能自检 SetTexture/GetTexture 索引对）
 *              |
 *              +-- Hook_CreateTexture: 识别字体图集(512x256 A8R8G8B8)
 *              |     -> font_tex_add() 登记指针; 生产版懒创建大图集纹理
 *              +-- Hook_SetTexture: tex 命中字体图集 -> 换成 4096x2048 大图集
 *              |     -> 同时记住"原版字体纹理" g_bigSrc
 *              +-- Hook_DrawPrimitive / Hook_DrawIndexedPrimitive:
 *              |     图集泄露拦截 —— stage0 若为大图集, 画 3D 几何前临时顶回
 *              |     原版字体纹理, 画完换回。修复"墙壁/地板/人物出现横向条纹"。
 *              +-- Hook_DrawPrimitiveUP / Hook_DrawIndexedPrimitiveUP:
 *              |     仅计数观测（2D 文字路径, 带图集是正常现象, 绝不拦截）
 *              +-- Hook_Reset:       计数/日志; MANAGED 大纹理自动跨 Reset 存活
 *              +-- Hook_Present:     帧计数 + vtable 挂载自愈(heal)
 *
 * 【与 Gen-2 datapack 的配合】
 *   datapack_zh_full4.hvp 内 nonserif12 字体 def 已改为引用 4096x2048 图集
 *   （新字形 x>=512, 原版 512x256 区域字节级保留）。引擎按 def 尺寸算 UV,
 *   UV 落在 [0,4096)x[0,2048) —— 只有显存里绑定的是 4096x2048 纹理时采样才正确。
 *   本代理在 SetTexture 时把引擎绑定的 512x256 原版图集换成同内容的 4096x2048
 *   大图集(内嵌 g3_atlas.png, 经 d3dx9_42.dll 解码), 二者内容在前 512x256 区域
 *   逐字节一致 -> 现有 155 字形盒不变, 新增 2171 字形位于扩展区（共 2326 字形）。
 *
 * 【两阶段构建】（严格增量: 先诊断后生产, one-variable-at-a-time）
 *   -DG3_DIAG=1  诊断版: 全量日志, 不替换不建纹理（零渲染风险, 首发实机）
 *   -DG3_DIAG=0  生产版: 启用图集替换
 *
 * 【COM 引用计数安全】
 *   vtable 克隆法不改 AddRef/Release/QueryInterface（原样转发）-> 游戏对象
 *   引用计数完全不受影响; 大图集纹理由我们创建并持有 1 个引用,
 *   DLL 卸载或设备更换时 Release; Reset 不销毁 MANAGED 池纹理。
 *
 * 【vtable 索引依据】（zig libc any-windows-any/d3d9.h 权威声明 + Gen-1 实证）
 *   IDirect3D9(17 项):      CreateDevice = 16
 *   IDirect3DDevice9(119):  Reset=16 Present=17 CreateTexture=23 UpdateTexture=31
 *                           GetDirect3D=6 GetDeviceCaps=7
 *                           GetTexture=64 SetTexture=65
 *                           DrawPrimitive=81 DrawIndexedPrimitive=82
 *   IDirect3DTexture9(22):  GetLevelCount=13 GetLevelDesc=17
 * ---------------------------------------------------------------------------
 * 构建: python -m ziglang cc -target x86-windows-gnu -O2 \
 *           -fno-sanitize=undefined -shared -o d3d9.dll d3d9_proxy.c d3d9.def
 * 日志: 与 dll 同目录 d3d9proxy.log
 * ==========================================================================*/
#include <windows.h>
#include <d3d9.h>

/* ---------------- 编译开关 ---------------- */
#ifndef G3_DIAG
#define G3_DIAG 0            /* 1=诊断版(只记录不替换) 0=生产版 */
#endif
#ifndef IDENT_HASH
#define IDENT_HASH 0   /* 0 = SetTexture 只用尺寸登记表（v21 行为）; 1 = 启用内容哈希身份 */
#endif

#ifndef DIP_RESTORE
#define DIP_RESTORE 1   /* v43：DIP 前还原成我们替换掉的那张纹理（g_bigSrc） */
#endif

#ifndef UT_HASH
#define UT_HASH 0   /* v30：关闭 LockRect 哈希，只做纯计数诊断 */
#endif

#ifndef PRESENT_RESTORE
#define PRESENT_RESTORE 1   /* v29：恢复 v21 的帧末还原行为 */
#endif

#ifndef VERTEX_THRESHOLD
#define VERTEX_THRESHOLD 100   /* primCount 超过此值视为 3D 网格，临时换回小图集 */
#endif

#ifndef DRAW_UNBIND
#define DRAW_UNBIND 0   /* v26: Draw 钩子纯透传，不做任何拦截 */
#endif

#ifndef HOOK_RESET
#define HOOK_RESET 0   /* 0=完全不拦截 Reset（对照实验：怀疑拦截本身干扰 D3D9 重置路径） */
#endif
#ifndef FORCE_POINT_SAMPLER
#define FORCE_POINT_SAMPLER 1   /* 1=强制点采样(需搭配锐化); 0=完全交还引擎默认(双线性) */
#endif
#ifndef BIGTEX_VIA_D3DX
#define BIGTEX_VIA_D3DX 1    /* 1=D3DXCreateTextureFromFileInMemory(MANAGED) */
#endif

/* 大图集尺寸 —— 必须与 gate3_atlas.py 的 NEW_W/NEW_H 及 def 的 atlas_w/h 一致 */
#define ATLAS_W 2048
#define ATLAS_H 1024

/* 字体图集识别判据（诊断版实机确认后再收紧） */
#define FONT_W 512
#define FONT_H 256
#define FONT_FMT D3DFMT_A8R8G8B8   /* = 21 */

/* ---------------- vtable 索引 ---------------- */
#define IX_D3D9_CREATEDEVICE   16
#define IX_DEV_RESET           16
#define IX_DEV_PRESENT         17
#define IX_DEV_CREATETEX       23
#define IX_DEV_UPDATETEX       31
#define IX_DEV_GETDIRECT3D      6
#define IX_DEV_GETDEVICECAPS    7
#define IX_DEV_GETTEXTURE      64
#define IX_DEV_SETTEXTURE      65
#define IX_DEV_DRAWPRIM        81   /* DrawPrimitive          (顶点缓冲, 3D 几何) */
#define IX_DEV_DRAWIDXPRIM     82   /* DrawIndexedPrimitive   (索引缓冲, 3D 几何) */
#define IX_DEV_DRAWPRIMUP      83   /* DrawPrimitiveUP        (2D 文字/精灵, 不拦截) */
#define IX_DEV_DRAWIDXPRIMUP   84   /* DrawIndexedPrimitiveUP (不拦截) */
#define IX_DEV_GETSAMPLER      68   /* GetSamplerState */
#define IX_DEV_SETSAMPLER      69   /* SetSamplerState（强制点采样用） */
#define IX_DEV_TESTCOOP        3    /* TestCooperativeLevel（设备丢失守卫） */
#define IX_DEV_GETRS           58   /* GetRenderState (D3DRS_ZENABLE 等) */
#define IX_DEV_GETTRANSFORM    45   /* GetTransform  (取投影矩阵判正交/透视) */
#define IX_DEV_GETFVF          90   /* GetFVF         (判断是否屏幕空间 2D) */
#define IX_TEX_GETLEVELCOUNT   13   /* IDirect3DBaseTexture9 */
#define IX_TEX_GETLEVELDESC    17   /* IDirect3DTexture9 */
#define DEV_VT_N              119  /* 头文件声明项数（仅作文档/下限参考） */
#define D3D9_VT_N              17
/* 代理槽位总数: 远大于声明项数, 容纳驱动/运行时私有扩展槽;
 * 全部非零填充（真实数据搬不满的部分用 DummySlot 顶上） */
#define DEV_VT_SLOTS          300
#define D3D9_VT_SLOTS          64

#if !G3_DIAG
#include "atlas_png.h"          /* g_atlasPng[] / g_atlasPngLen (gen_atlas_header.py 生成) */
#endif

/* ============================================================================
 * 日志（写 dll 同目录 d3d9proxy.log; 行数上限防爆盘）
 * ==========================================================================*/
static char        g_logPath[MAX_PATH];
static long        g_logLines = 0;
static long        g_logCap   = 40000;
static CRITICAL_SECTION g_logCS;
static int         g_logCSInit = 0;

static void WriteFileLogRaw(const char* s, DWORD len) {
    DWORD n;
    HANDLE h;
    static const char crlf[2] = { 13, 10 };
    if (g_logLines >= g_logCap) return;
    if (g_logCSInit) EnterCriticalSection(&g_logCS);
    h = CreateFileA(g_logPath, FILE_APPEND_DATA, FILE_SHARE_READ | FILE_SHARE_WRITE,
                    NULL, OPEN_ALWAYS, FILE_ATTRIBUTE_NORMAL, NULL);
    if (h != INVALID_HANDLE_VALUE) {
        WriteFile(h, s, len, &n, NULL);
        WriteFile(h, crlf, 2, &n, NULL);
        CloseHandle(h);
        g_logLines++;
    }
    if (g_logCSInit) LeaveCriticalSection(&g_logCS);
}

/* 定长日志（调用方自带 \r\n） */
static void LOG(const char* s) { WriteFileLogRaw(s, lstrlenA(s)); }

/* wsprintfA 版变参日志（单行, 自动补 CRLF; 缓冲 512B）
 * 注: ##__VA_ARGS__ 用于支持无附加参数的单行日志（clang/GNU 扩展） */
#define LOGB(fmt, ...) do { \
    if (g_logLines < g_logCap) { \
        char b_[512]; int n_ = wsprintfA(b_, fmt, ##__VA_ARGS__); \
        if (n_ > 0) WriteFileLogRaw(b_, (DWORD)n_); \
    } } while (0)

/* 地址所属模块名（诊断用; Gen-1 同款） */
static void mod_of(DWORD a, char* out, int outLen) {
    HMODULE hm = 0;
    static char buf[MAX_PATH];
    out[0] = 0;
    if (!GetModuleHandleExA(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS |
                            GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT,
                            (LPCSTR)a, &hm)) { lstrcpynA(out, "?", outLen); return; }
    GetModuleFileNameA(hm, buf, MAX_PATH);
    {
        char* p = strrchr(buf, '\\');
        lstrcpynA(out, p ? p + 1 : buf, outLen);
    }
}

/* ============================================================================
 * 真实 d3d9.dll 转发（17 个命名导出, 全部尾跳转桩; 缺函数者中和为 ret 0）
 * ==========================================================================*/
static HMODULE g_realD3d9 = NULL;

/* 转发目标指针必须是【外部链接】(非 static): COFF 下 static 变量是 LOCAL 符号,
 * naked 桩里的 asm 引用无法由链接器重定位（实测 lld-link: undefined symbol）。
 * 所有大小写条件: 用扩展 asm 的 "m" 操作数让编译器自行处理符号修饰,
 * 生成的机器码为 FF 25 <abs> = jmp dword ptr [目标指针]，是真正的尾跳转。 */
void* g_ptr_Direct3DCreate9           = NULL;
void* g_ptr_Direct3DCreate9Ex         = NULL;
void* g_ptr_Direct3DCreate9On12       = NULL;
void* g_ptr_Direct3DCreate9On12Ex     = NULL;
void* g_ptr_Direct3DShaderValidatorCreate9 = NULL;
void* g_ptr_PSGPError                 = NULL;
void* g_ptr_PSGPSampleTexture         = NULL;
void* g_ptr_D3DPERF_BeginEvent        = NULL;
void* g_ptr_D3DPERF_EndEvent          = NULL;
void* g_ptr_D3DPERF_GetStatus         = NULL;
void* g_ptr_D3DPERF_QueryRepeatFrame  = NULL;
void* g_ptr_D3DPERF_SetMarker         = NULL;
void* g_ptr_D3DPERF_SetOptions        = NULL;
void* g_ptr_D3DPERF_SetRegion         = NULL;
void* g_ptr_DebugSetLevel             = NULL;
void* g_ptr_DebugSetMute              = NULL;
void* g_ptr_D3D9EnableMaxWinShim      = NULL;
void* g_ptr_impl_Direct3DCreate9      = NULL;   /* 钩子实现（DllMain 里赋值） */

/* Direct3DCreate9 = 本代理入口（naked 尾跳转到 impl, 保持 stdcall 语义） */
__attribute__((naked)) void Proxy_Direct3DCreate9(void) {
    __asm__("jmp *%0" :: "m"(g_ptr_impl_Direct3DCreate9));
}
__attribute__((naked)) void Stub_Direct3DCreate9Ex(void) {
    __asm__("jmp *%0" :: "m"(g_ptr_Direct3DCreate9Ex)); }
__attribute__((naked)) void Stub_Direct3DCreate9On12(void) {
    __asm__("jmp *%0" :: "m"(g_ptr_Direct3DCreate9On12)); }
__attribute__((naked)) void Stub_Direct3DCreate9On12Ex(void) {
    __asm__("jmp *%0" :: "m"(g_ptr_Direct3DCreate9On12Ex)); }
__attribute__((naked)) void Stub_Direct3DShaderValidatorCreate9(void) {
    __asm__("jmp *%0" :: "m"(g_ptr_Direct3DShaderValidatorCreate9)); }
__attribute__((naked)) void Stub_PSGPError(void) {
    __asm__("jmp *%0" :: "m"(g_ptr_PSGPError)); }
__attribute__((naked)) void Stub_PSGPSampleTexture(void) {
    __asm__("jmp *%0" :: "m"(g_ptr_PSGPSampleTexture)); }
__attribute__((naked)) void Stub_D3DPERF_BeginEvent(void) {
    __asm__("jmp *%0" :: "m"(g_ptr_D3DPERF_BeginEvent)); }
__attribute__((naked)) void Stub_D3DPERF_EndEvent(void) {
    __asm__("jmp *%0" :: "m"(g_ptr_D3DPERF_EndEvent)); }
__attribute__((naked)) void Stub_D3DPERF_GetStatus(void) {
    __asm__("jmp *%0" :: "m"(g_ptr_D3DPERF_GetStatus)); }
__attribute__((naked)) void Stub_D3DPERF_QueryRepeatFrame(void) {
    __asm__("jmp *%0" :: "m"(g_ptr_D3DPERF_QueryRepeatFrame)); }
__attribute__((naked)) void Stub_D3DPERF_SetMarker(void) {
    __asm__("jmp *%0" :: "m"(g_ptr_D3DPERF_SetMarker)); }
__attribute__((naked)) void Stub_D3DPERF_SetOptions(void) {
    __asm__("jmp *%0" :: "m"(g_ptr_D3DPERF_SetOptions)); }
__attribute__((naked)) void Stub_D3DPERF_SetRegion(void) {
    __asm__("jmp *%0" :: "m"(g_ptr_D3DPERF_SetRegion)); }
__attribute__((naked)) void Stub_DebugSetLevel(void) {
    __asm__("jmp *%0" :: "m"(g_ptr_DebugSetLevel)); }
__attribute__((naked)) void Stub_DebugSetMute(void) {
    __asm__("jmp *%0" :: "m"(g_ptr_DebugSetMute)); }
__attribute__((naked)) void Stub_D3D9EnableMaximizedWindowedModeShim(void) {
    __asm__("jmp *%0" :: "m"(g_ptr_D3D9EnableMaxWinShim)); }

/* 把解析失败的桩中和为 `xor eax,eax; ret 0`（安全返回 0/NULL, 防不同 Windows 版本缺导出） */
static void neutralize_stub(void* fn) {
    DWORD old;
    unsigned char* p = (unsigned char*)fn;
    if (!fn) return;
    if (!VirtualProtect(p, 16, PAGE_EXECUTE_READWRITE, &old)) return;
    p[0] = 0x31; p[1] = 0xC0;   /* xor eax, eax      */
    p[2] = 0xC2; p[3] = 0x00; p[4] = 0x00; /* ret 0 */
    VirtualProtect(p, 16, old, &old);
}

static int resolve_real(void) {
    char sysDir[MAX_PATH];
    char path[MAX_PATH];
    int miss = 0;
    struct { const char* name; void** slot; } tbl[] = {
        { "Direct3DCreate9",           &g_ptr_Direct3DCreate9 },
        { "Direct3DCreate9Ex",         &g_ptr_Direct3DCreate9Ex },
        { "Direct3DCreate9On12",       &g_ptr_Direct3DCreate9On12 },
        { "Direct3DCreate9On12Ex",     &g_ptr_Direct3DCreate9On12Ex },
        { "Direct3DShaderValidatorCreate9", &g_ptr_Direct3DShaderValidatorCreate9 },
        { "PSGPError",                 &g_ptr_PSGPError },
        { "PSGPSampleTexture",         &g_ptr_PSGPSampleTexture },
        { "D3DPERF_BeginEvent",        &g_ptr_D3DPERF_BeginEvent },
        { "D3DPERF_EndEvent",          &g_ptr_D3DPERF_EndEvent },
        { "D3DPERF_GetStatus",         &g_ptr_D3DPERF_GetStatus },
        { "D3DPERF_QueryRepeatFrame",  &g_ptr_D3DPERF_QueryRepeatFrame },
        { "D3DPERF_SetMarker",         &g_ptr_D3DPERF_SetMarker },
        { "D3DPERF_SetOptions",        &g_ptr_D3DPERF_SetOptions },
        { "D3DPERF_SetRegion",         &g_ptr_D3DPERF_SetRegion },
        { "DebugSetLevel",             &g_ptr_DebugSetLevel },
        { "DebugSetMute",              &g_ptr_DebugSetMute },
        { "Direct3D9EnableMaximizedWindowedModeShim", &g_ptr_D3D9EnableMaxWinShim },
    };
    int i, n = (int)(sizeof(tbl) / sizeof(tbl[0]));
    GetSystemDirectoryA(sysDir, MAX_PATH);      /* 32 位进程 -> SysWOW64 */
    lstrcpyA(path, sysDir);
    lstrcatA(path, "\\d3d9.dll");
    g_realD3d9 = LoadLibraryExA(path, NULL, LOAD_WITH_ALTERED_SEARCH_PATH);
    if (!g_realD3d9) { LOG("[INIT] FATAL: cannot load real d3d9.dll\r\n"); return 0; }
    for (i = 0; i < n; i++) {
        *tbl[i].slot = (void*)GetProcAddress(g_realD3d9, tbl[i].name);
        if (!*tbl[i].slot) miss++;
    }
    /* 缺导出的桩中和（Direct3DCreate9 必须成功, 否则代理无意义） */
    if (!g_ptr_Direct3DCreate9) { LOG("[INIT] FATAL: real d3d9.dll lacks Direct3DCreate9"); return 0; }
    neutralize_stub((void*)Stub_Direct3DCreate9Ex);
    neutralize_stub((void*)Stub_Direct3DCreate9On12);
    neutralize_stub((void*)Stub_Direct3DCreate9On12Ex);
    neutralize_stub((void*)Stub_Direct3DShaderValidatorCreate9);
    neutralize_stub((void*)Stub_PSGPError);
    neutralize_stub((void*)Stub_PSGPSampleTexture);
    neutralize_stub((void*)Stub_D3DPERF_BeginEvent);
    neutralize_stub((void*)Stub_D3DPERF_EndEvent);
    neutralize_stub((void*)Stub_D3DPERF_GetStatus);
    neutralize_stub((void*)Stub_D3DPERF_QueryRepeatFrame);
    neutralize_stub((void*)Stub_D3DPERF_SetMarker);
    neutralize_stub((void*)Stub_D3DPERF_SetOptions);
    neutralize_stub((void*)Stub_D3DPERF_SetRegion);
    neutralize_stub((void*)Stub_DebugSetLevel);
    neutralize_stub((void*)Stub_DebugSetMute);
    neutralize_stub((void*)Stub_D3D9EnableMaximizedWindowedModeShim);
    return n - miss;
}

/* ============================================================================
 * 前向声明（attach_* 先于 Hook_* 定义; 注意真实 d3d9.dll 全进程只有一个
 * IDirect3D9 vtable, 故 D3D9 层用单例克隆即完备）
 * ==========================================================================*/
static long WINAPI Hook_CreateDevice(void*, UINT, D3DDEVTYPE, HWND, DWORD,
                                     D3DPRESENT_PARAMETERS*, IDirect3DDevice9**);
static long WINAPI Hook_CreateTexture(void*, UINT, UINT, UINT, DWORD, D3DFORMAT,
                                      D3DPOOL, IDirect3DTexture9**, HANDLE*);
static long WINAPI Hook_UpdateTexture(void*, IDirect3DBaseTexture9*, IDirect3DBaseTexture9*);
static long WINAPI Hook_SetTexture(void*, DWORD, IDirect3DBaseTexture9*);
static long WINAPI Hook_Reset(void*, D3DPRESENT_PARAMETERS*);
static long WINAPI Hook_Present(void*, const RECT*, const RECT*, HWND, const RGNDATA*);
static long WINAPI Hook_GetDirect3D(void*, IDirect3D9**);
static long WINAPI Hook_DrawPrimitive(void*, D3DPRIMITIVETYPE, UINT, UINT);
static long WINAPI Hook_DrawIndexedPrimitive(void*, D3DPRIMITIVETYPE, INT,
                                             UINT, UINT, UINT, UINT);
static long WINAPI Hook_DrawPrimitiveUP(void*, D3DPRIMITIVETYPE, UINT,
                                        const void*, UINT);
static long WINAPI Hook_DrawIndexedPrimitiveUP(void*, D3DPRIMITIVETYPE, UINT, UINT,
                                               const void*, D3DFORMAT,
                                               const void*, UINT);
static long WINAPI Hook_SetSamplerState(void*, DWORD, D3DSAMPLERSTATETYPE, DWORD);

/* ============================================================================
 * 全局状态
 * ==========================================================================*/
static const char* g_ckpt = "init";
static void* g_exeBase   = NULL;     /* 主模块基址（RA 相对偏移用） */
static long  g_stxN      = 0;        /* [STX] 诊断条数 */
static long  g_swapLogN  = 0;        /* [SWAP] 诊断条数 */
static long  g_rstrLogN  = 0;        /* [RSTR] 诊断条数 */
static long  g_utxN      = 0;        /* [UTX] 诊断条数 */

/* ★ v30：Draw 计数诊断（纯观测，不影响渲染） */
static long  g_draws_since_swap = 0;   /* 距离上次换入大图集的绘制次数 */
static long  g_drawsMax         = 0;   /* 历史最大 */
static long  g_leakCandN        = 0;   /* 已打印的候选条数 */
static long  g_leakSuppressed   = 0;   /* 超上限被抑制的条数 */
static long  g_mile             = 5;   /* 精确触发点：5,10,20,40,80... */
static void* g_lastFontPtr      = NULL;/* 最近一次换入图集时游戏的字体指针 */
static void* g_lastSwapRA       = NULL;/* 最近一次换入图集时的 RA */
/* ★ v34：最后一个非字体 stage0 纹理 */
static void* g_prev0 = NULL;

/* ★ v35：诊断状态 */
#define TS_MAX 64
static struct { DWORD stage; void* tex; } g_ts[TS_MAX];
static int  g_tsN = 0;
static long g_tsSup = 0;          /* 超出上限被抑制的组数 */
static long g_dipLeakN = 0;
static int  g_restoreTarget = -1;   /* -1=未初始化; 0=NULL,1=字体,2=prev0 */
static long g_dipRstN = 0;
static void* g_last3D0 = NULL;      /* 上一次 3D 绘制时 stage0 的材质纹理 */
static long  g_last3DFrame = -1;    /* 抓取所在帧（每帧只抓一次） */
static long  g_staleN = 0;         /* v44：指针复用（登记表命中但尺寸不符）计数 */
static void* g_beforeSwap = NULL;   /* 换绑前一刻 stage0 上的纹理 */

static long g_frames;   /* 前向声明（真正定义在下方） */

static void rt_init_once(void) {
    if (g_restoreTarget >= 0) return;
    {
        char b[16];
        DWORD got = GetEnvironmentVariableA("O2_RESTORE_TARGET", b, (DWORD)sizeof(b));
        g_restoreTarget = (got > 0 && b[0] >= '0' && b[0] <= '4') ? (b[0] - '0') : 4;
        LOGB("[CFG] 还原目标 = %d (%s)", g_restoreTarget,
             g_restoreTarget == 0 ? "NULL" : g_restoreTarget == 1 ? "字体"
             : g_restoreTarget == 2 ? "prev0" : g_restoreTarget == 3 ? "last3D0"
             : "beforeSwap(换绑前那张)");
    }
}
static long g_dipLeakSup = 0;

/* RA → 模块名 + 模块内偏移 */
static void ra_module(void* ra, char* out, int cap, unsigned long* off) {
    HMODULE hm = NULL;
    char path[MAX_PATH];
    int i, k = 0, last = -1;
    *off = 0;
    out[0] = 0;
    if (GetModuleHandleExA(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS
                           | GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT,
                           (LPCSTR)ra, &hm) && hm) {
        *off = (unsigned long)((char*)ra - (char*)hm);
        if (GetModuleFileNameA(hm, path, MAX_PATH)) {
            for (i = 0; path[i]; i++) if (path[i] == '\\' || path[i] == '/') last = i;
            for (i = last + 1; path[i] && k < cap - 1; i++) out[k++] = path[i];
            out[k] = 0;
        }
    }
    if (!k) { out[0] = '?'; out[1] = 0; }
}
static long  g_devLostFrame  = -1;           /* 上次查询 TestCooperativeLevel 的帧号 */
static int   g_devLost       = 0;            /* 1 = 设备已丢失, 所有 hook 直通 */
static int   g_bigAt0        = 0;            /* 账本: stage0 当前绑的是我们的大图集 */
static long  g_frameRestoreN = 0;            /* 帧末还原次数 */
static long  g_bkLogN       = 0;            /* 账本跃迁日志条数上限 */
static long g_frames = 0;
static long g_resetN = 0;
static long g_createN = 0;
static long g_bindN = 0;
static long g_fontBindN = 0;
static long g_swapN = 0;
static long g_healN = 0;
static long g_ctLogN = 0;     /* CreateTexture 日志条数 */
static long g_stLogN = 0;     /* SetTexture/UpdateTexture 日志条数 */

/* 字体图集指针登记（游戏可能反复重建, Gen-1 c44 教训: 跟踪最新指针） */
#define FONT_TEX_MAX 32
static void* g_fontTexes[FONT_TEX_MAX];
static int   g_fontTexN = 0;
static int   g_fontTexFull = 0;

static int is_font_tex(void* t) {
    int i;
    if (!t) return 0;
    for (i = 0; i < g_fontTexN; i++) if (g_fontTexes[i] == t) return 1;
    return 0;
}

/* ★ v26：内容哈希识别（借鉴一代 c62/c92 思想，按二代实测路径重写）
 *   - 哈希对象 = UpdateTexture 的 src（pool=2 SYSTEMMEM，可 Lock）
 *   - 命中后把 dst 记为"字体载体"，SetTexture 严格按指针命中
 *   - 载体用 FIFO 集合（游戏会重建字体纹理，单指针会失效） */
#define FONT_CARRIER_MAX 8
#define FONT_BAD_MAX     32
static void*        g_badTex[FONT_BAD_MAX];   /* 已确认【非字体】的 512x256 纹理指针 */
static int          g_badTexN   = 0;
static unsigned int g_badHash[8];             /* 已确认非字体的内容哈希 */
static int          g_badHashN  = 0;
static long         g_badSkipN  = 0;          /* 因命中黑名单而跳过替换的次数 */

static int is_bad_tex(void* t) {
    int i;
    if (!t) return 0;
    for (i = 0; i < g_badTexN; i++) if (g_badTex[i] == (void*)t) return 1;
    return 0;
}

static int is_bad_hash(unsigned int h) {
    int i;
    for (i = 0; i < g_badHashN; i++) if (g_badHash[i] == h) return 1;
    return 0;
}

static void bad_add(unsigned int h, void* dst, const char* why) {
    if (h && !is_bad_hash(h) && g_badHashN < 8) {
        g_badHash[g_badHashN++] = h;
    }
    if (dst) {
        int i;
        for (i = 0; i < g_badTexN; i++) if (g_badTex[i] == dst) return;
        if (g_badTexN < FONT_BAD_MAX) g_badTex[g_badTexN++] = dst;
        LOGB("[BLACK] %s hash=0x%08lX dst=%p (黑名单 #%d, 哈希档 %d)",
             why, (unsigned long)h, dst, g_badTexN, g_badHashN);
    }
}
static void*        g_fontCarrier[FONT_CARRIER_MAX];
static int          g_fontCarrierN  = 0;
static unsigned int g_fontHash      = 0;     /* 字体内容 FNV-1a 基准 */
static long         g_utN           = 0;     /* UpdateTexture 拦截数 */
static long         g_utFontN       = 0;     /* 尺寸命中 512x256 的次数 */
static long         g_hashOKN       = 0;     /* 成功算出哈希的次数 */
static long         g_hashFailN     = 0;     /* Lock/读取失败次数 */
static long         g_identHitN     = 0;     /* SetTexture 命中载体并替换的次数 */
static long         g_resetHrLogN   = 0;

static int carrier_has(void* t) {
    int i;
    if (!t) return 0;
    for (i = 0; i < g_fontCarrierN; i++) if (g_fontCarrier[i] == (void*)t) return 1;
    return 0;
}

static void carrier_add(void* d) {
    int i;
    if (!d) return;
    for (i = 0; i < g_fontCarrierN; i++) if (g_fontCarrier[i] == d) return;
    if (g_fontCarrierN < FONT_CARRIER_MAX) {
        g_fontCarrier[g_fontCarrierN++] = d;
    } else {
        for (i = 1; i < FONT_CARRIER_MAX; i++) g_fontCarrier[i - 1] = g_fontCarrier[i];
        g_fontCarrier[FONT_CARRIER_MAX - 1] = d;
    }
    LOGB("[HASH] 字体载体加入 #%d dst=%p (hash=0x%08lX)", g_fontCarrierN, d,
         (unsigned long)g_fontHash);
}

/* FNV-1a 32bit：对【UpdateTexture 的 src】（SYSTEMMEM，可 Lock）整块读取后哈希。
 * 一代 c62 经验：不缓存、读固定字节块、不依赖"这个纹理一定代表字体"。
 * 返回 0 = 读取失败（此时必须放弃本次识别，绝不写入错误基准）。 */
static unsigned int hash_src_texture(void* src) {
    IDirect3DTexture9* t = (IDirect3DTexture9*)src;
    D3DLOCKED_RECT lr;
    unsigned int h = 2166136261u;
    unsigned long i, total;
    unsigned char* p;
    if (!t || !t->lpVtbl || !t->lpVtbl->LockRect || !t->lpVtbl->UnlockRect) {
        if (g_hashFailN < 8) { g_hashFailN++; LOGB("[HASH] 失败: src=%p vtable 不全", src); }
        return 0;
    }
    ZeroMemory(&lr, sizeof(lr));
    if (t->lpVtbl->LockRect(t, 0, &lr, NULL, D3DLOCK_READONLY) != D3D_OK
        || !lr.pBits || lr.Pitch <= 0) {
        if (g_hashFailN < 8) {
            g_hashFailN++;
            LOGB("[HASH] 失败: src=%p LockRect hr/试读失败 pitch=%ld bits=%p",
                 src, (long)lr.Pitch, lr.pBits);
        }
        return 0;
    }
    total = (unsigned long)lr.Pitch * (unsigned long)FONT_H;   /* 整张 512x256 */
    if (total > 512u * 1024u) total = 512u * 1024u;            /* 上限 512KB */
    p = (unsigned char*)lr.pBits;
    for (i = 0; i < total; i++) {
        h ^= (unsigned int)p[i];
        h *= 16777619u;
    }
    t->lpVtbl->UnlockRect(t, 0);
    g_hashOKN++;
    if (g_hashOKN <= 6)
        LOGB("[HASH] OK src=%p pitch=%ld 读取=%lu 字节 hash=0x%08lX",
             src, (long)lr.Pitch, total, (unsigned long)(h ? h : 1u));
    return h ? h : 1u;
}


static void font_tex_add(void* t) {
    int i;
    if (!t) return;
    for (i = 0; i < g_fontTexN; i++) if (g_fontTexes[i] == t) return;  /* 去重 */
    if (g_fontTexN >= FONT_TEX_MAX) {
        /* 表满：淘汰最旧的一条（Reset 后游戏反复重建字体时，表的持续可用比保全都重要） */
        int k;
        for (k = 1; k < FONT_TEX_MAX; k++) g_fontTexes[k - 1] = g_fontTexes[k];
        g_fontTexes[FONT_TEX_MAX - 1] = t;
        if (!g_fontTexFull) {
            g_fontTexFull = 1;
            LOGB("[WARN] 字体纹理登记满(%d)，改为淘汰最旧", FONT_TEX_MAX);
        }
        return;
    }
    g_fontTexes[g_fontTexN++] = t;
    LOGB("[FONT] 字体图集登记 #%d tex=%p (%dx%d fmt=%d)", g_fontTexN, t, FONT_W, FONT_H, (int)FONT_FMT);
}

/* 大图集纹理 */
static IDirect3DTexture9* g_bigTex = NULL;
static void* g_bigDev = NULL;
static int   g_bigTexFail = 0;   /* 本设备创建失败过 -> 不重试 */

/* 大图集对应的"原版字体纹理"：DrawPrimitive 拦截时用它临时顶回 stage0 */
static IDirect3DTexture9* g_bigSrc = NULL;

/* 图集泄露拦截统计 */
static long g_dpN = 0,  g_dpRevN = 0;     /* DrawPrimitive          */
static long g_dipN = 0, g_dipRevN = 0;    /* DrawIndexedPrimitive   */
static long g_upN = 0,  g_upAtlasN = 0;   /* DrawPrimitiveUP        (仅观测) */
static long g_upiN = 0, g_upiAtlasN = 0;  /* DrawIndexedPrimitiveUP (仅观测) */
static long g_revLogN = 0;                /* 拦截明细日志条数上限 */

/* 门槛判定统计（实机 dp=8.8M / dip=0 -> 全引擎只走 DrawPrimitive,
 * 必须靠渲染状态区分 2D 文字 与 3D 几何） */
static long g_atlasBoundN = 0;            /* 绘制时 stage0 == 大图集 */
static long g_skipRhwN   = 0;             /* 其中 XYZRHW 屏幕空间 2D -> 放过 */
static long g_skipOrthoN = 0;             /* 其中 正交投影(UI)       -> 放过 */
static long g_skipZoffN  = 0;             /* 其中 ZENABLE 关闭      -> 放过 */
static long g_gateLogN   = 0;             /* 门槛明细日志条数上限 */

/* --- 点采样强制（消除字边缘灰糊）--- */
static int  g_fontStage = -1;            /* 大图集当前所在 stage；-1=未绑定 */
static long g_sampN = 0;                 /* 被改写的采样器设置次数 */
static long g_sampLogN = 0;              /* 采样器日志条数上限 */
static long g_devLostLogN = 0;           /* 设备异常日志条数上限 */

/* 纹理描述缓存（SetTexture 诊断用, 64 槽 hash） */
typedef struct { void* tex; DWORD w, h, lv; D3DFORMAT fmt; D3DPOOL pool; } TexDesc;
static TexDesc g_dcache[64];

/* ★ v46：运行时改写 exe 里的"成就"标题（只改内存，不改文件） */
static int wstr_eq(const unsigned short* a, const char* b) {
    int i = 0;
    while (b[i]) {
        if ((unsigned char)b[i] != (unsigned char)a[i]) return 0;
        i++;
    }
    return a[i] == 0;   /* a 也要在这里结束 */
}

static void patch_ach_label(void) {
    typedef BOOL (WINAPI *PFN_VP)(LPVOID, SIZE_T, DWORD, LPDWORD);
    HMODULE base = GetModuleHandleA(NULL);
    unsigned char* p;
    unsigned char* end;
    DWORD old = 0;
    int hits = 0;
    static const char* kTarget = "Achievements";
    static const char* kAlts[] = { "Erfolge", "Obiettivi", "Logros", NULL };  /* Succès 有重音，单独处理 */
    int i, k;

    if (!base) return;
    p = (unsigned char*)base;
    /* 用 PE 的 SizeOfImage 限定扫描范围 */
    {
        IMAGE_DOS_HEADER* dos = (IMAGE_DOS_HEADER*)p;
        IMAGE_NT_HEADERS* nt;
        DWORD size;
        if (dos->e_magic != IMAGE_DOS_SIGNATURE) { LOGB("[ACH] 非 PE，跳过"); return; }
        nt = (IMAGE_NT_HEADERS*)(p + dos->e_lfanew);
        if (nt->Signature != IMAGE_NT_SIGNATURE) { LOGB("[ACH] NT 头异常，跳过"); return; }
        size = nt->OptionalHeader.SizeOfImage;
        end = p + size;
    }

    /* 1) 找 "Achievements"（UTF-16） */
    {
        unsigned char* q = p;
        unsigned char* found = NULL;
        while (q + 26 < end) {
            if (q[0] == 'A' && q[1] == 0 && q[2] == 'c' && q[3] == 0
                && q[4] == 'h' && q[5] == 0 && wstr_eq((const unsigned short*)q, kTarget)) {
                found = q;
                break;
            }
            q += 2;
        }
        if (!found) { LOGB("[ACH] 未找到宽字符串 Achievements，跳过"); return; }

        /* 2) 从该处起 1KB 内逐个宽字符串检查并改写 */
        {
            unsigned char* q2 = found;
            unsigned char* limit = found + 1024;
            while (q2 + 4 < limit && q2 + 4 < end) {
                /* q2 指向一个宽字符串起点：前两个字节非 0 且后两个字节为 0 */
                if (q2[1] == 0 && q2[0] >= 0x20 && q2[0] < 0x7f) {
                    int match = 0;
                    if (wstr_eq((const unsigned short*)q2, kTarget)) match = 1;
                    if (!match) {
                        for (i = 0; kAlts[i]; i++)
                            if (wstr_eq((const unsigned short*)q2, kAlts[i])) { match = 1; break; }
                    }
                    /* Succès：宽字符里 è = 0x00E8，只比前 4 个 ASCII 字符 */
                    if (!match && q2[0] == 'S' && q2[1] == 0 && q2[2] == 'u' && q2[3] == 0
                        && q2[4] == 'c' && q2[5] == 0 && q2[6] == 'c' && q2[7] == 0)
                        match = 2;

                    if (match) {
                        DWORD protect = 0;
                        if (((PFN_VP)VirtualProtect)(q2, 4, PAGE_READWRITE, &protect)) {
                            ((unsigned short*)q2)[0] = 0x6210;   /* 成 */
                            ((unsigned short*)q2)[1] = 0x5C31;   /* 就 */
                            ((unsigned short*)q2)[2] = 0;        /* ★ 必须补 NUL，否则残留原串尾部 */
                            VirtualProtect(q2, 4, protect, &protect);
                            hits++;
                        }
                    }
                    /* 跳到该字符串结尾 */
                    while (q2 + 1 < end && !(q2[0] == 0 && q2[1] == 0)) q2 += 2;
                }
                q2 += 2;
            }
        }
    }
    LOGB("[ACH] 成就标题已改写 %d 处（共 5 语种）", hits);
}

/* ★ v45：不查缓存的版本——用于"指针是否被复用"的最终判定 */
static int tex_desc_direct(void* tex, TexDesc* out) {
    void** tv;
    D3DSURFACE_DESC sd;
    if (!tex || !out) return 0;
    tv = *(void***)tex;
    if (!tv || !tv[IX_TEX_GETLEVELDESC]) return 0;
    ZeroMemory(&sd, sizeof(sd));
    if (((HRESULT (WINAPI *)(void*, UINT, D3DSURFACE_DESC*))tv[IX_TEX_GETLEVELDESC])(tex, 0, &sd) != D3D_OK)
        return 0;
    out->w = sd.Width; out->h = sd.Height; out->fmt = sd.Format; out->pool = sd.Pool;
    return 1;
}

static int tex_desc(void* tex, TexDesc* out) {
    void** tv;
    D3DSURFACE_DESC sd;
    unsigned int slot = ((unsigned int)(size_t)tex >> 2) & 63;
    TexDesc* e = &g_dcache[slot];
    if (e->tex == tex && e->w) { *out = *e; return 1; }
    if (!tex) return 0;
    tv = *(void***)tex;
    if (!tv || !tv[IX_TEX_GETLEVELDESC]) return 0;
    ZeroMemory(&sd, sizeof(sd));
    if (((HRESULT (WINAPI *)(void*, UINT, D3DSURFACE_DESC*))tv[IX_TEX_GETLEVELDESC])(tex, 0, &sd) != D3D_OK)
        return 0;
    e->tex = tex; e->w = sd.Width; e->h = sd.Height;
    e->fmt = sd.Format; e->pool = sd.Pool;
    e->lv = tv[IX_TEX_GETLEVELCOUNT]
          ? ((DWORD (WINAPI *)(void*))tv[IX_TEX_GETLEVELCOUNT])(tex) : 1;
    *out = *e;
    return 1;
}

/* 安全着陆垫: 若某个「未被真实占用」的槽位被调用, 在此被捕获并记录一次,
 * 返回 E_NOTIMPL, 而不是让 EIP 跳到 0 地址导致进程闪退。
 * 注: COM 方法为 stdcall, 未知槽位的参数个数无法预知, 故本垫仅作最后防线 +
 *     取证用; 正常路径（拷贝覆盖区）永远不该进入。 */
#define G3_E_NOTIMPL 0x80004001L
static long g_dummyHits = 0;
static long WINAPI DummySlot(void) {
    if (g_dummyHits < 8) {
        g_dummyHits++;
        LOGB("[DUMMY] 命中未被真实数据覆盖的槽位 (第 %ld 次) -> 返回 E_NOTIMPL",
             g_dummyHits);
    }
    return G3_E_NOTIMPL;
}

/* 源 vtable 可读槽位数（只用于避免 memcpy 读穿页面边界, 不是长度探测） */
static int readable_slots(void** vt, int cap) {
    MEMORY_BASIC_INFORMATION mbi;
    SIZE_T span;
    if (!vt) return 0;
    if (!VirtualQuery((LPCVOID)vt, &mbi, sizeof(mbi))) return 0;
    if (!(mbi.State & MEM_COMMIT)) return 0;
    if (mbi.Protect & (PAGE_NOACCESS | PAGE_GUARD)) return 0;
    span = (SIZE_T)((char*)mbi.BaseAddress + mbi.RegionSize) - (SIZE_T)vt;
    if (span > (SIZE_T)cap * sizeof(void*)) span = (SIZE_T)cap * sizeof(void*);
    return (int)(span / sizeof(void*));
}

/* ============================================================================
 * vtable 克隆挂载（业界标准: 大槽位数组 + 全量搬表 + Dummy 填尾 + 定点 patch）
 *
 *   T7 关键修复 (root cause):
 *     旧实现按头文件「声明项数」截尾拷贝（设备 119 / D3D9 17）。运行时 d3d9
 *     （含 N 卡/A 卡驱动相关实现）会在声明项之后带私有/扩展槽位, 内部派发会
 *     经这些高位槽位。截尾 -> 这些槽位为 0 -> 调用时 EIP 跳到 0 地址。
 *     实证: selftest32 走 Reset 抛 AV code=0xC0000005 addr=00000000;
 *           无代理基线 resetbase32.exe 同序列 Reset hr=0 正常 -> 崩溃确由代理引入。
 *
 *   做法:
 *     1) VirtualAlloc 申请 slots 个槽位（提交页由 OS 零初始化, 仍显式清零）
 *     2) 原样 memcpy 搬原始 vtable（拷贝数 = min(slots, 可读槽数)）
 *        —— 多搬的部分与原表逐字节一致, 行为与「无代理」完全相同
 *     3) 剩余槽位全部写入 DummySlot —— 克隆表里不存在任何 NULL 项
 *     4) 把对象首指针改为这份大表; 只 patch 明确要 Hook 的槽位
 * ==========================================================================*/
static void** make_clone(void** realVt, int slots, const char* tag) {
    void** fake;
    int copy, i;
    if (!realVt) return NULL;
    fake = (void**)VirtualAlloc(NULL, (SIZE_T)slots * sizeof(void*),
                                MEM_COMMIT | MEM_RESERVE, PAGE_EXECUTE_READWRITE);
    if (!fake) { LOGB("[FATAL] vtable 克隆 VirtualAlloc 失败 (%d 槽)", slots); return NULL; }
    for (i = 0; i < slots; i++) fake[i] = NULL;          /* 防御性清零 */
    copy = readable_slots(realVt, slots);
    if (copy < slots)
        LOGB("[WARN] %s: 源 vtable 可读 %d 槽 (<%d), %d 槽由 Dummy 填充",
             tag, copy, slots, slots - copy);
    for (i = 0; i < copy; i++) fake[i] = realVt[i];      /* 原表原样搬 */
    for (i = copy; i < slots; i++) fake[i] = (void*)DummySlot;   /* 杜绝 NULL 槽 */
    LOGB("[VT] %s: 槽位=%d 拷贝原表=%d Dummy=%d  orig=%p -> clone=%p",
         tag, slots, copy, slots - copy, (void*)realVt, (void*)fake);
    return fake;
}

/* ---- IDirect3D9 层（单例克隆） ---- */
static void** g_d3d9OrigVt  = NULL;
static void** g_d3d9CloneVt = NULL;

static void attach_d3d9(void* obj) {
    void** vt;
    char m[64];
    if (!obj) return;
    vt = *(void***)obj;
    if (!vt) return;
    if (vt == g_d3d9CloneVt) return;                 /* 已挂 */
    if (vt != g_d3d9OrigVt) {                        /* 新 vtable -> 建克隆 */
        g_d3d9OrigVt  = vt;
        g_d3d9CloneVt = make_clone(vt, D3D9_VT_SLOTS, "IDirect3D9");
        if (g_d3d9CloneVt)
            g_d3d9CloneVt[IX_D3D9_CREATEDEVICE] = (void*)Hook_CreateDevice;
        mod_of((DWORD)vt, m, 64);
        LOGB("[D3D9] clone vt=%p (%s) -> %p, patch vt[%d]=CreateDevice",
             (void*)vt, m, (void*)g_d3d9CloneVt, IX_D3D9_CREATEDEVICE);
    }
    if (g_d3d9CloneVt) *(void***)obj = g_d3d9CloneVt;
}

/* ---- IDirect3DDevice9 层（多设备注册表, 上限 4） ---- */
typedef struct { void* dev; void** origVt; void** cloneVt; } DevRec;
/* 采样器 hook 用的函数指针（必须早于 force_point_sampler） */
typedef HRESULT (WINAPI *PFN_GETSAMP)(void*, DWORD, D3DSAMPLERSTATETYPE, DWORD*);
typedef HRESULT (WINAPI *PFN_SETSAMP)(void*, DWORD, D3DSAMPLERSTATETYPE, DWORD);
typedef HRESULT (WINAPI *PFN_TCL)(void*);
static DevRec g_devs[4];
static int    g_devN = 0;

/* 设备丢失守卫：每帧最多查一次 TestCooperativeLevel（走原 vtable，避免递归）。
 * 返回 1 = 设备已丢失 —— 此时所有 hook 必须**原样透传**，
 * 绝不做纹理替换 / 解绑 / vtable 修补，否则会在引擎销毁资源时撞车。 */
static int dev_lost(void* self, DevRec* r) {
    HRESULT hr;
    if (g_devLostFrame == g_frames) return g_devLost;
    g_devLostFrame = g_frames;
    if (!r || !r->origVt || !r->origVt[IX_DEV_TESTCOOP]) { g_devLost = 0; return 0; }
    hr = ((PFN_TCL)r->origVt[IX_DEV_TESTCOOP])(self);
    g_devLost = (hr != D3D_OK);
    if (g_devLost && g_devLostLogN < 10) {
        g_devLostLogN++;
        LOGB("[GUARD] TestCooperativeLevel=0x%08lX -> 本帧起全部 hook 直通(不替换/不解绑/不heal)",
             (unsigned long)hr);
    }
    return g_devLost;
}

static DevRec* dev_find(void* dev) {
    int i;
    for (i = 0; i < g_devN; i++) if (g_devs[i].dev == dev) return &g_devs[i];
    return NULL;
}

/* 功能自检: vt[65] 必须真是 SetTexture（对 stage0 解绑必须返回 D3D_OK 且
 * GetTexture 回读 NULL）。索引错则不挂 hook（安全失败, 游戏原样运行）。 */
static int selftest_settexture(void* dev, void** vt) {
    typedef HRESULT (WINAPI *PFN_ST)(void*, DWORD, IDirect3DBaseTexture9*);
    typedef HRESULT (WINAPI *PFN_GT)(void*, DWORD, IDirect3DBaseTexture9**);
    IDirect3DBaseTexture9* got = (IDirect3DBaseTexture9*)0x1;
    HRESULT hr;
    if (!vt[IX_DEV_SETTEXTURE] || !vt[IX_DEV_GETTEXTURE]) return 0;
    hr = ((PFN_ST)vt[IX_DEV_SETTEXTURE])(dev, 0, NULL);
    if (hr != D3D_OK) {
        LOGB("[SELF] vt[%d] SetTexture(stage0,NULL) hr=0x%08lX -> 索引可疑, 不挂 hook",
             IX_DEV_SETTEXTURE, (unsigned long)hr);
        return 0;
    }
    hr = ((PFN_GT)vt[IX_DEV_GETTEXTURE])(dev, 0, &got);
    if (hr != D3D_OK || got != NULL) {
        LOGB("[SELF] vt[%d] GetTexture 回读异常 hr=0x%08lX p=%p -> 索引可疑",
             IX_DEV_GETTEXTURE, (unsigned long)hr, (void*)got);
        return 0;
    }
    return 1;
}

static void attach_dev(void* dev) {
    void** vt;
    DevRec* r = dev_find(dev);
    char m[64];
    int i;
    if (!dev) return;
    vt = *(void***)dev;
    if (!vt) return;
    if (r) {                                         /* 已挂: heal 检查 */
        if (*(void***)dev != r->cloneVt) {
            *(void***)dev = r->cloneVt;
            g_healN++;
            LOGB("[HEAL] 设备 vtable 被还原, 重新指向 clone #%d", (int)(r - g_devs));
        }
        return;
    }
    if (g_devN >= 4) { LOGB("[FATAL] 设备数超过 4, 放弃挂载（游戏原样运行）"); return; }
    if (!selftest_settexture(dev, vt)) return;       /* 索引自检失败 -> 不挂 */
    {
        void** clone = make_clone(vt, DEV_VT_SLOTS, "IDirect3DDevice9");
        if (!clone) { LOGB("[FATAL] vtable 克隆失败"); return; }
        /* 只 patch 明确要 Hook 的槽位, 其余全部保持原表内容 */
        clone[IX_DEV_CREATETEX]     = (void*)Hook_CreateTexture;
        clone[IX_DEV_UPDATETEX]     = (void*)Hook_UpdateTexture;
        clone[IX_DEV_SETTEXTURE]    = (void*)Hook_SetTexture;
#if HOOK_RESET
        clone[IX_DEV_RESET]         = (void*)Hook_Reset;
#endif
        clone[IX_DEV_PRESENT]       = (void*)Hook_Present;
        clone[IX_DEV_GETDIRECT3D]   = (void*)Hook_GetDirect3D;
        clone[IX_DEV_DRAWPRIM]      = (void*)Hook_DrawPrimitive;
        clone[IX_DEV_DRAWIDXPRIM]   = (void*)Hook_DrawIndexedPrimitive;
        clone[IX_DEV_DRAWPRIMUP]    = (void*)Hook_DrawPrimitiveUP;
        clone[IX_DEV_DRAWIDXPRIMUP] = (void*)Hook_DrawIndexedPrimitiveUP;
#if FORCE_POINT_SAMPLER
        /* 索引合理性检查：vt[69] 必须存在且不等于 vt[65]（否则索引可疑，宁可不挂） */
        if (vt[IX_DEV_SETSAMPLER] && vt[IX_DEV_SETSAMPLER] != vt[IX_DEV_SETTEXTURE])
            clone[IX_DEV_SETSAMPLER] = (void*)Hook_SetSamplerState;
        else
            LOGB("[WARN] vt[%d]=%p 可疑，不挂 SetSamplerState（点采样将失效）",
                 IX_DEV_SETSAMPLER, (void*)vt[IX_DEV_SETSAMPLER]);
#endif
        g_devs[g_devN].dev = dev;
        g_devs[g_devN].origVt = vt;
        g_devs[g_devN].cloneVt = clone;
        r = &g_devs[g_devN];
        g_devN++;
        *(void***)dev = clone;                        /* 对象首指针 -> 大克隆表 */
        {
            static const int kIdx[11] = {
                IX_DEV_CREATETEX, IX_DEV_UPDATETEX, IX_DEV_SETTEXTURE,
                IX_DEV_RESET, IX_DEV_PRESENT, IX_DEV_GETDIRECT3D,
                IX_DEV_DRAWPRIM, IX_DEV_DRAWIDXPRIM,
                IX_DEV_DRAWPRIMUP, IX_DEV_DRAWIDXPRIMUP, IX_DEV_SETSAMPLER
            };
            for (i = 0; i < 11; i++) {
                mod_of((DWORD)vt[kIdx[i]], m, 64);
                LOGB("[DEV] vt[%d]=%p (%s) -> hook", kIdx[i], (void*)vt[kIdx[i]], m);
            }
            LOGB("[DEV] device=%p 已挂 %d 个 hook (clone=%p, 槽位=%d)",
                 dev, 11, (void*)clone, DEV_VT_SLOTS);
        }
    }
}

/* ============================================================================
 * 大图集创建（懒: 首次识别到字体图集时, 用同一设备创建）
 * ==========================================================================*/
static void ensure_big_tex(void* dev) {
#if G3_DIAG
    (void)dev; return;                              /* 诊断版不建纹理 */
#else
    HMODULE hx;
    typedef HRESULT (WINAPI *PFN_TexMem)(IDirect3DDevice9*, LPCVOID, UINT, IDirect3DTexture9**);
    typedef HRESULT (WINAPI *PFN_TexMemEx)(IDirect3DDevice9*, LPCVOID, UINT,
                                           UINT, UINT, UINT, DWORD, D3DFORMAT,
                                           D3DPOOL, DWORD, DWORD, D3DCOLOR,
                                           void*, void*, IDirect3DTexture9**);
    PFN_TexMem pfn;
    PFN_TexMemEx pfx;
    IDirect3DTexture9* tex = NULL;
    D3DSURFACE_DESC sd;
    HRESULT hr;
    char m[64];

    if (!dev) return;
    if (g_bigTex) {
        if (g_bigDev == dev) return;                /* 已就绪 */
        /* 设备更换: 释放旧大纹理（旧设备持有的资源随之清理） */
        LOGB("[BIG] 设备更换 %p -> %p, 释放旧大纹理 %p", g_bigDev, dev, (void*)g_bigTex);
        g_bigTex->lpVtbl->Release(g_bigTex);
        g_bigTex = NULL; g_bigDev = NULL;
        g_bigSrc = NULL;                            /* 旧设备字体纹理已失效 */
    }
    if (g_bigTexFail) return;                       /* 本设备已失败过, 不重试 */

    {   /* 手动兜底：O2_BADHASH=7122FAA5 可强制拉黑一个哈希 */
        char envb[32];
        DWORD got = GetEnvironmentVariableA("O2_BADHASH", envb, (DWORD)sizeof(envb));
        if (got > 0) {
            unsigned int hh = 0; int k = 0; int okhex = 1;
            while (envb[k]) {
                char c = envb[k++];
                if (c >= '0' && c <= '9') hh = hh * 16u + (unsigned int)(c - '0');
                else if (c >= 'a' && c <= 'f') hh = hh * 16u + (unsigned int)(c - 'a' + 10);
                else if (c >= 'A' && c <= 'F') hh = hh * 16u + (unsigned int)(c - 'A' + 10);
                else { okhex = 0; break; }
            }
            if (okhex && hh) {
                bad_add(hh, NULL, "环境变量 O2_BADHASH 强制拉黑");
                if (g_badHashN <= 8) LOGB("[BLACK] O2_BADHASH=0x%08lX 已加入黑名单哈希档",
                                          (unsigned long)hh);
            }
        }
    }
    {   /* v46：一次性改写 exe 里的成就标题 */
        static int achDone = 0;
        if (!achDone) { achDone = 1; patch_ach_label(); }
    }
    g_ckpt = "BIG:1-d3dx";
    hx = GetModuleHandleA("d3dx9_42.dll");
    if (!hx) hx = LoadLibraryA("d3dx9_42.dll");
    pfn = hx ? (PFN_TexMem)GetProcAddress(hx, "D3DXCreateTextureFromFileInMemory") : NULL;
    if (!pfn) {
        LOGB("[BIG] FATAL: d3dx9_42!D3DXCreateTextureFromFileInMemory 不可用 -> 不替换");
        g_bigTexFail = 1;
        return;
    }
    g_ckpt = "BIG:2-create";
    pfx = hx ? (PFN_TexMemEx)GetProcAddress(hx, "D3DXCreateTextureFromFileInMemoryEx") : NULL;
    if (pfx) {
        /* MipLevels = 1：不生成 mip 链。
         * 实测：4096x2048 + 13 级 mip（约 43MB）会让 Alt-Tab 后的 Reset 失败，
         * 游戏随即退出；DIAG（不建纹理）不退出，可确认是纹理侧的问题。 */
        hr = pfx((IDirect3DDevice9*)dev, g_atlasPng, (UINT)g_atlasPngLen,
                 0, 0, 1, 0, D3DFMT_UNKNOWN, D3DPOOL_MANAGED,
                 (DWORD)0xFFFFFFFFu, (DWORD)0xFFFFFFFFu, 0, NULL, NULL, &tex);
    } else {
        LOGB("[BIG] 无 Ex 接口，回退到默认 mip 链版本");
        hr = pfn((IDirect3DDevice9*)dev, g_atlasPng, (UINT)g_atlasPngLen, &tex);
    }
    if (hr != D3D_OK || !tex) {
        LOGB("[BIG] FATAL: D3DXCreateTextureFromFileInMemory hr=0x%08lX -> 不替换", (unsigned long)hr);
        g_bigTexFail = 1;
        return;
    }
    g_ckpt = "BIG:3-verify";
    ZeroMemory(&sd, sizeof(sd));
    if (tex->lpVtbl->GetLevelDesc(tex, 0, &sd) != D3D_OK) {
        LOGB("[BIG] FATAL: GetLevelDesc 失败 -> 不替换");
        tex->lpVtbl->Release(tex);
        g_bigTexFail = 1;
        return;
    }
    if (sd.Width != ATLAS_W || sd.Height != ATLAS_H) {
        LOGB("[BIG] FATAL: 图集尺寸 %ux%u != %dx%d -> 不替换",
             sd.Width, sd.Height, ATLAS_W, ATLAS_H);
        tex->lpVtbl->Release(tex);
        g_bigTexFail = 1;
        return;
    }
    if (sd.Format != FONT_FMT) {
        LOGB("[BIG] WARN: 大图集格式 %d != 字体格式 %d（继续）", (int)sd.Format, (int)FONT_FMT);
    }
    g_bigTex = tex;
    g_bigDev = dev;
    mod_of((DWORD)(size_t)tex, m, 64);
    LOGB("[BIG] 大图集就绪 tex=%p %ux%u fmt=%d pool=%d lv=%u (%s) — 替换已启用",
         (void*)tex, sd.Width, sd.Height, (int)sd.Format, (int)sd.Pool,
         tex->lpVtbl->GetLevelCount(tex), m);
#endif
}

/* ============================================================================
 * Hook: IDirect3D9::CreateDevice (vt16)
 * ==========================================================================*/
static long WINAPI Hook_CreateDevice(void* self, UINT adapter, D3DDEVTYPE type,
                                     HWND focus, DWORD flags,
                                     D3DPRESENT_PARAMETERS* pp, IDirect3DDevice9** outDev) {
    DevRec* r;
    long hr;
    static int logN = 0;
    void* slot16;
    g_ckpt = "CD:0-enter";
    r = NULL;
    slot16 = g_d3d9OrigVt ? g_d3d9OrigVt[IX_D3D9_CREATEDEVICE] : NULL;
    LOGB("[CDDBG] self=%p objvt=%p origVt=%p slot16=%p hook=%p",
         self, *(void***)self, (void*)g_d3d9OrigVt, slot16, (void*)Hook_CreateDevice);
    slot16 = Hook_CreateDevice;   /* icc: prevent tail-call optimization dropping frame */
    g_ckpt = "CD:1-enter";
    /* 原始函数 = 该 IDirect3D9 对象的 origVt[16] */
    hr = (g_d3d9OrigVt && g_d3d9OrigVt[IX_D3D9_CREATEDEVICE])
       ? ((long (WINAPI *)(void*, UINT, D3DDEVTYPE, HWND, DWORD,
                           D3DPRESENT_PARAMETERS*, IDirect3DDevice9**))
          g_d3d9OrigVt[IX_D3D9_CREATEDEVICE])(self, adapter, type, focus, flags, pp, outDev)
       : D3DERR_INVALIDCALL;
    g_ckpt = "CD:2-done";
    if (hr == D3D_OK && outDev && *outDev) {
        if (logN < 4) {
            logN++;
            LOGB("[CD] #%d adapter=%u type=%d flags=0x%08lX hr=0x%08lX dev=%p",
                 logN, adapter, (int)type, (unsigned long)flags, (unsigned long)hr, (void*)*outDev);
            if (pp) {
                LOGB("[CD]   pp: %ux%u fmt=%d bb=%d wnd=%d vsync=%d",
                     pp->BackBufferWidth, pp->BackBufferHeight, (int)pp->BackBufferFormat,
                     (int)pp->BackBufferCount, pp->Windowed ? 1 : 0,
                     (pp->PresentationInterval == D3DPRESENT_INTERVAL_ONE) ? 1 : 0);
            }
        }
        g_ckpt = "CD:3-attach";
        attach_dev(*outDev);
        /* 设备能力诊断: 最大纹理尺寸（4096x2048 必须放得下） */
        {
            static D3DCAPS9 caps;   /* ~3KB 静态缓冲, 不放栈上 */
            DevRec* dr = dev_find(*outDev);
            if (dr && dr->origVt[IX_DEV_GETDEVICECAPS]) {
                HRESULT ch = ((HRESULT (WINAPI *)(void*, D3DCAPS9*))dr->origVt[IX_DEV_GETDEVICECAPS])(*outDev, &caps);
                if (ch == D3D_OK) {
                    LOGB("[CAPS] MaxTextureWidth=%lu MaxTextureHeight=%lu MaxTextureAspectRatio=%lu",
                         caps.MaxTextureWidth, caps.MaxTextureHeight, caps.MaxTextureAspectRatio);
                    if (caps.MaxTextureWidth < ATLAS_W || caps.MaxTextureHeight < ATLAS_H)
                        LOGB("[CAPS] WARN: GPU 最大纹理 < %dx%d, 大图集可能创建失败!", ATLAS_W, ATLAS_H);
                }
            }
        }
    } else if (logN < 4) {
        logN++;
        LOGB("[CD] FAILED adapter=%u type=%d flags=0x%08lX hr=0x%08lX",
             adapter, (int)type, (unsigned long)flags, (unsigned long)hr);
    }
    g_ckpt = "CD:9-ret";
    return hr;
}

/* ============================================================================
 * Hook: IDirect3DDevice9::CreateTexture (vt23) —— 字体图集识别
 * ==========================================================================*/
static long WINAPI Hook_CreateTexture(void* self, UINT w, UINT h, UINT levels,
                                      DWORD usage, D3DFORMAT fmt, D3DPOOL pool,
                                      IDirect3DTexture9** out, HANDLE* shared) {
    DevRec* r = dev_find(self);
    long hr;
    g_ckpt = "CT:1-enter";
    if (!r) return D3DERR_INVALIDCALL;   /* 不可能: 未挂载则不会被调用 */
    hr = ((long (WINAPI *)(void*, UINT, UINT, UINT, DWORD, D3DFORMAT, D3DPOOL,
                           IDirect3DTexture9**, HANDLE*))
          r->origVt[IX_DEV_CREATETEX])(self, w, h, levels, usage, fmt, pool, out, shared);
    g_ckpt = "CT:2-done";
    if (hr == D3D_OK && out && *out) {
        g_createN++;
        if (g_ctLogN < 300) {
            g_ctLogN++;
            LOGB("[CT] #%ld %ux%u lv=%u usage=0x%08lX fmt=%d pool=%d -> %p%s",
                 g_createN, w, h, levels, (unsigned long)usage, (int)fmt, (int)pool,
                 (void*)*out, (w == FONT_W && h == FONT_H && fmt == FONT_FMT) ? "  <<< 字体候选" : "");
        }
        if (w == FONT_W && h == FONT_H && fmt == FONT_FMT) {
            font_tex_add((void*)*out);
            /* v26：创建阶段【不做】身份识别 —— DEFAULT 池纹理不可 Lock，
             * 且此时内容尚未上传，哈希无意义（v24 崩坏的根因）。 */
            ensure_big_tex(self);       /* 生产版: 懒创建大图集 */
        }
    }
    return hr;
}

/* ============================================================================
 * Hook: IDirect3DDevice9::UpdateTexture (vt31) —— 诊断: 确认上传路径
 * ==========================================================================*/
static long WINAPI Hook_UpdateTexture(void* self, IDirect3DBaseTexture9* src,
                                      IDirect3DBaseTexture9* dst) {
    DevRec* r = dev_find(self);
    long hr;
    TexDesc ds, dd;
    g_ckpt = "UT:1-enter";
    if (!r) return D3DERR_INVALIDCALL;
    hr = ((long (WINAPI *)(void*, IDirect3DBaseTexture9*, IDirect3DBaseTexture9*))
          r->origVt[IX_DEV_UPDATETEX])(self, src, dst);
#if G3_DIAG
    if (g_stLogN < 300) {
        g_stLogN++;
        if (tex_desc((void*)src, &ds) && tex_desc((void*)dst, &dd))
            LOGB("[UT] src=%p %lux%lu fmt=%d pool=%d -> dst=%p %lux%lu fmt=%d pool=%d",
                 (void*)src, ds.w, ds.h, (int)ds.fmt, (int)ds.pool,
                 (void*)dst, dd.w, dd.h, (int)dd.fmt, (int)dd.pool);
        else
            LOGB("[UT] src=%p -> dst=%p (desc n/a)", (void*)src, (void*)dst);
    }
#else
    (void)ds; (void)dd;
    /* ★ v26 核心：只在 UT 的 src 上做内容哈希识别。
     * 二代实测：字体是 [UT] src(pool=2 SYSTEMMEM) -> dst(pool=0 DEFAULT) 上传的，
     * src 可 Lock，dst 不可 Lock —— 这就是 v24 撞墙的地方。 */
    g_utN++;
    if (src && !dev_lost(self, r)
        && tex_desc((void*)src, &ds) && ds.w == FONT_W && ds.h == FONT_H
        && ds.fmt == FONT_FMT) {
        unsigned int hh = 0;
        g_utFontN++;
        (void)hh;   /* v34：不再计算内容哈希 */
        if (hh && g_utxN < 60) {
            g_utxN++;
            LOGB("[UTX] f=%ld src=%p(pool=%d) dst=%p(pool=%d) %lux%lu fmt=%d hash=0x%08lX",
                 g_frames, (void*)src, (int)ds.pool, (void*)dst,
                 (void*)dst && tex_desc((void*)dst, &dd) ? (int)dd.pool : -1,
                 ds.w, ds.h, (int)ds.fmt, (unsigned long)hh);
        }
    }
#endif
    return hr;
}

/* ============================================================================
 * 点采样强制（消除字边缘的灰色模糊）
 *
 * 症状：中文笔画边缘有一层灰糊，不够锐利。
 * 成因：4096x2048 图集带 13 级 mip 链，加上引擎默认双线性 + mip 过滤，
 *       1:1 显示时也会被插值成一圈灰边。
 * 对策：只对「大图集所在的 stage」强制 MIN/MAG=POINT、MIP=NONE、MAXMIPLEVEL=0，
 *       绝不碰其它 stage —— 否则整个 3D 场景都会被像素化。
 * ==========================================================================*/
static void force_point_sampler(void* dev, DevRec* r, DWORD stage) {
    PFN_SETSAMP p;
    if (!r || !r->origVt[IX_DEV_SETSAMPLER]) return;
    p = (PFN_SETSAMP)r->origVt[IX_DEV_SETSAMPLER];
    p(dev, stage, D3DSAMP_MINFILTER,     D3DTEXF_POINT);
    p(dev, stage, D3DSAMP_MAGFILTER,     D3DTEXF_POINT);
    p(dev, stage, D3DSAMP_MIPFILTER,     D3DTEXF_NONE);
    p(dev, stage, D3DSAMP_MAXMIPLEVEL,   0);
    p(dev, stage, D3DSAMP_MIPMAPLODBIAS, 0);
}

/* ============================================================================
 * Hook: IDirect3DDevice9::SetSamplerState (vt69)
 *   引擎若在字体 stage 上设线性/mip 过滤，就地改写成点采样。
 * ==========================================================================*/
static long WINAPI Hook_SetSamplerState(void* self, DWORD stage,
                                        D3DSAMPLERSTATETYPE type, DWORD value) {
    DevRec* r = dev_find(self);
    DWORD v = value;
    if (!r) return D3DERR_INVALIDCALL;
    if (g_fontStage >= 0 && (int)stage == g_fontStage) {
        switch (type) {
        case D3DSAMP_MINFILTER:
        case D3DSAMP_MAGFILTER:     v = D3DTEXF_POINT; break;
        case D3DSAMP_MIPFILTER:     v = D3DTEXF_NONE;  break;
        case D3DSAMP_MAXMIPLEVEL:   v = 0;             break;
        case D3DSAMP_MIPMAPLODBIAS: v = 0;             break;
        default: break;
        }
        if (v != value) {
            g_sampN++;
            if (g_sampLogN < 12) {
                g_sampLogN++;
                LOGB("[SAMP#%ld] stage=%lu type=%d %lu -> %lu (已强制点采样)",
                     g_sampN, (unsigned long)stage, (int)type,
                     (unsigned long)value, (unsigned long)v);
            }
        }
    }
    return ((PFN_SETSAMP)r->origVt[IX_DEV_SETSAMPLER])(self, stage, type, v);
}

/* ============================================================================
 * Hook: IDirect3DDevice9::SetTexture (vt65) —— 核心: 字体图集 -> 大图集
 * ==========================================================================*/
static long WINAPI Hook_SetTexture(void* self, DWORD stage, IDirect3DBaseTexture9* tex) {
    void* ra = __builtin_return_address(0);   /* 调用者返回地址（必须最顶捕获） */
    DevRec* r = dev_find(self);
    TexDesc d;
    g_ckpt = "ST:1-enter";
    if (!r) return D3DERR_INVALIDCALL;
    /* 设备丢失守卫：DEVICELOST 期间原样透传，绝不做替换/解绑/heal */
    if (dev_lost(self, r))
        return ((long (WINAPI *)(void*, DWORD, IDirect3DBaseTexture9*))
                r->origVt[IX_DEV_SETTEXTURE])(self, stage, tex);
    if (tex) {
        g_bindN++;
        /* ★ v35：判定回到 v21；仅记录 512x256 出现在哪个 stage */
        int fontHit = is_font_tex((void*)tex);
        if (fontHit) {
            TexDesc dv;
            if (!tex_desc_direct((void*)tex, &dv)
                || dv.w != FONT_W || dv.h != FONT_H || dv.fmt != FONT_FMT) {
                fontHit = 0;
                if (g_staleN < 12) {
                    g_staleN++;
                    LOGB("[STALE] f=%ld tex=%p registry-hit but dims mismatch -> pointer reused, skip", g_frames, (void*)tex);
                }
            }
        }
        if (!fontHit && (int)stage == 0) g_prev0 = (void*)tex;
        {
            TexDesc dt;
            if (tex_desc((void*)tex, &dt)
                && dt.w == FONT_W && dt.h == FONT_H && dt.fmt == FONT_FMT) {
                int i, dup = 0;
                for (i = 0; i < g_tsN; i++)
                    if (g_ts[i].stage == stage && g_ts[i].tex == (void*)tex) { dup = 1; break; }
                if (!dup) {
                    if (g_tsN < TS_MAX) {
                        g_ts[g_tsN].stage = stage; g_ts[g_tsN].tex = (void*)tex; g_tsN++;
                        LOGB("[TEX512] #%d stage=%lu tex=%p %lux%lu fmt=%d fh=%d",
                             g_tsN, (unsigned long)stage, (void*)tex,
                             dt.w, dt.h, (int)dt.fmt, fontHit);
                    } else {
                        g_tsSup++;
                    }
                }
            }
        }
        if (fontHit) {
            g_fontBindN++;
            g_ckpt = "ST:2-font";
#if !G3_DIAG
            /* Reset 后大图集已被释放，这里按需重建（自愈，绝不依赖旧指针） */
            if (!g_bigTex && !g_bigTexFail) ensure_big_tex(self);
#endif
#if G3_DIAG
            if (g_stLogN < 300 && tex_desc((void*)tex, &d)) {
                g_stLogN++;
                LOGB("[ST] stage=%lu tex=%p %lux%lu fmt=%d pool=%d lv=%lu  <<< FONT bind#%ld",
                     (unsigned long)stage, (void*)tex, d.w, d.h, (int)d.fmt, (int)d.pool,
                     (unsigned long)d.lv, g_fontBindN);
            }
#else
            if (g_bigTex) {
                g_swapN++;
                g_identHitN++;
                /* 记住"原版字体纹理", 供 3D 绘制前临时顶回 stage0（防图集泄露） */
                g_bigSrc = (IDirect3DTexture9*)tex;
                if ((int)stage == 0 && !g_bigAt0 && g_bkLogN < 20) {
                    g_bkLogN++;
                    LOGB("[BOOK] stage0 换成大图集 -> 账本置 1 f=%ld", g_frames);
                }
                g_bigAt0 = ((int)stage == 0);   /* 账本: stage0 现在绑的是大图集 */

                if (g_swapLogN < 120) {
                    g_swapLogN++;
                    LOGB("[SWAP#%ld] stage=%lu font=%p -> big=%p f=%ld ra=exe+%#lx",
                         g_swapN, (unsigned long)stage, (void*)tex, (void*)g_bigTex,
                         g_frames, (unsigned long)((char*)ra - (char*)g_exeBase));
                }
                g_ckpt = "ST:3-swap";
                tex = (IDirect3DBaseTexture9*)g_bigTex;
            } else if (g_swapN == 0 && g_fontBindN == 1) {
                LOGB("[ST] 字体图集已绑定但大图集未就绪 -> 本次不替换（渲染将错乱=预期 FAIL）");
            }
#endif
        }
        else if ((int)stage == 0 && g_bigAt0) g_bigAt0 = 0;   /* 非字体纹理绑定 stage0 */
#if G3_DIAG
        if (g_stLogN < 300 && tex_desc((void*)tex, &d)) {
            /* 非字体纹理: 记录前 300 个不同尺寸的绑定, 供判据复盘 */
            static unsigned int seen[64]; static int seenN = 0;
            unsigned int key = (d.w << 16) | d.h;
            int i, dup = 0;
            for (i = 0; i < seenN; i++) if (seen[i] == key) { dup = 1; break; }
            if (!dup && seenN < 64) {
                seen[seenN++] = key;
                g_stLogN++;
                LOGB("[ST] stage=%lu tex=%p %lux%lu fmt=%d pool=%d",
                     (unsigned long)stage, (void*)tex, d.w, d.h, (int)d.fmt, (int)d.pool);
            }
        }
#endif
        /* 非字体纹理的账本清零已由上面的 not_font_tex: 标签统一处理（此处若再写 else 会在
         * 生产版悬空，因为 #if G3_DIAG 块被编译裁掉）。 */
    }
    /* 点采样：跟踪大图集所在 stage，首次进入时主动设一次（引擎可能从不调 SetSamplerState） */
#if FORCE_POINT_SAMPLER
    if (tex && (void*)tex == (void*)g_bigTex) {
        if (g_fontStage != (int)stage) {
            g_fontStage = (int)stage;
            force_point_sampler(self, r, stage);
            LOGB("[SAMP] 字体 stage=%lu 已强制点采样（MIN/MAG=POINT, MIP=NONE, MAXMIP=0）",
                 (unsigned long)stage);
        }
    } else if ((int)stage == g_fontStage) {
        g_fontStage = -1;                     /* 该 stage 换成别的贴图了，停止强制 */
    }
#endif
    g_ckpt = "ST:9-callOrig";
    return ((long (WINAPI *)(void*, DWORD, IDirect3DBaseTexture9*))
            r->origVt[IX_DEV_SETTEXTURE])(self, stage, tex);
}

/* ============================================================================
 * 图集泄露修复: DrawPrimitive (vt81) / DrawIndexedPrimitive (vt82)
 *
 *   症状(实机 2026-10-18): UI 与字幕完美, 但墙壁/地板/人物模型上出现巨大
 *   横向半透明条纹 —— 我方 4096x2048 中文字库被当成普通贴图糊在 3D 物体上。
 *
 *   成因: 游戏画完 UI 文字后, 画 3D 场景时没有重新绑定 stage0, 该槽位仍然是
 *   被我们替换过的大图集。原版 512x256 字库 98% 是透明像素, 所以原版看不到
 *   泄露; 我们的大图集塞满字形, 泄露就变得极其醒目。
 *   实测数据: fontBinds=198196 / binds=6512858 —— 字体纹理被反复绑定,
 *   每次都被换成大图集, 3D 场景自然继承了这个绑定。
 *
 *   对策(实测定标, 非猜测): 在绘制入口前, 若 stage0 是大图集 **且** 本次是
 *   3D 几何, 才用原版字体纹理顶回 stage0, 画完立刻换回大图集。
 *   "是不是 3D" 由 atlas_unbind() 的两级门槛判定(FVF XYZRHW / ZENABLE)。
 *
 *   【v3 修正】v2 曾无条件拦截, 结果 UI 文字整体消失 —— 实机证明该引擎连 2D
 *   文字也走 DrawPrimitive(vt81), 且 dip=up=0。故必须加渲染状态门槛。
 * ==========================================================================*/
typedef HRESULT (WINAPI *PFN_GT)(void*, DWORD, IDirect3DBaseTexture9**);
typedef HRESULT (WINAPI *PFN_ST)(void*, DWORD, IDirect3DBaseTexture9*);
typedef HRESULT (WINAPI *PFN_DP)(void*, D3DPRIMITIVETYPE, UINT, UINT);
typedef HRESULT (WINAPI *PFN_DIP)(void*, D3DPRIMITIVETYPE, INT, UINT, UINT, UINT, UINT);
typedef HRESULT (WINAPI *PFN_DPU)(void*, D3DPRIMITIVETYPE, UINT, const void*, UINT);
typedef HRESULT (WINAPI *PFN_DIPU)(void*, D3DPRIMITIVETYPE, UINT, UINT,
                                   const void*, D3DFORMAT, const void*, UINT);
typedef HRESULT (WINAPI *PFN_GRS)(void*, D3DRENDERSTATETYPE, DWORD*);
typedef HRESULT (WINAPI *PFN_GTF)(void*, D3DTRANSFORMSTATETYPE, D3DMATRIX*);
typedef HRESULT (WINAPI *PFN_GFVF)(void*, DWORD*);

/* ---------------------------------------------------------------------------
 * 门槛模式（环境变量 O2_LEAK_GATE 可在运行期切换, 不必重编 DLL）
 *   0 = 关闭泄露拦截（文字保证正常, 条纹回来）        —— 应急
 *   1 = 只看 FVF 是否 XYZRHW
 *   2 = FVF + 正交投影 + ZENABLE                     —— 【默认】
 *   3 = 同 2, 另要求 ZWRITE=TRUE 且 ALPHABLEND=FALSE  —— 最严
 *
 * 判定序列（任一命中即"这是 2D", 保留大图集; 全部落空才认定 3D 并回退）:
 *   1) FVF 含 D3DFVF_XYZRHW     -> 屏幕空间顶点, 一定是文字/UI
 *   2) 投影矩阵是正交 (_34≈0, _44≠0) -> UI 常用的正交投影
 *   3) ZENABLE != TRUE          -> 没开深度测试, 不是 3D 场景
 * ------------------------------------------------------------------------- */
static int gate_mode(void) {
    static int m = -1;
    if (m < 0) {
        char b[16];
        DWORD n = GetEnvironmentVariableA("O2_LEAK_GATE", b, sizeof(b));
        m = -1;
        if (n > 0 && b[0] >= '0' && b[0] <= '3' && (n == 1 || b[1] == 0))
            m = b[0] - '0';
        /* 其次读 DLL 同目录的 g3_gate.txt（只用首个 0-3 字符, 方便随手应急切换） */
        if (m < 0 && g_logPath[0]) {
            char p[MAX_PATH];
            char* q;
            lstrcpynA(p, g_logPath, MAX_PATH - 16);
            q = strrchr(p, '\\');
            if (q) {
                HANDLE h;
                lstrcpyA(q + 1, "g3_gate.txt");
                h = CreateFileA(p, GENERIC_READ, FILE_SHARE_READ | FILE_SHARE_WRITE,
                                NULL, OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, NULL);
                if (h != INVALID_HANDLE_VALUE) {
                    char fb[8];
                    DWORD got = 0;
                    if (ReadFile(h, fb, 8, &got, NULL) && got > 0
                        && fb[0] >= '0' && fb[0] <= '3')
                        m = fb[0] - '0';
                    CloseHandle(h);
                }
            }
        }
        if (m < 0) m = 2;
        LOGB("[CFG] 图集泄露门槛模式 = %d (可用 O2_LEAK_GATE 或 g3_gate.txt 改 0/1/2/3)", m);
    }
    return m;
}

/* 投影矩阵是否正交（透视: _34=1,_44=0 ; 正交: _34=0,_44=1） */
static int proj_is_ortho(void* dev, DevRec* r) {
    D3DMATRIX m;
    if (!r->origVt[IX_DEV_GETTRANSFORM]) return 0;
    ZeroMemory(&m, sizeof(m));
    if (((PFN_GTF)r->origVt[IX_DEV_GETTRANSFORM])(dev, D3DTS_PROJECTION, &m) != D3D_OK)
        return 0;
    if (m._34 > -0.001f && m._34 < 0.001f)
        if (m._44 < -0.001f || m._44 > 0.001f) return 1;
    return 0;
}

/* 返回: 1 = 已顶回原版字体纹理(调用方画完须换回); 0 = 未改动 */
static int atlas_unbind(void* dev, DevRec* r, UINT primCount) {
    DWORD fvf = 0, z = 0xFFFFFFFF, zw = 0, ab = 0;
    int mode = gate_mode();
#if !DRAW_UNBIND
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
}

static void atlas_rebind(void* dev, DevRec* r) {
    ((PFN_ST)r->origVt[IX_DEV_SETTEXTURE])(dev, 0, (IDirect3DBaseTexture9*)g_bigTex);
}

/* vt81: DrawPrimitive */
static long WINAPI Hook_DrawPrimitive(void* self, D3DPRIMITIVETYPE pt,
                                      UINT startVtx, UINT primCount) {
    /* ★ v41：只观测"上一次绑定之后第一个绘制是什么" */
    DevRec* r = dev_find(self);
    if (!r) return D3DERR_INVALIDCALL;
    if (dev_lost(self, r))
        return ((PFN_DP)r->origVt[IX_DEV_DRAWPRIM])(self, pt, startVtx, primCount);
    return ((PFN_DP)r->origVt[IX_DEV_DRAWPRIM])(self, pt, startVtx, primCount);
}

/* vt82: DrawIndexedPrimitive —— 3D 墙壁/地板/人物的主绘制路径 */
static long WINAPI Hook_DrawIndexedPrimitive(void* self, D3DPRIMITIVETYPE pt,
                                             INT baseVtx, UINT minIdx, UINT numVtx,
                                             UINT startIdx, UINT primCount) {
    /* ★ v41：观测绑定点用途 */
    DevRec* r = dev_find(self);
    if (!r) return D3DERR_INVALIDCALL;
    /* ★ v37：每帧抓一次「3D 绘制时 stage0 的真实材质纹理」（仅 at0==0 时） */
    rt_init_once();
    if (!g_bigAt0 && g_last3DFrame != g_frames && r->origVt[IX_DEV_GETTEXTURE]) {
        IDirect3DBaseTexture9* cur = NULL;
        g_last3DFrame = g_frames;
        ((PFN_GT)r->origVt[IX_DEV_GETTEXTURE])(self, 0, &cur);
        if (cur) { g_last3D0 = (void*)cur; cur->lpVtbl->Release(cur); }
    }
#if DIP_RESTORE
    if (g_bigAt0 && !dev_lost(self, r) && r->origVt[IX_DEV_SETTEXTURE]) {
        IDirect3DBaseTexture9* tgt = NULL;
        /* ★ v43：始终还原成我们刚才替换掉的那张（g_bigSrc）——
         *   对文字绑定它是字体；对书架/光照绑定它就是那张材质本身 */
        tgt = (IDirect3DBaseTexture9*)g_bigSrc;
        /* target 0 -> NULL */
        ((PFN_ST)r->origVt[IX_DEV_SETTEXTURE])(self, 0, tgt);
        if (g_dipRstN < 20) {
            g_dipRstN++;
            LOGB("[DIP-RST] f=%ld prim=%u tgt=%d -> %p (big=%p prev0=%p last3D=%p before=%p)",
                 g_frames, primCount, g_restoreTarget, (void*)tgt,
                 (void*)g_bigTex, g_prev0, g_last3D0, g_beforeSwap);
        }
        g_bigAt0 = 0;
    }
#endif
    if (dev_lost(self, r))
        return ((PFN_DIP)r->origVt[IX_DEV_DRAWIDXPRIM])(self, pt, baseVtx, minIdx, numVtx,
                                                        startIdx, primCount);
    return ((PFN_DIP)r->origVt[IX_DEV_DRAWIDXPRIM])(self, pt, baseVtx, minIdx, numVtx,
                                                    startIdx, primCount);
}

/* vt83: DrawPrimitiveUP —— 2D 文字/精灵路径, 只观测不拦截 */
static long WINAPI Hook_DrawPrimitiveUP(void* self, D3DPRIMITIVETYPE pt,
                                        UINT primCount, const void* vtxData,
                                        UINT stride) {
    DevRec* r = dev_find(self);
    if (!r) return D3DERR_INVALIDCALL;
    /* 设备丢失守卫：丢失期绝不调任何 D3D9 API（一代铁律） */
    if (dev_lost(self, r))
        return ((PFN_DPU)r->origVt[IX_DEV_DRAWPRIMUP])(self, pt, primCount, vtxData, stride);
    g_upN++;
    if (g_bigAt0) g_upAtlasN++;        /* 纯观测，不做任何干预 */
    return ((PFN_DPU)r->origVt[IX_DEV_DRAWPRIMUP])(self, pt, primCount, vtxData, stride);
}

/* vt84: DrawIndexedPrimitiveUP —— 只观测不拦截 */
static long WINAPI Hook_DrawIndexedPrimitiveUP(void* self, D3DPRIMITIVETYPE pt,
                                               UINT minVtxIdx, UINT numVtx,
                                               const void* idxData, D3DFORMAT idxFmt,
                                               const void* vtxData, UINT stride) {
    DevRec* r = dev_find(self);
    if (!r) return D3DERR_INVALIDCALL;
    if (dev_lost(self, r))
        return ((PFN_DIPU)r->origVt[IX_DEV_DRAWIDXPRIMUP])(self, pt, minVtxIdx, numVtx,
                                                           idxData, idxFmt, vtxData, stride);
    g_upiN++;
    if (g_bigAt0) g_upiAtlasN++;
    return ((PFN_DIPU)r->origVt[IX_DEV_DRAWIDXPRIMUP])(self, pt, minVtxIdx, numVtx,
                                                       idxData, idxFmt, vtxData, stride);
}

/* ============================================================================
 * Hook: IDirect3DDevice9::Reset (vt16)
 *   MANAGED 池大纹理跨 Reset 自动存活; 仅清理统计 + 重挂 vtable
 * ==========================================================================*/
static long WINAPI Hook_Reset(void* self, D3DPRESENT_PARAMETERS* pp) {
    if (!HOOK_RESET) { (void)self; (void)pp; }   /* 未启用时仍保留实现，便于随时打开 */
    DevRec* r = dev_find(self);
    long hr;
    g_ckpt = "RST:1-enter";
    if (!r) return D3DERR_INVALIDCALL;
    g_resetN++;
    if (g_resetN <= 8) {
        LOGB("[RST] #%ld pp=%p%s%s", g_resetN, (void*)pp,
             pp ? " " : "", pp && pp->Windowed ? "windowed" : "fullscreen");
        LOGB("[RSTDBG] self=%p dev=%p origVt=%p cloneVt=%p orig[16]=%p hook=%p",
             (void*)self, (void*)r->dev, (void*)r->origVt, (void*)r->cloneVt,
             r->origVt ? (void*)r->origVt[IX_DEV_RESET] : NULL, (void*)Hook_Reset);
    }
    /* 【重要】这里**绝不 Release g_bigTex**。
     * 原因（实测崩溃）：D3D9 中已被 SetTexture 绑定的纹理，若在 Reset 前被释放到
     * 引用计数 0，设备内部会留下悬空引用；紧随其后的 Reset 一旦失败（例如
     * D3DERR_DEVICENOTRESET 0x8876086C），游戏再动鼠标/重绘就立刻崩溃。
     * g_bigTex 是 D3DPOOL_MANAGED，本身跨 Reset 存活，保留它才是安全的。
     * 只作废"指向游戏资源"的引用（g_bigSrc 在 Reset 后必悬空）。 */
    g_bigSrc = NULL;
    g_fontStage = -1;
    if (g_resetN <= 8)
        LOGB("[RST] #%ld 作废 g_bigSrc/g_fontStage；保留 g_bigTex=%p（MANAGED 跨 Reset 存活）",
             g_resetN, (void*)g_bigTex);

    /* ★★★ c47 防线（一代二分实验确证，本项目的真正根因）★★★
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
    g_ckpt = "RST:2-done";
    {
        const char* why = "";
        if (hr == 0x88760868UL)      why = " [D3DERR_DEVICELOST 设备丢失]";
        else if (hr == 0x88760869UL) why = " [D3DERR_DEVICENOTRESET 尚未复位]";
        else if (hr == 0x8876086CUL) why = " [D3DERR_INVALIDCALL 参数/状态非法]";
        else if (hr == 0x8876017CUL) why = " [D3DERR_OUTOFVIDEOMEMORY]";
        if (g_resetHrLogN < 40 || hr != 0) {
            g_resetHrLogN++;
            LOGB("[RST] #%ld hr=0x%08lX%s (大纹理 %s, 字体载体数=%d)",
                 g_resetN, (unsigned long)hr, why,
                 g_bigTex ? "保留" : "未创建", g_fontCarrierN);
        }
    }

    if (hr != D3D_OK) {
        /* 重置失败：设备处于丢失/待重置态。此时**不动 vtable、不碰任何资源**，
         * 把 hr 原样交还游戏，由它按自己的节奏重试或重建。 */
        LOGB("[RST] #%ld 重置未成功(0x%08lX)，跳过 heal 与资源操作，等待游戏重试",
             g_resetN, (unsigned long)hr);
        return hr;
    }

    /* 重置成功：此时设备健康，可以安全校验/丢弃大图集 */
    if (g_bigTex) {
        D3DSURFACE_DESC sd;
        if (g_bigTex->lpVtbl->GetLevelDesc(g_bigTex, 0, &sd) != D3D_OK) {
            LOGB("[RST] #%ld 大图集已失效，丢弃并等待惰性重建", g_resetN);
            g_bigTex->lpVtbl->Release(g_bigTex);
            g_bigTex = NULL;
            g_bigDev = NULL;
        }
    }
    g_bigTexFail = 0;         /* 允许重试创建 */
    /* Reset 后校验挂载（设备指针不变, vtable 指针理论上也不变; heal 保险） */
    if (*(void***)self != r->cloneVt) {
        *(void***)self = r->cloneVt;
        g_healN++;
        LOGB("[HEAL] Reset 后重新指向 clone");
    }
    return hr;
}

/* ============================================================================
 * Hook: IDirect3DDevice9::Present (vt17) —— 帧计数 + heal + 周期摘要
 * ==========================================================================*/
static long WINAPI Hook_Present(void* self, const RECT* s, const RECT* d,
                                HWND h, const RGNDATA* g) {
    DevRec* r = dev_find(self);
    long hr;
    g_ckpt = "PRESENT:1-enter";
    g_frames++;
    if (!r) return D3D_OK;
    /* 设备丢失守卫：DEVICELOST 期间原样透传（连 heal 都不做） */
    if (dev_lost(self, r))
        return ((long (WINAPI *)(void*, const RECT*, const RECT*, HWND, const RGNDATA*))
                r->origVt[IX_DEV_PRESENT])(self, s, d, h, g);
    if (*(void***)self != r->cloneVt) {
        *(void***)self = r->cloneVt;
        g_healN++;
        LOGB("[HEAL] Present 发现 vtable 被还原, 重新指向 clone (f=%ld)", g_frames);
    }
    if ((g_frames % 250) == 0) {
        LOGB("[STAT] f=%ld binds=%ld fontBinds=%ld swaps=%ld creates=%ld "
             "dp=%ld dpRev=%ld dip=%ld dipRev=%ld "
             "atlas=%ld skipRhw=%ld skipOrtho=%ld skipZoff=%ld up=%ld samp=%ld rst=%ld ut=%ld utf=%ld hok=%ld hfail=%ld ident=%ld bad=%ld bskip=%ld stale=%ld ts=%ld tssup=%ld dl=%ld dlsup=%ld rt=%d rst=%ld",
             g_frames, g_bindN, g_fontBindN, g_swapN, g_createN,
             g_dpN, g_dpRevN, g_dipN, g_dipRevN,
             g_atlasBoundN, g_skipRhwN, g_skipOrthoN, g_skipZoffN, g_upN, g_sampN,
             g_frameRestoreN, g_utN, g_utFontN, g_hashOKN, g_hashFailN, g_identHitN,
             (long)g_badTexN, g_badSkipN, g_staleN,
             (long)g_badTexN, g_badSkipN,
             (long)g_tsN, g_tsSup, g_dipLeakN, g_dipLeakSup,
             g_restoreTarget, g_dipRstN);
    }
    /* 帧末还原：把 stage0 还回游戏原本的字体纹理，
     * 别让引擎在帧边界/Reset 前看到我们的大图集（c47 的日常版）。 */
    if (PRESENT_RESTORE && g_bigAt0 && g_bigTex && g_bigSrc && !dev_lost(self, r)
        && r->origVt[IX_DEV_SETTEXTURE]) {
        if (g_rstrLogN < 100) {
            g_rstrLogN++;
            LOGB("[RSTR] f=%ld stage0 大图集 -> 游戏字体 %p（帧末还原）", g_frames, (void*)g_bigSrc);
        }
        ((PFN_ST)r->origVt[IX_DEV_SETTEXTURE])(self, 0,
                                               (IDirect3DBaseTexture9*)g_bigSrc);
        g_bigAt0 = 0;
        g_frameRestoreN++;
    }
    g_ckpt = "PRESENT:2-callOrig";
    hr = ((long (WINAPI *)(void*, const RECT*, const RECT*, HWND, const RGNDATA*))
          r->origVt[IX_DEV_PRESENT])(self, s, d, h, g);
    g_ckpt = "PRESENT:3-done";
    if (hr != D3D_OK) {
        /* 设备丢失 / 需要重置：立刻作废指向游戏资源的引用，
         * 这样即使不拦 Reset 也不会用到悬空指针（下一个 Present 前必已失效）。 */
        if (g_bigSrc || g_fontStage >= 0) {
            g_bigSrc = NULL;
            g_fontStage = -1;
            if (g_devLostLogN < 8) {
                g_devLostLogN++;
                LOGB("[PRESENT] hr=0x%08lX 设备异常，已作废 g_bigSrc/g_fontStage",
                     (unsigned long)hr);
            }
        }
    }
    return hr;
}

/* ============================================================================
 * Hook: IDirect3DDevice9::GetDirect3D (vt6)
 *   设备回查得到的 IDirect3D9* 是真实对象（其 vtable 未被克隆）——
 *   若游戏经此路径二次 CreateDevice 会绕过挂载, 在此补挂。
 * ==========================================================================*/
static long WINAPI Hook_GetDirect3D(void* self, IDirect3D9** pp) {
    DevRec* r = dev_find(self);
    long hr;
    g_ckpt = "GD3:1-enter";
    if (!r) return D3DERR_INVALIDCALL;
    hr = ((long (WINAPI *)(void*, IDirect3D9**))
          r->origVt[IX_DEV_GETDIRECT3D])(self, pp);
    if (hr == D3D_OK && pp && *pp) attach_d3d9(*pp);
    return hr;
}

/* ============================================================================
 * 崩溃检查点（Gen-1 同款）: 记录最后到达位置, 便于闪退定位
 * ==========================================================================*/
static LONG WINAPI ExceptionFilter(EXCEPTION_POINTERS* ep) {
    char b[512];
    wsprintfA(b, "[FATAL] 未处理异常 code=0x%08lX addr=%p ckpt=%s",
              (unsigned long)ep->ExceptionRecord->ExceptionCode,
              ep->ExceptionRecord->ExceptionAddress, g_ckpt);
    LOG(b);
    return EXCEPTION_CONTINUE_SEARCH;   /* 交还原有崩溃处理（WER/调试器） */
}

/* ============================================================================
 * 导出入口: Direct3DCreate9（经 naked 桩 Proxy_Direct3DCreate9 跳入）
 * ==========================================================================*/
static IDirect3D9* WINAPI impl_Direct3DCreate9(UINT sdk) {
    IDirect3D9* obj;
    char m[64];
    g_ckpt = "D3DC9:1-call";
    obj = g_ptr_Direct3DCreate9
        ? ((IDirect3D9* (WINAPI *)(UINT))g_ptr_Direct3DCreate9)(sdk) : NULL;
    g_ckpt = "D3DC9:2-attach";
    if (obj) {
        mod_of((DWORD)(size_t)*(void***)obj, m, 64);
        LOGB("[D3DC9] sdk=%u obj=%p vt=%p (%s)", sdk, (void*)obj,
             (void*)*(void***)obj, m);
        attach_d3d9(obj);
    } else {
        LOGB("[D3DC9] FATAL: 真实 Direct3DCreate9 返回 NULL (sdk=%u)", sdk);
    }
    g_ckpt = "D3DC9:9-ret";
    return obj;
}

/* ============================================================================
 * DllMain
 * ==========================================================================*/
static HINSTANCE g_hSelf = NULL;

BOOL WINAPI DllMain(HINSTANCE h, DWORD reason, LPVOID r) {
    (void)r;
    if (reason == DLL_PROCESS_ATTACH) {
        g_exeBase = (void*)GetModuleHandleA(NULL);
        int resolved;
        DisableThreadLibraryCalls(h);
        g_hSelf = h;
        /* 日志路径 = dll 同目录 */
        GetModuleFileNameA(h, g_logPath, MAX_PATH);
        {
            char* p = strrchr(g_logPath, '\\');
            if (p) p[1] = 0;
            lstrcatA(g_logPath, "d3d9proxy.log");
        }
        InitializeCriticalSection(&g_logCS);
        g_logCSInit = 1;
        LOG("\r\n================ d3d9 proxy (Obscure II Gate 3) ================\r\n");
        resolved = resolve_real();
        g_ptr_impl_Direct3DCreate9 = (void*)impl_Direct3DCreate9;
        SetUnhandledExceptionFilter(ExceptionFilter);
#if G3_DIAG
        LOG("[INIT] 模式 = DIAG（只记录, 不替换, 不建纹理）\r\n");
#else
        LOG("[INIT] 模式 = PRODUCTION（图集替换启用, 4096x2048）\r\n");
#endif
        LOGB("[INIT] pid=%lu real d3d9 导出解析=%d/17", (unsigned long)GetCurrentProcessId(), resolved);
        LOGB("[INIT] 图集常量: %dx%d, 字体判据 %dx%d fmt=%d",
             ATLAS_W, ATLAS_H, FONT_W, FONT_H, (int)FONT_FMT);
    } else if (reason == DLL_PROCESS_DETACH) {
        /* 绝对禁止在 DllMain 里做实质清理（持加载器锁）。Gen-1 教训同源:
         * 在 detach 里 Release D3D 资源 -> D3D 内部可能触发 DLL 加载/卸载,
         * 在加载器锁下死锁或直接崩。实测表现: selftest32 的 stdout 全部丢失
         * (进程在 FreeLibrary 之后未能正常走到 exit flush)。
         * 对策: detach 只留日志; 显存资源由进程退出时的内核回收负责。 */
        {
            const char* prev = g_ckpt;
            g_ckpt = "DETACH";
            LOGB("[INIT] detach: 上一个检查点=%s  f=%ld  bigTex=%p",
                 prev ? prev : "?", g_frames, (void*)g_bigTex);
        }
#if !G3_DIAG
        if (g_bigTex) {
            LOGB("[INIT] detach: bigTex=%p 交由进程退出回收（不在加载器锁内 Release）",
                 (void*)g_bigTex);
            g_bigTex = NULL;
        }
#endif
        LOG("[INIT] detach\r\n");
        if (g_logCSInit) { DeleteCriticalSection(&g_logCS); g_logCSInit = 0; }
    }
    return TRUE;
}

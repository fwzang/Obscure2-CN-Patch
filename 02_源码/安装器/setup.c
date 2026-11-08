// setup.c — Obscure II 简体中文汉化补丁 V1.04 安装器
// 原生 Win32，无第三方依赖。
// 载荷：[setup.exe][datapack.delta][d3d9.dll][datapack_a.delta][d3d9_a.dll][dinput8.dll][main.patch][Footer]
//   方案 B（默认）：活楷体 + 4x 超采样，datapack.delta → full18，d3d9.dll = v49
//   方案 A：寒蝉端黑体，datapack_a.delta → fullA，d3d9_a.dll = 黑体图集版
// 数据包采用「差分重建」：安装包内只带两套 0.6MB 级差异，安装时用本机原版
// datapack.hvp 重建中文数据包，体积从 887MB 降到 ~3MB。
#define WIN32_LEAN_AND_MEAN
#define _CRT_SECURE_NO_WARNINGS
#include <windows.h>
#include <windowsx.h>
#include <commctrl.h>
#include <shlobj.h>
#include <stdio.h>
#include <stdarg.h>
#include <string.h>

#pragma comment(lib, "comctl32.lib")

/* ---------- 载荷尾部清单 ---------- */
#pragma pack(push, 1)
typedef struct {
    char           name[32];
    unsigned long long off;    /* 绝对文件偏移 */
    unsigned long long size;
} Ent;
typedef struct {
    char           magic[8];   /* "O2SETUP1" */
    unsigned int   ver;
    unsigned int   n;
    Ent            ent[8];
} Footer;

/* 差分补丁头（40 字节） */
typedef struct {
    char           magic[8];   /* "O2DLT1\0\0" */
    unsigned int   ver;
    unsigned int   nops;
    unsigned long long srcSize;
    unsigned long long dstSize;
    unsigned int   srcCrc;
    unsigned int   dstCrc;
} DltHdr;
#pragma pack(pop)

#define ID_EDIT_INFO   1001
#define ID_EDIT_PATH   1002
#define ID_BTN_BROWSE  1003
#define ID_CHK_BACKUP  1004
#define ID_CHK_WS      1005
#define ID_BTN_INSTALL 1006
#define ID_BTN_RESTORE 1007
#define ID_BTN_EXIT    1008
#define ID_PROGRESS    1009
#define ID_STATUS      1010
#define ID_RADIO_A     1011
#define ID_RADIO_B     1012
#define ID_RADIO_SMART 1013   /* v87: 渲染模式 - 智能兼容（推荐） */
#define ID_RADIO_NATIVE 1014  /* v87: 渲染模式 - 强制原生 DX9 */

static HINSTANCE g_hInst;
static HWND g_hMain, g_hInfo, g_hPath, g_hChkBackup, g_hChkWS, g_hProg, g_hStatus;
static HWND g_hRadioA, g_hRadioB;
static HWND g_hRadioSmart, g_hRadioNative;   /* v87: 渲染模式 */
static int  g_nativeOnly = 0;                /* v87: 1 = 强制原生 DX9（写 o2_mode.txt=compat） */
static HFONT g_fTitle, g_fSub, g_fBody;
static HBRUSH g_bg, g_band, g_white;
static HPEN   g_line;
static Footer g_ft;
static int g_haveFt = 0;
static int g_s = 100;                 /* DPI 百分比 */
static unsigned int g_crcTab[256];

#define S(v) MulDiv((v), g_s, 100)

static const wchar_t* kTitle = L"Obscure II 简体中文汉化补丁";
static const wchar_t* kSub   = L"V1.04  ·  Steam 版 (AppID 254480)  ·  N 卡自动 D3D9On12";

#include "info_o2.h"

/* ---------- 工具 ---------- */
static void set_status(const wchar_t* s) { if (g_hStatus) SetWindowTextW(g_hStatus, s); }
static void set_prog(int pct) { if (g_hProg) SendMessageW(g_hProg, PBM_SETPOS, (WPARAM)pct, 0); }
static void pump(void) { MSG m; while (PeekMessageW(&m, NULL, 0, 0, PM_REMOVE)) { TranslateMessage(&m); DispatchMessageW(&m); } }

static int file_exists(const wchar_t* p) {
    DWORD a = GetFileAttributesW(p);
    return a != INVALID_FILE_ATTRIBUTES && !(a & FILE_ATTRIBUTE_DIRECTORY);
}

/* 诊断日志：%TEMP%\O2Setup.log（排障用，正常安装也会留一行摘要） */
static void logf(const wchar_t* fmt, ...) {
    wchar_t path[MAX_PATH], buf[1024];
    DWORD n = GetTempPathW(MAX_PATH, path);
    if (!n) return;
    lstrcatW(path, L"O2Setup.log");
    va_list ap; va_start(ap, fmt);
    wvsprintfW(buf, fmt, ap);
    va_end(ap);
    HANDLE h = CreateFileW(path, FILE_APPEND_DATA, FILE_SHARE_READ, NULL, OPEN_ALWAYS, FILE_ATTRIBUTE_NORMAL, NULL);
    if (h == INVALID_HANDLE_VALUE) return;
    SetFilePointer(h, 0, NULL, FILE_END);
    char u8[2048] = {0};
    int len = WideCharToMultiByte(CP_UTF8, 0, buf, -1, u8, sizeof(u8) - 1, NULL, NULL);
    DWORD put = 0;
    if (len > 1) WriteFile(h, u8, (DWORD)len - 1, &put, NULL);
    WriteFile(h, "\r\n", 2, &put, NULL);
    CloseHandle(h);
}

static void join(wchar_t* out, const wchar_t* dir, const wchar_t* name) {
    lstrcpyW(out, dir);
    size_t n = lstrlenW(out);
    if (n && out[n - 1] != L'\\') lstrcatW(out, L"\\");
    lstrcatW(out, name);
}

/* ---------- CRC32 ---------- */
static void crc_init(void) {
    for (unsigned int i = 0; i < 256; i++) {
        unsigned int c = i;
        for (int k = 0; k < 8; k++) c = (c & 1) ? (0xEDB88320u ^ (c >> 1)) : (c >> 1);
        g_crcTab[i] = c;
    }
}
static unsigned int crc_upd(unsigned int s, const BYTE* p, size_t n) {
    while (n--) s = g_crcTab[(s ^ *p++) & 0xFF] ^ (s >> 8);
    return s;
}

/* 计算文件 CRC32（顺带报告进度 0..100） */
static int crc_of_file(HANDLE h, unsigned int* out, int pctFrom, int pctTo) {
    LARGE_INTEGER z; GetFileSizeEx(h, &z);
    LARGE_INTEGER p; p.QuadPart = 0;
    SetFilePointerEx(h, p, NULL, FILE_BEGIN);
    static BYTE buf[1 << 20];
    unsigned int s = 0xFFFFFFFFu;
    unsigned long long done = 0, total = (unsigned long long)z.QuadPart;
    for (;;) {
        DWORD got = 0;
        if (!ReadFile(h, buf, sizeof(buf), &got, NULL) || !got) break;
        s = crc_upd(s, buf, got);
        done += got;
        if (total) set_prog(pctFrom + (int)((pctTo - pctFrom) * (double)done / (double)total));
        pump();
    }
    SetFilePointerEx(h, p, NULL, FILE_BEGIN);
    *out = s ^ 0xFFFFFFFFu;
    return 1;
}

/* 从注册表 / 常见路径猜 Steam 库 */
static int guess_game_dir(wchar_t* out, DWORD cap) {
    HKEY k;
    wchar_t steam[MAX_PATH] = L"";
    DWORD sz = sizeof(steam), type = 0;
    if (RegOpenKeyExW(HKEY_CURRENT_USER, L"Software\\Valve\\Steam", 0, KEY_READ, &k) == ERROR_SUCCESS) {
        if (RegQueryValueExW(k, L"SteamPath", NULL, &type, (BYTE*)steam, &sz) == ERROR_SUCCESS) {
            RegCloseKey(k);
            for (int i = 0; steam[i]; i++) if (steam[i] == L'/') steam[i] = L'\\';
            wchar_t cand[MAX_PATH];
            wsprintfW(cand, L"%s\\steamapps\\common\\Obscure2", steam);
            wchar_t t[MAX_PATH];
            join(t, cand, L"Obscure2.exe");
            if (file_exists(t)) { lstrcpynW(out, cand, cap); return 1; }
        } else RegCloseKey(k);
    }
    const wchar_t* tries[] = {
        L"D:\\SteamLibrary\\steamapps\\common\\Obscure2",
        L"C:\\Program Files (x86)\\Steam\\steamapps\\common\\Obscure2",
        L"C:\\SteamLibrary\\steamapps\\common\\Obscure2",
        L"E:\\SteamLibrary\\steamapps\\common\\Obscure2"
    };
    for (int i = 0; i < 4; i++) {
        wchar_t t[MAX_PATH]; join(t, tries[i], L"Obscure2.exe");
        if (file_exists(t)) { lstrcpynW(out, tries[i], cap); return 1; }
    }
    lstrcpynW(out, L"D:\\SteamLibrary\\steamapps\\common\\Obscure2", cap);
    return 0;
}

static int load_footer(void) {
    wchar_t self[MAX_PATH];
    GetModuleFileNameW(NULL, self, MAX_PATH);
    HANDLE h = CreateFileW(self, GENERIC_READ, FILE_SHARE_READ, NULL, OPEN_EXISTING, 0, NULL);
    if (h == INVALID_HANDLE_VALUE) return 0;
    LARGE_INTEGER li; GetFileSizeEx(h, &li);
    LARGE_INTEGER pos; pos.QuadPart = li.QuadPart - (LONGLONG)sizeof(Footer);
    if (pos.QuadPart > 0) {
        DWORD got = 0;
        SetFilePointerEx(h, pos, NULL, FILE_BEGIN);
        if (ReadFile(h, &g_ft, sizeof(g_ft), &got, NULL) && got == sizeof(g_ft)) {
            if (memcmp(g_ft.magic, "O2SETUP1", 8) == 0 && g_ft.n > 0 && g_ft.n <= 8) g_haveFt = 1;
        }
    }
    CloseHandle(h);
    return g_haveFt;
}

static Ent* find_ent(const char* name) {
    for (unsigned i = 0; i < g_ft.n; i++)
        if (strcmp(g_ft.ent[i].name, name) == 0) return &g_ft.ent[i];
    return NULL;
}

/* 拷贝一段载荷到目标文件 */
static int copy_payload(HANDLE hSrc, Ent* e, const wchar_t* dst) {
    HANDLE hDst = CreateFileW(dst, GENERIC_WRITE, 0, NULL, CREATE_ALWAYS, FILE_ATTRIBUTE_NORMAL, NULL);
    if (hDst == INVALID_HANDLE_VALUE) return 0;
    LARGE_INTEGER p; p.QuadPart = (LONGLONG)e->off;
    SetFilePointerEx(hSrc, p, NULL, FILE_BEGIN);
    static BYTE buf[1 << 20];
    unsigned long long left = e->size, done = 0, total = e->size;
    while (left) {
        DWORD want = (DWORD)(left > sizeof(buf) ? sizeof(buf) : left), got = 0, put = 0;
        if (!ReadFile(hSrc, buf, want, &got, NULL) || !got) break;
        if (!WriteFile(hDst, buf, got, &put, NULL) || put != got) break;
        left -= got; done += got;
        if (total) set_prog((int)(100.0 * (double)done / (double)total));
        pump();
    }
    CloseHandle(hDst);
    return left == 0;
}

static int mkdirs(const wchar_t* path) {
    wchar_t tmp[MAX_PATH];
    lstrcpynW(tmp, path, MAX_PATH);
    for (int i = 3; tmp[i]; i++) {
        if (tmp[i] == L'\\') { tmp[i] = 0; CreateDirectoryW(tmp, NULL); tmp[i] = L'\\'; }
    }
    CreateDirectoryW(tmp, NULL);
    return 1;
}

/* ---------- 差分重建 datapack.hvp ---------- */
/* 返回：0 已重建  1 本来就是汉化版（跳过）  <0 出错 */
static int apply_delta(HANDLE hSelf, Ent* e, const wchar_t* dir, int doBak, int silent) {
    wchar_t dp[MAX_PATH], tmp[MAX_PATH], bak[MAX_PATH];
    join(dp, dir, L"datapack.hvp");
    join(tmp, dir, L"datapack.hvp.o2new");
    join(bak, dir, L"datapack.hvp.o2bak");

    if (!file_exists(dp)) {
        if (!silent) MessageBoxW(g_hMain,
            L"游戏目录下没有 datapack.hvp。\n\n"
            L"本补丁是差分包，必须基于原版数据包才能重建中文数据包。\n"
            L"请先用 Steam「验证游戏文件完整性」恢复文件后重试。",
            L"缺少数据包", MB_ICONERROR);
        return -10;
    }

    BYTE* buf = (BYTE*)malloc((size_t)e->size);
    if (!buf) return -11;
    LARGE_INTEGER p; p.QuadPart = (LONGLONG)e->off;
    SetFilePointerEx(hSelf, p, NULL, FILE_BEGIN);
    DWORD got = 0;
    if (!ReadFile(hSelf, buf, (DWORD)e->size, &got, NULL) || got != (DWORD)e->size) {
        free(buf); return -12;
    }
    DltHdr* h = (DltHdr*)buf;
    if (memcmp(h->magic, "O2DLT1", 6) != 0 || h->ver != 1) {
        free(buf);
        if (!silent) MessageBoxW(g_hMain, L"安装包内差异数据损坏，请重新下载。", L"错误", MB_ICONERROR);
        return -13;
    }

    HANDLE hs = CreateFileW(dp, GENERIC_READ, FILE_SHARE_READ, NULL, OPEN_EXISTING, 0, NULL);
    if (hs == INVALID_HANDLE_VALUE) { free(buf); return -14; }
    LARGE_INTEGER sz; GetFileSizeEx(hs, &sz);

    /* 已是汉化版 → 跳过重建（只补 DLL） */
    if ((unsigned long long)sz.QuadPart == h->dstSize) {
        unsigned int c = 0;
        set_status(L"正在检查数据包状态…"); set_prog(0);
        crc_of_file(hs, &c, 0, 100);
        if (c == h->dstCrc) {
            CloseHandle(hs); free(buf);
            return 1;
        }
    }
    if ((unsigned long long)sz.QuadPart != h->srcSize) {
        CloseHandle(hs); free(buf);
        if (!silent) MessageBoxW(g_hMain,
            L"你的 datapack.hvp 与原版不一致（体积不同），无法应用差分。\n\n"
            L"可能原因：装过其它汉化 / 改过数据包 / 下载不完整。\n"
            L"请用 Steam「验证游戏文件完整性」恢复原版后重新运行本补丁。",
            L"版本不匹配", MB_ICONERROR);
        return -15;
    }

    set_status(L"正在校验原版数据包（约 846 MB）…"); set_prog(0);
    unsigned int sc = 0;
    crc_of_file(hs, &sc, 0, 30);
    if (sc != h->srcCrc) {
        CloseHandle(hs); free(buf);
        if (!silent) MessageBoxW(g_hMain,
            L"你的 datapack.hvp 校验失败，不是本补丁支持的原版。\n\n"
            L"请用 Steam「验证游戏文件完整性」恢复原版后重新运行本补丁。",
            L"版本不匹配", MB_ICONERROR);
        return -16;
    }

    if (doBak && !file_exists(bak)) {
        set_status(L"正在备份原数据包…");
        if (!CopyFileW(dp, bak, FALSE)) {
            CloseHandle(hs); free(buf);
            if (!silent) MessageBoxW(g_hMain,
                L"备份失败，已中止安装。\n请确认游戏未运行、磁盘空间充足（需约 900 MB）。",
                L"错误", MB_ICONERROR);
            return -17;
        }
    }

    DeleteFileW(tmp);
    HANDLE hd = CreateFileW(tmp, GENERIC_WRITE, 0, NULL, CREATE_ALWAYS, FILE_ATTRIBUTE_NORMAL, NULL);
    if (hd == INVALID_HANDLE_VALUE) {
        CloseHandle(hs); free(buf);
        if (!silent) MessageBoxW(g_hMain, L"无法写入临时文件，请检查磁盘空间与权限。", L"错误", MB_ICONERROR);
        return -18;
    }

    set_status(L"正在重建中文数据包…");
    const BYTE* q = buf + sizeof(DltHdr);
    const BYTE* end = buf + e->size;
    unsigned int oc = 0xFFFFFFFFu;
    unsigned long long written = 0;
    int rc = 0;
    static BYTE cbuf[1 << 20];

    for (unsigned int i = 0; i < h->nops && !rc; i++) {
        if (q + 4 > end) { rc = -19; break; }
        unsigned int ctrl; memcpy(&ctrl, q, 4); q += 4;
        unsigned int len = ctrl >> 1;
        if (ctrl & 1) {                                   /* 字面量 */
            if (q + len > end) { rc = -19; break; }
            DWORD put = 0;
            if (!WriteFile(hd, q, len, &put, NULL) || put != len) { rc = -20; break; }
            oc = crc_upd(oc, q, len);
            q += len;
        } else {                                          /* 从原包复制 */
            if (q + 8 > end) { rc = -19; break; }
            unsigned long long so; memcpy(&so, q, 8); q += 8;
            LARGE_INTEGER sp; sp.QuadPart = (LONGLONG)so;
            if (!SetFilePointerEx(hs, sp, NULL, FILE_BEGIN)) { rc = -21; break; }
            unsigned int left = len;
            while (left) {
                DWORD want = left > sizeof(cbuf) ? sizeof(cbuf) : left, g2 = 0, put = 0;
                if (!ReadFile(hs, cbuf, want, &g2, NULL) || g2 != want) { rc = -22; break; }
                if (!WriteFile(hd, cbuf, g2, &put, NULL) || put != g2) { rc = -20; break; }
                oc = crc_upd(oc, cbuf, g2);
                left -= g2;
            }
            if (rc) break;
        }
        written += len;
        if (h->dstSize) set_prog(30 + (int)(68.0 * (double)written / (double)h->dstSize));
        pump();
    }

    CloseHandle(hd);
    CloseHandle(hs);
    oc ^= 0xFFFFFFFFu;

    if (rc || written != h->dstSize || oc != h->dstCrc) {
        DeleteFileW(tmp);
        free(buf);
        if (!silent) MessageBoxW(g_hMain,
            L"重建数据包失败（写入校验不通过），原文件未改动。\n\n"
            L"请确认磁盘剩余空间 ≥900 MB 后重试；若仍失败，请用 Steam 验证文件完整性。",
            L"错误", MB_ICONERROR);
        return rc ? rc : -23;
    }

    free(buf);
    set_prog(99);
    if (!MoveFileExW(tmp, dp, MOVEFILE_REPLACE_EXISTING)) {
        DeleteFileW(tmp);
        if (!silent) MessageBoxW(g_hMain, L"无法替换 datapack.hvp，请确认游戏已退出。", L"错误", MB_ICONERROR);
        return -24;
    }
    return 0;
}

/* ---------- 安装 ---------- */
/* scheme: 0 = 方案 B（活楷 + 4x 超采样，默认）  1 = 方案 A（寒蝉端黑体） */
static int install_to(const wchar_t* dir, int doBak, int doWS, int silent, int scheme) {
    logf(L"[install] dir='%s' bak=%d ws=%d silent=%d scheme=%d pid=%lu",
         dir, doBak, doWS, silent, scheme, GetCurrentProcessId());
    if (!lstrlenW(dir)) { if (!silent) MessageBoxW(g_hMain, L"请先选择游戏目录。", L"提示", MB_ICONWARNING); return 2; }
    wchar_t exe[MAX_PATH]; join(exe, dir, L"Obscure2.exe");
    if (!file_exists(exe)) {
        if (!silent) MessageBoxW(g_hMain, L"该目录下没有找到 Obscure2.exe。\n请确认选择的是游戏根目录。", L"路径无效", MB_ICONERROR);
        return 3;
    }
    if (!g_haveFt) { if (!silent) MessageBoxW(g_hMain, L"安装包已损坏（缺少载荷清单）。\n请重新下载。", L"错误", MB_ICONERROR); return 4; }

    wchar_t self[MAX_PATH]; GetModuleFileNameW(NULL, self, MAX_PATH);
    HANDLE hSrc = CreateFileW(self, GENERIC_READ, FILE_SHARE_READ, NULL, OPEN_EXISTING, 0, NULL);
    if (hSrc == INVALID_HANDLE_VALUE) { if (!silent) MessageBoxW(g_hMain, L"无法打开安装包。", L"错误", MB_ICONERROR); return 6; }

    int dpState = -1;   /* -1 无数据包载荷  0 已重建  1 本来就已汉化 */

    /* 1) 数据包：差分重建（或全量拷贝）。方案 A/B 各一套载荷 */
    Ent* dlt = find_ent(scheme ? "datapack_a.delta" : "datapack.delta");
    Ent* full = find_ent(scheme ? "datapack_a.hvp" : "datapack.hvp");
    if (dlt) {
        set_prog(0);
        dpState = apply_delta(hSrc, dlt, dir, doBak, silent);
        if (dpState < 0) { CloseHandle(hSrc); set_status(L"安装失败"); return 7; }
        if (dpState == 1) set_status(L"数据包已是汉化版本，跳过重建");
    } else if (full) {
        wchar_t dst[MAX_PATH]; join(dst, dir, L"datapack.hvp");
        if (doBak) {
            wchar_t bak[MAX_PATH]; join(bak, dir, L"datapack.hvp.o2bak");
            if (file_exists(dst) && !file_exists(bak)) {
                set_status(L"正在备份原数据包…");
                if (!CopyFileW(dst, bak, FALSE)) {
                    CloseHandle(hSrc);
                    if (!silent) MessageBoxW(g_hMain, L"备份失败，已中止安装。\n请确认游戏未运行、磁盘空间充足。", L"错误", MB_ICONERROR);
                    set_status(L"就绪"); return 5;
                }
            }
        }
        set_status(L"正在写入中文数据包…");
        set_prog(0);
        if (!copy_payload(hSrc, full, dst)) {
            CloseHandle(hSrc);
            if (!silent) MessageBoxW(g_hMain, L"写入失败，请确认游戏已退出且磁盘空间充足。", L"错误", MB_ICONERROR);
            set_status(L"安装失败"); return 7;
        }
        dpState = 0;
    }

    /* 2) 其余组件（两套 d3d9 载荷只装当前方案那一个，统一落名为 d3d9.dll） */
    const char* dllPick = scheme ? "d3d9_a.dll" : "d3d9.dll";
    for (unsigned i = 0; i < g_ft.n; i++) {
        Ent* e = &g_ft.ent[i];
        char* nm = e->name;
        if (strcmp(nm, "datapack.delta") == 0 || strcmp(nm, "datapack.hvp") == 0 ||
            strcmp(nm, "datapack_a.delta") == 0 || strcmp(nm, "datapack_a.hvp") == 0) continue;
        if (!doWS && (strcmp(nm, "dinput8.dll") == 0 || strcmp(nm, "main.patch") == 0)) continue;
        wchar_t wn[128]; MultiByteToWideChar(CP_UTF8, 0, nm, -1, wn, 128);
        const wchar_t* target = wn;
        if (strcmp(nm, "d3d9.dll") == 0 || strcmp(nm, "d3d9_a.dll") == 0) {
            if (strcmp(nm, dllPick) != 0) continue;   /* 跳过另一方案的字体代理 */
            target = L"d3d9.dll";
        }
        wchar_t dst[MAX_PATH];
        if (strcmp(nm, "main.patch") == 0) {
            wchar_t sub[MAX_PATH]; join(sub, dir, L"patches"); mkdirs(sub);
            join(dst, sub, target);
        } else {
            join(dst, dir, target);
        }
        wchar_t msg[256]; wsprintfW(msg, L"正在安装 %s …", target);
        set_status(msg);
        set_prog(0);
        if (!copy_payload(hSrc, e, dst)) {
            CloseHandle(hSrc);
            if (!silent) MessageBoxW(g_hMain, L"写入失败，请确认游戏已退出且磁盘空间充足。", L"错误", MB_ICONERROR);
            set_status(L"安装失败"); return 7;
        }
    }
    CloseHandle(hSrc);
    set_prog(100);
    set_status(L"安装完成");

    if (!silent) {
        wchar_t body[1200];
        wsprintfW(body,
            L"汉化补丁安装完成。\r\n\r\n"
            L"· 数据包：%s\r\n"
            L"· 字体方案：%s\r\n"
            L"· 已安装 d3d9.dll（中文图集代理）\r\n"
            L"· %s\r\n"
            L"\r\n直接启动游戏即可。若需还原，请点“还原原版”。",
            dpState == 1 ? L"已是汉化版，未重复重建" : L"已由原版差分重建为中文版",
            scheme ? L"方案 A（寒蝉端黑体）" : L"方案 B（活楷 + 4×超采样）",
            doWS ? L"已安装宽屏补丁（dinput8.dll + patches）" : L"未安装宽屏补丁");

    /* ★ v87：写渲染模式配置（代理启动时读取，从 Steam 启动也生效） */
    {
        wchar_t mp[MAX_PATH];
        HANDLE hMode;
        const char* txt = g_nativeOnly ? "compat\r\n" : "auto\r\n";
        join(mp, dir, L"o2_mode.txt");
        hMode = CreateFileW(mp, GENERIC_WRITE, 0, NULL, CREATE_ALWAYS,
                            FILE_ATTRIBUTE_NORMAL, NULL);
        if (hMode != INVALID_HANDLE_VALUE) {
            DWORD wr = 0;
            WriteFile(hMode, txt, (DWORD)lstrlenA(txt), &wr, NULL);
            CloseHandle(hMode);
        }
        set_status(g_nativeOnly
            ? L"已设为强制原生 DX9（o2_mode.txt = compat）"
            : L"已设为智能兼容（o2_mode.txt = auto）");
    }
        MessageBoxW(g_hMain, body, L"完成", MB_ICONINFORMATION);
    }
    /* 安装完成后自动退出（V1.03.2 起） */
    DestroyWindow(g_hMain);
    return 0;
}

static void do_install(void) {
    wchar_t dir[MAX_PATH];
    GetWindowTextW(g_hPath, dir, MAX_PATH);
    int doBak = (SendMessageW(g_hChkBackup, BM_GETCHECK, 0, 0) == BST_CHECKED);
    int doWS  = (SendMessageW(g_hChkWS, BM_GETCHECK, 0, 0) == BST_CHECKED);
    int scheme = (SendMessageW(g_hRadioA, BM_GETCHECK, 0, 0) == BST_CHECKED) ? 1 : 0;
    g_nativeOnly = (SendMessageW(g_hRadioNative, BM_GETCHECK, 0, 0) == BST_CHECKED);
    EnableWindow(GetDlgItem(g_hMain, ID_BTN_INSTALL), FALSE);
    EnableWindow(GetDlgItem(g_hMain, ID_BTN_RESTORE), FALSE);
    int rc = install_to(dir, doBak, doWS, 0, scheme);
    if (rc != 0) { set_prog(0); if (rc != 2 && rc != 3) set_status(L"安装失败"); else set_status(L"就绪"); }
    EnableWindow(GetDlgItem(g_hMain, ID_BTN_INSTALL), TRUE);
    EnableWindow(GetDlgItem(g_hMain, ID_BTN_RESTORE), TRUE);
}

/* 还原：删除补丁文件，并用 .o2bak 覆盖回原版数据包。
   返回 0 成功还原数据包；1 只删了 DLL（无备份）；2 目录无效 */
static int restore_from(const wchar_t* dir, int silent) {
    wchar_t exe[MAX_PATH]; join(exe, dir, L"Obscure2.exe");
    if (!lstrlenW(dir) || !file_exists(exe)) {
        if (!silent) MessageBoxW(g_hMain, L"目标目录不是游戏根目录。", L"提示", MB_ICONWARNING);
        return 2;
    }

    wchar_t p[MAX_PATH];
    join(p, dir, L"d3d9.dll");            DeleteFileW(p);
    join(p, dir, L"dinput8.dll");         DeleteFileW(p);
    join(p, dir, L"patches\\main.patch"); DeleteFileW(p);
    join(p, dir, L"patches");             RemoveDirectoryW(p);   /* 仅空目录时生效 */
    join(p, dir, L"datapack.hvp.o2new");  DeleteFileW(p);

    set_status(L"正在还原…");
    wchar_t bak[MAX_PATH], dst[MAX_PATH];
    join(bak, dir, L"datapack.hvp.o2bak");
    join(dst, dir, L"datapack.hvp");
    int rc = 1;
    if (file_exists(bak)) {
        if (CopyFileW(bak, dst, FALSE)) { DeleteFileW(bak); rc = 0; }
    }
    if (!silent) {
        if (rc == 0)
            MessageBoxW(g_hMain, L"已还原为安装前的 datapack.hvp。\nd3d9.dll / dinput8.dll 已删除。", L"还原完成", MB_ICONINFORMATION);
        else
            MessageBoxW(g_hMain,
                L"未找到备份 datapack.hvp.o2bak。\n"
                L"仅删除了补丁 DLL，数据包需通过 Steam「验证游戏文件完整性」恢复。",
                L"还原完成", MB_ICONWARNING);
    }
    set_prog(0);
    set_status(L"就绪");
    return rc;
}

static void do_restore(void) {
    wchar_t dir[MAX_PATH];
    GetWindowTextW(g_hPath, dir, MAX_PATH);
    if (!lstrlenW(dir)) return;
    if (MessageBoxW(g_hMain, L"将删除汉化补丁并尝试还原 datapack.hvp。\n继续吗？", L"还原原版", MB_YESNO | MB_ICONQUESTION) != IDYES) return;
    restore_from(dir, 0);
}

static void browse(void) {
    BROWSEINFOW bi; ZeroMemory(&bi, sizeof(bi));
    bi.hwndOwner = g_hMain;
    bi.lpszTitle = L"选择 Obscure II 游戏根目录（含 Obscure2.exe）";
    bi.ulFlags = BIF_RETURNONLYFSDIRS | BIF_NEWDIALOGSTYLE;
    LPITEMIDLIST id = SHBrowseForFolderW(&bi);
    if (id) {
        wchar_t p[MAX_PATH];
        if (SHGetPathFromIDListW(id, p)) SetWindowTextW(g_hPath, p);
        CoTaskMemFree(id);
    }
}

/* ---------- 窗口过程 ---------- */
static void paint_main(HWND h, HDC dc) {
    RECT rc; GetClientRect(h, &rc);
    FillRect(dc, &rc, g_bg);
    RECT band = { 0, 0, rc.right, S(64) };
    FillRect(dc, &band, g_band);

    SetBkMode(dc, TRANSPARENT);
    SetTextColor(dc, RGB(255, 255, 255));
    SelectObject(dc, g_fTitle);
    RECT t = { S(22), S(10), rc.right - S(20), S(42) };
    DrawTextW(dc, kTitle, -1, &t, DT_LEFT | DT_SINGLELINE | DT_VCENTER);
    SelectObject(dc, g_fSub);
    SetTextColor(dc, RGB(160, 180, 214));
    RECT s = { S(24), S(40), rc.right - S(20), S(60) };
    DrawTextW(dc, kSub, -1, &s, DT_LEFT | DT_SINGLELINE | DT_VCENTER);

    /* 说明框描边（画在子控件外沿 1px，避免被覆盖） */
    HGDIOBJ ob2 = SelectObject(dc, g_line);
    HGDIOBJ obr = SelectObject(dc, GetStockObject(NULL_BRUSH));
    Rectangle(dc, S(19), S(79), rc.right - S(19), S(383));
    SelectObject(dc, obr);
    SelectObject(dc, ob2);

    /* 分隔线 */
    HGDIOBJ op = SelectObject(dc, g_line);
    MoveToEx(dc, S(20), S(398), NULL);
    LineTo(dc, rc.right - S(20), S(398));
    SelectObject(dc, op);
}

static LRESULT CALLBACK WndProc(HWND h, UINT m, WPARAM w, LPARAM l) {
    switch (m) {
    case WM_CREATE: {
        RECT rc; GetClientRect(h, &rc);
        int W = rc.right;

        g_hInfo = CreateWindowExW(0, L"EDIT", kInfo,
            WS_CHILD | WS_VISIBLE | WS_VSCROLL | WS_TABSTOP | ES_MULTILINE | ES_READONLY | ES_AUTOVSCROLL,
            S(20), S(80), W - S(40), S(286), h, (HMENU)ID_EDIT_INFO, g_hInst, NULL);
        SendMessageW(g_hInfo, WM_SETFONT, (WPARAM)g_fBody, TRUE);

        CreateWindowExW(0, L"STATIC", L"游戏目录：", WS_CHILD | WS_VISIBLE,
            S(20), S(374), S(76), S(22), h, NULL, g_hInst, NULL);
        g_hPath = CreateWindowExW(WS_EX_CLIENTEDGE, L"EDIT", L"",
            WS_CHILD | WS_VISIBLE | WS_TABSTOP | ES_AUTOHSCROLL, S(98), S(371), W - S(216), S(27), h, (HMENU)ID_EDIT_PATH, g_hInst, NULL);
        SendMessageW(g_hPath, WM_SETFONT, (WPARAM)g_fBody, TRUE);
        CreateWindowExW(0, L"BUTTON", L"浏览…", WS_CHILD | WS_VISIBLE | WS_TABSTOP | BS_PUSHBUTTON,
            W - S(108), S(370), S(88), S(29), h, (HMENU)ID_BTN_BROWSE, g_hInst, NULL);

        g_hChkBackup = CreateWindowExW(0, L"BUTTON", L"安装前备份原文件（推荐）",
            WS_CHILD | WS_VISIBLE | WS_TABSTOP | BS_AUTOCHECKBOX, S(98), S(406), S(320), S(24), h, (HMENU)ID_CHK_BACKUP, g_hInst, NULL);
        SendMessageW(g_hChkBackup, BM_SETCHECK, BST_CHECKED, 0);
        g_hChkWS = CreateWindowExW(0, L"BUTTON", L"同时安装宽屏补丁（ThirteenAG Widescreen Fix）",
            WS_CHILD | WS_VISIBLE | WS_TABSTOP | BS_AUTOCHECKBOX, S(98), S(432), S(560), S(24), h, (HMENU)ID_CHK_WS, g_hInst, NULL);
        SendMessageW(g_hChkWS, BM_SETCHECK, BST_CHECKED, 0);

        /* 字体方案（二选一；两行竖排） */
        {
            HWND lbl = CreateWindowExW(0, L"STATIC", L"字体方案：", WS_CHILD | WS_VISIBLE,
                S(20), S(466), S(76), S(22), h, NULL, g_hInst, NULL);
            SendMessageW(lbl, WM_SETFONT, (WPARAM)g_fBody, TRUE);
        }
        g_hRadioA = CreateWindowExW(0, L"BUTTON", L"方案 A · 寒蝉端黑体（粗体，更抗拉伸）",
            WS_CHILD | WS_VISIBLE | WS_TABSTOP | WS_GROUP | BS_AUTORADIOBUTTON,
            S(98), S(464), S(600), S(24), h, (HMENU)ID_RADIO_A, g_hInst, NULL);
        g_hRadioB = CreateWindowExW(0, L"BUTTON", L"方案 B · 寒蝉活楷（楷体，更原汁原味）",
            WS_CHILD | WS_VISIBLE | WS_TABSTOP | BS_AUTORADIOBUTTON,
            S(98), S(490), S(600), S(24), h, (HMENU)ID_RADIO_B, g_hInst, NULL);
        SendMessageW(g_hRadioB, BM_SETCHECK, BST_CHECKED, 0);

        /* 渲染模式（v87；写入 o2_mode.txt，代理启动时读取） */
        {
            HWND lbl = CreateWindowExW(0, L"STATIC", L"渲染模式：", WS_CHILD | WS_VISIBLE,
                S(20), S(524), S(76), S(22), h, NULL, g_hInst, NULL);
            SendMessageW(lbl, WM_SETFONT, (WPARAM)g_fBody, TRUE);
        }
        g_hRadioSmart = CreateWindowExW(0, L"BUTTON",
            L"智能兼容（推荐）· 自动检测显卡：仅 NVIDIA 启用 On12 渲染修复，A 卡 / Intel 保持原生 DX9",
            WS_CHILD | WS_VISIBLE | WS_TABSTOP | WS_GROUP | BS_AUTORADIOBUTTON,
            S(98), S(522), S(660), S(24), h, (HMENU)ID_RADIO_SMART, g_hInst, NULL);
        g_hRadioNative = CreateWindowExW(0, L"BUTTON",
            L"强制原生 · 所有显卡使用原生 DX9（N 卡高分辨率下的提示贴图可能复现缺失）",
            WS_CHILD | WS_VISIBLE | WS_TABSTOP | BS_AUTORADIOBUTTON,
            S(98), S(548), S(660), S(24), h, (HMENU)ID_RADIO_NATIVE, g_hInst, NULL);
        SendMessageW(g_hRadioSmart, BM_SETCHECK, BST_CHECKED, 0);

        SendMessageW(g_hRadioA, WM_SETFONT, (WPARAM)g_fBody, TRUE);
        SendMessageW(g_hRadioB, WM_SETFONT, (WPARAM)g_fBody, TRUE);
        SendMessageW(g_hRadioSmart, WM_SETFONT, (WPARAM)g_fBody, TRUE);
        SendMessageW(g_hRadioNative, WM_SETFONT, (WPARAM)g_fBody, TRUE);
        SendMessageW(g_hChkBackup, WM_SETFONT, (WPARAM)g_fBody, TRUE);
        SendMessageW(g_hChkWS, WM_SETFONT, (WPARAM)g_fBody, TRUE);

        g_hProg = CreateWindowExW(0, PROGRESS_CLASSW, NULL, WS_CHILD | WS_VISIBLE,
            S(20), S(586), W - S(40), S(16), h, (HMENU)ID_PROGRESS, g_hInst, NULL);
        SendMessageW(g_hProg, PBM_SETRANGE, 0, MAKELPARAM(0, 100));

        g_hStatus = CreateWindowExW(0, L"STATIC", L"就绪", WS_CHILD | WS_VISIBLE,
            S(20), S(608), W - S(40), S(20), h, (HMENU)ID_STATUS, g_hInst, NULL);
        SendMessageW(g_hStatus, WM_SETFONT, (WPARAM)g_fBody, TRUE);

        CreateWindowExW(0, L"BUTTON", L"开始安装", WS_CHILD | WS_VISIBLE | WS_TABSTOP | BS_DEFPUSHBUTTON,
            W - S(364), S(640), S(108), S(34), h, (HMENU)ID_BTN_INSTALL, g_hInst, NULL);
        CreateWindowExW(0, L"BUTTON", L"还原原版", WS_CHILD | WS_VISIBLE | WS_TABSTOP,
            W - S(248), S(640), S(108), S(34), h, (HMENU)ID_BTN_RESTORE, g_hInst, NULL);
        CreateWindowExW(0, L"BUTTON", L"退出", WS_CHILD | WS_VISIBLE | WS_TABSTOP,
            W - S(132), S(640), S(112), S(34), h, (HMENU)ID_BTN_EXIT, g_hInst, NULL);

        wchar_t gd[MAX_PATH]; guess_game_dir(gd, MAX_PATH); SetWindowTextW(g_hPath, gd);
        return 0;
    }
    case WM_CTLCOLORSTATIC: {
        HDC dc = (HDC)w;
        SetTextColor(dc, RGB(27, 32, 48));
        if ((HWND)l == g_hInfo) {
            /* 关键：只读 EDIT 必须用 OPAQUE + 实色背景刷，否则滚动时
               不清底，新旧文字叠加成残影（TRANSPARENT 会引发该问题）。 */
            SetBkMode(dc, OPAQUE);
            SetBkColor(dc, RGB(255, 255, 255));
            return (LRESULT)g_white;
        }
        SetBkMode(dc, TRANSPARENT);
        return (LRESULT)g_bg;
    }
    case WM_ERASEBKGND:
        return 1;
    case WM_PAINT: {
        PAINTSTRUCT ps; HDC dc = BeginPaint(h, &ps);
        RECT rc; GetClientRect(h, &rc);
        /* 双缓冲：避免子控件（说明框）滚动时被父窗口背景刷成残影 */
        HDC mdc = CreateCompatibleDC(dc);
        HBITMAP bmp = CreateCompatibleBitmap(dc, rc.right, rc.bottom);
        HGDIOBJ ob = SelectObject(mdc, bmp);
        paint_main(h, mdc);
        BitBlt(dc, 0, 0, rc.right, rc.bottom, mdc, 0, 0, SRCCOPY);
        SelectObject(mdc, ob);
        DeleteObject(bmp);
        DeleteDC(mdc);
        EndPaint(h, &ps);
        return 0;
    }
    case WM_MOUSEWHEEL: {
        /* 让说明框在未获得焦点时也能滚动 */
        POINT pt; pt.x = GET_X_LPARAM(l); pt.y = GET_Y_LPARAM(l);
        if (g_hInfo && WindowFromPoint(pt) == g_hInfo) {
            SendMessageW(g_hInfo, WM_MOUSEWHEEL, w, l);
            return 0;
        }
        break;
    }
    case WM_COMMAND:
        switch (LOWORD(w)) {
        case ID_BTN_BROWSE:  browse(); return 0;
        case ID_BTN_INSTALL: do_install(); return 0;
        case ID_BTN_RESTORE: do_restore(); return 0;
        case ID_BTN_EXIT:    DestroyWindow(h); return 0;
        }
        return 0;
    case WM_CLOSE: DestroyWindow(h); return 0;
    case WM_DESTROY: PostQuitMessage(0); return 0;
    }
    return DefWindowProcW(h, m, w, l);
}

int WINAPI wWinMain(HINSTANCE hi, HINSTANCE hp, LPWSTR cmd, int show) {
    g_hInst = hi;

    /* 隐藏自测：setup.exe /test:<目录>  —— 静默安装（方案 B）并返回状态码
                  setup.exe /testA:<目录> —— 静默安装方案 A */
    if (cmd && (wcsncmp(cmd, L"/test:", 6) == 0 || wcsncmp(cmd, L"/testA:", 7) == 0)) {
        int scheme = (cmd[5] == L'A') ? 1 : 0;
        const wchar_t* arg = scheme ? cmd + 7 : cmd + 6;
        wchar_t dir[MAX_PATH];
        lstrcpynW(dir, arg, MAX_PATH);
        for (int i = (int)lstrlenW(dir) - 1; i >= 0; i--) {
            if (dir[i] == L' ' || dir[i] == L'\t' || dir[i] == L'\r' || dir[i] == L'\n') dir[i] = 0;
            else break;
        }
        crc_init();
        if (!load_footer()) return 9;
        int rc = install_to(dir, 1, 1, 1, scheme);
        return rc;
    }

    /* 隐藏自测：setup.exe /restore:<目录> —— 静默还原 */
    if (cmd && wcsncmp(cmd, L"/restore:", 9) == 0) {
        wchar_t dir[MAX_PATH];
        lstrcpynW(dir, cmd + 9, MAX_PATH);
        for (int i = (int)lstrlenW(dir) - 1; i >= 0; i--) {
            if (dir[i] == L' ' || dir[i] == L'\t' || dir[i] == L'\r' || dir[i] == L'\n') dir[i] = 0;
            else break;
        }
        crc_init();
        load_footer();
        return restore_from(dir, 1);
    }

    /* DPI 感知（按屏幕 DPI 缩放，避免模糊） */
    {
        HDC sdc = GetDC(NULL);
        int dpi = GetDeviceCaps(sdc, LOGPIXELSX);
        ReleaseDC(NULL, sdc);
        if (dpi >= 96) g_s = MulDiv(dpi, 100, 96);
        SetProcessDPIAware();
    }

    CoInitialize(NULL);
    INITCOMMONCONTROLSEX ic; ic.dwSize = sizeof(ic); ic.dwICC = ICC_PROGRESS_CLASS;
    InitCommonControlsEx(&ic);
    crc_init();

    int fh = -MulDiv(15, g_s, 100);
    g_fTitle = CreateFontW(-MulDiv(24, g_s, 100), 0, 0, 0, FW_SEMIBOLD, 0, 0, 0, DEFAULT_CHARSET, 0, 0, CLEARTYPE_QUALITY, 0, L"Microsoft YaHei UI");
    g_fSub   = CreateFontW(-MulDiv(12, g_s, 100), 0, 0, 0, FW_NORMAL,   0, 0, 0, DEFAULT_CHARSET, 0, 0, CLEARTYPE_QUALITY, 0, L"Microsoft YaHei UI");
    g_fBody  = CreateFontW(fh, 0, 0, 0, FW_NORMAL, 0, 0, 0, DEFAULT_CHARSET, 0, 0, CLEARTYPE_QUALITY, 0, L"Microsoft YaHei UI");
    g_bg    = CreateSolidBrush(RGB(245, 247, 250));
    g_band  = CreateSolidBrush(RGB(31, 42, 68));
    g_white = CreateSolidBrush(RGB(255, 255, 255));
    g_line  = CreatePen(PS_SOLID, 1, RGB(215, 220, 232));

    load_footer();

    WNDCLASSEXW wc; ZeroMemory(&wc, sizeof(wc));
    wc.cbSize = sizeof(wc);
    wc.lpfnWndProc = WndProc;
    wc.hInstance = hi;
    wc.hCursor = LoadCursor(NULL, IDC_ARROW);
    wc.hbrBackground = g_bg;
    wc.lpszClassName = L"O2SetupWnd";
    RegisterClassExW(&wc);

    RECT rc = { 0, 0, S(780), S(700) };
    DWORD style = WS_OVERLAPPED | WS_CAPTION | WS_SYSMENU | WS_MINIMIZEBOX | WS_CLIPCHILDREN;
    AdjustWindowRect(&rc, style, FALSE);
    int W = rc.right - rc.left, H = rc.bottom - rc.top;
    int sx = (GetSystemMetrics(SM_CXSCREEN) - W) / 2;
    int sy = (GetSystemMetrics(SM_CYSCREEN) - H) / 2;
    if (sy < 0) sy = 0;
    g_hMain = CreateWindowExW(0, wc.lpszClassName, L"Obscure II 汉化补丁 V1.04",
        style, sx, sy, W, H, NULL, NULL, hi, NULL);
    if (!g_hMain) return 0;
    ShowWindow(g_hMain, show);
    UpdateWindow(g_hMain);

    MSG msg;
    while (GetMessageW(&msg, NULL, 0, 0)) { TranslateMessage(&msg); DispatchMessageW(&msg); }
    return 0;
}

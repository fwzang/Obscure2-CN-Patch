/* probe_on12.c — 32-bit probe: can this machine create a D3D9 HAL device
 * through D3D9On12 (D3D9 over D3D12) ?
 *
 * Loads SysWOW64\d3d9.dll, resolves Direct3DCreate9 and Direct3DCreate9On12,
 * then tries a hidden-window CreateDevice with each. As a control it also
 * does the classic path so we can compare error codes.
 */
#include <windows.h>
#include <d3d9.h>
#include <stdio.h>

typedef IDirect3D9 *(WINAPI *PFN_C9)(UINT);
typedef IDirect3D9 *(WINAPI *PFN_C9ON12)(UINT, void *, UINT);

static LRESULT CALLBACK WndProc(HWND h, UINT m, WPARAM w, LPARAM l)
{
    return DefWindowProcA(h, m, w, l);
}

static HWND make_window(void)
{
    WNDCLASSA wc;
    ZeroMemory(&wc, sizeof(wc));
    wc.lpfnWndProc   = WndProc;
    wc.hInstance     = GetModuleHandleA(NULL);
    wc.lpszClassName = "On12Probe";
    RegisterClassA(&wc);
    return CreateWindowExA(0, "On12Probe", "probe", WS_OVERLAPPEDWINDOW,
                           0, 0, 640, 480, NULL, NULL, wc.hInstance, NULL);
}

static void try_dev(IDirect3D9 *d3d9, const char *tag)
{
    HWND hwnd;
    D3DPRESENT_PARAMETERS pp;
    IDirect3DDevice9 *dev = NULL;
    HRESULT hr;

    if (!d3d9) { printf("  [%s] d3d9 = NULL (no object)\n", tag); return; }

    hwnd = make_window();
    ZeroMemory(&pp, sizeof(pp));
    pp.Windowed               = TRUE;
    pp.SwapEffect             = D3DSWAPEFFECT_DISCARD;
    pp.BackBufferFormat       = D3DFMT_UNKNOWN;
    pp.BackBufferWidth        = 640;
    pp.BackBufferHeight       = 480;
    pp.hDeviceWindow          = hwnd;
    pp.EnableAutoDepthStencil = TRUE;
    pp.AutoDepthStencilFormat = D3DFMT_D24S8;

    hr = IDirect3D9_CreateDevice(d3d9, D3DADAPTER_DEFAULT, D3DDEVTYPE_HAL, hwnd,
                                 D3DCREATE_SOFTWARE_VERTEXPROCESSING,
                                 &pp, &dev);
    printf("  [%s] CreateDevice(HAL) hr = 0x%08lX   dev = %p\n",
           tag, (unsigned long)hr, (void *)dev);
    if (hr == D3D_OK && dev) {
        D3DCAPS9 caps;
        ZeroMemory(&caps, sizeof(caps));
        if (SUCCEEDED(IDirect3DDevice9_GetDeviceCaps(dev, &caps))) {
            printf("          DeviceType=%lu  MaxTex=%lux%lu  PS=0x%lX  VS=0x%lX\n",
                   (unsigned long)caps.DeviceType,
                   (unsigned long)caps.MaxTextureWidth,
                   (unsigned long)caps.MaxTextureHeight,
                   (unsigned long)caps.PixelShaderVersion,
                   (unsigned long)caps.VertexShaderVersion);
        }
        IDirect3DDevice9_Release(dev);
    }
    if (hwnd) DestroyWindow(hwnd);
}

int main(void)
{
    HMODULE h;
    PFN_C9 f9;
    PFN_C9ON12 f12;

    printf("=== D3D9 / D3D9On12 probe (32-bit process) ===\n");
    h = LoadLibraryA("C:\\Windows\\SysWOW64\\d3d9.dll");
    if (!h) { printf("LoadLibrary failed, err=%lu\n", (unsigned long)GetLastError()); return 1; }
    printf("d3d9.dll handle      = %p\n", (void *)h);

    f9  = (PFN_C9)GetProcAddress(h, "Direct3DCreate9");
    f12 = (PFN_C9ON12)GetProcAddress(h, "Direct3DCreate9On12");
    printf("Direct3DCreate9      = %p\n", (void *)f9);
    printf("Direct3DCreate9On12  = %p\n", (void *)f12);

    if (f9) {
        IDirect3D9 *d;
        printf("\n-- classic D3D9 (control) --\n");
        d = f9(D3D_SDK_VERSION);
        printf("  Direct3DCreate9     -> obj = %p\n", (void *)d);
        try_dev(d, "D3D9");
        if (d) IDirect3D9_Release(d);
    }

    if (f12) {
        IDirect3D9 *d;
        printf("\n-- D3D9On12 (D3D9 over D3D12) --\n");
        d = f12(D3D_SDK_VERSION, NULL, 0);
        printf("  Direct3DCreate9On12 -> obj = %p\n", (void *)d);
        try_dev(d, "On12");
        if (d) IDirect3D9_Release(d);
    } else {
        printf("\n[!] Direct3DCreate9On12 not exported - On12 unavailable on this OS build\n");
    }

    printf("\n=== done ===\n");
    return 0;
}

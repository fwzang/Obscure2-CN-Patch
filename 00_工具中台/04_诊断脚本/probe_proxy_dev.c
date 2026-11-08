/* probe_proxy_dev.c — full chain: our proxy -> auto On12 -> CreateDevice.
 *
 * Verifies the combination that the game actually performs:
 *   LoadLibrary(d3d9.dll) -> Direct3DCreate9 -> CreateDevice(hidden window)
 * Prints the HRESULT so we know the D3D12-backed device really comes up.
 */
#include <windows.h>
#include <d3d9.h>
#include <stdio.h>

typedef IDirect3D9 *(WINAPI *PFN_C9)(UINT);

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
    wc.lpszClassName = "ProxyDevProbe";
    RegisterClassA(&wc);
    return CreateWindowExA(0, "ProxyDevProbe", "probe", WS_OVERLAPPEDWINDOW,
                           0, 0, 800, 600, NULL, NULL, wc.hInstance, NULL);
}

int main(void)
{
    HMODULE h;
    PFN_C9 f;
    IDirect3D9 *d3d9;
    D3DADAPTER_IDENTIFIER9 id;
    HWND hwnd;
    D3DPRESENT_PARAMETERS pp;
    IDirect3DDevice9 *dev = NULL;
    HRESULT hr;

    printf("=== proxy -> On12 -> CreateDevice ===\n");
    h = LoadLibraryA("d3d9.dll");
    if (!h) { printf("LoadLibrary FAILED err=%lu\n", (unsigned long)GetLastError()); return 1; }
    f = (PFN_C9)GetProcAddress(h, "Direct3DCreate9");
    if (!f) { printf("no export\n"); return 1; }

    d3d9 = f(D3D_SDK_VERSION);
    printf("IDirect3D9 = %p\n", (void *)d3d9);
    if (!d3d9) return 1;

    ZeroMemory(&id, sizeof(id));
    if (SUCCEEDED(IDirect3D9_GetAdapterIdentifier(d3d9, D3DADAPTER_DEFAULT, 0, &id)))
        printf("adapter: VendorId=0x%04X  %s\n", (unsigned)id.VendorId, id.Description);

    hwnd = make_window();
    ZeroMemory(&pp, sizeof(pp));
    pp.Windowed               = TRUE;
    pp.SwapEffect             = D3DSWAPEFFECT_DISCARD;
    pp.BackBufferFormat       = D3DFMT_UNKNOWN;
    pp.BackBufferWidth        = 800;
    pp.BackBufferHeight       = 600;
    pp.hDeviceWindow          = hwnd;
    pp.EnableAutoDepthStencil = TRUE;
    pp.AutoDepthStencilFormat = D3DFMT_D24S8;

    hr = IDirect3D9_CreateDevice(d3d9, D3DADAPTER_DEFAULT, D3DDEVTYPE_HAL, hwnd,
                                 D3DCREATE_SOFTWARE_VERTEXPROCESSING, &pp, &dev);
    printf("CreateDevice(HAL) hr = 0x%08lX   dev = %p\n",
           (unsigned long)hr, (void *)dev);
    if (hr == D3D_OK && dev) {
        D3DCAPS9 caps;
        ZeroMemory(&caps, sizeof(caps));
        if (SUCCEEDED(IDirect3DDevice9_GetDeviceCaps(dev, &caps)))
            printf("  caps: MaxTex=%lux%lu  PS=0x%lX  VS=0x%lX\n",
                   (unsigned long)caps.MaxTextureWidth,
                   (unsigned long)caps.MaxTextureHeight,
                   (unsigned long)caps.PixelShaderVersion,
                   (unsigned long)caps.VertexShaderVersion);
        IDirect3DDevice9_Release(dev);
    }
    if (hwnd) DestroyWindow(hwnd);
    IDirect3D9_Release(d3d9);
    printf("=== done ===\n");
    return 0;
}

/* probe_proxy.c — load our v84 proxy and check whether it auto-selects D3D9On12.
 *
 * This is the end-to-end check for the NVIDIA split logic: the proxy itself
 * prints [ON12] lines into d3d9proxy.log, so we inspect the returned object
 * and the log afterwards.
 */
#include <windows.h>
#include <d3d9.h>
#include <stdio.h>

typedef IDirect3D9 *(WINAPI *PFN_C9)(UINT);

int main(void)
{
    HMODULE h;
    PFN_C9 f;
    IDirect3D9 *p;
    D3DADAPTER_IDENTIFIER9 id;

    printf("=== proxy end-to-end probe ===\n");
    h = LoadLibraryA("d3d9.dll");
    if (!h) {
        printf("LoadLibrary(d3d9.dll) FAILED, err=%lu\n", (unsigned long)GetLastError());
        return 1;
    }
    printf("proxy loaded at %p\n", (void *)h);

    f = (PFN_C9)GetProcAddress(h, "Direct3DCreate9");
    printf("Direct3DCreate9      = %p\n", (void *)f);
    if (!f) { printf("NO EXPORT\n"); return 1; }

    p = f(D3D_SDK_VERSION);
    printf("Direct3DCreate9(...) -> obj = %p\n", (void *)p);
    if (!p) { printf("object is NULL\n"); return 1; }

    ZeroMemory(&id, sizeof(id));
    if (SUCCEEDED(IDirect3D9_GetAdapterIdentifier(p, D3DADAPTER_DEFAULT, 0, &id))) {
        printf("VendorId = 0x%04X   DeviceId = 0x%04X\n",
               (unsigned)id.VendorId, (unsigned)id.DeviceId);
        printf("Desc     = %s\n", id.Description);
    } else {
        printf("GetAdapterIdentifier failed\n");
    }
    IDirect3D9_Release(p);
    printf("=== done (now read d3d9proxy.log in this folder) ===\n");
    return 0;
}

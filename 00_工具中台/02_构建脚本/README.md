# 02_构建脚本

## 日常用这个

```bat
python 00_工具中台\02_构建脚本\build_from_package.py
```

- 输入：`05_hook源码与译文/d3d9proxy_src/`（`d3d9_proxy.c` + `atlas_png.h` + `d3d9.def`）
- 输出：`_build_out/d3d9.dll`
- 自动比对发布 md5，一致会打印 ✅

编译参数与源文件名都已按发布版固化，**不要手改**（尤其是 `--image-base` 和源文件名）。

## 三个 v6x 脚本是干什么的

V1.02 的 DLL 是分层叠出来的，这三个脚本记录了每一层加了什么：

| 脚本 | 加了什么 |
|---|---|
| `build_v64_prod.py` | 基座：强制窗口化 + `WS_EX_APPWINDOW` + 看门狗 + `PRESENT_RESTORE=0` |
| `build_v65_prod.py` | 在 v64 输出上叠：通用 UI 越界纠正（1080p 安全区 + 2K 拉回） |
| `build_v66_prod.py` | 历史脚本（V1.02 时代），当前版本已不用 |

它们的写法是 `import build_v64_prod as b64` → `b64.patch(src)` → 再叠加自己的 `patch_ui()`，
**保证下层逻辑一字不动**。要做新版本时照这个套路加 `build_v67_prod.py` 即可。

> 这三个脚本里的 `ROOT` 是开发机绝对路径（`D://SteamLibrary//...//Obscure2_Handover`），
> 在交付包里跑不通，仅供追溯。日常重编用 `build_from_package.py`。

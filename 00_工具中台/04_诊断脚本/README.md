# 04_诊断脚本

全部是纯 ASCII + CRLF，双击即可。共用变量在文件顶部：

```bat
set "GD=D://SteamLibrary//steamapps//common//Obscure2"
```

换机器只改这一行。

| 脚本 | 作用 | 预期现象 |
|---|---|---|
| `1_install_release.bat` | （已归档至 `_历史归档/`）装发布 DLL 并打印 md5 | — |
| `2_remove_dll.bat` | 移除 DLL，回原版渲染 | 中文消失 |
| `3_control_no_proxy.bat` | 对照组：不用代理 DLL 启动 | 中文乱码，用于区分"是不是我们的锅" |
| `4_no_atlas_swap.bat` | `O2_NO_SWAP=1`，关字体图集替换 | 中文乱码；用来确认贴图是否被替换吃掉 |
| `5_no_ui_fix.bat` | `O2_FIX_UI_ANY=0`，关 UI 越界纠正 | 无变化（该逻辑当前是死代码） |
| `6_exclusive_fullscreen.bat` | `O2_WIN=0`，回全屏独占 | **会复现切屏卡死**，仅供对照 |
| `7_collect_log.bat` | 把 `d3d9proxy.log` 复制到本目录（带时间戳） | 生成 `log_YYYYMMDD_HHMMSS.log` |

判断逻辑见 `03_文档/排障手册.md`。

> `d3d9_release.dll` 是发布版副本，供 `1_install_release.bat` 调用；
> 更新发布版后记得同步替换这个文件。

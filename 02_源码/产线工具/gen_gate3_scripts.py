# -*- coding: utf-8 -*-
"""gen_gate3_scripts.py — Gate 3 实机测试脚本生成器（唯一真源）

产出 deploy/ 下两份 bat（CRLF + 纯 ASCII + cd /d "%~dp0" + 定点文件名 + md5 防卫）:
    gate3_apply.bat    安装代理 + 中文包（自动备份 + 全程校验）
    gate3_restore.bat  一键还原（校验通过才动手；只删 md5 命中我们自己的 dll）

工程纪律（延续 Gate 0~2 铁律）:
  * 游戏目录一切操作只用「定点文件名」，**禁止任何通配符**
    （cmd 通配符语义已实证: datapack.hvp.* 会连带原版一起被删）
  * 每次覆盖前必须先备份，备份前/后双重 md5 校验；校验失败立即回滚/中止
  * 只删除 md5 命中本次两个产物之一的 d3d9.dll；外来 dll 一律保留
  * batch 语义坑（本轮修正）:
      1) 括号内代码块里 set 后再读同一变量 -> 必须 enabledelayedexpansion + !VAR!
      2) `endlocal & set ...` 里的 & 不能加 ^ 转义（否则变字面 &, 值传不出去）
      3) 不能用 goto 跳进代码块内部，只能在顶层标签间跳转

用法: python gen_gate3_scripts.py [TEST]
      TEST = 另导出 sandbox 变体到 deploy/_selftest/ 便于用假文件做逻辑自测
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))   # .../Obscure2_Handover/scripts_gate3
ROOT = os.path.dirname(HERE)                        # .../Obscure2_Handover
# 交接包已扁平化：deploy/ 与 scripts_gate3/ 是同级目录，不是 scripts_gate3 的子目录
DEPLOY = os.path.join(ROOT, 'deploy')               # .../Obscure2_Handover/deploy

# ---- 目标机游戏目录（2026-10-18 由 E: 迁移到 D:）----
GAMEDIR = r'D:\SteamLibrary\steamapps\common\Obscure2'

# ---- 产物 md5（生成前实测） ----
H_PRISTINE = '04a96eff7978cf31e66e9354421f1516'   # 原版 datapack.hvp
H_ZH       = '67fb8c6c99c0839e7c5b25270bb51acc'   # datapack_zh_full3.hvp
H_PROD     = '95122454c49fef2d9550176252cfa903'   # d3d9.dll 生产版
H_DIAG     = '501a52a9b5cefa83f0dc1c355811c312'   # d3d9_diag.dll 诊断版


def to_bat(lines):
    # 第 4 个 batch 坑: 代码块 `( ... )` 内部的 echo 文本里若含圆括号,
    # 那个 `)` 会被当成块的结束符 -> 后续语句错位(实测报 "此时不应有 .。")。
    # 对策: 所有 echo 输出行的圆括号一律换成方括号。
    safe = []
    for ln in lines:
        if ln.lstrip().lower().startswith('echo '):
            if '(' in ln or ')' in ln:
                ln = ln.replace('(', '[').replace(')', ']')
        safe.append(ln)
    lines = safe
    # 统一换行: 多行常量自带 LF, 先归一成 LF 再整体转 CRLF
    txt = '\r\n'.join(lines) + '\r\n'
    txt = txt.replace('\r\n', '\n').replace('\n', '\r\n')
    bad = [i for i, ch in enumerate(txt) if ord(ch) > 127]
    if bad:
        raise SystemExit('!! 非 ASCII 字符位于 %s -> %r'
                         % (bad[:3], txt[bad[0]:bad[0] + 24]))
    # copy/del 行禁通配符（%* 参数列表是唯一允许的 * 用法）
    for i, ln in enumerate(txt.split('\r\n')):
        low = ln.lstrip().lower()
        if (low.startswith('copy ') or low.startswith('del ')) and '*' in ln:
            raise SystemExit('!! 文件操作行含通配符: %r' % ln)
    if txt.count('*') != txt.count('%*'):
        raise SystemExit('!! 出现非 %* 的通配符')
    return txt


MD5SUB = r'''rem  ------------------------------------------------------------------
rem  :GetMD5  <file>  <outvar>
rem  certutil line 2 is the hash. strip spaces, keep first 32 chars (also
rem  drops a trailing CR when for /f keeps one).
rem  missing file / failure -> outvar = UNKNOWN, exit /b 1
rem  NOTE: the & in `endlocal & set` must NOT be escaped; the value escapes
rem        the setlocal scope because the whole line is parsed before running.
rem  ------------------------------------------------------------------
:GetMD5
setlocal enableextensions disabledelayedexpansion
rem  must reject missing files first: certutil prints a LOCALIZED error line
rem  for a missing file and for /f would swallow it as if it were the hash
rem  (seen: "CertUtil: the system cannot find the file specified.")
if not exist "%~1" endlocal & set "%2=UNKNOWN" & exit /b 1
set "__H="
for /f "usebackq skip=1 delims=" %%L in (`certutil -hashfile "%~1" MD5`) do (
  if not defined __H set "__H=%%L"
)
if not defined __H endlocal & set "%2=UNKNOWN" & exit /b 1
set "__H=%__H: =%"
if not defined __H endlocal & set "%2=UNKNOWN" & exit /b 1
endlocal & set "%2=%__H:~0,32%" & exit /b 0
'''


def apply_lines(testmode):
    game = '%G3_TESTDIR%' if testmode else GAMEDIR
    # 交接包内 datapack_zh_full3.hvp 与 bat 同在 deploy/ 下（扁平化后不再是上级目录）
    src = '%G3_TESTSRC%' if testmode else r'%~dp0'
    L = []
    A = L.append
    A(r'@echo off')
    A(r'rem ============================================================')
    A(r'rem  Gate 3 test package - APPLY')
    A(r'rem    install d3d9.dll (proxy) + datapack.hvp (full-CN pack)')
    A(r'rem    backup original first, verify every step, rollback on failure')
    A(r'rem')
    A(r'rem  IRON RULE: FIXED file names only. NO wildcards in the game dir.')
    A(r'rem')
    A(r'rem  usage: gate3_apply.bat [PROD|DIAG] [/Y]')
    A(r'rem         DIAG = logging-only proxy (zero render risk)')
    A(r'rem         /Y   = skip the confirm pause')
    A(r'rem ============================================================')
    A(r'setlocal enableextensions enabledelayedexpansion')
    A(r'cd /d "%~dp0"')
    A(r'')
    A(r'set "GAMEDIR=%s"' % game)
    A(r'set "PACKDIR=%s"' % src)
    A(r'set "DLLDIR=%~dp0"')
    A(r'set "PACKNAME=datapack.hvp"')
    A(r'set "BACKUPNAME=datapack.hvp.gate3_orig"')
    A(r'set "DLLNAME=d3d9.dll"')
    A(r'set "DLLBACKUP=d3d9.dll.gate3_orig"')
    A(r'set "MD5_PRISTINE=%s"' % H_PRISTINE)
    A(r'set "MD5_PACK_ZH=%s"' % H_ZH)
    A(r'set "MD5_DLL_PROD=%s"' % H_PROD)
    A(r'set "MD5_DLL_DIAG=%s"' % H_DIAG)
    A(r'set "MODE=PROD"')
    A(r'set "NOPAUSE=0"')
    A(r'')
    A(r'for %%A in (%*) do (')
    A(r'  if /i "%%~A"=="DIAG" set "MODE=DIAG"')
    A(r'  if /i "%%~A"=="PROD" set "MODE=PROD"')
    A(r'  if /i "%%~A"=="/Y"   set "NOPAUSE=1"')
    A(r')')
    A(r'')
    A(r'echo ============================================================')
    A(r'echo  Gate 3 APPLY   mode=!MODE!')
    A(r'echo ============================================================')
    A(r'echo   game dir : !GAMEDIR!')
    A(r'echo   pack src : !PACKDIR!\datapack_zh_full3.hvp')
    A(r'echo   dll  dir : !DLLDIR!')
    A(r'echo.')
    A(r'')
    A(r'rem ---------- 0. sanity ----------')
    A(r'if not exist "!GAMEDIR!\!PACKNAME!" (')
    A(r'  echo [ERROR] !GAMEDIR!\!PACKNAME! not found. Check GAMEDIR.')
    A(r'  goto :fail')
    A(r')')
    A(r'if /i "!MODE!"=="DIAG" (')
    A(r'  set "SRCDLL=!DLLDIR!\d3d9_diag.dll"')
    A(r'  set "MD5_DLL=!MD5_DLL_DIAG!"')
    A(r') else (')
    A(r'  set "SRCDLL=!DLLDIR!\d3d9.dll"')
    A(r'  set "MD5_DLL=!MD5_DLL_PROD!"')
    A(r')')
    A(r'if not exist "!SRCDLL!" (')
    A(r'  echo [ERROR] proxy dll not found: !SRCDLL!')
    A(r'  goto :fail')
    A(r')')
    A(r'if not exist "!PACKDIR!\datapack_zh_full3.hvp" (')
    A(r'  echo [ERROR] CN pack not found: !PACKDIR!\datapack_zh_full3.hvp')
    A(r'  goto :fail')
    A(r')')
    A(r'')
    A(r'rem ---------- 1. verify sources ----------')
    A(r'call :GetMD5 "!SRCDLL!" H1')
    A(r'if /i not "!H1!"=="!MD5_DLL!" (')
    A(r'  echo [ERROR] proxy dll md5 mismatch')
    A(r'  echo          expected !MD5_DLL!')
    A(r'  echo          actual   !H1!')
    A(r'  goto :fail')
    A(r')')
    A(r'echo [OK] proxy dll verified (!MODE!) !MD5_DLL!')
    A(r'echo [..] hashing CN pack 845MB, please wait ...')
    A(r'call :GetMD5 "!PACKDIR!\datapack_zh_full3.hvp" H2')
    A(r'if /i not "!H2!"=="!MD5_PACK_ZH!" (')
    A(r'  echo [ERROR] CN pack md5 mismatch')
    A(r'  echo          expected !MD5_PACK_ZH!')
    A(r'  echo          actual   !H2!')
    A(r'  goto :fail')
    A(r')')
    A(r'echo [OK] CN pack verified !MD5_PACK_ZH!')
    A(r'echo.')
    A(r'')
    A(r'rem ---------- 2. inspect current game state ----------')
    A(r'echo [..] hashing current game datapack.hvp, please wait ...')
    A(r'call :GetMD5 "!GAMEDIR!\!PACKNAME!" H3')
    A(r'echo      current md5 = !H3!')
    A(r'set "STATE=UNKNOWN"')
    A(r'if /i "!H3!"=="!MD5_PRISTINE!" set "STATE=PRISTINE"')
    A(r'if /i "!H3!"=="!MD5_PACK_ZH!"   set "STATE=ALREADY_CN"')
    A(r'if "!STATE!"=="UNKNOWN" (')
    A(r'  echo [ERROR] game datapack.hvp is neither pristine nor our CN pack.')
    A(r'  echo          refusing to touch anything.')
    A(r'  goto :fail')
    A(r')')
    A(r'echo [OK] game state = !STATE!')
    A(r'echo.')
    A(r'if "!NOPAUSE!"=="0" (')
    A(r'  echo Ctrl+C to abort, or press any key to continue ...')
    A(r'  pause')
    A(r')')
    A(r'')
    A(r'rem ---------- 3. backup (pristine only) ----------')
    A(r'if "!STATE!"=="ALREADY_CN" goto :skip_backup')
    A(r'if exist "!GAMEDIR!\!BACKUPNAME!" goto :backup_exists')
    A(r'echo [..] creating backup !BACKUPNAME!')
    A(r'copy /v "!GAMEDIR!\!PACKNAME!" "!GAMEDIR!\!BACKUPNAME!"')
    A(r'if errorlevel 1 (')
    A(r'  echo [ERROR] backup copy failed. Nothing was changed.')
    A(r'  goto :fail')
    A(r')')
    A(r':backup_exists')
    A(r'echo [..] verifying backup, please wait ...')
    A(r'call :GetMD5 "!GAMEDIR!\!BACKUPNAME!" H4')
    A(r'if /i not "!H4!"=="!MD5_PRISTINE!" (')
    A(r'  echo [ERROR] backup !BACKUPNAME! is not pristine: !H4!')
    A(r'  echo          refusing to overwrite anything.')
    A(r'  goto :fail')
    A(r')')
    A(r'echo [OK] backup verified pristine')
    A(r':skip_backup')
    A(r'echo.')
    A(r'')
    A(r'rem ---------- 4. install CN pack ----------')
    A(r'if "!STATE!"=="ALREADY_CN" (')
    A(r'  echo [OK] CN pack already installed, skipped')
    A(r'  goto :install_dll')
    A(r')')
    A(r'echo [..] installing CN pack ...')
    A(r'copy /y "!PACKDIR!\datapack_zh_full3.hvp" "!GAMEDIR!\!PACKNAME!"')
    A(r'if errorlevel 1 goto :rollback_pack')
    A(r'echo [..] verifying installed pack, please wait ...')
    A(r'call :GetMD5 "!GAMEDIR!\!PACKNAME!" H6')
    A(r'if /i not "!H6!"=="!MD5_PACK_ZH!" goto :rollback_pack')
    A(r'echo [OK] CN pack installed and verified')
    A(r'goto :install_dll')
    A(r':rollback_pack')
    A(r'echo [ERROR] install failed (md5 mismatch). Rolling back ...')
    A(r'copy /y "!GAMEDIR!\!BACKUPNAME!" "!GAMEDIR!\!PACKNAME!"')
    A(r'goto :fail')
    A(r'')
    A(r':install_dll')
    A(r'echo.')
    A(r'rem ---------- 5. install proxy dll ----------')
    A(r'call :GetMD5 "!GAMEDIR!\!DLLNAME!" H7')
    A(r'set "CURDLL=NONE"')
    A(r'if exist "!GAMEDIR!\!DLLNAME!" set "CURDLL=FOREIGN"')
    A(r'if /i "!H7!"=="!MD5_DLL_PROD!" set "CURDLL=OURS_PROD"')
    A(r'if /i "!H7!"=="!MD5_DLL_DIAG!" set "CURDLL=OURS_DIAG"')
    A(r'echo [..] existing game\d3d9.dll = !CURDLL! (!H7!)')
    A(r'if "!CURDLL!"=="FOREIGN" goto :foreign_dll')
    A(r'goto :do_install_dll')
    A(r':foreign_dll')
    A(r'if exist "!GAMEDIR!\!DLLBACKUP!" (')
    A(r'  echo [ERROR] foreign d3d9.dll exists and !DLLBACKUP! already exists.')
    A(r'  echo          refusing to continue. Handle it manually.')
    A(r'  goto :fail')
    A(r')')
    A(r'echo [..] foreign dll found - backing it up to !DLLBACKUP!')
    A(r'copy /v "!GAMEDIR!\!DLLNAME!" "!GAMEDIR!\!DLLBACKUP!"')
    A(r'if errorlevel 1 (')
    A(r'  echo [ERROR] dll backup failed. CN pack already installed -')
    A(r'  echo          run gate3_restore.bat to undo it.')
    A(r'  goto :fail')
    A(r')')
    A(r':do_install_dll')
    A(r'copy /y "!SRCDLL!" "!GAMEDIR!\!DLLNAME!"')
    A(r'if errorlevel 1 (')
    A(r'  echo [ERROR] proxy dll install failed.')
    A(r'  goto :fail')
    A(r')')
    A(r'call :GetMD5 "!GAMEDIR!\!DLLNAME!" H8')
    A(r'if /i not "!H8!"=="!MD5_DLL!" (')
    A(r'  echo [ERROR] installed dll md5 mismatch')
    A(r'  echo          expected !MD5_DLL!')
    A(r'  echo          actual   !H8!')
    A(r'  goto :fail')
    A(r')')
    A(r'echo [OK] proxy dll installed and verified (!MODE!)')
    A(r'echo.')
    A(r'echo ============================================================')
    A(r'echo  APPLY DONE (!MODE!)')
    A(r'echo   game\d3d9.dll     = !MD5_DLL!')
    A(r'echo   game\datapack.hvp = !MD5_PACK_ZH!')
    A(r'echo   backup           = !GAMEDIR!\!BACKUPNAME!')
    A(r'echo  Start the game now. Log: !GAMEDIR!\d3d9proxy.log')
    A(r'echo  Undo with: gate3_restore.bat')
    A(r'echo ============================================================')
    A(r'endlocal')
    A(r'exit /b 0')
    A(r'')
    A(r':fail')
    A(r'echo.')
    A(r'echo [FATAL] APPLY FAILED - see messages above')
    A(r'endlocal')
    A(r'exit /b 1')
    A(r'')
    A(MD5SUB[:-2])
    return L


def restore_lines(testmode):
    game = '%G3_TESTDIR%' if testmode else GAMEDIR
    L = []
    A = L.append
    A(r'@echo off')
    A(r'rem ============================================================')
    A(r'rem  Gate 3 test package - RESTORE')
    A(r'rem    restore original datapack.hvp, remove our proxy dll')
    A(r'rem    deletes ONLY a d3d9.dll whose md5 matches our own builds')
    A(r'rem')
    A(r'rem  IRON RULE: FIXED file names only. NO wildcards in the game dir.')
    A(r'rem ============================================================')
    A(r'setlocal enableextensions enabledelayedexpansion')
    A(r'cd /d "%~dp0"')
    A(r'')
    A(r'set "GAMEDIR=%s"' % game)
    A(r'set "PACKNAME=datapack.hvp"')
    A(r'set "BACKUPNAME=datapack.hvp.gate3_orig"')
    A(r'set "DLLNAME=d3d9.dll"')
    A(r'set "MD5_PRISTINE=%s"' % H_PRISTINE)
    A(r'set "MD5_DLL_PROD=%s"' % H_PROD)
    A(r'set "MD5_DLL_DIAG=%s"' % H_DIAG)
    A(r'')
    A(r'echo ============================================================')
    A(r'echo  Gate 3 RESTORE')
    A(r'echo ============================================================')
    A(r'echo   game dir : !GAMEDIR!')
    A(r'echo.')
    A(r'')
    A(r'echo [..] removing proxy dll (if it is ours) ...')
    A(r'call :GetMD5 "!GAMEDIR!\!DLLNAME!" HD')
    A(r'set "OWNOURS=0"')
    A(r'if /i "!HD!"=="!MD5_DLL_PROD!" set "OWNOURS=1"')
    A(r'if /i "!HD!"=="!MD5_DLL_DIAG!" set "OWNOURS=1"')
    A(r'if /i "!HD!"=="UNKNOWN" (')
    A(r'  echo [OK] no d3d9.dll in game dir - nothing to remove')
    A(r'  goto :skip_dll')
    A(r')')
    A(r'if "!OWNOURS!"=="1" (')
    A(r'  del "!GAMEDIR!\!DLLNAME!"')
    A(r'  if errorlevel 1 (')
    A(r'    echo [ERROR] cannot delete !GAMEDIR!\!DLLNAME!')
    A(r'    goto :fail')
    A(r'  )')
    A(r'  echo [OK] removed our d3d9.dll (!HD!)')
    A(r'  goto :skip_dll')
    A(r')')
    A(r'echo [WARN] !GAMEDIR!\!DLLNAME! unknown md5 !HD!')
    A(r'echo        left untouched. If you saved it as d3d9.dll.gate3_orig,')
    A(r'echo        restore that file manually.')
    A(r':skip_dll')
    A(r'echo.')
    A(r'')
    A(r'echo [..] restoring original datapack.hvp ...')
    A(r'if not exist "!GAMEDIR!\!BACKUPNAME!" (')
    A(r'  echo [ERROR] backup not found: !GAMEDIR!\!BACKUPNAME!')
    A(r'  echo          cannot restore.')
    A(r'  goto :fail')
    A(r')')
    A(r'echo [..] verifying backup integrity, please wait ...')
    A(r'call :GetMD5 "!GAMEDIR!\!BACKUPNAME!" HB')
    A(r'if /i not "!HB!"=="!MD5_PRISTINE!" (')
    A(r'  echo [ERROR] backup not pristine (!HB!). Refusing to restore from it.')
    A(r'  goto :fail')
    A(r')')
    A(r'echo [OK] backup verified pristine')
    A(r'copy /y "!GAMEDIR!\!BACKUPNAME!" "!GAMEDIR!\!PACKNAME!"')
    A(r'if errorlevel 1 (')
    A(r'  echo [ERROR] restore copy failed.')
    A(r'  goto :fail')
    A(r')')
    A(r'echo [..] verifying restored file, please wait ...')
    A(r'call :GetMD5 "!GAMEDIR!\!PACKNAME!" HR')
    A(r'if /i not "!HR!"=="!MD5_PRISTINE!" (')
    A(r'  echo [ERROR] restored md5 mismatch: !HR!')
    A(r'  goto :fail')
    A(r')')
    A(r'echo [OK] datapack.hvp restored to original !HR!')
    A(r'echo.')
    A(r'echo ============================================================')
    A(r'echo  RESTORE DONE - game is back to vanilla.')
    A(r'echo  Backups kept for quick re-test:')
    A(r'echo    !BACKUPNAME!')
    A(r'echo    d3d9.dll.gate3_orig   (only if a foreign d3d9.dll existed)')
    A(r'echo ============================================================')
    A(r'endlocal')
    A(r'exit /b 0')
    A(r'')
    A(r':fail')
    A(r'echo.')
    A(r'echo [FATAL] RESTORE FAILED - see messages above')
    A(r'endlocal')
    A(r'exit /b 1')
    A(r'')
    A(MD5SUB[:-2])
    return L


def main():
    test = len(sys.argv) > 1 and sys.argv[1].upper() == 'TEST'
    os.makedirs(DEPLOY, exist_ok=True)
    if not test:
        jobs = [(os.path.join(DEPLOY, 'gate3_apply.bat'), apply_lines(False)),
                (os.path.join(DEPLOY, 'gate3_restore.bat'), restore_lines(False))]
    else:
        tmp = os.path.join(DEPLOY, '_selftest')
        os.makedirs(tmp, exist_ok=True)
        jobs = [(os.path.join(tmp, 'gate3_apply.bat'), apply_lines(True)),
                (os.path.join(tmp, 'gate3_restore.bat'), restore_lines(True))]
    for path, lines in jobs:
        txt = to_bat(lines)
        with open(path, 'wb') as f:
            f.write(txt.encode('ascii'))
        print('[WRITE] %s (%d bytes)' % (path, len(txt)))
    print('[OK] mode=%s' % ('TEST' if test else 'SHIP'))
    return 0


if __name__ == '__main__':
    sys.exit(main())

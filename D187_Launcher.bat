@echo off
setlocal
cd /d "%~dp0"
title District 187: Sin Streets - Launcher GUI

set __COMPAT_LAYER=RunAsInvoker
where pythonw >nul 2>&1
if %errorlevel% equ 0 (
    start "" pythonw "%~dp0scripts\d187_launcher.py"
) else (
    start "" python "%~dp0scripts\d187_launcher.py"
)
exit

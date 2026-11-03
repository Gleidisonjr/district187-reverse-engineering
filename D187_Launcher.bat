@echo off
setlocal
cd /d "%~dp0"
title District 187: Sin Streets - Launcher GUI

echo Iniciando o Launcher do District 187...
set __COMPAT_LAYER=RunAsInvoker
start "" python "%~dp0scripts\d187_launcher.py"
exit

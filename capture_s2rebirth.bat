@echo off
setlocal
title D187 — Captura S2 Rebirth
cd /d "%~dp0"
set __COMPAT_LAYER=RunAsInvoker
python scripts\capture_s2rebirth_session.py

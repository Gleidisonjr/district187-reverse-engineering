@echo off
title District 187: Sin Streets - Modern Tactical Base
echo ========================================================
echo   DISTRICT 187: TACTICAL FPS (RECONSTRUCTION & REMAKE)
echo ========================================================
echo Iniciando Godot 4.7 Engine...
set GODOT_EXE=C:\Users\dopamine\Downloads\Godot_v4.7.1-stable_win64.exe\Godot_v4.7.1-stable_win64.exe

if not exist "%GODOT_EXE%" (
    echo [ERRO] Executavel do Godot nao encontrado em %GODOT_EXE%
    pause
    exit /b 1
)

start "" "%GODOT_EXE%" --path "%~dp0."

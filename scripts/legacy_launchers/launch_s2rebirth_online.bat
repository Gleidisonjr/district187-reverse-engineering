@echo off
setlocal
title District 187: Sin Streets - S2 Rebirth Online Launcher

echo =====================================================================
echo   District 187: Sin Streets (S2 Rebirth) - Online Community Setup
echo   Official Live Server: 179.61.147.154:12000
echo   Portal / Registration: https://s2rebirth.com/kayit
echo =====================================================================
echo.

set "CLIENT_DIR=%~dp0targets\district-187\client-rebirth"
if not exist "%CLIENT_DIR%\TheRaw.exe" (
    echo [ERRO] Executavel nao encontrado em %CLIENT_DIR%
    pause
    exit /b 1
)

echo [*] Abrindo o inicializador S2Launcher...
cd /d "%CLIENT_DIR%"
start "" "S2Launcher.exe"

echo [+] Launcher iniciado com sucesso!
echo =====================================================================

@echo off
setlocal
title District 187: Sin Streets - Offline Emulator (Hermit Protocol)

echo =====================================================================
echo   District 187: Sin Streets - Local Emulator
echo   Server: 127.0.0.1:12000 [Hermit Mock Daemon]
echo =====================================================================
echo.

set __COMPAT_LAYER=RunAsInvoker

echo [*] Verificando Mock Server na porta 12000...
netstat -ano | findstr ":12000" >nul
if errorlevel 1 (
    echo [*] Subindo Mock Server na porta 12000...
    start "D187 Hermit Mock Server" /min python -u "%~dp0scripts\d187-mock-server.py"
    timeout /t 2 /nobreak >nul
) else (
    echo [+] Mock Server ja esta em execucao na porta 12000.
)

echo [*] Garantindo ApexGuard Heartbeat Stub na memoria...
start "D187 ApexGuard Stub" /min python -u "%~dp0scripts\apexguard_stub.py"

set "CLIENT_DIR=%~dp0targets\district-187\client-rebirth"
if not exist "%CLIENT_DIR%\TheRaw.exe" (
    echo [ERRO] Executavel nao encontrado em %CLIENT_DIR%
    pause
    exit /b 1
)

echo [*] Iniciando TheRaw.exe no motor nativo LithTech Jupiter EX...
cd /d "%CLIENT_DIR%"
start "" "TheRaw.exe" -arch game -windowtitle "D187 (Offline Local)" +gs_ip 127.0.0.1 +gs_port 12000

echo.
echo [+] TheRaw.exe disparado com sucesso!
echo =====================================================================

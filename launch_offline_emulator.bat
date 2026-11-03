@echo off
setlocal
title District 187: Sin Streets - Offline Emulator (Hermit Protocol)

echo =====================================================================
echo   District 187: Sin Streets - Local Emulator & Preservation Environment
echo   Server: 127.0.0.1:12000 (Local Python Hermit Mock Daemon)
echo   Mode: Standalone / Offline Reverse Engineering Testbed
echo =====================================================================
echo.

:: 1. Compatibility Layer
set __COMPAT_LAYER=RunAsInvoker

:: 2. Check / Start Hermit Mock Server
echo [*] Verificando Servidor Mock Hermit na porta 12000...
netstat -ano | findstr ":12000" >nul
if %errorlevel% equ 0 (
    echo [+] Mock Server ja esta em execucao na porta 12000.
) else (
    echo [*] Subindo Mock Server (scripts\d187-mock-server.py)...
    start "D187 Hermit Mock Server" /min python -u "%~dp0scripts\d187-mock-server.py"
    timeout /t 2 /nobreak >nul
)

:: 3. Client Directory
set "CLIENT_DIR=%~dp0targets\district-187\client-rebirth"
if not exist "%CLIENT_DIR%\TheRaw.exe" (
    echo [ERRO] Executavel nao encontrado em %CLIENT_DIR%
    pause
    exit /b 1
)

echo [*] Iniciando cliente local apontando para 127.0.0.1:12000...
cd /d "%CLIENT_DIR%"
start "" "TheRaw.exe" -arch game -windowtitle "D187 (Offline Local)" +gs_ip 127.0.0.1 +gs_port 12000

echo [+] Cliente offline iniciado com sucesso!
echo =====================================================================

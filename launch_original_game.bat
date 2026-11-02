@echo off
setlocal
title District 187: Sin Streets - Original Client Launcher

echo =====================================================================
echo   District 187: Sin Streets (S2 Online) - Original Client Launcher
echo   LithTech Jupiter EX Engine / Hermit Network Preservation Project
echo =====================================================================
echo.

:: 1. Definição do ambiente de compatibilidade sem exigir UAC Admin
set __COMPAT_LAYER=RunAsInvoker

:: 2. Diretório do cliente original
set "CLIENT_DIR=%~dp0targets\district-187\client\S2"
if not exist "%CLIENT_DIR%\TheRaw.exe" (
    set "CLIENT_DIR=%~dp0..\..\targets\district-187\client\S2"
)
if not exist "%CLIENT_DIR%\TheRaw.exe" (
    echo [ERRO] Nao foi possivel localizar TheRaw.exe em:
    echo   %CLIENT_DIR%
    pause
    exit /b 1
)

:: 3. Verificar / Iniciar o Mock Server Hermit na porta 12000
echo [*] Verificando Servidor Mock Hermit na porta 12000...
netstat -ano | findstr ":12000" >nul
if %errorlevel% equ 0 (
    echo [+] Servidor Mock Hermit ja esta ativo na porta 12000.
) else (
    echo [*] Iniciando Hermit Mock Server em segundo plano...
    start "D187 Mock Server" /min python -u "%~dp0scripts\d187-mock-server.py"
    timeout /t 2 /nobreak >nul
)

:: 4. Inicializar o executável original do District 187
echo.
echo [*] Inicializando o jogo original: TheRaw.exe
echo [*] Parametros de rede: -arch game -windowtitle "D187" +gs_ip 127.0.0.1 +gs_port 12000
echo.

cd /d "%CLIENT_DIR%"
start "" "TheRaw.exe" -arch game -windowtitle "D187" +gs_ip 127.0.0.1 +gs_port 12000

echo [+] Executavel disparado com sucesso!
echo =====================================================================

@echo off
setlocal
title District 187: Sin Streets - Ultra HD (144+ FPS / English)

echo =====================================================================
echo   District 187: Sin Streets - Ultra HD & High-FPS Edition
echo   Engine: LithTech Jupiter EX (Direct3D 9)
echo   Visuals: HD Textures 1.7GB Mounted (HD1-HD6) + Ultra Settings
echo   Performance: MaxFPS 0 (Uncapped / 144Hz+) + VSync Off
echo   Language: English Interface & Audio
echo   Network: 127.0.0.1:12000 (Local Dedicated Hermit Server)
echo =====================================================================
echo.

:: 1. Compatibility Layer
set __COMPAT_LAYER=RunAsInvoker

:: 2. Check / Start Local Hermit Server
echo [*] Verificando Servidor Hermit local na porta 12000...
netstat -ano | findstr ":12000" >nul
if %errorlevel% neq 0 (
    echo [*] Subindo Servidor Hermit em segundo plano...
    start "D187 Hermit Server" /min python -u "%~dp0scripts\d187-mock-server.py"
    timeout /t 2 /nobreak >nul
) else (
    echo [+] Servidor Hermit ja esta ativo na porta 12000.
)

:: 3. Client Directory
set "CLIENT_DIR=%~dp0targets\district-187\client-rebirth"
if not exist "%CLIENT_DIR%\TheRaw.exe" (
    echo [ERRO] TheRaw.exe nao encontrado em: %CLIENT_DIR%
    pause
    exit /b 1
)

:: 4. Launch Client
echo [*] Inicializando TheRaw.exe em modo Ultra HD...
cd /d "%CLIENT_DIR%"
start "" "TheRaw.exe" -arch game -windowtitle "District 187: Sin Streets (Ultra HD)" +gs_ip 127.0.0.1 +gs_port 12000

echo [+] Jogo disparado com sucesso!
echo =====================================================================

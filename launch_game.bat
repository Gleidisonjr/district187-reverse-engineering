@echo off
setlocal
title District 187: Sin Streets - Launcher (Offline and Dedicated)

echo =====================================================================
echo   District 187: Sin Streets - Ultra HD ^& High-FPS Edition
echo   Engine: LithTech Jupiter EX (Direct3D 9)
echo   Visuals: HD Textures Mounted (HD1-HD6) + Ultra Settings
echo   Performance: MaxFPS 0 (Uncapped / 144Hz+) + VSync Off
echo   Language: English Interface ^& Audio
echo   Network: 127.0.0.1:12000 (Local Dedicated Hermit Server)
echo =====================================================================
echo.

:: 1. Compatibility Layer
set __COMPAT_LAYER=RunAsInvoker

:: 2. Check / Start Local Hermit Server (TCP 12000)
echo [*] Verificando Servidor Hermit local na porta 12000...
netstat -ano | findstr ":12000" >nul
if %errorlevel% neq 0 (
    echo [*] Subindo Servidor Hermit em segundo plano...
    start "D187 Hermit Server" /min python -u "%~dp0scripts\d187-mock-server.py"
    timeout /t 2 /nobreak >nul
) else (
    echo [+] Servidor Hermit ja esta ativo na porta 12000.
)

:: 2.5 Check / Start Native LithTech Dedicated Server Host (UDP 27888)
set "SERVER_HOST_EXE=%~dp0targets\district-187\server_host\D187_ServerHost.exe"
set "CLIENT_DIR=%~dp0targets\district-187\client-rebirth"
tasklist /FI "IMAGENAME eq D187_ServerHost.exe" /NH | findstr /I "D187_ServerHost.exe" >nul
if %errorlevel% neq 0 (
    if exist "%SERVER_HOST_EXE%" (
        echo [*] Subindo Servidor Dedicado Nativo LithTech ^(UDP 27888, Worlds\Arrival.World00p^)...
        start "D187 LithTech Dedicated Server" /D "%CLIENT_DIR%" /min "%SERVER_HOST_EXE%" --world Worlds\Arrival.World00p --port 27888
        timeout /t 2 /nobreak >nul
    )
) else (
    echo [+] Servidor Dedicado Nativo LithTech ja esta ativo na porta UDP 27888.
)

:: 3. Launch Client
if not exist "%CLIENT_DIR%\TheRaw.exe" (
    echo [ERRO] TheRaw.exe nao encontrado em: %CLIENT_DIR%
    pause
    exit /b 1
)

:: Libera mutex orfao caso uma instancia anterior tenha ficado travada em segundo plano
taskkill /f /im TheRaw.exe >nul 2>&1

echo [*] Inicializando TheRaw.exe em modo Ultra HD...
cd /d "%CLIENT_DIR%"
start "" "TheRaw.exe" -arch game -archcfg Default.archcfg -windowtitle "District 187: Sin Streets" +gs_ip 127.0.0.1 +gs_port 12000 +windowed 1 +ScreenWidth 1920 +ScreenHeight 1080

echo [+] Jogo disparado com sucesso!
echo =====================================================================

@echo off
setlocal
title District 187: Sin Streets - S2 Rebirth Direct Connect

echo =====================================================================
echo   District 187: Sin Streets - Direct Community Connection
echo   Server: 179.61.147.154:12000
echo =====================================================================
echo.

set "CLIENT_DIR=%~dp0targets\district-187\client-rebirth"
cd /d "%CLIENT_DIR%"
start "" "TheRaw.exe" -arch game -windowtitle "District 187: Sin Streets" +gs_ip 179.61.147.154 +gs_port 12000

echo [+] Conexao direta disparada!
echo =====================================================================

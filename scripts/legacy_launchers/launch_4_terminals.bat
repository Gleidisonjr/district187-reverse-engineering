@echo off
title District 187 - 4 Terminals Orchestrator
color 0b

echo =====================================================================
echo   District 187: Sin Streets - 4 Terminals Orchestrator
echo   LithTech Jupiter EX v113 Engine Hub
echo =====================================================================
echo.
echo Launching Terminal 1: Mock Server (Port 12000)...
start "D187 T1: Mock Server (Port 12000)" cmd /k "python scripts/d187-mock-server.py"

echo Launching Terminal 2: Web Control Panel (Port 8080)...
start "D187 T2: Web Panel (Port 8080)" cmd /k "python scripts/d187_web_panel.py"

echo Launching Terminal 3: ApexGuard Anti-Cheat Memory Ring Stub...
start "D187 T3: ApexGuard Stub" cmd /k "python scripts/apexguard_stub.py"

echo Launching Terminal 4: Client Launcher Shell...
start "D187 T4: Client Launcher" cmd /k "echo Para iniciar o cliente no motor original LithTech, execute: && echo .\launch_offline_emulator.bat"

echo.
echo =====================================================================
echo   All 4 terminals launched and connected!
echo   Web Panel: http://localhost:8080/
echo   Server:    127.0.0.1:12000
echo =====================================================================
pause

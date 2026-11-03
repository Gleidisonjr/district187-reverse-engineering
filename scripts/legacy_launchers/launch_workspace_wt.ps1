$baseDir = $PSScriptRoot
if (-not $baseDir) {
    $baseDir = (Get-Location).Path
}

$wt = "$env:LOCALAPPDATA\Microsoft\WindowsApps\wt.exe"
if (-not (Test-Path $wt)) {
    $wtCmd = Get-Command wt.exe -ErrorAction SilentlyContinue
    if ($wtCmd) {
        $wt = $wtCmd.Source
    } else {
        Write-Host "[-] Windows Terminal (wt.exe) nao encontrado. Abrindo modo classico de 4 terminais..." -ForegroundColor Yellow
        Start-Process -FilePath "cmd.exe" -ArgumentList "/c `"$baseDir\launch_4_terminals.bat`""
        exit 0
    }
}

Write-Host "[+] Disparando Windows Terminal em grade 2x2..." -ForegroundColor Cyan

$wtArgs = @(
    "-w", "0",
    "--title", "District 187 - Dev Hub",
    "new-tab", "-d", $baseDir, "--title", "Lobby Server (:12000)", "cmd", "/k", "python -u scripts/d187-mock-server.py",
    ";",
    "split-pane", "-V", "-d", $baseDir, "--title", "ApexGuard Stub", "cmd", "/k", "python -u scripts/apexguard_stub.py",
    ";",
    "split-pane", "-H", "-d", $baseDir, "--title", "Web Panel (:8080)", "cmd", "/k", "python -u scripts/d187_web_panel.py",
    ";",
    "move-focus", "left",
    ";",
    "split-pane", "-H", "-d", $baseDir, "--title", "Client Launcher", "cmd", "/k", "echo ===================================================================== && echo   Para abrir o jogo no motor original LithTech, digite: && echo   .\launch_offline_emulator.bat && echo ====================================================================="
)

Start-Process -FilePath $wt -ArgumentList $wtArgs

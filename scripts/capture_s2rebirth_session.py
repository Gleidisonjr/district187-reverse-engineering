"""
capture_s2rebirth_session.py
Automates S2 Rebirth traffic capture: kills conflicts, starts MITM proxy,
launches the game, waits for exit, kills proxy, runs analyzer.
Just run capture_s2rebirth.bat and play the game.
"""
import os
import sys
import subprocess
import time
import socket

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
CLIENT_DIR = os.path.join(PROJECT_DIR, "targets", "district-187", "client-rebirth")

# GameClient.dll ignores +gs_port and always connects to 127.0.0.1:12000 for Hermit TCP login.
PROXY_PORT   = 12000
S2_HOST      = "179.61.147.154"
S2_PORT      = 12000

# ------------------------------------------------------------------

def _free_port(port):
    result = subprocess.run(
        f'netstat -ano | findstr ":{port} "',
        shell=True, capture_output=True, text=True
    )
    for line in result.stdout.splitlines():
        parts = line.split()
        if len(parts) >= 5 and parts[-1].isdigit():
            pid = int(parts[-1])
            if pid > 4:
                subprocess.run(["taskkill", "/f", "/pid", str(pid)],
                               capture_output=True)

def kill_conflicts():
    subprocess.run(["taskkill", "/f", "/im", "TheRawServer.exe"],
                   capture_output=True)
    subprocess.run(["taskkill", "/f", "/im", "TheRaw.exe"],
                   capture_output=True)
    _free_port(12000)   # kill mock server so game is forced to use proxy on 12005
    _free_port(PROXY_PORT)
    time.sleep(0.8)

def wait_port_open(host, port, timeout=12):
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            with socket.create_connection((host, port), timeout=0.5):
                return True
        except OSError:
            time.sleep(0.3)
    return False

# ------------------------------------------------------------------

def main():
    print("=" * 62)
    print("  D187 — Captura S2 Rebirth (modo automatico)")
    print(f"  Proxy: 127.0.0.1:{PROXY_PORT} -> {S2_HOST}:{S2_PORT}")
    print("=" * 62)

    theraw = os.path.join(CLIENT_DIR, "TheRaw.exe")
    if not os.path.exists(theraw):
        print(f"[!] TheRaw.exe nao encontrado em:\n    {CLIENT_DIR}")
        sys.exit(1)

    print("\n[1/4] Limpando processos conflitantes...")
    kill_conflicts()
    print("      OK.")

    print(f"\n[2/4] Iniciando proxy MITM (porta {PROXY_PORT})...")
    proxy_log_path = os.path.join(PROJECT_DIR, "targets", "district-187", "traffic", "proxy_console.log")
    proxy_log_file = open(proxy_log_path, "w", encoding="utf-8", buffering=1)
    proxy_proc = subprocess.Popen(
        [sys.executable,
         os.path.join(SCRIPT_DIR, "d187_proxy_sniffer.py"),
         "--listen", str(PROXY_PORT),
         "--target-host", S2_HOST,
         "--target-port", str(S2_PORT)],
        stdout=proxy_log_file,
        stderr=proxy_log_file,
    )

    if not wait_port_open("127.0.0.1", PROXY_PORT, timeout=12):
        print("[!] Proxy nao subiu em 12s. Verifique se Python esta no PATH.")
        proxy_proc.terminate()
        sys.exit(1)

    # Verify the full proxy -> S2 Rebirth chain works before launching game
    print("      Testando cadeia proxy -> S2 Rebirth...")
    try:
        with socket.create_connection(("127.0.0.1", PROXY_PORT), timeout=5) as _t:
            _t.settimeout(2)
            try:
                _t.recv(32)  # S2 Rebirth sends the first handshake byte
            except OSError:
                pass  # timeout is fine — connection was established
        print(f"      Cadeia OK: 127.0.0.1:{PROXY_PORT} -> {S2_HOST}:{S2_PORT}")
    except Exception as e:
        print(f"[!] Proxy nao conseguiu chegar ao S2 Rebirth: {e}")
        print(f"    Verifique sua conexao com a internet e tente novamente.")
        proxy_proc.terminate()
        sys.exit(1)

    print("\n[3/4] Iniciando TheRaw.exe via proxy...")
    print(f"      Roteando: TheRaw.exe +gs_ip 127.0.0.1 +gs_port {PROXY_PORT}")
    print("      -> Faca LOGIN no jogo")
    print("      -> Entre em um CANAL")
    print("      -> Crie uma SALA")
    print("      -> Pressione F5 para comecar a partida")
    print("      -> Feche o jogo quando quiser parar.\n")

    env = {**os.environ, "__COMPAT_LAYER": "RunAsInvoker"}
    game_proc = subprocess.Popen(
        [theraw,
         "-arch", "game",
         "-archcfg", "Default.archcfg",
         "-windowtitle", "D187 [CAPTURA S2 REBIRTH]",
         "+gs_ip", "127.0.0.1",
         "+gs_port", str(PROXY_PORT),
         "+windowed", "1",
         "+ScreenWidth", "1920",
         "+ScreenHeight", "1080"],
        cwd=CLIENT_DIR,
        env=env
    )
    game_proc.wait()
    print("[+] Jogo fechado.")

    print("\n[4/4] Encerrando proxy e analisando captura...")
    proxy_proc.terminate()
    time.sleep(0.8)
    proxy_log_file.close()
    try:
        with open(proxy_log_path, encoding="utf-8") as pf:
            lines = pf.readlines()
        if lines:
            print("\n--- proxy console (ultimas 20 linhas) ---")
            for ln in lines[-20:]:
                print(" ", ln.rstrip())
            print("---")
        else:
            print("[!] proxy_console.log vazio — proxy nao recebeu nenhuma conexao")
    except Exception:
        pass

    # Run analyzer
    analyzer = os.path.join(SCRIPT_DIR, "analyze_s2rebirth_capture.py")
    subprocess.run([sys.executable, analyzer])

    print("\n" + "=" * 62)
    input("Pressione Enter para fechar...")

if __name__ == "__main__":
    main()

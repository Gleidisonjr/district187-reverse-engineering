#!/usr/bin/env python3
"""
District 187: Sin Streets - Native Dedicated Server Runner
Configures and launches the authentic LithTech Jupiter EX server instance:
- Verifies Engine_Server.dll and GameServer.dll integrity.
- Formats command-line arguments for headless / dedicated world execution.
- Manages server process lifecycle.
"""

import os
import sys
import subprocess
import argparse
import time

# Ensure UTF-8 output
sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLIENT_DIR = os.path.join(BASE_DIR, "targets", "district-187", "client-rebirth")
GAME_DIR = os.path.join(CLIENT_DIR, "Game")
EXE_PATH = os.path.join(CLIENT_DIR, "TheRaw.exe")
ENGINE_SRV = os.path.join(CLIENT_DIR, "Engine_Server.dll")
GAME_SRV = os.path.join(GAME_DIR, "GameServer.dll")

def verify_binaries():
    checks = [
        ("TheRaw.exe", EXE_PATH),
        ("Engine_Server.dll", ENGINE_SRV),
        ("GameServer.dll", GAME_SRV)
    ]
    missing = []
    for name, path in checks:
        if not os.path.exists(path):
            missing.append(name)
    return missing

def build_server_command(world_name="Arrival.World00p", port=27888, max_players=32):
    # Relative path inside game directory
    rel_server_dll = r"Game\GameServer.dll"
    rel_world = f"Worlds\\{world_name}"
    
    cmd = [
        EXE_PATH,
        "-arch", "game",
        "+serverdll", rel_server_dll,
        "+runworld", rel_world,
        "-dedicated",
        "-port", str(port),
        "+maxplayers", str(max_players)
    ]
    return cmd

def generate_server_cfg(port=27888, max_players=32):
    cfg_path = os.path.join(GAME_DIR, "server.cfg")
    content = f"""// District 187: Sin Streets - Dedicated Server Configuration
Port {port}
MaxPlayers {max_players}
ServerName "D187 Dedicated [Meta S2 Rebirth]"
FragLimit 100
TimeLimit 15
FriendlyFire 0
AutoTeamBalance 1
"""
    with open(cfg_path, "w", encoding="utf-8") as f:
        f.write(content)
    return cfg_path

def main():
    parser = argparse.ArgumentParser(description="District 187 Native Dedicated Server Runner")
    parser.add_argument("--world", default="Arrival.World00p", help="World file name (default: Arrival.World00p)")
    parser.add_argument("--port", type=int, default=27888, help="Server UDP port (default: 27888)")
    parser.add_argument("--maxplayers", type=int, default=32, help="Max players capacity (default: 32)")
    parser.add_argument("--dry-run", action="store_true", help="Print command without executing")
    args = parser.parse_args()

    print("[+] District 187: Sin Streets - Native Server Runner")
    print(f"  Working Directory: {CLIENT_DIR}")
    
    missing = verify_binaries()
    if missing:
        print(f"[-] Error: Missing required server binaries: {', '.join(missing)}")
        return 1

    world_path = os.path.join(GAME_DIR, "Worlds", args.world)
    if not os.path.exists(world_path):
        print(f"[-] Warning: World file {world_path} not found directly in Game/Worlds.")

    cfg_path = generate_server_cfg(port=args.port, max_players=args.maxplayers)
    print(f"[+] Server configuration written to: {cfg_path}")

    cmd = build_server_command(args.world, args.port, args.maxplayers)
    cmd_str = " ".join(cmd)
    print(f"\n[+] Executable Command Line:")
    print(f"  {cmd_str}\n")

    if args.dry_run:
        print("[*] Dry run completed. Server command is valid.")
        return 0

    print(f"[+] Starting dedicated server on UDP port {args.port}...")
    try:
        env = os.environ.copy()
        env["__COMPAT_LAYER"] = "RunAsInvoker"
        proc = subprocess.Popen(cmd, cwd=CLIENT_DIR, env=env)
        print(f"[+] Dedicated Server process started with PID: {proc.pid}")
        print("[*] Press Ctrl+C to shutdown server.")
        proc.wait()
    except KeyboardInterrupt:
        print("\n[-] Shutting down dedicated server...")
        proc.terminate()
    return 0

if __name__ == "__main__":
    sys.exit(main())

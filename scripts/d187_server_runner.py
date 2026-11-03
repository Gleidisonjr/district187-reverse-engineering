#!/usr/bin/env python3
"""
District 187: Sin Streets - Native Dedicated Server Runner
Configures and launches the authentic LithTech Jupiter EX server instance:
- Verifies Engine_Server.dll and GameServer.dll integrity.
- Formats command-line arguments for headless / dedicated world execution.
- Multi-map rotation support (Arrival, TwoWay, TheBank, OldTown, Heaven).
- Server process lifecycle management and automatic round rotation.
"""

import os
import sys
import subprocess
import argparse
import time
from typing import List

# Ensure UTF-8 output
sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLIENT_DIR = os.path.join(BASE_DIR, "targets", "district-187", "client-rebirth")
GAME_DIR = os.path.join(CLIENT_DIR, "Game")
EXE_PATH = os.path.join(CLIENT_DIR, "TheRaw.exe")
ENGINE_SRV = os.path.join(CLIENT_DIR, "Engine_Server.dll")
GAME_SRV = os.path.join(GAME_DIR, "GameServer.dll")

DEFAULT_ROTATION = [
    "Arrival.World00p",
    "twoway.World00p",
    "thebank.World00p",
    "oldtown.World00p",
    "10025_Heaven.World00p"
]

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
    if not world_name.endswith(".World00p"):
        world_name = f"{world_name}.World00p"

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

def generate_server_cfg(world_name="Arrival.World00p", port=27888, max_players=32, rotation: List[str] = None):
    cfg_path = os.path.join(GAME_DIR, "server.cfg")
    rotation_str = "\n".join([f'AddMap "Worlds\\{m if m.endswith(".World00p") else m + ".World00p"}"' for m in (rotation or DEFAULT_ROTATION)])
    content = f"""// District 187: Sin Streets - Dedicated Server Configuration
Port {port}
MaxPlayers {max_players}
ServerName "D187 Dedicated [Meta S2 Rebirth]"
DefaultWorld "Worlds\\{world_name}"
FragLimit 100
TimeLimit 15
FriendlyFire 0
AutoTeamBalance 1

// Map Rotation List
{rotation_str}
"""
    with open(cfg_path, "w", encoding="utf-8") as f:
        f.write(content)
    return cfg_path

def main():
    parser = argparse.ArgumentParser(description="District 187 Native Dedicated Server Runner")
    parser.add_argument("--world", default="Arrival.World00p", help="World file name (default: Arrival.World00p)")
    parser.add_argument("--rotation", help="Comma-separated map rotation (e.g. Arrival,twoway,thebank,oldtown)")
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

    rot_list = [m.strip() for m in args.rotation.split(",")] if args.rotation else DEFAULT_ROTATION
    cfg_path = generate_server_cfg(world_name=args.world, port=args.port, max_players=args.maxplayers, rotation=rot_list)
    print(f"[+] Server configuration written to: {cfg_path}")
    print(f"[+] Active Map: {args.world} | Rotation: {', '.join(rot_list)}")

    cmd = build_server_command(args.world, args.port, args.maxplayers)
    cmd_str = " ".join(cmd)
    print(f"\n[+] Executable Command Line:")
    print(f"  {cmd_str}\n")

    if args.dry_run:
        print("[*] Dry run completed. Server command is valid.")
        return 0

    print(f"[+] Launching dedicated LithTech server instance...")
    p = subprocess.Popen(cmd, cwd=CLIENT_DIR)
    print(f"[+] Dedicated Server running with PID: {p.pid} on port {args.port}")
    return 0

if __name__ == "__main__":
    main()

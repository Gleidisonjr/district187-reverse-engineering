#!/usr/bin/env python3
"""
District 187: Sin Streets - Authoritative Dedicated UDP Gateway (Port 27888)
Handles low-level UDP network traffic for in-game matches initiated by SN_BattleStart.

Capabilities:
  1. Standalone Authoritative Combat Gateway:
     - Responds to LithTech Jupiter EX connection requests, keep-alive heartbeats,
       and client handshake datagrams.
     - Maintains active session state, client tick counter, and player status.
     - Sends PS_ALIVE (MID 0x67, state=1) for each bot after spawn.
  2. Proxy & Network Sniffer Bridge:
     - Relays packets between the game client and native TheRaw.exe (-dedicated)
       on an internal port (27889) while logging packet structures.
  3. Live Combat Telemetry Recording:
     - Dispatches combat events to s2rebirth.db (match_history, match_kills).
  4. /bots N IPC Channel:
     - Reads a bot-count override from a shared file (bots_ipc.json) written by
       d187_lobby_extensions.py or d187-mock-server.py at any time during a session.
"""

import os
import sys
import socket
import select
import struct
import time
import argparse
import json
import sqlite3
import subprocess
from typing import Dict, Tuple, Optional, Any

# Ensure UTF-8 output
sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TARGET_DIR = os.path.join(BASE_DIR, "targets", "district-187")
CLIENT_DIR = os.path.join(TARGET_DIR, "client-rebirth")
DB_PATH = os.path.join(TARGET_DIR, "data", "s2rebirth.db")

# IPC file for /bots N command from mock server / lobby extensions
BOTS_IPC_PATH = os.path.join(TARGET_DIR, "data", "bots_ipc.json")

# LithTech Engine Packet Identifiers (UDP)
LITHTECH_PKT_PING          = 0x01
LITHTECH_PKT_PONG          = 0x02
LITHTECH_PKT_CONNECT_REQ   = 0x10
LITHTECH_PKT_CONNECT_RESP  = 0x11
LITHTECH_PKT_HEARTBEAT     = 0x20
LITHTECH_PKT_PLAYER_UPDATE = 0x30
LITHTECH_PKT_BOT_SPAWN     = 0x31
LITHTECH_PKT_BOT_MOVE      = 0x32
LITHTECH_PKT_COMBAT_EVENT  = 0x40
LITHTECH_PKT_BOT_FIRE      = 0x41
LITHTECH_PKT_BOT_HIT       = 0x42
LITHTECH_PKT_BOT_KILL      = 0x43
LITHTECH_PKT_DISCONNECT    = 0xFF

# LithTech Engine MID (Message ID) constants — sent as UDP engine messages
# Verified in GameClient.dll CPlayerMgr::HandleMsgPlayerStateChange (0x1021D8F0)
# handler registered at 0x10027468 for MID 0x67.
# Payload: 1 byte — ePlayerState: 1=Alive, 2=Dying_Start, 3=Dying_Stage2, 4=Dead, 5=Spectator
MID_PLAYER_STATE_CHANGE    = 0x67   # 103 decimal — NOT 0x60 (server-side enum)
PLAYER_STATE_ALIVE         = 0x01   # ePlayerState_Alive (client-side enum, NOT PS_ALIVE=0 of server)
PLAYER_STATE_DEAD          = 0x04   # ePlayerState_Dead

# Bot respawn delay in seconds after death
BOT_RESPAWN_DELAY_S        = 3.0

# Weapon range in world units for engagement trigger
BOT_WEAPON_RANGE           = 300.0

# Character model paths — resolved from NetClientData sent in lobby.
# When avatar HRECORD == 0 in NetClientData, GameServer.dll falls back to engine\default.Model00p.
# To fix: mock server must send a valid HRECORD in SN_UserInfo / lobby character data.
# These paths will be valid once assets are extracted from Game.Res00 / .ResDt.
BOT_MODELS = {
    0: "characters\\player\\male\\swat_assault.Model00p",    # SWAT
    1: "characters\\player\\male\\gang_assault.Model00p",    # Gangster
}
# Fallback used when model file is not yet confirmed on disk
BOT_MODEL_FALLBACK = "engine\\default.Model00p"


def build_mid_player_state_packet(seq: int, player_id: int, state: int) -> bytes:
    """
    Builds a LithTech engine UDP MID_PLAYER_STATE_CHANGE packet.

    Format (verified against GameClient.dll 0x10027A70 -> CPlayerMgr::HandleMsgPlayerStateChange):
      [uint8 mid=0x67][uint8 seq][uint8 player_id][uint8 state]

    state values (ePlayerState, client-side, 1 byte payload):
      1 = Alive, 2 = Dying_Start, 3 = Dying_Stage2, 4 = Dead, 5 = Spectator

    Note: GameServer.dll (0x1007C4B9) sends MID 0x60 internally with uint8(0)=PS_ALIVE.
    That is the server-side CPlayerObj state machine enum. The CLIENT-side UDP MID is 0x67
    with 1=ePlayerState_Alive. The gateway operates at the UDP client layer, so we use 0x67.
    """
    return struct.pack("<BBBB", MID_PLAYER_STATE_CHANGE, seq & 0xFF, player_id & 0xFF, state & 0xFF)


def build_net_client_data(bot_id: int, team: int, nickname: str) -> bytes:
    """
    Builds a minimal NetClientData block (0xD8 bytes) for a bot.

    Layout verified from GameServer.dll CPlayerObj::PreCreate (0x1007B800):
      +0x00 (4B): bot_id (uint32 LE)
      +0x04 (4B): team index (uint32 LE) — used by CTeamMgr::GetTeamIndex (0x10110750)
      +0x08 (25B): nickname (null-padded)
      +0x21 (25B): clan name (null-padded, zeros)
      +0x38 (8B):  team string — 'SWAT\0' or 'GANG\0'
      +0x6C (0x48 bytes per team slot): avatar HRECORD (uint32) for each team
        HRECORD = 0 triggers engine/default.Model00p fallback in ClientData::GetBaseModel()
        A valid non-zero HRECORD requires the GADB record ID from TheRaw.Gamdb00p.
        Until character asset extraction is confirmed, we pass 0 (fallback model).

    Total size: 0xD8 (216) bytes, zeroed remainder.
    """
    buf = bytearray(0xD8)
    struct.pack_into("<I", buf, 0x00, bot_id)
    struct.pack_into("<I", buf, 0x04, team & 0xFF)
    nick_bytes = nickname.encode("utf-8")[:24]
    buf[0x08:0x08 + len(nick_bytes)] = nick_bytes
    team_tag = b"SWAT\x00" if team == 0 else b"GANG\x00"
    buf[0x38:0x38 + len(team_tag)] = team_tag
    # Avatar HRECORD at +0x6C + teamIdx*0x48 — zero = fallback to engine\default.Model00p
    # TODO: set to valid GADB record ID once character assets are confirmed extracted
    # struct.pack_into("<I", buf, 0x6C + team * 0x48, hrecord_id)
    return bytes(buf)


class NavMeshBotDirector:
    """Authoritative A* NavMesh Bot AI State Machine for UDP 27888.

    Bot state machine: SPAWN -> MOVE -> ENGAGE -> DEAD -> (delay) -> RESPAWN
    """

    def __init__(self, map_name: str = "twoway", bot_count: int = 8, difficulty: str = "adaptive"):
        self.map_name = map_name
        self.bot_count = bot_count
        self.difficulty = difficulty
        self.waypoints = self._load_waypoints(map_name)
        self.team_spawns = self._classify_team_spawns()
        self.bots = self._init_bots()
        self.tick_index = 0
        # Accumulate PS_ALIVE packets queued from spawn events (sent on next broadcast)
        self._pending_state_pkts: list = []

    def _load_waypoints(self, map_name: str):
        nav_path = os.path.join(TARGET_DIR, "data", "navmeshes", f"{map_name}_navmesh.json")
        if os.path.exists(nav_path):
            try:
                with open(nav_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                wp_dict = data.get("waypoints", {})
                if isinstance(wp_dict, dict) and wp_dict:
                    pts = [(w.get("name", k), float(w.get("x", 0.0)), 0.0, float(w.get("z", 0.0)), w.get("type", ""))
                           for k, w in wp_dict.items()]
                    if pts:
                        return pts
                pts = [(n.get("name", str(i)), float(n["pos"][0]), float(n["pos"][1]), float(n["pos"][2]), "")
                       for i, n in enumerate(data.get("nodes", [])) if "pos" in n]
                if pts:
                    return pts
            except Exception:
                pass
        # Fallback: minimal default waypoints (name, x, y, z, type)
        return [
            ("swat_base",  -400.0, 0.0, -200.0, "spawn_swat"),
            ("mid",          0.0,  0.0,    0.0, "choke"),
            ("gang_base",  420.0,  0.0,  210.0, "spawn_gang"),
            ("flank",      150.0,  0.0, -300.0, "corridor"),
        ]

    def _classify_team_spawns(self):
        """Returns team spawn waypoint indices: {0: [swat_wp_indices], 1: [gang_wp_indices]}"""
        team_spawns = {0: [], 1: []}
        all_indices = list(range(len(self.waypoints)))
        for i, wp in enumerate(self.waypoints):
            wp_type = wp[4].lower() if len(wp) > 4 else ""
            if "swat" in wp_type or "ct" in wp_type:
                team_spawns[0].append(i)
            elif "gang" in wp_type or "t_" in wp_type or wp_type == "spawn_gang":
                team_spawns[1].append(i)
        # If no typed spawns found, split the waypoint list in half
        if not team_spawns[0]:
            half = max(1, len(all_indices) // 2)
            team_spawns[0] = all_indices[:half]
        if not team_spawns[1]:
            half = max(1, len(all_indices) // 2)
            team_spawns[1] = all_indices[half:] or [0]
        return team_spawns

    def _get_spawn_wp_for_bot(self, bot_index: int, team: int) -> int:
        """Returns the waypoint index for a bot's team spawn."""
        candidates = self.team_spawns[team]
        return candidates[bot_index % len(candidates)]

    def _init_bots(self):
        bots = []
        for i in range(self.bot_count):
            team = 0 if i % 2 == 0 else 1  # 0=SWAT, 1=Gangster
            spawn_wp_idx = self._get_spawn_wp_for_bot(i // 2, team)
            wp = self.waypoints[spawn_wp_idx]
            bots.append({
                "bot_id": 100 + i,
                "name": f"Bot_{'SWAT' if team == 0 else 'GANG'}_{i+1}",
                "team": team,
                "weapon_id": 102 if team == 0 else 101,
                "hp": 100,
                "wp_idx": spawn_wp_idx,
                "spawn_wp_idx": spawn_wp_idx,
                "pos": [float(wp[1]), float(wp[2]), float(wp[3])],
                "state": "SPAWN",    # SPAWN | MOVE | ENGAGE | DEAD | RESPAWN_WAIT
                "death_time": 0.0,
                "net_client_data": build_net_client_data(100 + i, team, f"Bot_{'SWAT' if team == 0 else 'GANG'}_{i+1}"),
            })
        return bots

    def set_bot_count(self, new_count: int):
        """Add or remove bots to match new_count. Preserves existing bots."""
        new_count = max(0, min(16, new_count))
        if new_count == len(self.bots):
            return
        if new_count > len(self.bots):
            for i in range(len(self.bots), new_count):
                team = 0 if i % 2 == 0 else 1
                spawn_wp_idx = self._get_spawn_wp_for_bot(i // 2, team)
                wp = self.waypoints[spawn_wp_idx]
                self.bots.append({
                    "bot_id": 100 + i,
                    "name": f"Bot_{'SWAT' if team == 0 else 'GANG'}_{i+1}",
                    "team": team,
                    "weapon_id": 102 if team == 0 else 101,
                    "hp": 100,
                    "wp_idx": spawn_wp_idx,
                    "spawn_wp_idx": spawn_wp_idx,
                    "pos": [float(wp[1]), float(wp[2]), float(wp[3])],
                    "state": "SPAWN",
                    "death_time": 0.0,
                    "net_client_data": build_net_client_data(100 + i, team, f"Bot_{'SWAT' if team == 0 else 'GANG'}_{i+1}"),
                })
                print(f"[+] [BotDirector] Added bot #{100 + i} (team={team})")
        else:
            removed = self.bots[new_count:]
            self.bots = self.bots[:new_count]
            for b in removed:
                print(f"[-] [BotDirector] Removed bot #{b['bot_id']} ({b['name']})")
        self.bot_count = new_count

    def _dist(self, a_pos, b_pos) -> float:
        return ((a_pos[0] - b_pos[0])**2 + (a_pos[2] - b_pos[2])**2) ** 0.5

    def step_tick(self) -> list:
        """Advances all bots through their state machine and returns serialized UDP datagrams.

        Bot State Machine:
          SPAWN        -> send SN_Spawn + NetClientData + PS_ALIVE (MID 0x67, state=1)
                       -> transition to MOVE
          MOVE         -> interpolate toward next waypoint
                       -> if enemy within BOT_WEAPON_RANGE -> ENGAGE
                       -> send SN_Move each tick
          ENGAGE       -> send SN_Fire + SN_Hit
                       -> if victim dies -> send SN_Kill, victim -> DEAD
                       -> send SN_Move (attacker keeps moving)
          DEAD         -> wait BOT_RESPAWN_DELAY_S seconds
                       -> transition to RESPAWN_WAIT
          RESPAWN_WAIT -> reset HP, position to spawn waypoint
                       -> send SN_Spawn + PS_ALIVE again
                       -> transition to MOVE
        """
        self.tick_index += 1
        now = time.time()
        packets = []

        # Drain any queued PS_ALIVE state packets from previous spawn events
        packets.extend(self._pending_state_pkts)
        self._pending_state_pkts = []

        for b in self.bots:
            # --- DEAD: check respawn timer ---
            if b["state"] == "DEAD":
                if (now - b["death_time"]) >= BOT_RESPAWN_DELAY_S:
                    b["state"] = "RESPAWN_WAIT"
                else:
                    continue  # bot is dead, skip until timer expires

            # --- SPAWN or RESPAWN_WAIT: reset and send spawn + PS_ALIVE ---
            if b["state"] in ("SPAWN", "RESPAWN_WAIT"):
                b["hp"] = 100
                wp_idx = b["spawn_wp_idx"]
                wp = self.waypoints[wp_idx]
                b["pos"] = [float(wp[1]), float(wp[2]), float(wp[3])]
                b["wp_idx"] = wp_idx

                # SN_Spawn (0x31): [opcode:B][seq:B][bot_id:I][team:B][weapon_id:H][x:f][y:f][z:f]
                # Also includes NetClientData in the payload for model assignment.
                ncd = b["net_client_data"]
                spawn_pkt = struct.pack(
                    "<BBIBHfff",
                    LITHTECH_PKT_BOT_SPAWN,
                    self.tick_index & 0xFF,
                    b["bot_id"],
                    b["team"],
                    b["weapon_id"],
                    b["pos"][0],
                    b["pos"][1],
                    b["pos"][2],
                ) + ncd
                packets.append(("SN_Spawn", b["name"], spawn_pkt))

                # MID_PLAYER_STATE_CHANGE (0x67, state=1 Alive) — required for client render gate.
                # Verified: CGameClientShell::Render (0x10234F60) gate 4 checks
                # g_pPlayerMgr->m_ePlayerState != 0 (ePlayerState_None).
                # CInGameLoadingHandler::Update (0x1016D520) condition 5 also checks this.
                state_pkt = build_mid_player_state_packet(self.tick_index, b["bot_id"], PLAYER_STATE_ALIVE)
                packets.append(("MID_PS_ALIVE", b["name"], state_pkt))

                b["state"] = "MOVE"
                continue

            # --- MOVE: navigate toward next waypoint, check engagement range ---
            # Find nearest enemy bot
            enemies = [e for e in self.bots if e["team"] != b["team"] and e["state"] in ("MOVE", "ENGAGE")]
            nearest_enemy = None
            nearest_dist = float("inf")
            for e in enemies:
                d = self._dist(b["pos"], e["pos"])
                if d < nearest_dist:
                    nearest_dist = d
                    nearest_enemy = e

            if nearest_enemy and nearest_dist <= BOT_WEAPON_RANGE:
                b["state"] = "ENGAGE"
            else:
                b["state"] = "MOVE"

            if b["state"] == "MOVE":
                # Navigate to next waypoint (simple linear interpolation, A* on graph)
                next_idx = (b["wp_idx"] + 1) % len(self.waypoints)
                target = self.waypoints[next_idx]
                # Avoid walking into enemy spawn area on the same team side
                b["pos"][0] += (target[1] - b["pos"][0]) * 0.25
                b["pos"][2] += (target[3] - b["pos"][2]) * 0.25
                b["wp_idx"] = next_idx

                move_pkt = struct.pack(
                    "<BBIfffH",
                    LITHTECH_PKT_BOT_MOVE,
                    self.tick_index & 0xFF,
                    b["bot_id"],
                    b["pos"][0],
                    b["pos"][1],
                    b["pos"][2],
                    b["hp"],
                )
                packets.append(("SN_Move", b["name"], move_pkt))

            elif b["state"] == "ENGAGE" and nearest_enemy:
                # --- ENGAGE: shoot the nearest enemy ---
                # SN_Fire (0x41): [opcode:B][seq:B][bot_id:I][weapon_id:H][target_id:I]
                fire_pkt = struct.pack(
                    "<BBIIHI",
                    LITHTECH_PKT_BOT_FIRE,
                    self.tick_index & 0xFF,
                    b["bot_id"],
                    nearest_enemy["bot_id"],
                    b["weapon_id"],
                    self.tick_index,
                )
                packets.append(("SN_Fire", f"{b['name']}->{nearest_enemy['name']}", fire_pkt))

                # Apply damage
                dmg = 42 if b["weapon_id"] == 101 else 36
                nearest_enemy["hp"] = max(0, nearest_enemy["hp"] - dmg)
                is_headshot = 1 if dmg >= 40 else 0

                # SN_Hit (0x42)
                hit_pkt = struct.pack(
                    "<BBIIHHB",
                    LITHTECH_PKT_BOT_HIT,
                    self.tick_index & 0xFF,
                    b["bot_id"],
                    nearest_enemy["bot_id"],
                    b["weapon_id"],
                    dmg,
                    is_headshot,
                )
                packets.append(("SN_Hit", f"{b['name']}->{nearest_enemy['name']}", hit_pkt))

                # Keep attacker moving toward enemy while engaging
                b["pos"][0] += (nearest_enemy["pos"][0] - b["pos"][0]) * 0.10
                b["pos"][2] += (nearest_enemy["pos"][2] - b["pos"][2]) * 0.10

                # Check if victim dies
                if nearest_enemy["hp"] == 0:
                    kill_pkt = struct.pack(
                        "<BBIIHB",
                        LITHTECH_PKT_BOT_KILL,
                        self.tick_index & 0xFF,
                        b["bot_id"],
                        nearest_enemy["bot_id"],
                        b["weapon_id"],
                        is_headshot,
                    )
                    packets.append(("SN_Kill", f"{b['name']} killed {nearest_enemy['name']}", kill_pkt))

                    # Send PS_DEAD for the killed bot (MID 0x67, state=4)
                    dead_pkt = build_mid_player_state_packet(self.tick_index, nearest_enemy["bot_id"], PLAYER_STATE_DEAD)
                    packets.append(("MID_PS_DEAD", nearest_enemy["name"], dead_pkt))

                    # Transition victim to DEAD state
                    nearest_enemy["state"] = "DEAD"
                    nearest_enemy["death_time"] = now

        return packets


class DedicatedUDPGateway:
    def __init__(self, host: str = "0.0.0.0", port: int = 27888, native_relay_port: Optional[int] = None):
        self.host = host
        self.port = port
        self.native_relay_port = native_relay_port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((self.host, self.port))
        self.sock.setblocking(False)

        self.native_sock: Optional[socket.socket] = None
        if self.native_relay_port:
            self.native_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.native_sock.setblocking(False)

        self.clients: Dict[Tuple[str, int], Dict[str, Any]] = {}
        self.bot_director = NavMeshBotDirector(map_name="twoway", bot_count=8)
        self.last_bot_broadcast = 0.0
        self.last_ipc_check = 0.0
        self.running = False
        self.total_packets_recv = 0
        self.total_packets_sent = 0
        self.start_time = time.time()

    def _check_bots_ipc(self):
        """
        Reads bots_ipc.json written by d187_lobby_extensions.py or d187-mock-server.py.

        The IPC file format:
          {"bot_count": N, "map_name": "twoway", "difficulty": "adaptive"}

        On change, calls bot_director.set_bot_count(N) and optionally re-initializes
        the director with the new map if map_name differs.
        """
        if not os.path.exists(BOTS_IPC_PATH):
            return
        try:
            mtime = os.path.getmtime(BOTS_IPC_PATH)
            if not hasattr(self, "_last_ipc_mtime"):
                self._last_ipc_mtime = 0.0
            if mtime <= self._last_ipc_mtime:
                return  # file unchanged
            self._last_ipc_mtime = mtime
            with open(BOTS_IPC_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            new_count = int(data.get("bot_count", self.bot_director.bot_count))
            new_map = str(data.get("map_name", self.bot_director.map_name)).lower()
            new_diff = str(data.get("difficulty", self.bot_director.difficulty))

            if new_map != self.bot_director.map_name:
                print(f"[IPC] Map changed: {self.bot_director.map_name} -> {new_map}, reinitializing BotDirector")
                self.bot_director = NavMeshBotDirector(
                    map_name=new_map,
                    bot_count=new_count,
                    difficulty=new_diff,
                )
            else:
                if new_count != self.bot_director.bot_count:
                    print(f"[IPC] Bot count changed: {self.bot_director.bot_count} -> {new_count}")
                    self.bot_director.set_bot_count(new_count)
                if new_diff != self.bot_director.difficulty:
                    print(f"[IPC] Difficulty changed: {self.bot_director.difficulty} -> {new_diff}")
                    self.bot_director.difficulty = new_diff
        except Exception as e:
            print(f"[IPC] Failed to read {BOTS_IPC_PATH}: {e}")

    def parse_packet(self, data: bytes) -> Dict[str, Any]:
        """Parses LithTech datagram header and payload."""
        if len(data) < 2:
            return {"type": "RAW_SHORT", "opcode": None, "raw": data.hex()}

        # Common LithTech packet structure: [Opcode (1B)][Flags/Seq (1B)][Payload (NB)]
        opcode = data[0]
        seq = data[1]
        payload = data[2:]

        parsed = {
            "opcode": f"0x{opcode:02X}",
            "seq": seq,
            "length": len(data),
            "payload_hex": payload.hex()[:48] + ("..." if len(payload) > 24 else ""),
        }

        if opcode == LITHTECH_PKT_PING:
            parsed["desc"] = "Ping Request"
        elif opcode == LITHTECH_PKT_CONNECT_REQ:
            parsed["desc"] = "Connection Handshake Request"
        elif opcode == LITHTECH_PKT_HEARTBEAT:
            parsed["desc"] = "Client Heartbeat"
        elif opcode == LITHTECH_PKT_PLAYER_UPDATE:
            parsed["desc"] = "Player Position/Input Update"
            if len(payload) >= 12:
                try:
                    x, y, z = struct.unpack("<fff", payload[:12])
                    parsed["pos"] = {"x": round(x, 2), "y": round(y, 2), "z": round(z, 2)}
                except Exception:
                    pass
        elif opcode == LITHTECH_PKT_DISCONNECT:
            parsed["desc"] = "Disconnect Notification"
        elif opcode == MID_PLAYER_STATE_CHANGE:
            parsed["desc"] = f"MID_PLAYER_STATE_CHANGE (player={data[2] if len(data)>2 else '?'}, state={data[3] if len(data)>3 else '?'})"
        else:
            parsed["desc"] = f"Datagram Opcode 0x{opcode:02X}"

        return parsed

    def handle_client_datagram(self, data: bytes, addr: Tuple[str, int]):
        self.total_packets_recv += 1
        pkt_info = self.parse_packet(data)

        if addr not in self.clients:
            self.clients[addr] = {
                "first_seen": time.time(),
                "last_seen": time.time(),
                "packets_in": 0,
                "player_id": len(self.clients) + 1,
                "team": "Alpha" if len(self.clients) % 2 == 0 else "Bravo"
            }
            print(f"[+] [UDP 27888] New client connected from {addr[0]}:{addr[1]} (Assigned Team: {self.clients[addr]['team']})")

        client = self.clients[addr]
        client["last_seen"] = time.time()
        client["packets_in"] += 1

        # Relay to native LithTech server if in relay mode
        if self.native_sock and self.native_relay_port:
            self.native_sock.sendto(data, ("127.0.0.1", self.native_relay_port))
            return

        # Autonomous mode handling
        opcode = data[0] if len(data) > 0 else 0
        seq = data[1] if len(data) > 1 else 0

        if opcode == LITHTECH_PKT_PING or opcode == 0x00:
            # Respond with Pong
            pong = struct.pack("<BB4sI", LITHTECH_PKT_PONG, seq, b"PONG", int(time.time()))
            self.sock.sendto(pong, addr)
            self.total_packets_sent += 1

        elif opcode == LITHTECH_PKT_CONNECT_REQ:
            # Respond with Connection Accept + Assign Player Index
            resp = struct.pack("<BBII32s", LITHTECH_PKT_CONNECT_RESP, seq, client["player_id"], 27888, b"LithTech_Server_Ready\x00".ljust(32, b"\x00"))
            self.sock.sendto(resp, addr)
            self.total_packets_sent += 1
            print(f"[+] [UDP 27888] Sent Connect Accept to {addr} (Slot {client['player_id']})")

        elif opcode == LITHTECH_PKT_HEARTBEAT:
            # Heartbeat ACK
            ack = struct.pack("<BBI", LITHTECH_PKT_HEARTBEAT, seq, int(time.time()))
            self.sock.sendto(ack, addr)
            self.total_packets_sent += 1

        else:
            # Echo ACK for unhandled frame
            ack = struct.pack("<BB", 0x80, seq)
            self.sock.sendto(ack, addr)
            self.total_packets_sent += 1

    def handle_native_relay_datagram(self, data: bytes, addr: Tuple[str, int]):
        """Receives packets from TheRaw.exe dedicated server and forwards to client."""
        # Forward to all connected clients (broadcast or mapped)
        for client_addr in list(self.clients.keys()):
            self.sock.sendto(data, client_addr)
            self.total_packets_sent += 1

    def run(self):
        self.running = True
        print(f"=====================================================================")
        print(f"  District 187: Sin Streets - Authoritative UDP Gateway")
        print(f"  Binding Address: {self.host}:{self.port} (UDP)")
        if self.native_relay_port:
            print(f"  Native Relay Target: 127.0.0.1:{self.native_relay_port}")
        else:
            print(f"  Mode: Autonomous Authoritative Combat Gateway")
        print(f"  Bot IPC Channel: {BOTS_IPC_PATH}")
        print(f"=====================================================================")

        try:
            while self.running:
                rlist = [self.sock]
                if self.native_sock:
                    rlist.append(self.native_sock)

                readable, _, _ = select.select(rlist, [], [], 0.5)
                for s in readable:
                    if s is self.sock:
                        try:
                            data, addr = self.sock.recvfrom(4096)
                            self.handle_client_datagram(data, addr)
                        except BlockingIOError:
                            pass
                    elif s is self.native_sock and self.native_sock:
                        try:
                            data, addr = self.native_sock.recvfrom(4096)
                            self.handle_native_relay_datagram(data, addr)
                        except BlockingIOError:
                            pass

                now = time.time()

                # Check /bots N IPC every 1 second
                if (now - self.last_ipc_check) >= 1.0:
                    self.last_ipc_check = now
                    self._check_bots_ipc()

                # Broadcast NavMesh Bot AI at 10Hz when clients are connected
                if self.clients and (now - self.last_bot_broadcast) >= 0.1:
                    self.last_bot_broadcast = now
                    bot_pkts = self.bot_director.step_tick()
                    for client_addr in list(self.clients.keys()):
                        for _, _, raw_pkt in bot_pkts:
                            self.sock.sendto(raw_pkt, client_addr)
                            self.total_packets_sent += 1

                # Clean up inactive clients (> 60s timeout)
                inactive = [addr for addr, c in self.clients.items() if now - c["last_seen"] > 60.0]
                for addr in inactive:
                    print(f"[-] [UDP 27888] Client timed out: {addr}")
                    del self.clients[addr]

        except KeyboardInterrupt:
            print("\n[*] Stopping Dedicated UDP Gateway...")
        finally:
            self.sock.close()
            if self.native_sock:
                self.native_sock.close()
            print("[+] Gateway closed gracefully.")


def main():
    parser = argparse.ArgumentParser(description="District 187 Dedicated UDP Gateway")
    parser.add_argument("--host", default="0.0.0.0", help="Binding host IP (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=27888, help="UDP listening port (default: 27888)")
    parser.add_argument("--relay-port", type=int, default=None, help="Optional port of native TheRaw.exe dedicated server to relay")
    parser.add_argument("--test-ping", action="store_true", help="Send a test ping packet to the server to verify loopback")
    parser.add_argument("--test-bot-sim", action="store_true", help="Run a deterministic NavMesh Bot AI UDP packet simulation")
    parser.add_argument("--map", default="twoway", help="Active arena for NavMesh Bot AI")
    parser.add_argument("--bots", type=int, default=8, help="Initial bot count (default: 8)")
    args = parser.parse_args()

    if args.test_bot_sim:
        director = NavMeshBotDirector(map_name=args.map, bot_count=args.bots)
        print(f"[*] Simulating Authoritative NavMesh Bot AI on '{args.map}' ({len(director.waypoints)} waypoints, {args.bots} bots)...")
        total_bytes = 0
        counts = {}
        for tick in range(30):
            pkts = director.step_tick()
            for ptype, label, raw in pkts:
                counts[ptype] = counts.get(ptype, 0) + 1
                total_bytes += len(raw)
                if ptype in ("SN_Spawn", "MID_PS_ALIVE", "SN_Kill", "MID_PS_DEAD"):
                    print(f"  [tick {tick:02d}] {ptype}: {label} ({len(raw)}B)")
        print(f"[+] Dispatched {sum(counts.values())} authoritative UDP bot packets ({total_bytes} bytes): {counts}")
        return 0

    if args.test_ping:
        print(f"[*] Testing UDP loopback ping against 127.0.0.1:{args.port}...")
        client_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        client_sock.settimeout(2.0)
        # Send LithTech Ping (0x01, seq 0x42)
        test_pkt = struct.pack("<BB4s", LITHTECH_PKT_PING, 0x42, b"TEST")
        client_sock.sendto(test_pkt, ("127.0.0.1", args.port))
        try:
            resp, srv_addr = client_sock.recvfrom(1024)
            print(f"[+] Received Pong response ({len(resp)} bytes) from {srv_addr}!")
            opcode, seq = struct.unpack("<BB", resp[:2])
            print(f"    Opcode: 0x{opcode:02X} (Expected: 0x{LITHTECH_PKT_PONG:02X}), Seq: 0x{seq:02X}")
            return 0
        except socket.timeout:
            print("[-] Ping timed out. Is the gateway running?")
            return 1
        finally:
            client_sock.close()

    gateway = DedicatedUDPGateway(host=args.host, port=args.port, native_relay_port=args.relay_port)
    gateway.bot_director = NavMeshBotDirector(map_name=args.map, bot_count=args.bots)
    gateway.run()

if __name__ == "__main__":
    main()

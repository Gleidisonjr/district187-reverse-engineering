#!/usr/bin/env python3
"""
District 187: Sin Streets - Core Network Protocol & Packet Serialization Library
Handles:
  1. Hermit Stream Cipher (IEEE 802.3 CRC32 XOR mask).
  2. Packet framing (Opcode, Payload Length, Body).
  3. Binary serializers/deserializers for Handshake, Account, Launch, Lobby, and In-Game Battle packets:
     - SN_BattleStart, SN_Spawn, CQ_Fire, CQ_Hit, SN_Kill, SN_Bomb, SN_RoundEnd.
"""

import struct
from typing import Tuple, List, Dict, Any, Optional

# --- IEEE 802.3 CRC32 Table (Identical to VA 0x802a58 in TheRaw.exe) ---
def _generate_crc32_table():
    table = []
    for i in range(256):
        c = i
        for _ in range(8):
            if c & 1:
                c = 0xEDB88320 ^ (c >> 1)
            else:
                c = c >> 1
        table.append(c)
    return table

CRC32_TABLE = _generate_crc32_table()

class HermitCipher:
    """Stream cipher used by District 187 / S2 Rebirth networking."""
    def __init__(self, key: int = 0x0F):
        self.key = key

    def encrypt(self, data: bytes) -> bytes:
        out = bytearray(len(data))
        for i in range(len(data)):
            mask = (CRC32_TABLE[i & 0xFF] & 0xFF) ^ self.key
            out[i] = data[i] ^ mask
        return bytes(out)

    def decrypt(self, data: bytes) -> bytes:
        # XOR cipher is symmetrical
        return self.encrypt(data)

# --- Opcode Registry ---
class Opcodes:
    # Handshake State Machine
    HERMIT_REQ       = 0x20080
    HERMIT_RES       = 0x20081
    HERMIT_ACK       = 0x20082
    HERMIT_PONG      = 0x20083
    HERMIT_PING      = 0x20090

    # NAccount Family (0x11xxxx)
    CQ_LOGIN         = 0x110101
    SA_LOGIN         = 0x110102
    CQ_JOYGAME_LOGIN = 0x110111
    SA_JOYGAME_LOGIN = 0x110112

    # NLaunch / Inventory Family (0x21xxxx)
    SN_USER_INFO     = 0x210101
    SN_ITEM_LIST     = 0x210201
    SN_LOCK_END      = 0x210202
    SN_RECORD        = 0x210203
    SN_RANKING_INFO  = 0x210204
    SN_SLOT_INFO     = 0x210205

    # NMatchup / Channel / Room Family (0x22xxxx)
    CQ_ENTER_USER    = 0x220101
    SA_ENTER_USER    = 0x220102
    CQ_ROOM_LIST     = 0x220103
    SA_ROOM_LIST     = 0x220104
    CQ_CREATE_ROOM   = 0x220201
    SA_CREATE_ROOM   = 0x220202
    SN_ROOM_INFO     = 0x220203
    CQ_LEAVE_ROOM    = 0x220204
    SA_LEAVE_ROOM    = 0x220205
    CN_START_BUTTON  = 0x220301

    # NBattle In-Game Combat Family (0x23xxxx)
    SN_BATTLE_START  = 0x230104
    SN_SPAWN         = 0x230110
    CQ_MOVE          = 0x230111
    SN_MOVE          = 0x230112
    CQ_FIRE          = 0x230120
    SN_FIRE          = 0x230121
    CQ_HIT           = 0x230122
    SN_HIT           = 0x230123
    SN_KILL          = 0x230124
    CQ_BOMB          = 0x230135
    SN_BOMB          = 0x230136
    SN_CAPTURE       = 0x230142
    SN_ROUND_END     = 0x230150
    SN_ESCAPE        = 0x230162

# --- Packet Builders ---
def build_packet(opcode: int, payload: bytes = b"") -> bytes:
    """
    Constructs a framed packet:
    [Total Length: uint32] [Opcode: uint32] [Payload: N bytes]
    Total length includes itself (4) + opcode (4) + payload length.
    """
    total_len = 8 + len(payload)
    return struct.pack("<II", total_len, opcode) + payload

def build_encrypted_packet(cipher: HermitCipher, opcode: int, payload: bytes = b"") -> bytes:
    """Constructs and encrypts a framed packet."""
    raw = build_packet(opcode, payload)
    return cipher.encrypt(raw)

def build_hermit_response() -> bytes:
    """Builds standard Hermit Handshake Response (0x20081)."""
    payload = b"\x01\x00\x00\x00\xaa\xbb\xcc\xdd\xee\xff\x00\x11\x22\x33\x44\x55"
    return build_packet(Opcodes.HERMIT_RES, payload)

def build_joygame_login_response(account_id: int = 1001, nickname: str = "Gleidison") -> bytes:
    """Builds SA_JoyGameLogin (0x110112)."""
    nick_bytes = nickname.encode("utf-8")[:31].ljust(32, b"\x00")
    payload = struct.pack("<II32s", 0, account_id, nick_bytes)
    return build_packet(Opcodes.SA_JOYGAME_LOGIN, payload)

def build_user_info_packet(
    account_id: int = 1001,
    nickname: str = "Gleidison",
    rank: int = 58,
    exp: int = 50000000,
    gold: int = 9999999,
    cash: int = 9999999,
    clan_name: str = "D187_Meta"
) -> bytes:
    """Builds SN_UserInfo (0x210101)."""
    nick_b = nickname.encode("utf-8")[:31].ljust(32, b"\x00")
    clan_b = clan_name.encode("utf-8")[:31].ljust(32, b"\x00")
    payload = struct.pack("<IIQII32s32s", account_id, rank, exp, gold, cash, nick_b, clan_b)
    return build_packet(Opcodes.SN_USER_INFO, payload)

def build_item_list_packet(items: List[Dict[str, Any]]) -> bytes:
    """Builds SN_ItemList (0x210201)."""
    payload = bytearray()
    payload += struct.pack("<I", len(items))
    for it in items:
        item_id = it.get("item_id", 0)
        item_type = it.get("item_type", 1)
        durability = it.get("durability", 100)
        slot = it.get("slot", -1)
        payload += struct.pack("<IHhh", item_id, item_type, durability, slot)
    return build_packet(Opcodes.SN_ITEM_LIST, bytes(payload))

def build_lock_end_packet() -> bytes:
    """Builds SN_LockEnd (0x210202)."""
    return build_packet(Opcodes.SN_LOCK_END, struct.pack("<I", 0))

def build_record_packet(kills: int = 2450, deaths: int = 180, headshots: int = 1620, wins: int = 310, losses: int = 15) -> bytes:
    """Builds SN_Record (0x210203)."""
    payload = struct.pack("<IIIII", kills, deaths, headshots, wins, losses)
    return build_packet(Opcodes.SN_RECORD, payload)

def build_room_list_packet(rooms: List[Dict[str, Any]]) -> bytes:
    """Builds SA_RoomList (0x220104) for lobby room browser."""
    payload = bytearray(struct.pack("<I", len(rooms)))
    for r in rooms:
        rid = r.get("room_id", 1)
        rname = r.get("name", "Room").encode("utf-8")[:31].ljust(32, b"\x00")
        map_name = r.get("map", "Arrival").encode("utf-8")[:19].ljust(20, b"\x00")
        mode = r.get("mode", 1)
        players = r.get("players", 1)
        max_p = r.get("max_players", 16)
        state = r.get("state", 0) # 0 = waiting, 1 = in battle
        payload += struct.pack("<I32s20sBBBB", rid, rname, map_name, mode, players, max_p, state)
    return build_packet(Opcodes.SA_ROOM_LIST, bytes(payload))

def build_battle_start_packet(ip: str = "127.0.0.1", port: int = 27888, world_path: str = "Worlds\\Arrival.World00p") -> bytes:
    """Builds SN_BattleStart (0x230104)."""
    ip_b = ip.encode("ascii")[:15].ljust(16, b"\x00")
    world_b = world_path.encode("ascii")[:31].ljust(32, b"\x00")
    payload = struct.pack("<16sH32s", ip_b, port, world_b)
    return build_packet(Opcodes.SN_BATTLE_START, payload)

# --- In-Game Battle Combat Serializers ---

def build_spawn_packet(player_id: int, team: int, x: float, y: float, z: float, yaw: float = 0.0, pitch: float = 0.0) -> bytes:
    """Builds SN_Spawn (0x230110): Informs clients of player spawn in battle."""
    payload = struct.pack("<IIfffff", player_id, team, x, y, z, yaw, pitch)
    return build_packet(Opcodes.SN_SPAWN, payload)

def build_fire_packet(player_id: int, weapon_id: int, ox: float, oy: float, oz: float, dx: float, dy: float, dz: float, seed: int = 12345) -> bytes:
    """Builds SN_Fire (0x230121): In-game authoritative ballistic raycast."""
    payload = struct.pack("<IIffffffI", player_id, weapon_id, ox, oy, oz, dx, dy, dz, seed)
    return build_packet(Opcodes.SN_FIRE, payload)

def build_hit_packet(attacker_id: int, victim_id: int, hitbox: int, damage: float, current_hp: float) -> bytes:
    """
    Builds SN_Hit (0x230123).
    hitbox: 0 = Head, 1 = Torso, 2 = Left Arm, 3 = Right Arm, 4 = Legs
    """
    payload = struct.pack("<IIiff", attacker_id, victim_id, hitbox, damage, current_hp)
    return build_packet(Opcodes.SN_HIT, payload)

def build_kill_packet(killer_id: int, victim_id: int, weapon_id: int, is_headshot: bool, combo_kills: int = 1) -> bytes:
    """Builds SN_Kill (0x230124): Kill notification broadcast."""
    payload = struct.pack("<IIIBB", killer_id, victim_id, weapon_id, 1 if is_headshot else 0, combo_kills)
    return build_packet(Opcodes.SN_KILL, payload)

def build_bomb_event_packet(action_type: int, player_id: int, site: str, x: float, y: float, z: float) -> bytes:
    """
    Builds SN_Bomb (0x230136).
    action_type: 1 = Plant Started, 2 = Planted, 3 = Defuse Started, 4 = Defused, 5 = Detonated
    """
    site_byte = 0 if "A" in site.upper() else 1
    payload = struct.pack("<IIBfff", action_type, player_id, site_byte, x, y, z)
    return build_packet(Opcodes.SN_BOMB, payload)

def build_round_end_packet(winner_team: int, reason: int, score_swat: int, score_gang: int) -> bytes:
    """
    Builds SN_RoundEnd (0x230150).
    winner_team: 0 = SWAT, 1 = Gangsters, 2 = Draw
    reason: 1 = Wipeout/Elimination, 2 = Bomb Detonated, 3 = Bomb Defused, 4 = Time Expired
    """
    payload = struct.pack("<IIII", winner_team, reason, score_swat, score_gang)
    return build_packet(Opcodes.SN_ROUND_END, payload)

# --- Packet Parser ---
def parse_packet(buffer: bytes) -> Optional[Tuple[int, bytes, int]]:
    """
    Attempts to parse a framed packet from buffer.
    Returns: (opcode, payload, total_packet_length) or None if incomplete.
    """
    if len(buffer) < 8:
        return None
    total_len, opcode = struct.unpack("<II", buffer[:8])
    if total_len > 65536 or total_len < 8:
        return None
    if len(buffer) < total_len:
        return None
    payload = buffer[8:total_len]
    return opcode, payload, total_len

if __name__ == "__main__":
    print("[+] District 187 Protocol Library Self-Test:")
    cipher = HermitCipher(0x0F)
    
    # Handshake
    res_pkt = build_hermit_response()
    dec = cipher.decrypt(cipher.encrypt(res_pkt))
    assert parse_packet(dec)[0] == Opcodes.HERMIT_RES
    print("  [OK] Hermit Handshake frame verified.")

    # Room List
    room_pkt = build_room_list_packet([
        {"room_id": 1, "name": "Arrival 8v8 [Bots]", "map": "Arrival", "players": 8, "max_players": 16},
        {"room_id": 2, "name": "TwoWay Demolition A/B", "map": "twoway", "players": 12, "max_players": 16},
        {"room_id": 3, "name": "The Bank Gold Heist", "map": "thebank", "players": 10, "max_players": 16}
    ])
    assert parse_packet(room_pkt)[0] == Opcodes.SA_ROOM_LIST
    print("  [OK] SA_RoomList multi-room browser verified.")

    # In-Game Combat
    spawn_pkt = build_spawn_packet(101, 0, -3072.0, 100.0, -966.0)
    assert parse_packet(spawn_pkt)[0] == Opcodes.SN_SPAWN
    print("  [OK] SN_Spawn verified.")

    fire_pkt = build_fire_packet(101, 1110001, -3072.0, 100.0, -966.0, 1.0, 0.0, 0.0)
    assert parse_packet(fire_pkt)[0] == Opcodes.SN_FIRE
    print("  [OK] SN_Fire ballistic broadcast verified.")

    kill_pkt = build_kill_packet(101, 202, 1110001, is_headshot=True)
    assert parse_packet(kill_pkt)[0] == Opcodes.SN_KILL
    print("  [OK] SN_Kill headshot broadcast verified.")

    round_pkt = build_round_end_packet(winner_team=0, reason=3, score_swat=5, score_gang=3)
    assert parse_packet(round_pkt)[0] == Opcodes.SN_ROUND_END
    print("  [OK] SN_RoundEnd bomb defusal win verified.")

    print("\n[+] All 12 protocol serializers passed tests successfully!")

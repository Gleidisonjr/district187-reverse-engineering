#!/usr/bin/env python3
"""
District 187: Sin Streets (S2 Online / S2 Rebirth)
Hermit Protocol Dedicated Server Emulator & Packet Sniffer

Implements the authentic LithTech Jupiter EX Hermit TCP protocol:
- CRC32 stream encryption/decryption (IEEE 802.3 polynomial 0xEDB88320)
- Hermit Handshake state machine (0x20080 -> 0x20081 -> 0x20082 -> 0x20083)
- Scaleform / GameClient login handlers (CQ_JoyGameLogin -> SA_JoyGameLogin)

Author: Gleidison Carvalho & Antigravity (2026-11-02)
"""
import binascii
import datetime
import os
import socket
import struct
import sys
import threading
import time

try:
    sys.stdout.reconfigure(line_buffering=True)
except Exception:
    pass

LOG_DIR = r"targets\district-187\traffic"

# Packet IDs (Network Byte Order on wire - Ground Truth from GameClient.dll)
PACKET_HERMIT_HANDSHAKE_REQ = 0x20080
PACKET_HERMIT_HANDSHAKE_RES = 0x20081
PACKET_HERMIT_HANDSHAKE_ACK = 0x20082
PACKET_HERMIT_HANDSHAKE_PONG = 0x20083
PACKET_HERMIT_PING_KEEPALIVE = 0x20084
PACKET_HERMIT_PING = 0x20090
PACKET_HERMIT_DISCONNECT = 0x200A0

PACKET_CQ_LOGIN = 0x110101
PACKET_SA_LOGIN = 0x110102
PACKET_CQ_JOYGAME_LOGIN = 0x110111
PACKET_SA_JOYGAME_LOGIN = 0x110112
PACKET_CQ_NETMARBLE_LOGIN = 0x110121
PACKET_SA_NETMARBLE_LOGIN = 0x110122
PACKET_CQ_JOIN = 0x110124
PACKET_SA_JOIN = 0x110125
PACKET_SA_KEY = 0x110131

# ApexGuard / S2Rebirth Anti-Cheat Heartbeat
PACKET_APEX_HEARTBEAT_REQ = 0x5A0101
PACKET_APEX_HEARTBEAT_RES = 0x5A0102

# Result/Error Code at offset 0x12 (18) checked by IsPacketerrorMessage(int err, uint16 origin) at VA 0x10191740:
# test edi, edi -> je 0x1019176c (0 = NO ERROR). Note: 0x00A40221 is UI_SYS_ROOM_NeedWeaponChange error!
ACCOUNT_ID_SUCCESS = 0x00000000

# NLaunch Family (Disassembled from GameClient.dll 0x10194800 & 0x10132d10)
PACKET_SN_USER_INFO = 0x210101
PACKET_SN_RECORD = 0x210103
PACKET_SN_RANKING_INFO = 0x210105
PACKET_SN_ITEM_LIST = 0x210111
PACKET_SN_SLOT_INFO = 0x210113
PACKET_CQ_EQUIP_SLOT = 0x210114
PACKET_SN_LOCK_END = 0x210121
PACKET_SN_MAIN_WEAPON_LIST = 0x210122
PACKET_CQ_CHAT = 0x210151
PACKET_SN_CHAT = 0x210152

# NMatchup / Channel / Room Family
PACKET_SN_SERVER_INFO = 0x220101
PACKET_SN_CHANNEL_LIST = 0x220102
PACKET_CQ_ROOM_LIST = 0x220103
PACKET_SA_ROOM_LIST = 0x220104
PACKET_SN_GROUP_LIST = 0x220107
PACKET_SN_SERVER_LIST = 0x220108
PACKET_CQ_ENTER_USER = 0x220111
PACKET_SA_ENTER_USER = 0x220112
PACKET_SN_USER_LIST = 0x220113
PACKET_CQ_MOVE_SERVER = 0x220131
PACKET_SA_MOVE_SERVER = 0x220132
PACKET_CQ_QUICK_JOIN = 0x220161
PACKET_SA_QUICK_JOIN = 0x220162
PACKET_CQ_CREATE_ROOM = 0x220201
PACKET_SA_CREATE_ROOM = 0x220202
PACKET_SN_ROOM_LIST = 0x220204
PACKET_CQ_ENTER_ROOM = 0x220231
PACKET_SA_ENTER_ROOM = 0x220232
PACKET_CN_START_BUTTON = 0x220301

# NHosting / NBattle Family
PACKET_SN_BATTLE_START = 0x420310

# Standard IEEE 802.3 CRC32 lookup table (matching TheRaw.exe VA 0x802a58)
CRC_TABLE = []
for i in range(256):
    c = i
    for _ in range(8):
        if c & 1:
            c = 0xEDB88320 ^ (c >> 1)
        else:
            c = c >> 1
    CRC_TABLE.append(c)

def format_hex(data):
    lines = []
    for i in range(0, len(data), 16):
        chunk = data[i:i+16]
        hex_str = " ".join(f"{b:02x}" for b in chunk)
        ascii_str = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
        lines.append(f"  {i:04x}: {hex_str:<48}  {ascii_str}")
    return "\n".join(lines)

def log_packet(proto, client_addr, data, note=""):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    extra = f" ({note})" if note else ""
    print(f"\n[{timestamp}] [{proto}] {len(data)} bytes from {client_addr}{extra}")
    print(format_hex(data))

    os.makedirs(LOG_DIR, exist_ok=True)
    filename = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f") + f"_{proto}.bin"
    filepath = os.path.join(LOG_DIR, filename)
    try:
        with open(filepath, "wb") as f:
            f.write(data)
    except Exception:
        pass

def encrypt_hermit_packet(plain_pkt: bytes, key_byte: int = 0x0F) -> bytes:
    """
    Encrypts a Hermit packet:
    C[i] = P[i] ^ (CRC_TABLE[i & 0xFF] & 0xFF) ^ key_byte for i in [4, len)
    C[0:4] = CRC32(C[4:]) Big-Endian
    """
    buf = bytearray(plain_pkt)
    for i in range(4, len(buf)):
        tbl_byte = CRC_TABLE[i & 0xFF] & 0xFF
        buf[i] = plain_pkt[i] ^ tbl_byte ^ key_byte
    crc = binascii.crc32(buf[4:]) & 0xFFFFFFFF
    buf[0:4] = struct.pack('>I', crc)
    return bytes(buf)

def decrypt_hermit_packet(cipher_pkt: bytes, key_byte: int = 0x0F) -> tuple[bytes, bool]:
    """
    Decrypts a Hermit packet:
    P[i] = C[i] ^ (CRC_TABLE[i & 0xFF] & 0xFF) ^ key_byte for i in [4, len)
    Checks CRC32(C[4:]) == C[0:4]
    """
    if len(cipher_pkt) < 16:
        return cipher_pkt, False
    expected_crc = struct.unpack('>I', cipher_pkt[0:4])[0]
    actual_crc = binascii.crc32(cipher_pkt[4:]) & 0xFFFFFFFF
    crc_valid = (expected_crc == actual_crc)

    buf = bytearray(cipher_pkt)
    for i in range(4, len(buf)):
        tbl_byte = CRC_TABLE[i & 0xFF] & 0xFF
        buf[i] = cipher_pkt[i] ^ tbl_byte ^ key_byte
    return bytes(buf), crc_valid

def build_handshake_response_81(session_id: int, client_ts: int = 0, key_byte: int = 0x0F) -> bytes:
    """
    Constructs Handshake Response 0x20081 (32 bytes).
    Client requirements reverse engineered from TheRaw.exe (VA 0x004fd190):
    - PacketID = 0x20081 (Big Endian)
    - Length = 32 (Big Endian)
    - Session ID matching client session
    - Payload DWORD 0 (offset 0x10): Server Timestamp / Seed (Big Endian)
    - Payload DWORD 1 (offset 0x14): Echo of Client Timestamp (Big Endian).
      Client compares: dwDelay = client_now - DWORD 1.
      If dwDelay > 30000ms (timeout * 3), client disconnects!
    - Payload DWORD 2 (offset 0x18): 0x00000000
    - Payload DWORD 3 (offset 0x1c): Little-Endian key_byte (b'\x0f\x00\x00\x00').
      0x4fd1e6 reads DWORD 3 as native x86 little-endian:
      mov ecx, [ebx + 0x1c]; xor ecx, [ebx + 0x18]; call 0x5004d0.
      Must be 0x0000000F so session key byte is 0x0F!
    """
    server_seed = (client_ts + 1) & 0xFFFFFFFF
    dw0 = struct.pack('>I', server_seed)
    dw1 = struct.pack('>I', client_ts)
    dw2 = struct.pack('<I', 0)
    dw3 = struct.pack('<I', key_byte)
    payload = dw0 + dw1 + dw2 + dw3
    header = struct.pack('>HHII', 0, 32, session_id, PACKET_HERMIT_HANDSHAKE_RES)
    plain = b'\x00\x00\x00\x00' + header + payload
    return encrypt_hermit_packet(plain, key_byte)

def build_handshake_pong_83(session_id: int, key_byte: int = 0x0F) -> bytes:
    """
    Constructs Handshake Pong 0x20083 (20 bytes).
    Acknowledges 0x20082 and Ping packets.
    """
    payload = struct.pack('>I', 0)
    header = struct.pack('>HHII', 0, 20, session_id, PACKET_HERMIT_HANDSHAKE_PONG)
    plain = b'\x00\x00\x00\x00' + header + payload
    return encrypt_hermit_packet(plain, key_byte)

def build_apex_heartbeat_response(session_id: int, payload_data: bytes = b"", key_byte: int = 0x0F) -> bytes:
    """
    Constructs Apex / S2Rebirth Heartbeat Response 0x5A0102 (48 bytes: 16 header + 32 payload).
    GameClient.dll at 0x1058c310 copies 32 bytes (rep movsd with ecx=8) to shared memory [edi + 0x50]
    and increments the heartbeat counter at [edi + 0x40].
    """
    payload = bytearray(32)
    if payload_data:
        payload[:min(32, len(payload_data))] = payload_data[:32]
    header = struct.pack('>HHII', 0, 48, session_id, PACKET_APEX_HEARTBEAT_RES)
    plain = b'\x00\x00\x00\x00' + header + bytes(payload)
    return encrypt_hermit_packet(plain, key_byte)

def build_login_success_response(packet_id: int, session_id: int, account_id: int = ACCOUNT_ID_SUCCESS, key_byte: int = 0x0F) -> bytes:
    """
    Constructs an authentic SA_JoyGameLogin (0x110112), SA_Login (0x110102), or SA_Join (0x110125) packet (80 bytes).
    Handler at 0x100d74a0 / 0x100d7450 / 0x10030c90 calls IsPacketerrorMessage(edx, ecx) at 0x10191740:
    - Offset 0x10 (16): Origin = 0 (uint16 LE)
    - Offset 0x12 (18): ErrorCode = 0 (uint32 LE, 0 = NO ERROR)
    """
    total_len = 80
    payload = bytearray(64)
    struct.pack_into('<H', payload, 0, 0)  # Offset 16: Origin = 0
    struct.pack_into('<I', payload, 2, 0)  # Offset 18: ErrorCode = 0 (Success)

    header = struct.pack('>HHII', 0, total_len, session_id, packet_id)
    plain = b'\x00\x00\x00\x00' + header + bytes(payload)
    return encrypt_hermit_packet(plain, key_byte)

def build_hermit_packet(packet_id: int, session_id: int, payload: bytes, key_byte: int = 0x0F) -> bytes:
    total_len = 16 + len(payload)
    header = struct.pack('>HHII', 0, total_len, session_id, packet_id)
    plain = b'\x00\x00\x00\x00' + header + payload
    return encrypt_hermit_packet(plain, key_byte)

def get_user_data_from_db(username_hint: str = "gleidison") -> dict:
    """Queries user profile and stats from SQLite database."""
    import sqlite3
    db_path = os.path.join(r"targets\district-187\data\s2rebirth.db")
    default_user = {
        "id": 1,
        "username": "gleidison",
        "nickname": "Gleidison",
        "rank": 58,
        "exp": 50000000,
        "gold": 9999999,
        "cash": 9999999,
        "kills": 2450,
        "deaths": 180,
        "headshots": 1620,
        "wins": 310,
        "losses": 15
    }
    if not os.path.exists(db_path):
        return default_user
    try:
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute("SELECT id, username, nickname, rank_level, exp, gold, cash, kills, deaths, headshots, wins, losses FROM users WHERE username = ? OR nickname = ? LIMIT 1", (username_hint, username_hint))
        row = c.fetchone()
        if not row:
            c.execute("SELECT id, username, nickname, rank_level, exp, gold, cash, kills, deaths, headshots, wins, losses FROM users LIMIT 1")
            row = c.fetchone()
        conn.close()
        if row:
            return {
                "id": row[0],
                "username": row[1],
                "nickname": row[2],
                "rank": row[3],
                "exp": row[4],
                "gold": row[5],
                "cash": row[6],
                "kills": row[7],
                "deaths": row[8],
                "headshots": row[9],
                "wins": row[10],
                "losses": row[11]
            }
    except Exception as e:
        print(f"[!] DB Query Error: {e}")
    return default_user

def build_user_info_hermit(session_id: int, user_data: dict, account_id: int = ACCOUNT_ID_SUCCESS, key_byte: int = 0x0F) -> bytes:
    """
    SN_UserInfo (0x210101): Handler at 0x100D7A70 in CLoginScene.
    Expects:
    - Offset 0x10 (payload +0): 25-byte null-terminated Nickname string
    - Offset 0x29 (payload +25): 25-byte null-terminated Clan Name string
    """
    nickname = user_data.get("nickname", "Gleidison")
    nick_b = nickname.encode("ascii", "ignore")[:24].ljust(25, b"\x00")
    clan_b = b"S2_Rebirth\x00".ljust(25, b"\x00")
    payload = bytearray(80)
    payload[0:25] = nick_b
    payload[25:50] = clan_b
    return build_hermit_packet(PACKET_SN_USER_INFO, session_id, bytes(payload), key_byte)

def build_ranking_info_hermit(session_id: int, user_data: dict, key_byte: int = 0x0F) -> bytes:
    """
    SN_RankingInfo (0x210105): Handler at 0x10031110.
    Reads dword[eax + 0x16] (payload +6) and dword[eax + 0x1a] (payload +10).
    """
    rank = user_data.get("rank", 58)
    exp = user_data.get("exp", 50000000)
    payload = bytearray(16)
    struct.pack_into("<II", payload, 6, rank, exp)
    return build_hermit_packet(PACKET_SN_RANKING_INFO, session_id, bytes(payload), key_byte)

def build_item_list_hermit(session_id: int, key_byte: int = 0x0F) -> bytes:
    """
    SN_ItemList (0x210111): Handler at 0x10031000 -> 0x10082B20.
    - Offset 0x10 (payload +0): uint8 page_flag (0 = clear & populate)
    - Offset 0x11 (payload +1): uint8 item_count
    - Offset 0x12 (payload +2): 27-byte (0x1B) item entries: <QBIIIHI
      (uint64 uid, uint8 flag, uint32 f9c, uint32 fa0, uint32 fa4, uint16 fa8, uint32 item_id)
    """
    import sqlite3
    db_path = os.path.join(r"targets\district-187\data\s2rebirth.db")
    gids = []
    if os.path.exists(db_path):
        try:
            conn = sqlite3.connect(db_path)
            c = conn.cursor()
            c.execute("SELECT group_id FROM weapons ORDER BY damage DESC LIMIT 32")
            gids = [int(row[0]) for row in c.fetchall() if row[0] is not None]
            conn.close()
        except Exception:
            pass

    if not gids:
        gids = [1110001, 1120001, 1130001, 1140001]

    count = min(len(gids), 32)
    payload = bytearray(struct.pack("<BB", 0, count))
    for idx, gid in enumerate(gids[:count], start=1):
        # 27 bytes: uid(Q=8) + flag(B=1) + f9c(I=4) + fa0(I=4) + fa4(I=4) + fa8(H=2) + item_id(I=4) = 27B
        payload += struct.pack("<QBIIIHI", idx, 1, 100, 0, 0, 1, gid)
    return build_hermit_packet(PACKET_SN_ITEM_LIST, session_id, bytes(payload), key_byte)

def build_record_hermit(session_id: int, user_data: dict, key_byte: int = 0x0F) -> bytes:
    """
    SN_Record (0x210103): Handler at 0x10031140 -> 0x100836E0.
    Reads user combat and economy stats up to packet offset 0xD6 (payload +198).
    """
    kills = user_data.get("kills", 2450)
    deaths = user_data.get("deaths", 180)
    headshots = user_data.get("headshots", 1620)
    wins = user_data.get("wins", 310)
    losses = user_data.get("losses", 15)
    gold = user_data.get("gold", 9999999)
    cash = user_data.get("cash", 9999999)
    exp = user_data.get("exp", 50000000)

    payload = bytearray(224)
    # Populate core stats across the record block read by 0x100836E0
    struct.pack_into("<IIIIIIII", payload, 0, wins, losses, kills, deaths, headshots, gold, cash, exp)
    return build_hermit_packet(PACKET_SN_RECORD, session_id, bytes(payload), key_byte)

def build_lock_end_hermit(session_id: int, key_byte: int = 0x0F) -> bytes:
    """
    SN_LockEnd (0x210121): Handler at 0x10032F30.
    Checks IsPacketerrorMessage(dword[0x12], word[0x10]).
    When both are 0, calls ChangeScene(0) (CServerListScene) or ChangeScene(1) (CChannelListScene)!
    """
    return build_hermit_packet(PACKET_SN_LOCK_END, session_id, b"\x00" * 16, key_byte)

def build_group_list_hermit(session_id: int, key_byte: int = 0x0F) -> bytes:
    """
    SN_GroupList (0x220107): Handler at 0x100326F0.
    - Offset 0x10 (payload +0): uint8 unk = 0
    - Offset 0x11 (payload +1): uint8 group_count = 1
    - Offset 0x12 (payload +2): count entries of 66 bytes (0x42):
      +0..4 (5B): group ID ("G1\x00\x00\x00")
      +5..9 (5B): group code ("G1\x00\x00\x00")
      +10..65 (56B): group name ("District 187 Official\x00...")
    """
    entry = bytearray(66)
    entry[0:5] = b"G1\x00\x00\x00"
    entry[5:10] = b"G1\x00\x00\x00"
    name = b"District 187 Official\x00"
    entry[10:10+len(name)] = name
    payload = bytearray(struct.pack("<BB", 0, 1)) + entry
    return build_hermit_packet(PACKET_SN_GROUP_LIST, session_id, bytes(payload), key_byte)

def build_server_list_hermit(session_id: int, key_byte: int = 0x0F) -> bytes:
    """
    SN_ServerList (0x220108): Handler at 0x10032810.
    - Offset 0x10 (payload +0): uint8 unk = 0
    - Offset 0x11 (payload +1): uint8 server_count = 1
    - Offset 0x12 (payload +2): count entries of 20 bytes (0x14):
      +0..4 (5B): server ID ("S2\x00\x00\x00")
      +5..9 (5B): group code ("G1\x00\x00\x00") - matches group_code of 0x220107!
      +10..19 (10B): server code ("S2\x00...") - matches server_code of 0x220101!
    """
    entry = bytearray(20)
    entry[0:5] = b"S2\x00\x00\x00"
    entry[5:10] = b"G1\x00\x00\x00"
    entry[10:12] = b"S2"
    payload = bytearray(struct.pack("<BB", 0, 1)) + entry
    return build_hermit_packet(PACKET_SN_SERVER_LIST, session_id, bytes(payload), key_byte)

def build_server_info_hermit(session_id: int, port: int = 12000, key_byte: int = 0x0F) -> bytes:
    """
    SN_ServerInfo (0x220101): Handler at 0x1011EB80 -> 0x10074F30 -> 0x100735F0.
    - Offset 0x10 (payload +0): uint8 flag = 0
    - Offset 0x11 (payload +1): uint8 server_count = 1
    - Offset 0x12 (payload +2): 98-byte (0x62) server entry:
      +0..4: 5B ID ("S2\x00\x00\x00")
      +5..9: 5B server_code ("S2\x00\x00\x00") - matched against SN_ServerList!
      +16..31: 16B IP string ("127.0.0.1\x00")
      +26..79: 54B Server Name ("District 187 Dedicated [BR]\x00")
      +81..84 (0x51): uint32 server_id (1)
      +85..86 (0x55): uint16 port (12000)
      +87..88 (0x57): uint16 cur_users (12)
      +89..90 (0x59): uint16 max_users (200)
      +91 (0x5B): uint8 skip_flag (0 = active/visible)
      +92 (0x5C): uint8 server_type (1 = normal)
    """
    entry = bytearray(98)
    entry[0:5] = b"S2\x00\x00\x00"
    entry[5:10] = b"S2\x00\x00\x00"
    ip_b = b"127.0.0.1\x00"
    entry[16:16+len(ip_b)] = ip_b
    name_b = b"District 187 Dedicated [BR]\x00"
    entry[26:26+len(name_b)] = name_b
    struct.pack_into("<IHHHBB", entry, 81, 1, port, 12, 200, 0, 1)

    payload = bytearray(struct.pack("<BB", 0, 1)) + entry
    return build_hermit_packet(PACKET_SN_SERVER_INFO, session_id, bytes(payload), key_byte)

def build_channel_list_hermit(session_id: int, key_byte: int = 0x0F) -> bytes:
    """
    SN_ChannelList (0x220102): Handler at 0x100BA790 -> 0x100743A0 -> 0x100742C0 -> 0x10073BF0.
    - Offset 0x10 (payload +0): uint8 flag = 0
    - Offset 0x11 (payload +1): uint8 channel_count
    - Offset 0x12..0x16 (payload +2..+6): 5-byte null-terminated server_code: b"S2\x00\x00\x00"
    - Offset 0x17 (payload +7): 57-byte (0x39) channel entries:
      +0: uint8 channel_id
      +1: uint16 cur_users
      +3: uint16 max_users
      +5: uint8 channel_type
      +10..13 (0x0A): uint32 status_flag (0)
      +14 (0x0E): 43-byte null-terminated channel name
    """
    channels = [
        (1, 12, 100, b"Channel 1 - Free [Bots & LAN]\x00"),
        (2, 8, 100, b"Channel 2 - Competitive [8v8]\x00"),
        (3, 4, 100, b"Channel 3 - Clan Match [VIP]\x00"),
    ]
    payload = bytearray(struct.pack("<BB5s", 0, len(channels), b"S2\x00\x00\x00"))
    for cid, cur_u, max_u, cname in channels:
        entry = bytearray(57)
        struct.pack_into("<BHHBI", entry, 0, cid, cur_u, max_u, 0, 0)
        entry[14:14+len(cname)] = cname[:42]
        payload += entry
    return build_hermit_packet(PACKET_SN_CHANNEL_LIST, session_id, bytes(payload), key_byte)

def build_enter_channel_response(session_id: int, channel_id: int = 1, key_byte: int = 0x0F) -> bytes:
    """
    SA_EnterUser (0x220112): Handler at 0x100BA640.
    - Offset 0x10 (payload +0): uint16 origin = 0
    - Offset 0x12 (payload +2): uint32 error_code = 0 (0 = NO ERROR)
    - Offset 0x18 (payload +8): uint8 channel_id
    Calls ChangeScene(2) (CLobbyScene)!
    """
    payload = bytearray(16)
    struct.pack_into("<HI", payload, 0, 0, 0)
    payload[8] = channel_id & 0xFF
    return build_hermit_packet(PACKET_SA_ENTER_USER, session_id, bytes(payload), key_byte)

def build_move_server_response(session_id: int, key_byte: int = 0x0F) -> bytes:
    """
    SA_MoveServer (0x220132): Handler at 0x100324C0.
    - payload[0:2]: uint16 origin = 0
    - payload[2:6]: uint32 err = 0 (Success)
    - payload[6:10]: uint32 token1 = 1
    - payload[10:14]: uint32 token2 = 1
    """
    payload = struct.pack("<HIII", 0, 0, 1, 1)
    return build_hermit_packet(PACKET_SA_MOVE_SERVER, session_id, payload, key_byte)

def build_room_list_hermit(session_id: int, key_byte: int = 0x0F) -> bytes:
    """
    SN_RoomList (0x220204): Handler at 0x100D59F0 -> 0x100D3580.
    - Offset 0x10 (payload +0): uint8 unk = 0
    - Offset 0x11 (payload +1): uint16 room_count
    - Offset 0x13 (payload +3): 7-byte room entries (with bitmask = 0):
      +0: uint16 room_id
      +2: uint8 cmd = 1 (Add/Active)
      +3: uint16 unk = 0
      +5: uint16 bitmask = 0
    """
    room_ids = [1, 2, 3, 4, 5]
    payload = bytearray(struct.pack("<BH", 0, len(room_ids)))
    for rid in room_ids:
        payload += struct.pack("<HBH H", rid, 1, 0, 0)
    return build_hermit_packet(PACKET_SN_ROOM_LIST, session_id, bytes(payload), key_byte)

def build_create_room_response(session_id: int, room_id: int = 1, room_name: str = "Arrival 8v8 [Bots & VIP]", key_byte: int = 0x0F) -> bytes:
    """SA_CreateRoom (0x220202): Response to CQ_CreateRoom."""
    rname = room_name.encode("utf-8")[:31].ljust(32, b"\x00")
    payload = struct.pack("<II32sI", 0, room_id, rname, 1)
    return build_hermit_packet(PACKET_SA_CREATE_ROOM, session_id, payload, key_byte)

def build_battle_start_hermit(session_id: int, map_name: str = "Arrival.World00p", port: int = 27888, key_byte: int = 0x0F) -> bytes:
    """SN_BattleStart (0x230104): Directs client to connect to combat server."""
    if not map_name.endswith(".World00p"):
        map_name = f"{map_name}.World00p"
    ip_b = b"127.0.0.1\x00".ljust(16, b"\x00")
    map_rel = f"Worlds\\{map_name}".encode("ascii")[:31].ljust(32, b"\x00")
    payload = struct.pack("<16sH32s", ip_b, port, map_rel)
    return build_hermit_packet(PACKET_SN_BATTLE_START, session_id, payload, key_byte)

class HermitClientSession:
    def __init__(self, sock, addr, active_map: str = "Arrival.World00p"):
        self.sock = sock
        self.addr = addr
        self.session_id = 0x04034992
        self.key_byte = 0x0F
        self.recv_buf = bytearray()
        self.state = "HANDSHAKE"
        self.active_map = active_map

    def handle(self):
        print(f"[+] Client connected from {self.addr}")
        try:
            while True:
                chunk = self.sock.recv(4096)
                if not chunk:
                    print(f"[-] Client {self.addr} closed connection.")
                    break
                self.recv_buf.extend(chunk)
                self.process_buffer()
        except Exception as e:
            print(f"[-] TCP Connection error with {self.addr}: {e}")
        finally:
            try:
                self.sock.close()
            except Exception:
                pass

    def process_buffer(self):
        while len(self.recv_buf) >= 16:
            # First try decrypting the 16-byte header to find the packet length
            expected_crc = struct.unpack('>I', self.recv_buf[0:4])[0]
            
            # The length is at offset 6..8 of the decrypted header (Big-Endian)
            tbl_b6 = CRC_TABLE[6] & 0xFF
            tbl_b7 = CRC_TABLE[7] & 0xFF
            len_b6 = self.recv_buf[6] ^ tbl_b6 ^ self.key_byte
            len_b7 = self.recv_buf[7] ^ tbl_b7 ^ self.key_byte
            pkt_len = (len_b6 << 8) | len_b7

            if pkt_len < 16 or pkt_len > 4096:
                # Fallback: check if client sent a raw 20-byte handshake
                if len(self.recv_buf) == 20:
                    pkt_len = 20
                else:
                    print(f"[!] Invalid packet length decoded: {pkt_len}, raw hex: {self.recv_buf[:16].hex()}")
                    # Skip 1 byte to re-sync
                    self.recv_buf.pop(0)
                    continue

            if len(self.recv_buf) < pkt_len:
                # Wait for more bytes to complete the packet
                break

            # Extract full packet
            raw_packet = bytes(self.recv_buf[:pkt_len])
            self.recv_buf = self.recv_buf[pkt_len:]

            self.process_packet(raw_packet)

    def process_packet(self, cipher_packet):
        plain_packet, crc_ok = decrypt_hermit_packet(cipher_packet, self.key_byte)
        if not crc_ok:
            print(f"[!] Warning: Packet CRC validation failed for {len(cipher_packet)} bytes from {self.addr}!")
        
        _, flags, pkt_len, session_id, pkt_id = struct.unpack('>IHHII', plain_packet[:16])
        if session_id != 0:
            self.session_id = session_id

        log_packet("TCP", self.addr, cipher_packet, f"PktID=0x{pkt_id:X}, Len={pkt_len}, Sess=0x{session_id:X}")
        print(f"    [Decrypted Header] Flags=0x{flags:X}, Length={pkt_len}, Session=0x{session_id:X}, PacketID=0x{pkt_id:X}")

        # 1. Hermit Handshake Step 1 (Client Request -> Server Response 0x20081)
        if pkt_id == PACKET_HERMIT_HANDSHAKE_REQ:
            client_ts = struct.unpack('>I', plain_packet[16:20])[0] if len(plain_packet) >= 20 else 0
            print(f"[+] Hermit Handshake Step 1 (0x20080) received! Client TS: {client_ts}. Sending 0x20081 response...")
            resp = build_handshake_response_81(self.session_id, client_ts, self.key_byte)
            self.sock.sendall(resp)
            print(f"[+] Dispatched Handshake Response 0x20081 ({len(resp)} bytes)")

        # 2. Hermit Handshake Step 2 (Client ACK 0x20082 -> Server Pong 0x20083)
        elif pkt_id == PACKET_HERMIT_HANDSHAKE_ACK:
            print(f"[+] Hermit Handshake Step 2 (0x20082) received! Establishing session...")
            self.state = "ONLINE"
            resp = build_handshake_pong_83(self.session_id, self.key_byte)
            self.sock.sendall(resp)
            print(f"[+] Dispatched Handshake Pong 0x20083 ({len(resp)} bytes). Session ESTABLISHED!")

        # 3. Hermit Ping (0x20090 or 0x20084 -> Pong 0x20083)
        elif pkt_id == PACKET_HERMIT_PING or pkt_id == PACKET_HERMIT_PING_KEEPALIVE:
            print(f"[+] Hermit Keepalive Ping (0x{pkt_id:X}) received. Sending Pong 0x20083...")
            resp = build_handshake_pong_83(self.session_id, self.key_byte)
            self.sock.sendall(resp)

        # 4. Apex / S2Rebirth Heartbeat (0x5A0101 -> 0x5A0102)
        elif pkt_id == PACKET_APEX_HEARTBEAT_REQ:
            payload_data = plain_packet[16:]
            resp = build_apex_heartbeat_response(self.session_id, payload_data, self.key_byte)
            self.sock.sendall(resp)
            print(f"[+] Dispatched Apex Heartbeat Pong 0x5A0102 ({len(resp)} bytes)")

        # 5. CQ_JoyGameLogin (0x110111) / CQ_Login (0x110101) / CQ_NetmarbleLogin (0x110121)
        elif pkt_id in (PACKET_CQ_JOYGAME_LOGIN, PACKET_CQ_LOGIN, PACKET_CQ_NETMARBLE_LOGIN):
            if pkt_id == PACKET_CQ_JOYGAME_LOGIN:
                login_type = "CQ_JoyGameLogin"
                resp_pkt_id = PACKET_SA_JOYGAME_LOGIN
            elif pkt_id == PACKET_CQ_NETMARBLE_LOGIN:
                login_type = "CQ_NetmarbleLogin"
                resp_pkt_id = PACKET_SA_NETMARBLE_LOGIN
            else:
                login_type = "CQ_Login"
                resp_pkt_id = PACKET_SA_LOGIN
            
            # Extract username hint from offset 16 if present
            username_hint = "gleidison"
            if len(plain_packet) > 16:
                try:
                    raw_user = plain_packet[16:48].split(b'\x00')[0]
                    decoded = raw_user.decode('utf-8', 'ignore').strip()
                    if decoded:
                        username_hint = decoded
                except Exception:
                    pass

            user_data = get_user_data_from_db(username_hint)
            print(f"[+] {login_type} (0x{pkt_id:X}) received for '{username_hint}'! Authenticating as '{user_data['nickname']}' (Rank {user_data['rank']})...")
            
            # 1. Login Response (Origin=0, ErrorCode=0 -> No Error at 0x10191740)
            resp = build_login_success_response(resp_pkt_id, self.session_id, account_id=0, key_byte=self.key_byte)
            self.sock.sendall(resp)
            print(f"[+] Dispatched SA_Login 0x{resp_pkt_id:X} ({len(resp)} bytes, Origin=0, ErrorCode=0)!")

            # 2. Dispatch User Info (0x210101: 25B Nickname + 25B ClanName in CLoginScene)
            uinfo = build_user_info_hermit(self.session_id, user_data, account_id=0, key_byte=self.key_byte)
            self.sock.sendall(uinfo)
            print(f"[+] Dispatched SN_UserInfo 0x210101 (Nickname='{user_data['nickname']}')!")

            # 3. Dispatch Ranking Info (0x210105: Rank + Exp)
            rinfo = build_ranking_info_hermit(self.session_id, user_data, key_byte=self.key_byte)
            self.sock.sendall(rinfo)
            print(f"[+] Dispatched SN_RankingInfo 0x210105 (Rank {user_data['rank']}, Exp {user_data['exp']:,})!")

            # 4. Dispatch Item List (0x210111: 27-byte item entries from s2rebirth.db)
            ilist = build_item_list_hermit(self.session_id, key_byte=self.key_byte)
            self.sock.sendall(ilist)
            print(f"[+] Dispatched SN_ItemList 0x210111 ({len(ilist)} bytes, 27B/item)!")

            # 5. Dispatch Record Stats (0x210103: 224-byte stats block)
            rec = build_record_hermit(self.session_id, user_data, key_byte=self.key_byte)
            self.sock.sendall(rec)
            print(f"[+] Dispatched SN_Record 0x210103 ({user_data['kills']} Kills, {user_data['headshots']} Headshots, {user_data['wins']} Wins)!")

            # 6. Pre-populate Groups, Servers and Channels in global manager
            glist = build_group_list_hermit(self.session_id, key_byte=self.key_byte)
            self.sock.sendall(glist)
            slist = build_server_list_hermit(self.session_id, key_byte=self.key_byte)
            self.sock.sendall(slist)
            sinfo = build_server_info_hermit(self.session_id, port=12000, key_byte=self.key_byte)
            self.sock.sendall(sinfo)
            clist = build_channel_list_hermit(self.session_id, key_byte=self.key_byte)
            self.sock.sendall(clist)
            print(f"[+] Dispatched SN_GroupList 0x220107, SN_ServerList 0x220108, SN_ServerInfo 0x220101 & SN_ChannelList 0x220102!")

            # 7. Dispatch LockEnd (0x210121: Calls ChangeScene(0) out of LoginScene!)
            lend = build_lock_end_hermit(self.session_id, key_byte=self.key_byte)
            self.sock.sendall(lend)
            print(f"[+] Dispatched SN_LockEnd 0x210121 -> Client transitioned out of LoginScene to ServerList (Scene[0])!")

            # 8. Re-send Group, Server & Channel lists now that CServerListScene is active
            self.sock.sendall(glist)
            self.sock.sendall(slist)
            self.sock.sendall(sinfo)
            self.sock.sendall(clist)

        # 5b. CQ_Join (0x110124) -> SA_Join (0x110125) + SN_ChannelList (0x220102) + SN_LockEnd (0x210121)
        elif pkt_id == PACKET_CQ_JOIN:
            print(f"[+] CQ_Join (0x110124) received (Server Selection)! Sending SA_Join + SN_ChannelList + SN_LockEnd...")
            resp = build_login_success_response(PACKET_SA_JOIN, self.session_id, account_id=0, key_byte=self.key_byte)
            self.sock.sendall(resp)
            clist = build_channel_list_hermit(self.session_id, key_byte=self.key_byte)
            self.sock.sendall(clist)
            lend = build_lock_end_hermit(self.session_id, key_byte=self.key_byte)
            self.sock.sendall(lend)
            print(f"[+] Dispatched SA_Join 0x110125 + SN_ChannelList 0x220102 + SN_LockEnd 0x210121 -> ChannelList (Scene[1])!")

        # 5c. CQ_MoveServer (0x220131) -> SA_MoveServer (0x220132)
        elif pkt_id == PACKET_CQ_MOVE_SERVER:
            print(f"[+] CQ_MoveServer (0x220131) received! Sending SA_MoveServer...")
            resp = build_move_server_response(self.session_id, key_byte=self.key_byte)
            self.sock.sendall(resp)
            print(f"[+] Dispatched SA_MoveServer 0x220132!")

        # 6. CQ_EnterUser (0x220111) -> SA_EnterUser (0x220112) [Channel Navigation]
        elif pkt_id == PACKET_CQ_ENTER_USER:
            channel_id = plain_packet[16] if len(plain_packet) > 16 else 1
            print(f"[+] CQ_EnterUser (0x{pkt_id:X}) received for Channel {channel_id}! Entering Lobby (Scene[2])...")
            resp = build_enter_channel_response(self.session_id, channel_id=channel_id, key_byte=self.key_byte)
            self.sock.sendall(resp)
            rlist = build_room_list_hermit(self.session_id, key_byte=self.key_byte)
            self.sock.sendall(rlist)
            print(f"[+] Dispatched SA_EnterUser 0x220112 (Channel {channel_id}) + SN_RoomList 0x220204!")

        # CQ_RoomList (0x220103) -> SN_RoomList (0x220204) [Lobby Browser]
        elif pkt_id == PACKET_CQ_ROOM_LIST:
            print(f"[+] CQ_RoomList (0x220103) received! Sending available rooms...")
            resp = build_room_list_hermit(self.session_id, key_byte=self.key_byte)
            self.sock.sendall(resp)
            print(f"[+] Dispatched SN_RoomList 0x220204 (5 active multi-map rooms)!")

        # 7. CQ_CreateRoom (0x220201) -> SA_CreateRoom (0x220202) [Room Creation]
        elif pkt_id == PACKET_CQ_CREATE_ROOM:
            print(f"[+] CQ_CreateRoom (0x220201) received! Creating Match Room...")
            resp = build_create_room_response(self.session_id, room_id=1, room_name=f"{self.active_map} 8v8 [Bots & VIP]", key_byte=self.key_byte)
            self.sock.sendall(resp)
            print(f"[+] Dispatched SA_CreateRoom (Room 1: {self.active_map} 8v8 [Bots & VIP])!")

        # 7b. CQ_EnterRoom (0x220231) -> SA_EnterRoom (0x220232)
        elif pkt_id == PACKET_CQ_ENTER_ROOM:
            room_id = struct.unpack('<H', plain_packet[16:18])[0] if len(plain_packet) >= 18 else 1
            print(f"[+] CQ_EnterRoom (0x220231) received for Room {room_id}!")
            payload = struct.pack("<HIH", 0, 0, room_id)
            resp = build_hermit_packet(PACKET_SA_ENTER_ROOM, self.session_id, payload, key_byte=self.key_byte)
            self.sock.sendall(resp)
            print(f"[+] Dispatched SA_EnterRoom 0x220232 for Room {room_id}!")

        # 7c. CQ_QuickJoin (0x220161) -> SA_QuickJoin (0x220162)
        elif pkt_id == PACKET_CQ_QUICK_JOIN:
            print(f"[+] CQ_QuickJoin (0x220161) received! Directing to Room 1...")
            payload = struct.pack("<HIH", 0, 0, 1)
            resp = build_hermit_packet(PACKET_SA_QUICK_JOIN, self.session_id, payload, key_byte=self.key_byte)
            self.sock.sendall(resp)
            print(f"[+] Dispatched SA_QuickJoin 0x220162 (Room 1)!")

        # 8. CN_StartButton (0x220301) -> SN_BattleStart (0x420310) [Match Trigger]
        elif pkt_id == PACKET_CN_START_BUTTON:
            print(f"[+] CN_StartButton (0x220301) received! Launching Battle on {self.active_map}...")
            resp = build_battle_start_hermit(self.session_id, map_name=self.active_map, key_byte=self.key_byte)
            self.sock.sendall(resp)
            print(f"[+] Dispatched SN_BattleStart -> Directing client to 127.0.0.1:27888 ({self.active_map})!")

        # 9. CQ_Chat (0x210151) -> Slash Command Processor (/map, /bots, /give, /mmr, /loadout, /clan) + SN_Chat (0x210152)
        elif pkt_id == PACKET_CQ_CHAT:
            raw_msg = plain_packet[16:].split(b"\x00")[0].decode("utf-8", errors="ignore").strip() or "/help"
            try:
                from d187_lobby_extensions import LobbyExtensionService
                ext = LobbyExtensionService()
                cmd_res = ext.process_chat_command("Gleidison", raw_msg)
                if "active_map" in cmd_res:
                    self.active_map = cmd_res["active_map"]
                chat_payload = ext.build_sn_chat_packet(cmd_res["sender"], cmd_res["reply"])
            except Exception as e:
                chat_payload = f"[SISTEMA]: {raw_msg}".encode("utf-8")[:128].ljust(168, b"\x00")
            resp = build_hermit_packet(PACKET_SN_CHAT, self.session_id, chat_payload, self.key_byte)
            self.sock.sendall(resp)
            print(f"[+] Processed CQ_Chat ('{raw_msg}') -> Dispatched SN_Chat (0x210152)!")

        # 10. CQ_EquipSlot (0x210114) -> Persistent Loadout Slot Update + SN_SlotInfo (0x210113)
        elif pkt_id == PACKET_CQ_EQUIP_SLOT:
            slot_idx = plain_packet[16] if len(plain_packet) > 16 else 0
            slot_payload = bytearray(244)
            struct.pack_into("<B", slot_payload, 0, slot_idx)
            resp = build_hermit_packet(PACKET_SN_SLOT_INFO, self.session_id, bytes(slot_payload), self.key_byte)
            self.sock.sendall(resp)
            print(f"[+] Processed CQ_EquipSlot (Slot {slot_idx}) -> Dispatched SN_SlotInfo (0x210113)!")

        else:
            print(f"[?] Unknown / Unhandled Hermit Packet ID: 0x{pkt_id:X}")
            # Send general success / pong if in doubt
            resp = build_handshake_pong_83(self.session_id, self.key_byte)
            try:
                self.sock.sendall(resp)
            except Exception:
                pass

def start_tcp_server(port=12000, active_map="Arrival.World00p"):
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # Windows: SO_REUSEADDR permits several servers on one port (stale instances answer clients).
    # SO_EXCLUSIVEADDRUSE guarantees a single listener.
    if os.name == "nt":
        server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
    else:
        server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        server_sock.bind(("0.0.0.0", port))
    except OSError as e:
        print(f"[FATAL] Port {port} already in use by another server instance: {e}")
        sys.exit(1)
    server_sock.listen(10)
    print(f"=====================================================================")
    print(f"  District 187: Sin Streets — Hermit Dedicated Server Emulator")
    print(f"  Listening on TCP 0.0.0.0:{port}")
    print(f"  Active Battle Map: {active_map}")
    print(f"  Protocol: Hermit Jupiter EX (CRC32 Stream Cipher, Key=0x0F)")
    print(f"=====================================================================")
    while True:
        try:
            client_sock, client_addr = server_sock.accept()
            session = HermitClientSession(client_sock, client_addr, active_map=active_map)
            thread = threading.Thread(target=session.handle, daemon=True)
            thread.start()
        except Exception as e:
            print(f"[-] Accept loop error: {e}")
            break

def start_udp_listener(port=12000):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("0.0.0.0", port))
    print(f"[+] UDP Listener active on 0.0.0.0:{port}")
    while True:
        try:
            data, addr = sock.recvfrom(65535)
            log_packet("UDP", addr, data, "UDP Datagram")
        except Exception as e:
            break

def main():
    import argparse
    parser = argparse.ArgumentParser(description="District 187 Hermit Protocol Dedicated Server")
    parser.add_argument("--port", type=int, default=12000, help="Server port (default: 12000)")
    parser.add_argument("--map", default="Arrival.World00p", help="Active battle map (default: Arrival.World00p)")
    args = parser.parse_args()

    active_map = args.map if args.map.endswith(".World00p") else f"{args.map}.World00p"
    udp_thread = threading.Thread(target=start_udp_listener, args=(args.port,), daemon=True)
    udp_thread.start()
    start_tcp_server(args.port, active_map=active_map)

if __name__ == "__main__":
    main()

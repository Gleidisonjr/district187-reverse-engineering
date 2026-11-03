#!/usr/bin/env python3
"""
District 187: Sin Streets - Core Network Protocol & Packet Serialization Library
Handles:
  1. Hermit Stream Cipher (IEEE 802.3 CRC32 XOR mask).
  2. Packet framing (Opcode, Payload Length, Body).
  3. Binary serializers/deserializers for Handshake, Account, Launch, Lobby, and Battle packets.
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
    CQ_CREATE_ROOM   = 0x220201
    SA_CREATE_ROOM   = 0x220202
    SN_ROOM_LIST     = 0x220203
    CQ_LEAVE_ROOM    = 0x220204
    SA_LEAVE_ROOM    = 0x220205
    CN_START_BUTTON  = 0x220301

    # NBattle Family (0x23xxxx)
    SN_BATTLE_START  = 0x230104
    SN_KILL          = 0x230124
    SN_BOMB          = 0x230136
    SN_CAPTURE       = 0x230142
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
    # 0x20081 response payload: 16 bytes auth challenge token + server flag
    payload = b"\x01\x00\x00\x00\xaa\xbb\xcc\xdd\xee\xff\x00\x11\x22\x33\x44\x55"
    return build_packet(Opcodes.HERMIT_RES, payload)

def build_joygame_login_response(account_id: int = 1001, nickname: str = "Gleidison") -> bytes:
    """
    Builds SA_JoyGameLogin (0x110112).
    Payload:
      ResultCode: uint32 (0 = SUCCESS, clears Scaleform loading flag at 0x100d74db)
      AccountID: uint32
      Nickname: 32 bytes (UTF-8 / ASCII null-padded)
    """
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
    """
    Builds tPacket_NLaunch_NLock_SN_UserInfo (0x210101).
    Struct:
      AccountID (uint32)
      Rank (uint32) - 1 to 58 (General of the Army)
      Experience (uint64)
      Gold (uint32)
      Cash (uint32)
      Nickname (32 bytes string)
      ClanName (32 bytes string)
    """
    nick_b = nickname.encode("utf-8")[:31].ljust(32, b"\x00")
    clan_b = clan_name.encode("utf-8")[:31].ljust(32, b"\x00")
    payload = struct.pack("<IIQII32s32s", account_id, rank, exp, gold, cash, nick_b, clan_b)
    return build_packet(Opcodes.SN_USER_INFO, payload)

def build_item_list_packet(items: List[Dict[str, Any]]) -> bytes:
    """
    Builds tPacket_NLaunch_NLock_SN_ItemList (0x210201).
    Struct:
      ItemCount: uint32
      Array of:
        ItemID: uint32
        ItemType: uint16
        Durability / Quantity: uint16
        SlotEquipped: int16 (-1 = inventory, 0 = primary, 1 = secondary, 2 = melee, 3 = grenade)
    """
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
    """
    Builds tPacket_NLaunch_NLock_SN_LockEnd (0x210202).
    Signals client that initial character & inventory loading is finished.
    """
    return build_packet(Opcodes.SN_LOCK_END, struct.pack("<I", 0))

def build_record_packet(kills: int = 1337, deaths: int = 42, headshots: int = 890, wins: int = 150, losses: int = 12) -> bytes:
    """
    Builds tPacket_NLaunch_NLock_SN_Record (0x210203).
    Struct:
      Kills: uint32
      Deaths: uint32
      Headshots: uint32
      Wins: uint32
      Losses: uint32
    """
    payload = struct.pack("<IIIII", kills, deaths, headshots, wins, losses)
    return build_packet(Opcodes.SN_RECORD, payload)

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
        # Corrupted packet framing
        return None
    if len(buffer) < total_len:
        return None  # Partial packet, waiting for more bytes
    payload = buffer[8:total_len]
    return opcode, payload, total_len

if __name__ == "__main__":
    print("[+] District 187 Protocol Library Self-Test:")
    cipher = HermitCipher(0x0F)
    
    # Test Handshake packet
    res_pkt = build_hermit_response()
    enc = cipher.encrypt(res_pkt)
    dec = cipher.decrypt(enc)
    assert res_pkt == dec
    parsed = parse_packet(dec)
    assert parsed is not None
    assert parsed[0] == Opcodes.HERMIT_RES
    print(f"  [OK] Hermit Handshake 0x{parsed[0]:x} framed and encrypted/decrypted successfully.")

    # Test JoyGame Login packet
    login_pkt = build_joygame_login_response(account_id=1001, nickname="Gleidison")
    parsed_login = parse_packet(login_pkt)
    assert parsed_login is not None
    assert parsed_login[0] == Opcodes.SA_JOYGAME_LOGIN
    print(f"  [OK] SA_JoyGameLogin 0x{parsed_login[0]:x} verified.")

    # Test User Info and Inventory
    user_pkt = build_user_info_packet()
    parsed_user = parse_packet(user_pkt)
    assert parsed_user is not None
    assert parsed_user[0] == Opcodes.SN_USER_INFO
    print(f"  [OK] SN_UserInfo 0x{parsed_user[0]:x} verified.")

    lock_pkt = build_lock_end_packet()
    parsed_lock = parse_packet(lock_pkt)
    assert parsed_lock is not None
    assert parsed_lock[0] == Opcodes.SN_LOCK_END
    print(f"  [OK] SN_LockEnd 0x{parsed_lock[0]:x} verified.")
    print("[+] All protocol unit tests passed.")

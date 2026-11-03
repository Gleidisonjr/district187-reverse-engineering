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

# Packet IDs (Network Byte Order on wire)
PACKET_HERMIT_HANDSHAKE_REQ = 0x20080
PACKET_HERMIT_HANDSHAKE_RES = 0x20081
PACKET_HERMIT_HANDSHAKE_ACK = 0x20082
PACKET_HERMIT_HANDSHAKE_PONG = 0x20083
PACKET_HERMIT_PING = 0x20090

PACKET_CQ_LOGIN = 0x110101
PACKET_SA_LOGIN = 0x110102
PACKET_CQ_JOYGAME_LOGIN = 0x110111
PACKET_SA_JOYGAME_LOGIN = 0x110112

# NLaunch Family
PACKET_SN_USER_INFO = 0x210101
PACKET_SN_ITEM_LIST = 0x210201
PACKET_SN_LOCK_END = 0x210202
PACKET_SN_RECORD = 0x210203

# NMatchup Family
PACKET_CQ_ENTER_USER = 0x220101
PACKET_SA_ENTER_USER = 0x220102
PACKET_CQ_CREATE_ROOM = 0x220201
PACKET_SA_CREATE_ROOM = 0x220202
PACKET_CN_START_BUTTON = 0x220301

# NBattle Family
PACKET_SN_BATTLE_START = 0x230104

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

def build_login_success_response(packet_id: int, session_id: int, account_id: int = 1001, key_byte: int = 0x0F) -> bytes:
    """
    Constructs an authentic SA_JoyGameLogin or SA_Login packet (80 bytes).
    Scaleform handler at 0x100d74a0 expects:
    - Offset 0x10 (16): ResultCode = 0 (uint16 LE, 0 = SUCCESS)
    - Offset 0x12 (18): AccountID != 0 (uint32 LE, e.g. 1001)
    - Offset 0x16 (22): ServerPort = 12000 (uint16 LE)
    - Offset 0x18 (24): Session Token (32 bytes)
    """
    total_len = 80
    payload = bytearray(64)
    struct.pack_into('<H', payload, 0, 0)          # ResultCode = 0 (Success)
    struct.pack_into('<I', payload, 2, account_id) # AccountID = 1001
    struct.pack_into('<H', payload, 6, 12000)      # Server Port = 12000
    token = b"D187_HERMIT_OFFLINE_SESSION_TOKEN_2026\x00"
    payload[8:8+len(token)] = token
    # Extra user details in payload
    nickname = b"Operativo\x00"
    payload[40:40+len(nickname)] = nickname

    header = struct.pack('>HHII', 0, total_len, session_id, packet_id)
    plain = b'\x00\x00\x00\x00' + header + bytes(payload)
    return encrypt_hermit_packet(plain, key_byte)

def build_hermit_packet(packet_id: int, session_id: int, payload: bytes, key_byte: int = 0x0F) -> bytes:
    total_len = 16 + len(payload)
    header = struct.pack('>HHII', 0, total_len, session_id, packet_id)
    plain = b'\x00\x00\x00\x00' + header + payload
    return encrypt_hermit_packet(plain, key_byte)

def build_user_info_hermit(session_id: int, account_id: int = 1001, nickname: str = "Gleidison", key_byte: int = 0x0F) -> bytes:
    """SN_UserInfo (0x210101): Rank 58, 50M Exp, 9.99M Gold/Cash, Nickname, Clan."""
    nick_b = nickname.encode("utf-8")[:31].ljust(32, b"\x00")
    clan_b = b"D187_Meta\x00".ljust(32, b"\x00")
    payload = struct.pack("<IIQII32s32s", account_id, 58, 50000000, 9999999, 9999999, nick_b, clan_b)
    return build_hermit_packet(PACKET_SN_USER_INFO, session_id, payload, key_byte)

def build_item_list_hermit(session_id: int, key_byte: int = 0x0F) -> bytes:
    """SN_ItemList (0x210201): Loads VIP weapons with slots equipped."""
    import sqlite3
    db_path = os.path.join(r"targets\district-187\data\s2rebirth.db")
    items = []
    if os.path.exists(db_path):
        try:
            conn = sqlite3.connect(db_path)
            c = conn.cursor()
            c.execute("SELECT group_id, slot FROM weapons ORDER BY damage DESC LIMIT 64")
            equipped = {0: False, 1: False, 2: False, 3: False}
            for row in c.fetchall():
                gid, slot_name = row[0], row[1] or ""
                slot = -1
                if slot_name == "ana-silah" and not equipped[0]:
                    slot = 0; equipped[0] = True
                elif slot_name == "tabanca" and not equipped[1]:
                    slot = 1; equipped[1] = True
                elif slot_name == "bicak" and not equipped[2]:
                    slot = 2; equipped[2] = True
                elif slot_name == "bomba" and not equipped[3]:
                    slot = 3; equipped[3] = True
                items.append((gid, 1, 100, slot))
            conn.close()
        except Exception:
            pass

    if not items:
        # Fallback VIP items
        items = [(1110001, 1, 100, 0), (1120001, 2, 100, 1), (1130001, 3, 100, 2), (1140001, 4, 100, 3)]

    payload = bytearray(struct.pack("<I", len(items)))
    for gid, itype, dur, slot in items:
        payload += struct.pack("<IHhh", gid, itype, dur, slot)
    return build_hermit_packet(PACKET_SN_ITEM_LIST, session_id, bytes(payload), key_byte)

def build_record_hermit(session_id: int, key_byte: int = 0x0F) -> bytes:
    """SN_Record (0x210203): Kills, Deaths, Headshots, Wins, Losses."""
    payload = struct.pack("<IIIII", 2450, 180, 1620, 310, 15)
    return build_hermit_packet(PACKET_SN_RECORD, session_id, payload, key_byte)

def build_lock_end_hermit(session_id: int, key_byte: int = 0x0F) -> bytes:
    """SN_LockEnd (0x210202): Signals UI to open lobby."""
    return build_hermit_packet(PACKET_SN_LOCK_END, session_id, struct.pack("<I", 0), key_byte)

def build_enter_channel_response(session_id: int, channel_id: int = 1, key_byte: int = 0x0F) -> bytes:
    """SA_EnterUser (0x220102): Response to CQ_EnterUser for lobby channel."""
    cname = b"Canal 1 - Livre [Competitivo]\x00".ljust(32, b"\x00")
    payload = struct.pack("<II32s", 0, channel_id, cname)
    return build_hermit_packet(PACKET_SA_ENTER_USER, session_id, payload, key_byte)

def build_create_room_response(session_id: int, room_id: int = 1, key_byte: int = 0x0F) -> bytes:
    """SA_CreateRoom (0x220202): Response to CQ_CreateRoom."""
    rname = b"Arrival 8v8 [Bots & VIP]\x00".ljust(32, b"\x00")
    payload = struct.pack("<II32sI", 0, room_id, rname, 1)
    return build_hermit_packet(PACKET_SA_CREATE_ROOM, session_id, payload, key_byte)

def build_battle_start_hermit(session_id: int, key_byte: int = 0x0F) -> bytes:
    """SN_BattleStart (0x230104): Directs client to connect to combat server."""
    ip_b = b"127.0.0.1\x00".ljust(16, b"\x00")
    map_b = b"Worlds\\Arrival.World00p\x00".ljust(32, b"\x00")
    payload = struct.pack("<16sH32s", ip_b, 27888, map_b)
    return build_hermit_packet(PACKET_SN_BATTLE_START, session_id, payload, key_byte)

class HermitClientSession:
    def __init__(self, sock, addr):
        self.sock = sock
        self.addr = addr
        self.session_id = 0x04034992
        self.key_byte = 0x0F
        self.recv_buf = bytearray()
        self.state = "HANDSHAKE"

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

        # 3. Hermit Ping (0x20090 -> Pong 0x20083)
        elif pkt_id == PACKET_HERMIT_PING:
            print(f"[+] Hermit Ping (0x20090) received. Sending Pong 0x20083...")
            resp = build_handshake_pong_83(self.session_id, self.key_byte)
            self.sock.sendall(resp)

        # 4. CQ_JoyGameLogin (0x110111) -> SA_JoyGameLogin + Full VIP Lobby Packets
        elif pkt_id == PACKET_CQ_JOYGAME_LOGIN or pkt_id == PACKET_CQ_LOGIN:
            login_type = "CQ_JoyGameLogin" if pkt_id == PACKET_CQ_JOYGAME_LOGIN else "CQ_Login"
            resp_pkt_id = PACKET_SA_JOYGAME_LOGIN if pkt_id == PACKET_CQ_JOYGAME_LOGIN else PACKET_SA_LOGIN
            print(f"[+] {login_type} (0x{pkt_id:X}) received! Authenticating user and preparing VIP Lobby...")
            
            # 1. Login Response (clears 'please wait' at 0x100d74db)
            resp = build_login_success_response(resp_pkt_id, self.session_id, account_id=1001, key_byte=self.key_byte)
            self.sock.sendall(resp)
            print(f"[+] Dispatched SA_JoyGameLogin ({len(resp)} bytes, ResultCode=0, AccountID=1001)!")

            # 2. Dispatch User Info (Rank 58, 50M Exp, 9.99M Gold/Cash)
            uinfo = build_user_info_hermit(self.session_id, account_id=1001, nickname="Gleidison", key_byte=self.key_byte)
            self.sock.sendall(uinfo)
            print(f"[+] Dispatched SN_UserInfo (Rank 58, 9.99M Gold/Cash)!")

            # 3. Dispatch Item List (VIP Arsenal from s2rebirth.db)
            ilist = build_item_list_hermit(self.session_id, key_byte=self.key_byte)
            self.sock.sendall(ilist)
            print(f"[+] Dispatched SN_ItemList ({len(ilist)} bytes with equipped weapon slots)!")

            # 4. Dispatch Record Stats
            rec = build_record_hermit(self.session_id, key_byte=self.key_byte)
            self.sock.sendall(rec)
            print(f"[+] Dispatched SN_Record (2450 Kills, 1620 Headshots)!")

            # 5. Dispatch LockEnd (Instructs UI to unlock Lobby and load Arsenal)
            lend = build_lock_end_hermit(self.session_id, key_byte=self.key_byte)
            self.sock.sendall(lend)
            print(f"[+] Dispatched SN_LockEnd -> Client transitioned to LOBBY!")

        # 6. CQ_EnterUser (0x220101) -> SA_EnterUser (0x220102) [Channel Navigation]
        elif pkt_id == PACKET_CQ_ENTER_USER:
            print(f"[+] CQ_EnterUser (0x220101) received! Entering Lobby Channel...")
            resp = build_enter_channel_response(self.session_id, channel_id=1, key_byte=self.key_byte)
            self.sock.sendall(resp)
            print(f"[+] Dispatched SA_EnterUser (Channel 1 [Competitivo])!")

        # 7. CQ_CreateRoom (0x220201) -> SA_CreateRoom (0x220202) [Room Creation]
        elif pkt_id == PACKET_CQ_CREATE_ROOM:
            print(f"[+] CQ_CreateRoom (0x220201) received! Creating Match Room...")
            resp = build_create_room_response(self.session_id, room_id=1, key_byte=self.key_byte)
            self.sock.sendall(resp)
            print(f"[+] Dispatched SA_CreateRoom (Room 1: Arrival 8v8 [Bots & VIP])!")

        # 8. CN_StartButton (0x220301) -> SN_BattleStart (0x230104) [Match Trigger]
        elif pkt_id == PACKET_CN_START_BUTTON:
            print(f"[+] CN_StartButton (0x220301) received! Launching Battle...")
            resp = build_battle_start_hermit(self.session_id, key_byte=self.key_byte)
            self.sock.sendall(resp)
            print(f"[+] Dispatched SN_BattleStart -> Directing client to 127.0.0.1:27888 (Arrival.World00p)!")

        else:
            print(f"[?] Unknown / Unhandled Hermit Packet ID: 0x{pkt_id:X}")
            # Send general success / pong if in doubt
            resp = build_handshake_pong_83(self.session_id, self.key_byte)
            try:
                self.sock.sendall(resp)
            except Exception:
                pass

def start_tcp_server(port=12000):
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_sock.bind(("0.0.0.0", port))
    server_sock.listen(10)
    print(f"=====================================================================")
    print(f"  District 187: Sin Streets — Hermit Dedicated Server Emulator")
    print(f"  Listening on TCP 0.0.0.0:{port}")
    print(f"  Protocol: Hermit Jupiter EX (CRC32 Stream Cipher, Key=0x0F)")
    print(f"=====================================================================")
    while True:
        try:
            client_sock, client_addr = server_sock.accept()
            session = HermitClientSession(client_sock, client_addr)
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
    port = 12000
    udp_thread = threading.Thread(target=start_udp_listener, args=(port,), daemon=True)
    udp_thread.start()
    start_tcp_server(port)

if __name__ == "__main__":
    main()

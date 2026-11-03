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

def build_handshake_response_81(session_id: int, key_byte: int = 0x0F) -> bytes:
    """
    Constructs Handshake Response 0x20081 (32 bytes).
    Client requires:
    - PacketID = 0x20081 (Big Endian)
    - Length = 32 (Big Endian)
    - Session ID matching client session
    - Payload DWORD 1 <= client random (0 is always valid)
    - Payload DWORD 3 ^ DWORD 2 = key_byte (0x0F)
    """
    payload = struct.pack('>IIII', 0x12345678, 0, 0, key_byte)
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
            print(f"[+] Hermit Handshake Step 1 (0x20080) received! Sending 0x20081 response...")
            resp = build_handshake_response_81(self.session_id, self.key_byte)
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

        # 4. CQ_JoyGameLogin (0x110111) -> SA_JoyGameLogin (0x110112)
        elif pkt_id == PACKET_CQ_JOYGAME_LOGIN:
            print(f"[+] CQ_JoyGameLogin (0x110111) received! Authenticating user...")
            resp = build_login_success_response(PACKET_SA_JOYGAME_LOGIN, self.session_id, account_id=1001, key_byte=self.key_byte)
            self.sock.sendall(resp)
            print(f"[+] Dispatched SA_JoyGameLogin ({len(resp)} bytes, ResultCode=0, AccountID=1001) to release 'please wait'!")

        # 5. CQ_Login Developer Mode (0x110101) -> SA_Login (0x110102)
        elif pkt_id == PACKET_CQ_LOGIN:
            print(f"[+] CQ_Login (0x110101) received! Sending SA_Login...")
            resp = build_login_success_response(PACKET_SA_LOGIN, self.session_id, account_id=1001, key_byte=self.key_byte)
            self.sock.sendall(resp)
            print(f"[+] Dispatched SA_Login ({len(resp)} bytes, ResultCode=0, AccountID=1001)!")

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

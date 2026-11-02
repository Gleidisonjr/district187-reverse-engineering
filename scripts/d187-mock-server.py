#!/usr/bin/env python3
"""
District 187 (S2 Online) — Hermit Protocol Mock Server & Packet Sniffer
Listens on TCP & UDP port 12000 to capture, decode and emulate the server handshake.

Author: Gleidison Carvalho & Antigravity (2026-11-02)
"""
import argparse
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

# Packet ID & Opcode Definitions
PACKET_CQ_LOGIN = 0x110101
PACKET_SA_LOGIN = 0x110102
PACKET_CQ_JOYGAME_LOGIN = 0x110111
PACKET_SA_JOYGAME_LOGIN = 0x110112
PACKET_CN_NETMARBLE_DATA = 0x110121
PACKET_SA_NETMARBLE_LOGIN = 0x110123

OPCODE_JOYGAME_LOGIN = 0x0062
OPCODE_DEV_LOGIN = 0x034d

def format_hex(data):
    lines = []
    for i in range(0, len(data), 16):
        chunk = data[i:i+16]
        hex_str = " ".join(f"{b:02x}" for b in chunk)
        ascii_str = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
        lines.append(f"  {i:04x}: {hex_str:<48}  {ascii_str}")
    return "\n".join(lines)

def log_packet(proto, client_addr, data):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    print(f"\n[{timestamp}] [{proto}] Received {len(data)} bytes from {client_addr}")
    print(format_hex(data))

    os.makedirs(LOG_DIR, exist_ok=True)
    filename = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f") + f"_{proto}.bin"
    filepath = os.path.join(LOG_DIR, filename)
    with open(filepath, "wb") as f:
        f.write(data)
    print(f"[*] Saved raw payload to {filepath}")

def build_login_response(req_packet_id, req_opcode):
    """
    Constructs an authentic Hermit response packet for SA_JoyGameLogin or SA_Login
    """
    resp_packet_id = PACKET_SA_JOYGAME_LOGIN if req_packet_id == PACKET_CQ_JOYGAME_LOGIN else PACKET_SA_LOGIN
    resp_opcode = req_opcode

    # Payload:
    # 0x00..0x01: Result code (0 = SUCCESS)
    # 0x02..0x05: Server IP (127.0.0.1 in network byte order)
    # 0x06..0x07: Server Port (12000)
    # 0x08..0x27: Session Token / User Key (32 bytes)
    payload = bytearray(64)
    struct.pack_into("<H", payload, 0, 0) # ResultCode = 0 (Success)
    struct.pack_into("<BBBB", payload, 2, 127, 0, 0, 1) # 127.0.0.1
    struct.pack_into("<H", payload, 6, 12000) # Port 12000
    payload[8:24] = b"D187_SESSION_KEY"

    # Header:
    # Size (uint16), Flags (uint32), Opcode (uint16), Session (uint32), PacketID (uint32)
    total_len = 16 + len(payload)
    header = bytearray(16)
    struct.pack_into("<H", header, 0, total_len)
    struct.pack_into("<I", header, 2, 0) # Flags
    struct.pack_into("<H", header, 6, resp_opcode)
    struct.pack_into("<I", header, 8, 1) # Session ID
    struct.pack_into("<I", header, 12, resp_packet_id)

    return bytes(header + payload)

def handle_incoming_data(client_sock, client_addr, data):
    log_packet("TCP", client_addr, data)

    if len(data) >= 16:
        try:
            pkt_len, flags, opcode, session_id, packet_id = struct.unpack_from("<HIHII", data, 0)
            print(f"[*] Decoded Hermit Header: Len={pkt_len}, Opcode={hex(opcode)}, PacketID={hex(packet_id)}")

            if packet_id in (PACKET_CQ_JOYGAME_LOGIN, PACKET_CQ_LOGIN) or opcode in (OPCODE_JOYGAME_LOGIN, OPCODE_DEV_LOGIN):
                print(f"[+] Recognized Login Request ({hex(packet_id)}). Emulating SA_JoyGameLogin response...")
                resp = build_login_response(packet_id, opcode)
                client_sock.sendall(resp)
                print(f"[+] Sent {len(resp)} bytes login response to {client_addr}")
        except Exception as ex:
            print(f"[-] Error decoding packet header: {ex}")

def handle_tcp_client(client_sock, client_addr):
    print(f"[+] TCP Client connected from {client_addr}")
    try:
        while True:
            data = client_sock.recv(4096)
            if not data:
                print(f"[-] TCP Client {client_addr} disconnected.")
                break
            handle_incoming_data(client_sock, client_addr, data)
    except Exception as e:
        print(f"[-] TCP Connection error with {client_addr}: {e}")
    finally:
        client_sock.close()

def start_tcp_listener(port):
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_sock.bind(("0.0.0.0", port))
    server_sock.listen(10)
    print(f"[+] TCP Listener active on 0.0.0.0:{port}")
    while True:
        try:
            client_sock, addr = server_sock.accept()
            client_thread = threading.Thread(target=handle_tcp_client, args=(client_sock, addr), daemon=True)
            client_thread.start()
        except Exception as e:
            print(f"[-] TCP Accept error: {e}")
            break

def start_udp_listener(port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("0.0.0.0", port))
    print(f"[+] UDP Listener active on 0.0.0.0:{port}")
    while True:
        try:
            data, addr = sock.recvfrom(65535)
            log_packet("UDP", addr, data)
        except Exception as e:
            print(f"[-] UDP error: {e}")
            break

def main():
    parser = argparse.ArgumentParser(description="District 187 Hermit Protocol Mock Server")
    parser.add_argument("--port", type=int, default=12000, help="Listen port (default: 12000)")
    args = parser.parse_args()

    print(f"=== District 187 Hermit Mock Server starting on port {args.port} ===")
    os.makedirs(LOG_DIR, exist_ok=True)

    t_udp = threading.Thread(target=start_udp_listener, args=(args.port,), daemon=True)
    t_tcp = threading.Thread(target=start_tcp_listener, args=(args.port,), daemon=True)
    t_udp.start()
    t_tcp.start()

    print("[*] Both TCP and UDP listeners ready. Waiting for incoming game packets...")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[*] Stopping server.")

if __name__ == "__main__":
    main()

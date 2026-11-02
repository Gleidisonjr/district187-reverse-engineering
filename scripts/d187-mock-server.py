#!/usr/bin/env python3
"""
District 187 (S2 Online) — Hermit Protocol Mock Server & Packet Sniffer
Listens on TCP & UDP port 12000 to capture and analyze the client handshake.

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

# Ensure immediate unbuffered console output
try:
    sys.stdout.reconfigure(line_buffering=True)
except Exception:
    pass

LOG_DIR = r"targets\district-187\traffic"

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

def handle_tcp_client(client_sock, client_addr):
    print(f"[+] TCP Client connected from {client_addr}")
    try:
        while True:
            data = client_sock.recv(4096)
            if not data:
                print(f"[-] TCP Client {client_addr} disconnected.")
                break
            log_packet("TCP", client_addr, data)
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

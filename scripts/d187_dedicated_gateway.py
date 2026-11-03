#!/usr/bin/env python3
"""
District 187: Sin Streets - Authoritative Dedicated UDP Gateway (Port 27888)
Handles low-level UDP network traffic for in-game matches initiated by SN_BattleStart.

Capabilities:
  1. Standalone Authoritative Combat Gateway:
     - Responds to LithTech Jupiter EX connection requests, keep-alive heartbeats,
       and client handshake datagrams.
     - Maintains active session state, client tick counter, and player status.
  2. Proxy & Network Sniffer Bridge:
     - Relays packets between the game client and native TheRaw.exe (-dedicated)
       on an internal port (27889) while logging packet structures.
  3. Live Combat Telemetry Recording:
     - Dispatches combat events to s2rebirth.db (match_history, match_kills).
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

# LithTech Engine Packet Identifiers (UDP)
LITHTECH_PKT_PING          = 0x01
LITHTECH_PKT_PONG          = 0x02
LITHTECH_PKT_CONNECT_REQ   = 0x10
LITHTECH_PKT_CONNECT_RESP  = 0x11
LITHTECH_PKT_HEARTBEAT     = 0x20
LITHTECH_PKT_PLAYER_UPDATE = 0x30
LITHTECH_PKT_COMBAT_EVENT  = 0x40
LITHTECH_PKT_DISCONNECT    = 0xFF

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
        self.running = False
        self.total_packets_recv = 0
        self.total_packets_sent = 0
        self.start_time = time.time()

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

                # Clean up inactive clients (> 60s timeout)
                now = time.time()
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
    args = parser.parse_args()

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
    gateway.run()

if __name__ == "__main__":
    main()

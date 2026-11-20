#!/usr/bin/env python3
"""
District 187: Sin Streets - Live MITM Decrypting Network Sniffer & Proxy
Transparent TCP proxy that sits between TheRaw.exe and the server (local or official),
decrypts the Hermit CRC32 stream in real time, and logs formatted protocol packets
matched against the 326-packet master schema.
"""

import os
import sys
import socket
import select
import struct
import json
import datetime
import argparse
from typing import Optional, Tuple

# Ensure UTF-8 output
sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCHEMA_PATH = os.path.join(BASE_DIR, "targets", "district-187", "data", "d187_protocol_schema.json")
LOG_DIR = os.path.join(BASE_DIR, "targets", "district-187", "traffic")

# Import protocol library
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from d187_protocol import HermitCipher, CRC32_TABLE

def load_protocol_schema():
    if not os.path.exists(SCHEMA_PATH):
        return {}
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    mapping = {}
    for p in data.get("packets", []):
        mapping[p["name"]] = p
    return mapping

# Known Opcode to Name mappings
KNOWN_OPCODES = {
    # Handshake
    0x20080: "HERMIT_HANDSHAKE_REQ",
    0x20081: "HERMIT_HANDSHAKE_RES",
    0x20082: "HERMIT_HANDSHAKE_ACK",
    0x20083: "HERMIT_HANDSHAKE_PONG",
    0x20084: "HERMIT_KEEPALIVE",
    0x20090: "HERMIT_PING",
    # Login
    0x110101: "CQ_Login",
    0x110102: "SA_Login",
    0x110111: "CQ_JoyGameLogin",
    0x110112: "SA_JoyGameLogin",
    0x110124: "CQ_Join",
    0x110125: "SA_Join",
    # Profile
    0x210101: "SN_UserInfo",
    0x210103: "SN_Record",
    0x210105: "SN_RankingInfo",
    0x210111: "SN_ItemList",
    0x210121: "SN_LockEnd",
    # Server/Channel
    0x220101: "SN_ServerInfo",
    0x220102: "SN_ChannelList",
    0x220107: "SN_GroupList",
    0x220108: "SN_ServerList",
    0x220111: "CQ_EnterUser",
    0x220112: "SA_EnterUser",
    # Room
    0x220201: "CQ_CreateRoom",
    0x220202: "SA_CreateRoom",
    0x220203: "SN_Info",
    0x220231: "CQ_EnterRoom",
    0x220232: "SA_EnterRoom",
    0x220233: "SN_UserList",
    0x220234: "CQ_LeaveRoom",
    0x220301: "CN_StartButton",
    0x220311: "CQ_ChangeTeam",
    0x220312: "SA_ChangeTeam",
    0x220313: "SN_ChangeTeam",
    0x220314: "CQ_StartGame",
    0x220319: "SN_ChangeLeader",
    # NPlay (battle start — only valid after F5)
    0x222101: "CN_PlayReadyButton",
    0x222103: "CN_PlayStartButton (F5)",
    0x222111: "SN_BaseRoomInfo",
    0x222112: "SN_BaseUserList",
    # Match server
    0x420303: "SN_HostConnect",
    0x420310: "SN_BattleStart",
    # Equipment/shop
    0x240101: "CQ_EquipOpen",
    0x240102: "SA_EquipOpen",
    # Combat
    0x230124: "SN_Kill",
    0x230136: "SN_Bomb",
    # ApexGuard
    0x5A0101: "APEX_HEARTBEAT_REQ",
    0x5A0102: "APEX_HEARTBEAT_ACK",
}

def decrypt_hermit(data: bytes, key_byte: int = 0x0F) -> bytes:
    buf = bytearray(data)
    for i in range(4, len(buf)):
        tbl_byte = CRC32_TABLE[i & 0xFF] & 0xFF
        buf[i] = data[i] ^ tbl_byte ^ key_byte
    return bytes(buf)

def inspect_packet(plain_bytes: bytes, direction: str, log_file):
    if len(plain_bytes) < 16:
        return
    try:
        _, flags, pkt_len, session_id, pkt_id = struct.unpack('>IHHII', plain_bytes[:16])
    except struct.error:
        return
    payload = plain_bytes[16:]
    name = KNOWN_OPCODES.get(pkt_id, f"tPacket_Opcode_0x{pkt_id:X}")

    timestamp = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
    arrow = "--> [C->S]" if direction == "C2S" else "<-- [S->C]"
    
    print(f"[{timestamp}] {arrow} {name:<35} | Len: {pkt_len:4d} | Sess: 0x{session_id:X}")
    
    if pkt_id == 0x110112 and len(payload) >= 4:
        rc = struct.unpack('<H', payload[:2])[0]
        acc_id = struct.unpack('<I', payload[2:6])[0]
        print(f"      SA_JoyGameLogin -> ResultCode={rc} (0=SUCCESS), AccountID={acc_id}")
    elif pkt_id == 0x210101 and len(payload) >= 48:
        acc, rank, exp, gold, cash = struct.unpack('<IIQII', payload[:24])
        print(f"      SN_UserInfo     -> Rank={rank}, Exp={exp}, Gold={gold:,}, Cash={cash:,}")
    elif pkt_id == 0x210201 and len(payload) >= 4:
        cnt = struct.unpack('<I', payload[:4])[0]
        print(f"      SN_ItemList     -> Total Items Delivered: {cnt}")

    log_entry = {
        "timestamp": timestamp,
        "direction": direction,
        "opcode": hex(pkt_id),
        "name": name,
        "length": pkt_len,
        "session_id": hex(session_id),
        "payload_hex": payload.hex()
    }
    if log_file:
        log_file.write(json.dumps(log_entry) + "\n")
        log_file.flush()

class MitmProxy:
    def __init__(self, listen_port=12005, target_host="127.0.0.1", target_port=12000):
        self.listen_port = listen_port
        self.target_host = target_host
        self.target_port = target_port

    def start(self):
        os.makedirs(LOG_DIR, exist_ok=True)
        log_path = os.path.join(LOG_DIR, f"mitm_sniff_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl")
        log_file = open(log_path, "w", encoding="utf-8")

        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(("0.0.0.0", self.listen_port))
        server.listen(5)

        print("=====================================================================")
        print(f"  District 187: Live Decrypting MITM Proxy Sniffer")
        print(f"  Listening on: 127.0.0.1:{self.listen_port}")
        print(f"  Forwarding to: {self.target_host}:{self.target_port}")
        print(f"  Logging Decrypted Packets to: {log_path}")
        print("=====================================================================\n")

        try:
            while True:
                client_sock, client_addr = server.accept()
                print(f"[+] Client connected from {client_addr}. Connecting to server {self.target_host}:{self.target_port}...")
                
                try:
                    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    server_sock.connect((self.target_host, self.target_port))
                    print("[+] Upstream server connection established. Sniffing active.\n")
                except Exception as e:
                    print(f"[-] Could not connect to target server: {e}")
                    client_sock.close()
                    continue

                sockets = [client_sock, server_sock]
                while True:
                    # Empty error-set: on Windows select() fires exceptional conditions on
                    # normal TCP events, causing silent break before any data is logged.
                    r, _, _ = select.select(sockets, [], [], 1.0)
                    for s in r:
                        other = server_sock if s is client_sock else client_sock
                        direction = "C2S" if s is client_sock else "S2C"
                        try:
                            data = s.recv(65536)
                            if not data:
                                raise ConnectionResetError()

                            # Log FIRST (write raw hex before any parse that could throw)
                            ts = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
                            raw_entry = {
                                "timestamp": ts, "direction": direction,
                                "opcode": "raw", "name": "RAW",
                                "length": len(data), "session_id": "?",
                                "payload_hex": data.hex()
                            }
                            log_file.write(json.dumps(raw_entry) + "\n")
                            log_file.flush()

                            # Relay original encrypted bytes unmodified
                            other.sendall(data)

                            # Also try to parse and log decoded packet on top
                            decrypted = decrypt_hermit(data)
                            if len(decrypted) >= 16:
                                inspect_packet(decrypted, direction, log_file)

                        except Exception as e:
                            print(f"[-] Connection closed ({e})")
                            sockets = []
                            break
                    if not sockets:
                        break

                client_sock.close()
                server_sock.close()

        except KeyboardInterrupt:
            print("\n[-] Stopping MITM proxy.")
        finally:
            log_file.close()

def main():
    parser = argparse.ArgumentParser(description="District 187 Hermit Decrypting MITM Sniffer")
    parser.add_argument("--listen", type=int, default=12005, help="Local listening port (default: 12005)")
    parser.add_argument("--target-host", default="127.0.0.1", help="Target server host (default: 127.0.0.1)")
    parser.add_argument("--target-port", type=int, default=12000, help="Target server port (default: 12000)")
    args = parser.parse_args()

    proxy = MitmProxy(listen_port=args.listen, target_host=args.target_host, target_port=args.target_port)
    proxy.start()

if __name__ == "__main__":
    main()

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
    0x20080: "HERMIT_HANDSHAKE_REQ (0x20080)",
    0x20081: "HERMIT_HANDSHAKE_RES (0x20081)",
    0x20082: "HERMIT_HANDSHAKE_ACK (0x20082)",
    0x20083: "HERMIT_HANDSHAKE_PONG (0x20083)",
    0x20090: "HERMIT_PING (0x20090)",
    0x110101: "CQ_Login (0x110101)",
    0x110102: "SA_Login (0x110102)",
    0x110111: "CQ_JoyGameLogin (0x110111)",
    0x110112: "SA_JoyGameLogin (0x110112)",
    0x210101: "SN_UserInfo (0x210101)",
    0x210201: "SN_ItemList (0x210201)",
    0x210202: "SN_LockEnd (0x210202)",
    0x210203: "SN_Record (0x210203)",
    0x220101: "CQ_EnterUser (0x220101)",
    0x220102: "SA_EnterUser (0x220102)",
    0x220201: "CQ_CreateRoom (0x220201)",
    0x220202: "SA_CreateRoom (0x220202)",
    0x220301: "CN_StartButton (0x220301)",
    0x230104: "SN_BattleStart (0x230104)",
    0x230124: "SN_Kill (0x230124)",
    0x230136: "SN_Bomb (0x230136)"
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
    _, flags, pkt_len, session_id, pkt_id = struct.unpack('>IHHII', plain_bytes[:16])
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
                    r, _, x = select.select(sockets, [], sockets, 1.0)
                    if x:
                        break
                    for s in r:
                        other = server_sock if s is client_sock else client_sock
                        direction = "C2S" if s is client_sock else "S2C"
                        try:
                            data = s.recv(4096)
                            if not data:
                                raise ConnectionResetError()
                            
                            # Decrypt copy for sniffer inspection
                            decrypted = decrypt_hermit(data)
                            inspect_packet(decrypted, direction, log_file)
                            
                            # Relay original unmodified bytes to destination
                            other.sendall(data)
                        except Exception:
                            print("[-] Connection closed by peer.")
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

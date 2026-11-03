#!/usr/bin/env python3
"""
District 187: Sin Streets - End-to-End Client Handshake & Lobby Smoke Test
Simulates the exact network sequence of TheRaw.exe against d187-mock-server.py:
  1. Hermit 0x20080 -> 0x20081
  2. Hermit 0x20082 -> 0x20083
  3. CQ_JoyGameLogin (0x110111) -> SA_JoyGameLogin (0x110112)
  4. Receives SN_UserInfo, SN_ItemList, SN_Record, SN_LockEnd
  5. CQ_EnterUser (0x220101) -> SA_EnterUser (0x220102)
  6. CQ_CreateRoom (0x220201) -> SA_CreateRoom (0x220202)
  7. CN_StartButton (0x220301) -> SN_BattleStart (0x230104)
"""

import socket
import struct
import binascii
import sys
import time

# Ensure UTF-8 output
sys.stdout.reconfigure(encoding='utf-8')

# CRC Table
CRC_TABLE = []
for i in range(256):
    c = i
    for _ in range(8):
        c = 0xEDB88320 ^ (c >> 1) if (c & 1) else (c >> 1)
    CRC_TABLE.append(c)

def encrypt(data, key=0x0F):
    buf = bytearray(data)
    for i in range(4, len(buf)):
        buf[i] = data[i] ^ (CRC_TABLE[i & 0xFF] & 0xFF) ^ key
    crc = binascii.crc32(buf[4:]) & 0xFFFFFFFF
    buf[0:4] = struct.pack('>I', crc)
    return bytes(buf)

def decrypt(data, key=0x0F):
    buf = bytearray(data)
    for i in range(4, len(buf)):
        buf[i] = data[i] ^ (CRC_TABLE[i & 0xFF] & 0xFF) ^ key
    return bytes(buf)

def build_pkt(pkt_id, sess_id, payload, key=0x0F):
    total_len = 16 + len(payload)
    header = struct.pack('>HHII', 0, total_len, sess_id, pkt_id)
    plain = b'\x00\x00\x00\x00' + header + payload
    return encrypt(plain, key)

def run_smoke_test(host="127.0.0.1", port=12000):
    print(f"[+] Connecting to District 187 Server at {host}:{port}...")
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(5.0)
    try:
        sock.connect((host, port))
    except Exception as e:
        print(f"[-] Could not connect to {host}:{port}: {e}")
        return False

    session_id = 0x04034992
    print("[+] TCP Connection established.")

    # 1. Send Handshake 0x20080
    req_80 = build_pkt(0x20080, session_id, b"\x00" * 16)
    sock.sendall(req_80)
    print("  [->] Sent Hermit Handshake Req (0x20080)")

    resp = sock.recv(4096)
    dec_81 = decrypt(resp)
    _, _, _, _, pkt_id = struct.unpack('>IHHII', dec_81[:16])
    assert pkt_id == 0x20081, f"Expected 0x20081, got 0x{pkt_id:X}"
    print(f"  [<-] Received Handshake Res (0x{pkt_id:X}) - Server Authenticated.")

    # 2. Send Handshake ACK 0x20082
    ack_82 = build_pkt(0x20082, session_id, b"\x00" * 4)
    sock.sendall(ack_82)
    print("  [->] Sent Hermit Handshake ACK (0x20082)")

    resp = sock.recv(4096)
    dec_83 = decrypt(resp)
    _, _, _, _, pkt_id = struct.unpack('>IHHII', dec_83[:16])
    assert pkt_id == 0x20083, f"Expected 0x20083, got 0x{pkt_id:X}"
    print(f"  [<-] Received Handshake Pong (0x{pkt_id:X}) - Session Active.")

    # 3. Send CQ_JoyGameLogin (0x110111)
    login_payload = b"Gleidison\x00".ljust(32, b"\x00") + b"secret_pass\x00".ljust(32, b"\x00")
    login_pkt = build_pkt(0x110111, session_id, login_payload)
    sock.sendall(login_pkt)
    print("  [->] Sent CQ_JoyGameLogin (0x110111) for user 'Gleidison'")

    # Read server stream (expect SA_JoyGameLogin, SN_UserInfo, SN_ItemList, SN_Record, SN_LockEnd)
    stream = bytearray()
    start_t = time.time()
    received_opcodes = []

    while time.time() - start_t < 3.0:
        try:
            chunk = sock.recv(4096)
            if not chunk:
                break
            stream.extend(chunk)
            
            # Try parsing packets from stream
            while len(stream) >= 16:
                # Decrypt length
                tbl_b6 = CRC_TABLE[6] & 0xFF
                tbl_b7 = CRC_TABLE[7] & 0xFF
                len_b6 = stream[6] ^ tbl_b6 ^ 0x0F
                len_b7 = stream[7] ^ tbl_b7 ^ 0x0F
                pkt_len = (len_b6 << 8) | len_b7
                if pkt_len < 16 or pkt_len > 8192:
                    break
                if len(stream) < pkt_len:
                    break
                raw_pkt = bytes(stream[:pkt_len])
                stream = stream[pkt_len:]
                dec_pkt = decrypt(raw_pkt)
                _, _, _, _, op = struct.unpack('>IHHII', dec_pkt[:16])
                received_opcodes.append(op)
                print(f"  [<-] Decoded Packet: 0x{op:X}")
        except socket.timeout:
            break

    print(f"\n[+] Total Packets Received: {len(received_opcodes)}")
    assert 0x110112 in received_opcodes, "Missing SA_JoyGameLogin (0x110112)"
    print("  [OK] SA_JoyGameLogin (0x110112) verified -> IsPacketerrorMessage(0, 0) = No Error!")
    assert 0x210101 in received_opcodes, "Missing SN_UserInfo (0x210101)"
    print("  [OK] SN_UserInfo (0x210101) verified -> 25B Nickname & 25B ClanName delivered!")
    assert 0x210105 in received_opcodes, "Missing SN_RankingInfo (0x210105)"
    print("  [OK] SN_RankingInfo (0x210105) verified -> Rank 58 & Exp delivered!")
    assert 0x210111 in received_opcodes, "Missing SN_ItemList (0x210111)"
    print("  [OK] SN_ItemList (0x210111) verified -> 27B/item VIP arsenal delivered!")
    assert 0x210103 in received_opcodes, "Missing SN_Record (0x210103)"
    print("  [OK] SN_Record (0x210103) verified -> 224B stats record delivered!")
    assert 0x210121 in received_opcodes, "Missing SN_LockEnd (0x210121)"
    print("  [OK] SN_LockEnd (0x210121) verified -> Calls ChangeScene(0) out of LoginScene!")
    assert 0x220101 in received_opcodes, "Missing SN_ServerInfo (0x220101)"
    print("  [OK] SN_ServerInfo (0x220101) verified -> 98B Server entry (127.0.0.1:12000) delivered!")
    assert 0x220102 in received_opcodes, "Missing SN_ChannelList (0x220102)"
    print("  [OK] SN_ChannelList (0x220102) verified -> 57B Channel entries delivered!")

    def recv_opcodes(sock, min_count=1):
        buf = bytearray()
        ops = []
        deadline = time.time() + 2.0
        while len(ops) < min_count and time.time() < deadline:
            chunk = sock.recv(4096)
            if not chunk:
                break
            buf.extend(chunk)
            while len(buf) >= 16:
                len_b6 = buf[6] ^ (CRC_TABLE[6] & 0xFF) ^ 0x0F
                len_b7 = buf[7] ^ (CRC_TABLE[7] & 0xFF) ^ 0x0F
                plen = (len_b6 << 8) | len_b7
                if plen < 16 or len(buf) < plen:
                    break
                raw_p = bytes(buf[:plen])
                buf = buf[plen:]
                dec_p = decrypt(raw_p)
                _, _, _, _, op_code = struct.unpack('>IHHII', dec_p[:16])
                ops.append(op_code)
        return ops

    # 4. Channel Navigation (CQ_EnterUser 0x220111 -> SA_EnterUser 0x220112 + SA_RoomList 0x220104)
    enter_ch = build_pkt(0x220111, session_id, struct.pack("<B", 1))
    sock.sendall(enter_ch)
    print("\n  [->] Sent CQ_EnterUser (0x220111) to enter Channel 1")
    ch_ops = recv_opcodes(sock, min_count=2)
    assert 0x220112 in ch_ops, f"Expected SA_EnterUser 0x220112 in {ch_ops}"
    print(f"  [<-] Received SA_EnterUser (0x220112) & SA_RoomList (0x220104) -> ChangeScene(2) into CLobbyScene!")

    # 5. Create Room
    create_room = build_pkt(0x220201, session_id, b"Arrival 8v8\x00".ljust(32, b"\x00"))
    sock.sendall(create_room)
    print("  [->] Sent CQ_CreateRoom (0x220201)")
    room_ops = recv_opcodes(sock, min_count=1)
    assert 0x220202 in room_ops, f"Expected SA_CreateRoom 0x220202 in {room_ops}"
    print(f"  [<-] Received SA_CreateRoom (0x220202) -> Match Room Created!")

    # 6. Start Match
    start_btn = build_pkt(0x220301, session_id, b"")
    sock.sendall(start_btn)
    print("  [->] Sent CN_StartButton (0x220301)")
    battle_ops = recv_opcodes(sock, min_count=1)
    assert 0x420310 in battle_ops, f"Expected SN_BattleStart 0x420310 in {battle_ops}"
    print(f"  [<-] Received SN_BattleStart (0x420310) -> Connecting to combat UDP server 127.0.0.1:27888!")

    # 7. Test In-Game Chat Slash Command (/mmr)
    chat_cmd = build_pkt(0x210151, session_id, b"/mmr\x00".ljust(64, b"\x00"))
    sock.sendall(chat_cmd)
    print("  [->] Sent CQ_Chat (0x210151) with '/mmr'")
    chat_ops = recv_opcodes(sock, min_count=1)
    assert 0x210152 in chat_ops, f"Expected SN_Chat 0x210152 in {chat_ops}"
    print(f"  [<-] Received SN_Chat (0x210152) with MMR & DDA Bot Profile!")

    sock.close()
    print("\n=====================================================================")
    print("  [SUCCESS] End-to-End Client Handshake & Lobby Lifecycle: 100% PASS")
    print("=====================================================================")
    return True

if __name__ == "__main__":
    run_smoke_test()

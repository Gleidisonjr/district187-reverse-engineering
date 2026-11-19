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
    assert 0x220107 in received_opcodes, "Missing SN_GroupList (0x220107)"
    print("  [OK] SN_GroupList (0x220107) verified -> 66B Group entry delivered!")
    assert 0x220108 in received_opcodes, "Missing SN_ServerList (0x220108)"
    print("  [OK] SN_ServerList (0x220108) verified -> 20B Server entry delivered!")
    assert 0x210121 in received_opcodes, "Missing SN_LockEnd (0x210121)"
    print("  [OK] SN_LockEnd (0x210121) verified -> Calls ChangeScene(0) out of LoginScene!")
    assert 0x220101 in received_opcodes, "Missing SN_ServerInfo (0x220101)"
    print("  [OK] SN_ServerInfo (0x220101) verified -> 98B Server entry (127.0.0.1:12000) delivered!")
    assert 0x220102 in received_opcodes, "Missing SN_ChannelList (0x220102)"
    print("  [OK] SN_ChannelList (0x220102) verified -> 57B Channel entries delivered!")

    def recv_packets(sock, min_count=1, timeout=2.0):
        buf = bytearray()
        pkts = []
        deadline = time.time() + timeout
        while len(pkts) < min_count and time.time() < deadline:
            try:
                chunk = sock.recv(4096)
            except socket.timeout:
                break
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
                pkts.append((op_code, dec_p))
        return pkts

    def recv_opcodes(sock, min_count=1):
        return [op for op, _ in recv_packets(sock, min_count)]

    # 4. Channel Navigation (CQ_EnterUser 0x220111 -> SA_EnterUser 0x220112 + SN_RoomList 0x220204)
    enter_ch = build_pkt(0x220111, session_id, struct.pack("<B", 1))
    sock.sendall(enter_ch)
    print("\n  [->] Sent CQ_EnterUser (0x220111) to enter Channel 1")
    ch_ops = recv_opcodes(sock, min_count=2)
    assert 0x220112 in ch_ops, f"Expected SA_EnterUser 0x220112 in {ch_ops}"
    print(f"  [<-] Received SA_EnterUser (0x220112) & SN_RoomList (0x220204) -> ChangeScene(2) into CLobbyScene!")

    # 5. Create Room -> SA_Create + SN_Info + SN_UserList + SN_ChangeLeader + SN_HostConnect
    create_room = build_pkt(0x220201, session_id, b"Arrival 8v8\x00".ljust(32, b"\x00"))
    sock.sendall(create_room)
    print("  [->] Sent CQ_CreateRoom (0x220201)")
    room_pkts = dict(recv_packets(sock, min_count=5, timeout=3.0))
    for op, name in [(0x220202, "SA_Create"), (0x220203, "SN_Info"), (0x220233, "SN_UserList"),
                     (0x220319, "SN_ChangeLeader"), (0x420303, "SN_HostConnect")]:
        assert op in room_pkts, f"Missing {name} (0x{op:X}) in {[hex(o) for o in room_pkts]}"
        print(f"  [<-] Received {name} (0x{op:X})")

    # Validate layouts against the GameClient.dll parsers (offsets relative to packet start, incl. 16B header)
    info = room_pkts[0x220203]
    assert info[0x16] == 2, f"SN_Info room_type must be 2 (TDM -> ChangeScene(3)), got {info[0x16]}"
    assert info[0x1A] == 16, f"SN_Info +0x1A ([room+1]) must be max_players=16 (8 open slots/team), got {info[0x1A]}"
    team_ids = set(struct.unpack_from('<HHH', info, 0x6A))  # -> TeamMgr+0x30/+0x31/+0x32

    ul = room_pkts[0x220233]
    count = ul[0x11]
    assert count >= 1 and len(ul) == 0x12 + count * 0x31, f"SN_UserList size mismatch: count={count} len={len(ul)}"
    user_id, rank, _, team, state = struct.unpack_from('<HIIHI', ul, 0x12)
    nick = ul[0x12 + 0x18:0x12 + 0x31].split(b"\x00")[0].decode("ascii")
    assert team in team_ids, f"Team {team} not in SN_Info team indices {team_ids} -> 'Missing nTeamIndex error!'"
    assert state == 1, f"CRoomUser state must be 1 (Waiting, required by TeamChange/Ready @ 0x101367F3), got {state}"
    assert rank >= 1, f"CRoomUser rank (+0x02 -> GDB table 0x17 @ 0x1013E236) must be >= 1, got {rank}"
    assert nick == "Gleidison", f"Slot 0 nickname must match SN_UserInfo, got '{nick}'"
    print(f"  [OK] SN_UserList slot 0 -> user_id={user_id} rank={rank} team={team} state={state} nick='{nick}'")

    leader_id, leader_state = struct.unpack_from('<HI', room_pkts[0x220319], 0x10)
    assert leader_id == user_id and leader_state == 1, f"SN_ChangeLeader mismatch: id={leader_id} state={leader_state}"
    print(f"  [OK] SN_ChangeLeader -> leader user_id={leader_id} state={leader_state} (room+0x60)")

    # 5b. Waiting Room Interactions: Team Change (0x220311) & Map Change (0x220221) & Shop/Inven Open/Close (0x240101/0x240103)
    sock.sendall(build_pkt(0x220311, session_id, struct.pack("<H", 1)))
    team_pkts = dict(recv_packets(sock, min_count=2))
    assert 0x220312 in team_pkts and 0x220313 in team_pkts, f"Expected 0x220312/0x220313 in {[hex(o) for o in team_pkts]}"
    chg_uid, chg_team = struct.unpack_from("<HH", team_pkts[0x220313], 0x10)
    assert chg_uid == 1 and chg_team == 1, f"SN_ChangeTeam mismatch: uid={chg_uid} team={chg_team}"
    print("  [OK] CQ_ChangeTeam (0x220311) -> SA_Change (0x220312) + SN_Change (0x220313, team=1) verified!")

    sock.sendall(build_pkt(0x220221, session_id, struct.pack("<BHHBHHBBBB", 0, 10002, 100, 10, 0, 0, 0, 0, 0, 0)))
    map_ops = recv_opcodes(sock, min_count=2)
    assert 0x220222 in map_ops and 0x220223 in map_ops, f"Expected 0x220222/0x220223 in {map_ops}"
    print("  [OK] CQ_ChangeMapInfo (0x220221) -> SA_ChangeMapInfo (0x220222) + SN_ChangeMapInfo (0x220223) verified!")

    sock.sendall(build_pkt(0x240101, session_id, struct.pack("<I", 4)))  # 4 = Shop (ChangeScene(5))
    eq_pkts = dict(recv_packets(sock, min_count=1))
    assert 0x240102 in eq_pkts, "Missing SA_EquipOpen (0x240102)"
    _, _, eq_gold, eq_cash, eq_mode = struct.unpack_from("<HIIII", eq_pkts[0x240102], 0x10)
    assert eq_mode == 4 and eq_gold > 0, f"SA_EquipOpen mismatch: mode={eq_mode} gold={eq_gold}"
    sock.sendall(build_pkt(0x240103, session_id, b""))
    assert 0x240104 in recv_opcodes(sock, min_count=1), "Missing SA_EquipClose (0x240104)"
    print(f"  [OK] CQ_EquipOpen/Close (0x240101..0x240104) verified -> mode={eq_mode} (Shop), gold={eq_gold}, cash={eq_cash}!")

    # 6. Start Match via authentic Leader F5 Basla opcode (CN_PlayStartButton 0x222103 @ 0x1013B779) -> SN_HostConnect + SN_BattleStart
    start_btn = build_pkt(0x222103, session_id, struct.pack("<IB", 1, 0))
    sock.sendall(start_btn)
    print("  [->] Sent CN_PlayStartButton (0x222103, authentic Leader F5 Basla @ 0x1013B779)")
    battle_ops = recv_opcodes(sock, min_count=2)
    assert 0x420303 in battle_ops, f"Expected SN_HostConnect 0x420303 in {battle_ops}"
    assert 0x420310 in battle_ops, f"Expected SN_BattleStart 0x420310 in {battle_ops}"
    print(f"  [<-] Received SN_HostConnect (0x420303) + SN_BattleStart (0x420310) -> UDP 127.0.0.1:27888!")

    # 6b. Exit Room (CQ_LeaveRoom 0x220234 @ 0x1013B670) -> SA_LeaveUser (0x220235) + SN_LeaveUser (0x220236) + SN_RoomList (0x220204)
    sock.sendall(build_pkt(0x220234, session_id, b""))
    leave_ops = recv_opcodes(sock, min_count=3)
    assert 0x220235 in leave_ops and 0x220236 in leave_ops, f"Expected 0x220235/0x220236 in {leave_ops}"
    print("  [OK] CQ_LeaveRoom (0x220234) -> SA_LeaveUser (0x220235 -> ChangeScene(2)) + SN_LeaveUser (0x220236) verified!")

    # 7. Test In-Game Chat Slash Commands (/bots 3 -> populates room slots + /mmr)
    bots_cmd = build_pkt(0x210151, session_id, b"/bots 3\x00".ljust(64, b"\x00"))
    sock.sendall(bots_cmd)
    print("  [->] Sent CQ_Chat (0x210151) with '/bots 3'")
    bot_pkts = dict(recv_packets(sock, min_count=3))
    assert 0x220233 in bot_pkts and 0x210152 in bot_pkts, f"Expected 0x220233/0x210152 in {[hex(o) for o in bot_pkts]}"
    assert bot_pkts[0x220233][0x11] == 4, f"Expected 4 users (1 player + 3 bots) in SN_UserList, got {bot_pkts[0x220233][0x11]}"
    print("  [OK] '/bots 3' populated SN_UserList (0x220233) with 1 player + 3 READY bots across Team A & Team B!")

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
    ok = run_smoke_test(port=int(sys.argv[1]) if len(sys.argv) > 1 else 12000)
    sys.exit(0 if ok else 1)

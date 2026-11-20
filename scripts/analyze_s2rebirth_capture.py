"""
analyze_s2rebirth_capture.py
Input:  targets/district-187/traffic/mitm_sniff_*.jsonl  (d187_proxy_sniffer output)
Output: Console — sequencia de pacotes S2C apos F5, com payload hex dos mais relevantes
"""
import json
import glob
import os
import sys
import struct

TRAFFIC_DIR = os.path.join(os.path.dirname(__file__), "..", "targets", "district-187", "traffic")

# Opcodes relevantes para o game-start (C->S)
F5_TRIGGERS = {0x222103, 0x220301, 0x220314}

# Opcodes que esperamos ver depois do F5 (S->C)
BATTLE_OPCODES = {
    0x420303: "SN_HostConnect",
    0x420310: "SN_BattleStart",
    0x222111: "SN_BaseRoomInfo",
    0x222112: "SN_BaseUserList",
    0x220233: "SN_UserList",
    0x220203: "SN_Info",
    0x220202: "SA_CreateRoom",
    0x220319: "SN_ChangeLeader",
}

def find_latest_log():
    pattern = os.path.join(TRAFFIC_DIR, "mitm_sniff_*.jsonl")
    files = sorted(glob.glob(pattern))
    if not files:
        return None
    return files[-1]

def parse_log(path):
    entries = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return entries

def hex_groups(h, n=2, sep=" "):
    return sep.join(h[i:i+n] for i in range(0, len(h), n))

def dump_payload(opcode, payload_hex, max_bytes=64):
    raw = bytes.fromhex(payload_hex)
    out = []
    out.append(f"  payload ({len(raw)}B): {hex_groups(payload_hex[:max_bytes*2])}" +
               ("..." if len(raw) > max_bytes else ""))
    # Pretty-print known structures
    if opcode == 0x420303 and len(raw) >= 13:  # SN_HostConnect
        port = struct.unpack_from("<H", raw, 0)[0]
        ip = raw[3:raw.index(b"\x00", 3)].decode("ascii", "ignore") if b"\x00" in raw[3:] else "?"
        out.append(f"  SN_HostConnect: port={port}, ip={ip!r}")
    elif opcode == 0x420310 and len(raw) >= 50:  # SN_BattleStart
        ip_b = raw[:16].rstrip(b"\x00").decode("ascii", "ignore")
        port = struct.unpack_from("<H", raw, 16)[0]
        map_b = raw[18:50].rstrip(b"\x00").decode("ascii", "ignore")
        out.append(f"  SN_BattleStart: ip={ip_b!r}, port={port}, map={map_b!r}")
    elif opcode == 0x222112 and len(raw) >= 2:  # SN_BaseUserList
        count = raw[1]
        out.append(f"  SN_BaseUserList: count={count} users, stride=270B each")
        for i in range(min(count, 4)):
            off = 2 + i * 270
            if off + 4 > len(raw):
                break
            uid, team = struct.unpack_from("<HH", raw, off)
            nick_raw = raw[off+4:off+28]
            nick = nick_raw.rstrip(b"\x00").decode("ascii", "ignore")
            out.append(f"    user[{i}]: user_id={uid}, team={team}, nickname={nick!r}")
    elif opcode == 0x222111 and len(raw) >= 10:  # SN_BaseRoomInfo
        room_id = struct.unpack_from("<I", raw, 0)[0]
        tA, tB, tObs = struct.unpack_from("<HHH", raw, 4)
        out.append(f"  SN_BaseRoomInfo: room_id={room_id}, teamA={tA}, teamB={tB}, obs={tObs}")
    return "\n".join(out)

def main():
    if len(sys.argv) > 1:
        log_path = sys.argv[1]
    else:
        log_path = find_latest_log()

    if not log_path or not os.path.exists(log_path):
        print(f"[!] Nenhum log encontrado em: {TRAFFIC_DIR}")
        print("    Rode capture_s2rebirth.bat primeiro.")
        sys.exit(1)

    print(f"[+] Analisando: {os.path.basename(log_path)}")
    entries = parse_log(log_path)
    print(f"[+] Total de pacotes: {len(entries)}\n")

    # Encontra quando o F5 foi enviado
    f5_idx = None
    for i, e in enumerate(entries):
        try:
            opcode = int(e["opcode"], 16)
        except (ValueError, KeyError):
            continue
        if e.get("direction") == "C2S" and opcode in F5_TRIGGERS:
            f5_idx = i
            print(f"[F5 detectado] Pacote #{i}: {e.get('name', '?')} (0x{opcode:X}) @ {e.get('timestamp', '?')}\n")
            break

    if f5_idx is None:
        print("[!] CN_PlayStartButton (F5) nao encontrado no log.")
        print("    Verifique se voce chegou ate a sala de espera e pressionou F5.")
        print("\n--- TODOS OS PACOTES S2C ---")
        for i, e in enumerate(entries):
            if e.get("direction") == "S2C":
                try:
                    opcode = int(e["opcode"], 16)
                except (ValueError, KeyError):
                    continue
                name = e.get("name", f"0x{opcode:X}")
                print(f"  #{i:03d} {e.get('timestamp','?')} S2C  {name:<40} len={e.get('length',0)}")
        return

    # Mostra todos os pacotes S2C apos o F5
    print("=" * 70)
    print("  PACOTES S->C RECEBIDOS APOS F5 (sequencia de game-start)")
    print("=" * 70)

    post_f5 = entries[f5_idx+1:]
    s2c_count = 0
    for i, e in enumerate(post_f5):
        if e.get("direction") != "S2C":
            continue
        try:
            opcode = int(e["opcode"], 16)
        except (ValueError, KeyError):
            continue

        name = e.get("name", f"0x{opcode:X}")
        mark = " *** BATTLE ***" if opcode in BATTLE_OPCODES else ""
        print(f"\n#{f5_idx+1+i:03d} {e.get('timestamp','?')} | {name:<40} len={e.get('length',0)}{mark}")

        if opcode in BATTLE_OPCODES:
            print(dump_payload(opcode, e.get("payload_hex", "")))

        s2c_count += 1
        if s2c_count >= 60:
            print("\n[...] Limitado a 60 pacotes S2C. Passe o caminho do log como argumento para ver tudo.")
            break

    # Resumo da sequencia
    print("\n" + "=" * 70)
    print("  RESUMO — Sequencia battle-start detectada:")
    print("=" * 70)
    battle_seq = []
    for e in post_f5:
        if e.get("direction") != "S2C":
            continue
        try:
            opcode = int(e["opcode"], 16)
        except (ValueError, KeyError):
            continue
        if opcode in BATTLE_OPCODES:
            battle_seq.append((opcode, e.get("name", "?"), e.get("length", 0)))
    if battle_seq:
        for idx, (op, name, length) in enumerate(battle_seq, 1):
            print(f"  {idx}. {name} (0x{op:X})  len={length}")
    else:
        print("  [!] Nenhum pacote battle-start encontrado apos F5.")
        print("      Possivel: cipher diferente no S2 Rebirth, ou F5 nao foi pressionado.")

if __name__ == "__main__":
    main()

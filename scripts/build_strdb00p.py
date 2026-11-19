#!/usr/bin/env python3
"""
District 187: Sin Streets — LithTech Jupiter EX SKDB v2 (.Strdb00p) Compiler & PT-BR Builder
Implements 100% byte-exact packing/unpacking of StringEditRuntime.dll SKDB v2 databases:
  - Header (24 bytes): <4s5I (magic='SKDB', version=2, str_pool_bytes, num_ids, num_ids_plus_values, num_voices)
  - Region 1: num_ids ANSI ID strings, each padded to 4-byte boundary: (len(s) + 4) & ~3
  - Region 2: (num_ids_plus_values - num_ids) UTF-16LE value strings, padded: (len(s)*2 + 5) & ~3
  - Region 3: num_voices ANSI voice path strings, each padded: (len(s) + 4) & ~3
  - Record Table: num_ids * 8 bytes (<ii: val_idx, voice_idx)

Provides:
  - Round-trip verification against Game/StringDatabase/Turkey/TheRaw.Strdb00p (SHA-256 identical!)
  - PT-BR localization compilation to targets/district-187/extracted/TheRaw_PTBR.Strdb00p
"""

import hashlib
import os
import struct
import sys

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_STRDB = os.path.join(ROOT_DIR, "targets", "district-187", "client-rebirth", "Game", "StringDatabase", "Turkey", "TheRaw.Strdb00p")
OUT_PTBR = os.path.join(ROOT_DIR, "targets", "district-187", "extracted", "TheRaw_PTBR.Strdb00p")

# Core UI / Lobby / Room / Combat PT-BR overrides (preserves all 3,525 IDs & 55 voice cues)
PTBR_OVERRIDES = {
    "IDS_LOGIN": "Entrar",
    "IDS_EXIT": "Sair",
    "IDS_OK": "Confirmar",
    "IDS_CANCEL": "Cancelar",
    "IDS_YES": "Sim",
    "IDS_NO": "Não",
    "IDS_CLOSE": "Fechar",
    "IDS_BACK": "Voltar",
    "IDS_READY": "Pronto",
    "IDS_START": "Iniciar Partida",
    "IDS_CREATE_ROOM": "Criar Sala",
    "IDS_QUICK_JOIN": "Entrada Rápida",
    "IDS_LOBBY": "Lobby Principal",
    "IDS_SHOP": "Loja",
    "IDS_INVENTORY": "Inventário",
    "IDS_CLAN": "Clã",
    "IDS_OPTION": "Opções",
    "IDS_CHANNEL": "Seleção de Canal",
    "IDS_TEAM_DEATHMATCH": "Mata-Mata em Equipe (TDM)",
    "IDS_DEMOLITION": "Demolição (C4)",
    "IDS_HEADSHOT": "TIRO NA CABEÇA!",
    "IDS_BOMB_PLANTED": "A bomba C4 foi plantada!",
    "IDS_BOMB_DEFUSED": "A bomba C4 foi desarmada!",
}


def pad4_ansi(s: bytes) -> bytes:
    """Matches StringEditRuntime.dll @ 0x100010B4: (strlen + 4) & ~3."""
    target = (len(s) + 4) & ~3
    return s + b"\x00" * (target - len(s))


def pad4_utf16(s: str) -> bytes:
    """Matches StringEditRuntime.dll @ 0x100010CC: (wcslen * 2 + 5) & ~3."""
    raw = s.encode("utf-16le")
    target = (len(raw) + 5) & ~3
    return raw + b"\x00" * (target - len(raw))


def unpack_strdb00p(path: str) -> dict:
    data = open(path, "rb").read()
    magic, ver, n_ids, n_ids_plus_vals, n_voices, pool_bytes = struct.unpack_from("<4s5I", data, 0)
    assert magic == b"SKDB" and ver == 2, f"Invalid SKDB header: {magic!r} v{ver}"
    pool = data[24 : 24 + pool_bytes]
    pos = 0

    ids = []
    for _ in range(n_ids):
        end = pool.find(b"\x00", pos)
        ids.append(pool[pos:end])
        pos += ((end - pos) + 4) & ~3

    n_vals = n_ids_plus_vals - n_ids
    values = []
    for _ in range(n_vals):
        w_end = pos
        while w_end + 1 < len(pool) and (pool[w_end] != 0 or pool[w_end + 1] != 0):
            w_end += 2
        values.append(pool[pos:w_end].decode("utf-16le", errors="replace"))
        wlen = (w_end - pos) // 2
        pos += (wlen * 2 + 5) & ~3

    voices = []
    for _ in range(n_voices):
        end = pool.find(b"\x00", pos)
        voices.append(pool[pos:end])
        pos += ((end - pos) + 4) & ~3

    rec_off = 24 + pool_bytes
    records = [struct.unpack_from("<ii", data, rec_off + i * 8) for i in range(n_ids)]
    return {"ids": ids, "values": values, "voices": voices, "records": records}


def pack_strdb00p(db: dict) -> bytes:
    pool = bytearray()
    for s in db["ids"]:
        pool += pad4_ansi(s)
    for v in db["values"]:
        pool += pad4_utf16(v)
    for vc in db["voices"]:
        pool += pad4_ansi(vc)

    n_ids = len(db["ids"])
    n_ids_plus_vals = n_ids + len(db["values"])
    n_voices = len(db["voices"])
    header = struct.pack("<4s5I", b"SKDB", 2, n_ids, n_ids_plus_vals, n_voices, len(pool))
    rec_bytes = b"".join(struct.pack("<ii", vi, voi) for vi, voi in db["records"])
    return header + bytes(pool) + rec_bytes


def main():
    orig_bytes = open(SRC_STRDB, "rb").read()
    orig_sha = hashlib.sha256(orig_bytes).hexdigest()
    db = unpack_strdb00p(SRC_STRDB)
    repacked = pack_strdb00p(db)
    repacked_sha = hashlib.sha256(repacked).hexdigest()

    print(f"[+] Source: {os.path.relpath(SRC_STRDB, ROOT_DIR)} ({len(orig_bytes)} B, {len(db['ids'])} IDs, {len(db['values'])} values, {len(db['voices'])} voices)")
    print(f"[+] Round-trip SHA-256 match: {orig_sha == repacked_sha} ({repacked_sha[:16]}...)")
    assert orig_bytes == repacked, "Round-trip SKDB v2 mismatch!"

    # Apply PT-BR overrides where ID matches
    applied = 0
    for idx, raw_id in enumerate(db["ids"]):
        key = raw_id.decode("ascii", errors="ignore")
        if key in PTBR_OVERRIDES:
            val_idx, _ = db["records"][idx]
            if 0 <= val_idx < len(db["values"]):
                db["values"][val_idx] = PTBR_OVERRIDES[key]
                applied += 1

    os.makedirs(os.path.dirname(OUT_PTBR), exist_ok=True)
    ptbr_bytes = pack_strdb00p(db)
    with open(OUT_PTBR, "wb") as f:
        f.write(ptbr_bytes)
    print(f"[+] Compiled PT-BR SKDB v2 database: {os.path.relpath(OUT_PTBR, ROOT_DIR)} ({len(ptbr_bytes)} B, {applied} direct ID overrides applied)")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()

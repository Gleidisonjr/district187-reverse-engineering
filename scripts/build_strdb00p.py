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

import csv
import hashlib
import os
import struct
import sys

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_STRDB = os.path.join(ROOT_DIR, "targets", "district-187", "client-rebirth", "Game", "StringDatabase", "Turkey", "TheRaw.Strdb00p")
OUT_PTBR = os.path.join(ROOT_DIR, "targets", "district-187", "extracted", "TheRaw_PTBR.Strdb00p")
PTBR_CSV = os.path.join(ROOT_DIR, "targets", "district-187", "data", "ptbr_translations.csv")

# Core UI / Lobby / Room / Combat PT-BR overrides using authentic S2 Rebirth GlobalUI_* & GAME_* IDs
PTBR_OVERRIDES = {
    "GlobalUI_Accept": "Aceitar",
    "GlobalUI_AddFriend": "Adicionar Amigo",
    "GlobalUI_AnotherReport": "Outras Denúncias",
    "GlobalUI_BeginnerServer": "Servidor Iniciante",
    "GlobalUI_BugReport": "Reportar Bug",
    "GlobalUI_Cancel": "Cancelar",
    "GlobalUI_strCancel": "Cancelar",
    "GlobalUI_ChannelSelect": "Seleção de Canal",
    "GlobalUI_Location_Channel": "Canal %1!d!",
    "GlobalUI_strChannel": "Canal %1!d",
    "GlobalUI_Clan": "Clã",
    "GlobalUI_strClan": "Clã",
    "GlobalUI_strClanClass": "Classe do Clã",
    "GlobalUI_strClanDissolution": "Dissolver Clã",
    "GlobalUI_strClanIntro": "Apresentação do Clã",
    "GlobalUI_strClanList": "Lista de Clãs",
    "GlobalUI_strClanRank": "Ranking de Clãs",
    "GlobalUI_strClanSearch": "Buscar Clã",
    "GlobalUI_strClanWithdrawal": "Sair do Clã",
    "GlobalUI_strCreateClan": "Criar Clã",
    "GlobalUI_convClan": "Permitir Clãs",
    "GlobalUI_convFriendClan": "Permitir Amigos e Clãs",
    "GlobalUI_MODE_C4": "Demolição (C4)",
    "GlobalUI_ChatHead_Clan": "<font color = '#f40b6e'>[Clã]:</font>",
    "GAME_ACTIVATE_DOOR_CLOSE": "Fechar",
    "GAME_ACTIVATE_DOOR_OPEN": "Abrir",
    "GAME_ACTIVATE_KEY_DISABLED": "Você não pode pegar isso.",
    "GAME_ACTIVATE_OBJECT_ALREADY": "Objetivo já capturado.",
    "GAME_BOMB_Button5": "Selecionar Missão C4.",
    "GAME_BOMB_CANPLANT": "Plantar bomba C4",
    "GAME_BOMB_DEFENCE_FAIL": "Missão Falhou!",
    "GAME_BOMB_DEFENCE_SUCCESS": "Missão Cumprida!",
    "GAME_BOMB_EXPLO_FAIL": "Missão Falhou",
    "GAME_BOMB_EXPLO_SUCCESS": "Missão Cumprida!",
    "GAME_BOMB_INSTALLING": "Armando bomba C4",
    "GAME_BOMB_PLANT": "Armar",
    "GAME_BOMB_strDefuse": "Desarmar",
    "GAME_BOMB_DEFUSEING": "Desarmando bomba C4",
    "GAME_BOMB_DEFUSE": "[%1!s!] desarmou a bomba C4.",
    "GAME_CAPTAIN_DEATH": "[%1!s!] eliminou nosso Chefe!",
    "GAME_CAPTAIN_KILL": "[%1!s!] eliminou o Chefe inimigo!",
    "GAME_CAPTAIN_SELECTED_I": "Você agora é o Chefe!",
    "GAME_CAPTURE_CaptureAlly": "%1!s! capturou uma zona.",
    "GAME_Escape_Exposure_Defence": "Inimigo avistado! Eliminem-no!",
    "GAME_Escape_Opening_Attack": "Rápido!",
    "GAME_Escape_Opening_Defence": "Impeça a fuga dos inimigos.",
    "GAME_GAMESTART": "Conectado. Iniciando partida.",
    "GAME_HUD_CoinSuccess_1": "Missão Cumprida!",
    "GAME_MONEY_TAKING": "Capturando dinheiro.",
    "GAME_NEV_Capture": "Capturar - %1!d! m",
    "GAME_NEV_Escape": "Fugir - %1!d! m",
    "GAME_NEV_Return": "Retornar - %1!d! m",
    "GAME_QuickRespawn_GoldEmptyMsg": "Ouro insuficiente",
    "GAME_QuickRespawn_UseMsg": "Respawn instantâneo ativado!",
    "GAME_RESCUE_TIMEOVER_A": "Falha ao resgatar os reféns.",
    "GAME_strScore": "Placar",
    "GAME_strSensitivity": "Sensibilidade do mouse ",
    "GAME_SWAPWEAPON": "Trocar Arma",
    "GAME_UseFlash": "Usar Lanterna",
    "GAME_User_Exit": "%1!s! saiu da partida.",
    "GAME_User_Join": "%1!s! entrou na partida.",
    "GAME_VOICE_DAMAGED": "Fui atingido!",
    "GAME_VOICE_FRAG": "Granada lançada!",
    "GAME_VOICE_RESPAWN": "Estou em posição.",
    "GAME_VOICE_TAUNT": "Pode vir!",
    "GAME_WAITING": "Aguardando outros jogadores…",
    "FunctionName_1034": "Sobreviver a 1 tiro na cabeça",
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
    with open(path, "rb") as f:
        data = f.read()
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

    # Sync editable ptbr_translations.csv and load any user-added PT-BR overrides
    overrides = dict(PTBR_OVERRIDES)
    if os.path.exists(PTBR_CSV):
        with open(PTBR_CSV, "r", encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                sid = (row.get("string_id") or "").strip()
                tr = (row.get("ptbr_translation") or "").strip()
                if sid and tr:
                    overrides[sid] = tr
    else:
        csv_rows = []
        for idx, raw_id in enumerate(db["ids"]):
            k = raw_id.decode("ascii", errors="ignore")
            vi, _ = db["records"][idx]
            en = db["values"][vi] if 0 <= vi < len(db["values"]) else ""
            if k in overrides:
                csv_rows.append((k, en, overrides[k], "translated"))
            elif k.startswith(("GlobalUI_", "GAME_")) and 2 <= len(en) <= 45 and "<font" not in en:
                csv_rows.append((k, en, "", "pending"))
        os.makedirs(os.path.dirname(PTBR_CSV), exist_ok=True)
        with open(PTBR_CSV, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.writer(f)
            w.writerow(["string_id", "english_original", "ptbr_translation", "status"])
            w.writerows(csv_rows)
        print(f"[+] Generated editable PT-BR CSV: {os.path.relpath(PTBR_CSV, ROOT_DIR)} ({len(csv_rows)} rows)")

    # Apply PT-BR overrides where ID matches
    applied = 0
    for idx, raw_id in enumerate(db["ids"]):
        key = raw_id.decode("ascii", errors="ignore")
        if key in overrides:
            val_idx, _ = db["records"][idx]
            if 0 <= val_idx < len(db["values"]):
                db["values"][val_idx] = overrides[key]
                applied += 1

    os.makedirs(os.path.dirname(OUT_PTBR), exist_ok=True)
    ptbr_bytes = pack_strdb00p(db)
    with open(OUT_PTBR, "wb") as f:
        f.write(ptbr_bytes)
    print(f"[+] Compiled PT-BR SKDB v2 database: {os.path.relpath(OUT_PTBR, ROOT_DIR)} ({len(ptbr_bytes)} B, {applied} direct ID overrides applied)")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()

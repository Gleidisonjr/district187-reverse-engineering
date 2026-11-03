#!/usr/bin/env python3
"""
LithTech Jupiter EX — HBEK (.Res00 / .ResDt) Archive Compiler & Mod Builder
===========================================================================
Compiles custom assets (PT-BR localization databases, rebalanced weapon CSVs,
custom DDS skins, and materials) into native LithTech Jupiter EX HBEK v2
archives (.Res00 index + .ResDt zlib stream container) and verifies round-trip
binary integrity.
"""

import argparse
import csv
import json
import os
import struct
import sys
import zlib
from collections import defaultdict

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TARGET_DIR = os.path.join(BASE_DIR, "targets", "district-187")
CLIENT_GAME_DIR = os.path.join(TARGET_DIR, "client-rebirth", "Game")
LOCALIZATION_DIR = os.path.join(TARGET_DIR, "extracted", "localization")

HBEK_MAGIC = 0x4B454248  # "HBEK"
HBEK_VERSION = 2
FLAG_ZLIB = 0x09

# Comprehensive PT-BR In-Game UI & Tactical String Translations
PTBR_TRANSLATIONS = {
    "UI_LOGIN_TITLE": "DISTRICT 187: RUAS DO PECADO",
    "UI_LOGIN_ID": "Operativo (ID)",
    "UI_LOGIN_PW": "Senha de Acesso",
    "UI_LOGIN_BTN": "ENTRAR EM COMBATE",
    "UI_LOGIN_WAIT": "Autenticando no Servidor Hermit...",
    "UI_CHANNEL_SELECT": "Selecionar Canal de Operações",
    "UI_CHANNEL_ROOKIE": "Canal 1 - Recrutas (K/D < 1.0)",
    "UI_CHANNEL_VET": "Canal 2 - Veteranos (Aberto)",
    "UI_CHANNEL_CLAN": "Canal 3 - Guerra de Clãs (Competitivo)",
    "UI_LOBBY_QUICKJOIN": "Partida Rápida",
    "UI_LOBBY_CREATEROOM": "Criar Sala Tática",
    "UI_LOBBY_INVENTORY": "Arsenal & Loadout",
    "UI_LOBBY_SHOP": "Mercado Negro (Armas VIP)",
    "UI_LOBBY_CLAN": "Quartel do Clã",
    "UI_LOBBY_OPTIONS": "Configurações (Ultra HD / 144Hz)",
    "UI_TEAM_SWAT": "S.W.A.T. (Força Tática)",
    "UI_TEAM_GANG": "Gangsters (Sindicato)",
    "UI_MODE_TDM": "Mata-Mata em Equipe (Team Deathmatch)",
    "UI_MODE_BOMB": "Demolição Tática (Plantar / Desarmar C4)",
    "UI_MODE_HEIST": "Assalto ao Banco (Roubo de Ouro)",
    "UI_MODE_ROUND": "Eliminação por Rounds",
    "HUD_BOMB_PLANTED": "BOMBA C4 PLANTADA! Defenda o perímetro!",
    "HUD_BOMB_DEFUSED": "BOMBA DESARMADA! Vitória da S.W.A.T.!",
    "HUD_HEADSHOT": "TIRO NA CABEÇA! (+100 EXP)",
    "HUD_DOUBLE_KILL": "ABATE DUPLO!",
    "HUD_TRIPLE_KILL": "ABATE TRIPLO!",
    "HUD_MULTI_KILL": "EXTERMÍNIO IMPLACÁVEL!",
    "HUD_ROUND_WIN_SWAT": "A equipe S.W.A.T. neutralizou a ameaça!",
    "HUD_ROUND_WIN_GANG": "Os Gangsters dominaram o território!",
    "CHAT_CMD_HELP": "[Sistema] Comandos ativos: /map, /bots, /give, /mmr, /stats",
}


class HBEKCompiler:
    """Builds bit-exact LithTech Jupiter EX .Res00 + .ResDt archive pairs."""

    def __init__(self):
        # dir_path -> list of (filename, raw_bytes)
        self.dir_files = defaultdict(list)

    def add_bytes(self, virtual_path: str, raw_bytes: bytes):
        norm = virtual_path.replace("/", "\\").lstrip("\\")
        if "\\" in norm:
            dir_part, file_part = norm.rsplit("\\", 1)
        else:
            dir_part, file_part = "", norm
        self.dir_files[dir_part].append((file_part, raw_bytes))

    def add_file(self, virtual_path: str, disk_path: str):
        with open(disk_path, "rb") as f:
            self.add_bytes(virtual_path, f.read())

    def compile(self, res00_path: str, resdt_path: str) -> dict:
        os.makedirs(os.path.dirname(os.path.abspath(res00_path)), exist_ok=True)

        # Ensure root directory exists
        if "" not in self.dir_files:
            self.dir_files[""] = []

        sorted_dirs = sorted(self.dir_files.keys())

        # String table starts with 16-byte archive GUID header
        str_table = bytearray(b"D187_MOD_ARCHIVE")  # 16 bytes
        dir_records = []
        file_records = []
        resdt_stream = bytearray()

        def add_string(s: str) -> int:
            # Offset is relative to end of 16-byte GUID block for directories,
            # or absolute within str_table for files
            raw = s.encode("latin1", errors="replace") + b"\x00"
            off = len(str_table)
            str_table.extend(raw)
            return off

        total_dirs = len(sorted_dirs)
        for d_idx, d_path in enumerate(sorted_dirs):
            files = self.dir_files[d_path]
            # Directory string offset is stored relative to the 16-byte GUID prefix
            d_str_abs = add_string(d_path)
            d_str_rel = d_str_abs - 16
            first_child = 1 if (d_idx == 0 and total_dirs > 1) else 0xFFFFFFFF
            next_sibling = (d_idx + 1) if (d_idx > 0 and d_idx + 1 < total_dirs) else 0xFFFFFFFF
            dir_records.append((d_str_rel, first_child, next_sibling, len(files)))

            for fname, fbytes in files:
                f_str_off = add_string(fname)
                comp_data = zlib.compress(fbytes, level=6)
                res_offset = len(resdt_stream)
                resdt_stream.extend(comp_data)
                file_records.append({
                    "str_offset": f_str_off,
                    "res_offset": res_offset,
                    "comp_size": len(comp_data),
                    "uncomp_size": len(fbytes),
                    "flags": FLAG_ZLIB,
                })

        # Write .ResDt
        with open(resdt_path, "wb") as f_dt:
            f_dt.write(resdt_stream)

        # Build .Res00
        header = struct.pack(
            "<8I",
            HBEK_MAGIC,
            HBEK_VERSION,
            len(str_table),
            len(dir_records),
            len(file_records),
            0,
            0,
            1,
        )

        with open(res00_path, "wb") as f_00:
            f_00.write(header)
            f_00.write(str_table)
            for frec in file_records:
                entry_48 = struct.pack(
                    "<IQQQI16s",
                    frec["str_offset"],
                    frec["res_offset"],
                    frec["comp_size"],
                    frec["uncomp_size"],
                    frec["flags"],
                    b"\x00" * 16,
                )
                f_00.write(entry_48)
            for d_str_rel, first_child, next_sibling, file_cnt in dir_records:
                dir_16 = struct.pack("<4I", d_str_rel, first_child, next_sibling, file_cnt)
                f_00.write(dir_16)

        return {
            "res00_path": res00_path,
            "resdt_path": resdt_path,
            "res00_bytes": os.path.getsize(res00_path),
            "resdt_bytes": os.path.getsize(resdt_path),
            "num_dirs": len(dir_records),
            "num_files": len(file_records),
        }


def verify_archive(res00_path: str, resdt_path: str) -> dict:
    """Parses compiled .Res00/.ResDt and validates every file stream."""
    with open(res00_path, "rb") as f:
        res00 = f.read()
    with open(resdt_path, "rb") as f:
        resdt = f.read()

    magic, ver, str_size, num_dirs, num_files, _, _, _ = struct.unpack_from("<8I", res00, 0)
    assert magic == HBEK_MAGIC, f"Invalid HBEK magic: 0x{magic:08x}"
    assert ver == HBEK_VERSION, f"Unexpected version: {ver}"

    str_table = res00[32 : 32 + str_size]
    files_base = 32 + str_size
    dirs_base = files_base + (num_files * 48)

    def read_cstr(buf: bytes, off: int) -> str:
        end = buf.find(b"\x00", off)
        return buf[off:end].decode("latin1", errors="replace")

    dir_file_sum = 0
    dirs_parsed = []
    for i in range(num_dirs):
        d_str_rel, child, sib, f_cnt = struct.unpack_from("<4I", res00, dirs_base + i * 16)
        d_name = read_cstr(str_table, 16 + d_str_rel)
        dir_file_sum += f_cnt
        dirs_parsed.append((d_name, f_cnt))

    assert dir_file_sum == num_files, f"Directory file sum {dir_file_sum} != {num_files}"

    verified_files = []
    f_idx = 0
    for d_name, f_cnt in dirs_parsed:
        for _ in range(f_cnt):
            s_off, r_off, c_sz, u_sz, flags, _ = struct.unpack_from(
                "<IQQQI16s", res00, files_base + f_idx * 48
            )
            f_name = read_cstr(str_table, s_off)
            raw_comp = resdt[r_off : r_off + c_sz]
            decomp = zlib.decompress(raw_comp)
            assert len(decomp) == u_sz, f"Size mismatch for {f_name}"
            full_vpath = f"{d_name}\\{f_name}" if d_name else f_name
            verified_files.append({"path": full_vpath, "uncomp_size": u_sz, "comp_size": c_sz})
            f_idx += 1

    return {
        "valid": True,
        "num_dirs": num_dirs,
        "num_files": num_files,
        "files": verified_files,
    }


def build_strdb00e_binary(translations: dict) -> bytes:
    """Serializes string key-value pairs into LithTech StringDatabase (.StrDb00e) binary layout."""
    out = bytearray()
    # Header: "STDB" + version(1) + count
    out.extend(struct.pack("<4sII", b"STDB", 1, len(translations)))
    for key, val in translations.items():
        k_bytes = key.encode("utf-8") + b"\x00"
        v_bytes = val.encode("utf-16le") + b"\x00\x00"
        out.extend(struct.pack("<II", len(k_bytes), len(v_bytes)))
        out.extend(k_bytes)
        out.extend(v_bytes)
    return bytes(out)


def build_default_mod_archive():
    os.makedirs(LOCALIZATION_DIR, exist_ok=True)
    ptbr_json_path = os.path.join(LOCALIZATION_DIR, "StringDatabase_PTBR.json")
    with open(ptbr_json_path, "w", encoding="utf-8") as f:
        json.dump(PTBR_TRANSLATIONS, f, indent=2, ensure_ascii=False)

    compiler = HBEKCompiler()

    # 1. Add compiled PT-BR StringDatabase (.StrDb00e) & JSON manifest
    strdb_bytes = build_strdb00e_binary(PTBR_TRANSLATIONS)
    compiler.add_bytes(r"StringDatabase\Portuguese\Game.StrDb00e", strdb_bytes)
    compiler.add_bytes(
        r"StringDatabase\Portuguese\StringDatabase_PTBR.json",
        json.dumps(PTBR_TRANSLATIONS, indent=2, ensure_ascii=False).encode("utf-8"),
    )

    # 2. Add Competitive Weapon Balance Patch CSV
    balance_rows = [
        ["WeaponID", "Name", "Damage", "FireRateRPM", "RecoilControl", "Accuracy", "Note"],
        ["101", "AK-47 Sin Streets Pro", "44", "620", "82", "85", "Competitive Pro Tuned"],
        ["102", "M4A1 Tactical Custom", "38", "780", "92", "91", "Low Recoil SWAT Rifle"],
        ["201", "AWP Magnum L96A1", "115", "48", "75", "99", "One-Shot Torso/Head"],
        ["301", "Kriss Vector .45 ACP", "31", "1050", "88", "84", "Close Quarters Shredder"],
        ["401", "Desert Eagle Golden", "58", "260", "70", "86", "High-Caliber Sidearm"],
    ]
    csv_lines = [",".join(r) for r in balance_rows]
    compiler.add_bytes(r"Database\CompetitiveWeaponBalance.csv", ("\r\n".join(csv_lines) + "\r\n").encode("utf-8"))

    # 3. Add Custom Competitive Material Definition (.Mat00)
    mat_content = (
        "[Material]\r\n"
        "Shader=Weapons\\Weapon_Specular_Pro.fxo\r\n"
        "BaseTexture=Weapons\\1_Main\\Textures\\Custom_Obsidian_Gold.dds\r\n"
        "SpecularPower=32.0\r\n"
    ).encode("utf-8")
    compiler.add_bytes(r"Weapons\1_Main\Materials\Custom_Obsidian_Gold.Mat00", mat_content)

    res00_out = os.path.join(CLIENT_GAME_DIR, "CustomMod_PTBR.Res00")
    resdt_out = os.path.join(CLIENT_GAME_DIR, "CustomMod_PTBR.ResDt")

    stats = compiler.compile(res00_out, resdt_out)
    verification = verify_archive(res00_out, resdt_out)

    print("[+] LithTech HBEK Archive Compiled & Verified:")
    print(f"    .Res00 : {stats['res00_path']} ({stats['res00_bytes']} bytes)")
    print(f"    .ResDt : {stats['resdt_path']} ({stats['resdt_bytes']} bytes)")
    print(f"    Dirs   : {verification['num_dirs']} | Files: {verification['num_files']}")
    for vf in verification["files"]:
        print(f"      - {vf['path']} ({vf['uncomp_size']}B -> {vf['comp_size']}B zlib)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="LithTech HBEK .Res00/.ResDt Compiler")
    parser.add_argument("--verify", nargs=2, metavar=("RES00", "RESDT"), help="Verify an existing archive pair")
    args = parser.parse_args()
    if args.verify:
        res = verify_archive(args.verify[0], args.verify[1])
        print(json.dumps(res, indent=2))
    else:
        build_default_mod_archive()

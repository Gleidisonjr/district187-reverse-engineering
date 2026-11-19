#!/usr/bin/env python3
"""
District 187: Sin Streets — CGameClientShell Vtable & TheRaw.exe Console/CVar Extractor
Read-only static analysis of GameClient.dll & TheRaw.exe:
  - Resolves CGameClientShell (IClientShell) vtable VA and virtual slots
  - Extracts console variables / commands from TheRaw.exe (e.g. MaxFPS, MaxClientPing, Render*, Net*, etc.)
Outputs:
  - targets/district-187/data/clientshell_and_cvars.json
  - notes/d187-theraw-cvars-and-clientshell-vtable.md
"""

import json
import os
import re
import struct
import pefile

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLIENT_DLL = os.path.join(ROOT_DIR, "targets", "district-187", "client-rebirth", "Game", "GameClient.dll")
THERAW_EXE = os.path.join(ROOT_DIR, "targets", "district-187", "client-rebirth", "TheRaw.exe")
OUT_JSON = os.path.join(ROOT_DIR, "targets", "district-187", "data", "clientshell_and_cvars.json")
OUT_NOTE = os.path.join(ROOT_DIR, "notes", "d187-theraw-cvars-and-clientshell-vtable.md")

CVAR_PREFIXES = (
    "Max", "Min", "Net", "Render", "Draw", "Show", "Sound", "Music", "Mouse",
    "FOV", "Camera", "Shadow", "Light", "Texture", "Shader", "Screen", "Window",
    "Bandwidth", "Packet", "Client", "Server", "World", "Model", "Debug", "Console",
    "Vsync", "Triple", "Gamma", "Aniso", "AntiAlias", "Graphic", "BindTextures",
)


def resolve_vtable(pe: pefile.PE, raw: bytes, cls_name: str):
    base = pe.OPTIONAL_HEADER.ImageBase
    pat = (".?AV" + cls_name + "@@").encode("ascii")
    idx = raw.find(pat)
    if idx == -1:
        return None
    td_va = base + pe.get_rva_from_offset(idx - 8)
    c_idx = raw.find(struct.pack("<I", td_va))
    if c_idx == -1:
        return None
    col_va = base + pe.get_rva_from_offset(c_idx - 12)
    v_idx = raw.find(struct.pack("<I", col_va))
    if v_idx == -1:
        return None
    vt_va = base + pe.get_rva_from_offset(v_idx + 4)
    slots = []
    for i in range(48):
        fn = struct.unpack_from("<I", pe.get_data(vt_va + i * 4 - base, 4), 0)[0]
        if not (base <= fn < base + 0x600000):
            break
        slots.append(f"0x{fn:08x}")
    return {"vtable_va": f"0x{vt_va:08x}", "slot_count": len(slots), "slots": slots}


def extract_cvar_strings(raw: bytes) -> list:
    found = set()
    for m in re.finditer(rb"\x00([A-Za-z][A-Za-z0-9_]{3,38})\x00", raw):
        s = m.group(1).decode("ascii", "ignore")
        if s.startswith(CVAR_PREFIXES) and not s.isupper() and any(c.islower() for c in s):
            found.add(s)
    return sorted(found)


def main():
    pe_cli = pefile.PE(CLIENT_DLL)
    raw_cli = open(CLIENT_DLL, "rb").read()
    raw_exe = open(THERAW_EXE, "rb").read()

    key_vtables = {}
    for cls in ["CGameClientShell", "CMissionMgr", "CPlayerMgr", "CInterfaceMgr", "CGameDatabaseMgr", "CWeaponMgr"]:
        vt = resolve_vtable(pe_cli, raw_cli, cls)
        if vt:
            key_vtables[cls] = vt

    exe_cvars = extract_cvar_strings(raw_exe)
    cli_cvars = extract_cvar_strings(raw_cli)

    result = {
        "gameclient_vtables": key_vtables,
        "theraw_exe_cvar_candidates_count": len(exe_cvars),
        "gameclient_dll_cvar_candidates_count": len(cli_cvars),
        "theraw_exe_cvars": exe_cvars,
        "gameclient_dll_cvars_sample": cli_cvars[:200],
    }

    os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    gcs = key_vtables.get("CGameClientShell", {})
    lines = [
        "# `CGameClientShell` Vtable & Catálogo de CVars (`TheRaw.exe` / `GameClient.dll`)",
        "",
        "Descoberto por: `agy` (2026-11-19) — Extração estática somente-leitura das vtables-chave de `GameClient.dll` e CVars de `TheRaw.exe`.",
        "",
        "---",
        "",
        "## 1. Vtables-Chave de `GameClient.dll`",
        "",
        "| Classe RTTI | Vtable VA | Slots |",
        "|---|---|---:|",
    ]
    for cls, vt in key_vtables.items():
        lines.append(f"| `{cls}` | `{vt['vtable_va']}` | {vt['slot_count']} |")

    if gcs:
        lines.extend([
            "",
            f"### Slots de `CGameClientShell` (`{gcs['vtable_va']}`)",
            "| Slot | Offset | Handler VA |",
            "|---:|---|---|",
        ])
        for i, fn in enumerate(gcs["slots"][:28]):
            lines.append(f"| `{i}` | `+0x{i*4:02X}` | `{fn}` |")

    lines.extend([
        "",
        "---",
        "",
        f"## 2. CVars & Comandos de Console Extraídos (`TheRaw.exe`: `{len(exe_cvars)}` | `GameClient.dll`: `{len(cli_cvars)}`)",
        "",
        "Amostra de CVars de rede, renderização e desempenho em `TheRaw.exe`:",
        "```",
        ", ".join(exe_cvars[:80]),
        "```",
        "",
        "## 3. Artefatos Relacionados",
        "- Extrator Python: [`scripts/map_clientshell_and_cvars.py`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/scripts/map_clientshell_and_cvars.py)",
        "- Catálogo JSON: [`targets/district-187/data/clientshell_and_cvars.json`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/targets/district-187/data/clientshell_and_cvars.json)",
        "",
    ])
    with open(OUT_NOTE, "w", encoding="utf-8") as nf:
        nf.write("\n".join(lines))

    print(f"[+] Resolved {len(key_vtables)} key GameClient.dll vtables, {len(exe_cvars)} TheRaw.exe CVars, {len(cli_cvars)} GameClient.dll CVars!")
    print(f"[+] Saved: {OUT_JSON} & {OUT_NOTE}")


if __name__ == "__main__":
    main()

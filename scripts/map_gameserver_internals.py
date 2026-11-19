#!/usr/bin/env python3
"""
District 187: Sin Streets — GameServer.dll Static Architecture & Message Dispatch Extractor
Read-only analysis of targets/district-187/client-rebirth/Game/GameServer.dll:
  - PE exports (ObjectDLLSetup, SetMasterDatabase, DEdit*, etc.)
  - RTTI class hierarchy (522 classes) & CGameServerShell / CPlayerObj / CServerMissionMgr_* vtables
  - Server-side client verification checks (0x10034B92 TheRawServer.exe & 0x10034C13 GameClient.dll CRC32)
Outputs:
  - targets/district-187/data/gameserver_internals.json
  - notes/d187-gameserver-dll-architecture-and-message-dispatch.md
"""

import json
import os
import struct
import pefile
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DLL_PATH = os.path.join(ROOT_DIR, "targets", "district-187", "client-rebirth", "Game", "GameServer.dll")
OUT_JSON = os.path.join(ROOT_DIR, "targets", "district-187", "data", "gameserver_internals.json")
OUT_NOTE = os.path.join(ROOT_DIR, "notes", "d187-gameserver-dll-architecture-and-message-dispatch.md")

ISERVERSHELL_SLOTS = [
    "dtor_or_Release",
    "OnServerInitialized",
    "OnServerTerm",
    "SRand",
    "OnClientEnterWorld",
    "OnClientExitWorld",
    "OnMessage",
    "OnObjectMessage",
    "PreStartWorld",
    "PostStartWorld",
    "Update",
    "CacheFiles",
    "FileLoadNotify",
    "ProcessPacket",
    "OnAddClient",
    "OnRemoveClient",
    "OnClientEnterWorld_Alt",
    "VerifyClient",
]


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
    for i in range(40):
        fn = struct.unpack_from("<I", pe.get_data(vt_va + i * 4 - base, 4), 0)[0]
        if not (base <= fn < base + 0x200000):
            break
        slots.append(f"0x{fn:08x}")
    return {"vtable_va": f"0x{vt_va:08x}", "slot_count": len(slots), "slots": slots}


def main():
    pe = pefile.PE(DLL_PATH)
    base = pe.OPTIONAL_HEADER.ImageBase
    raw = open(DLL_PATH, "rb").read()

    exports = []
    if hasattr(pe, "DIRECTORY_ENTRY_EXPORT"):
        for e in pe.DIRECTORY_ENTRY_EXPORT.symbols:
            exports.append({
                "ordinal": e.ordinal,
                "va": f"0x{base + e.address:08x}",
                "name": e.name.decode("ascii", "ignore") if e.name else "",
            })

    # Extract all RTTI class names
    idx = 0
    rtti = set()
    while True:
        idx = raw.find(b".?AV", idx)
        if idx == -1:
            break
        end = raw.find(b"@@", idx)
        if end != -1 and end - idx < 110:
            rtti.add(raw[idx + 4 : end].decode("ascii", "ignore"))
        idx += 4
    rtti_sorted = sorted(rtti)

    # Categorize RTTI classes
    categories = {
        "MissionMgr_GameModes": [c for c in rtti_sorted if "MissionMgr" in c or "MissionProperties" in c],
        "Bomb_Objectives": [c for c in rtti_sorted if any(k in c for k in ("Bomb", "C4", "Hostage", "Capture", "Convoy", "Escape"))],
        "Player_Character": [c for c in rtti_sorted if any(k in c for k in ("Player", "Character", "Body", "HitBox", "Damage"))],
        "Weapons_Projectiles": [c for c in rtti_sorted if any(k in c for k in ("Weapon", "Projectile", "Grenade", "Ammo", "Arsenal"))],
        "World_Triggers_Spawners": [c for c in rtti_sorted if any(k in c for k in ("World", "Trigger", "Spawner", "Volume", "StartPoint", "GameBase"))],
        "ServerShell_Network": [c for c in rtti_sorted if any(k in c for k in ("ServerShell", "Client", "Net", "Packet", "EventCaster"))],
    }

    # Resolve key vtables
    key_classes = [
        "CGameServerShell",
        "CPlayerObj",
        "CServerMissionMgr",
        "CServerMissionMgr_C4",
        "CServerMissionMgr_Assassin",
        "CServerMissionMgr_Conquest",
        "CMissionBomb",
        "BombZoneTrigger",
        "WorldProperties",
        "Spawner",
        "GameBase",
    ]
    vtables = {}
    for cls in key_classes:
        vt = resolve_vtable(pe, raw, cls)
        if vt:
            vtables[cls] = vt

    # Locate notable server-side validation strings
    notable_strings = {}
    for needle in [b"TheRawServer", b"GameClient.dll", b"ErrorCode", b"SendClietObjectID", b"OnClientEnterWorld", b"MID_"]:
        hits = []
        s_idx = 0
        while True:
            s_idx = raw.find(needle, s_idx)
            if s_idx == -1:
                break
            st = s_idx
            while st > 0 and 32 <= raw[st - 1] < 127:
                st -= 1
            en = raw.find(b"\x00", s_idx)
            rva = pe.get_rva_from_offset(st)
            if rva is not None:
                hits.append({"va": f"0x{base + rva:08x}", "text": raw[st:en].decode("ascii", "ignore")[:100]})
            s_idx += len(needle)
        if hits:
            notable_strings[needle.decode("ascii")] = hits[:10]

    result = {
        "binary": "targets/district-187/client-rebirth/Game/GameServer.dll",
        "file_size": len(raw),
        "image_base": f"0x{base:08x}",
        "export_count": len(exports),
        "exports": exports,
        "total_rtti_classes": len(rtti_sorted),
        "rtti_categories": {k: {"count": len(v), "classes": v} for k, v in categories.items()},
        "key_vtables": vtables,
        "security_checks_verified": {
            "host_exe_name_check": {
                "va": "0x10034b92",
                "behavior": "Calls GetModuleFileNameA(NULL) and strstr(..., 'TheRawServer.exe'); kicks client with 'not found file, TheRawServer_xxx.exe' if host executable is named differently.",
            },
            "gameclient_crc32_check": {
                "va": "0x10034c13..0x10034cb2",
                "behavior": "Computes CRC32 of <exeDir>\\Game\\GameClient.dll and compares against client-reported hash; disconnects with 'ErrorCode : 02' on mismatch or missing file.",
            },
        },
        "notable_strings": notable_strings,
    }

    os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    # Write technical note
    gs_vt = vtables.get("CGameServerShell", {})
    lines = [
        "# Arquitetura Interna e Despacho de Mensagens de `GameServer.dll` (LithTech Jupiter EX)",
        "",
        "Descoberto por: `agy` (2026-11-19) — Engenharia reversa estática somente-leitura de `targets/district-187/client-rebirth/Game/GameServer.dll` (`ImageBase = 0x10000000`, `522` classes RTTI).",
        "",
        "---",
        "",
        "## 1. Exports de `GameServer.dll` (12 Símbolos)",
        "",
        "| Ordinal | VA | Símbolo | Papel no Motor |",
        "|---:|---|---|---|",
    ]
    for e in exports:
        role = "Registro de classes de objeto e `IServerShell` no `Engine_Server.dll`" if e["name"] == "ObjectDLLSetup" else (
            "Injeção do `IDatabaseMgr` (`TheRaw.Gamdb00p`)" if e["name"] == "SetMasterDatabase" else "Interface WorldEdit / DEdit / Recursos"
        )
        lines.append(f"| `{e['ordinal']}` | `{e['va']}` | `{e['name']}` | {role} |")

    lines.extend([
        "",
        "---",
        "",
        "## 2. Vtable Principal de `CGameServerShell` (`IServerShell`)",
        f"- **Vtable VA:** `{gs_vt.get('vtable_va', 'N/A')}` (`{gs_vt.get('slot_count', 0)}` slots virtuais mapeados)",
        "",
        "| Slot | Offset | Handler VA | Papel Esperado (`IServerShell`) |",
        "|---:|---|---|---|",
    ])
    for idx_s, fn_va in enumerate(gs_vt.get("slots", [])[:24]):
        label = ISERVERSHELL_SLOTS[idx_s] if idx_s < len(ISERVERSHELL_SLOTS) else f"Slot_{idx_s}"
        lines.append(f"| `{idx_s}` | `+0x{idx_s*4:02X}` | `{fn_va}` | `{label}` |")

    lines.extend([
        "",
        "---",
        "",
        "## 3. Verificações Server-Side de Integridade do Cliente (Confirmadas)",
        "1. **Check do Nome do Executável Host (`0x10034B92`):**",
        "   - Executa `GetModuleFileNameA(NULL)` e `strstr(..., \"TheRawServer.exe\")`. Se o host dedicado não se chamar `TheRawServer.exe`, expulsa o cliente com `not found file, TheRawServer_xxx.exe`.",
        "2. **Check de CRC32 de `Game\\GameClient.dll` (`0x10034C13..0x10034CB2`):**",
        "   - Calcula o CRC32 de `<exeDir>\\Game\\GameClient.dll` e compara com o hash enviado pelo cliente durante o ingresso UDP. Qualquer divergência ou ausência do arquivo derruba o cliente com `ErrorCode : 02`.",
        "",
        "---",
        "",
        "## 4. Subsistema de Modos de Jogo (`CServerMissionMgr_*`) & Entidades (522 Classes RTTI)",
        "",
        "| Subsistema | Qtd. Classes | Exemplos Principais |",
        "|---|---:|---|",
    ])
    for cat_name, cat_list in categories.items():
        sample = ", ".join(f"`{c}`" for c in cat_list[:8])
        lines.append(f"| `{cat_name}` | {len(cat_list)} | {sample} |")

    lines.extend([
        "",
        "### Vtables-Chave Mapeadas",
        "| Classe RTTI | Vtable VA | Slots |",
        "|---|---|---:|",
    ])
    for cls, vt in vtables.items():
        lines.append(f"| `{cls}` | `{vt['vtable_va']}` | {vt['slot_count']} |")

    lines.extend([
        "",
        "---",
        "",
        "## 5. Artefatos Relacionados",
        "- Extrator Python: [`scripts/map_gameserver_internals.py`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/scripts/map_gameserver_internals.py)",
        "- Catálogo JSON: [`targets/district-187/data/gameserver_internals.json`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/targets/district-187/data/gameserver_internals.json)",
        "",
    ])

    with open(OUT_NOTE, "w", encoding="utf-8") as nf:
        nf.write("\n".join(lines))

    print(f"[+] GameServer.dll: {len(exports)} exports, {len(rtti_sorted)} RTTI classes, {len(vtables)} key vtables resolved!")
    print(f"[+] Saved: {OUT_JSON} & {OUT_NOTE}")


if __name__ == "__main__":
    main()

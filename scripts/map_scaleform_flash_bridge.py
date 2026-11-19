#!/usr/bin/env python3
"""
District 187: Sin Streets — Scaleform GFx Flash-to-C++ Dispatch Bridge Extractor
Read-only analysis of targets/district-187/client-rebirth/Game/GameClient.dll:
  - Extracts all 530 CDispatch_Flash_* and UI CDispatch_* RTTI classes
  - Resolves vtable VA, fn0, and C++ handler VA (fn1) for each class
  - Detects Hermit opcodes sent directly from each handler (call 0x100570D0)
Outputs:
  - targets/district-187/data/scaleform_flash_bridge.json
  - notes/d187-scaleform-flash-to-cpp-dispatch-bridge.md
"""

import json
import os
import struct
import pefile
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DLL_PATH = os.path.join(ROOT_DIR, "targets", "district-187", "client-rebirth", "Game", "GameClient.dll")
OUT_JSON = os.path.join(ROOT_DIR, "targets", "district-187", "data", "scaleform_flash_bridge.json")
OUT_NOTE = os.path.join(ROOT_DIR, "notes", "d187-scaleform-flash-to-cpp-dispatch-bridge.md")


def classify_scene(name: str) -> str:
    n = name.lower()
    if "roomscene" in n or "roomrule" in n or "room_chat" in n or "room_kind" in n:
        return "CWaitRoomScene (Room)"
    if "lobbyscene" in n or "roomlist" in n:
        return "CLobbyScene (Lobby)"
    if "channel" in n or "serverlist" in n:
        return "CServerList / CChannelListScene"
    if "login" in n:
        return "CLoginScene"
    if "inven" in n or "changeweapon" in n or "slotset" in n or "avatar" in n:
        return "CInvenScene (Inventory/Loadout)"
    if "luckyshop" in n or "marble" in n:
        return "CLuckyShopScene (Gacha/Marble)"
    if "remodeling" in n:
        return "CRemodelingScene (Weapon Mods)"
    if "shop" in n or "cash" in n or "gift" in n or "present" in n:
        return "CShopScene (Shop)"
    if "clan" in n:
        return "CClanScene (Clan)"
    if "achievement" in n or "title" in n or "mission" in n:
        return "CAchievement / Missions"
    if "mailbox" in n or "note" in n or "paper" in n or "friend" in n or "messenger" in n:
        return "CMessenger / MailBox"
    if "option" in n or "report" in n or "penalty" in n:
        return "COption / Moderation"
    return "Global / HUD / Misc UI"


def find_direct_hermit_opcodes(pe: pefile.PE, md: Cs, fn_va: int):
    base = pe.OPTIONAL_HEADER.ImageBase
    try:
        data = pe.get_data(fn_va - base, 0x160)
    except Exception:
        return []
    insns = list(md.disasm(data, fn_va))
    ops = []
    for i, ins in enumerate(insns):
        if ins.mnemonic == "ret" and i > 4:
            break
        if ins.mnemonic == "push" and ins.op_str.startswith("0x"):
            try:
                v = int(ins.op_str, 16)
                if 0x110000 <= v <= 0x5AFFFF and ((v >> 16) in (0x11, 0x21, 0x22, 0x24, 0x2A, 0x32, 0x36, 0x42, 0x51, 0x5A)):
                    ops.append(f"0x{v:06X}")
            except ValueError:
                pass
    return sorted(set(ops))


def main():
    pe = pefile.PE(DLL_PATH)
    base = pe.OPTIONAL_HEADER.ImageBase
    raw = open(DLL_PATH, "rb").read()
    md = Cs(CS_ARCH_X86, CS_MODE_32)

    idx = 0
    cls_names = set()
    while True:
        idx = raw.find(b".?AVCDispatch_", idx)
        if idx == -1:
            break
        end = raw.find(b"@@", idx)
        if end != -1 and end - idx < 120:
            name = raw[idx + 4 : end].decode("ascii", "ignore")
            if "Flash" in name or "PlayerInfo" in name or "PlayerInven" in name or "PlayerMyInfo" in name:
                cls_names.add(name)
        idx += 10

    entries = []
    by_scene = {}
    resolved_vt = 0

    for name in sorted(cls_names):
        pat = (".?AV" + name + "@@").encode("ascii")
        p_idx = raw.find(pat)
        vt_va = None
        fn0 = None
        fn1 = None
        direct_ops = []
        if p_idx != -1:
            td_va = base + pe.get_rva_from_offset(p_idx - 8)
            c_idx = raw.find(struct.pack("<I", td_va))
            if c_idx != -1:
                col_va = base + pe.get_rva_from_offset(c_idx - 12)
                v_idx = raw.find(struct.pack("<I", col_va))
                if v_idx != -1:
                    vt_va = base + pe.get_rva_from_offset(v_idx + 4)
                    fn0, fn1 = struct.unpack("<II", pe.get_data(vt_va - base, 8))
                    resolved_vt += 1
                    direct_ops = find_direct_hermit_opcodes(pe, md, fn1)

        scene = classify_scene(name)
        by_scene[scene] = by_scene.get(scene, 0) + 1
        entries.append({
            "class_name": name,
            "scene": scene,
            "vtable_va": f"0x{vt_va:08x}" if vt_va else None,
            "fn0_va": f"0x{fn0:08x}" if fn0 else None,
            "handler_va": f"0x{fn1:08x}" if fn1 else None,
            "direct_hermit_opcodes": direct_ops,
        })

    result = {
        "binary": "targets/district-187/client-rebirth/Game/GameClient.dll",
        "total_flash_dispatch_classes": len(entries),
        "resolved_vtables": resolved_vt,
        "scene_distribution": dict(sorted(by_scene.items(), key=lambda kv: -kv[1])),
        "handlers": entries,
    }

    os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    lines = [
        "# Ponte Scaleform GFx Flash ↔ C++ (`CDispatch_Flash_*`) — `GameClient.dll`",
        "",
        f"Descoberto por: `agy` (2026-11-19) — Varredura RTTI e resolução de vtables em `GameClient.dll` (`{len(entries)}` classes `CDispatch_Flash_*` / UI, `{resolved_vt}` vtables resolvidas).",
        "",
        "---",
        "",
        "## 1. Distribuição por Cena / Subsistema de Interface",
        "",
        "| Cena / Subsistema | Qtd. Callbacks Flash → C++ |",
        "|---|---:|",
    ]
    for sc, cnt in result["scene_distribution"].items():
        lines.append(f"| `{sc}` | {cnt} |")

    lines.extend([
        "",
        "---",
        "",
        "## 2. Principais Callbacks de Sala, Lobby, Inventário e Loja",
        "",
        "| Cena | Classe RTTI (`CDispatch_Flash_*`) | Vtable VA | Handler C++ (`fn1`) | Opcodes Diretos |",
        "|---|---|---|---|---|",
    ])
    priority_scenes = {
        "CWaitRoomScene (Room)",
        "CLobbyScene (Lobby)",
        "CServerList / CChannelListScene",
        "CInvenScene (Inventory/Loadout)",
        "CShopScene (Shop)",
    }
    for e in entries:
        if e["scene"] in priority_scenes:
            ops = ", ".join(f"`{o}`" for o in e["direct_hermit_opcodes"]) if e["direct_hermit_opcodes"] else "—"
            lines.append(f"| `{e['scene']}` | `{e['class_name']}` | `{e['vtable_va'] or '—'}` | `{e['handler_va'] or '—'}` | {ops} |")

    lines.extend([
        "",
        "---",
        "",
        "## 3. Artefatos Relacionados",
        "- Extrator Python: [`scripts/map_scaleform_flash_bridge.py`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/scripts/map_scaleform_flash_bridge.py)",
        "- Catálogo Completo (530 classes): [`targets/district-187/data/scaleform_flash_bridge.json`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/targets/district-187/data/scaleform_flash_bridge.json)",
        "",
    ])

    with open(OUT_NOTE, "w", encoding="utf-8") as nf:
        nf.write("\n".join(lines))

    print(f"[+] Scaleform Flash Bridge: {len(entries)} classes, {resolved_vt} vtables/handlers resolved!")
    print(f"[+] Saved: {OUT_JSON} & {OUT_NOTE}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
District 187: Sin Streets — LithTech UDP Combat Message ID (MID_*) Extractor
Dissects CGameServerShell::OnMessage (0x1004FD70) & OnClientEnterWorld (0x100547D0) in GameServer.dll
to extract the server-side LithTech UDP message dispatch table (MID_* 0..255), jump tables, and handler VAs.
Outputs:
  - targets/district-187/data/lithtech_udp_mid_protocol.json
  - notes/d187-lithtech-udp-mid-protocol.md
"""

import json
import os
import struct
import pefile
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GS_DLL = os.path.join(ROOT_DIR, "targets", "district-187", "client-rebirth", "Game", "GameServer.dll")
OUT_JSON = os.path.join(ROOT_DIR, "targets", "district-187", "data", "lithtech_udp_mid_protocol.json")
OUT_NOTE = os.path.join(ROOT_DIR, "notes", "d187-lithtech-udp-mid-protocol.md")


def extract_switch_cases(pe: pefile.PE, md: Cs, start_va: int, scan_size: int = 0x1A00):
    """
    Scans a LithTech OnMessage function for jump tables (`jmp dword ptr [reg*4 + tbl_va]`)
    and direct `cmp reg, imm8; je target` comparisons to recover handled MID_* IDs and targets.
    """
    base = pe.OPTIONAL_HEADER.ImageBase
    code = pe.get_data(start_va - base, scan_size)
    insns = list(md.disasm(code, start_va))

    direct_cases = {}
    jump_tables = []

    for idx, ins in enumerate(insns):
        # Pattern 1: cmp eax/ecx/edx/esi, imm8 followed by je target
        if ins.mnemonic == "cmp" and idx + 1 < len(insns):
            parts = [p.strip() for p in ins.op_str.split(",")]
            if len(parts) == 2 and parts[1].startswith("0x"):
                try:
                    val = int(parts[1], 16)
                    nxt = insns[idx + 1]
                    if 0 <= val <= 0xFF and nxt.mnemonic == "je" and nxt.op_str.startswith("0x"):
                        direct_cases[val] = nxt.op_str
                except ValueError:
                    pass

        # Pattern 2: jmp dword ptr [reg*4 + tbl_va]
        if ins.mnemonic == "jmp" and "*4 +" in ins.op_str and "0x10" in ins.op_str:
            tbl_str = ins.op_str.split("+")[1].split("]")[0].strip()
            try:
                tbl_va = int(tbl_str, 16)
            except ValueError:
                continue
            # Look backwards for `add/sub/lea` base offset and `cmp ..., max_val`
            base_id = 0
            max_idx = 0
            index_tbl_va = None
            for back in range(max(0, idx - 24), idx):
                bi = insns[back]
                if bi.mnemonic in ("sub", "add") and "," in bi.op_str:
                    rhs = bi.op_str.split(",")[1].strip()
                    try:
                        v = int(rhs, 0)
                        if 0 < v < 0x100:
                            base_id = v if bi.mnemonic == "sub" else (-v & 0xFF)
                    except ValueError:
                        pass
                elif bi.mnemonic == "lea" and "-" in bi.op_str:
                    rhs = bi.op_str.split("-")[1].split("]")[0].strip()
                    try:
                        v = int(rhs, 0)
                        if 0 < v < 0x100:
                            base_id = v
                    except ValueError:
                        pass
                elif bi.mnemonic == "cmp" and "," in bi.op_str:
                    rhs = bi.op_str.split(",")[1].strip()
                    try:
                        v = int(rhs, 0)
                        if 2 <= v <= 0xFF:
                            max_idx = v
                    except ValueError:
                        pass
                elif bi.mnemonic == "movzx" and "+" in bi.op_str and "0x10" in bi.op_str:
                    it_str = bi.op_str.split("+")[1].split("]")[0].strip()
                    try:
                        index_tbl_va = int(it_str, 16)
                    except ValueError:
                        pass

            cases = {}
            if max_idx > 0:
                for k in range(max_idx + 1):
                    if index_tbl_va:
                        slot = pe.get_data(index_tbl_va + k - base, 1)[0]
                    else:
                        slot = k
                    dst = struct.unpack_from("<I", pe.get_data(tbl_va + slot * 4 - base, 4), 0)[0]
                    if base <= dst < base + 0x200000:
                        cases[base_id + k] = f"0x{dst:08x}"
            jump_tables.append({
                "jmp_va": f"0x{ins.address:08x}",
                "table_va": f"0x{tbl_va:08x}",
                "index_table_va": f"0x{index_tbl_va:08x}" if index_tbl_va else None,
                "base_mid": base_id,
                "max_span": max_idx,
                "unique_targets": len(set(cases.values())),
                "cases": {f"0x{k:02X}": v for k, v in sorted(cases.items())},
            })

    return direct_cases, jump_tables


def main():
    pe = pefile.PE(GS_DLL)
    md = Cs(CS_ARCH_X86, CS_MODE_32)

    # CGameServerShell::OnMessage is at 0x1004FD70 (slot 6 of vtable 0x1019220C)
    direct_cases, jump_tables = extract_switch_cases(pe, md, 0x1004FD70, 0x2400)

    # Merge all discovered MIDs
    all_mids = {}
    for k, v in direct_cases.items():
        all_mids[k] = v
    for jt in jump_tables:
        for k_hex, v in jt["cases"].items():
            all_mids[int(k_hex, 16)] = v

    # Count distinct handler targets (excluding default fallthrough)
    target_freq = {}
    for v in all_mids.values():
        target_freq[v] = target_freq.get(v, 0) + 1
    default_target = max(target_freq.items(), key=lambda kv: kv[1])[0] if target_freq else None
    active_mids = {f"0x{k:02X}": v for k, v in sorted(all_mids.items()) if v != default_target}

    result = {
        "binary": "targets/district-187/client-rebirth/Game/GameServer.dll",
        "on_message_va": "0x1004fd70",
        "vtable_va": "0x1019220c",
        "default_fallthrough_va": default_target,
        "jump_tables_found": len(jump_tables),
        "active_mid_count": len(active_mids),
        "active_mids": active_mids,
        "jump_tables": jump_tables,
    }

    os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    lines = [
        "# Protocolo UDP de Combate 3D LithTech (`MID_*`) — `CGameServerShell::OnMessage`",
        "",
        f"Descoberto por: `agy` (2026-11-19) — Dissecação estática da rotina `CGameServerShell::OnMessage` (`0x1004FD70`, slot `[6]` da vtable `0x1019220C` em `GameServer.dll`).",
        "",
        "---",
        "",
        "## 1. Sumário do Despachante UDP (`UDP 27888`)",
        f"- **Handler Principal:** `CGameServerShell::OnMessage` @ `0x1004FD70`",
        f"- **Tabelas de Salto (`switch`) Identificadas:** `{len(jump_tables)}`",
        f"- **Message IDs (`MID_*`) Ativos Mapeados:** `{len(active_mids)}` (excluindo fallthrough default `{default_target}`)",
        "",
        "---",
        "",
        "## 2. Tabela de Message IDs UDP (`MID_*` → Handler VA em `GameServer.dll`)",
        "",
        "| MID (Hex) | MID (Dec) | Handler VA em `GameServer.dll` |",
        "|---|---:|---|",
    ]
    for k_hex, v in active_mids.items():
        lines.append(f"| `{k_hex}` | `{int(k_hex, 16)}` | `{v}` |")

    lines.extend([
        "",
        "---",
        "",
        "## 3. Artefatos Relacionados",
        "- Extrator Python: [`scripts/map_lithtech_udp_messages.py`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/scripts/map_lithtech_udp_messages.py)",
        "- Catálogo JSON: [`targets/district-187/data/lithtech_udp_mid_protocol.json`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/targets/district-187/data/lithtech_udp_mid_protocol.json)",
        "",
    ])
    with open(OUT_NOTE, "w", encoding="utf-8") as nf:
        nf.write("\n".join(lines))

    print(f"[+] CGameServerShell::OnMessage (0x1004FD70): {len(jump_tables)} jump tables, {len(active_mids)} active UDP MID_* handlers mapped!")
    print(f"[+] Saved: {OUT_JSON} & {OUT_NOTE}")


if __name__ == "__main__":
    main()

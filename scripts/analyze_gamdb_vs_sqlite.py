#!/usr/bin/env python3
"""
District 187: Sin Streets — Ballistics Audit: Native TheRaw.Gamdb00p vs SQLite s2rebirth.db
Cross-references native LithTech GADB v3 weapon/ammo records against the 185 SQLite weapons
and generates notes/d187-gamdb-vs-sqlite-ballistics-audit.md.
"""

import json
import os
import sqlite3
import sys

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT_DIR, "targets", "district-187", "data")
GAMDB_BAL = os.path.join(DATA_DIR, "gamdb_ballistics_and_modes.json")
DB_PATH = os.path.join(DATA_DIR, "s2rebirth.db")
OUT_NOTE = os.path.join(ROOT_DIR, "notes", "d187-gamdb-vs-sqlite-ballistics-audit.md")


def main():
    with open(GAMDB_BAL, encoding="utf-8") as f:
        gdata = json.load(f)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    sql_weapons = [dict(r) for r in conn.execute("SELECT * FROM weapons ORDER BY damage DESC").fetchall()]
    conn.close()

    ammo_damages = []
    for a in gdata["ammo_multiplayer"]:
        st = a["stats"]
        dmg = st.get("InstDamage", st.get("AreaDamage", 0))
        if isinstance(dmg, (int, float)) and dmg > 0:
            ammo_damages.append((a["ammo_record"], dmg, st.get("Range", 0)))
    ammo_damages.sort(key=lambda x: -x[1])

    lines = [
        "# Auditoria de Balística: `TheRaw.Gamdb00p` (Motor Nativo) vs `s2rebirth.db` (SQLite)",
        "",
        "Gerado por: [`scripts/analyze_gamdb_vs_sqlite.py`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/scripts/analyze_gamdb_vs_sqlite.py) (2026-11-19).",
        "",
        "---",
        "",
        "## 1. Comparativo de Cobertura",
        "| Fonte | Munições MP | Armas MP | Modos de Jogo |",
        "|---|---:|---:|---:|",
        f"| `Database/TheRaw.Gamdb00p` (`GADB` v3) | `{gdata['ammo_multiplayer_count']}` | `{gdata['weapons_multiplayer_count']}` ({gdata['weapon_slots']}) | `{gdata['modes_count']}` |",
        f"| `s2rebirth.db` (`weapons` table) | — | `{len(sql_weapons)}` | — |",
        "",
        "## 2. Top 15 Munições por Dano Instantâneo (`InstDamage` em `TheRaw.Gamdb00p`)",
        "| Registro `Arsenal/Ammo/MultiPlayer` | `InstDamage` | `Range` |",
        "|---|---:|---:|",
    ]
    for rec, dmg, rng in ammo_damages[:15]:
        lines.append(f"| `{rec}` | `{dmg}` | `{rng}` |")

    lines.extend([
        "",
        "## 3. Top 15 Armas por Dano no SQLite (`s2rebirth.db`)",
        "| Arma | Slot | Dano |",
        "|---|---|---:|",
    ])
    for w in sql_weapons[:15]:
        lines.append(f"| `{w.get('name', '?')}` | `{w.get('slot', '?')}` | `{w.get('damage', 0)}` |")

    lines.append("")
    with open(OUT_NOTE, "w", encoding="utf-8") as nf:
        nf.write("\n".join(lines))

    print(f"[+] Ballistics audit generated: {OUT_NOTE} ({len(ammo_damages)} non-zero ammo records, {len(sql_weapons)} SQLite weapons)")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()

#!/usr/bin/env python3
"""
District 187: Sin Streets — GADB v3 (.Gamdb00p) Ballistics, Weapons & Game Mode Rules Extractor
Uses scripts/inspect_gamdb00p.py (byte-exact GADB v3 parser) to extract:
  - All 183 Arsenal/Ammo records (damage, penetration, fire/instdamage stats)
  - All Arsenal/Weapons/Multiplayer/* records from Database/TheRaw.Gamdb00p (3.11 MB)
  - All 20 Missions/Mode records (TDM, C4, Assassin, Rescue, Conquest, SuddenDeath, etc.)
Outputs:
  - targets/district-187/data/gamdb_ballistics_and_modes.json
"""

import json
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from inspect_gamdb00p import parse_gamdb00p

ROOT_DIR = os.path.dirname(SCRIPT_DIR)
ROOT_GAMDB = os.path.join(ROOT_DIR, "targets", "district-187", "client-rebirth", "Database", "TheRaw.Gamdb00p")
OUT_JSON = os.path.join(ROOT_DIR, "targets", "district-187", "data", "gamdb_ballistics_and_modes.json")


def flatten_attrs(attrs: dict, keys_filter=None) -> dict:
    out = {}
    for k, v in attrs.items():
        if keys_filter and not any(kf in k.lower() for kf in keys_filter):
            continue
        out[k] = v["value"]
    return out


def main():
    db = parse_gamdb00p(ROOT_GAMDB)
    cats = db["categories"]

    ammo_list = []
    for rec_name, attrs in cats.get("Arsenal/Ammo/MultiPlayer", {}).items():
        ammo_list.append({
            "ammo_record": rec_name,
            "stats": flatten_attrs(attrs, ["damage", "inst", "area", "range", "penetr", "speed", "gravity", "type"]),
        })

    weapons_by_slot = {}
    total_weapons = 0
    for cat_name, recs in cats.items():
        if cat_name.startswith("Arsenal/Weapons/Multiplayer/") and "Old_Weapon" not in cat_name:
            slot = cat_name.split("/")[-1]
            wlist = []
            for rec_name, attrs in recs.items():
                total_weapons += 1
                wlist.append({
                    "weapon_record": rec_name,
                    "stats": flatten_attrs(attrs, ["ammo", "fire", "reload", "range", "recoil", "perturb", "spread", "move", "zoom", "damage", "clip", "rate"]),
                })
            weapons_by_slot[slot] = wlist

    modes = []
    for rec_name, attrs in cats.get("Missions/Mode", {}).items():
        modes.append({
            "mode_record": rec_name,
            "attribute_count": len(attrs),
            "rules": flatten_attrs(attrs, ["round", "time", "score", "kill", "respawn", "bomb", "team", "max", "min", "intrusion"]),
        })

    result = {
        "source_database": "targets/district-187/client-rebirth/Database/TheRaw.Gamdb00p",
        "byte_exact": db["byte_exact"],
        "ammo_multiplayer_count": len(ammo_list),
        "weapons_multiplayer_count": total_weapons,
        "weapon_slots": {k: len(v) for k, v in weapons_by_slot.items()},
        "modes_count": len(modes),
        "modes": modes,
        "ammo_multiplayer": ammo_list,
        "weapons_multiplayer": weapons_by_slot,
    }

    os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"[+] Extracted {len(ammo_list)} MP Ammo records, {total_weapons} MP Weapons across {len(weapons_by_slot)} slots, and {len(modes)} Game Modes!")
    print(f"[+] Saved: {OUT_JSON}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()

#!/usr/bin/env python3
"""
District 187: Sin Streets — Native GADB v3 (.Gamdb00p) Clean-Maps Patcher (Non-Destructive)
Demonstrates programmatic patching of Game/Database/TheRaw.Gamdb00p using build_gamdb00p.py:
  - Finds the 6 legacy Missions/Level records with DetailInfo == 0
  - Assigns fallback DetailInfo = 10000 (08_twoway) in a NEW copy targets/district-187/extracted/TheRaw_CleanMaps.Gamdb00p
  - Never modifies client-rebirth/ files directly; verifies output with inspect_gamdb00p.parse_gamdb00p (byte_exact=True)
"""

import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from build_gamdb00p import unpack_gamdb00p_raw, pack_gamdb00p_raw
from inspect_gamdb00p import parse_gamdb00p

ROOT_DIR = os.path.dirname(SCRIPT_DIR)
SRC_DB = os.path.join(ROOT_DIR, "targets", "district-187", "client-rebirth", "Game", "Database", "TheRaw.Gamdb00p")
OUT_DB = os.path.join(ROOT_DIR, "targets", "district-187", "extracted", "TheRaw_CleanMaps.Gamdb00p")


def get_cstr(pool: bytearray, off: int) -> str:
    end = pool.find(b"\x00", off)
    return pool[off:end].decode("utf-8", errors="replace")


def main():
    db = unpack_gamdb00p_raw(SRC_DB)
    pool = db["str_pool"]
    patched = []

    for c_off, recs in db["categories"]:
        if get_cstr(pool, c_off) == "Missions/Level":
            for r_off, attrs in recs:
                r_name = get_cstr(pool, r_off)
                for idx, (a_off, a_type, a_usage, vals) in enumerate(attrs):
                    if get_cstr(pool, a_off) == "DetailInfo" and vals and vals[0] == 0:
                        attrs[idx] = (a_off, a_type, a_usage, [10000])
                        patched.append(r_name)

    os.makedirs(os.path.dirname(OUT_DB), exist_ok=True)
    out_bytes = pack_gamdb00p_raw(db)
    with open(OUT_DB, "wb") as f:
        f.write(out_bytes)

    check = parse_gamdb00p(OUT_DB)
    assert check["byte_exact"], "Patched TheRaw_CleanMaps.Gamdb00p failed byte-exact check!"
    print(f"[+] Patched {len(patched)} legacy DetailInfo==0 records -> 10000: {patched}")
    print(f"[+] Verified byte-exact output: {os.path.relpath(OUT_DB, ROOT_DIR)} ({len(out_bytes)} B)")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()

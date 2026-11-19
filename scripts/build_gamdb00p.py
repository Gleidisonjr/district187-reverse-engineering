#!/usr/bin/env python3
"""
District 187: Sin Streets — Bit-Exact LithTech Jupiter EX GADB v3 (.Gamdb00p) Compiler
Reverse engineered from GameDatabase.dll (0x1000B772 -> 0x1000B68D -> 0x1000B55A -> 0x100094A9):
  - Unpacks any .Gamdb00p into raw string pool + structured categories/records/attributes/values
  - Repacks with 100% bit-exact SHA-256 round-trip fidelity (verified on Defaults.Gamdb00p & TheRaw.Gamdb00p)
  - Supports in-place patching of any attribute value (e.g. weapon damage, DetailInfo, mode rules)
"""

import hashlib
import os
import struct
import sys

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLIENT_DIR = os.path.join(ROOT_DIR, "targets", "district-187", "client-rebirth")


def unpack_gamdb00p_raw(path: str) -> dict:
    with open(path, "rb") as f:
        data = f.read()

    magic, ver, str_sz, n_cat, n_rec, n_attr, n_val = struct.unpack_from("<4s6I", data, 0)
    assert magic == b"GADB" and ver == 3, f"Unsupported GADB header: {magic!r} v{ver}"
    str_pool = bytearray(data[28 : 28 + str_sz])
    pos = 28 + str_sz
    cat_cnt = struct.unpack_from("<I", data, pos)[0]
    pos += 4

    cats = []
    for _ in range(cat_cnt):
        c_off, r_cnt = struct.unpack_from("<II", data, pos)
        pos += 8
        recs = []
        for _ in range(r_cnt):
            r_off, a_cnt = struct.unpack_from("<II", data, pos)
            pos += 8
            attrs = []
            for _ in range(a_cnt):
                a_off, a_type, a_usage, v_cnt = struct.unpack_from("<4I", data, pos)
                pos += 16
                vals = list(struct.unpack_from(f"<{v_cnt}I", data, pos)) if v_cnt else []
                pos += v_cnt * 4
                attrs.append((a_off, a_type, a_usage, vals))
            recs.append((r_off, attrs))
        cats.append((c_off, recs))

    assert pos == len(data), f"Did not reach EOF: {pos} != {len(data)}"
    return {"str_pool": str_pool, "categories": cats}


def pack_gamdb00p_raw(db: dict) -> bytes:
    str_pool = bytes(db["str_pool"])
    cats = db["categories"]
    n_cat = len(cats)
    n_rec = sum(len(recs) for _, recs in cats)
    n_attr = sum(len(attrs) for _, recs in cats for _, attrs in recs)
    n_val = sum(len(vals) for _, recs in cats for _, attrs in recs for _, _, _, vals in attrs)

    out = bytearray()
    out += struct.pack("<4s6I", b"GADB", 3, len(str_pool), n_cat, n_rec, n_attr, n_val)
    out += str_pool
    out += struct.pack("<I", n_cat)
    for c_off, recs in cats:
        out += struct.pack("<II", c_off, len(recs))
        for r_off, attrs in recs:
            out += struct.pack("<II", r_off, len(attrs))
            for a_off, a_type, a_usage, vals in attrs:
                out += struct.pack("<4I", a_off, a_type, a_usage, len(vals))
                if vals:
                    out += struct.pack(f"<{len(vals)}I", *vals)
    return bytes(out)


def verify_roundtrip(rel_path: str):
    full = os.path.join(CLIENT_DIR, rel_path)
    with open(full, "rb") as f:
        orig = f.read()
    repacked = pack_gamdb00p_raw(unpack_gamdb00p_raw(full))
    sha_orig = hashlib.sha256(orig).hexdigest()
    sha_repack = hashlib.sha256(repacked).hexdigest()
    assert orig == repacked, f"Round-trip mismatch on {rel_path}!"
    print(f"[+] {rel_path:42s} | {len(orig):8d} B | SHA-256 bit-exact: True ({sha_repack[:16]}...)")


def main():
    for rel in [
        os.path.join("ProfileDatabase", "Defaults.Gamdb00p"),
        os.path.join("Game", "DatabaseLocalized", "TheRawL.Gamdb00p"),
        os.path.join("AnimationDatabase", "S2_anim.Gamdb00p"),
        os.path.join("Game", "Database", "TheRaw.Gamdb00p"),
        os.path.join("Database", "TheRaw.Gamdb00p"),
    ]:
        verify_roundtrip(rel)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()

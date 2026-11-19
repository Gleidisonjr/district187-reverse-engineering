#!/usr/bin/env python3
"""
District 187: Sin Streets — LithTech Jupiter EX GameDatabase v3 (GADB / .Gamdb00p) Dissector
Reverse engineered from GameDatabase.dll (0x1000B772 -> 0x1000B68D -> 0x1000B55A -> 0x100094A9):
  - 28-byte header: <4s6I (magic='GADB', version=3, string_pool_size, num_cats, num_recs, num_attrs, num_vals)
  - String pool: string_pool_size bytes at offset 0x1C (null-terminated strings indexed by byte offset)
  - Body at offset 0x1C + string_pool_size:
      uint32 cat_count
      For each category:
        uint32 name_off, uint32 record_count
        For each record:
          uint32 name_off, uint32 attrib_count
          For each attribute:
            uint32 name_off, uint32 attr_type, uint32 attr_usage, uint32 value_count
            uint32[value_count] values (if 4 <= attr_type <= 8: string pool offset; type 1: float32; type 2: int32)
"""

import json
import os
import struct
import sys

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLIENT_DIR = os.path.join(ROOT_DIR, "targets", "district-187", "client-rebirth")
OUT_JSON = os.path.join(ROOT_DIR, "targets", "district-187", "data", "gamdb00p_catalog.json")

ATTR_TYPE_NAMES = {
    0: "Invalid/Bool",
    1: "Float32",
    2: "Int32",
    3: "RecordLink",
    4: "String",
    5: "WString",
    6: "StringRes",
    7: "StringTable",
    8: "StringPath",
    9: "Vector2",
    10: "Vector3",
    11: "Vector4",
}


def parse_gamdb00p(path: str) -> dict:
    with open(path, "rb") as f:
        data = f.read()

    magic, version, str_sz, n_cat, n_rec, n_attr, n_val = struct.unpack_from("<4s6I", data, 0)
    if magic != b"GADB" or version != 3:
        raise ValueError(f"Unsupported GADB header in {path}: magic={magic!r}, version={version}")

    str_pool = data[28 : 28 + str_sz]

    def get_str(off: int) -> str:
        if off >= len(str_pool):
            return f"<OOB:{off}>"
        end = str_pool.find(b"\x00", off)
        if end == -1:
            end = len(str_pool)
        raw_s = str_pool[off:end]
        try:
            return raw_s.decode("utf-8")
        except UnicodeDecodeError:
            return raw_s.decode("cp949", errors="replace")

    pos = 28 + str_sz
    cat_cnt = struct.unpack_from("<I", data, pos)[0]
    pos += 4

    categories = {}
    tot_rec = 0
    tot_attr = 0
    tot_val = 0
    type_counts = {}

    for _ in range(cat_cnt):
        c_off, r_cnt = struct.unpack_from("<II", data, pos)
        pos += 8
        c_name = get_str(c_off)
        records = {}
        for _ in range(r_cnt):
            r_off, a_cnt = struct.unpack_from("<II", data, pos)
            pos += 8
            r_name = get_str(r_off)
            tot_rec += 1
            attrs = {}
            for _ in range(a_cnt):
                a_off, a_type, a_usage, v_cnt = struct.unpack_from("<4I", data, pos)
                pos += 16
                a_name = get_str(a_off)
                tot_attr += 1
                tot_val += v_cnt
                type_counts[a_type] = type_counts.get(a_type, 0) + 1

                vals = []
                for _ in range(v_cnt):
                    raw_u32 = struct.unpack_from("<I", data, pos)[0]
                    if 4 <= a_type <= 8:
                        vals.append(get_str(raw_u32))
                    elif a_type == 1:
                        vals.append(round(struct.unpack_from("<f", data, pos)[0], 5))
                    elif a_type == 2:
                        vals.append(struct.unpack_from("<i", data, pos)[0])
                    else:
                        vals.append(raw_u32)
                    pos += 4

                attrs[a_name] = {
                    "type": a_type,
                    "usage": a_usage,
                    "value": vals[0] if len(vals) == 1 else vals,
                }
            records[r_name] = attrs
        categories[c_name] = records

    return {
        "path": os.path.relpath(path, ROOT_DIR).replace("\\", "/"),
        "file_size": len(data),
        "parsed_bytes": pos,
        "byte_exact": pos == len(data),
        "header": {
            "magic": magic.decode("ascii"),
            "version": version,
            "string_pool_bytes": str_sz,
            "num_categories": n_cat,
            "num_records": n_rec,
            "num_attributes": n_attr,
            "num_values": n_val,
        },
        "attribute_type_distribution": {
            f"{t} ({ATTR_TYPE_NAMES.get(t, 'Unknown')})": cnt for t, cnt in sorted(type_counts.items())
        },
        "categories": categories,
    }


def main():
    db_files = [
        os.path.join(CLIENT_DIR, "Game", "Database", "TheRaw.Gamdb00p"),
        os.path.join(CLIENT_DIR, "Database", "TheRaw.Gamdb00p"),
        os.path.join(CLIENT_DIR, "Game", "DatabaseLocalized", "TheRawL.Gamdb00p"),
        os.path.join(CLIENT_DIR, "AnimationDatabase", "S2_anim.Gamdb00p"),
        os.path.join(CLIENT_DIR, "ProfileDatabase", "Defaults.Gamdb00p"),
    ]

    parsed = {}
    for p in db_files:
        if os.path.exists(p):
            res = parse_gamdb00p(p)
            key = os.path.relpath(p, CLIENT_DIR).replace("\\", "/")
            parsed[key] = res
            h = res["header"]
            print(
                f"[+] {key:42s} | {res['file_size']:8d} B | exact={res['byte_exact']} | "
                f"cats={h['num_categories']:3d} recs={h['num_records']:4d} attrs={h['num_attributes']:6d}"
            )

    game_db = parsed["Game/Database/TheRaw.Gamdb00p"]["categories"]
    root_db = parsed["Database/TheRaw.Gamdb00p"]["categories"]

    # Extract Missions/Level (valid maps with DetailInfo >= 10000 vs legacy/unmapped DetailInfo == 0)
    levels_active = []
    levels_unmapped = []
    for rec_name, attrs in game_db.get("Missions/Level", {}).items():
        detail_id = attrs.get("DetailInfo", {}).get("value", 0)
        disp = attrs.get("DisplayName", {}).get("value", "")
        cc_mat = attrs.get("ColorCurveMaterial", {}).get("value", "")
        entry = {
            "record": rec_name,
            "detail_info_id": detail_id,
            "display_name": disp,
            "color_curve_material": cc_mat,
        }
        if isinstance(detail_id, int) and detail_id >= 10000:
            levels_active.append(entry)
        else:
            levels_unmapped.append(entry)

    # Extract Missions/Mode
    modes = []
    for rec_name, attrs in game_db.get("Missions/Mode", {}).items():
        modes.append({
            "record": rec_name,
            "attribute_count": len(attrs),
        })

    catalog = {
        "databases": {
            k: {
                "file_size": v["file_size"],
                "parsed_bytes": v["parsed_bytes"],
                "byte_exact": v["byte_exact"],
                "header": v["header"],
                "attribute_type_distribution": v["attribute_type_distribution"],
                "category_summary": {cn: len(crecs) for cn, crecs in v["categories"].items()},
            }
            for k, v in parsed.items()
        },
        "diff_root_vs_game_theraw": {
            "categories_only_in_root_Database_TheRaw": sorted(set(root_db.keys()) - set(game_db.keys())),
            "categories_only_in_Game_Database_TheRaw": sorted(set(game_db.keys()) - set(root_db.keys())),
        },
        "missions_modes": modes,
        "missions_levels_active_count": len(levels_active),
        "missions_levels_unmapped_zero_detailinfo_count": len(levels_unmapped),
        "missions_levels_active": sorted(levels_active, key=lambda x: x["detail_info_id"]),
        "missions_levels_unmapped_sample": levels_unmapped[:25],
        "profile_defaults": {
            cn: {rn: {an: av["value"] for an, av in rattrs.items()} for rn, rattrs in crecs.items()}
            for cn, crecs in parsed.get("ProfileDatabase/Defaults.Gamdb00p", {}).get("categories", {}).items()
        },
    }

    os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(catalog, f, indent=2, ensure_ascii=False)

    print(
        f"[+] Missions/Level: {len(levels_active)} active maps (DetailInfo >= 10000), "
        f"{len(levels_unmapped)} legacy records with DetailInfo == 0 (cause of 0x10408C7E assertion)."
    )
    print(f"[+] Saved GADB v3 catalog to: {OUT_JSON}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()

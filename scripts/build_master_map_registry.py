#!/usr/bin/env python3
"""
District 187: Sin Streets — Master Map & Mode Registry Builder
Cross-references:
  1. Native .World00p files on disk (targets/district-187/client-rebirth/Game/Worlds/)
  2. Native Missions/Level & Missions/Mode records in TheRaw.Gamdb00p (gamdb00p_catalog.json)
  3. Generated A* NavMeshes & 2D KDE Heatmaps (targets/district-187/data/navmeshes/)
Outputs:
  - targets/district-187/data/master_map_registry.json
  - notes/d187-master-map-and-mode-registry.md
"""

import glob
import json
import os
import sys

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT_DIR, "targets", "district-187", "data")
WORLDS_DIR = os.path.join(ROOT_DIR, "targets", "district-187", "client-rebirth", "Game", "Worlds")
OUT_JSON = os.path.join(DATA_DIR, "master_map_registry.json")
OUT_NOTE = os.path.join(ROOT_DIR, "notes", "d187-master-map-and-mode-registry.md")


def main():
    with open(os.path.join(DATA_DIR, "gamdb00p_catalog.json"), encoding="utf-8") as f:
        gcat = json.load(f)

    world_files = sorted(os.path.basename(p) for p in glob.glob(os.path.join(WORLDS_DIR, "*.World00p")))
    world_lower = {w.lower(): w for w in world_files}

    nav_dir = os.path.join(DATA_DIR, "navmeshes")
    nav_files = set(os.path.basename(p).lower().replace("_navmesh.json", "") for p in glob.glob(os.path.join(nav_dir, "*.json")))

    matched_maps = []
    for lv in gcat.get("missions_levels_active", []):
        rec = lv["record"]
        # Strip numeric prefix e.g. '08_twoway' -> 'twoway'
        clean = rec.split("_", 1)[1] if "_" in rec and rec.split("_", 1)[0].isdigit() else rec
        w_match = None
        for wl, orig_w in world_lower.items():
            stem = wl.replace(".world00p", "")
            if stem == clean.lower() or stem == rec.lower() or clean.lower() in stem:
                w_match = orig_w
                break
        has_nav = clean.lower() in nav_files or (w_match and w_match.lower().replace(".world00p", "") in nav_files)
        matched_maps.append({
            "detail_info_id": lv["detail_info_id"],
            "gamdb_record": rec,
            "display_name": lv["display_name"],
            "world_file": w_match,
            "playable_on_disk": w_match is not None,
            "has_navmesh": bool(has_nav),
        })

    playable = [m for m in matched_maps if m["playable_on_disk"]]
    result = {
        "total_world00p_on_disk": len(world_files),
        "world00p_files": world_files,
        "total_gamdb_active_levels": len(matched_maps),
        "matched_playable_levels": len(playable),
        "modes": gcat.get("missions_modes", []),
        "playable_maps": playable,
        "all_gamdb_levels": matched_maps,
    }

    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    lines = [
        "# Registro Mestre de Mapas & Modos — District 187: Sin Streets",
        "",
        f"Gerado por: [`scripts/build_master_map_registry.py`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/scripts/build_master_map_registry.py) (2026-11-19).",
        "",
        f"- **Arquivos `.World00p` em disco (`Game/Worlds/`):** `{len(world_files)}`",
        f"- **Registros ativos em `TheRaw.Gamdb00p` (`Missions/Level`):** `{len(matched_maps)}`",
        f"- **Mapas correlacionados prontos para uso (`.World00p` + `DetailInfo` ID):** `{len(playable)}`",
        f"- **Modos de Jogo (`Missions/Mode`):** `{len(result['modes'])}`",
        "",
        "---",
        "",
        "## 1. Mapas Jogáveis em Disco (`.World00p` ↔ `DetailInfo` ID)",
        "| `DetailInfo` ID | Registro `Gamdb00p` | Arquivo `.World00p` | NavMesh A* |",
        "|---:|---|---|---|",
    ]
    for m in playable[:40]:
        lines.append(f"| `{m['detail_info_id']}` | `{m['gamdb_record']}` | `{m['world_file']}` | {'✅' if m['has_navmesh'] else '—'} |")

    lines.extend([
        "",
        "## 2. Modos de Jogo Oficiais (`Missions/Mode` — 20 Modos)",
        ", ".join(f"`{m['record']}`" for m in result["modes"]),
        "",
    ])
    with open(OUT_NOTE, "w", encoding="utf-8") as nf:
        nf.write("\n".join(lines))

    print(f"[+] Master Map Registry: {len(world_files)} .World00p on disk, {len(playable)} matched with Gamdb00p DetailInfo IDs!")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()

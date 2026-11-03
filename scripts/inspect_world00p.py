#!/usr/bin/env python3
"""
District 187: Sin Streets - Universal LithTech Jupiter EX World (.World00p) Parser
Extracts:
  - 3D Spawns (Team 0 SWAT, Team 1 Gangsters, FFA Deathmatch)
  - Bomb Defusal Sites (Site A, Site B) with bounding volume dimensions
  - Bank Robbery / Carry Object dropzones
  - Tactical metrics (base-to-base distance, choke point centroid, bounding box)
Generates:
  - Structured JSON metadata per map in targets/district-187/data/maps/
  - High-res interactive vector minimap (HTML/SVG) per map
"""

import os
import sys
import re
import struct
import math
import json
import argparse
from typing import Dict, Any, List, Optional

# Ensure UTF-8 output
sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORLDS_DIR = os.path.join(BASE_DIR, "targets", "district-187", "client-rebirth", "Game", "Worlds")
DATA_DIR = os.path.join(BASE_DIR, "targets", "district-187", "data", "maps")
HTML_DIR = os.path.join(BASE_DIR, "targets", "district-187", "maps")

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(HTML_DIR, exist_ok=True)

def parse_world_geometry(world_path: str) -> Optional[Dict[str, Any]]:
    if not os.path.exists(world_path):
        print(f"[-] World not found: {world_path}")
        return None

    map_name = os.path.splitext(os.path.basename(world_path))[0]
    file_size = os.path.getsize(world_path)

    if file_size < 1000:
        return None

    with open(world_path, "rb") as f:
        data = f.read()

    version = struct.unpack("<I", data[:4])[0]

    # 1. Extract Spawns
    spawns = []
    # Pattern covers: GameStartPoint_0_00, GameStartPointTeam_0_00, GameStartPoint00
    spawn_pattern = rb'(GameStartPoint(?:Team)?_?([01])?_?([0-9]{2}))\x00'
    for m in re.finditer(spawn_pattern, data):
        full_name = m.group(1).decode('ascii', errors='ignore')
        team_str = m.group(2)
        idx_str = m.group(3)
        
        team_id = int(team_str.decode()) if team_str else 0
        idx = int(idx_str.decode()) if idx_str else 0
        
        p_idx = m.start()
        # Find 'Pos\x00' within 80 bytes
        pos_idx = data.find(b'Pos\x00', p_idx)
        if pos_idx != -1 and (pos_idx - p_idx) < 90:
            x, y, z = struct.unpack('<fff', data[pos_idx+4:pos_idx+16])
            if abs(x) < 50000 and abs(y) < 50000 and abs(z) < 50000:
                spawns.append({
                    "name": full_name,
                    "team": team_id,
                    "team_name": "SWAT (Law)" if team_id == 0 else "Gangsters (Crime)",
                    "index": idx,
                    "x": round(x, 2),
                    "y": round(y, 2),
                    "z": round(z, 2)
                })

    # Deduplicate spawns by name
    seen_spawns = {}
    for s in spawns:
        seen_spawns[s["name"]] = s
    spawns = sorted(list(seen_spawns.values()), key=lambda s: (s["team"], s["index"]))

    # 2. Extract Bomb Sites (Site A & Site B)
    bomb_sites = []
    for b_pat in [rb'(BombZoneTrigger(?:00|01|A|B)?)\x00']:
        for m in re.finditer(b_pat, data):
            b_name = m.group(1).decode('ascii', errors='ignore')
            p_idx = m.start()
            pos_idx = data.find(b'Pos\x00', p_idx)
            dims_idx = data.find(b'Dims\x00', p_idx)
            
            if pos_idx != -1 and (pos_idx - p_idx) < 90:
                x, y, z = struct.unpack('<fff', data[pos_idx+4:pos_idx+16])
                dx, dy, dz = (100.0, 100.0, 100.0)
                if dims_idx != -1 and (dims_idx - p_idx) < 180:
                    for off in range(4, 16):
                        try:
                            tdx, tdy, tdz = struct.unpack('<fff', data[dims_idx+off:dims_idx+off+12])
                            if 10 < tdx < 10000 and 10 < tdy < 10000 and 10 < tdz < 10000:
                                dx, dy, dz = tdx, tdy, tdz
                                break
                        except Exception:
                            pass
                
                label = "Site A" if ("00" in b_name or "A" in b_name) else "Site B"
                bomb_sites.append({
                    "name": b_name,
                    "site": label,
                    "x": round(x, 2),
                    "y": round(y, 2),
                    "z": round(z, 2),
                    "dims_x": round(dx, 2),
                    "dims_y": round(dy, 2),
                    "dims_z": round(dz, 2)
                })

    seen_bomb = {}
    for b in bomb_sites:
        seen_bomb[b["name"]] = b
    bomb_sites = list(seen_bomb.values())

    # 3. Extract Carry Object Areas (Bank / Heist loot zones)
    carry_sites = []
    for m in re.finditer(rb'(CarryObjectArea[0-9A-Za-z_]*)\x00', data):
        c_name = m.group(1).decode('ascii', errors='ignore')
        p_idx = m.start()
        pos_idx = data.find(b'Pos\x00', p_idx)
        if pos_idx != -1 and (pos_idx - p_idx) < 90:
            x, y, z = struct.unpack('<fff', data[pos_idx+4:pos_idx+16])
            carry_sites.append({
                "name": c_name,
                "x": round(x, 2),
                "y": round(y, 2),
                "z": round(z, 2)
            })

    seen_carry = {}
    for c in carry_sites:
        seen_carry[c["name"]] = c
    carry_sites = list(seen_carry.values())

    # Calculate tactical bounds
    all_points = [(s["x"], s["z"]) for s in spawns] + [(b["x"], b["z"]) for b in bomb_sites] + [(c["x"], c["z"]) for c in carry_sites]
    if not all_points:
        return None

    xs = [p[0] for p in all_points]
    zs = [p[1] for p in all_points]
    min_x, max_x = min(xs), max(xs)
    min_z, max_z = min(zs), max(zs)

    t0_spawns = [s for s in spawns if s["team"] == 0]
    t1_spawns = [s for s in spawns if s["team"] == 1]

    t0_cx = sum(s["x"] for s in t0_spawns) / len(t0_spawns) if t0_spawns else min_x
    t0_cz = sum(s["z"] for s in t0_spawns) / len(t0_spawns) if t0_spawns else min_z
    t1_cx = sum(s["x"] for s in t1_spawns) / len(t1_spawns) if t1_spawns else max_x
    t1_cz = sum(s["z"] for s in t1_spawns) / len(t1_spawns) if t1_spawns else max_z

    base_dist = math.sqrt((t1_cx - t0_cx)**2 + (t1_cz - t0_cz)**2)
    mid_x = (t0_cx + t1_cx) / 2
    mid_z = (t0_cz + t1_cz) / 2

    # Game mode inference
    mode = "Team Deathmatch (TDM)"
    if bomb_sites:
        mode = "Demolition (Bomb Defusal / Search & Destroy)"
    elif carry_sites:
        mode = "Heist / Bank Robbery (Carry Loot)"

    map_meta = {
        "map_name": map_name,
        "engine_version": version,
        "file_size": file_size,
        "game_mode": mode,
        "bounds": {
            "min_x": round(min_x, 1),
            "max_x": round(max_x, 1),
            "min_z": round(min_z, 1),
            "max_z": round(max_z, 1),
            "span_x": round(max_x - min_x, 1),
            "span_z": round(max_z - min_z, 1)
        },
        "base_to_base_distance": round(base_dist, 1),
        "choke_point_mid": {"x": round(mid_x, 1), "z": round(mid_z, 1)},
        "spawns_team0": len(t0_spawns),
        "spawns_team1": len(t1_spawns),
        "spawns": spawns,
        "bomb_sites": bomb_sites,
        "carry_sites": carry_sites
    }

    # Save JSON
    json_path = os.path.join(DATA_DIR, f"{map_name}.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(map_meta, f, indent=2)

    # Generate HTML minimap
    generate_tactical_html(map_meta)

    print(f"[+] Map: {map_name:20s} | Mode: {mode[:24]:24s} | Spawns: {len(spawns):2d} | Bombs: {len(bomb_sites)} | JSON: {os.path.basename(json_path)}")
    return map_meta

def generate_tactical_html(meta: Dict[str, Any]):
    map_name = meta["map_name"]
    spawns = meta["spawns"]
    bomb_sites = meta["bomb_sites"]
    carry_sites = meta["carry_sites"]
    b = meta["bounds"]

    svg_w = 900
    svg_h = 600
    pad = 70

    span_x = max(b["span_x"], 100.0)
    span_z = max(b["span_z"], 100.0)

    def tx(x):
        return pad + ((x - b["min_x"]) / span_x) * (svg_w - 2 * pad)

    def ty(z):
        # Invert Z so north is top
        return svg_h - pad - ((z - b["min_z"]) / span_z) * (svg_h - 2 * pad)

    svg_elements = []

    # Connecting line between bases
    t0_spawns = [s for s in spawns if s["team"] == 0]
    t1_spawns = [s for s in spawns if s["team"] == 1]
    if t0_spawns and t1_spawns:
        t0_x = tx(sum(s["x"] for s in t0_spawns) / len(t0_spawns))
        t0_y = ty(sum(s["z"] for s in t0_spawns) / len(t0_spawns))
        t1_x = tx(sum(s["x"] for s in t1_spawns) / len(t1_spawns))
        t1_y = ty(sum(s["z"] for s in t1_spawns) / len(t1_spawns))

        svg_elements.append(
            f'<line x1="{t0_x:.1f}" y1="{t0_y:.1f}" x2="{t1_x:.1f}" y2="{t1_y:.1f}" '
            f'stroke="#334155" stroke-width="2" stroke-dasharray="6,4" />'
        )
        mid_x = (t0_x + t1_x) / 2
        mid_y = (t0_y + t1_y) / 2
        svg_elements.append(
            f'<circle cx="{mid_x:.1f}" cy="{mid_y:.1f}" r="14" fill="#f59e0b" fill-opacity="0.15" stroke="#f59e0b" stroke-width="2" />'
            f'<text x="{mid_x:.1f}" y="{mid_y-18:.1f}" fill="#f59e0b" font-size="11" font-weight="bold" text-anchor="middle">MID CHOKE POINT</text>'
        )

    # Bomb Sites
    for b_site in bomb_sites:
        bx = tx(b_site["x"])
        by = ty(b_site["z"])
        color = "#ef4444" if "A" in b_site["site"] else "#f97316"
        svg_elements.append(
            f'<g class="bomb-site" data-name="{b_site["name"]}" data-coord="({b_site["x"]}, {b_site["y"]}, {b_site["z"]})">'
            f'<rect x="{bx-20:.1f}" y="{by-20:.1f}" width="40" height="40" fill="{color}" fill-opacity="0.25" stroke="{color}" stroke-width="2.5" rx="6" />'
            f'<text x="{bx:.1f}" y="{by+5:.1f}" fill="#ffffff" font-size="14" font-weight="bold" text-anchor="middle">{b_site["site"]}</text>'
            f'</g>'
        )

    # Carry Sites
    for c_site in carry_sites:
        cx = tx(c_site["x"])
        cy = ty(c_site["z"])
        svg_elements.append(
            f'<g class="carry-site" data-name="{c_site["name"]}" data-coord="({c_site["x"]}, {c_site["y"]}, {c_site["z"]})">'
            f'<polygon points="{cx:.1f},{cy-18:.1f} {cx+18:.1f},{cy+14:.1f} {cx-18:.1f},{cy+14:.1f}" fill="#eab308" fill-opacity="0.3" stroke="#eab308" stroke-width="2" />'
            f'<text x="{cx:.1f}" y="{cy+8:.1f}" fill="#ffffff" font-size="10" font-weight="bold" text-anchor="middle">GOLD</text>'
            f'</g>'
        )

    # Spawns
    for s in spawns:
        sx = tx(s["x"])
        sy = ty(s["z"])
        color = "#3b82f6" if s["team"] == 0 else "#ef4444"
        label = f"{s['index']:02d}"
        svg_elements.append(
            f'<g class="spawn-node" data-name="{s["name"]}" data-coord="({s["x"]}, {s["y"]}, {s["z"]})">'
            f'<circle cx="{sx:.1f}" cy="{sy:.1f}" r="9" fill="{color}" stroke="#ffffff" stroke-width="1.5" />'
            f'<text x="{sx:.1f}" y="{sy+3.5:.1f}" fill="#ffffff" font-size="9" font-weight="bold" text-anchor="middle">{label}</text>'
            f'</g>'
        )

    svg_content = "\n".join(svg_elements)

    html_code = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>D187 Tactical Radar - {map_name}</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <style>
    body {{ background-color: #0b1120; color: #f8fafc; font-family: ui-sans-serif, system-ui, sans-serif; }}
    .spawn-node:hover circle, .bomb-site:hover rect {{ filter: drop-shadow(0 0 10px rgba(255,255,255,0.9)); cursor: pointer; }}
  </style>
</head>
<body class="p-6">
  <div class="max-w-7xl mx-auto space-y-6">
    <header class="border-b border-slate-800 pb-4 flex justify-between items-center">
      <div>
        <h1 class="text-3xl font-bold tracking-tight text-white flex items-center gap-3">
          <span class="p-2 bg-indigo-600 rounded-lg text-lg">D187</span>
          Tactical Map Radar: <span class="text-indigo-400 font-mono">{map_name}</span>
        </h1>
        <p class="text-slate-400 text-sm mt-1">Engine: LithTech Jupiter EX v{meta["engine_version"]} | Mode: <strong class="text-emerald-400">{meta["game_mode"]}</strong></p>
      </div>
      <div class="flex gap-3">
        <span class="px-3 py-1.5 bg-blue-900/40 text-blue-400 border border-blue-700/50 rounded-md text-xs font-semibold">SWAT: {meta["spawns_team0"]} Spawns</span>
        <span class="px-3 py-1.5 bg-red-900/40 text-red-400 border border-red-700/50 rounded-md text-xs font-semibold">Gangsters: {meta["spawns_team1"]} Spawns</span>
        <span class="px-3 py-1.5 bg-purple-900/40 text-purple-400 border border-purple-700/50 rounded-md text-xs font-semibold">{len(bomb_sites)} Bomb Sites</span>
      </div>
    </header>

    <div class="grid grid-cols-4 gap-4">
      <div class="bg-slate-900 border border-slate-800 p-4 rounded-xl">
        <p class="text-xs text-slate-400 uppercase font-semibold">Combat Arena Span</p>
        <p class="text-2xl font-bold text-white mt-1">{b["span_x"]:.0f} &times; {b["span_z"]:.0f}</p>
        <p class="text-xs text-slate-500 mt-1">Units (X &times; Z extents)</p>
      </div>
      <div class="bg-slate-900 border border-slate-800 p-4 rounded-xl">
        <p class="text-xs text-slate-400 uppercase font-semibold">Base-to-Base Distance</p>
        <p class="text-2xl font-bold text-amber-400 mt-1">{meta["base_to_base_distance"]:.0f} u</p>
        <p class="text-xs text-slate-500 mt-1">~{meta["base_to_base_distance"]/50:.1f} meters combat corridor</p>
      </div>
      <div class="bg-slate-900 border border-slate-800 p-4 rounded-xl">
        <p class="text-xs text-slate-400 uppercase font-semibold">Lobby Capacity</p>
        <p class="text-2xl font-bold text-emerald-400 mt-1">{len(spawns)} Slots</p>
        <p class="text-xs text-slate-500 mt-1">Full 8v8 or 16v16 Match</p>
      </div>
      <div class="bg-slate-900 border border-slate-800 p-4 rounded-xl">
        <p class="text-xs text-slate-400 uppercase font-semibold">Objectives</p>
        <p class="text-2xl font-bold text-cyan-400 mt-1">{len(bomb_sites) + len(carry_sites)} Zones</p>
        <p class="text-xs text-slate-500 mt-1">Target Plant / Heist vaults</p>
      </div>
    </div>

    <div class="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-2xl relative">
      <div class="flex justify-between items-center mb-4">
        <h2 class="text-lg font-semibold text-white">Top-Down Vector Radar (XZ Coordinate Plane)</h2>
        <div class="text-xs text-slate-400 flex gap-4">
          <span class="flex items-center gap-1.5"><span class="w-3 h-3 rounded-full bg-blue-500 inline-block"></span> Team 0: SWAT</span>
          <span class="flex items-center gap-1.5"><span class="w-3 h-3 rounded-full bg-red-500 inline-block"></span> Team 1: Gangsters</span>
          <span class="flex items-center gap-1.5"><span class="w-3 h-3 rounded bg-red-500/80 inline-block"></span> Bomb Site A</span>
          <span class="flex items-center gap-1.5"><span class="w-3 h-3 rounded bg-orange-500/80 inline-block"></span> Bomb Site B</span>
        </div>
      </div>

      <div class="bg-slate-950 rounded-lg p-2 border border-slate-800/80 flex justify-center">
        <svg viewBox="0 0 {svg_w} {svg_h}" class="w-full h-auto max-h-[580px]">
          <defs>
            <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
              <path d="M 40 0 L 0 0 0 40" fill="none" stroke="#1e293b" stroke-width="0.8"/>
            </pattern>
          </defs>
          <rect width="100%" height="100%" fill="url(#grid)" />
          {svg_content}
        </svg>
      </div>

      <div id="inspector-bar" class="mt-4 p-3 bg-slate-950 border border-slate-800 rounded text-xs text-slate-300 flex justify-between items-center">
        <span id="inspect-label"><strong>Live Entity Inspector:</strong> Hover any node on the radar above.</span>
        <span class="text-slate-500">LithTech Engine World Space</span>
      </div>
    </div>
  </div>

  <script>
    const label = document.getElementById('inspect-label');
    document.querySelectorAll('.spawn-node, .bomb-site, .carry-site').forEach(el => {{
      el.addEventListener('mouseenter', () => {{
        const name = el.getAttribute('data-name');
        const coord = el.getAttribute('data-coord');
        label.innerHTML = `<strong class="text-emerald-400">${{name}}</strong> &mdash; Coordinates: <span class="font-mono text-cyan-300">${{coord}}</span>`;
      }});
      el.addEventListener('mouseleave', () => {{
        label.innerHTML = '<strong>Live Entity Inspector:</strong> Hover any node on the radar above.';
      }});
    }});
  </script>
</body>
</html>
"""
    html_path = os.path.join(HTML_DIR, f"{map_name}_tactical.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_code)

def main():
    parser = argparse.ArgumentParser(description="LithTech World00p Universal Entity Parser")
    parser.add_argument("--world", help="Specific .World00p file path or map name")
    parser.add_argument("--all", action="store_true", help="Parse all worlds in Game/Worlds")
    args = parser.parse_args()

    if args.all:
        import glob
        worlds = sorted(glob.glob(os.path.join(WORLDS_DIR, "*.World00p")))
        print(f"[+] Batch parsing {len(worlds)} World00p maps in {WORLDS_DIR}...")
        parsed = 0
        for w in worlds:
            res = parse_world_geometry(w)
            if res:
                parsed += 1
        print(f"\n[+] Successfully parsed and generated radars for {parsed} maps!")
    elif args.world:
        target = args.world
        if not os.path.isabs(target) and not os.path.exists(target):
            target = os.path.join(WORLDS_DIR, target if target.endswith(".World00p") else f"{target}.World00p")
        parse_world_geometry(target)
    else:
        # Default run on top competitive maps
        for default_map in ["twoway.World00p", "thebank.World00p", "oldtown.World00p", "Arrival.World00p", "10025_Heaven.World00p"]:
            parse_world_geometry(os.path.join(WORLDS_DIR, default_map))

if __name__ == "__main__":
    main()

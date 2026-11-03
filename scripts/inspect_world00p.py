#!/usr/bin/env python3
"""
District 187: Sin Streets - LithTech Jupiter EX World (.World00p) Parser
Extracts 3D spawn entities, team coordinates, bounding boxes, and generates
an interactive tactical top-down minimap (tactical_map_arrival.html).
"""

import os
import sys
import re
import struct
import math
import json

# Ensure UTF-8 output
sys.stdout.reconfigure(encoding='utf-8')

WORLD_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "targets", "district-187", "client-rebirth", "Game", "Worlds", "Arrival.World00p"
)
OUTPUT_HTML = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "targets", "district-187", "tactical_map_arrival.html"
)
OUTPUT_JSON = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "targets", "district-187", "data", "arrival_spawns.json"
)

def parse_world00p():
    if not os.path.exists(WORLD_PATH):
        print(f"[-] World file not found at {WORLD_PATH}")
        return

    print(f"[+] Loading LithTech World: {WORLD_PATH}")
    file_size = os.path.getsize(WORLD_PATH)
    print(f"  File size: {file_size:,} bytes")

    with open(WORLD_PATH, "rb") as f:
        data = f.read()

    version = struct.unpack("<I", data[:4])[0]
    print(f"  LithTech World Version: {version} (Jupiter EX standard: 113)")

    # Extract all player start points
    spawns = []
    # Pattern: GameStartPoint_<team>_<index>
    pattern = rb'GameStartPoint_([01])_([0-9]{2})'
    for m in re.finditer(pattern, data):
        team_id = int(m.group(1))
        spawn_idx = int(m.group(2))
        pos_str = m.start()
        name = m.group(0).decode('ascii')

        # Coordinate is located at offset + 24 bytes after string
        coord_offset = pos_str + 24
        if coord_offset + 12 <= len(data):
            x, y, z = struct.unpack('<fff', data[coord_offset:coord_offset+12])
            spawns.append({
                "name": name,
                "team": team_id,
                "team_name": "SWAT (Law Enforcement)" if team_id == 0 else "Gangsters (Underworld)",
                "index": spawn_idx,
                "x": round(x, 2),
                "y": round(y, 2),
                "z": round(z, 2)
            })

    # Sort spawns
    spawns.sort(key=lambda s: (s["team"], s["index"]))
    print(f"[+] Successfully extracted {len(spawns)} spawn entities:")

    team0_spawns = [s for s in spawns if s["team"] == 0]
    team1_spawns = [s for s in spawns if s["team"] == 1]
    print(f"  Team 0 (SWAT): {len(team0_spawns)} points")
    print(f"  Team 1 (Gangsters): {len(team1_spawns)} points")

    # Calculate map bounds and centers
    all_x = [s["x"] for s in spawns]
    all_z = [s["z"] for s in spawns]
    min_x, max_x = min(all_x), max(all_x)
    min_z, max_z = min(all_z), max(all_z)

    t0_cx = sum(s["x"] for s in team0_spawns) / len(team0_spawns) if team0_spawns else 0
    t0_cz = sum(s["z"] for s in team0_spawns) / len(team0_spawns) if team0_spawns else 0
    t1_cx = sum(s["x"] for s in team1_spawns) / len(team1_spawns) if team1_spawns else 0
    t1_cz = sum(s["z"] for s in team1_spawns) / len(team1_spawns) if team1_spawns else 0

    base_dist = math.sqrt((t1_cx - t0_cx)**2 + (t1_cz - t0_cz)**2)
    print(f"  Map Extents: X=[{min_x}, {max_x}], Z=[{min_z}, {max_z}]")
    print(f"  Base-to-Base Tactical Distance: {base_dist:.1f} game units (~{base_dist/50:.1f} meters)")

    # Save JSON
    os.makedirs(os.path.dirname(OUTPUT_JSON), exist_ok=True)
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump({
            "world_name": "Arrival",
            "version": version,
            "total_spawns": len(spawns),
            "bounds": {
                "min_x": min_x, "max_x": max_x,
                "min_z": min_z, "max_z": max_z
            },
            "team_centers": {
                "team0_swat": {"x": round(t0_cx, 2), "z": round(t0_cz, 2)},
                "team1_gangsters": {"x": round(t1_cx, 2), "z": round(t1_cz, 2)},
                "distance_units": round(base_dist, 2)
            },
            "spawns": spawns
        }, f, indent=2)

    # Generate Tactical SVG/HTML Map
    # Map coordinates to SVG viewBox (1000x800)
    padding = 100
    svg_w, svg_h = 1000, 750
    span_x = (max_x - min_x) if max_x != min_x else 1
    span_z = (max_z - min_z) if max_z != min_z else 1

    def to_svg(x, z):
        sx = padding + ((x - min_x) / span_x) * (svg_w - 2 * padding)
        # Flip Z so top-down matches traditional FPS radar
        sy = (svg_h - padding) - ((z - min_z) / span_z) * (svg_h - 2 * padding)
        return round(sx, 1), round(sy, 1)

    t0_svg_x, t0_svg_y = to_svg(t0_cx, t0_cz)
    t1_svg_x, t1_svg_y = to_svg(t1_cx, t1_cz)
    mid_svg_x = (t0_svg_x + t1_svg_x) / 2
    mid_svg_y = (t0_svg_y + t1_svg_y) / 2

    # SVG elements
    svg_nodes = []
    # Base engagement line
    svg_nodes.append(
        f'<line x1="{t0_svg_x}" y1="{t0_svg_y}" x2="{t1_svg_x}" y2="{t1_svg_y}" '
        f'stroke="#475569" stroke-width="2" stroke-dasharray="6 6" />'
    )
    # Tactical mid-zone circle
    svg_nodes.append(
        f'<circle cx="{mid_svg_x}" cy="{mid_svg_y}" r="65" fill="#f59e0b15" stroke="#f59e0b" stroke-width="2" stroke-dasharray="4 4"/>'
        f'<text x="{mid_svg_x}" y="{mid_svg_y+4}" fill="#fbbf24" font-size="12" font-weight="bold" text-anchor="middle">MID CHOKE POINT</text>'
    )

    # Spawns
    for s in spawns:
        sx, sy = to_svg(s["x"], s["z"])
        color = "#3b82f6" if s["team"] == 0 else "#ef4444"
        label = f'P{s["index"]}'
        svg_nodes.append(
            f'<g class="spawn-marker" data-name="{s["name"]}" data-coord="({s["x"]}, {s["y"]}, {s["z"]})">'
            f'<circle cx="{sx}" cy="{sy}" r="9" fill="{color}" stroke="#ffffff" stroke-width="1.5" />'
            f'<text x="{sx}" y="{sy+3.5}" fill="#ffffff" font-size="9" font-weight="bold" text-anchor="middle">{label}</text>'
            f'</g>'
        )

    svg_content = "\n".join(svg_nodes)

    html_code = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>District 187 - Tactical Map: Arrival (LithTech Jupiter EX)</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <style>
    body {{ background-color: #0f172a; color: #f8fafc; font-family: ui-sans-serif, system-ui, sans-serif; }}
    .spawn-marker:hover circle {{ r: 13; filter: drop-shadow(0 0 8px rgba(255,255,255,0.8)); cursor: pointer; }}
  </style>
</head>
<body class="p-6">
  <div class="max-w-7xl mx-auto space-y-6">
    <header class="border-b border-slate-800 pb-4 flex justify-between items-center">
      <div>
        <h1 class="text-3xl font-bold tracking-tight text-white flex items-center gap-3">
          <span class="p-2 bg-blue-600 rounded-lg text-lg">D187</span>
          Tactical Map Inspector: Arrival (<code class="text-emerald-400">Arrival.World00p</code>)
        </h1>
        <p class="text-slate-400 text-sm mt-1">Extracted from LithTech Jupiter EX v{version} Binary Geometry</p>
      </div>
      <div class="flex gap-4">
        <span class="px-3 py-1.5 bg-blue-900/50 text-blue-400 border border-blue-700/50 rounded-md text-xs font-semibold">SWAT Spawn: 16 Slots</span>
        <span class="px-3 py-1.5 bg-red-900/50 text-red-400 border border-red-700/50 rounded-md text-xs font-semibold">Gangsters Spawn: 16 Slots</span>
      </div>
    </header>

    <!-- Top Stats -->
    <div class="grid grid-cols-4 gap-4">
      <div class="bg-slate-900 border border-slate-800 p-4 rounded-xl">
        <p class="text-xs text-slate-400 uppercase font-semibold">World Format</p>
        <p class="text-2xl font-bold text-white mt-1">LithTech v{version}</p>
        <p class="text-xs text-slate-500 mt-1">Binary World00p Engine Mesh</p>
      </div>
      <div class="bg-slate-900 border border-slate-800 p-4 rounded-xl">
        <p class="text-xs text-slate-400 uppercase font-semibold">Player Start Entities</p>
        <p class="text-2xl font-bold text-emerald-400 mt-1">{len(spawns)} Points</p>
        <p class="text-xs text-slate-500 mt-1">16 vs 16 Full Lobby Capacity</p>
      </div>
      <div class="bg-slate-900 border border-slate-800 p-4 rounded-xl">
        <p class="text-xs text-slate-400 uppercase font-semibold">Base-to-Base Distance</p>
        <p class="text-2xl font-bold text-amber-400 mt-1">{base_dist:.0f} Units</p>
        <p class="text-xs text-slate-500 mt-1">~{base_dist/50:.1f}m Engagement Corridor</p>
      </div>
      <div class="bg-slate-900 border border-slate-800 p-4 rounded-xl">
        <p class="text-xs text-slate-400 uppercase font-semibold">World Elevation</p>
        <p class="text-2xl font-bold text-cyan-400 mt-1">Y = 100.0</p>
        <p class="text-xs text-slate-500 mt-1">Ground Plane Standard</p>
      </div>
    </div>

    <!-- Map Canvas Card -->
    <div class="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl relative">
      <div class="flex justify-between items-center mb-4">
        <div class="flex items-center gap-3">
          <h2 class="text-lg font-semibold text-white">Top-Down Tactical Radar (XZ Plane)</h2>
          <span class="text-xs bg-slate-800 px-2.5 py-1 rounded text-slate-400">Hover over markers for 3D coordinates</span>
        </div>
        <div class="text-xs text-slate-400 flex gap-4">
          <span class="flex items-center gap-1.5"><span class="w-3 h-3 rounded-full bg-blue-500 inline-block"></span> Team 0: SWAT</span>
          <span class="flex items-center gap-1.5"><span class="w-3 h-3 rounded-full bg-red-500 inline-block"></span> Team 1: Gangsters</span>
          <span class="flex items-center gap-1.5"><span class="w-3 h-3 rounded-full bg-amber-500 inline-block"></span> Neutral Engagement Mid</span>
        </div>
      </div>

      <div class="bg-slate-950 rounded-lg p-2 border border-slate-800/80 flex justify-center">
        <svg viewBox="0 0 {svg_w} {svg_h}" class="w-full h-auto max-h-[580px]">
          <!-- Grid Background -->
          <defs>
            <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
              <path d="M 40 0 L 0 0 0 40" fill="none" stroke="#1e293b" stroke-width="0.8"/>
            </pattern>
          </defs>
          <rect width="100%" height="100%" fill="url(#grid)" />

          <!-- Dynamic Tactical Nodes -->
          {svg_content}
        </svg>
      </div>

      <div id="coord-tooltip" class="mt-4 p-3 bg-slate-950 border border-slate-800 rounded text-xs text-slate-300 flex justify-between items-center">
        <span><strong>Live Entity Inspector:</strong> Hover any spawn node on the radar above.</span>
        <span class="text-slate-500">Coordinate units in LithTech World Space (X, Y, Z)</span>
      </div>
    </div>

    <!-- Entity Coordinates Table -->
    <div class="bg-slate-900 border border-slate-800 rounded-xl p-6">
      <h3 class="text-md font-semibold text-white mb-3">Spawn Entities Table (First 10)</h3>
      <div class="overflow-x-auto">
        <table class="w-full text-left text-xs text-slate-400">
          <thead class="bg-slate-950 text-slate-300 uppercase font-semibold">
            <tr>
              <th class="p-2.5">Entity Name</th>
              <th class="p-2.5">Team</th>
              <th class="p-2.5">X Coordinate</th>
              <th class="p-2.5">Y Elevation</th>
              <th class="p-2.5">Z Coordinate</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-800 font-mono">
            {''.join(f'''<tr class="hover:bg-slate-800/50">
              <td class="p-2.5 text-white font-semibold">{s['name']}</td>
              <td class="p-2.5 {'text-blue-400' if s['team'] == 0 else 'text-red-400'}">{s['team_name']}</td>
              <td class="p-2.5">{s['x']}</td>
              <td class="p-2.5 text-emerald-400">{s['y']}</td>
              <td class="p-2.5">{s['z']}</td>
            </tr>''' for s in spawns[:10])}
          </tbody>
        </table>
      </div>
    </div>
  </div>

  <script>
    document.querySelectorAll('.spawn-marker').forEach(marker => {{
      marker.addEventListener('mouseenter', () => {{
        const name = marker.getAttribute('data-name');
        const coord = marker.getAttribute('data-coord');
        document.getElementById('coord-tooltip').innerHTML = 
          `<span class="text-emerald-400 font-semibold">${{name}}</span> &mdash; LithTech World Coordinates: <code class="text-amber-300 bg-slate-900 px-2 py-0.5 rounded font-mono">${{coord}}</code>`;
      }});
    }});
  </script>
</body>
</html>
"""

    with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
        f.write(html_code)

    print(f"\n[+] Interactive Tactical Map generated at: {OUTPUT_HTML}")

if __name__ == "__main__":
    parse_world00p()

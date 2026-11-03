#!/usr/bin/env python3
"""
District 187: Sin Streets - Universal Tactical NavMesh & A* Pathfinding Generator
Synthesizes waypoint graphs, cover heuristics, and A* routing (Direct Assault vs Stealth Flanking)
for all competitive scenarios (Arrival, TwoWay, TheBank, OldTown, Heaven).
Outputs:
  - targets/district-187/data/navmeshes/<map_name>_navmesh.json
  - targets/district-187/navmeshes/<map_name>_navmesh.html
"""

import os
import sys
import json
import math
import heapq
import argparse
from typing import Dict, List, Tuple, Any, Optional

# Ensure UTF-8 output
sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TARGET_DIR = os.path.join(BASE_DIR, "targets", "district-187")
MAPS_DATA_DIR = os.path.join(TARGET_DIR, "data", "maps")
NAVMESH_DATA_DIR = os.path.join(TARGET_DIR, "data", "navmeshes")
NAVMESH_HTML_DIR = os.path.join(TARGET_DIR, "navmeshes")

os.makedirs(NAVMESH_DATA_DIR, exist_ok=True)
os.makedirs(NAVMESH_HTML_DIR, exist_ok=True)

def euclidean_dist(p1: Dict[str, float], p2: Dict[str, float]) -> float:
    return math.sqrt((p1["x"] - p2["x"])**2 + (p1["z"] - p2["z"])**2)

class TacticalNavMesh:
    def __init__(self, map_name: str, waypoints: Dict[str, Any], edges: List[Tuple[str, str, float]], bounds: Dict[str, float]):
        self.map_name = map_name
        self.waypoints = waypoints
        self.edges = edges
        self.bounds = bounds
        self.graph = self._build_graph()

    def _build_graph(self) -> Dict[str, List[Dict[str, Any]]]:
        g = {k: [] for k in self.waypoints}
        for u, v, cover in self.edges:
            if u in self.waypoints and v in self.waypoints:
                dist = euclidean_dist(self.waypoints[u], self.waypoints[v])
                g[u].append({"node": v, "dist": dist, "cover": cover})
                g[v].append({"node": u, "dist": dist, "cover": cover})
        return g

    def a_star(self, start_key: str, goal_key: str, route_type: str = "direct") -> Tuple[Optional[List[str]], float]:
        if start_key not in self.waypoints or goal_key not in self.waypoints:
            return None, float('inf')

        frontier = []
        heapq.heappush(frontier, (0.0, start_key, [start_key]))
        cost_so_far = {start_key: 0.0}

        while frontier:
            current_cost, current_node, path = heapq.heappop(frontier)

            if current_node == goal_key:
                return path, current_cost

            for edge in self.graph.get(current_node, []):
                next_node = edge["node"]
                dist = edge["dist"]
                cover = edge["cover"]

                # Direct uses raw distance; stealth divides distance by cover factor (favors high cover)
                weight = dist if route_type == "direct" else (dist / max(cover, 0.1))
                new_cost = cost_so_far[current_node] + weight

                if next_node not in cost_so_far or new_cost < cost_so_far[next_node]:
                    cost_so_far[next_node] = new_cost
                    priority = new_cost + euclidean_dist(self.waypoints[next_node], self.waypoints[goal_key])
                    heapq.heappush(frontier, (priority, next_node, path + [next_node]))

        return None, float('inf')

    def to_json(self) -> Dict[str, Any]:
        return {
            "map_name": self.map_name,
            "bounds": self.bounds,
            "waypoints": self.waypoints,
            "edges": [{"from": u, "to": v, "cover": c} for u, v, c in self.edges]
        }

def build_twoway_navmesh(map_data: Dict[str, Any]) -> TacticalNavMesh:
    # TwoWay Demolition NavMesh
    b = map_data["bounds"]
    t0_spawns = [s for s in map_data["spawns"] if s["team"] == 0]
    t1_spawns = [s for s in map_data["spawns"] if s["team"] == 1]
    
    t0_cx = sum(s["x"] for s in t0_spawns) / len(t0_spawns)
    t0_cz = sum(s["z"] for s in t0_spawns) / len(t0_spawns)
    t1_cx = sum(s["x"] for s in t1_spawns) / len(t1_spawns)
    t1_cz = sum(s["z"] for s in t1_spawns) / len(t1_spawns)

    bomb_a = next((b for b in map_data["bomb_sites"] if "A" in b["site"]), {"x": 1965.0, "z": -2375.0})
    bomb_b = next((b for b in map_data["bomb_sites"] if "B" in b["site"]), {"x": 3825.0, "z": 765.0})

    waypoints = {
        "SWAT_BASE": {"name": "SWAT Deployment Base", "x": t0_cx, "z": t0_cz, "type": "spawn_swat"},
        "SWAT_SNIPER": {"name": "Overpass Sniper Post", "x": t0_cx + 500.0, "z": t0_cz - 400.0, "type": "vantage"},
        "ALLEY_A": {"name": "Narrow Alley to Site A", "x": (t0_cx + bomb_a["x"]) / 2, "z": bomb_a["z"] + 300.0, "type": "corridor"},
        "BOMB_SITE_A": {"name": "Bomb Site A (Lower Warehouse)", "x": bomb_a["x"], "z": bomb_a["z"], "type": "objective"},
        "MID_STREET": {"name": "Central Boulevard Choke", "x": (t0_cx + t1_cx) / 2, "z": (t0_cz + t1_cz) / 2, "type": "choke"},
        "TUNNEL_B": {"name": "Underground Passage to B", "x": (t0_cx + bomb_b["x"]) / 2, "z": (t0_cz + bomb_b["z"]) / 2 - 200.0, "type": "tunnel"},
        "BOMB_SITE_B": {"name": "Bomb Site B (Upper Plaza)", "x": bomb_b["x"], "z": bomb_b["z"], "type": "objective"},
        "GANG_SNIPER": {"name": "Rooftop Overlook", "x": t1_cx - 400.0, "z": t1_cz + 300.0, "type": "vantage"},
        "GANG_BASE": {"name": "Gangsters Deployment Base", "x": t1_cx, "z": t1_cz, "type": "spawn_gang"}
    }

    edges = [
        ("SWAT_BASE", "SWAT_SNIPER", 0.8),
        ("SWAT_BASE", "ALLEY_A", 0.7),
        ("SWAT_BASE", "TUNNEL_B", 0.9),
        ("SWAT_SNIPER", "MID_STREET", 0.4),
        ("ALLEY_A", "BOMB_SITE_A", 0.7),
        ("ALLEY_A", "MID_STREET", 0.5),
        ("BOMB_SITE_A", "MID_STREET", 0.6),
        ("BOMB_SITE_A", "GANG_BASE", 0.6),
        ("TUNNEL_B", "BOMB_SITE_B", 0.8),
        ("MID_STREET", "BOMB_SITE_B", 0.5),
        ("BOMB_SITE_B", "GANG_SNIPER", 0.7),
        ("BOMB_SITE_B", "GANG_BASE", 0.8),
        ("GANG_SNIPER", "GANG_BASE", 0.85)
    ]

    return TacticalNavMesh("twoway", waypoints, edges, b)

def build_thebank_navmesh(map_data: Dict[str, Any]) -> TacticalNavMesh:
    b = map_data["bounds"]
    t0_spawns = [s for s in map_data["spawns"] if s["team"] == 0]
    t1_spawns = [s for s in map_data["spawns"] if s["team"] == 1]
    
    t0_cx = sum(s["x"] for s in t0_spawns) / len(t0_spawns)
    t0_cz = sum(s["z"] for s in t0_spawns) / len(t0_spawns)
    t1_cx = sum(s["x"] for s in t1_spawns) / len(t1_spawns)
    t1_cz = sum(s["z"] for s in t1_spawns) / len(t1_spawns)

    waypoints = {
        "POLICE_PERIMETER": {"name": "Police Cordon (Street)", "x": t0_cx, "z": t0_cz, "type": "spawn_swat"},
        "FRONT_ENTRANCE": {"name": "Bank Revolving Doors", "x": t0_cx * 0.7 + t1_cx * 0.3, "z": t0_cz * 0.7 + t1_cz * 0.3, "type": "corridor"},
        "BANK_LOBBY": {"name": "Marble Central Lobby", "x": (t0_cx + t1_cx) / 2, "z": (t0_cz + t1_cz) / 2, "type": "choke"},
        "SIDE_ALLEY": {"name": "Security Emergency Exit", "x": t0_cx + 800.0, "z": (t0_cz + t1_cz) / 2, "type": "tunnel"},
        "VAULT_GATE": {"name": "Heavy Steel Vault Gate", "x": t1_cx * 0.7 + t0_cx * 0.3, "z": t1_cz * 0.7 + t0_cz * 0.3, "type": "choke"},
        "GOLD_VAULT": {"name": "Subterranean Gold Vault", "x": t1_cx - 400.0, "z": t1_cz - 200.0, "type": "objective"},
        "ESCAPE_VAN": {"name": "Robbers Getaway Van", "x": t1_cx, "z": t1_cz, "type": "spawn_gang"}
    }

    edges = [
        ("POLICE_PERIMETER", "FRONT_ENTRANCE", 0.4),
        ("POLICE_PERIMETER", "SIDE_ALLEY", 0.75),
        ("FRONT_ENTRANCE", "BANK_LOBBY", 0.5),
        ("SIDE_ALLEY", "BANK_LOBBY", 0.8),
        ("SIDE_ALLEY", "VAULT_GATE", 0.7),
        ("BANK_LOBBY", "VAULT_GATE", 0.6),
        ("VAULT_GATE", "GOLD_VAULT", 0.9),
        ("GOLD_VAULT", "ESCAPE_VAN", 0.8)
    ]

    return TacticalNavMesh("thebank", waypoints, edges, b)

def build_universal_navmesh(map_data: Dict[str, Any]) -> TacticalNavMesh:
    map_name = map_data["map_name"]
    b = map_data["bounds"]
    spawns = map_data["spawns"]

    t0_spawns = [s for s in spawns if s["team"] == 0]
    t1_spawns = [s for s in spawns if s["team"] == 1]

    t0_cx = sum(s["x"] for s in t0_spawns) / len(t0_spawns) if t0_spawns else b["min_x"]
    t0_cz = sum(s["z"] for s in t0_spawns) / len(t0_spawns) if t0_spawns else b["min_z"]
    t1_cx = sum(s["x"] for s in t1_spawns) / len(t1_spawns) if t1_spawns else b["max_x"]
    t1_cz = sum(s["z"] for s in t1_spawns) / len(t1_spawns) if t1_spawns else b["max_z"]

    mid_x = (t0_cx + t1_cx) / 2
    mid_z = (t0_cz + t1_cz) / 2
    delta_x = t1_cx - t0_cx
    delta_z = t1_cz - t0_cz
    perp_x = -delta_z * 0.35
    perp_z = delta_x * 0.35

    waypoints = {
        "SWAT_BASE": {"name": "SWAT Spawn HQ", "x": t0_cx, "z": t0_cz, "type": "spawn_swat"},
        "SWAT_FORWARD": {"name": "SWAT Forward Line", "x": t0_cx * 0.65 + mid_x * 0.35, "z": t0_cz * 0.65 + mid_z * 0.35, "type": "corridor"},
        "FLANK_LEFT": {"name": "Left Flank Corridor", "x": mid_x + perp_x, "z": mid_z + perp_z, "type": "tunnel"},
        "MID_CHOKE": {"name": "Central Choke Point", "x": mid_x, "z": mid_z, "type": "choke"},
        "FLANK_RIGHT": {"name": "Right Flank Corridor", "x": mid_x - perp_x, "z": mid_z - perp_z, "type": "corridor"},
        "GANG_FORWARD": {"name": "Gangster Forward Line", "x": t1_cx * 0.65 + mid_x * 0.35, "z": t1_cz * 0.65 + mid_z * 0.35, "type": "corridor"},
        "GANG_BASE": {"name": "Gangster Spawn HQ", "x": t1_cx, "z": t1_cz, "type": "spawn_gang"}
    }

    edges = [
        ("SWAT_BASE", "SWAT_FORWARD", 0.75),
        ("SWAT_FORWARD", "FLANK_LEFT", 0.8),
        ("SWAT_FORWARD", "MID_CHOKE", 0.45),
        ("SWAT_FORWARD", "FLANK_RIGHT", 0.8),
        ("FLANK_LEFT", "GANG_FORWARD", 0.85),
        ("MID_CHOKE", "GANG_FORWARD", 0.5),
        ("FLANK_RIGHT", "GANG_FORWARD", 0.8),
        ("GANG_FORWARD", "GANG_BASE", 0.75)
    ]

    return TacticalNavMesh(map_name, waypoints, edges, b)

def render_navmesh_html(navmesh: TacticalNavMesh):
    map_name = navmesh.map_name
    wps = navmesh.waypoints
    b = navmesh.bounds

    svg_w = 900
    svg_h = 600
    pad = 70

    span_x = max(b["span_x"], 100.0)
    span_z = max(b["span_z"], 100.0)

    def tx(x):
        return pad + ((x - b["min_x"]) / span_x) * (svg_w - 2 * pad)

    def ty(z):
        return svg_h - pad - ((z - b["min_z"]) / span_z) * (svg_h - 2 * pad)

    # Compute A* routes: direct vs stealth
    direct_path, direct_cost = navmesh.a_star("SWAT_BASE", list(wps.keys())[-1], "direct")
    stealth_path, stealth_cost = navmesh.a_star("SWAT_BASE", list(wps.keys())[-1], "stealth")

    svg_elements = []

    # Edges
    for u, v, cover in navmesh.edges:
        if u in wps and v in wps:
            x1, y1 = tx(wps[u]["x"]), ty(wps[u]["z"])
            x2, y2 = tx(wps[v]["x"]), ty(wps[v]["z"])
            svg_elements.append(
                f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
                f'stroke="#334155" stroke-width="2.5" />'
            )

    # Direct Route overlay (Cyan)
    if direct_path:
        pts = " ".join([f"{tx(wps[n]['x']):.1f},{ty(wps[n]['z']):.1f}" for n in direct_path])
        svg_elements.append(
            f'<polyline points="{pts}" fill="none" stroke="#06b6d4" stroke-width="4.5" stroke-dasharray="8,6" opacity="0.85" />'
        )

    # Stealth Route overlay (Emerald)
    if stealth_path and stealth_path != direct_path:
        pts = " ".join([f"{tx(wps[n]['x']):.1f},{ty(wps[n]['z']):.1f}" for n in stealth_path])
        svg_elements.append(
            f'<polyline points="{pts}" fill="none" stroke="#10b981" stroke-width="4.5" stroke-dasharray="4,4" opacity="0.85" />'
        )

    # Waypoints
    for k, wp in wps.items():
        wx, wy = tx(wp["x"]), ty(wp["z"])
        col = "#3b82f6" if "swat" in wp["type"] else "#ef4444" if "gang" in wp["type"] else "#f59e0b" if "objective" in wp["type"] else "#a855f7"
        svg_elements.append(
            f'<g class="wp-node" data-name="{wp["name"]}" data-type="{wp["type"]}">'
            f'<circle cx="{wx:.1f}" cy="{wy:.1f}" r="12" fill="{col}" stroke="#ffffff" stroke-width="2" />'
            f'<text x="{wx:.1f}" y="{wy-16:.1f}" fill="#cbd5e1" font-size="10" font-weight="bold" text-anchor="middle">{wp["name"]}</text>'
            f'</g>'
        )

    svg_content = "\n".join(svg_elements)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>D187 A* NavMesh Inspector: {map_name}</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <style>
    body {{ background-color: #0b1120; color: #f8fafc; font-family: ui-sans-serif, system-ui, sans-serif; }}
    .wp-node:hover circle {{ r: 16; filter: drop-shadow(0 0 10px rgba(255,255,255,0.9)); cursor: pointer; }}
  </style>
</head>
<body class="p-6">
  <div class="max-w-7xl mx-auto space-y-6">
    <header class="border-b border-slate-800 pb-4 flex justify-between items-center">
      <div>
        <h1 class="text-3xl font-bold tracking-tight text-white flex items-center gap-3">
          <span class="p-2 bg-emerald-600 rounded-lg text-lg">A*</span>
          Tactical NavMesh & Bot Routes: <span class="text-emerald-400 font-mono">{map_name}</span>
        </h1>
        <p class="text-slate-400 text-sm mt-1">Autonomous Graph Pathfinding & Cover Analysis</p>
      </div>
      <div class="flex gap-3">
        <span class="px-3 py-1.5 bg-cyan-950 text-cyan-400 border border-cyan-800 rounded-md text-xs font-semibold">Direct Assault Route ({len(direct_path or [])} Waypoints)</span>
        <span class="px-3 py-1.5 bg-emerald-950 text-emerald-400 border border-emerald-800 rounded-md text-xs font-semibold">Stealth Flank Route ({len(stealth_path or [])} Waypoints)</span>
      </div>
    </header>

    <div class="grid grid-cols-4 gap-4">
      <div class="bg-slate-900 border border-slate-800 p-4 rounded-xl">
        <p class="text-xs text-slate-400 uppercase font-semibold">Total Graph Nodes</p>
        <p class="text-2xl font-bold text-white mt-1">{len(wps)} Waypoints</p>
        <p class="text-xs text-slate-500 mt-1">{len(navmesh.edges)} Connected Lanes</p>
      </div>
      <div class="bg-slate-900 border border-slate-800 p-4 rounded-xl">
        <p class="text-xs text-slate-400 uppercase font-semibold">Direct Assault Cost</p>
        <p class="text-2xl font-bold text-cyan-400 mt-1">{direct_cost:.0f} u</p>
        <p class="text-xs text-slate-500 mt-1">Shortest Path Metric</p>
      </div>
      <div class="bg-slate-900 border border-slate-800 p-4 rounded-xl">
        <p class="text-xs text-slate-400 uppercase font-semibold">Stealth Flank Cost</p>
        <p class="text-2xl font-bold text-emerald-400 mt-1">{stealth_cost:.0f} u</p>
        <p class="text-xs text-slate-500 mt-1">Weighted by Cover Quality</p>
      </div>
      <div class="bg-slate-900 border border-slate-800 p-4 rounded-xl">
        <p class="text-xs text-slate-400 uppercase font-semibold">Algorithm</p>
        <p class="text-2xl font-bold text-purple-400 mt-1">A* Heuristic</p>
        <p class="text-xs text-slate-500 mt-1">Euclidean Admissible Search</p>
      </div>
    </div>

    <div class="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-2xl relative">
      <div class="flex justify-between items-center mb-4">
        <h2 class="text-lg font-semibold text-white">NavMesh Navigation Graph & Optimal Paths</h2>
        <div class="text-xs text-slate-400 flex gap-4">
          <span class="flex items-center gap-1.5"><span class="w-3 h-3 rounded-full bg-cyan-500 inline-block"></span> Direct Route</span>
          <span class="flex items-center gap-1.5"><span class="w-3 h-3 rounded-full bg-emerald-500 inline-block"></span> Stealth Flank</span>
          <span class="flex items-center gap-1.5"><span class="w-3 h-3 rounded-full bg-amber-500 inline-block"></span> Objective</span>
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
    </div>
  </div>
</body>
</html>
"""
    out_html = os.path.join(NAVMESH_HTML_DIR, f"{map_name}_navmesh.html")
    with open(out_html, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"[+] Generated NavMesh Radar HTML: {os.path.basename(out_html)}")

def process_map(map_name: str):
    json_path = os.path.join(MAPS_DATA_DIR, f"{map_name}.json")
    if not os.path.exists(json_path):
        print(f"[-] Map metadata not found for: {map_name}")
        return

    with open(json_path, "r", encoding="utf-8") as f:
        map_data = json.load(f)

    if map_name == "twoway" or map_name == "twoway_night":
        nav = build_twoway_navmesh(map_data)
    elif map_name == "thebank":
        nav = build_thebank_navmesh(map_data)
    else:
        nav = build_universal_navmesh(map_data)

    # Save NavMesh JSON
    nav_json_path = os.path.join(NAVMESH_DATA_DIR, f"{map_name}_navmesh.json")
    with open(nav_json_path, "w", encoding="utf-8") as f:
        json.dump(nav.to_json(), f, indent=2)

    # Render HTML
    render_navmesh_html(nav)
    print(f"[+] NavMesh synthesized: {map_name:20s} | Waypoints: {len(nav.waypoints)} | Lanes: {len(nav.edges)}")

def main():
    parser = argparse.ArgumentParser(description="Universal Tactical NavMesh & A* Route Generator")
    parser.add_argument("--map", help="Map name to generate (e.g. twoway, thebank, Arrival, oldtown)")
    parser.add_argument("--all", action="store_true", help="Generate NavMeshes for all parsed maps")
    args = parser.parse_args()

    if args.all:
        import glob
        maps = [os.path.splitext(os.path.basename(p))[0] for p in glob.glob(os.path.join(MAPS_DATA_DIR, "*.json"))]
        for m in sorted(maps):
            process_map(m)
    elif args.map:
        process_map(args.map)
    else:
        for m in ["twoway", "thebank", "oldtown", "Arrival", "10025_Heaven"]:
            process_map(m)

if __name__ == "__main__":
    main()

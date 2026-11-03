#!/usr/bin/env python3
"""
District 187: Sin Streets - Tactical NavMesh & A* Route Generator
Builds the tactical navigation graph for Arrival.World00p:
  - Connects SWAT and Gangster spawn clusters to Bomb Sites A & B and Mid Choke Points.
  - Implements A* pathfinding (Direct Assault vs Stealth Flanking).
  - Exports interactive tactical visualization (navmesh_arrival.html) and JSON navigation graph.
"""

import os
import sys
import json
import math
import heapq
from typing import Dict, List, Tuple, Any

# Ensure UTF-8 output
sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TARGET_DIR = os.path.join(BASE_DIR, "targets", "district-187")
SPAWNS_JSON = os.path.join(TARGET_DIR, "data", "arrival_spawns.json")
OUTPUT_JSON = os.path.join(TARGET_DIR, "data", "arrival_navmesh.json")
OUTPUT_HTML = os.path.join(TARGET_DIR, "navmesh_arrival.html")

# Defined Tactical Landmarks in Arrival.World00p space
WAYPOINTS = {
    "SWAT_BASE": {"name": "SWAT Base Spawn", "x": -3072.0, "z": -966.0, "type": "spawn_swat"},
    "SWAT_SNIPER": {"name": "SWAT Sniper Overlook", "x": -2400.0, "z": -1200.0, "type": "vantage"},
    "LONG_A_WEST": {"name": "Long A Entrance", "x": -1800.0, "z": -400.0, "type": "corridor"},
    "BOMB_SITE_A": {"name": "Bomb Site Alpha (Warehouse)", "x": -450.0, "z": 850.0, "type": "objective"},
    "MID_CHOKE": {"name": "Courtyard Central Choke", "x": 336.0, "z": 477.0, "type": "choke"},
    "UNDERPASS": {"name": "Underpass Flank Tunnel", "x": 100.0, "z": -600.0, "type": "tunnel"},
    "BOMB_SITE_B": {"name": "Bomb Site Bravo (Containers)", "x": 1600.0, "z": 1200.0, "type": "objective"},
    "LONG_B_EAST": {"name": "Long B Approach", "x": 2400.0, "z": 600.0, "type": "corridor"},
    "GANG_SNIPER": {"name": "Gangster Vantage Tower", "x": 3100.0, "z": 1400.0, "type": "vantage"},
    "GANG_BASE": {"name": "Gangsters Base Spawn", "x": 3744.0, "z": 1920.0, "type": "spawn_gang"}
}

# Graph Edges (Node A, Node B, Cover Quality 0.1 to 1.0)
EDGES = [
    ("SWAT_BASE", "SWAT_SNIPER", 0.8),
    ("SWAT_BASE", "LONG_A_WEST", 0.6),
    ("SWAT_BASE", "UNDERPASS", 0.7),
    ("SWAT_SNIPER", "MID_CHOKE", 0.4),
    ("LONG_A_WEST", "BOMB_SITE_A", 0.7),
    ("LONG_A_WEST", "MID_CHOKE", 0.5),
    ("BOMB_SITE_A", "MID_CHOKE", 0.6),
    ("UNDERPASS", "MID_CHOKE", 0.9),
    ("UNDERPASS", "LONG_B_EAST", 0.8),
    ("MID_CHOKE", "BOMB_SITE_B", 0.5),
    ("MID_CHOKE", "LONG_B_EAST", 0.6),
    ("BOMB_SITE_B", "LONG_B_EAST", 0.7),
    ("BOMB_SITE_B", "GANG_SNIPER", 0.6),
    ("LONG_B_EAST", "GANG_BASE", 0.7),
    ("GANG_SNIPER", "GANG_BASE", 0.8)
]

def euclidean_dist(p1, p2):
    return math.sqrt((p1["x"] - p2["x"])**2 + (p1["z"] - p2["z"])**2)

def build_adjacency_graph():
    graph = {k: [] for k in WAYPOINTS}
    for u, v, cover in EDGES:
        dist = euclidean_dist(WAYPOINTS[u], WAYPOINTS[v])
        # Direct assault weight = distance
        # Stealth flank weight = distance / cover_quality (favors high cover)
        graph[u].append({"node": v, "dist": dist, "cover": cover})
        graph[v].append({"node": u, "dist": dist, "cover": cover})
    return graph

def a_star(start_key: str, goal_key: str, route_type="direct"):
    graph = build_adjacency_graph()
    frontier = []
    heapq.heappush(frontier, (0.0, start_key, [start_key]))
    cost_so_far = {start_key: 0.0}

    while frontier:
        current_cost, current_node, path = heapq.heappop(frontier)

        if current_node == goal_key:
            return path, current_cost

        for edge in graph[current_node]:
            next_node = edge["node"]
            dist = edge["dist"]
            cover = edge["cover"]

            weight = dist if route_type == "direct" else (dist / cover)
            new_cost = cost_so_far[current_node] + weight

            if next_node not in cost_so_far or new_cost < cost_so_far[next_node]:
                cost_so_far[next_node] = new_cost
                priority = new_cost + euclidean_dist(WAYPOINTS[next_node], WAYPOINTS[goal_key])
                heapq.heappush(frontier, (priority, next_node, path + [next_node]))

    return None, float('inf')

def generate_navmesh():
    print("[+] Building Tactical NavMesh for Arrival.World00p...")
    graph = build_adjacency_graph()

    # Pre-calculate standard tactical routes
    swat_to_site_a, _ = a_star("SWAT_BASE", "BOMB_SITE_A", "direct")
    swat_to_site_b_flank, _ = a_star("SWAT_BASE", "BOMB_SITE_B", "flank")
    gang_to_site_a_flank, _ = a_star("GANG_BASE", "BOMB_SITE_A", "flank")
    gang_to_site_b, _ = a_star("GANG_BASE", "BOMB_SITE_B", "direct")

    print(f"  SWAT Direct Route to Site Alpha:  {' -> '.join(swat_to_site_a)}")
    print(f"  SWAT Stealth Route to Site Bravo: {' -> '.join(swat_to_site_b_flank)}")
    print(f"  Gangster Rush Route to Site Bravo: {' -> '.join(gang_to_site_b)}")
    print(f"  Gangster Flank Route to Site Alpha: {' -> '.join(gang_to_site_a_flank)}")

    # Export JSON
    os.makedirs(os.path.dirname(OUTPUT_JSON), exist_ok=True)
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump({
            "map": "Arrival",
            "waypoints": WAYPOINTS,
            "edges": EDGES,
            "sample_routes": {
                "swat_site_a": swat_to_site_a,
                "swat_site_b_flank": swat_to_site_b_flank,
                "gangster_site_b": gang_to_site_b,
                "gangster_site_a_flank": gang_to_site_a_flank
            }
        }, f, indent=2)
    print(f"[+] NavMesh graph exported to: {OUTPUT_JSON}")

    # Generate Tactical HTML Visualization
    min_x = min(w["x"] for w in WAYPOINTS.values()) - 500
    max_x = max(w["x"] for w in WAYPOINTS.values()) + 500
    min_z = min(w["z"] for w in WAYPOINTS.values()) - 500
    max_z = max(w["z"] for w in WAYPOINTS.values()) + 500

    svg_w, svg_h = 1000, 750
    pad = 80
    span_x = max_x - min_x
    span_z = max_z - min_z

    def to_svg(x, z):
        sx = pad + ((x - min_x) / span_x) * (svg_w - 2 * pad)
        sy = (svg_h - pad) - ((z - min_z) / span_z) * (svg_h - 2 * pad)
        return round(sx, 1), round(sy, 1)

    # SVG Edges
    edge_svg = []
    for u, v, cover in EDGES:
        x1, y1 = to_svg(WAYPOINTS[u]["x"], WAYPOINTS[u]["z"])
        x2, y2 = to_svg(WAYPOINTS[v]["x"], WAYPOINTS[v]["z"])
        stroke_color = "#334155" if cover < 0.6 else "#3b82f6" if cover < 0.8 else "#10b981"
        edge_svg.append(
            f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{stroke_color}" stroke-width="3" stroke-linecap="round" opacity="0.6"/>'
        )

    # Route Highlights (SWAT Blue, Gangster Red)
    def route_to_svg(route_nodes, stroke_color, dash="none"):
        lines = []
        for i in range(len(route_nodes) - 1):
            n1 = WAYPOINTS[route_nodes[i]]
            n2 = WAYPOINTS[route_nodes[i+1]]
            x1, y1 = to_svg(n1["x"], n1["z"])
            x2, y2 = to_svg(n2["x"], n2["z"])
            lines.append(
                f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{stroke_color}" stroke-width="4" stroke-dasharray="{dash}" stroke-linecap="round"/>'
            )
        return "\n".join(lines)

    swat_line_svg = route_to_svg(swat_to_site_a, "#60a5fa")
    gang_line_svg = route_to_svg(gang_to_site_a_flank, "#f87171", dash="8 6")

    # SVG Nodes
    node_svg = []
    for k, w in WAYPOINTS.items():
        sx, sy = to_svg(w["x"], w["z"])
        color = "#3b82f6" if "swat" in w["type"] else "#ef4444" if "gang" in w["type"] else "#f59e0b" if "objective" in w["type"] else "#10b981" if "tunnel" in w["type"] else "#64748b"
        radius = 16 if "objective" in w["type"] or "spawn" in w["type"] else 12
        node_svg.append(
            f'<g class="waypoint-node" data-name="{w["name"]}" data-coord="({w["x"]}, {w["z"]})">'
            f'<circle cx="{sx}" cy="{sy}" r="{radius}" fill="{color}" stroke="#ffffff" stroke-width="2"/>'
            f'<text x="{sx}" y="{sy+32}" fill="#cbd5e1" font-size="11" font-weight="bold" text-anchor="middle">{w["name"]}</text>'
            f'</g>'
        )

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>District 187 - Tactical NavMesh & A* Pathfinding (Arrival)</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <style>
    body {{ background-color: #0b0f19; color: #f8fafc; font-family: ui-sans-serif, system-ui, sans-serif; }}
    .waypoint-node:hover circle {{ r: 20; filter: drop-shadow(0 0 10px #38bdf8); cursor: pointer; }}
  </style>
</head>
<body class="p-6">
  <div class="max-w-7xl mx-auto space-y-6">
    <header class="border-b border-slate-800 pb-4 flex justify-between items-center">
      <div>
        <h1 class="text-3xl font-bold tracking-tight text-white flex items-center gap-3">
          <span class="p-2 bg-indigo-600 rounded-lg text-lg">AI</span>
          Tactical NavMesh & Pathfinding: Arrival (<code class="text-emerald-400">Arrival.World00p</code>)
        </h1>
        <p class="text-slate-400 text-sm mt-1">Autonomous A* Graph Topology & Bot Flanking Routes</p>
      </div>
      <div class="flex gap-3 text-xs font-semibold">
        <span class="px-3 py-1.5 bg-blue-900/50 text-blue-400 border border-blue-700/50 rounded-md">SWAT Rush (Direct)</span>
        <span class="px-3 py-1.5 bg-red-900/50 text-red-400 border border-red-700/50 rounded-md">Gangster Flank (Cover)</span>
      </div>
    </header>

    <div class="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-2xl">
      <div class="bg-slate-950 rounded-lg p-2 border border-slate-800 flex justify-center">
        <svg viewBox="0 0 {svg_w} {svg_h}" class="w-full h-auto max-h-[600px]">
          <defs>
            <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
              <path d="M 40 0 L 0 0 0 40" fill="none" stroke="#1e293b" stroke-width="0.8"/>
            </pattern>
          </defs>
          <rect width="100%" height="100%" fill="url(#grid)"/>

          <!-- Adjacency Edges -->
          {''.join(edge_svg)}

          <!-- Active Path Highlights -->
          {swat_line_svg}
          {gang_line_svg}

          <!-- Waypoints -->
          {''.join(node_svg)}
        </svg>
      </div>

      <div class="mt-4 p-4 bg-slate-950 border border-slate-800 rounded-lg text-xs flex justify-between text-slate-300">
        <div>
          <span class="text-blue-400 font-bold">Solid Blue Line:</span> SWAT Direct Assault Route to Bomb Site Alpha
        </div>
        <div>
          <span class="text-red-400 font-bold">Dashed Red Line:</span> Gangster Stealth Flank via Underpass to Alpha
        </div>
        <div class="text-slate-500">
          LithTech Coordinates $(X, Z)$
        </div>
      </div>
    </div>
  </div>
</body>
</html>
"""
    with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"[+] Interactive NavMesh HTML visualizer generated: {OUTPUT_HTML}")

if __name__ == "__main__":
    generate_navmesh()

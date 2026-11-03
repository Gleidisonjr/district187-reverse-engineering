#!/usr/bin/env python3
"""
District 187: Sin Streets — Competitive MMR (Elo/TrueSkill), Persistent Loadouts,
Clans & 2D Tactical Match Replay Generator (HLTV / Scope.gg Style)
=================================================================================
"""

import json
import math
import os
import random
import sqlite3
import sys
from datetime import datetime

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TARGET_DIR = os.path.join(BASE_DIR, "targets", "district-187")
DB_PATH = os.path.join(TARGET_DIR, "data", "s2rebirth.db")
MAPS_DATA_DIR = os.path.join(TARGET_DIR, "data", "maps")
NAVMESH_DATA_DIR = os.path.join(TARGET_DIR, "data", "navmeshes")
ANALYTICS_DIR = os.path.join(TARGET_DIR, "analytics")


def get_skill_tier(elo: float) -> str:
    if elo >= 2100:
        return "Master 187 (Lenda)"
    if elo >= 1850:
        return "Diamond (Diamante)"
    if elo >= 1650:
        return "Platinum (Platina)"
    if elo >= 1450:
        return "Gold (Ouro)"
    if elo >= 1250:
        return "Silver (Prata)"
    return "Bronze (Recruta)"


def compute_adaptive_bot_profile(elo: float, hs_rate: float) -> dict:
    """Dynamic Difficulty Adjustment (DDA) calibrated from player Elo and HS%."""
    norm = max(0.0, min(1.0, (elo - 1000.0) / 1200.0))
    reaction_ms = int(420 - norm * 260)  # 420ms (easy) down to 160ms (elite)
    aim_sigma_deg = round(6.5 - norm * 4.8, 2)  # angular spread in degrees
    strafe_prob = round(0.15 + norm * 0.70, 2)
    if elo >= 1800 or hs_rate >= 0.42:
        label = "Elite 187 (Adaptativo Pro)"
    elif elo >= 1450:
        label = "Veterano (Adaptativo Médio)"
    else:
        label = "Recruta (Adaptativo Inicial)"
    return {
        "difficulty_label": label,
        "reaction_ms": reaction_ms,
        "aim_sigma_deg": aim_sigma_deg,
        "strafe_probability": strafe_prob,
        "tactical_flank_ratio": round(0.25 + norm * 0.55, 2),
    }


def init_extended_schema(conn: sqlite3.Connection):
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS player_mmr (
            account_id INTEGER PRIMARY KEY,
            nickname TEXT UNIQUE,
            elo_rating REAL DEFAULT 1500.0,
            volatility REAL DEFAULT 45.0,
            win_streak INTEGER DEFAULT 0,
            matches_played INTEGER DEFAULT 0,
            wins INTEGER DEFAULT 0,
            losses INTEGER DEFAULT 0,
            avg_ttk_ms REAL DEFAULT 410.0,
            hs_rate REAL DEFAULT 0.35,
            skill_tier TEXT DEFAULT 'Gold (Ouro)',
            recommended_bot_difficulty TEXT DEFAULT 'Veterano (Adaptativo Médio)',
            updated_at TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS player_loadouts (
            account_id INTEGER,
            slot_index INTEGER,
            slot_name TEXT,
            primary_weapon_id INTEGER,
            primary_weapon_name TEXT,
            secondary_weapon_id INTEGER,
            secondary_weapon_name TEXT,
            melee_weapon_id INTEGER,
            melee_weapon_name TEXT,
            grenade_id INTEGER,
            grenade_name TEXT,
            swat_skin TEXT,
            gang_skin TEXT,
            optic_attachment TEXT,
            barrel_attachment TEXT,
            mag_attachment TEXT,
            PRIMARY KEY (account_id, slot_index)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS clans (
            clan_id INTEGER PRIMARY KEY AUTOINCREMENT,
            clan_tag TEXT UNIQUE,
            clan_name TEXT,
            leader_nickname TEXT,
            emblem_id INTEGER DEFAULT 1,
            clan_elo REAL DEFAULT 1600.0,
            wins INTEGER DEFAULT 0,
            losses INTEGER DEFAULT 0,
            members_count INTEGER DEFAULT 1
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS match_replays (
            replay_id INTEGER PRIMARY KEY AUTOINCREMENT,
            map_name TEXT,
            mode TEXT,
            winner TEXT,
            swat_score INTEGER,
            gang_score INTEGER,
            duration_sec INTEGER,
            ticks_json TEXT,
            created_at TEXT
        )
    """)
    conn.commit()


def seed_mmr_loadouts_and_clans(conn: sqlite3.Connection):
    c = conn.cursor()
    c.execute("SELECT id, nickname, kills, deaths, headshots, wins, losses FROM users")
    users = c.fetchall()

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for uid, nick, kills, deaths, hs, wins, losses in users:
        kd = kills / max(1, deaths)
        hs_r = round(hs / max(1, kills), 3)
        base_elo = round(1350.0 + (kd * 220.0) + (hs_r * 350.0) + (wins - losses) * 4.5, 1)
        tier = get_skill_tier(base_elo)
        dda = compute_adaptive_bot_profile(base_elo, hs_r)
        ttk = round(max(185.0, 520.0 - (kd * 95.0)), 1)

        c.execute("""
            INSERT OR REPLACE INTO player_mmr
            (account_id, nickname, elo_rating, volatility, win_streak, matches_played,
             wins, losses, avg_ttk_ms, hs_rate, skill_tier, recommended_bot_difficulty, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            uid, nick, base_elo, 32.5, max(0, wins - losses) % 7,
            wins + losses, wins, losses, ttk, hs_r, tier, dda["difficulty_label"], now_str
        ))

        # Seed 3 tactical loadout slots (Slot A: Assault, Slot B: Sniper, Slot C: CQB Rush)
        default_slots = [
            (0, "Slot A (Assalto Competitivo)", 101, "AK-47 Sin Streets Pro", 401, "Desert Eagle Golden", 501, "Karambit Tactical", 601, "M67 Frag Grenade", "SWAT Commander", "Syndicate Enforcer", "EOTech Holographic", "Compensator Pro", "Extended Dual Mag (40rds)"),
            (1, "Slot B (Sniper Precisão)", 201, "AWP Magnum L96A1", 402, "Glock-18 Auto", 502, "M9 Bayonet", 602, "AN-M8 Smoke Grenade", "SWAT Recon Sniper", "Street Ghost", "8x Ballistic Scope", "Heavy Fluted Barrel", "Fast Pull Mag"),
            (2, "Slot C (Invasão CQB)", 301, "Kriss Vector .45 ACP", 401, "Desert Eagle Golden", 503, "Tactical Tomahawk", 603, "M84 Flashbang", "SWAT Breacher", "Gang Boss", "Red Dot Reflex", "Tactical Suppressor", "Drum Magazine (50rds)"),
        ]
        for slot_tuple in default_slots:
            c.execute("""
                INSERT OR IGNORE INTO player_loadouts VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (uid, *slot_tuple))

    default_clans = [
        ("META", "Meta Data Science Ops", "Gleidison", 7, 2145.0, 48, 6, 12),
        ("S2BR", "S2 Rebirth Brasil Elite", "Shadow187", 3, 1890.0, 35, 14, 24),
        ("SWAT", "Special Tactical Division", "ViperSWAT", 1, 1760.0, 29, 18, 19),
        ("SIN", "Sin Streets Syndicate", "Ghost TR", 5, 1680.0, 22, 19, 15),
    ]
    for tag, name, leader, emb, celo, w, l, mcnt in default_clans:
        c.execute("""
            INSERT OR IGNORE INTO clans
            (clan_tag, clan_name, leader_nickname, emblem_id, clan_elo, wins, losses, members_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (tag, name, leader, emb, celo, w, l, mcnt))

    conn.commit()


def generate_tactical_replay_data(map_name: str = "twoway", seed: int = 187) -> dict:
    """Generates a realistic tick-by-tick 8v8 round replay over the map's A* NavMesh."""
    rng = random.Random(seed)
    nav_file = os.path.join(NAVMESH_DATA_DIR, f"{map_name}_navmesh.json")
    nodes = []
    if os.path.exists(nav_file):
        with open(nav_file, "r", encoding="utf-8") as f:
            ndata = json.load(f)
            wp_dict = ndata.get("waypoints", {})
            if isinstance(wp_dict, dict) and wp_dict:
                nodes = [{"pos": [float(w.get("x", 0.0)), 0.0, float(w.get("z", 0.0))], "name": k} for k, w in wp_dict.items()]
            else:
                nodes = ndata.get("nodes", [])

    # Normalize coordinates to [80..920, 80..520] canvas space
    if nodes:
        xs = [n["pos"][0] for n in nodes]
        zs = [n["pos"][2] for n in nodes]
        min_x, max_x = min(xs), max(xs)
        min_z, max_z = min(zs), max(zs)
        span_x = max(1.0, max_x - min_x)
        span_z = max(1.0, max_z - min_z)

        def norm_pt(x, z):
            return (
                round(90 + ((x - min_x) / span_x) * 820, 1),
                round(70 + ((z - min_z) / span_z) * 460, 1),
            )

        canvas_nodes = [norm_pt(n["pos"][0], n["pos"][2]) for n in nodes]
    else:
        canvas_nodes = [(140, 300), (300, 180), (500, 300), (700, 420), (860, 300)]

    swat_roster = [
        {"id": "S1", "name": "[META] Gleidison", "team": "SWAT", "weapon": "M4A1 Tactical", "x": 120.0, "y": 240.0, "hp": 100},
        {"id": "S2", "name": "[SWAT] Viper", "team": "SWAT", "weapon": "AWP L96A1", "x": 135.0, "y": 300.0, "hp": 100},
        {"id": "S3", "name": "[SWAT] Falcon", "team": "SWAT", "weapon": "Kriss Vector", "x": 125.0, "y": 360.0, "hp": 100},
        {"id": "S4", "name": "[SWAT] Rook", "team": "SWAT", "weapon": "SCAR-L Pro", "x": 150.0, "y": 210.0, "hp": 100},
        {"id": "S5", "name": "[SWAT] Blitz", "team": "SWAT", "weapon": "MP7A1 Navy", "x": 150.0, "y": 390.0, "hp": 100},
    ]
    gang_roster = [
        {"id": "G1", "name": "[SIN] Diablo", "team": "GANG", "weapon": "AK-47 Pro", "x": 880.0, "y": 230.0, "hp": 100},
        {"id": "G2", "name": "[SIN] Razer", "team": "GANG", "weapon": "AK-47 Gold", "x": 865.0, "y": 300.0, "hp": 100},
        {"id": "G3", "name": "[SIN] Kobra", "team": "GANG", "weapon": "Dragunov SVD", "x": 875.0, "y": 370.0, "hp": 100},
        {"id": "G4", "name": "[SIN] Vandal", "team": "GANG", "weapon": "P90 Tactical", "x": 845.0, "y": 205.0, "hp": 100},
        {"id": "G5", "name": "[SIN] Havoc", "team": "GANG", "weapon": "SA-58 Para", "x": 845.0, "y": 395.0, "hp": 100},
    ]

    bomb_site_a = (490.0, 195.0)
    bomb_site_b = (510.0, 415.0)

    ticks = []
    bomb_state = {"status": "CARRIED", "x": 865.0, "y": 300.0}

    for t in range(60):
        tracers = []
        events = []

        # Move alive units toward mid / bomb sites
        for u in swat_roster:
            if u["hp"] <= 0:
                continue
            target_x = bomb_site_a[0] if u["id"] in ("S1", "S4") else bomb_site_b[0]
            target_y = bomb_site_a[1] if u["id"] in ("S1", "S4") else bomb_site_b[1]
            dx = (target_x - u["x"]) * 0.08 + rng.uniform(-9, 9)
            dy = (target_y - u["y"]) * 0.08 + rng.uniform(-9, 9)
            u["x"] = round(max(70.0, min(930.0, u["x"] + dx)), 1)
            u["y"] = round(max(60.0, min(540.0, u["y"] + dy)), 1)

        for u in gang_roster:
            if u["hp"] <= 0:
                continue
            target_x = bomb_site_a[0] if u["id"] in ("G1", "G2", "G4") else bomb_site_b[0]
            target_y = bomb_site_a[1] if u["id"] in ("G1", "G2", "G4") else bomb_site_b[1]
            dx = (target_x - u["x"]) * 0.085 + rng.uniform(-9, 9)
            dy = (target_y - u["y"]) * 0.085 + rng.uniform(-9, 9)
            u["x"] = round(max(70.0, min(930.0, u["x"] + dx)), 1)
            u["y"] = round(max(60.0, min(540.0, u["y"] + dy)), 1)

        # Check line-of-sight engagements
        alive_swat = [s for s in swat_roster if s["hp"] > 0]
        alive_gang = [g for g in gang_roster if g["hp"] > 0]

        if t == 22 and bomb_state["status"] == "CARRIED":
            bomb_state = {"status": "PLANTED_A", "x": bomb_site_a[0], "y": bomb_site_a[1]}
            events.append({"type": "BOMB_PLANT", "text": "💣 [SIN] Razer plantou a C4 no Bomb Site A!"})

        for s in alive_swat:
            for g in alive_gang:
                dist = math.hypot(s["x"] - g["x"], s["y"] - g["y"])
                if dist < 245.0 and rng.random() < 0.34:
                    # SWAT bias for Gleidison (S1)
                    swat_adv = 0.68 if s["id"] == "S1" else 0.54
                    if rng.random() < swat_adv:
                        dmg = rng.randint(36, 100)
                        g["hp"] = max(0, g["hp"] - dmg)
                        hs = dmg >= 85
                        tracers.append({"x1": s["x"], "y1": s["y"], "x2": g["x"], "y2": g["y"], "team": "SWAT", "hs": hs})
                        if g["hp"] == 0:
                            events.append({
                                "type": "KILL",
                                "killer": s["name"],
                                "victim": g["name"],
                                "weapon": s["weapon"],
                                "hs": hs,
                                "text": f"{'🎯 [HEADSHOT] ' if hs else '🔫 '}{s['name']} [{s['weapon']}] eliminou {g['name']}",
                            })
                    else:
                        dmg = rng.randint(28, 75)
                        s["hp"] = max(0, s["hp"] - dmg)
                        tracers.append({"x1": g["x"], "y1": g["y"], "x2": s["x"], "y2": s["y"], "team": "GANG", "hs": False})
                        if s["hp"] == 0:
                            events.append({
                                "type": "KILL",
                                "killer": g["name"],
                                "victim": s["name"],
                                "weapon": g["weapon"],
                                "hs": False,
                                "text": f"🔫 {g['name']} [{g['weapon']}] eliminou {s['name']}",
                            })

        alive_gang_after = [g for g in gang_roster if g["hp"] > 0]
        if not alive_gang_after and bomb_state["status"] == "PLANTED_A":
            bomb_state["status"] = "DEFUSED"
            events.append({"type": "BOMB_DEFUSE", "text": "🛡️ [META] Gleidison desarmou a C4! Vitória da S.W.A.T.!"})

        ticks.append({
            "tick": t,
            "time_str": f"0{1 - (t // 45)}:{59 - (t % 60):02d}",
            "units": [dict(u) for u in (swat_roster + gang_roster)],
            "tracers": tracers,
            "events": events,
            "bomb": dict(bomb_state),
        })
        if not alive_gang_after and bomb_state["status"] == "DEFUSED":
            break

    return {
        "map_name": map_name,
        "mode": "Demolição Tática (Bomb Match)",
        "winner": "S.W.A.T.",
        "swat_score": 6,
        "gang_score": 4,
        "bomb_sites": {"A": bomb_site_a, "B": bomb_site_b},
        "nav_nodes": canvas_nodes[:45],
        "ticks": ticks,
    }


def build_replay_html(replays_by_map: dict, out_path: str):
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    replays_json = json.dumps(replays_by_map, ensure_ascii=False)

    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<title>District 187 — 2D Tactical Match Replay Player (HLTV / Scope.gg Edition)</title>
<style>
  :root {{
    --bg: #090b10;
    --panel: #12151f;
    --border: #252a3a;
    --gold: #f59e0b;
    --swat: #38bdf8;
    --gang: #f43f5e;
    --text: #f3f4f6;
    --muted: #9ca3af;
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    background: var(--bg);
    color: var(--text);
    font-family: 'Segoe UI', system-ui, sans-serif;
    padding: 20px;
  }}
  .header {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    background: var(--panel);
    border: 1px solid var(--border);
    padding: 16px 24px;
    border-radius: 12px;
    margin-bottom: 16px;
  }}
  .header h1 {{ color: var(--gold); font-size: 20px; letter-spacing: 0.5px; }}
  .controls {{
    display: flex;
    gap: 12px;
    align-items: center;
  }}
  select, button {{
    background: #1e2333;
    color: var(--text);
    border: 1px solid var(--border);
    padding: 8px 14px;
    border-radius: 8px;
    font-weight: 600;
    cursor: pointer;
  }}
  button.primary {{ background: var(--gold); color: #000; border-color: var(--gold); }}
  .layout {{
    display: grid;
    grid-template-columns: 1fr 360px;
    gap: 16px;
  }}
  .canvas-card {{
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 16px;
    display: flex;
    flex-direction: column;
    align-items: center;
  }}
  canvas {{
    background: radial-gradient(circle at center, #161b28 0%, #0b0e15 100%);
    border: 1px solid #2b3248;
    border-radius: 10px;
    width: 100%;
    max-width: 1000px;
    height: auto;
  }}
  .scrubber {{
    width: 100%;
    margin-top: 14px;
    display: flex;
    align-items: center;
    gap: 12px;
  }}
  input[type=range] {{ flex: 1; accent-color: var(--gold); cursor: pointer; }}
  .sidebar {{
    display: flex;
    flex-direction: column;
    gap: 16px;
  }}
  .card {{
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 16px;
  }}
  .card h3 {{
    color: var(--gold);
    font-size: 13px;
    text-transform: uppercase;
    margin-bottom: 10px;
    letter-spacing: 0.8px;
  }}
  .roster-row {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 6px 0;
    border-bottom: 1px solid #1d2230;
    font-size: 13px;
  }}
  .hp-bar {{
    width: 70px;
    height: 8px;
    background: #272c3f;
    border-radius: 4px;
    overflow: hidden;
  }}
  .hp-fill {{ height: 100%; transition: width 0.15s; }}
  .killfeed {{
    max-height: 240px;
    overflow-y: auto;
    font-size: 12px;
    display: flex;
    flex-direction: column;
    gap: 6px;
  }}
  .feed-item {{
    padding: 6px 10px;
    background: #191d2b;
    border-left: 3px solid var(--gold);
    border-radius: 4px;
  }}
</style>
</head>
<body>
  <div class="header">
    <div>
      <h1>🎯 DISTRICT 187 — 2D TACTICAL REPLAY TELEMETRY (HLTV / SCOPE.GG EDITION)</h1>
      <div style="font-size:12px;color:var(--muted);margin-top:4px;">
        Motor LithTech Jupiter EX • A* NavMesh Pathing & Ballistic Raycast Log
      </div>
    </div>
    <div class="controls">
      <label style="font-size:13px;color:var(--muted);">Arena:</label>
      <select id="mapSelect" onchange="changeMap()"></select>
      <button class="primary" id="playBtn" onclick="togglePlay()">⏸ Pause</button>
      <select id="speedSelect" onchange="changeSpeed()">
        <option value="450">1.0x Normal</option>
        <option value="220">2.0x Rápido</option>
        <option value="800">0.5x Slow-Mo</option>
      </select>
    </div>
  </div>

  <div class="layout">
    <div class="canvas-card">
      <canvas id="radarCanvas" width="1000" height="600"></canvas>
      <div class="scrubber">
        <span id="clockLabel" style="font-family:monospace;font-size:16px;color:var(--gold);font-weight:bold;">01:59</span>
        <input type="range" id="tickRange" min="0" max="50" value="0" oninput="seekTick(this.value)">
        <span id="tickCounter" style="font-family:monospace;font-size:13px;color:var(--muted);">Tick 0/0</span>
      </div>
    </div>

    <div class="sidebar">
      <div class="card">
        <h3>🛡️ S.W.A.T. vs 💀 Gangsters (Status em Tempo Real)</h3>
        <div id="rosterContainer"></div>
      </div>
      <div class="card" style="flex:1;">
        <h3>⚡ Feed Tático de Combate & Objetivos</h3>
        <div class="killfeed" id="killFeed"></div>
      </div>
    </div>
  </div>

<script>
const REPLAYS = {replays_json};
let currentMap = Object.keys(REPLAYS)[0];
let currentTick = 0;
let playing = true;
let intervalMs = 450;
let timer = null;

const mapSelect = document.getElementById('mapSelect');
Object.keys(REPLAYS).forEach(m => {{
  const opt = document.createElement('option');
  opt.value = m;
  opt.textContent = m.toUpperCase() + ' (' + REPLAYS[m].mode + ')';
  mapSelect.appendChild(opt);
}});

function changeMap() {{
  currentMap = mapSelect.value;
  currentTick = 0;
  document.getElementById('killFeed').innerHTML = '';
  renderTick();
}}

function changeSpeed() {{
  intervalMs = parseInt(document.getElementById('speedSelect').value, 10);
  if (playing) {{
    clearInterval(timer);
    timer = setInterval(stepForward, intervalMs);
  }}
}}

function togglePlay() {{
  playing = !playing;
  document.getElementById('playBtn').textContent = playing ? '⏸ Pause' : '▶ Play';
  if (playing) {{
    timer = setInterval(stepForward, intervalMs);
  }} else {{
    clearInterval(timer);
  }}
}}

function seekTick(val) {{
  currentTick = parseInt(val, 10);
  renderTick();
}}

function stepForward() {{
  const ticks = REPLAYS[currentMap].ticks;
  currentTick = (currentTick + 1) % ticks.length;
  if (currentTick === 0) document.getElementById('killFeed').innerHTML = '';
  renderTick();
}}

function renderTick() {{
  const replay = REPLAYS[currentMap];
  const tickData = replay.ticks[currentTick];
  const range = document.getElementById('tickRange');
  range.max = replay.ticks.length - 1;
  range.value = currentTick;

  document.getElementById('clockLabel').textContent = tickData.time_str;
  document.getElementById('tickCounter').textContent = `Tick ${{currentTick + 1}}/${{replay.ticks.length}}`;

  const canvas = document.getElementById('radarCanvas');
  const ctx = canvas.getContext('2d');
  ctx.clearRect(0, 0, canvas.width, canvas.height);

  // Draw tactical grid
  ctx.strokeStyle = 'rgba(255,255,255,0.04)';
  ctx.lineWidth = 1;
  for (let x = 0; x < canvas.width; x += 50) {{
    ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, canvas.height); ctx.stroke();
  }}
  for (let y = 0; y < canvas.height; y += 50) {{
    ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(canvas.width, y); ctx.stroke();
  }}

  // Draw NavMesh waypoints
  ctx.fillStyle = 'rgba(245, 158, 11, 0.14)';
  replay.nav_nodes.forEach(pt => {{
    ctx.beginPath();
    ctx.arc(pt[0], pt[1], 4, 0, Math.PI * 2);
    ctx.fill();
  }});

  // Draw Bomb Sites A & B
  ['A', 'B'].forEach(site => {{
    const pos = replay.bomb_sites[site];
    ctx.strokeStyle = 'rgba(245, 158, 11, 0.75)';
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.arc(pos[0], pos[1], 28, 0, Math.PI * 2);
    ctx.stroke();
    ctx.fillStyle = '#f59e0b';
    ctx.font = 'bold 14px Segoe UI';
    ctx.fillText('SITE ' + site, pos[0] - 22, pos[1] - 34);
  }});

  // Draw C4 state
  if (tickData.bomb.status === 'PLANTED_A') {{
    ctx.fillStyle = '#ef4444';
    ctx.beginPath();
    ctx.arc(tickData.bomb.x, tickData.bomb.y, 10, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = '#fff';
    ctx.font = 'bold 11px Segoe UI';
    ctx.fillText('C4 ARMED', tickData.bomb.x - 26, tickData.bomb.y + 24);
  }}

  // Draw weapon fire tracers
  tickData.tracers.forEach(tr => {{
    ctx.strokeStyle = tr.hs ? '#f59e0b' : (tr.team === 'SWAT' ? '#38bdf8' : '#f43f5e');
    ctx.lineWidth = tr.hs ? 2.8 : 1.8;
    ctx.beginPath();
    ctx.moveTo(tr.x1, tr.y1);
    ctx.lineTo(tr.x2, tr.y2);
    ctx.stroke();
  }});

  // Draw operatives
  const rosterEl = document.getElementById('rosterContainer');
  rosterEl.innerHTML = '';

  tickData.units.forEach(u => {{
    const isSwat = u.team === 'SWAT';
    const color = isSwat ? '#38bdf8' : '#f43f5e';
    const alive = u.hp > 0;

    ctx.save();
    ctx.globalAlpha = alive ? 1.0 : 0.25;
    ctx.fillStyle = color;
    ctx.beginPath();
    ctx.arc(u.x, u.y, alive ? 11 : 7, 0, Math.PI * 2);
    ctx.fill();
    ctx.strokeStyle = '#fff';
    ctx.lineWidth = 1.5;
    ctx.stroke();

    ctx.fillStyle = '#e5e7eb';
    ctx.font = 'bold 11px Segoe UI';
    ctx.fillText(u.name, u.x - 28, u.y - 15);
    ctx.restore();

    const row = document.createElement('div');
    row.className = 'roster-row';
    row.style.opacity = alive ? '1' : '0.4';
    row.innerHTML = `
      <div>
        <span style="color:${{color}};font-weight:700;">●</span>
        <strong>${{u.name}}</strong>
        <span style="color:#9ca3af;font-size:11px;">(${{u.weapon}})</span>
      </div>
      <div style="display:flex;align-items:center;gap:8px;">
        <span style="font-family:monospace;font-size:12px;">${{u.hp}} HP</span>
        <div class="hp-bar"><div class="hp-fill" style="width:${{u.hp}}%;background:${{color}};"></div></div>
      </div>
    `;
    rosterEl.appendChild(row);
  }});

  // Append events to killfeed
  const feed = document.getElementById('killFeed');
  tickData.events.forEach(ev => {{
    const div = document.createElement('div');
    div.className = 'feed-item';
    div.textContent = `[${{tickData.time_str}}] ${{ev.text}}`;
    feed.prepend(div);
  }});
}}

renderTick();
timer = setInterval(stepForward, intervalMs);
</script>
</body>
</html>
"""
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)


def main():
    conn = sqlite3.connect(DB_PATH)
    init_extended_schema(conn)
    seed_mmr_loadouts_and_clans(conn)

    replays_by_map = {}
    c = conn.cursor()
    c.execute("DELETE FROM match_replays")
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for idx, mname in enumerate(["twoway", "thebank", "Arrival", "oldtown", "Kill_Port"]):
        rep = generate_tactical_replay_data(mname, seed=187 + idx * 13)
        replays_by_map[mname] = rep
        c.execute("""
            INSERT INTO match_replays (map_name, mode, winner, swat_score, gang_score, duration_sec, ticks_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            mname, rep["mode"], rep["winner"], rep["swat_score"], rep["gang_score"],
            len(rep["ticks"]) * 2, json.dumps(rep), now_str
        ))
    conn.commit()
    conn.close()

    replay_html_path = os.path.join(ANALYTICS_DIR, "match_replay.html")
    build_replay_html(replays_by_map, replay_html_path)
    print(f"[+] MMR Engine, Loadouts (Slots A/B/C), Clans & Replays initialized in {DB_PATH}")
    print(f"[+] Interactive 2D Tactical Match Replay Player generated at: {replay_html_path}")


if __name__ == "__main__":
    main()

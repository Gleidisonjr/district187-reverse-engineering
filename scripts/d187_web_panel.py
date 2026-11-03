#!/usr/bin/env python3
"""
District 187: Sin Streets - Web Control Panel & Administration Dashboard
Lightweight zero-dependency web interface providing:
  - Real-time engine & server status monitoring.
  - Weapon Arsenal & VIP Loadout editor backed by s2rebirth.db.
  - LithTech Competitive CVar configuration (FPS uncap, FOV, graphic presets).
  - 1-Click Game & Emulator launchers.
"""

import os
import sys
import json
import sqlite3
import subprocess
import socket
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

# Ensure UTF-8 output
sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TARGET_DIR = os.path.join(BASE_DIR, "targets", "district-187")
CLIENT_DIR = os.path.join(TARGET_DIR, "client-rebirth")
DB_PATH = os.path.join(TARGET_DIR, "data", "s2rebirth.db")
CFG_PATH = os.path.join(CLIENT_DIR, "autoexec.cfg")

def check_port_open(host="127.0.0.1", port=12000, timeout=0.5):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        result = s.connect_ex((host, port))
        s.close()
        return result == 0
    except:
        return False

def get_process_status(name="TheRaw.exe"):
    try:
        clean_name = name.replace(".exe", "")
        cmd = f'powershell -Command "Get-Process -Name \'{clean_name}\' -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Id"'
        out = subprocess.check_output(cmd, shell=True).decode().strip()
        if out:
            pids = [int(p) for p in out.splitlines() if p.strip().isdigit()]
            return {"running": True, "pids": pids}
    except:
        pass
    return {"running": False, "pids": []}

def get_weapons_list():
    if not os.path.exists(DB_PATH):
        return []
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT group_id, name, slot, class, damage, fire_delay, recoil FROM weapons ORDER BY damage DESC")
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows

HTML_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>District 187 - Native Engine Control Panel</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <style>
    body { background-color: #0b0f19; color: #f1f5f9; font-family: ui-sans-serif, system-ui, sans-serif; }
    .glass-card { background: rgba(17, 24, 39, 0.85); backdrop-filter: blur(12px); border: 1px solid rgba(55, 65, 81, 0.6); }
  </style>
</head>
<body class="p-6">
  <div class="max-w-7xl mx-auto space-y-6">
    <!-- Header -->
    <header class="glass-card rounded-2xl p-6 flex justify-between items-center shadow-2xl">
      <div class="flex items-center gap-4">
        <div class="w-12 h-12 rounded-xl bg-gradient-to-tr from-blue-600 to-indigo-500 flex items-center justify-center font-black text-xl shadow-lg shadow-blue-500/30">
          D187
        </div>
        <div>
          <h1 class="text-2xl font-black tracking-tight text-white flex items-center gap-2">
            District 187: Sin Streets
            <span class="text-xs px-2.5 py-0.5 rounded-full bg-blue-500/20 text-blue-400 border border-blue-500/30 font-semibold">Native Engine Hub</span>
          </h1>
          <p class="text-xs text-slate-400 mt-0.5">LithTech Jupiter EX v113 &bull; Server Emulation &bull; Real-time Telemetry</p>
        </div>
      </div>
      <div class="flex items-center gap-3">
        <button onclick="launchClient()" class="px-5 py-2.5 bg-gradient-to-r from-emerald-500 to-teal-600 hover:from-emerald-600 hover:to-teal-700 font-bold text-sm text-white rounded-xl shadow-lg shadow-emerald-500/25 transition flex items-center gap-2">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z"/><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
          Launch Native Client
        </button>
      </div>
    </header>

    <!-- System Status Grid -->
    <div class="grid grid-cols-4 gap-4">
      <div class="glass-card rounded-xl p-4">
        <span class="text-xs font-semibold text-slate-400 uppercase tracking-wider">Emulator Status (Port 12000)</span>
        <div class="flex items-center gap-2.5 mt-2">
          <span id="port-dot" class="w-3.5 h-3.5 rounded-full bg-slate-600 animate-pulse"></span>
          <span id="port-text" class="text-lg font-bold text-white">Checking...</span>
        </div>
        <p class="text-xs text-slate-500 mt-1">TCP Hermit Stream Cipher</p>
      </div>

      <div class="glass-card rounded-xl p-4">
        <span class="text-xs font-semibold text-slate-400 uppercase tracking-wider">TheRaw.exe Process</span>
        <div class="flex items-center gap-2.5 mt-2">
          <span id="game-dot" class="w-3.5 h-3.5 rounded-full bg-slate-600"></span>
          <span id="game-text" class="text-lg font-bold text-white">Checking...</span>
        </div>
        <p class="text-xs text-slate-500 mt-1">LithTech Engine Process</p>
      </div>

      <div class="glass-card rounded-xl p-4">
        <span class="text-xs font-semibold text-slate-400 uppercase tracking-wider">Total Arsenal (SQLite)</span>
        <div class="flex items-center gap-2.5 mt-2">
          <span class="text-2xl font-black text-amber-400" id="weapon-count">185</span>
          <span class="text-xs bg-amber-500/20 text-amber-300 px-2 py-0.5 rounded border border-amber-500/30">VIP Loadout</span>
        </div>
        <p class="text-xs text-slate-500 mt-1">Combat stats & balance models</p>
      </div>

      <div class="glass-card rounded-xl p-4">
        <span class="text-xs font-semibold text-slate-400 uppercase tracking-wider">World Spawns (Arrival)</span>
        <div class="flex items-center gap-2.5 mt-2">
          <span class="text-2xl font-black text-cyan-400">32</span>
          <span class="text-xs bg-cyan-500/20 text-cyan-300 px-2 py-0.5 rounded border border-cyan-500/30">16v16 Slots</span>
        </div>
        <p class="text-xs text-slate-500 mt-1">Arrival.World00p v113</p>
      </div>
    </div>

    <!-- Quick Navigation Links -->
    <div class="grid grid-cols-2 gap-4">
      <a href="/map" target="_blank" class="glass-card hover:border-blue-500/50 p-4 rounded-xl flex items-center justify-between group transition">
        <div class="flex items-center gap-3">
          <div class="p-2.5 bg-blue-500/20 text-blue-400 rounded-lg group-hover:bg-blue-500 group-hover:text-white transition">
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7"/></svg>
          </div>
          <div>
            <h3 class="text-sm font-bold text-white group-hover:text-blue-400 transition">Interactive Tactical Radar (Arrival)</h3>
            <p class="text-xs text-slate-400">3D XZ Top-Down Minimap with 32 player spawns</p>
          </div>
        </div>
        <span class="text-xs text-slate-500 group-hover:text-blue-400 transition">&rarr;</span>
      </a>

      <a href="/analytics" target="_blank" class="glass-card hover:border-indigo-500/50 p-4 rounded-xl flex items-center justify-between group transition">
        <div class="flex items-center gap-3">
          <div class="p-2.5 bg-indigo-500/20 text-indigo-400 rounded-lg group-hover:bg-indigo-500 group-hover:text-white transition">
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"/></svg>
          </div>
          <div>
            <h3 class="text-sm font-bold text-white group-hover:text-indigo-400 transition">Weapon Analytics & Meta Dashboard</h3>
            <p class="text-xs text-slate-400">DPS, STK, TTK, Recoil distribution and XP curves</p>
          </div>
        </div>
        <span class="text-xs text-slate-500 group-hover:text-indigo-400 transition">&rarr;</span>
      </a>
    </div>

    <!-- Competitive CVar Tuning -->
    <div class="glass-card rounded-2xl p-6">
      <h2 class="text-lg font-bold text-white mb-4 flex items-center gap-2">
        <svg class="w-5 h-5 text-amber-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4"/></svg>
        LithTech Engine Competitive Tuning (autoexec.cfg)
      </h2>
      <div class="grid grid-cols-3 gap-4">
        <div>
          <label class="block text-xs font-semibold text-slate-400 mb-1">Max FPS Cap</label>
          <select id="cfg-fps" class="w-full bg-slate-900 border border-slate-700 rounded-lg p-2.5 text-xs text-white">
            <option value="0">0 (Uncapped / Ultra High Hz)</option>
            <option value="144">144 FPS</option>
            <option value="240">240 FPS</option>
            <option value="360">360 FPS</option>
          </select>
        </div>
        <div>
          <label class="block text-xs font-semibold text-slate-400 mb-1">Field of View (FOV)</label>
          <select id="cfg-fov" class="w-full bg-slate-900 border border-slate-700 rounded-lg p-2.5 text-xs text-white">
            <option value="90">90 (Standard Competitive)</option>
            <option value="95">95 (Wide Angle)</option>
            <option value="100">100 (Ultra Wide Pro)</option>
            <option value="75">75 (Default)</option>
          </select>
        </div>
        <div>
          <label class="block text-xs font-semibold text-slate-400 mb-1">Texture Mip Offset (Ultra HD)</label>
          <select id="cfg-mip" class="w-full bg-slate-900 border border-slate-700 rounded-lg p-2.5 text-xs text-white">
            <option value="0">0 (Full 4K Uncompressed HD)</option>
            <option value="1">1 (Performance Mid)</option>
          </select>
        </div>
      </div>
      <div class="mt-4 flex justify-end">
        <button onclick="saveCvars()" class="px-4 py-2 bg-blue-600 hover:bg-blue-700 font-semibold text-xs text-white rounded-lg transition">
          Apply Engine CVars
        </button>
      </div>
    </div>
  </div>

  <script>
    async function updateStatus() {
      try {
        const res = await fetch('/api/status');
        const data = await res.json();
        
        const portDot = document.getElementById('port-dot');
        const portText = document.getElementById('port-text');
        if (data.port_12000_open) {
          portDot.className = 'w-3.5 h-3.5 rounded-full bg-emerald-500 shadow-lg shadow-emerald-500/50';
          portText.innerText = 'Listening (Online)';
          portText.className = 'text-lg font-bold text-emerald-400';
        } else {
          portDot.className = 'w-3.5 h-3.5 rounded-full bg-rose-500';
          portText.innerText = 'Offline';
          portText.className = 'text-lg font-bold text-rose-400';
        }

        const gameDot = document.getElementById('game-dot');
        const gameText = document.getElementById('game-text');
        if (data.game_running) {
          gameDot.className = 'w-3.5 h-3.5 rounded-full bg-emerald-500 shadow-lg shadow-emerald-500/50';
          gameText.innerText = `Active (PID ${data.game_pids.join(', ')})`;
          gameText.className = 'text-lg font-bold text-emerald-400';
        } else {
          gameDot.className = 'w-3.5 h-3.5 rounded-full bg-slate-600';
          gameText.innerText = 'Idle';
          gameText.className = 'text-lg font-bold text-slate-400';
        }
      } catch (e) {
        console.error(e);
      }
    }

    async function launchClient() {
      if (confirm('Start District 187 original client (TheRaw.exe)?')) {
        await fetch('/api/launch?target=client');
        alert('Launch signal sent to TheRaw.exe!');
        setTimeout(updateStatus, 1500);
      }
    }

    async function saveCvars() {
      const fps = document.getElementById('cfg-fps').value;
      const fov = document.getElementById('cfg-fov').value;
      const mip = document.getElementById('cfg-mip').value;
      const res = await fetch(`/api/save_cvars?fps=${fps}&fov=${fov}&mip=${mip}`);
      const data = await res.json();
      if (data.success) {
        alert('Engine configuration written to autoexec.cfg successfully!');
      }
    }

    setInterval(updateStatus, 2500);
    updateStatus();
  </script>
</body>
</html>
"""

class PanelHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        url = urlparse(self.path)
        path = url.path

        if path == "/":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_PAGE.encode("utf-8"))

        elif path == "/api/status":
            port_open = check_port_open(port=12000)
            game_proc = get_process_status("TheRaw.exe")
            payload = {
                "port_12000_open": port_open,
                "game_running": game_proc["running"],
                "game_pids": game_proc["pids"]
            }
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(payload).encode("utf-8"))

        elif path == "/api/save_cvars":
            params = parse_qs(url.query)
            fps = params.get("fps", ["0"])[0]
            fov = params.get("fov", ["90"])[0]
            mip = params.get("mip", ["0"])[0]

            cfg_content = f"""// District 187: Sin Streets - Competitive autoexec.cfg
MaxFPS {fps}
Fov {fov}
BindTexturesMipOffset {mip}
GraphicQualityLevel 3
ShowFrameRate 1
"""
            with open(CFG_PATH, "w", encoding="utf-8") as f:
                f.write(cfg_content)

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"success": True}).encode("utf-8"))

        elif path == "/api/launch":
            params = parse_qs(url.query)
            target = params.get("target", ["client"])[0]
            if target == "client":
                bat_path = os.path.join(CLIENT_DIR, "launch_offline_emulator.bat")
                if os.path.exists(bat_path):
                    subprocess.Popen(["cmd.exe", "/c", bat_path], cwd=CLIENT_DIR)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"launched": target}).encode("utf-8"))

        elif path == "/map":
            map_path = os.path.join(TARGET_DIR, "tactical_map_arrival.html")
            if os.path.exists(map_path):
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                with open(map_path, "rb") as f:
                    self.wfile.write(f.read())
            else:
                self.send_error(404)

        elif path == "/analytics":
            ana_path = os.path.join(TARGET_DIR, "weapon_analytics_dashboard.html")
            if os.path.exists(ana_path):
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                with open(ana_path, "rb") as f:
                    self.wfile.write(f.read())
            else:
                self.send_error(404)
        else:
            self.send_error(404)

def run_panel(port=8080):
    server = None
    for p in (port, 8081, 8082, 8888):
        try:
            server = HTTPServer(("127.0.0.1", p), PanelHandler)
            print(f"[+] District 187 Web Control Panel running at: http://127.0.0.1:{p}/")
            break
        except OSError:
            continue

    if server:
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\n[-] Web panel stopped.")

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    run_panel(port)

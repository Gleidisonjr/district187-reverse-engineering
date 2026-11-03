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

class ServiceManager:
    SERVICES = {
        "mock_server": {
            "name": "Hermit Mock Server",
            "cmd": [sys.executable, "-u", os.path.join(BASE_DIR, "scripts", "d187-mock-server.py")],
            "port": 12000,
            "desc": "TCP Hermit Handshake & Scaleform Lobby",
            "cwd": BASE_DIR
        },
        "dedicated_server": {
            "name": "LithTech Dedicated Gateway",
            "cmd": [sys.executable, "-u", os.path.join(BASE_DIR, "scripts", "d187_dedicated_gateway.py"), "--port", "27888"],
            "port": 27888,
            "desc": "Jupiter EX Combat UDP Gateway (27888)",
            "cwd": BASE_DIR
        },
        "apexguard": {
            "name": "ApexGuard Anti-Cheat Stub",
            "cmd": [sys.executable, "-u", os.path.join(BASE_DIR, "scripts", "apexguard_stub.py")],
            "port": None,
            "desc": "Shared Memory Heartbeat (Local\\ApexRing_)",
            "cwd": BASE_DIR
        },
        "sniffer": {
            "name": "Hermit MITM Packet Sniffer",
            "cmd": [sys.executable, "-u", os.path.join(BASE_DIR, "scripts", "d187_proxy_sniffer.py")],
            "port": None,
            "desc": "Decodes real-time client/server opcodes",
            "cwd": BASE_DIR
        }
    }
    
    _procs = {}

    @classmethod
    def start_service(cls, svc_id: str) -> bool:
        if svc_id not in cls.SERVICES:
            return False
        if cls.is_running(svc_id):
            return True
        info = cls.SERVICES[svc_id]
        try:
            p = subprocess.Popen(info["cmd"], cwd=info.get("cwd", BASE_DIR))
            cls._procs[svc_id] = p
            return True
        except Exception as e:
            print(f"[-] Failed to start {svc_id}: {e}")
            return False

    @classmethod
    def stop_service(cls, svc_id: str) -> bool:
        if svc_id in cls._procs:
            p = cls._procs[svc_id]
            if p.poll() is None:
                try:
                    p.terminate()
                    p.wait(timeout=1.0)
                except Exception:
                    p.kill()
            del cls._procs[svc_id]
            return True
        return False

    @classmethod
    def is_running(cls, svc_id: str) -> bool:
        if svc_id in cls._procs:
            p = cls._procs[svc_id]
            if p.poll() is None:
                return True
            else:
                del cls._procs[svc_id]
        port = cls.SERVICES.get(svc_id, {}).get("port")
        if port and check_port_open("127.0.0.1", port):
            return True
        return False

    @classmethod
    def get_status_all(cls):
        res = {}
        for svc_id, info in cls.SERVICES.items():
            running = cls.is_running(svc_id)
            pid = cls._procs[svc_id].pid if svc_id in cls._procs and cls._procs[svc_id].poll() is None else None
            port_open = check_port_open("127.0.0.1", info["port"]) if info.get("port") else False
            res[svc_id] = {
                "name": info["name"],
                "desc": info["desc"],
                "running": running or port_open,
                "pid": pid,
                "port": info.get("port"),
                "port_open": port_open
            }
        return res

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

    <!-- Microservices Supervisor & Lifecycle Manager -->
    <div class="glass-card rounded-2xl p-6">
      <div class="flex justify-between items-center mb-4">
        <div>
          <h2 class="text-lg font-bold text-white flex items-center gap-2">
            <svg class="w-5 h-5 text-indigo-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"/></svg>
            Microservices Supervisor & Lifecycle Manager
          </h2>
          <p class="text-xs text-slate-400">Isolated daemons running on loopback (127.0.0.1) without port collisions</p>
        </div>
        <div class="flex gap-2">
          <button onclick="controlAllServices('start')" class="px-3.5 py-1.5 bg-emerald-600/30 hover:bg-emerald-600/50 text-emerald-300 border border-emerald-500/40 rounded-lg text-xs font-semibold transition">
            Start All
          </button>
          <button onclick="controlAllServices('stop')" class="px-3.5 py-1.5 bg-rose-600/30 hover:bg-rose-600/50 text-rose-300 border border-rose-500/40 rounded-lg text-xs font-semibold transition">
            Stop All
          </button>
        </div>
      </div>

      <div class="grid grid-cols-4 gap-4" id="services-grid">
        <div class="col-span-4 text-center py-4 text-slate-500 text-xs">Loading services status...</div>
      </div>
    </div>

    <!-- Maps & Tactical NavMesh Hub -->
    <div class="glass-card rounded-2xl p-6">
      <h2 class="text-lg font-bold text-white mb-4 flex items-center justify-between">
        <span class="flex items-center gap-2">
          <svg class="w-5 h-5 text-cyan-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7"/></svg>
          LithTech Jupiter EX Tactical Radar & NavMesh Hub (25 Maps)
        </span>
        <span class="text-xs bg-cyan-500/20 text-cyan-300 px-3 py-1 rounded-full border border-cyan-500/30">Extracted from Game.ResDt</span>
      </h2>
      <div class="grid grid-cols-3 gap-4 items-end">
        <div class="col-span-1">
          <label class="block text-xs font-semibold text-slate-400 mb-1">Select Map</label>
          <select id="selected-map" class="w-full bg-slate-900 border border-slate-700 rounded-lg p-2.5 text-xs text-white">
            <option value="twoway">TwoWay (Demolition - Bomb A/B)</option>
            <option value="thebank">TheBank (Heist - Robbery)</option>
            <option value="10025_Heaven">10025 Heaven (Demolition)</option>
            <option value="Arrival">Arrival (16v16 TDM)</option>
            <option value="ghostcity">GhostCity (Demolition)</option>
            <option value="lostland">LostLand (Demolition)</option>
            <option value="10034_TheMetro">10034 TheMetro (TDM)</option>
            <option value="oldtown">OldTown (TDM)</option>
            <option value="10016_underworld">10016 UnderWorld (TDM)</option>
            <option value="10023_GrandBazar">10023 GrandBazar (TDM)</option>
            <option value="10029_DummyHouse">10029 DummyHouse (TDM)</option>
            <option value="10031_Hospital">10031 Hospital (TDM)</option>
            <option value="huntinghill">HuntingHill (TDM)</option>
            <option value="Ghost_Ship">Ghost Ship (TDM)</option>
          </select>
        </div>
        <div class="flex gap-3 col-span-2">
          <button onclick="openTacticalRadar()" class="flex-1 px-4 py-2.5 bg-blue-600 hover:bg-blue-700 font-semibold text-xs text-white rounded-lg transition flex items-center justify-center gap-2">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/></svg>
            Open 2D Tactical Vector Radar
          </button>
          <button onclick="openNavmeshRadar()" class="flex-1 px-4 py-2.5 bg-purple-600 hover:bg-purple-700 font-semibold text-xs text-white rounded-lg transition flex items-center justify-center gap-2">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/></svg>
            Open A* NavMesh Radar (Bots)
          </button>
        </div>
      </div>
    </div>

    <!-- Live Bot Combat Simulation & Telemetry -->
    <div class="glass-card rounded-2xl p-6">
      <div class="flex justify-between items-center mb-4">
        <div>
          <h2 class="text-lg font-bold text-white flex items-center gap-2">
            <svg class="w-5 h-5 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/></svg>
            Authoritative Bot Match Simulator & Match History
          </h2>
          <p class="text-xs text-slate-400">Simulates 8v8 tactical combat using real SQLite stats & authentic spawns</p>
        </div>
        <button id="btn-sim" onclick="runSimulation()" class="px-5 py-2 bg-gradient-to-r from-emerald-500 to-teal-600 hover:from-emerald-600 hover:to-teal-700 font-bold text-xs text-white rounded-xl shadow-lg shadow-emerald-500/25 transition">
          Simulate 8v8 Match
        </button>
      </div>

      <div id="sim-result" class="hidden mb-4 p-4 rounded-xl bg-slate-900 border border-emerald-500/40 text-xs"></div>

      <div class="overflow-x-auto">
        <table class="w-full text-left text-xs">
          <thead class="text-slate-400 border-b border-slate-700">
            <tr>
              <th class="py-2.5">Time</th>
              <th>Map</th>
              <th>Winner</th>
              <th>Score</th>
              <th>MVP</th>
              <th>Total Kills</th>
            </tr>
          </thead>
          <tbody id="matches-body" class="divide-y divide-slate-800 text-slate-200">
            <tr><td colspan="6" class="py-3 text-center text-slate-500">Loading match history...</td></tr>
          </tbody>
        </table>
      </div>
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

    function openTacticalRadar() {
      const map = document.getElementById('selected-map').value;
      window.open(`/maps/${map}_tactical.html`, '_blank');
    }

    function openNavmeshRadar() {
      const map = document.getElementById('selected-map').value;
      window.open(`/navmeshes/${map}_navmesh.html`, '_blank');
    }

    async function loadMatches() {
      try {
        const res = await fetch('/api/matches');
        const matches = await res.json();
        const tbody = document.getElementById('matches-body');
        if (!matches || matches.length === 0) {
          tbody.innerHTML = '<tr><td colspan="6" class="py-3 text-center text-slate-500">No match records found in database.</td></tr>';
          return;
        }
        tbody.innerHTML = matches.map(m => `
          <tr class="hover:bg-slate-800/40">
            <td class="py-2.5 font-mono text-slate-400">${m.timestamp || '-'}</td>
            <td class="font-bold text-cyan-400">${m.map_name}</td>
            <td class="${m.winner.includes('SWAT') ? 'text-blue-400' : 'text-rose-400'} font-semibold">${m.winner}</td>
            <td class="font-mono">${m.swat_score} - ${m.gang_score}</td>
            <td class="text-amber-300">${m.mvp}</td>
            <td class="font-mono text-slate-300">${m.total_kills}</td>
          </tr>
        `).join('');
      } catch (e) {
        console.error(e);
      }
    }

    async function runSimulation() {
      const map = document.getElementById('selected-map').value;
      const btn = document.getElementById('btn-sim');
      const box = document.getElementById('sim-result');
      btn.disabled = true;
      btn.innerText = 'Simulating Combat...';
      try {
        const res = await fetch(`/api/simulate?map=${map}&rounds=3`);
        const data = await res.json();
        box.classList.remove('hidden');
        box.innerHTML = `
          <div class="flex justify-between items-center">
            <span class="font-bold text-emerald-400">Match Completed on ${data.map_name}</span>
            <span class="text-slate-400">Total Kills: ${data.total_kills}</span>
          </div>
          <div class="mt-2 text-sm">
            Winner: <strong class="${data.winner.includes('SWAT') ? 'text-blue-400' : 'text-rose-400'}">${data.winner}</strong> (${data.swat_score} x ${data.gang_score}) &bull; MVP: <strong class="text-amber-300">${data.mvp}</strong>
          </div>
        `;
        loadMatches();
      } catch (e) {
        alert('Simulation error: ' + e);
      } finally {
        btn.disabled = false;
        btn.innerText = 'Simulate 8v8 Match';
      }
    }

    async function loadServices() {
      try {
        const res = await fetch('/api/services');
        const services = await res.json();
        const grid = document.getElementById('services-grid');
        grid.innerHTML = Object.entries(services).map(([id, s]) => {
          const isRunning = s.running;
          const portStr = s.port ? `<span class="text-[11px] font-mono text-cyan-300">:${s.port}</span>` : '';
          return `
            <div class="glass-card rounded-xl p-3 border border-slate-800">
              <div class="flex justify-between items-start">
                <span class="text-xs font-bold text-white">${s.name}</span>
                <span class="w-2.5 h-2.5 rounded-full ${isRunning ? 'bg-emerald-400 shadow-md shadow-emerald-400/50' : 'bg-slate-600'}"></span>
              </div>
              <p class="text-[10px] text-slate-400 mt-1 truncate">${s.desc}</p>
              <div class="flex justify-between items-center mt-3 pt-2 border-t border-slate-800/80">
                <div class="text-[11px] text-slate-400">
                  ${portStr} ${s.pid ? `<span class="text-slate-500 font-mono">PID ${s.pid}</span>` : ''}
                </div>
                <div>
                  ${isRunning ? `
                    <button onclick="toggleService('${id}', 'stop')" class="px-2.5 py-1 bg-rose-500/20 hover:bg-rose-500 text-rose-300 hover:text-white rounded text-[11px] font-semibold transition">Stop</button>
                  ` : `
                    <button onclick="toggleService('${id}', 'start')" class="px-2.5 py-1 bg-emerald-500/20 hover:bg-emerald-500 text-emerald-300 hover:text-white rounded text-[11px] font-semibold transition">Start</button>
                  `}
                </div>
              </div>
            </div>
          `;
        }).join('');
      } catch (e) {
        console.error(e);
      }
    }

    async function toggleService(svcId, action) {
      await fetch(`/api/service/${action}?name=${svcId}`);
      setTimeout(loadServices, 500);
    }

    async function controlAllServices(action) {
      await fetch(`/api/service/${action}_all`);
      setTimeout(loadServices, 1000);
    }

    setInterval(() => { updateStatus(); loadServices(); }, 2500);
    updateStatus();
    loadServices();
    loadMatches();
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

        elif path == "/api/services":
            status_data = ServiceManager.get_status_all()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(status_data).encode("utf-8"))

        elif path.startswith("/api/service/"):
            action = path.replace("/api/service/", "")
            params = parse_qs(url.query)
            svc_name = params.get("name", [""])[0]

            success = False
            if action == "start":
                success = ServiceManager.start_service(svc_name)
            elif action == "stop":
                success = ServiceManager.stop_service(svc_name)
            elif action == "start_all":
                for s_id in ServiceManager.SERVICES:
                    ServiceManager.start_service(s_id)
                success = True
            elif action == "stop_all":
                for s_id in ServiceManager.SERVICES:
                    ServiceManager.stop_service(s_id)
                success = True

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"success": success, "action": action, "service": svc_name}).encode("utf-8"))

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
                bat_path = os.path.join(BASE_DIR, "launch_game.bat")
                if os.path.exists(bat_path):
                    subprocess.Popen(["cmd.exe", "/c", bat_path], cwd=BASE_DIR)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"launched": target}).encode("utf-8"))

        elif path.startswith("/analytics/heatmap/"):
            map_name = os.path.basename(path)
            heat_file = f"{map_name}_combat_heatmap.html"
            full_path = os.path.join(TARGET_DIR, "analytics", heat_file)
            if os.path.exists(full_path):
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                with open(full_path, "rb") as f:
                    self.wfile.write(f.read())
            else:
                self.send_error(404)

        elif path.startswith("/maps/"):
            map_file = os.path.basename(path)
            full_path = os.path.join(TARGET_DIR, "maps", map_file)
            if os.path.exists(full_path):
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                with open(full_path, "rb") as f:
                    self.wfile.write(f.read())
            else:
                self.send_error(404)

        elif path.startswith("/navmeshes/"):
            nav_file = os.path.basename(path)
            full_path = os.path.join(TARGET_DIR, "navmeshes", nav_file)
            if os.path.exists(full_path):
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                with open(full_path, "rb") as f:
                    self.wfile.write(f.read())
            else:
                self.send_error(404)

        elif path == "/api/matches":
            matches = []
            if os.path.exists(DB_PATH):
                try:
                    conn = sqlite3.connect(DB_PATH)
                    conn.row_factory = sqlite3.Row
                    c = conn.cursor()
                    c.execute("SELECT * FROM match_history ORDER BY id DESC LIMIT 10")
                    matches = [dict(r) for r in c.fetchall()]
                    conn.close()
                except:
                    pass
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(matches).encode("utf-8"))

        elif path == "/api/simulate":
            params = parse_qs(url.query)
            sim_map = params.get("map", ["twoway"])[0]
            rounds = int(params.get("rounds", ["3"])[0])
            try:
                from scripts.d187_match_simulator import run_match
                res = run_match(map_name=sim_map, rounds_to_win=rounds, team_size=8)
            except Exception as e:
                res = {"error": str(e), "winner": "Error", "swat_score": 0, "gang_score": 0, "mvp": "None", "total_kills": 0, "map_name": sim_map}
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(res).encode("utf-8"))

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

def run_panel(port=8081):
    server = None
    for p in (port, 8082, 8888, 8080):
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
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8081
    run_panel(port)

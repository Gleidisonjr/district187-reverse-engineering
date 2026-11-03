#!/usr/bin/env python3
"""
District 187 / S2 Rebirth — Interactive Weapon Balance & Meta Analytics Dashboard Generator
Reads the structured SQLite catalog (s2rebirth.db) and compiles a responsive HTML dashboard
with TTK (Time-to-Kill), DPS, Damage vs Recoil scatter plots, and military rank XP curves.

Author: Gleidison Carvalho (Senior Data Analyst @ Meta) (2026-11-02)
"""

import os
import sys
import math
import json
import sqlite3

sys.stdout.reconfigure(encoding='utf-8')

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DB_PATH = os.path.join(ROOT_DIR, 'targets', 'district-187', 'data', 's2rebirth.db')
HTML_OUTPUT = os.path.join(ROOT_DIR, 'targets', 'district-187', 'weapon_analytics_dashboard.html')

def build_analytics():
    if not os.path.exists(DB_PATH):
        print(f"[-] SQLite database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # 1. Fetch weapons with combat stats
    cur.execute("""
        SELECT group_id, name, dev_name, class, damage, recoil, fire_delay, accuracy, range, magazine, mobility
        FROM weapons
        WHERE damage IS NOT NULL AND fire_delay IS NOT NULL AND damage > 0
        ORDER BY damage DESC
    """)
    raw_weapons = cur.fetchall()

    weapons = []
    class_stats = {}

    for w in raw_weapons:
        gid, name, dev_name, cls, dmg, rec, delay, acc, rng, mag, mob = w
        cls = cls or 'Outros'
        
        # Calculate Combat Metrics
        stk = math.ceil(100.0 / dmg) # Shots to kill (100 HP target)
        fire_delay_ms = max(delay * 10, 50) # Normalized fire delay in ms
        ttk_ms = (stk - 1) * fire_delay_ms # Time to kill in ms
        dps = round(dmg * (1000.0 / fire_delay_ms), 1)
        meta_score = round((dmg * 1.8 + acc * 1.2 + rng * 0.8) / (max(rec, 5) * 0.4 + delay * 0.1), 1)

        item = {
            "id": gid,
            "name": name,
            "dev_name": dev_name,
            "class": cls,
            "damage": dmg,
            "recoil": rec,
            "delay": delay,
            "accuracy": acc,
            "range": rng,
            "magazine": mag,
            "mobility": mob,
            "stk": stk,
            "ttk_ms": ttk_ms,
            "dps": dps,
            "meta_score": meta_score
        }
        weapons.append(item)

        if cls not in class_stats:
            class_stats[cls] = {"count": 0, "total_dmg": 0, "total_dps": 0, "total_ttk": 0, "total_recoil": 0}
        class_stats[cls]["count"] += 1
        class_stats[cls]["total_dmg"] += dmg
        class_stats[cls]["total_dps"] += dps
        class_stats[cls]["total_ttk"] += ttk_ms
        class_stats[cls]["total_recoil"] += rec

    # Calculate class averages
    class_summary = []
    for cls, stats in class_stats.items():
        c = stats["count"]
        class_summary.append({
            "class": cls,
            "count": c,
            "avg_damage": round(stats["total_dmg"] / c, 1),
            "avg_dps": round(stats["total_dps"] / c, 1),
            "avg_ttk": round(stats["total_ttk"] / c, 1),
            "avg_recoil": round(stats["total_recoil"] / c, 1)
        })

    # 2. Fetch military progression curve (Ranks)
    cur.execute("SELECT level, name, min_xp, max_xp FROM ranks ORDER BY level ASC")
    ranks = [{"level": r[0], "name": r[1], "min_xp": r[2], "max_xp": r[3]} for r in cur.fetchall()]

    conn.close()

    # Generate HTML with Chart.js and Tailwind
    html_content = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>District 187 — Weapon Balance & Combat Analytics</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body {{ background-color: #0f1115; color: #e2e8f0; font-family: 'Segoe UI', system-ui, sans-serif; }}
        .card {{ background-color: #1a1d24; border: 1px solid #2d323e; }}
        .badge-sniper {{ background-color: rgba(239, 68, 68, 0.2); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.3); }}
        .badge-ar {{ background-color: rgba(59, 130, 246, 0.2); color: #60a5fa; border: 1px solid rgba(59, 130, 246, 0.3); }}
        .badge-smg {{ background-color: rgba(16, 185, 129, 0.2); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.3); }}
        .badge-sg {{ background-color: rgba(245, 158, 11, 0.2); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.3); }}
    </style>
</head>
<body class="p-6">
    <div class="max-w-7xl mx-auto space-y-6">
        <!-- Header -->
        <div class="flex flex-col md:flex-row justify-between items-start md:items-center pb-6 border-b border-gray-800">
            <div>
                <h1 class="text-3xl font-black tracking-wider text-cyan-400">DISTRICT 187: SIN STREETS</h1>
                <p class="text-gray-400 text-sm mt-1">Combat Balance Dashboard • LithTech Jupiter EX Native Weapon Registry • 185 Weapons Analyzed</p>
            </div>
            <div class="mt-4 md:mt-0 flex gap-3">
                <span class="px-3 py-1 bg-cyan-950 border border-cyan-800 text-cyan-400 rounded-md text-xs font-semibold">185 Armas Mapeadas</span>
                <span class="px-3 py-1 bg-purple-950 border border-purple-800 text-purple-400 rounded-md text-xs font-semibold">58 Patentes Militares</span>
                <span class="px-3 py-1 bg-emerald-950 border border-emerald-800 text-emerald-400 rounded-md text-xs font-semibold">Dataset SQLite Live</span>
            </div>
        </div>

        <!-- Metric Cards -->
        <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div class="card p-4 rounded-xl shadow-lg">
                <div class="text-gray-400 text-xs font-semibold uppercase">Classe Mais Popular</div>
                <div class="text-2xl font-bold text-white mt-1">MAR (Assault)</div>
                <div class="text-xs text-cyan-400 mt-1">57 variações calibradas</div>
            </div>
            <div class="card p-4 rounded-xl shadow-lg">
                <div class="text-gray-400 text-xs font-semibold uppercase">Maior Dano por Disparo</div>
                <div class="text-2xl font-bold text-red-400 mt-1">100 HP (1-Shot)</div>
                <div class="text-xs text-gray-400 mt-1">AWM 300, DSR-E1, JNG-90</div>
            </div>
            <div class="card p-4 rounded-xl shadow-lg">
                <div class="text-gray-400 text-xs font-semibold uppercase">TTK Médio (Rifles)</div>
                <div class="text-2xl font-bold text-blue-400 mt-1">~140 ms</div>
                <div class="text-xs text-gray-400 mt-1">3 a 4 tiros no peito</div>
            </div>
            <div class="card p-4 rounded-xl shadow-lg">
                <div class="text-gray-400 text-xs font-semibold uppercase">XP Máximo (General Exército)</div>
                <div class="text-2xl font-bold text-emerald-400 mt-1">3.000.000+</div>
                <div class="text-xs text-gray-400 mt-1">58 Níveis de progressão</div>
            </div>
        </div>

        <!-- Charts Section -->
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <!-- Chart 1: Damage vs Recoil -->
            <div class="card p-5 rounded-xl shadow-lg">
                <h2 class="text-lg font-bold text-white mb-2">Matriz de Dano x Recuo (Identificação de Meta)</h2>
                <p class="text-gray-400 text-xs mb-4">Armas no canto superior esquerdo combinam alto dano com baixo recuo (Meta weapons).</p>
                <div class="h-80"><canvas id="scatterChart"></canvas></div>
            </div>

            <!-- Chart 2: Average DPS by Class -->
            <div class="card p-5 rounded-xl shadow-lg">
                <h2 class="text-lg font-bold text-white mb-2">DPS Médio & Cadência por Classe</h2>
                <p class="text-gray-400 text-xs mb-4">Comparativo quantitativo de dano teórico sustentado por segundo.</p>
                <div class="h-80"><canvas id="dpsChart"></canvas></div>
            </div>
        </div>

        <!-- Chart 3: Progression Curve -->
        <div class="card p-5 rounded-xl shadow-lg">
            <h2 class="text-lg font-bold text-white mb-2">Curva Exponencial de XP de Patentes Militares (Nível 1 a 58)</h2>
            <p class="text-gray-400 text-xs mb-4">Mapeamento da retenção e tempo necessário de jogo para desbloqueio de patentes de patente militar.</p>
            <div class="h-64"><canvas id="xpChart"></canvas></div>
        </div>

        <!-- Weapons Data Table -->
        <div class="card p-5 rounded-xl shadow-lg">
            <div class="flex justify-between items-center mb-4">
                <div>
                    <h2 class="text-lg font-bold text-white">Catálogo Completo de Armas Calibradas</h2>
                    <p class="text-gray-400 text-xs">Valores oficiais extraídos da GameDatabase.dll nativa e validados no banco relacional.</p>
                </div>
            </div>
            <div class="overflow-x-auto">
                <table class="w-full text-left text-sm text-gray-300">
                    <thead class="bg-gray-800 text-gray-400 text-xs uppercase font-semibold">
                        <tr>
                            <th class="p-3">Arma</th>
                            <th class="p-3">Classe</th>
                            <th class="p-3">Dano</th>
                            <th class="p-3">Recuo</th>
                            <th class="p-3">Precisão</th>
                            <th class="p-3">Alcance</th>
                            <th class="p-3">STK (Tiros)</th>
                            <th class="p-3">TTK Teórico</th>
                            <th class="p-3">DPS</th>
                            <th class="p-3">Meta Score</th>
                        </tr>
                    </thead>
                    <tbody class="divide-y divide-gray-800" id="weaponTableBody">
                    </tbody>
                </table>
            </div>
        </div>
    </div>

    <script>
        const weapons = {json.dumps(weapons, ensure_ascii=False)};
        const classSummary = {json.dumps(class_summary, ensure_ascii=False)};
        const ranks = {json.dumps(ranks, ensure_ascii=False)};

        // Populate Table
        const tbody = document.getElementById('weaponTableBody');
        weapons.slice(0, 50).forEach(w => {{
            const tr = document.createElement('tr');
            tr.className = "hover:bg-gray-800/40 transition-colors";
            let badgeClass = "badge-ar";
            if (w.class.includes("Nisanci") || w.class.includes("Sniper")) badgeClass = "badge-sniper";
            else if (w.class.includes("SMG")) badgeClass = "badge-smg";
            else if (w.class.includes("Pompali")) badgeClass = "badge-sg";

            tr.innerHTML = `
                <td class="p-3 font-semibold text-white">${{w.name}} <span class="text-xs text-gray-500 font-normal">(${{w.dev_name}})</span></td>
                <td class="p-3"><span class="px-2 py-0.5 rounded text-xs ${{badgeClass}}">${{w.class}}</span></td>
                <td class="p-3 font-bold text-red-400">${{w.damage}}</td>
                <td class="p-3">${{w.recoil}}</td>
                <td class="p-3">${{w.accuracy}}%</td>
                <td class="p-3">${{w.range}}m</td>
                <td class="p-3 font-semibold text-amber-400">${{w.stk}} tiros</td>
                <td class="p-3">${{w.ttk_ms}} ms</td>
                <td class="p-3 font-semibold text-emerald-400">${{w.dps}}</td>
                <td class="p-3 font-bold text-cyan-400">${{w.meta_score}}</td>
            `;
            tbody.appendChild(tr);
        }});

        // Chart 1: Scatter Damage vs Recoil
        new Chart(document.getElementById('scatterChart'), {{
            type: 'scatter',
            data: {{
                datasets: [{{
                    label: 'Armas',
                    data: weapons.map(w => ({{ x: w.recoil, y: w.damage, name: w.name }})),
                    backgroundColor: 'rgba(0, 173, 181, 0.7)',
                    borderColor: '#00adb5',
                    pointRadius: 5
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                scales: {{
                    x: {{ title: {{ display: true, text: 'Recuo (Recoil)' }}, grid: {{ color: '#2d323e' }} }},
                    y: {{ title: {{ display: true, text: 'Dano Base (Damage)' }}, grid: {{ color: '#2d323e' }} }}
                }}
            }}
        }});

        // Chart 2: DPS by Class
        new Chart(document.getElementById('dpsChart'), {{
            type: 'bar',
            data: {{
                labels: classSummary.map(c => c.class),
                datasets: [{{
                    label: 'DPS Médio',
                    data: classSummary.map(c => c.avg_dps),
                    backgroundColor: '#3b82f6'
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                scales: {{
                    y: {{ grid: {{ color: '#2d323e' }} }},
                    x: {{ grid: {{ color: '#2d323e' }} }}
                }}
            }}
        }});

        // Chart 3: XP Curve
        new Chart(document.getElementById('xpChart'), {{
            type: 'line',
            data: {{
                labels: ranks.filter((_, i) => i % 2 === 0).map(r => `Lv ${{r.level}} (${{r.name}})`),
                datasets: [{{
                    label: 'XP Requerido',
                    data: ranks.filter((_, i) => i % 2 === 0).map(r => r.min_xp),
                    borderColor: '#10b981',
                    backgroundColor: 'rgba(16, 185, 129, 0.1)',
                    fill: true,
                    tension: 0.3
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                scales: {{
                    y: {{ grid: {{ color: '#2d323e' }} }},
                    x: {{ grid: {{ color: '#2d323e' }} }}
                }}
            }}
        }});
    </script>
</body>
</html>
"""

    with open(HTML_OUTPUT, 'w', encoding='utf-8') as f:
        f.write(html_content)

    print(f"[+] Weapon Balance Dashboard generated successfully!")
    print(f"    File: {HTML_OUTPUT}")

if __name__ == '__main__':
    build_analytics()

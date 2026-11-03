#!/usr/bin/env python3
"""
District 187: Sin Streets - Standalone Web Portal
FastAPI + SQLite + Tailwind CSS (Bilingual PT-BR / EN)

Provides:
- Account Management & Registration
- Interactive Weapon Armory (185 weapons with real stats)
- Player Profiles & Leaderboards (58 Ranks, K/D, XP)
- Dedicated Server Live Status Monitor
"""
import os
import socket
import sqlite3
import uvicorn
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse

app = FastAPI(title="District 187 Web Portal")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "targets", "district-187", "data", "s2rebirth.db")

def check_server_status(host="127.0.0.1", port=12000, timeout=0.5):
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except Exception:
        return False

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

@app.get("/api/status")
def api_status():
    online = check_server_status("127.0.0.1", 12000)
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT COUNT(1) FROM users")
    total_users = c.fetchone()[0]
    c.execute("SELECT COUNT(1) FROM weapons")
    total_weapons = c.fetchone()[0]
    conn.close()
    return {
        "server_name": "District 187 Private Dedicated Server",
        "online": online,
        "host": "127.0.0.1",
        "port": 12000,
        "protocol": "Hermit Jupiter EX",
        "active_map": "Arrival.World00p",
        "total_players": total_users,
        "total_weapons": total_weapons
    }

@app.get("/api/weapons")
def api_weapons(category: str = None):
    conn = get_db()
    c = conn.cursor()
    if category:
        c.execute("SELECT * FROM weapons WHERE slot = ? ORDER BY damage DESC", (category,))
    else:
        c.execute("SELECT * FROM weapons ORDER BY damage DESC")
    weapons = [dict(row) for row in c.fetchall()]
    conn.close()
    return {"weapons": weapons}

@app.get("/api/leaderboard")
def api_leaderboard():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT id, username, nickname, rank_level, exp, kills, deaths, headshots, wins, losses FROM users ORDER BY exp DESC, kills DESC")
    users = [dict(row) for row in c.fetchall()]
    conn.close()
    return {"leaderboard": users}

@app.post("/api/register")
def api_register(username: str = Form(...), password: str = Form(...), nickname: str = Form(...)):
    conn = get_db()
    c = conn.cursor()
    try:
        c.execute(
            "INSERT INTO users (username, password_hash, nickname, rank_level, exp, gold, cash, kills, deaths, headshots, wins, losses) "
            "VALUES (?, ?, ?, 1, 0, 100000, 50000, 0, 0, 0, 0, 0)",
            (username.strip().lower(), password, nickname.strip())
        )
        conn.commit()
        conn.close()
        return {"success": True, "message": "Conta criada com sucesso! Faça login dentro do jogo."}
    except sqlite3.IntegrityError:
        conn.close()
        return JSONResponse(status_code=400, content={"success": False, "message": "Nome de usuário já existe!"})

@app.get("/", response_class=HTMLResponse)
def index_page():
    online = check_server_status("127.0.0.1", 12000)
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM users ORDER BY exp DESC")
    users = [dict(r) for r in c.fetchall()]
    c.execute("SELECT * FROM weapons ORDER BY damage DESC LIMIT 16")
    featured_weapons = [dict(r) for r in c.fetchall()]
    c.execute("SELECT * FROM maps LIMIT 12")
    maps = [dict(r) for r in c.fetchall()]
    conn.close()

    status_badge = '<span class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30"><span class="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span> ONLINE</span>' if online else '<span class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-rose-500/20 text-rose-400 border border-rose-500/30"><span class="w-2 h-2 rounded-full bg-rose-400"></span> OFFLINE</span>'

    html = f"""<!DOCTYPE html>
<html lang="pt-BR" class="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>District 187: Sin Streets - Portal do Operativo</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script>
        tailwind.config = {{
            darkMode: 'class',
            theme: {{
                extend: {{
                    colors: {{
                        gold: {{
                            400: '#F59E0B',
                            500: '#D97706',
                            600: '#B45309',
                        }},
                        dark: {{
                            800: '#18181B',
                            900: '#0F0F12',
                            950: '#09090B',
                        }}
                    }}
                }}
            }}
        }}
    </script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Rajdhani:wght@500;600;700&family=Inter:wght@400;500;600;700&display=swap');
        h1, h2, h3, .font-heading {{ font-family: 'Rajdhani', sans-serif; }}
        body {{ font-family: 'Inter', sans-serif; }}
        .glass-panel {{ background: rgba(24, 24, 27, 0.7); backdrop-filter: blur(12px); border: 1px solid rgba(255, 255, 255, 0.08); }}
        .gold-glow {{ text-shadow: 0 0 20px rgba(245, 158, 11, 0.5); }}
    </style>
</head>
<body class="bg-dark-950 text-zinc-100 min-h-screen flex flex-col">

    <!-- Top Navigation Bar -->
    <header class="sticky top-0 z-50 glass-panel border-b border-zinc-800">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-20 flex items-center justify-between">
            <div class="flex items-center gap-3">
                <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-amber-500 to-amber-700 flex items-center justify-center shadow-lg shadow-amber-500/20 font-heading font-bold text-xl text-black">
                    D187
                </div>
                <div>
                    <h1 class="text-xl font-bold tracking-wider text-amber-400 font-heading uppercase">District 187</h1>
                    <p class="text-xs text-zinc-400 font-medium tracking-widest uppercase">Sin Streets — Private Ecosystem</p>
                </div>
            </div>

            <nav class="hidden md:flex items-center gap-8 text-sm font-medium">
                <a href="#overview" class="text-zinc-300 hover:text-amber-400 transition" data-pt="Visão Geral" data-en="Overview">Visão Geral</a>
                <a href="#weapons" class="text-zinc-300 hover:text-amber-400 transition" data-pt="Arsenal VIP" data-en="VIP Armory">Arsenal VIP</a>
                <a href="#leaderboard" class="text-zinc-300 hover:text-amber-400 transition" data-pt="Classificação" data-en="Leaderboard">Classificação</a>
                <a href="#maps" class="text-zinc-300 hover:text-amber-400 transition" data-pt="Mapas Oficiais" data-en="Official Maps">Mapas Oficiais</a>
                <a href="#register" class="text-zinc-300 hover:text-amber-400 transition" data-pt="Criar Conta" data-en="Create Account">Criar Conta</a>
            </nav>

            <div class="flex items-center gap-4">
                <div class="flex items-center gap-2">
                    {status_badge}
                </div>
                <!-- Language Toggle Button -->
                <button onclick="toggleLanguage()" id="langBtn" class="px-3 py-1.5 rounded-lg border border-zinc-700 bg-zinc-900 text-xs font-bold text-amber-400 hover:bg-zinc-800 transition">
                    🇧🇷 PT-BR / EN
                </button>
            </div>
        </div>
    </header>

    <!-- Hero Section -->
    <section id="overview" class="relative overflow-hidden py-16 lg:py-24 border-b border-zinc-800 bg-gradient-to-b from-dark-900 via-dark-950 to-dark-950">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
            <div class="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
                <div>
                    <div class="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-amber-500/10 border border-amber-500/30 text-amber-400 text-xs font-semibold uppercase tracking-wider mb-4">
                        <i class="fa-solid fa-crosshairs"></i> <span data-pt="Servidor Dedicado Independente" data-en="Standalone Dedicated Server">Servidor Dedicado Independente</span>
                    </div>
                    <h2 class="text-4xl sm:text-6xl font-extrabold tracking-tight font-heading leading-tight mb-6">
                        <span data-pt="DOMINE AS RUAS DE" data-en="RULE THE STREETS OF">DOMINE AS RUAS DE</span><br>
                        <span class="text-transparent bg-clip-text bg-gradient-to-r from-amber-400 via-amber-200 to-amber-500 gold-glow">DISTRICT 187</span>
                    </h2>
                    <p class="text-base sm:text-lg text-zinc-400 mb-8 max-w-xl leading-relaxed" data-pt="Seu ecossistema privado completo com suporte a partidas Solo contra Bots de IA, partidas competitivas online e LAN com amigos, 58 patentes e arsenal com 185 armas desbloqueadas." data-en="Your complete private server ecosystem with Solo AI Bot matches, competitive online and LAN matches with friends, 58 military ranks, and 185 unlocked VIP weapons.">
                        Seu ecossistema privado completo com suporte a partidas Solo contra Bots de IA, partidas competitivas online e LAN com amigos, 58 patentes e arsenal com 185 armas desbloqueadas.
                    </p>
                    <div class="flex flex-wrap gap-4">
                        <a href="#register" class="px-6 py-3.5 rounded-xl bg-gradient-to-r from-amber-500 to-amber-600 hover:from-amber-400 hover:to-amber-500 text-black font-heading font-bold text-lg tracking-wider shadow-lg shadow-amber-500/25 transition transform hover:-translate-y-0.5 flex items-center gap-2">
                            <i class="fa-solid fa-user-plus"></i> <span data-pt="CRIAR CONTA GRÁTIS" data-en="CREATE FREE ACCOUNT">CRIAR CONTA GRÁTIS</span>
                        </a>
                        <a href="#weapons" class="px-6 py-3.5 rounded-xl glass-panel hover:bg-zinc-800 text-zinc-200 font-heading font-bold text-lg tracking-wider border border-zinc-700 transition flex items-center gap-2">
                            <i class="fa-solid fa-gun"></i> <span data-pt="VER ARSENAL (185)" data-en="VIEW ARMORY (185)">VER ARSENAL (185)</span>
                        </a>
                    </div>
                </div>

                <!-- Server Live Card -->
                <div class="glass-panel rounded-2xl p-6 sm:p-8 relative">
                    <div class="flex items-center justify-between mb-6 border-b border-zinc-800 pb-4">
                        <div class="flex items-center gap-3">
                            <i class="fa-solid fa-server text-amber-400 text-xl"></i>
                            <div>
                                <h3 class="font-heading font-bold text-lg text-zinc-200" data-pt="Status do Servidor Dedicado" data-en="Dedicated Server Status">Status do Servidor Dedicado</h3>
                                <p class="text-xs text-zinc-400">Hermit Protocol Jupiter EX (CRC32 Stream Cipher)</p>
                            </div>
                        </div>
                        {status_badge}
                    </div>

                    <div class="grid grid-cols-2 gap-4 mb-6">
                        <div class="bg-zinc-900/60 p-4 rounded-xl border border-zinc-800">
                            <span class="text-xs text-zinc-500 uppercase tracking-wider block mb-1" data-pt="Endereço de Conexão" data-en="Connection Address">Endereço de Conexão</span>
                            <span class="font-mono text-sm text-amber-400 font-bold">127.0.0.1:12000</span>
                        </div>
                        <div class="bg-zinc-900/60 p-4 rounded-xl border border-zinc-800">
                            <span class="text-xs text-zinc-500 uppercase tracking-wider block mb-1" data-pt="Mapa Atual" data-en="Active Battle Map">Mapa Atual</span>
                            <span class="font-heading text-sm text-zinc-200 font-bold">Arrival (8v8 Bots/LAN)</span>
                        </div>
                        <div class="bg-zinc-900/60 p-4 rounded-xl border border-zinc-800">
                            <span class="text-xs text-zinc-500 uppercase tracking-wider block mb-1" data-pt="Tick Rate & Engine" data-en="Tick Rate & Engine">Tick Rate & Engine</span>
                            <span class="font-mono text-sm text-emerald-400 font-bold">128 Tick / Ultra HD</span>
                        </div>
                        <div class="bg-zinc-900/60 p-4 rounded-xl border border-zinc-800">
                            <span class="text-xs text-zinc-500 uppercase tracking-wider block mb-1" data-pt="Armas Carregadas" data-en="Weapons Loaded">Armas Carregadas</span>
                            <span class="font-mono text-sm text-zinc-200 font-bold">185 Itens VIP</span>
                        </div>
                    </div>

                    <div class="bg-amber-500/10 border border-amber-500/20 p-4 rounded-xl flex items-center justify-between">
                        <div class="text-xs text-amber-300">
                            <strong data-pt="Como Jogar:" data-en="How to Play:">Como Jogar:</strong> <span data-pt="Abra o Launcher ou clique em launch_game.bat e utilize suas credenciais." data-en="Open the Launcher or click launch_game.bat and use your credentials.">Abra o Launcher ou clique em launch_game.bat e utilize suas credenciais.</span>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </section>

    <!-- Weapons Armory Section -->
    <section id="weapons" class="py-16 border-b border-zinc-800">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div class="flex flex-col sm:flex-row sm:items-end justify-between mb-10 gap-4">
                <div>
                    <h2 class="text-3xl font-extrabold font-heading text-amber-400" data-pt="Arsenal VIP Completo" data-en="Complete VIP Armory">Arsenal VIP Completo</h2>
                    <p class="text-sm text-zinc-400" data-pt="185 armas extraídas com dados balísticos autênticos de dano, precisão e cadência." data-en="185 extracted weapons with authentic ballistic damage, accuracy, and fire rate stats.">185 armas extraídas com dados balísticos autênticos de dano, precisão e cadência.</p>
                </div>
                <div class="flex items-center gap-2">
                    <span class="text-xs text-zinc-400 uppercase tracking-wider" data-pt="Exibindo 16 Armas de Elite" data-en="Showing 16 Elite Weapons">Exibindo 16 Armas de Elite</span>
                </div>
            </div>

            <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
                {''.join([f'''
                <div class="glass-panel rounded-xl p-5 hover:border-amber-500/50 transition group flex flex-col justify-between">
                    <div>
                        <div class="flex items-center justify-between text-xs text-zinc-400 mb-2">
                            <span class="px-2 py-0.5 rounded bg-zinc-800 text-amber-400 uppercase font-mono">{w['slot'] or 'PRIMARY'}</span>
                            <span class="font-mono text-zinc-500">ID: {w['group_id']}</span>
                        </div>
                        <h4 class="font-heading font-bold text-lg text-zinc-100 group-hover:text-amber-400 transition">{w['name']}</h4>
                        <p class="text-xs text-zinc-500 mb-4">{w['dev_name'] or 'Standard Edition'}</p>
                    </div>

                    <div class="space-y-2 text-xs border-t border-zinc-800/80 pt-3">
                        <div class="flex justify-between">
                            <span class="text-zinc-400">Dano:</span>
                            <span class="font-bold text-amber-400 font-mono">{w['damage']}</span>
                        </div>
                        <div class="w-full bg-zinc-800 h-1.5 rounded-full overflow-hidden">
                            <div class="bg-amber-400 h-full rounded-full" style="width: {min(100, int(w['damage'] or 0))}%"></div>
                        </div>

                        <div class="flex justify-between">
                            <span class="text-zinc-400">Precisão:</span>
                            <span class="font-bold text-zinc-200 font-mono">{w['accuracy']}</span>
                        </div>
                        <div class="w-full bg-zinc-800 h-1.5 rounded-full overflow-hidden">
                            <div class="bg-blue-400 h-full rounded-full" style="width: {min(100, int(w['accuracy'] or 0))}%"></div>
                        </div>

                        <div class="flex justify-between">
                            <span class="text-zinc-400">Pente / Balas:</span>
                            <span class="font-bold text-emerald-400 font-mono">{w['magazine']}</span>
                        </div>
                    </div>
                </div>
                ''' for w in featured_weapons])}
            </div>
        </div>
    </section>

    <!-- Leaderboard Section -->
    <section id="leaderboard" class="py-16 border-b border-zinc-800 bg-dark-900/50">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div class="mb-10">
                <h2 class="text-3xl font-extrabold font-heading text-amber-400" data-pt="Ranking dos Operativos" data-en="Operative Leaderboard">Ranking dos Operativos</h2>
                <p class="text-sm text-zinc-400" data-pt="Classificação em tempo real por Patente, Experiência e Eliminações." data-en="Real-time ranking by Rank Level, Experience, and Kills.">Classificação em tempo real por Patente, Experiência e Eliminações.</p>
            </div>

            <div class="glass-panel rounded-2xl overflow-hidden border border-zinc-800">
                <div class="overflow-x-auto">
                    <table class="w-full text-left text-sm text-zinc-300">
                        <thead class="bg-zinc-900 text-xs text-zinc-400 uppercase tracking-wider border-b border-zinc-800">
                            <tr>
                                <th class="px-6 py-4">#</th>
                                <th class="px-6 py-4" data-pt="Operativo" data-en="Operative">Operativo</th>
                                <th class="px-6 py-4" data-pt="Patente" data-en="Rank">Patente</th>
                                <th class="px-6 py-4" data-pt="EXP" data-en="EXP">EXP</th>
                                <th class="px-6 py-4" data-pt="Kills / Mortes" data-en="Kills / Deaths">Kills / Mortes</th>
                                <th class="px-6 py-4" data-pt="Headshots" data-en="Headshots">Headshots</th>
                                <th class="px-6 py-4" data-pt="K/D" data-en="K/D">K/D</th>
                            </tr>
                        </thead>
                        <tbody class="divide-y divide-zinc-800/60 font-mono">
                            {''.join([f'''
                            <tr class="hover:bg-zinc-800/40 transition">
                                <td class="px-6 py-4 font-bold text-amber-400">#{i+1}</td>
                                <td class="px-6 py-4 font-heading font-bold text-base text-zinc-100 flex items-center gap-2">
                                    <span class="w-2 h-2 rounded-full bg-emerald-400"></span> {u['nickname']}
                                </td>
                                <td class="px-6 py-4">
                                    <span class="px-2.5 py-1 rounded bg-amber-500/20 text-amber-400 font-sans font-bold text-xs border border-amber-500/30">
                                        Rank {u['rank_level']}
                                    </span>
                                </td>
                                <td class="px-6 py-4 text-zinc-200">{u['exp']:,}</td>
                                <td class="px-6 py-4 text-emerald-400 font-bold">{u['kills']} <span class="text-zinc-500">/</span> <span class="text-rose-400">{u['deaths']}</span></td>
                                <td class="px-6 py-4 text-amber-400">{u['headshots']}</td>
                                <td class="px-6 py-4 text-amber-300 font-bold">{round(u['kills'] / max(1, u['deaths']), 2)}</td>
                            </tr>
                            ''' for i, u in enumerate(users)])}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    </section>

    <!-- Maps Section -->
    <section id="maps" class="py-16 border-b border-zinc-800">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div class="mb-10">
                <h2 class="text-3xl font-extrabold font-heading text-amber-400" data-pt="Mapas & Modos de Combate" data-en="Maps & Combat Modes">Mapas & Modos de Combate</h2>
                <p class="text-sm text-zinc-400" data-pt="Mapas oficiais do jogo com suporte a Deathmatch, Bomb Defusal e Solo Bots." data-en="Official game maps supporting Deathmatch, Bomb Defusal, and Solo Bots.">Mapas oficiais do jogo com suporte a Deathmatch, Bomb Defusal e Solo Bots.</p>
            </div>

            <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
                {''.join([f'''
                <div class="glass-panel rounded-xl p-5 border border-zinc-800 flex items-center justify-between">
                    <div>
                        <span class="text-xs font-mono text-amber-400 uppercase tracking-wider block mb-1">{m['modes']}</span>
                        <h4 class="font-heading font-bold text-lg text-zinc-100">{m['dev_name']}</h4>
                        <p class="text-xs text-zinc-500">{m['name']}</p>
                    </div>
                    <div class="w-12 h-12 rounded-lg bg-zinc-900 border border-zinc-700 flex items-center justify-center text-zinc-400">
                        <i class="fa-solid fa-map-location-dot text-lg"></i>
                    </div>
                </div>
                ''' for m in maps])}
            </div>
        </div>
    </section>

    <!-- Register Account Section -->
    <section id="register" class="py-16 bg-gradient-to-b from-dark-900 to-dark-950">
        <div class="max-w-xl mx-auto px-4 sm:px-6 lg:px-8">
            <div class="glass-panel rounded-2xl p-8 border border-zinc-800 shadow-2xl">
                <div class="text-center mb-8">
                    <h2 class="text-3xl font-extrabold font-heading text-amber-400" data-pt="Cadastrar Novo Operativo" data-en="Register New Operative">Cadastrar Novo Operativo</h2>
                    <p class="text-sm text-zinc-400 mt-2" data-pt="Crie sua conta para jogar online com amigos ou solo contra bots." data-en="Create your account to play online with friends or solo against bots.">Crie sua conta para jogar online com amigos ou solo contra bots.</p>
                </div>

                <form id="regForm" onsubmit="handleRegister(event)" class="space-y-4">
                    <div>
                        <label class="block text-xs font-bold uppercase tracking-wider text-zinc-400 mb-1" data-pt="Nome de Usuário (Login)" data-en="Username (Login)">Nome de Usuário (Login)</label>
                        <input type="text" name="username" required class="w-full px-4 py-3 rounded-xl bg-zinc-900 border border-zinc-700 focus:border-amber-400 focus:outline-none text-zinc-100 font-mono text-sm" placeholder="ex: operative187">
                    </div>

                    <div>
                        <label class="block text-xs font-bold uppercase tracking-wider text-zinc-400 mb-1" data-pt="Nickname no Jogo" data-en="In-Game Nickname">Nickname no Jogo</label>
                        <input type="text" name="nickname" required class="w-full px-4 py-3 rounded-xl bg-zinc-900 border border-zinc-700 focus:border-amber-400 focus:outline-none text-zinc-100 font-sans text-sm" placeholder="ex: Cobra_Sniper">
                    </div>

                    <div>
                        <label class="block text-xs font-bold uppercase tracking-wider text-zinc-400 mb-1" data-pt="Senha" data-en="Password">Senha</label>
                        <input type="password" name="password" required class="w-full px-4 py-3 rounded-xl bg-zinc-900 border border-zinc-700 focus:border-amber-400 focus:outline-none text-zinc-100 text-sm" placeholder="••••••••">
                    </div>

                    <button type="submit" class="w-full py-3.5 rounded-xl bg-gradient-to-r from-amber-500 to-amber-600 hover:from-amber-400 hover:to-amber-500 text-black font-heading font-bold text-lg tracking-wider shadow-lg shadow-amber-500/25 transition mt-6">
                        <span data-pt="CRIAR CONTA & ENTRAR" data-en="CREATE ACCOUNT & ENTER">CRIAR CONTA & ENTRAR</span>
                    </button>
                    <div id="regMsg" class="text-center text-sm font-medium mt-3 hidden"></div>
                </form>
            </div>
        </div>
    </section>

    <!-- Footer -->
    <footer class="mt-auto py-8 border-t border-zinc-800 text-center text-xs text-zinc-500">
        <p>District 187: Sin Streets — Standalone Private Server Edition (2026)</p>
        <p class="mt-1">Built with LithTech Jupiter EX Hermit Protocol Emulator & FastAPI</p>
    </footer>

    <script>
        let currentLang = 'pt';
        function toggleLanguage() {{
            currentLang = currentLang === 'pt' ? 'en' : 'pt';
            document.querySelectorAll('[data-' + currentLang + ']').forEach(el => {{
                el.innerText = el.getAttribute('data-' + currentLang);
            }});
            document.getElementById('langBtn').innerText = currentLang === 'pt' ? '🇧🇷 PT-BR / EN' : '🇺🇸 EN / PT-BR';
        }}

        async function handleRegister(e) {{
            e.preventDefault();
            const form = document.getElementById('regForm');
            const data = new FormData(form);
            const msg = document.getElementById('regMsg');
            msg.className = 'text-center text-sm font-medium mt-3 block text-zinc-400';
            msg.innerText = currentLang === 'pt' ? 'Criando conta...' : 'Creating account...';

            try {{
                const res = await fetch('/api/register', {{ method: 'POST', body: data }});
                const json = await res.json();
                if (res.ok) {{
                    msg.className = 'text-center text-sm font-medium mt-3 block text-emerald-400';
                    msg.innerText = json.message;
                    form.reset();
                    setTimeout(() => window.location.reload(), 1500);
                }} else {{
                    msg.className = 'text-center text-sm font-medium mt-3 block text-rose-400';
                    msg.innerText = json.message;
                }}
            }} catch (err) {{
                msg.className = 'text-center text-sm font-medium mt-3 block text-rose-400';
                msg.innerText = 'Erro de conexão com o servidor web.';
            }}
        }}
    </script>
</body>
</html>
"""
    return HTMLResponse(content=html)

def main():
    print("=====================================================================")
    print("  District 187: Sin Streets — Web Portal Standalone")
    print("  Starting on http://0.0.0.0:8080")
    print("  Language: Bilingual (Português & English)")
    print("=====================================================================")
    uvicorn.run(app, host="0.0.0.0", port=8080, log_level="info")

if __name__ == "__main__":
    main()

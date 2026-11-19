#!/usr/bin/env python3
"""
District 187: Sin Streets - Official GUI Launcher (Standalone Edition)
Python Tkinter + Modern Dark/Amber Theme

Features:
- Solo AI Bot match launcher (Map, Difficulty, Team size)
- Online / LAN multiplayer launcher (Connect with friends)
- Live Dedicated Hermit Server status monitor & controls
- Graphic & Display presets (Ultra HD, 144+ FPS Uncapped)
- Direct link to Web Portal (Armory, Leaderboards, Registration)
"""
import os
import socket
import subprocess
import sys
import threading
import time
import webbrowser
import tkinter as tk
from tkinter import ttk, messagebox

# Resolve base paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
CLIENT_DIR = os.path.join(PROJECT_DIR, r"targets\district-187\client-rebirth")
WORLDS_DIR = os.path.join(CLIENT_DIR, "Game", "Worlds")
THE_RAW_EXE = os.path.join(CLIENT_DIR, "TheRaw.exe")
SERVER_HOST_EXE = os.path.join(PROJECT_DIR, r"targets\district-187\server_host\TheRawServer.exe")
SERVER_SCRIPT = os.path.join(SCRIPT_DIR, "d187-mock-server.py")
WEB_PORTAL_SCRIPT = os.path.join(SCRIPT_DIR, "d187_web_portal.py")
WEB_PANEL_SCRIPT = os.path.join(SCRIPT_DIR, "d187_web_panel.py")

try:
    from d187_qol_optimizer import apply_qol_profile, enforce_borderless_window
except Exception:
    apply_qol_profile = None
    enforce_borderless_window = None

_CURATED_MAPS = [
    ("Arrival (Recomendado)", "Arrival.World00p"),
    ("Two Way (Çifte Yol)", "twoway.World00p"),
    ("The Bank (Banka)", "thebank.World00p"),
    ("Old Town (Eski Şehir)", "oldtown.World00p"),
    ("Kill Port (Ölüm Limanı)", "Kill_Port.World00p"),
    ("Ghost Ship (Hayalet Gemi)", "Ghost_Ship.World00p"),
    ("Heaven (10025_Heaven)", "10025_Heaven.World00p"),
    ("Hospital (10031_Hospital)", "10031_Hospital.World00p"),
    ("Grand Bazar (10023_GrandBazar)", "10023_GrandBazar.World00p"),
]

MAPS = [
    (label, fname)
    for label, fname in _CURATED_MAPS
    if os.path.exists(os.path.join(WORLDS_DIR, fname))
    and os.path.getsize(os.path.join(WORLDS_DIR, fname)) > 100_000
] or [("Arrival (Recomendado)", "Arrival.World00p")]

class D187Launcher(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("District 187: Sin Streets — Launcher")
        self.geometry("780x640")
        self.resizable(False, False)
        self.configure(bg="#0c0d12")

        self.server_online = False
        self._closing = False
        self._child_procs = []
        self.setup_styles()
        self.build_ui()
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.start_status_checker()

    def setup_styles(self):
        self.style = ttk.Style(self)
        self.style.theme_use("clam")

        # Color palette
        self.c_bg = "#0c0d12"
        self.c_panel = "#161821"
        self.c_border = "#282a36"
        self.c_gold = "#F59E0B"
        self.c_gold_hover = "#D97706"
        self.c_text = "#F4F4F5"
        self.c_muted = "#A1A1AA"
        self.c_green = "#10B981"
        self.c_red = "#EF4444"

        # Frame styles
        self.style.configure("TFrame", background=self.c_bg)
        self.style.configure("Panel.TFrame", background=self.c_panel, relief="flat")
        self.style.configure("TLabel", background=self.c_panel, foreground=self.c_text, font=("Segoe UI", 10))
        self.style.configure("Header.TLabel", background=self.c_bg, foreground=self.c_gold, font=("Segoe UI", 18, "bold"))
        self.style.configure("Sub.TLabel", background=self.c_bg, foreground=self.c_muted, font=("Segoe UI", 9))
        self.style.configure("Badge.TLabel", font=("Segoe UI", 9, "bold"))

        # Combobox style
        self.style.configure("TCombobox", fieldbackground="#1f2230", background="#2a2d40", foreground="#ffffff")

    def build_ui(self):
        # Top Header Banner
        header_frame = tk.Frame(self, bg=self.c_bg, height=80)
        header_frame.pack(fill="x", padx=24, pady=(16, 8))

        title_lbl = tk.Label(header_frame, text="DISTRICT 187: SIN STREETS", font=("Segoe UI", 20, "bold"), fg=self.c_gold, bg=self.c_bg)
        title_lbl.pack(anchor="w")
        sub_lbl = tk.Label(header_frame, text="Dedicated Standalone Launcher & Solo/Online Combat Ecosystem", font=("Segoe UI", 10), fg=self.c_muted, bg=self.c_bg)
        sub_lbl.pack(anchor="w")

        # Status Bar Panel
        status_panel = tk.Frame(self, bg=self.c_panel, highlightbackground=self.c_border, highlightthickness=1)
        status_panel.pack(fill="x", padx=24, pady=8)

        status_left = tk.Frame(status_panel, bg=self.c_panel)
        status_left.pack(side="left", padx=16, pady=10)

        self.status_dot = tk.Label(status_left, text="●", font=("Segoe UI", 14), fg=self.c_muted, bg=self.c_panel)
        self.status_dot.pack(side="left", padx=(0, 6))

        self.status_text = tk.Label(status_left, text="Verificando Servidor Hermit (127.0.0.1:12000)...", font=("Segoe UI", 10, "bold"), fg=self.c_text, bg=self.c_panel)
        self.status_text.pack(side="left")

        status_right = tk.Frame(status_panel, bg=self.c_panel)
        status_right.pack(side="right", padx=16, pady=8)

        btn_server = tk.Button(status_right, text="Reiniciar Servidor", font=("Segoe UI", 9, "bold"), bg="#27272a", fg=self.c_gold, activebackground="#3f3f46", activeforeground="#ffffff", border=0, padx=12, pady=4, cursor="hand2", command=self.restart_server)
        btn_server.pack(side="left", padx=4)

        btn_portal = tk.Button(status_right, text="Abrir Web Portal", font=("Segoe UI", 9, "bold"), bg="#F59E0B", fg="#000000", activebackground="#D97706", activeforeground="#000000", border=0, padx=12, pady=4, cursor="hand2", command=self.open_portal)
        btn_portal.pack(side="left", padx=4)

        btn_panel = tk.Button(status_right, text="Painel Dev", font=("Segoe UI", 9, "bold"), bg="#1f2230", fg="#a78bfa", activebackground="#2a2d40", activeforeground="#ffffff", border=0, padx=10, pady=4, cursor="hand2", command=self.open_panel)
        btn_panel.pack(side="left", padx=4)

        btn_replay = tk.Button(status_right, text="🎬 Replay 2D", font=("Segoe UI", 9, "bold"), bg="#1f2230", fg="#38bdf8", activebackground="#2a2d40", activeforeground="#ffffff", border=0, padx=10, pady=4, cursor="hand2", command=self.open_replay)
        btn_replay.pack(side="left", padx=4)

        # Main Tabs / Modes Panel
        content_frame = tk.Frame(self, bg=self.c_bg)
        content_frame.pack(fill="both", expand=True, padx=24, pady=8)

        # Mode Selection Radio Buttons
        mode_select_frame = tk.Frame(content_frame, bg=self.c_bg)
        mode_select_frame.pack(fill="x", pady=(0, 8))

        self.mode_var = tk.StringVar(value="solo")
        rb_solo = tk.Radiobutton(mode_select_frame, text="🤖 Jogar Solo (Contra Bots)", variable=self.mode_var, value="solo", command=self.on_mode_change, font=("Segoe UI", 11, "bold"), fg=self.c_gold, bg=self.c_bg, selectcolor=self.c_panel, activebackground=self.c_bg, activeforeground=self.c_gold)
        rb_solo.pack(side="left", padx=(0, 20))

        rb_online = tk.Radiobutton(mode_select_frame, text="🌐 Jogar Online / LAN (Com Amigos)", variable=self.mode_var, value="online", command=self.on_mode_change, font=("Segoe UI", 11, "bold"), fg=self.c_text, bg=self.c_bg, selectcolor=self.c_panel, activebackground=self.c_bg, activeforeground=self.c_gold)
        rb_online.pack(side="left")

        # Container for Options
        self.options_panel = tk.Frame(content_frame, bg=self.c_panel, highlightbackground=self.c_border, highlightthickness=1)
        self.options_panel.pack(fill="both", expand=True, pady=4, padx=0)

        # Sub-frame for Solo Bot Settings
        self.solo_frame = tk.Frame(self.options_panel, bg=self.c_panel, padx=20, pady=16)
        self.solo_frame.pack(fill="both", expand=True)

        lbl_map = tk.Label(self.solo_frame, text="SELECIONE O MAPA DA BATALHA:", font=("Segoe UI", 10, "bold"), fg=self.c_gold, bg=self.c_panel)
        lbl_map.grid(row=0, column=0, sticky="w", pady=(0, 4))

        self.cb_map = ttk.Combobox(self.solo_frame, values=[m[0] for m in MAPS], state="readonly", width=36, font=("Segoe UI", 10))
        self.cb_map.current(0)
        self.cb_map.grid(row=1, column=0, sticky="w", pady=(0, 16))

        lbl_diff = tk.Label(self.solo_frame, text="DIFICULDADE DOS BOTS:", font=("Segoe UI", 10, "bold"), fg=self.c_gold, bg=self.c_panel)
        lbl_diff.grid(row=0, column=1, sticky="w", padx=(30, 0), pady=(0, 4))

        self.cb_diff = ttk.Combobox(self.solo_frame, values=["Recruta (Fácil)", "Veterano (Médio)", "Elite 187 (Difícil)"], state="readonly", width=24, font=("Segoe UI", 10))
        self.cb_diff.current(1)
        self.cb_diff.grid(row=1, column=1, sticky="w", padx=(30, 0), pady=(0, 16))

        lbl_team = tk.Label(self.solo_frame, text="FORMATO DE EQUIPE:", font=("Segoe UI", 10, "bold"), fg=self.c_gold, bg=self.c_panel)
        lbl_team.grid(row=2, column=0, sticky="w", pady=(0, 4))

        self.cb_team = ttk.Combobox(self.solo_frame, values=["8 vs 8 (Batalha Completa)", "4 vs 4 (Competitivo)", "2 vs 2 (Dupla)", "1 vs 1 (Duelo)"], state="readonly", width=36, font=("Segoe UI", 10))
        self.cb_team.current(0)
        self.cb_team.grid(row=3, column=0, sticky="w", pady=(0, 16))

        lbl_xp = tk.Label(self.solo_frame, text="SISTEMA DE PROGRESSÃO:", font=("Segoe UI", 10, "bold"), fg=self.c_gold, bg=self.c_panel)
        lbl_xp.grid(row=2, column=1, sticky="w", padx=(30, 0), pady=(0, 4))

        lbl_xp_val = tk.Label(self.solo_frame, text="✓ EXP & Patente Ativos (Salvos no banco)\n✓ Armas VIP Equipadas automaticamente", font=("Segoe UI", 9), fg=self.c_green, bg=self.c_panel, justify="left")
        lbl_xp_val.grid(row=3, column=1, sticky="w", padx=(30, 0), pady=(0, 16))

        # Sub-frame for Online Settings (hidden initially)
        self.online_frame = tk.Frame(self.options_panel, bg=self.c_panel, padx=20, pady=16)

        lbl_ip = tk.Label(self.online_frame, text="IP DO SERVIDOR HERMIT:", font=("Segoe UI", 10, "bold"), fg=self.c_gold, bg=self.c_panel)
        lbl_ip.grid(row=0, column=0, sticky="w", pady=(0, 4))

        self.ent_ip = tk.Entry(self.online_frame, font=("Segoe UI", 11), bg="#1f2230", fg="#ffffff", border=1, relief="solid", width=28)
        self.ent_ip.insert(0, "127.0.0.1")
        self.ent_ip.grid(row=1, column=0, sticky="w", pady=(0, 16))

        lbl_port = tk.Label(self.online_frame, text="PORTA:", font=("Segoe UI", 10, "bold"), fg=self.c_gold, bg=self.c_panel)
        lbl_port.grid(row=0, column=1, sticky="w", padx=(30, 0), pady=(0, 4))

        self.ent_port = tk.Entry(self.online_frame, font=("Segoe UI", 11), bg="#1f2230", fg="#ffffff", border=1, relief="solid", width=12)
        self.ent_port.insert(0, "12000")
        self.ent_port.grid(row=1, column=1, sticky="w", padx=(30, 0), pady=(0, 16))

        lbl_info = tk.Label(self.online_frame, text="Para jogar com amigos: hospede seu servidor Hermit e passe seu IP para seus amigos.\nVocê pode usar IP Local (mesma rede Wi-Fi) ou VPN (Radmin / Hamachi / VPS).", font=("Segoe UI", 9), fg=self.c_muted, bg=self.c_panel, justify="left")
        lbl_info.grid(row=2, column=0, columnspan=2, sticky="w", pady=(4, 0))

        # Bottom Display & Performance Bar
        perf_frame = tk.Frame(self, bg=self.c_bg)
        perf_frame.pack(fill="x", padx=24, pady=4)

        self.borderless_var = tk.BooleanVar(value=True)
        chk_borderless = tk.Checkbutton(
            perf_frame,
            text="Janela Sem Bordas (Win11 Instant Alt+Tab)",
            variable=self.borderless_var,
            font=("Segoe UI", 8, "bold"),
            fg=self.c_gold,
            bg=self.c_bg,
            selectcolor=self.c_panel,
            activebackground=self.c_bg,
            activeforeground=self.c_gold,
        )
        chk_borderless.pack(side="left", padx=(0, 12))

        lbl_perf = tk.Label(perf_frame, text="⚡ Ultra HD (HD1-HD6) | 144Hz+ Raw Mouse | FOV 95° | Mod PT-BR/EN", font=("Segoe UI", 8), fg=self.c_muted, bg=self.c_bg)
        lbl_perf.pack(side="left")

        # Giant Launch Button
        self.btn_launch = tk.Button(self, text="🚀 ENTRAR NO JOGO / LAUNCH GAME", font=("Segoe UI", 14, "bold"), bg="#F59E0B", fg="#000000", activebackground="#D97706", activeforeground="#000000", border=0, pady=12, cursor="hand2", command=self.launch_game)
        self.btn_launch.pack(fill="x", padx=24, pady=(8, 4))

        self.feedback_lbl = tk.Label(self, text="Pronto. Na tela de login in-game, digite seu usuário (ex: gleidison) + qualquer senha.", font=("Segoe UI", 8), fg=self.c_muted, bg=self.c_bg)
        self.feedback_lbl.pack(fill="x", padx=24, pady=(0, 12))

    def on_mode_change(self):
        mode = self.mode_var.get()
        if mode == "solo":
            self.online_frame.pack_forget()
            self.solo_frame.pack(fill="both", expand=True)
        else:
            self.solo_frame.pack_forget()
            self.online_frame.pack(fill="both", expand=True)

    def _set_feedback(self, text: str, color: str = None):
        if not self._closing:
            self.after(0, lambda: self.feedback_lbl.config(text=text, fg=color or self.c_muted))

    def _selected_map_file(self) -> str:
        idx = self.cb_map.current()
        if 0 <= idx < len(MAPS):
            return MAPS[idx][1]
        return "Arrival.World00p"

    def _check_tcp_port(self, port: int, host: str = "127.0.0.1") -> bool:
        try:
            with socket.create_connection((host, port), timeout=0.4):
                return True
        except Exception:
            return False

    def check_server(self):
        return self._check_tcp_port(12000)

    def _is_dedicated_running(self) -> bool:
        try:
            out = subprocess.check_output(
                ["tasklist", "/FI", "IMAGENAME eq TheRawServer.exe", "/NH"],
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            ).decode("utf-8", errors="ignore")
            return "TheRawServer.exe" in out
        except Exception:
            return False

    def _start_dedicated_server(self, selected_map: str):
        if not os.path.exists(SERVER_HOST_EXE):
            return
        if self._is_dedicated_running():
            return
        flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        world_arg = selected_map if selected_map.lower().startswith("worlds\\") else f"Worlds\\{selected_map}"
        proc = subprocess.Popen(
            [SERVER_HOST_EXE, "--world", world_arg, "--port", "27888"],
            cwd=CLIENT_DIR,
            creationflags=flags,
        )
        self._child_procs.append(proc)

    def _update_status_ui(self, online: bool, dedicated_online: bool = False):
        if self._closing:
            return
        if online and dedicated_online:
            self.status_dot.config(fg=self.c_green)
            self.status_text.config(text="Hermit (12000) + LithTech Dedicated (27888): ONLINE", fg=self.c_green)
        elif online:
            self.status_dot.config(fg=self.c_gold)
            self.status_text.config(text="Hermit: ONLINE (12000) | Dedicated 3D: sobe ao clicar Jogar", fg=self.c_gold)
        else:
            self.status_dot.config(fg=self.c_red)
            self.status_text.config(text="Servidores: OFFLINE — Clique em Entrar no Jogo ou Reiniciar", fg=self.c_red)

    def start_status_checker(self):
        def worker():
            while not self._closing:
                online = self.check_server()
                ded = self._is_dedicated_running()
                self.server_online = online
                try:
                    self.after(0, lambda o=online, d=ded: self._update_status_ui(o, d))
                except Exception:
                    break
                time.sleep(2)
        threading.Thread(target=worker, daemon=True).start()

    def _spawn_background(self, args: list):
        flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        proc = subprocess.Popen(args, cwd=PROJECT_DIR, creationflags=flags)
        self._child_procs.append(proc)
        return proc

    def restart_server(self):
        selected_map = self._selected_map_file()
        self._set_feedback(f"Reiniciando Servidor Hermit na porta 12000 (Mapa: {selected_map})...", self.c_gold)

        def worker():
            flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
            subprocess.run(
                ["powershell", "-Command", "Get-NetTCPConnection -LocalPort 12000 -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }"],
                capture_output=True,
                creationflags=flags,
            )
            subprocess.run(["taskkill", "/F", "/IM", "TheRawServer.exe"], capture_output=True, creationflags=flags)
            time.sleep(0.4)
            self._spawn_background([sys.executable, "-u", SERVER_SCRIPT, "--map", selected_map])
            self._start_dedicated_server(selected_map)
            for _ in range(15):
                if self.check_server():
                    self._set_feedback(f"Hermit (12000) + LithTech Dedicated (27888) ONLINE (Mapa: {selected_map}).", self.c_green)
                    self.after(0, lambda: self._update_status_ui(True, self._is_dedicated_running()))
                    return
                time.sleep(0.25)
            self._set_feedback("Falha ao subir Servidor Hermit na porta 12000.", self.c_red)

        threading.Thread(target=worker, daemon=True).start()

    def _open_web_service(self, script_path: str, port: int, label: str):
        self._set_feedback(f"Abrindo {label} (localhost:{port})...", self.c_gold)

        def worker():
            if not self._check_tcp_port(port):
                self._spawn_background([sys.executable, "-u", script_path])
                for _ in range(25):
                    if self._check_tcp_port(port):
                        break
                    time.sleep(0.25)
            webbrowser.open(f"http://localhost:{port}")
            self._set_feedback(f"{label} aberto em http://localhost:{port}.", self.c_green)

        threading.Thread(target=worker, daemon=True).start()

    def open_portal(self):
        self._open_web_service(WEB_PORTAL_SCRIPT, 8080, "Web Portal")

    def open_panel(self):
        self._open_web_service(WEB_PANEL_SCRIPT, 8081, "Painel Dev")

    def open_replay(self):
        replay_html = os.path.join(PROJECT_DIR, "targets", "district-187", "analytics", "match_replay.html")
        if os.path.exists(replay_html):
            webbrowser.open(f"file:///{replay_html.replace(os.sep, '/')}")
        else:
            self.open_portal()

    def on_close(self):
        self._closing = True
        for proc in self._child_procs:
            try:
                if proc.poll() is None:
                    proc.terminate()
            except Exception:
                pass
        self.destroy()

    def launch_game(self):
        if not os.path.exists(THE_RAW_EXE):
            messagebox.showerror("Erro", f"TheRaw.exe não encontrado em:\n{THE_RAW_EXE}")
            return

        target_ip = "127.0.0.1"
        target_port = "12000"
        if self.mode_var.get() == "online":
            target_ip = self.ent_ip.get().strip() or "127.0.0.1"
            target_port = self.ent_port.get().strip() or "12000"

        borderless = self.borderless_var.get()
        selected_map = self._selected_map_file()
        self.btn_launch.config(state="disabled")
        self._set_feedback(f"Preparando motor LithTech ({selected_map})...", self.c_gold)

        def worker():
            try:
                if target_ip in ("127.0.0.1", "localhost"):
                    if not self.check_server():
                        self._spawn_background([sys.executable, "-u", SERVER_SCRIPT, "--map", selected_map])
                        for _ in range(15):
                            if self.check_server():
                                break
                            time.sleep(0.25)
                    self._start_dedicated_server(selected_map)

                flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
                subprocess.run(["taskkill", "/F", "/IM", "TheRaw.exe"], capture_output=True, creationflags=flags)
                time.sleep(0.3)

                env = os.environ.copy()
                env["__COMPAT_LAYER"] = "RunAsInvoker"
                os.environ["__COMPAT_LAYER"] = "RunAsInvoker"

                screen_w, screen_h = 1920, 1080
                if apply_qol_profile is not None:
                    try:
                        qol = apply_qol_profile(fov=95, raw_mouse=True, borderless=borderless)
                        screen_w = int(qol.get("width", 1920))
                        screen_h = int(qol.get("height", 1080))
                    except Exception:
                        pass

                cmd = [
                    THE_RAW_EXE,
                    "-arch", "game",
                    "-archcfg", "Default.archcfg",
                    "-windowtitle", "District 187: Sin Streets",
                    "+gs_ip", target_ip,
                    "+gs_port", target_port,
                    "+windowed", "1" if borderless else "0",
                    "+ScreenWidth", str(screen_w),
                    "+ScreenHeight", str(screen_h),
                ]

                subprocess.Popen(cmd, cwd=CLIENT_DIR, env=env)
                if borderless and enforce_borderless_window is not None:
                    threading.Thread(target=enforce_borderless_window, kwargs={"timeout_sec": 12.0}, daemon=True).start()
                self._set_feedback(
                    f"TheRaw.exe iniciado ({screen_w}x{screen_h}) -> {target_ip}:{target_port}. Faça login in-game (ex: gleidison).",
                    self.c_green,
                )
            except Exception as e:
                self._set_feedback(f"Falha ao iniciar TheRaw.exe: {e}", self.c_red)
            finally:
                if not self._closing:
                    self.after(0, lambda: self.btn_launch.config(state="normal"))

        threading.Thread(target=worker, daemon=True).start()

def main():
    app = D187Launcher()
    app.mainloop()

if __name__ == "__main__":
    main()

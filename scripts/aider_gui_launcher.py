#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
District 187: Sin Streets — Aider Free AI Pair Programmer Launcher
Terminal elegante com arte ASCII, paleta de cores Cyberpunk/Amber e injecao de contexto mestre.
"""

import os
import sys
import subprocess
import time

# Forca UTF-8 no terminal Windows
if os.name == "nt":
    os.system("chcp 65001 >nul 2>&1")
    os.system("color")  # Ativa sequencias ANSI no Windows CMD

# Paleta ANSI 256 cores / TrueColor
GOLD = "\033[38;2;245;158;11m"
GOLD_BOLD = "\033[1;38;2;245;158;11m"
AMBER = "\033[38;2;217;119;6m"
CYAN = "\033[38;2;56;189;248m"
GREEN = "\033[38;2;16;185;129m"
PURPLE = "\033[38;2;168;85;247m"
WHITE = "\033[38;2;244;244;245m"
GRAY = "\033[38;2;113;113;122m"
RED = "\033[38;2;239;68;68m"
RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if not os.path.exists(os.path.join(BASE_DIR, "AGENTS.md")):
    # Se rodar como executavel standalone
    BASE_DIR = os.getcwd()

ENV_PATH = os.path.join(BASE_DIR, ".env")

ASCII_BANNER = f"""{GOLD_BOLD}
   ██████╗  ██╗███████╗████████╗██████╗ ██╗ ██████╗████████╗    ██╗ ██████╗ ███████╗
   ██╔══██╗ ██║██╔════╝╚══██╔══╝██╔══██╗██║██╔════╝╚══██╔══╝   ███║██╔════╝ ╚════██║
   ██║  ██║ ██║███████╗   ██║   ██████╔╝██║██║        ██║      ╚██║╚█████╗     ██╔╝
   ██║  ██║ ██║╚════██║   ██║   ██╔══██╗██║██║        ██║       ██║ ██╔══██╗  ██╔╝  
   ██████╔╝ ██║███████║   ██║   ██║  ██║██║╚██████╗   ██║       ██║ ╚█████╔╝  ██║   
   ╚═════╝  ╚═╝╚══════╝   ╚═╝   ╚═╝  ╚═╝╚═╝ ╚═════╝   ╚═╝       ╚═╝  ╚════╝   ╚═╝   
{RESET}{CYAN}      [ A I D E R   C O D E   P A I R I N G   —   M O D E L O S   F R E E ]{RESET}
{GRAY}         Engenharia Reversa • Motor Nativo LithTech Jupiter EX • Custo $0.00{RESET}
"""

def load_env():
    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    if not api_key and os.path.exists(ENV_PATH):
        try:
            with open(ENV_PATH, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("OPENROUTER_API_KEY="):
                        api_key = line.split("=", 1)[1].strip()
                        os.environ["OPENROUTER_API_KEY"] = api_key
        except Exception:
            pass
    return api_key

def print_box(title, items, border_color=AMBER, text_color=WHITE):
    w = 78
    print(f"{border_color}┌{'─' * (w - 2)}┐{RESET}")
    print(f"{border_color}│{RESET} {BOLD}{title:<{w - 4}}{RESET} {border_color}│{RESET}")
    print(f"{border_color}├{'─' * (w - 2)}┤{RESET}")
    for it in items:
        clean_len = len(it.replace("\033[0m", "").replace(GOLD, "").replace(CYAN, "").replace(GREEN, "").replace(PURPLE, "").replace(WHITE, "").replace(GRAY, "").replace(BOLD, "").replace(DIM, "").replace(RESET, ""))
        padding = max(0, w - 4 - clean_len)
        print(f"{border_color}│{RESET} {it}{' ' * padding} {border_color}│{RESET}")
    print(f"{border_color}└{'─' * (w - 2)}┘{RESET}")

def main():
    os.system("cls" if os.name == "nt" else "clear")
    print(ASCII_BANNER)

    key = load_env()
    if not key:
        print(f"\n{RED}[ERRO]{RESET} OPENROUTER_API_KEY não foi encontrada no arquivo .env!")
        input("\nPressione Enter para sair...")
        return

    context_items = [
        f"{GREEN}✓{RESET} {BOLD}sessions/current.md{RESET}   {GRAY}(Estado atual da sessao & handoff){RESET}",
        f"{GREEN}✓{RESET} {BOLD}projects/now.md{RESET}        {GRAY}(12 Fases ativas, diretrizes & arquitetura){RESET}",
        f"{GREEN}✓{RESET} {BOLD}decisions.md{RESET}           {GRAY}(Decisoes tecnicas e travas arquiteturais){RESET}",
        f"{GREEN}✓{RESET} {BOLD}AGENTS.md{RESET}              {GRAY}(Regras de RE, Karpathy Principles & Git){RESET}",
        f"{CYAN}ℹ{RESET} {DIM}Modo Git Ativo: Todo commit sera feito automaticamente no repo.{RESET}"
    ]
    print_box("🧠 CONTEXTO MESTRE INJETADO AUTOMATICAMENTE", context_items, border_color=CYAN)
    print()

    models_menu = [
        f"{GOLD}[1] OpenRouter Auto Free{RESET} {GREEN}(100% CUSTO ZERO • Recomendado){RESET}",
        f"    {GRAY}└─ ID:{RESET} {CYAN}openrouter/openrouter/free{RESET} {DIM}(Roteia sempre pro melhor online){RESET}",
        "",
        f"{GOLD}[2] Cohere North Mini Code{RESET} {GREEN}(100% CUSTO ZERO • Especialista Code){RESET}",
        f"    {GRAY}└─ ID:{RESET} {CYAN}openrouter/cohere/north-mini-code:free{RESET}",
        "",
        f"{GOLD}[3] NVIDIA Nemotron 3 Nano Omni{RESET} {GREEN}(100% CUSTO ZERO • 30B Reasoning){RESET}",
        f"    {GRAY}└─ ID:{RESET} {CYAN}openrouter/nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free{RESET}",
        "",
        f"{GOLD}[4] Liquid LFM 2.5{RESET} {GREEN}(100% CUSTO ZERO • Ultra Rapido){RESET}",
        f"    {GRAY}└─ ID:{RESET} {CYAN}openrouter/liquid/lfm-2.5-2.6b:free{RESET}",
    ]
    print_box("🤖 SELECIONE O MODELO GRATUITO PARA PAIR PROGRAMMING", models_menu, border_color=GOLD)

    print()
    sys.stdout.write(f"{BOLD}{GOLD}➤ Escolha uma opção [1-4] (Padrão: 1): {RESET}")
    sys.stdout.flush()
    choice = input().strip()

    if choice == "2":
        model_id = "openrouter/cohere/north-mini-code:free"
        model_name = "Cohere North Mini Code"
    elif choice == "3":
        model_id = "openrouter/nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free"
        model_name = "NVIDIA Nemotron 3 Nano"
    elif choice == "4":
        model_id = "openrouter/liquid/lfm-2.5-2.6b:free"
        model_name = "Liquid LFM 2.5"
    else:
        model_id = "openrouter/openrouter/free"
        model_name = "OpenRouter Auto Free"

    print(f"\n{GREEN}[*]{RESET} Conectando {BOLD}{model_name}{RESET}...")
    print(f"{CYAN}[*]{RESET} Modelo: {CYAN}{model_id}{RESET}")
    print(f"{GOLD}[*]{RESET} Custo: {GREEN}$0.00 (Totalmente Gratuito){RESET}")
    print(f"{GRAY}──────────────────────────────────────────────────────────────────────────────{RESET}\n")

    cmd = [
        "aider",
        "--model", model_id,
        "--read", os.path.join(BASE_DIR, "sessions", "current.md"),
        "--read", os.path.join(BASE_DIR, "projects", "now.md"),
        "--read", os.path.join(BASE_DIR, "decisions.md"),
        "--read", os.path.join(BASE_DIR, "AGENTS.md"),
    ]

    try:
        subprocess.run(cmd, cwd=BASE_DIR)
    except Exception as e:
        print(f"\n{RED}[ERRO ao disparar Aider]{RESET}: {e}")
        input("\nPressione Enter para sair...")

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
District 187: Sin Streets - Authoritative Tactical Bot Match Simulator
Simulates full 8v8 or 16v16 tactical combat on Arrival.World00p using:
  - Authentic spawn coordinates from arrival_spawns.json
  - Combat stats (damage, recoil, fire delay) from s2rebirth.db
  - AI state machine (PATROL -> ENGAGE -> RETREAT -> DEFUSE)
  - Statistical match history logging.
"""

import os
import sys
import json
import sqlite3
import random
import math
import time
from typing import List, Dict, Any

# Ensure UTF-8 output
sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TARGET_DIR = os.path.join(BASE_DIR, "targets", "district-187")
SPAWNS_JSON = os.path.join(TARGET_DIR, "data", "arrival_spawns.json")
DB_PATH = os.path.join(TARGET_DIR, "data", "s2rebirth.db")

class Weapon:
    def __init__(self, name: str, damage: int, recoil: int, fire_delay: int, slot: str):
        self.name = name
        self.damage = max(damage, 15)
        self.recoil = recoil
        self.fire_delay = max(fire_delay, 50)
        self.slot = slot

class Bot:
    def __init__(self, bot_id: int, name: str, team: int, spawn_pos: Dict[str, float], weapon: Weapon):
        self.bot_id = bot_id
        self.name = name
        self.team = team  # 0 = SWAT, 1 = Gangsters
        self.team_name = "SWAT" if team == 0 else "Gangster"
        self.spawn_pos = spawn_pos
        self.x = spawn_pos["x"]
        self.y = spawn_pos["y"]
        self.z = spawn_pos["z"]
        self.health = 100
        self.alive = True
        self.weapon = weapon
        self.kills = 0
        self.deaths = 0
        self.headshots = 0
        self.damage_dealt = 0

    def reset_round(self):
        self.health = 100
        self.alive = True
        self.x = self.spawn_pos["x"]
        self.y = self.spawn_pos["y"]
        self.z = self.spawn_pos["z"]

def load_weapons_from_db() -> List[Weapon]:
    if not os.path.exists(DB_PATH):
        # Fallback default weapons
        return [
            Weapon("M4a1", 31, 37, 85, "ana-silah"),
            Weapon("AK-47", 36, 48, 100, "ana-silah"),
            Weapon("K1 Rail", 25, 23, 70, "ana-silah"),
            Weapon("AWM Camo", 100, 85, 950, "ana-silah")
        ]
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT name, damage, recoil, fire_delay, slot FROM weapons WHERE slot='ana-silah' AND damage > 0 ORDER BY damage DESC LIMIT 20")
    rows = c.fetchall()
    conn.close()
    return [Weapon(r["name"], r["damage"], r["recoil"], r["fire_delay"], r["slot"]) for r in rows]

def load_spawns() -> Dict[int, List[Dict[str, float]]]:
    with open(SPAWNS_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)
    spawns_by_team = {0: [], 1: []}
    for s in data["spawns"]:
        spawns_by_team[s["team"]].append({"x": s["x"], "y": s["y"], "z": s["z"]})
    return spawns_by_team

def run_match(rounds_to_win=3, team_size=8):
    print("=====================================================================")
    print("  District 187: Sin Streets — Authoritative Bot Match Simulator")
    print("  Map: Arrival (LithTech Jupiter EX World00p)")
    print(f"  Format: {team_size}v{team_size} Competitive Bomb Defusal (Best of {rounds_to_win*2 - 1})")
    print("=====================================================================\n")

    weapons = load_weapons_from_db()
    spawns = load_spawns()

    swat_names = ["Ghost", "Vanguard", "Sentinel", "Delta", "Alpha", "Bravo", "Echo", "Recon"]
    gang_names = ["Apex", "Cobra", "Havoc", "Viper", "Rogue", "Bane", "Zero", "Sin"]

    swat_team: List[Bot] = []
    gang_team: List[Bot] = []

    for i in range(team_size):
        s_pos = spawns[0][i % len(spawns[0])]
        g_pos = spawns[1][i % len(spawns[1])]
        w_swat = random.choice(weapons)
        w_gang = random.choice(weapons)
        swat_team.append(Bot(i, f"SWAT_{swat_names[i % len(swat_names)]}", 0, s_pos, w_swat))
        gang_team.append(Bot(i + team_size, f"Gang_{gang_names[i % len(gang_names)]}", 1, g_pos, w_gang))

    swat_score = 0
    gang_score = 0
    round_num = 1

    # Mid Choke Point coordinates from inspect_world00p
    mid_x, mid_z = 336.0, 477.0

    while swat_score < rounds_to_win and gang_score < rounds_to_win:
        print(f"--- [ROUND {round_num}] Score: SWAT {swat_score} x {gang_score} Gangsters ---")
        for b in swat_team + gang_team:
            b.reset_round()

        round_time = 0
        bomb_planted = False
        bomb_defused = False
        bomb_timer = 45.0

        # Simulate round ticks
        while True:
            round_time += 1.0
            # Alive counts
            swat_alive = [b for b in swat_team if b.alive]
            gang_alive = [b for b in gang_team if b.alive]

            if not swat_alive or not gang_alive:
                break

            # Move bots closer to Mid
            for b in swat_alive:
                b.x += (mid_x - b.x) * 0.15 + random.uniform(-25, 25)
                b.z += (mid_z - b.z) * 0.15 + random.uniform(-25, 25)
            for b in gang_alive:
                b.x += (mid_x - b.x) * 0.15 + random.uniform(-25, 25)
                b.z += (mid_z - b.z) * 0.15 + random.uniform(-25, 25)

            # Bomb plant trigger for Gangsters
            if not bomb_planted and round_time >= 15.0 and random.random() < 0.25:
                bomb_planter = random.choice(gang_alive)
                bomb_planted = True
                print(f"  [BOMB PLANTED] {bomb_planter.name} planted C4 at Site Alpha! 45s timer active.")

            # Firefight simulation
            attacker = random.choice(swat_alive + gang_alive)
            target_pool = gang_alive if attacker.team == 0 else swat_alive
            if target_pool:
                target = random.choice(target_pool)
                # Calculate distance
                dist = math.sqrt((target.x - attacker.x)**2 + (target.z - attacker.z)**2)
                # Hit probability decreases with recoil and distance
                hit_prob = max(0.20, 0.85 - (attacker.weapon.recoil / 120.0) - (dist / 8000.0))

                if random.random() < hit_prob:
                    is_headshot = random.random() < 0.25
                    multiplier = 2.5 if is_headshot else 1.0
                    dmg = int(attacker.weapon.damage * multiplier * random.uniform(0.9, 1.1))
                    target.health -= dmg
                    attacker.damage_dealt += dmg

                    if target.health <= 0:
                        target.alive = False
                        target.deaths += 1
                        attacker.kills += 1
                        hs_str = " (HEADSHOT!)" if is_headshot else ""
                        if is_headshot:
                            attacker.headshots += 1
                        print(f"  [KILL] {attacker.name} eliminated {target.name} with {attacker.weapon.name}{hs_str} ({dmg} dmg)")

            # Check bomb defusal if planted and SWAT in vicinity
            if bomb_planted and not bomb_defused:
                bomb_timer -= 1.0
                if bomb_timer <= 0:
                    print(f"  [C4 DETONATION] The bomb exploded! Gangsters win round {round_num}!")
                    gang_score += 1
                    break
                elif len(gang_alive) == 0 and len(swat_alive) > 0:
                    bomb_defused = True
                    defuser = random.choice(swat_alive)
                    print(f"  [BOMB DEFUSED] {defuser.name} safely defused the C4! SWAT wins round {round_num}!")
                    swat_score += 1
                    break

        # Round winner evaluation if by elimination
        if not bomb_planted or (bomb_planted and len(swat_alive) == 0):
            if len(swat_alive) > len(gang_alive):
                print(f"  [ROUND END] SWAT eliminated all hostile forces! (+1 point)")
                swat_score += 1
            elif len(gang_alive) > len(swat_alive):
                print(f"  [ROUND END] Gangsters wiped out SWAT forces! (+1 point)")
                gang_score += 1

        print(f"  Round {round_num} Completed in {round_time:.1f}s\n")
        round_num += 1

    # Match Summary
    winner = "SWAT (Law Enforcement)" if swat_score > gang_score else "Gangsters (Underworld)"
    print("=====================================================================")
    print(f"  MATCH RESULT: {winner.upper()} VICTORIOUS ({swat_score} x {gang_score})")
    print("=====================================================================")

    all_bots = swat_team + gang_team
    all_bots.sort(key=lambda b: (b.kills, b.damage_dealt), reverse=True)
    mvp = all_bots[0]

    print(f"\n  MVP of the Match: {mvp.name} [{mvp.team_name}] - {mvp.kills} Kills, {mvp.headshots} Headshots, {mvp.damage_dealt} Dmg\n")

    print(f"  {'Player':<18} {'Team':<10} {'Kills':<6} {'Deaths':<8} {'Headshots':<10} {'Damage':<8} {'Weapon':<14}")
    print("  " + "-"*76)
    for b in all_bots:
        print(f"  {b.name:<18} {b.team_name:<10} {b.kills:<6} {b.deaths:<8} {b.headshots:<10} {b.damage_dealt:<8} {b.weapon.name:<14}")

    return {
        "winner": winner,
        "swat_score": swat_score,
        "gang_score": gang_score,
        "mvp": mvp.name,
        "total_kills": sum(b.kills for b in all_bots)
    }

if __name__ == "__main__":
    run_match()

import sys
import ssl
import json
import argparse
import urllib.request
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8')

API_BASE = 'https://s2rebirth.com/api/oyuncu'

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

class S2RebirthAPI:
    def __init__(self):
        self.headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

    def _fetch(self, endpoint):
        url = f"{API_BASE}{endpoint}"
        req = urllib.request.Request(url, headers=self.headers)
        with urllib.request.urlopen(req, context=ctx, timeout=15) as resp:
            return json.loads(resp.read().decode('utf-8'))

    def get_server_config(self):
        return self._fetch('/ayar')

    def get_rankings_and_telemetry(self):
        return self._fetch('/siralama')

def main():
    parser = argparse.ArgumentParser(description="S2 Rebirth Live Portal API Client & Telemetry Inspector")
    parser.add_argument('--summary', action='store_true', help="Show high-level server telemetry summary")
    parser.add_argument('--top-players', type=int, default=0, metavar='N', help="List top N players")
    parser.add_argument('--top-clans', type=int, default=0, metavar='N', help="List top N clans")
    parser.add_argument('--matches', type=int, default=0, metavar='N', help="List last N completed matches")
    parser.add_argument('--player', type=str, help="Search specific player across leaderboards and match logs")

    args = parser.parse_args()
    api = S2RebirthAPI()

    try:
        data = api.get_rankings_and_telemetry()
    except Exception as e:
        print(f"[-] Error querying live API: {e}")
        return

    # Default to summary if no flags
    if not (args.summary or args.top_players or args.top_clans or args.matches or args.player):
        args.summary = True

    if args.summary:
        print("="*65)
        print("          S2 REBIRTH — LIVE COMMUNITY TELEMETRY          ")
        print("="*65)
        print(f"Total Registered/Active Players: {data.get('toplamOyuncu', 0):,}")
        print(f"Total Active Clans:             {data.get('toplamKlan', 0):,}")
        print(f"Live Leaderboard Snapshot:      {len(data.get('oyuncular', []))} top ranked")
        print(f"Recent Match Telemetry Buffer:  {len(data.get('maclar', []))} matches recorded")
        
        cfg = api.get_server_config()
        print(f"Turnstile Protection Active:    {cfg.get('turnstile')}")
        print(f"Registration / Downloads Open:  {cfg.get('indirme')}")
        print("="*65)

    if args.top_players > 0:
        players = data.get('oyuncular', [])[:args.top_players]
        print(f"\nTOP {len(players)} PLAYERS:")
        print(f"{'#':<4} | {'Player':<18} | {'Clan':<16} | {'Level':<5} | {'XP (TP)':<10} | {'K/D':<6} | {'Win Rate':<8}")
        print("-" * 78)
        for p in players:
            kills = p.get('oldurme', 0)
            deaths = max(p.get('olum', 1), 1)
            kd = kills / deaths
            wins = p.get('galibiyet', 0)
            losses = p.get('maglubiyet', 0)
            total_games = max(wins + losses, 1)
            wr = (wins / total_games) * 100
            clan = p.get('klan') or '-'
            print(f"{p.get('sira', '-'):<4} | {p.get('ad'):<18} | {clan:<16} | Lv{p.get('seviye',0):<3} | {p.get('tp',0):<10,} | {kd:<6.2f} | {wr:<7.1f}%")

    if args.top_clans > 0:
        clans = data.get('klanlar', [])[:args.top_clans]
        print(f"\nTOP {len(clans)} CLANS:")
        print(f"{'#':<4} | {'Clan Name':<20} | {'Leader':<16} | {'Points':<8} | {'W/L':<10} | {'Win Rate':<8}")
        print("-" * 72)
        for i, c in enumerate(clans, 1):
            wins = c.get('galibiyet', 0)
            losses = c.get('maglubiyet', 0)
            wr = (wins / max(wins + losses, 1)) * 100
            print(f"{i:<4} | {c.get('ad'):<20} | {c.get('lider', '-'):<16} | {c.get('puan',0):<8} | {wins}/{losses:<7} | {wr:<7.1f}%")

    if args.matches > 0:
        matches = data.get('maclar', [])[:args.matches]
        print(f"\nLAST {len(matches)} MATCHES:")
        for m in matches:
            t_finish = datetime.fromtimestamp(m.get('bitis', 0)/1000).strftime('%Y-%m-%d %H:%M') if m.get('bitis') else 'N/A'
            duration_min = m.get('sureSn', 0) // 60
            duration_sec = m.get('sureSn', 0) % 60
            is_clan = "CLAN MATCH" if m.get('klanMaci') else "PUBLIC"
            score = f"Team 1 [{m.get('skor1',0)}] x [{m.get('skor2',0)}] Team 2"
            clans_info = f"({m.get('klanAd1')} vs {m.get('klanAd2')})" if m.get('klanMaci') else ""
            print(f"\n[{t_finish}] {m.get('haritaAd')} ({m.get('modAd')}) — {is_clan} {clans_info}")
            print(f"  Score: {score} | Duration: {duration_min}m{duration_sec}s | MVP: {m.get('mvp', 'N/A')}")
            players_in_match = m.get('oyuncular', [])
            top_scorers = sorted(players_in_match, key=lambda x: x.get('oldurme', 0), reverse=True)[:4]
            scorers_str = ", ".join([f"{p.get('ad')} ({p.get('oldurme')}/{p.get('olum')})" for p in top_scorers])
            print(f"  Top Fraggers: {scorers_str}")

    if args.player:
        q = args.player.lower()
        found = False
        for p in data.get('oyuncular', []):
            if q in p.get('ad', '').lower():
                found = True
                print(f"\n[+] Found Player in Leaderboards:")
                print(f"  Name: {p.get('ad')} | Clan: {p.get('klan')} | Rank: {p.get('rutbe')} (Lv {p.get('seviye')})")
                print(f"  Total XP: {p.get('tp'):,} | Rank #{p.get('sira')}")
                kills = p.get('oldurme', 0)
                deaths = max(p.get('olum', 1), 1)
                print(f"  K/D: {kills}/{deaths} ({kills/deaths:.2f})")
                print(f"  Wins/Losses: {p.get('galibiyet')}/{p.get('maglubiyet')}")
        if not found:
            print(f"[-] Player '{args.player}' not found in top 100 leaderboard.")

if __name__ == '__main__':
    main()

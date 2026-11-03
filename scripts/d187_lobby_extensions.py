#!/usr/bin/env python3
"""
District 187: Sin Streets — Lobby Extensions:
  - In-Game Chat Command Processor (/map, /bots, /give, /mmr, /stats, /loadout, /clan)
  - Persistent Loadout Manager (Slots A/B/C, Weapon Attachments, SWAT/Gangster Skins)
  - Clan Registry & Emblem Service backed by s2rebirth.db
"""

import os
import sqlite3
import struct
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "targets", "district-187", "data", "s2rebirth.db")

AVAILABLE_MAPS = {
    "arrival": "Arrival.World00p",
    "twoway": "Worlds\\twoway.World00p",
    "thebank": "Worlds\\thebank.World00p",
    "oldtown": "Worlds\\oldtown.World00p",
    "killport": "Worlds\\Kill_Port.World00p",
    "ghostship": "Worlds\\Ghost_Ship.World00p",
    "heaven": "Worlds\\10025_Heaven.World00p",
    "hospital": "Worlds\\10031_Hospital.World00p",
    "downtown": "Worlds\\10038_Downtown.World00p",
    "grandbazar": "Worlds\\10023_GrandBazar.World00p",
}


class LobbyExtensionService:
    """Manages persistent loadouts, clans, and in-game slash commands."""

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self.active_map = "Worlds\\twoway.World00p"
        self.bot_count = 16
        self.bot_difficulty = "adaptive"
        self.active_slot = 0

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def get_player_loadouts(self, account_id: int = 1) -> list:
        conn = self._conn()
        rows = conn.execute(
            "SELECT * FROM player_loadouts WHERE account_id = ? ORDER BY slot_index ASC",
            (account_id,),
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def update_loadout_slot(
        self,
        account_id: int,
        slot_index: int,
        primary_name: str = None,
        secondary_name: str = None,
        optic: str = None,
        barrel: str = None,
        mag: str = None,
    ) -> dict:
        conn = self._conn()
        c = conn.cursor()
        if primary_name:
            w = c.execute(
                "SELECT group_id, name FROM weapons WHERE name LIKE ? LIMIT 1",
                (f"%{primary_name}%",),
            ).fetchone()
            if w:
                c.execute(
                    "UPDATE player_loadouts SET primary_weapon_id = ?, primary_weapon_name = ? WHERE account_id = ? AND slot_index = ?",
                    (w["group_id"], w["name"], account_id, slot_index),
                )
        if secondary_name:
            w = c.execute(
                "SELECT group_id, name FROM weapons WHERE name LIKE ? LIMIT 1",
                (f"%{secondary_name}%",),
            ).fetchone()
            if w:
                c.execute(
                    "UPDATE player_loadouts SET secondary_weapon_id = ?, secondary_weapon_name = ? WHERE account_id = ? AND slot_index = ?",
                    (w["group_id"], w["name"], account_id, slot_index),
                )
        if optic:
            c.execute(
                "UPDATE player_loadouts SET optic_attachment = ? WHERE account_id = ? AND slot_index = ?",
                (optic, account_id, slot_index),
            )
        if barrel:
            c.execute(
                "UPDATE player_loadouts SET barrel_attachment = ? WHERE account_id = ? AND slot_index = ?",
                (barrel, account_id, slot_index),
            )
        if mag:
            c.execute(
                "UPDATE player_loadouts SET mag_attachment = ? WHERE account_id = ? AND slot_index = ?",
                (mag, account_id, slot_index),
            )
        conn.commit()
        updated = c.execute(
            "SELECT * FROM player_loadouts WHERE account_id = ? AND slot_index = ?",
            (account_id, slot_index),
        ).fetchone()
        conn.close()
        return dict(updated) if updated else {}

    def get_clans(self) -> list:
        conn = self._conn()
        rows = conn.execute("SELECT * FROM clans ORDER BY clan_elo DESC").fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def process_chat_command(self, nickname: str, raw_text: str) -> dict:
        """
        Executes in-game slash commands (/map, /bots, /give, /mmr, /stats, /loadout, /clan, /help)
        and returns a structured response + system chat reply.
        """
        text = raw_text.strip()
        if not text.startswith("/"):
            return {
                "is_command": False,
                "sender": nickname,
                "reply": f"{nickname}: {text}",
            }

        parts = text.split()
        cmd = parts[0].lower()
        args = parts[1:]

        if cmd == "/help":
            return {
                "is_command": True,
                "sender": "[SISTEMA D187]",
                "reply": "Comandos: /map <nome> | /bots <qtd> <easy|med|hard|adaptive> | /give <arma> | /loadout <A|B|C> | /mmr | /clan",
            }

        if cmd == "/map":
            key = args[0].lower() if args else "twoway"
            resolved = AVAILABLE_MAPS.get(key, f"Worlds\\{key}.World00p")
            self.active_map = resolved
            return {
                "is_command": True,
                "sender": "[SISTEMA D187]",
                "reply": f"Arena da sala alterada para: {resolved}",
                "active_map": resolved,
            }

        if cmd == "/bots":
            cnt = int(args[0]) if (args and args[0].isdigit()) else 16
            diff = args[1].lower() if len(args) > 1 else "adaptive"
            self.bot_count = max(1, min(16, cnt))
            self.bot_difficulty = diff
            return {
                "is_command": True,
                "sender": "[SISTEMA D187]",
                "reply": f"Bots configurados: {self.bot_count} operativos | Dificuldade: {self.bot_difficulty.upper()}",
                "bot_count": self.bot_count,
                "bot_difficulty": self.bot_difficulty,
            }

        if cmd == "/give":
            query = " ".join(args) if args else "AK-47"
            updated = self.update_loadout_slot(1, self.active_slot, primary_name=query)
            wname = updated.get("primary_weapon_name", query)
            return {
                "is_command": True,
                "sender": "[ARSENAL VIP]",
                "reply": f"Arma equipada no Slot {chr(65 + self.active_slot)}: {wname} (+Mira EOTech & Pente Duplo)",
            }

        if cmd == "/loadout":
            slot_letter = args[0].upper() if args else "A"
            idx = {"A": 0, "B": 1, "C": 2}.get(slot_letter, 0)
            self.active_slot = idx
            slots = self.get_player_loadouts(1)
            cur = slots[idx] if idx < len(slots) else {}
            return {
                "is_command": True,
                "sender": "[LOADOUT]",
                "reply": (
                    f"Ativado {cur.get('slot_name', slot_letter)}: "
                    f"{cur.get('primary_weapon_name')} | {cur.get('secondary_weapon_name')} | "
                    f"{cur.get('optic_attachment')}"
                ),
            }

        if cmd in ("/mmr", "/stats"):
            conn = self._conn()
            row = conn.execute(
                "SELECT * FROM player_mmr WHERE LOWER(nickname) = LOWER(?) LIMIT 1",
                (nickname,),
            ).fetchone()
            if not row:
                row = conn.execute("SELECT * FROM player_mmr ORDER BY elo_rating DESC LIMIT 1").fetchone()
            conn.close()
            if row:
                return {
                    "is_command": True,
                    "sender": "[TELEMETRIA MMR]",
                    "reply": (
                        f"{row['nickname']} -> Elo: {row['elo_rating']} ({row['skill_tier']}) | "
                        f"HS%: {int(row['hs_rate']*100)}% | TTK: {row['avg_ttk_ms']}ms | "
                        f"Bots: {row['recommended_bot_difficulty']}"
                    ),
                }

        if cmd == "/clan":
            clans = self.get_clans()
            top = clans[0] if clans else {"clan_tag": "META", "clan_name": "Meta Data Science Ops", "clan_elo": 2145}
            return {
                "is_command": True,
                "sender": "[QUARTEL CLÃ]",
                "reply": f"Clã Ativo: [{top['clan_tag']}] {top['clan_name']} | Elo do Clã: {top['clan_elo']}",
            }

        return {
            "is_command": True,
            "sender": "[SISTEMA D187]",
            "reply": f"Comando desconhecido '{cmd}'. Digite /help para ver as opções.",
        }

    @staticmethod
    def build_sn_chat_packet(sender: str, message: str) -> bytes:
        """Serializes SN_Chat (0x210152) payload for GameClient.dll."""
        payload = bytearray(168)
        struct.pack_into("<I", payload, 0, 0x210152)
        s_bytes = sender.encode("utf-8")[:31]
        m_bytes = message.encode("utf-8")[:127]
        payload[8 : 8 + len(s_bytes)] = s_bytes
        payload[40 : 40 + len(m_bytes)] = m_bytes
        return bytes(payload)


if __name__ == "__main__":
    svc = LobbyExtensionService()
    for test_cmd in ["/help", "/mmr", "/loadout B", "/give Vector", "/map thebank", "/bots 12 hard", "/clan"]:
        res = svc.process_chat_command("Gleidison", test_cmd)
        print(f"CMD: {test_cmd:<18} -> {res['sender']}: {res['reply']}")

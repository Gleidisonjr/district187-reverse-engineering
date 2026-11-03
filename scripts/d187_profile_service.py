#!/usr/bin/env python3
"""
District 187: Sin Streets - VIP Profile & Lobby Inventory Service
Pulls weapons, items, and ranks from s2rebirth.db and synthesizes full VIP
binary packets (SN_UserInfo, SN_ItemList, SN_Record, SN_LockEnd) for the native client.
"""

import os
import sys
import sqlite3
import json
from typing import Dict, Any, List

# Ensure UTF-8 output
sys.stdout.reconfigure(encoding='utf-8')

# Import core protocol library
try:
    from d187_protocol import (
        HermitCipher,
        build_user_info_packet,
        build_item_list_packet,
        build_record_packet,
        build_lock_end_packet,
        Opcodes
    )
except ImportError:
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from d187_protocol import (
        HermitCipher,
        build_user_info_packet,
        build_item_list_packet,
        build_record_packet,
        build_lock_end_packet,
        Opcodes
    )

DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "targets", "district-187", "data", "s2rebirth.db"
)

def get_db_connection() -> sqlite3.Connection:
    if not os.path.exists(DB_PATH):
        raise FileNotFoundError(f"Database not found at {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def load_vip_weapons(limit: int = 185) -> List[Dict[str, Any]]:
    """Loads weapons from s2rebirth.db and formats them for SN_ItemList."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT group_id, name, slot, class, damage, recoil
        FROM weapons
        ORDER BY damage DESC
        LIMIT ?
    """, (limit,))
    rows = cursor.fetchall()
    conn.close()

    items = []
    # Equip the top items into default slots
    # Slot 0: Primary ('ana-silah')
    # Slot 1: Secondary ('tabanca')
    # Slot 2: Melee ('bicak')
    # Slot 3: Grenade ('bomba')
    equipped = {0: False, 1: False, 2: False, 3: False}

    for r in rows:
        w_id = r["group_id"]
        db_slot = (r["slot"] or "").strip()
        assigned_slot = -1  # Default in inventory

        if db_slot == "ana-silah" and not equipped[0]:
            assigned_slot = 0
            equipped[0] = True
        elif db_slot == "tabanca" and not equipped[1]:
            assigned_slot = 1
            equipped[1] = True
        elif db_slot == "bicak" and not equipped[2]:
            assigned_slot = 2
            equipped[2] = True
        elif db_slot == "bomba" and not equipped[3]:
            assigned_slot = 3
            equipped[3] = True

        items.append({
            "item_id": int(w_id),
            "item_type": 1,
            "durability": 100,
            "slot": assigned_slot,
            "name": r["name"]
        })

    return items

def build_full_vip_profile(
    account_id: int = 1001,
    nickname: str = "Gleidison",
    rank: int = 58,
    exp: int = 50000000,
    gold: int = 9999999,
    cash: int = 9999999,
    clan_name: str = "D187_Meta"
) -> Dict[str, bytes]:
    """
    Generates all binary packets needed to load a complete VIP character
    into the District 187 lobby.
    """
    items = load_vip_weapons(limit=185)

    user_info_pkt = build_user_info_packet(
        account_id=account_id,
        nickname=nickname,
        rank=rank,
        exp=exp,
        gold=gold,
        cash=cash,
        clan_name=clan_name
    )

    item_list_pkt = build_item_list_packet(items)
    record_pkt = build_record_packet(kills=2450, deaths=180, headshots=1620, wins=310, losses=15)
    lock_end_pkt = build_lock_end_packet()

    return {
        "user_info": user_info_pkt,
        "item_list": item_list_pkt,
        "record": record_pkt,
        "lock_end": lock_end_pkt,
        "items_count": len(items)
    }

if __name__ == "__main__":
    print("[+] Building VIP Character Profile and Lobby Payloads...")
    profile = build_full_vip_profile()
    print(f"  [+] Loaded {profile['items_count']} weapons into inventory.")
    print(f"  [+] SN_UserInfo packet size: {len(profile['user_info'])} bytes")
    print(f"  [+] SN_ItemList packet size: {len(profile['item_list'])} bytes")
    print(f"  [+] SN_Record   packet size: {len(profile['record'])} bytes")
    print(f"  [+] SN_LockEnd  packet size: {len(profile['lock_end'])} bytes")

    # Verify Hermit encryption on all packets
    cipher = HermitCipher(0x0F)
    stream = bytearray()
    for key in ("user_info", "item_list", "record", "lock_end"):
        stream += cipher.encrypt(profile[key])

    print(f"[+] Total encrypted lobby handshake stream: {len(stream)} bytes ready for TCP dispatch.")

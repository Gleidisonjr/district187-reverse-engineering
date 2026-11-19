#!/usr/bin/env python3
"""
District 187: Sin Streets — Automated RE Toolchain Regression Test Suite (Zero Warnings)
Validates all offline static RE extractors, binary dissectors, and bit-exact compilers:
  1. 326/326 protocol opcodes + 251 CDispatch_* handlers (d187_protocol_schema.json)
  2. 530/530 Scaleform GFx Flash-to-C++ handlers (scaleform_flash_bridge.json)
  3. 522 RTTI classes + 12 exports in GameServer.dll (gameserver_internals.json)
  4. Byte-exact (diff=0) GADB v3 (.Gamdb00p) parsing across all 5 client databases
  5. Bit-exact SHA-256 round-trip of SKDB v2 (.Strdb00p) compiler (build_strdb00p.py)
  6. Ballistics & game mode extraction + LithTech UDP MID_* dispatch map
  7. Bit-exact SHA-256 round-trip of GADB v3 (.Gamdb00p) compiler (build_gamdb00p.py)
  8. ClientShell vtables & TheRaw.exe/GameClient.dll CVar catalog
"""

import hashlib
import json
import os
import sys
import unittest

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(SCRIPT_DIR)
DATA_DIR = os.path.join(ROOT_DIR, "targets", "district-187", "data")
CLIENT_DIR = os.path.join(ROOT_DIR, "targets", "district-187", "client-rebirth")

if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)


def _read_json(name: str) -> dict:
    with open(os.path.join(DATA_DIR, name), encoding="utf-8") as f:
        return json.load(f)


class TestDistrict187REToolchain(unittest.TestCase):
    def test_01_protocol_schema_326_opcodes(self):
        data = _read_json("d187_protocol_schema.json")
        self.assertEqual(data["total_packets"], 326)
        self.assertEqual(data["resolved_opcodes"], 326)
        self.assertGreaterEqual(data["resolved_client_handlers"], 250)
        by_op = {p["opcode"]: p for p in data["packets"]}
        self.assertEqual(by_op[0x110112]["name"], "tPacket_NAccount_NIdentity_SA_JoyGameLogin")
        self.assertEqual(by_op[0x210121]["name"], "tPacket_NLaunch_NLock_SN_LockEnd")
        self.assertEqual(by_op[0x220203]["name"], "tPacket_NMatchup_NRoom_SN_Info")
        self.assertEqual(by_op[0x220233]["name"], "tPacket_NMatchup_NRoom_SN_UserList")
        self.assertEqual(by_op[0x220319]["name"], "tPacket_NMatchup_NTeam_SN_ChangeLeader")
        self.assertEqual(by_op[0x222103]["name"], "tPacket_NMatchup_NPlay_CN_StartButton")
        self.assertEqual(by_op[0x420303]["name"], "tPacket_NHosting_NGuest_SN_HostConnect")

    def test_02_scaleform_flash_bridge_530_handlers(self):
        data = _read_json("scaleform_flash_bridge.json")
        self.assertEqual(data["total_flash_dispatch_classes"], 530)
        self.assertEqual(data["resolved_vtables"], 530)

    def test_03_gameserver_internals_522_rtti(self):
        data = _read_json("gameserver_internals.json")
        self.assertEqual(data["export_count"], 12)
        self.assertEqual(data["total_rtti_classes"], 522)
        self.assertIn("CGameServerShell", data["key_vtables"])

    def test_04_gamdb00p_byte_exact_all_5_databases(self):
        from inspect_gamdb00p import parse_gamdb00p
        for rel in [
            os.path.join("Game", "Database", "TheRaw.Gamdb00p"),
            os.path.join("Database", "TheRaw.Gamdb00p"),
            os.path.join("Game", "DatabaseLocalized", "TheRawL.Gamdb00p"),
            os.path.join("AnimationDatabase", "S2_anim.Gamdb00p"),
            os.path.join("ProfileDatabase", "Defaults.Gamdb00p"),
        ]:
            res = parse_gamdb00p(os.path.join(CLIENT_DIR, rel))
            self.assertTrue(res["byte_exact"], f"Not byte-exact: {rel}")

    def test_05_strdb00p_skdb_v2_sha256_roundtrip(self):
        from build_strdb00p import SRC_STRDB, unpack_strdb00p, pack_strdb00p
        with open(SRC_STRDB, "rb") as f:
            orig = f.read()
        repacked = pack_strdb00p(unpack_strdb00p(SRC_STRDB))
        self.assertEqual(hashlib.sha256(orig).hexdigest(), hashlib.sha256(repacked).hexdigest())

    def test_06_ballistics_and_udp_mid_artifacts(self):
        bal = _read_json("gamdb_ballistics_and_modes.json")
        self.assertGreaterEqual(bal["ammo_multiplayer_count"], 180)
        self.assertGreaterEqual(bal["weapons_multiplayer_count"], 95)
        self.assertEqual(bal["modes_count"], 20)
        udp = _read_json("lithtech_udp_mid_protocol.json")
        self.assertEqual(udp["on_message_va"], "0x1004fd70")
        self.assertGreaterEqual(udp["active_mid_count"], 7)

    def test_07_gamdb00p_bit_exact_sha256_roundtrip(self):
        from build_gamdb00p import unpack_gamdb00p_raw, pack_gamdb00p_raw
        for rel in [
            os.path.join("ProfileDatabase", "Defaults.Gamdb00p"),
            os.path.join("Game", "DatabaseLocalized", "TheRawL.Gamdb00p"),
        ]:
            full = os.path.join(CLIENT_DIR, rel)
            with open(full, "rb") as f:
                orig = f.read()
            repacked = pack_gamdb00p_raw(unpack_gamdb00p_raw(full))
            self.assertEqual(hashlib.sha256(orig).hexdigest(), hashlib.sha256(repacked).hexdigest())

    def test_08_clientshell_and_cvars(self):
        data = _read_json("clientshell_and_cvars.json")
        self.assertGreaterEqual(data["theraw_exe_cvar_candidates_count"], 100)
        self.assertGreaterEqual(data["gameclient_dll_cvar_candidates_count"], 100)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    unittest.main(verbosity=2)

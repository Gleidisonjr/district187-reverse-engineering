#!/usr/bin/env python3
"""
District 187: Sin Streets — 1-Command Mod Bundle Builder & Safe Installer/Rollback
Builds a self-contained, SHA-256 verified mod bundle in targets/district-187/extracted/mod_bundle_ptbr_clean/:
  - TheRaw_PTBR.Strdb00p     -> Game/StringDatabase/Turkey/TheRaw.Strdb00p
  - TheRaw_CleanMaps.Gamdb00p -> Game/Database/TheRaw.Gamdb00p
  - manifest.json            -> SHA-256 checksums & target paths

Usage:
  python scripts/build_d187_mod_bundle.py              # Build bundle only (safe, never touches client-rebirth)
  python scripts/build_d187_mod_bundle.py --install    # Backup originals to .bak and install bundle
  python scripts/build_d187_mod_bundle.py --rollback   # Restore .bak originals cleanly
"""

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXTRACTED_DIR = os.path.join(ROOT_DIR, "targets", "district-187", "extracted")
BUNDLE_DIR = os.path.join(EXTRACTED_DIR, "mod_bundle_ptbr_clean")
CLIENT_DIR = os.path.join(ROOT_DIR, "targets", "district-187", "client-rebirth")

BUNDLE_FILES = [
    ("TheRaw_PTBR.Strdb00p", os.path.join("Game", "StringDatabase", "Turkey", "TheRaw.Strdb00p")),
    ("TheRaw_CleanMaps.Gamdb00p", os.path.join("Game", "Database", "TheRaw.Gamdb00p")),
]


def sha256_file(path: str) -> str:
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def build_bundle():
    subprocess.run([sys.executable, os.path.join(ROOT_DIR, "scripts", "build_strdb00p.py")], check=True)
    subprocess.run([sys.executable, os.path.join(ROOT_DIR, "scripts", "patch_gamdb_clean_maps.py")], check=True)

    os.makedirs(BUNDLE_DIR, exist_ok=True)
    manifest = {"bundle": "District 187 PT-BR + CleanMaps Mod Bundle", "files": []}

    for fname, rel_target in BUNDLE_FILES:
        src = os.path.join(EXTRACTED_DIR, fname)
        dst = os.path.join(BUNDLE_DIR, fname)
        shutil.copy2(src, dst)
        manifest["files"].append({
            "bundle_file": fname,
            "target_rel_path": rel_target.replace("\\", "/"),
            "size_bytes": os.path.getsize(dst),
            "sha256": sha256_file(dst),
        })

    manifest_path = os.path.join(BUNDLE_DIR, "manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    print(f"[+] Mod bundle ready at: {os.path.relpath(BUNDLE_DIR, ROOT_DIR)} ({len(manifest['files'])} files, SHA-256 verified)")


def install_bundle():
    if not os.path.exists(os.path.join(BUNDLE_DIR, "manifest.json")):
        build_bundle()
    for fname, rel_target in BUNDLE_FILES:
        src = os.path.join(BUNDLE_DIR, fname)
        dst = os.path.join(CLIENT_DIR, rel_target)
        bak = dst + ".bak"
        if os.path.exists(dst) and not os.path.exists(bak):
            shutil.copy2(dst, bak)
            print(f"[+] Backed up original -> {rel_target}.bak")
        shutil.copy2(src, dst)
        print(f"[+] Installed {fname} -> {rel_target}")


def rollback_bundle():
    for _, rel_target in BUNDLE_FILES:
        dst = os.path.join(CLIENT_DIR, rel_target)
        bak = dst + ".bak"
        if os.path.exists(bak):
            shutil.copy2(bak, dst)
            print(f"[+] Restored original from {rel_target}.bak")
        else:
            print(f"[-] No backup found for {rel_target}")


def main():
    parser = argparse.ArgumentParser(description="District 187 Mod Bundle Builder & Safe Installer")
    parser.add_argument("--install", action="store_true", help="Backup originals and install bundle into client-rebirth/")
    parser.add_argument("--rollback", action="store_true", help="Restore .bak originals in client-rebirth/")
    args = parser.parse_args()

    if args.rollback:
        rollback_bundle()
    elif args.install:
        install_bundle()
    else:
        build_bundle()


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()

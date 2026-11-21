#!/usr/bin/env python3
"""
extract_all_game_assets.py
Extrai TODOS os assets 3D restantes de District 187 (character models, player models,
animation files .Anim00p, material/texture files) dos archives HBEK para disco.

Input:  Game.Res00 / Game.ResDt
        Update_1.Res00 / Update_1.ResDt
        Update_2.Res00 / Update_2.ResDt
Output: Game/characters/, Game/players/, Game/animations/, etc.
"""

import struct
import os
import sys
import zlib
from collections import defaultdict

CLIENT = r'C:\Users\dopamine\Desktop\Projetos\Reverse Engineering\targets\district-187\client-rebirth'
GAME   = os.path.join(CLIENT, 'Game')

HDR_SZ = 48

# Archives to scan (index, data)
ARCHIVES = [
    (os.path.join(GAME, 'Game.Res00'),     os.path.join(GAME, 'Game.ResDt')),
    (os.path.join(GAME, 'Update_1.Res00'), os.path.join(GAME, 'Update_1.ResDt')),
    (os.path.join(GAME, 'Update_2.Res00'), os.path.join(GAME, 'Update_2.ResDt')),
]

# File extensions / path prefixes we care about
TARGET_PREFIXES = (
    'characters\\',
    'characters/',
    'players\\',
    'players/',
    'animations\\',
    'animations/',
)

TARGET_EXTENSIONS = (
    '.model00p',
    '.anim00p',
    '.mat00p',
    '.tex00p',
)

# Any .Model00p or .Anim00p anywhere (not just under target prefixes)
GLOBAL_EXTENSIONS = (
    '.anim00p',
)


def parse_res00(res00_path):
    """Parse HBEK index file, return list of (path, r_off, c_sz)."""
    if not os.path.exists(res00_path):
        print(f'  [SKIP] Archive not found: {res00_path}')
        return []

    with open(res00_path, 'rb') as f:
        hdr = f.read(HDR_SZ)

    # Magic check
    magic = hdr[:4]
    print(f'  Magic: {magic!r}')

    str_sz  = struct.unpack_from('<I', hdr,  8)[0]
    n_dirs  = struct.unpack_from('<I', hdr, 12)[0]
    n_files = struct.unpack_from('<I', hdr, 16)[0]

    print(f'  str_sz={str_sz}, n_dirs={n_dirs}, n_files={n_files}')

    strtab_off = HDR_SZ
    dir_off    = strtab_off + str_sz
    file_off   = dir_off + n_dirs * 16

    with open(res00_path, 'rb') as f:
        f.seek(strtab_off)
        strtab = f.read(str_sz)
        f.seek(file_off)
        recs_raw = f.read(n_files * 48)

    def get_str(off):
        if off >= len(strtab):
            return ''
        end = strtab.find(b'\x00', off)
        return strtab[off:end].decode('ascii', 'ignore') if end >= 0 else ''

    # Enumerate all unique string table entries for directory prefix discovery
    all_dirs = set()
    pos = 0
    while pos < len(strtab) - 1:
        end = strtab.find(b'\x00', pos)
        if end < 0:
            break
        s = strtab[pos:end].decode('ascii', 'ignore')
        if s:
            # Collect the top-level directory prefix
            parts = s.replace('/', '\\').split('\\')
            if len(parts) > 1:
                all_dirs.add(parts[0].lower())
        pos = end + 1

    records = []

    # Scan 48-byte file records
    for i in range(n_files):
        rec  = recs_raw[i*48:(i+1)*48]
        str_off = struct.unpack_from('<I', rec, 32)[0]
        r_off   = struct.unpack_from('<Q', rec, 36)[0]
        c_sz    = struct.unpack_from('<I', rec, 44)[0]

        if r_off >= (1 << 48):
            continue
        if c_sz == 0:
            continue

        path = get_str(str_off)
        if not path:
            continue

        path_lo = path.lower()
        ext_lo  = os.path.splitext(path_lo)[1]

        # Check if this file should be extracted
        wanted = False

        # 1. Files under target prefixes (characters\, players\, animations\)
        if any(path_lo.startswith(p) for p in TARGET_PREFIXES):
            wanted = True

        # 2. Any .Anim00p globally
        if ext_lo in GLOBAL_EXTENSIONS:
            wanted = True

        # 3. .Model00p files not under weapons\ (characters/players anywhere in path)
        if ext_lo == '.model00p':
            if not path_lo.startswith('weapons\\') and not path_lo.startswith('weapons/'):
                wanted = True
            # Also grab any .Model00p that has 'character' or 'player' in path
            if 'character' in path_lo or 'player' in path_lo:
                wanted = True

        if wanted:
            records.append((path, r_off, c_sz))

    # Also scan 16-byte dir/compact records (some files are encoded here)
    with open(res00_path, 'rb') as f:
        f.seek(dir_off)
        compact_raw = f.read(n_dirs * 16)

    for i in range(n_dirs):
        rec = compact_raw[i*16:(i+1)*16]
        str_off, r_off_u32, pad, c_sz = struct.unpack('<4I', rec)
        if r_off_u32 == 0 or c_sz == 0:
            continue
        r_off = r_off_u32  # 32-bit offset for compact records

        path = get_str(str_off)
        if not path:
            continue

        path_lo = path.lower()
        ext_lo  = os.path.splitext(path_lo)[1]

        wanted = False
        if any(path_lo.startswith(p) for p in TARGET_PREFIXES):
            wanted = True
        if ext_lo in GLOBAL_EXTENSIONS:
            wanted = True
        if ext_lo == '.model00p':
            if not path_lo.startswith('weapons\\') and not path_lo.startswith('weapons/'):
                wanted = True
            if 'character' in path_lo or 'player' in path_lo:
                wanted = True

        if wanted:
            records.append((path, r_off, c_sz))

    return records, all_dirs


def discover_all_prefixes(res00_path):
    """Return set of all top-level directory prefixes found in strtab."""
    if not os.path.exists(res00_path):
        return set()

    with open(res00_path, 'rb') as f:
        hdr = f.read(HDR_SZ)

    str_sz = struct.unpack_from('<I', hdr, 8)[0]

    with open(res00_path, 'rb') as f:
        f.seek(HDR_SZ)
        strtab = f.read(str_sz)

    prefixes = set()
    all_paths = []
    pos = 0
    while pos < len(strtab) - 1:
        end = strtab.find(b'\x00', pos)
        if end < 0:
            break
        s = strtab[pos:end].decode('ascii', 'ignore')
        if s:
            parts = s.replace('/', '\\').split('\\')
            if len(parts) > 1:
                prefixes.add(parts[0].lower())
            all_paths.append(s)
        pos = end + 1

    return prefixes, all_paths


def extract_records(records, resdt_path, archive_name):
    """Extract files from .ResDt data archive."""
    if not os.path.exists(resdt_path):
        print(f'  [SKIP] Data archive not found: {resdt_path}')
        return 0, 0

    extracted = 0
    skipped   = 0
    errors    = 0

    with open(resdt_path, 'rb') as resdt_f:
        for path, r_off, c_sz in records:
            # Normalize path separators
            norm_path = path.replace('/', os.sep).replace('\\', os.sep)
            out_path  = os.path.join(GAME, norm_path)
            os.makedirs(os.path.dirname(out_path), exist_ok=True)

            if os.path.exists(out_path):
                skipped += 1
                continue

            try:
                resdt_f.seek(r_off)
                compressed = resdt_f.read(c_sz)
                if not compressed:
                    errors += 1
                    print(f'  [ERR] {path}: empty read at r_off={r_off}')
                    continue
                data = zlib.decompress(compressed)
                with open(out_path, 'wb') as out:
                    out.write(data)
                extracted += 1
                print(f'  [OK] {archive_name}: {path} ({len(data):,} bytes)')
            except zlib.error as e:
                errors += 1
                print(f'  [ZLIB ERR] {archive_name}: {path} r_off={r_off} c_sz={c_sz}: {e}')
            except Exception as e:
                errors += 1
                print(f'  [ERR] {archive_name}: {path}: {e}')

    return extracted, skipped, errors


# ─── MAIN ───────────────────────────────────────────────────────────────────

print('=' * 70)
print('District 187 — Full Game Asset Extractor')
print('=' * 70)

# Phase 1: Discover all top-level prefixes across all archives
print('\n[PHASE 1] Discovering all strtab path prefixes...')
all_prefixes = set()
for res00, resdt in ARCHIVES:
    if not os.path.exists(res00):
        continue
    name = os.path.basename(res00)
    print(f'\n  Scanning {name}...')
    prefixes, all_paths = discover_all_prefixes(res00)
    all_prefixes.update(prefixes)
    print(f'  Top-level dirs in {name}: {sorted(prefixes)}')
    print(f'  Total strtab entries: {len(all_paths)}')

print(f'\n  ALL unique top-level prefixes: {sorted(all_prefixes)}')

# Phase 2: Parse and extract target files
print('\n[PHASE 2] Extracting character/player/animation assets...')

total_records   = []
archive_stats   = {}

for res00, resdt in ARCHIVES:
    if not os.path.exists(res00):
        continue
    name = os.path.basename(res00)
    print(f'\nParsing {name}...')

    result = parse_res00(res00)
    if isinstance(result, list):
        records = result
        dirs = set()
    else:
        records, dirs = result

    # Categorize for reporting
    char_models   = [r for r in records if r[0].lower().startswith('characters\\') and r[0].lower().endswith('.model00p')]
    player_models = [r for r in records if r[0].lower().startswith('players\\') and r[0].lower().endswith('.model00p')]
    anim_files    = [r for r in records if r[0].lower().endswith('.anim00p')]
    mat_files     = [r for r in records if r[0].lower().endswith('.mat00p')]
    other_models  = [r for r in records
                     if r[0].lower().endswith('.model00p')
                     and not r[0].lower().startswith('characters\\')
                     and not r[0].lower().startswith('players\\')
                     and not r[0].lower().startswith('weapons\\')]

    print(f'  Character models (.Model00p under characters\\): {len(char_models)}')
    print(f'  Player models (.Model00p under players\\):       {len(player_models)}')
    print(f'  Animation files (.Anim00p):                     {len(anim_files)}')
    print(f'  Material files (.Mat00p):                       {len(mat_files)}')
    print(f'  Other non-weapon models (.Model00p):            {len(other_models)}')
    print(f'  Total records to extract:                       {len(records)}')

    archive_stats[name] = {
        'char_models': len(char_models),
        'player_models': len(player_models),
        'anim_files': len(anim_files),
        'mat_files': len(mat_files),
        'other_models': len(other_models),
        'total': len(records),
    }

    if records:
        print(f'  Extracting from {os.path.basename(resdt)}...')
        extracted, skipped, errors = extract_records(records, resdt, name)
        archive_stats[name]['extracted'] = extracted
        archive_stats[name]['skipped']   = skipped
        archive_stats[name]['errors']    = errors
        print(f'  Result: {extracted} extracted, {skipped} skipped (already on disk), {errors} errors')
    else:
        print('  No matching records — nothing to extract from this archive.')

# Phase 3: Final disk state report
print('\n[PHASE 3] Post-extraction disk state...')

def count_files(path):
    if not os.path.exists(path):
        return 0, []
    all_files = []
    for root, dirs, files in os.walk(path):
        for fn in files:
            all_files.append(os.path.join(root, fn))
    return len(all_files), all_files

chars_dir   = os.path.join(GAME, 'characters')
players_dir = os.path.join(GAME, 'players')
anims_dir   = os.path.join(GAME, 'animations')

chars_count,   chars_files   = count_files(chars_dir)
players_count, players_files = count_files(players_dir)
anims_count,   anims_files   = count_files(anims_dir)

print(f'\n  Game\\characters\\ : {chars_count} files')
for f in sorted(chars_files)[:30]:
    print(f'    {os.path.relpath(f, GAME)}')
if chars_count > 30:
    print(f'    ... and {chars_count - 30} more')

print(f'\n  Game\\players\\    : {players_count} files')
for f in sorted(players_files)[:30]:
    print(f'    {os.path.relpath(f, GAME)}')
if players_count > 30:
    print(f'    ... and {players_count - 30} more')

print(f'\n  Game\\animations\\ : {anims_count} files')
for f in sorted(anims_files)[:20]:
    print(f'    {os.path.relpath(f, GAME)}')
if anims_count > 20:
    print(f'    ... and {anims_count - 20} more')

# Summary
print('\n' + '=' * 70)
print('SUMMARY')
print('=' * 70)
for archive_name, stats in archive_stats.items():
    print(f'\n  {archive_name}:')
    for k, v in stats.items():
        print(f'    {k}: {v}')

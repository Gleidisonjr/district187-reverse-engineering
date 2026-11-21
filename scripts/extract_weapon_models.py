#!/usr/bin/env python3
"""
extract_weapon_models.py
Extrai os model files de armas de Game.Res00/Game.ResDt para o disco,
corrigindo o Fail_OpenModelFile que causa a tela preta no D187.
"""
import struct, os, sys, zlib

CLIENT = r'C:\Users\dopamine\Desktop\Projetos\Reverse Engineering\targets\district-187\client-rebirth'
GAME   = os.path.join(CLIENT, 'Game')
RES00  = os.path.join(GAME, 'Game.Res00')
RESDT  = os.path.join(GAME, 'Game.ResDt')

HDR_SZ = 48
with open(RES00, 'rb') as f:
    hdr = f.read(HDR_SZ)

str_sz  = struct.unpack_from('<I', hdr, 8)[0]
n_dirs  = struct.unpack_from('<I', hdr, 12)[0]
n_files = struct.unpack_from('<I', hdr, 16)[0]

strtab_off = HDR_SZ
dir_off    = strtab_off + str_sz
file_off   = dir_off + n_dirs * 16

with open(RES00, 'rb') as f:
    f.seek(strtab_off)
    strtab = f.read(str_sz)
    f.seek(file_off)
    recs_raw = f.read(n_files * 48)

def get_str(off):
    if off >= len(strtab): return ''
    end = strtab.find(b'\x00', off)
    return strtab[off:end].decode('ascii', 'ignore') if end >= 0 else ''

# Search strtab for the full path of weapon model files
# to discover which str_off offsets correspond to full-path entries
target_paths = {}
search_terms = [
    b'weapons\\1_main\\world_models\\',
    b'weapons\\1_main\\view_models\\',
    b'weapons\\1_main\\materials\\',
    b'weapons\\1_main\\textures\\',
    b'weapons\\1_main\\animations\\',
]

print('Scanning strtab for full weapon paths...')
pos = 0
while pos < len(strtab) - 4:
    end = strtab.find(b'\x00', pos)
    if end < 0:
        break
    s = strtab[pos:end]
    for term in search_terms:
        if s.lower().startswith(term.lower()):
            target_paths[pos] = s.decode('ascii', 'ignore')
    pos = end + 1

print(f'Found {len(target_paths)} full weapon model paths in strtab')

# Build a lookup: str_off -> full_path
# so we can find file records that use these str_offs
full_path_records = {}
compact_path_records = {}

for i in range(n_files):
    rec = recs_raw[i*48:(i+1)*48]
    str_off = struct.unpack_from('<I', rec, 32)[0]
    r_off   = struct.unpack_from('<Q', rec, 36)[0]
    c_sz    = struct.unpack_from('<I', rec, 44)[0]
    if str_off in target_paths and r_off < (1 << 48):
        full_path_records[i] = (target_paths[str_off], r_off, c_sz)

print(f'File records with full weapon model paths: {len(full_path_records)}')
for idx, (path, r_off, c_sz) in sorted(full_path_records.items())[:20]:
    print(f'  [{idx}] {path}  r_off={r_off} c_sz={c_sz}')

# ALSO check compact records (16-byte "dir records") for full weapon paths
print('\nScanning compact records (at dir_off) for weapon paths...')
with open(RES00, 'rb') as f:
    f.seek(dir_off)
    compact_raw = f.read(n_dirs * 16)

compact_matches = []
for i in range(n_dirs):
    rec = compact_raw[i*16:(i+1)*16]
    str_off, r_off_u32, pad, c_sz = struct.unpack('<4I', rec)
    if str_off in target_paths and r_off_u32 > 0 and c_sz > 0:
        compact_matches.append((i, target_paths[str_off], r_off_u32, c_sz))

print(f'Compact records with full weapon model paths: {len(compact_matches)}')
for idx, path, r_off, c_sz in compact_matches[:20]:
    print(f'  compact[{idx}] {path}  r_off={r_off} c_sz={c_sz}')

# EXTRACTION
# Collect all records to extract
to_extract = []

# From full-path file records
for idx, (path, r_off, c_sz) in full_path_records.items():
    to_extract.append((path, r_off, c_sz))

# From compact records
for idx, path, r_off, c_sz in compact_matches:
    to_extract.append((path, r_off, c_sz))

if not to_extract:
    print('\nNo full-path weapon model records found!')
    print('Falling back: extracting LOD models to world_models/, others to view_models/')

    for i in range(n_files):
        rec = recs_raw[i*48:(i+1)*48]
        str_off = struct.unpack_from('<I', rec, 32)[0]
        r_off   = struct.unpack_from('<Q', rec, 36)[0]
        c_sz    = struct.unpack_from('<I', rec, 44)[0]
        name    = get_str(str_off)

        if not name.endswith('.Model00p'):
            continue
        # Only weapon world/view models (not eye or character models)
        name_lo = name.lower()
        prefixes = ('mar_', 'ar_', 'sg_', 'smg_', 'sn_', 'ps_', 'pi_', 'pi2_')
        if not any(name_lo.startswith(p) for p in prefixes):
            continue
        # Skip invalid entries (c_sz too small or huge r_off)
        if c_sz < 100 or r_off > 1_000_000_000:
            continue

        if 'lod' in name_lo:
            path = f'weapons\\1_main\\world_models\\{name}'
        else:
            path = f'weapons\\1_main\\view_models\\{name}'
        to_extract.append((path, r_off, c_sz))

print(f'\nTotal files to extract: {len(to_extract)}')

# Do the extraction
extracted = 0
errors = 0
with open(RESDT, 'rb') as resdt_f:
    for path, r_off, c_sz in to_extract:
        out_path = os.path.join(GAME, path.replace('\\', os.sep))
        os.makedirs(os.path.dirname(out_path), exist_ok=True)

        try:
            resdt_f.seek(r_off)
            compressed = resdt_f.read(c_sz)
            data = zlib.decompress(compressed)
            with open(out_path, 'wb') as out:
                out.write(data)
            extracted += 1
            print(f'  [OK] {path} ({len(data):,} bytes)')
        except Exception as e:
            errors += 1
            print(f'  [ERR] {path}: {e}')

print(f'\nDone: {extracted} extracted, {errors} errors')

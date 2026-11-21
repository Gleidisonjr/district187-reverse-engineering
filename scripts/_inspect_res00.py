import struct, os, sys, re, zlib

RES00 = r'C:\Users\dopamine\Desktop\Projetos\Reverse Engineering\targets\district-187\client-rebirth\Game\Game.Res00'
RESDT = r'C:\Users\dopamine\Desktop\Projetos\Reverse Engineering\targets\district-187\client-rebirth\Game\Game.ResDt'

HDR_SZ = 48
with open(RES00, 'rb') as f:
    hdr = f.read(HDR_SZ)

str_sz = struct.unpack_from('<I', hdr, 8)[0]
n_dirs = struct.unpack_from('<I', hdr, 12)[0]
n_files = struct.unpack_from('<I', hdr, 16)[0]

strtab_off = HDR_SZ
# Layout: hdr -> strtab -> dir_records -> file_records
dir_off  = strtab_off + str_sz
file_off = dir_off + n_dirs * 16

with open(RES00, 'rb') as f:
    f.seek(strtab_off)
    strtab = f.read(str_sz)
    f.seek(dir_off)
    dirs_raw = f.read(n_dirs * 16)
    f.seek(file_off)
    recs_raw = f.read(n_files * 48)

def get_str(off):
    if off >= len(strtab): return ''
    end = strtab.find(b'\x00', off)
    return strtab[off:end].decode('ascii', 'ignore') if end >= 0 else ''

# Read a file record
def read_frec(i):
    rec = recs_raw[i*48:(i+1)*48]
    dir_idx = struct.unpack_from('<I', rec, 0)[0]
    str_off = struct.unpack_from('<I', rec, 32)[0]
    r_off   = struct.unpack_from('<Q', rec, 36)[0]
    c_sz    = struct.unpack_from('<I', rec, 44)[0]
    name    = get_str(str_off)
    return dir_idx, name, r_off, c_sz

# Inspect the "directory marker" records (r_off = 0xFFFFFFFFFFFFFFFF or huge)
INVALID_ROFF = 0xFFFFFFFFFFFFFFFF
print('--- Directory marker records (r_off >= 2^48) ---')
dir_markers = []
for i in range(n_files):
    dir_idx, name, r_off, c_sz = read_frec(i)
    if r_off > (1 << 48):  # implausible offset = dir marker
        dir_markers.append((i, name, r_off, c_sz, dir_idx))
        if len(dir_markers) <= 30:
            print(f'  [{i:5d}] "{name}" dir_idx={dir_idx} r_off=0x{r_off:X} c_sz={c_sz}')

print(f'Total dir markers: {len(dir_markers)}')

# Now: for each file record check what dir_idx values exist in the weapon model range
print('\n--- dir_idx distribution for records 12780-12830 ---')
for i in range(12780, 12830):
    dir_idx, name, r_off, c_sz = read_frec(i)
    if name.endswith('.Model00p'):
        print(f'  [{i:5d}] "{name}" dir_idx={dir_idx}')

# Check: is dir_idx a file_record index (pointing to a directory marker)?
# Check dir_idx for the directory markers themselves
print('\n--- dir_idx of some directory markers ---')
for fm_idx, fm_name, fm_roff, fm_csz, fm_diridx in dir_markers[:10]:
    print(f'  marker[{fm_idx}] name="{fm_name}" its_dir_idx={fm_diridx}')

# Try: does any directory marker have a name matching the directory for weapon models?
print('\n--- Weapon-related directory markers ---')
for fm_idx, fm_name, fm_roff, fm_csz, fm_diridx in dir_markers:
    if 'weapon' in fm_name.lower() or '1_main' in fm_name or 'world_model' in fm_name.lower():
        print(f'  [{fm_idx:5d}] "{fm_name}" dir_idx={fm_diridx}')

# Key question: what is dir_idx=0 referring to?
# Inspect dir record 0 at offset dir_off
print(f'\n--- Dir record 0 raw bytes at offset {dir_off} ---')
rec0 = dirs_raw[0:16]
print('  hex:', ' '.join(f'{b:02x}' for b in rec0))
print('  as 4×uint32:', [hex(v) for v in struct.unpack('<4I', rec0)])
# Try as str_off + parent + first_child + num_files
so, par, fc, nf = struct.unpack('<4I', rec0)
print(f'  str_off={so} → "{get_str(so)}", parent={par}, first_child={fc}, num_files={nf}')

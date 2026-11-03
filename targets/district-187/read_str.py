import pefile
pe = pefile.PE(r'targets\district-187\client-rebirth\Game\GameClient.dll')
base = pe.OPTIONAL_HEADER.ImageBase
for va in [0x10498804, 0x104a4630, 0x104a4680, 0x104a4610]:
    txt = pe.get_data(va - base, 64).split(b'\x00')[0]
    print(f'0x{va:08x}: {repr(txt)}')

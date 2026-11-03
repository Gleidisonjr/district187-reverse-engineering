import capstone

with open(r'targets/district-187/client-rebirth/Game/GameClient.dll', 'rb') as f:
    dll = f.read()

# 0x10190e20
# Offset = 0x400 + (0x10190e20 - 0x10001000) = 0x400 + 0x18fe20 = 0x190220
off = 0x190220
va = 0x10190e20
code = dll[off:off+200]

md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
for ins in md.disasm(code, va):
    print(f"0x{ins.address:08x}: {ins.mnemonic:<8} {ins.op_str}")

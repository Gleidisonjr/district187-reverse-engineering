import pefile
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

pe = pefile.PE(r'targets\district-187\client-rebirth\Game\GameClient.dll')
base = pe.OPTIONAL_HEADER.ImageBase
md = Cs(CS_ARCH_X86, CS_MODE_32)

va_start = 0x10191cbd
rva = va_start - base
data = pe.get_data(rva, 200)

for insn in md.disasm(data, va_start):
    print(f'0x{insn.address:08x}: {insn.mnemonic:<8} {insn.op_str}')
    if insn.address > 0x10191d60:
        break

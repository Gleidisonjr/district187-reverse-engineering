import struct, capstone

with open(r'targets/district-187/client-rebirth/Game/GameClient.dll', 'rb') as f:
    dll = f.read()

def va2raw(va):
    if va >= 0x10482000:
        return 0x480600 + (va - 0x10482000)
    return 0x400 + (va - 0x10001000)

for name in [b'tPacket_NAccount_NIdentity_CQ_Login', b'tPacket_NAccount_NIdentity_SA_Login', b'tPacket_NAccount_NIdentity_CQ_MenaLogin', b'tPacket_NAccount_NIdentity_SA_MenaLogin']:
    pos = dll.find(name)
    if pos != -1:
        va = 0x10482000 + (pos - 0x480600)
        print(f"String '{name.decode()}' at raw {hex(pos)} (VA: {hex(va)})")
        # search references to string VA
        pat = struct.pack('<I', va)
        idx = 0
        while True:
            p = dll.find(pat, idx)
            if p == -1: break
            ref_va = 0x10001000 + (p - 0x400) if p < 0x480600 else 0x10482000 + (p - 0x480600)
            print(f"  Referenced at VA: {hex(ref_va)}")
            idx = p + 1

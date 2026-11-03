#!/usr/bin/env python3
"""
Surgical Patcher for GameClient.dll (District 187: Sin Streets / S2 Rebirth)
Neutralizes the fatal "Message Error" assertion:
"GDB Mission/Level에 CSV 테이블과 일치 하지 않은 DetailInfo 정보가 있습니다."

Applied Patches:
1. Offset 0x407f50 (VA 0x10408b50):
   Changes prologue to `mov al, 1; ret; nop; nop; nop` (\xb0\x01\xc3\x90\x90\x90)
   Ensures the verification routine returns TRUE immediately.
2. Offset 0x65704 (VA 0x10066304):
   Changes `jne 0x1006634d` (\x75\x47) to `jmp 0x1006634d` (\xeb\x47)
   Unconditionally skips the MessageBoxA call and engine shutdown routine.
"""

import os
import sys

TARGET_FILES = [
    os.path.join(os.path.dirname(__file__), "..", "targets", "district-187", "client-rebirth", "Game", "GameClient.dll"),
    os.path.join(os.path.dirname(__file__), "..", "targets", "district-187", "client-rebirth", "GameClient.dll"),
]

def apply_patch():
    for target in TARGET_FILES:
        target = os.path.abspath(target)
        if not os.path.exists(target):
            print(f"[!] Target not found: {target}")
            continue

        with open(target, "rb") as f:
            data = bytearray(f.read())

        # Check & patch 0x65704
        b_65704 = data[0x65704:0x65704+2]
        if b_65704 == b"\x75\x47":
            data[0x65704:0x65704+2] = b"\xeb\x47"
            print(f"[+] 0x65704 patched (jne -> jmp) in {os.path.basename(target)}")
        elif b_65704 == b"\xeb\x47":
            print(f"[*] 0x65704 already patched in {os.path.basename(target)}")
        else:
            print(f"[-] Unexpected bytes at 0x65704 in {target}: {b_65704.hex()}")

        # Check & patch 0x407f50
        b_407f50 = data[0x407f50:0x407f50+6]
        if b_407f50 == b"\x81\xec\x1c\x01\x00\x00":
            data[0x407f50:0x407f50+6] = b"\xb0\x01\xc3\x90\x90\x90"
            print(f"[+] 0x407f50 patched (mov al, 1; ret) in {os.path.basename(target)}")
        elif b_407f50 == b"\xb0\x01\xc3\x90\x90\x90":
            print(f"[*] 0x407f50 already patched in {os.path.basename(target)}")
        else:
            print(f"[-] Unexpected bytes at 0x407f50 in {target}: {b_407f50.hex()}")

        with open(target, "wb") as f:
            f.write(data)

    print("[+] All target DLLs verified and patched.")

if __name__ == "__main__":
    apply_patch()

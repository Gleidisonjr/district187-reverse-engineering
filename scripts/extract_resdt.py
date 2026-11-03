#!/usr/bin/env python3
"""
District 187: Sin Streets - ResDt Archive Extractor & Asset Tool
Reverse-engineered specification of LithTech / CJ GameLab .ResDt container format:
  - Header: Sequential concatenated Zlib deflated streams (78 da)
  - Data: Raw uncompressed DDS textures, World00p maps, Model00p meshes, Strdb00p strings
  - Footer: Table of Contents (TOC) with length-prefixed path strings and flags
"""

import os
import sys
import zlib
import struct
import argparse
from typing import List, Dict, Any, Tuple

# Ensure UTF-8 output
sys.stdout.reconfigure(encoding='utf-8')

def parse_resdt_toc(file_bytes: bytes) -> List[str]:
    """
    Parses the Table of Contents stored at the end of the .ResDt file.
    TOC format per entry:
      [name_length: uint16] [file_path: ASCII string] [padding/flags: 4 bytes]
    """
    # Find start of TOC by searching backwards from the end
    # We look for a valid sequence of string entries
    entries = []
    
    # Locate where the string table begins (scan backwards from end)
    pos = len(file_bytes) - 4
    # Scan backwards until we hit compressed binary data
    while pos > 1024:
        # Check if byte is 0x00 and previous is a valid string character
        if file_bytes[pos] == 0x00 and file_bytes[pos-1] in (0x70, 0x73, 0x65, 0x30, 0x64): # 'p', 's', 'e', '0', 'd'
            pos -= 1
        else:
            pos -= 1
        if pos < len(file_bytes) - 500000:
            break

    # Robust parsing of all TOC entries from the end
    # Walk forward from the earliest detected valid path
    # Search for pattern: uint16 length followed by path with backslash or slash
    start_pos = -1
    for p in range(len(file_bytes) - 200000, len(file_bytes) - 20):
        if p < 0:
            continue
        n_len = struct.unpack('<H', file_bytes[p:p+2])[0]
        if 4 <= n_len <= 160 and p + 2 + n_len + 4 <= len(file_bytes):
            name_bytes = file_bytes[p+2:p+2+n_len]
            if (b'\\' in name_bytes or b'/' in name_bytes) and all(32 <= b < 127 for b in name_bytes):
                start_pos = p
                break

    if start_pos == -1:
        # Fallback: find first occurrence of CRC\\ or Data
        import re
        m = re.search(rb'[A-Za-z0-9_]{3,}\\[A-Za-z0-9_]{3,}\.[A-Za-z0-9]{3,}', file_bytes)
        if m:
            start_pos = m.start() - 2

    if start_pos != -1:
        cur = start_pos
        while cur < len(file_bytes) - 4:
            n_len = struct.unpack('<H', file_bytes[cur:cur+2])[0]
            if 0 < n_len < 256 and cur + 2 + n_len + 4 <= len(file_bytes):
                name = file_bytes[cur+2:cur+2+n_len].decode('ascii', errors='ignore')
                entries.append(name)
                cur += 2 + n_len + 4
            else:
                cur += 1

    return entries

def extract_resdt(resdt_path: str, output_dir: str = None, list_only: bool = False, max_extract: int = None):
    if not os.path.exists(resdt_path):
        print(f"[-] File not found: {resdt_path}")
        return

    file_size = os.path.getsize(resdt_path)
    print(f"[+] Loading .ResDt archive: {resdt_path} ({file_size:,} bytes)...")

    with open(resdt_path, "rb") as f:
        file_bytes = f.read()

    toc_names = parse_resdt_toc(file_bytes)
    print(f"[+] Decoded {len(toc_names)} asset paths from Table of Contents (TOC).")

    if list_only:
        print("\n--- Asset Manifest (First 35 files) ---")
        for i, name in enumerate(toc_names[:35]):
            print(f"  [{i:04d}] {name}")
        if len(toc_names) > 35:
            print(f"  ... and {len(toc_names) - 35} more assets.")
        return

    if not output_dir:
        base_name = os.path.splitext(os.path.basename(resdt_path))[0]
        output_dir = os.path.join(os.path.dirname(resdt_path), f"extracted_{base_name}")

    os.makedirs(output_dir, exist_ok=True)
    print(f"[+] Extracting assets to: {output_dir}")

    # Sequential decompression of Zlib streams
    pos = 0
    stream_idx = 0
    extracted_count = 0

    while pos < len(file_bytes) - 10:
        if file_bytes[pos] == 0x78 and file_bytes[pos+1] in (0xda, 0x9c, 0x01):
            try:
                d = zlib.decompressobj()
                unpacked = d.decompress(file_bytes[pos:])
                consumed = len(file_bytes[pos:]) - len(d.unused_data)
                
                # Match asset name from TOC if available
                if stream_idx < len(toc_names):
                    asset_rel_path = toc_names[stream_idx]
                else:
                    # Generic name based on format
                    ext = "bin"
                    if unpacked[:4] == b"DDS ":
                        ext = "dds"
                    elif unpacked[:4] == b"\x71\x00\x00\x00":
                        ext = "World00p"
                    asset_rel_path = f"asset_{stream_idx:04d}.{ext}"

                # Clean relative path
                asset_rel_path = asset_rel_path.replace("/", os.sep).replace("\\", os.sep)
                out_path = os.path.join(output_dir, asset_rel_path)
                os.makedirs(os.path.dirname(out_path), exist_ok=True)

                with open(out_path, "wb") as out_f:
                    out_f.write(unpacked)

                pos += consumed
                stream_idx += 1
                extracted_count += 1

                if extracted_count % 25 == 0:
                    print(f"  [*] Extracted {extracted_count} assets ({pos / file_size * 100:.1f}%)...")

                if max_extract and extracted_count >= max_extract:
                    print(f"[+] Reached extraction limit of {max_extract} assets.")
                    break

            except Exception as e:
                pos += 1
        else:
            # Reached end of compressed data / TOC boundary
            break

    print(f"\n[+] Successfully extracted {extracted_count} assets into {output_dir}")

def main():
    parser = argparse.ArgumentParser(description="District 187 LithTech ResDt Archive Tool")
    parser.add_argument("archive", help="Path to .ResDt archive file")
    parser.add_argument("--list", action="store_true", help="List files in TOC without extracting")
    parser.add_argument("--out", default=None, help="Output destination folder")
    parser.add_argument("--max", type=int, default=None, help="Maximum number of files to extract")
    args = parser.parse_args()

    extract_resdt(args.archive, output_dir=args.out, list_only=args.list, max_extract=args.max)

if __name__ == "__main__":
    main()

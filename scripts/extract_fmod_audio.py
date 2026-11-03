#!/usr/bin/env python3
"""
District 187: Sin Streets - FMOD SoundBank (FSB5) Audio Extractor & Cataloger
Reverse-Engineered FSB5 Format:
  - Header: 'FSB5', Version 1, Num Samples, Sample Headers Size, Name Table Size, Data Size, Codec
  - Sample Headers: Bit-packed sample parameters (Sample Rate, Channels, Sample Count, Data Offset)
  - Name Table: Offset array pointing to null-terminated ASCII sample identifiers
  - Data Stream: MPEG/CELT/ADPCM frames
Outputs:
  - targets/district-187/extracted/audio/<bank_name>/<sample_name>.<ext>
  - targets/district-187/data/audio_manifest.json
"""

import os
import sys
import struct
import json
import argparse
from typing import Dict, List, Any

# Ensure UTF-8 output
sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TARGET_DIR = os.path.join(BASE_DIR, "targets", "district-187")
AUDIO_OUT_DIR = os.path.join(TARGET_DIR, "extracted", "audio")
MANIFEST_JSON = os.path.join(TARGET_DIR, "data", "audio_manifest.json")

os.makedirs(AUDIO_OUT_DIR, exist_ok=True)
os.makedirs(os.path.dirname(MANIFEST_JSON), exist_ok=True)

# FMOD FSB5 Codec Table
CODEC_NAMES = {
    0: "NONE",
    1: "PCM8",
    2: "PCM16",
    3: "PCM24",
    4: "PCM32",
    5: "PCMFLOAT",
    6: "GCADPCM",
    7: "IMAADPCM",
    8: "VAG",
    9: "HEVAG",
    10: "XMA",
    11: "MPEG",
    12: "CELT",
    13: "AT9",
    14: "XWMA",
    15: "VORBIS",
    16: "FADPCM"
}

def parse_fsb5(file_path: str, extract_payloads: bool = True) -> Dict[str, Any]:
    if not os.path.exists(file_path):
        print(f"[-] File not found: {file_path}")
        return {}

    bank_name = os.path.splitext(os.path.basename(file_path))[0]
    file_size = os.path.getsize(file_path)

    with open(file_path, "rb") as f:
        data = f.read()

    if data[:4] != b"FSB5":
        print(f"[-] Not an FSB5 file: {file_path}")
        return {}

    magic, ver, num_samples, sample_hdr_sz, name_tbl_sz, data_sz, mode = struct.unpack('<4s6I', data[:28])
    codec_name = CODEC_NAMES.get(mode, f"UNKNOWN_{mode}")

    print(f"\n[+] Inspecting FSB5 SoundBank: {bank_name}.fsb ({file_size:,} bytes)")
    print(f"  Version: {ver} | Samples: {num_samples} | Codec: {codec_name} (ID {mode})")
    print(f"  Header Size: {sample_hdr_sz} | Name Table Size: {name_tbl_sz:,} | Data Size: {data_sz:,}")

    # Name Table
    name_table_off = 64 + sample_hdr_sz
    name_tbl = data[name_table_off:name_table_off+name_tbl_sz]

    sample_names = []
    if name_tbl_sz > 0 and len(name_tbl) >= num_samples * 4:
        offsets = struct.unpack(f"<{num_samples}I", name_tbl[:num_samples*4])
        for off in offsets:
            end = name_tbl.find(b"\x00", off)
            name = name_tbl[off:end].decode("ascii", errors="ignore") if end != -1 else f"sample_{len(sample_names):04d}"
            # Clean name
            clean_name = "".join(c if (c.isalnum() or c in "_-") else "_" for c in name).strip("_")
            if not clean_name:
                clean_name = f"sample_{len(sample_names):04d}"
            sample_names.append(clean_name)
    else:
        sample_names = [f"sample_{i:04d}" for i in range(num_samples)]

    # Parse Sample Headers (simplified slice division for extraction)
    data_off = 64 + sample_hdr_sz + name_tbl_sz
    raw_audio_data = data[data_off:data_off+data_sz]

    # Calculate average block per sample or extract full stream
    ext = "mp3" if mode == 11 or mode == 12 else "wav"
    out_bank_dir = os.path.join(AUDIO_OUT_DIR, bank_name)
    if extract_payloads:
        os.makedirs(out_bank_dir, exist_ok=True)

    samples_catalog = []
    avg_sample_size = data_sz // max(num_samples, 1)

    for i, name in enumerate(sample_names):
        s_off = i * avg_sample_size
        s_len = avg_sample_size if i < num_samples - 1 else (data_sz - s_off)
        sample_bytes = raw_audio_data[s_off:s_off+s_len]

        if extract_payloads and len(sample_bytes) > 0:
            out_file = os.path.join(out_bank_dir, f"{i:03d}_{name}.{ext}")
            with open(out_file, "wb") as f_out:
                f_out.write(sample_bytes)

        samples_catalog.append({
            "index": i,
            "name": name,
            "bank": bank_name,
            "codec": codec_name,
            "offset": data_off + s_off,
            "size": s_len
        })

    print(f"[+] Successfully cataloged and unpacked {len(samples_catalog)} audio samples into: {out_bank_dir}")
    return {
        "bank_name": bank_name,
        "codec": codec_name,
        "num_samples": num_samples,
        "total_data_bytes": data_sz,
        "samples": samples_catalog
    }

def main():
    parser = argparse.ArgumentParser(description="District 187 FSB5 Audio Extractor")
    parser.add_argument("--bank", help="Path or name of specific FSB SoundBank")
    parser.add_argument("--all", action="store_true", help="Extract all discovered FSB soundbanks")
    args = parser.parse_args()

    banks_to_process = []
    # Find all .fsb files
    search_dirs = [
        os.path.join(TARGET_DIR, "client-rebirth", "Game", "FMOD", "Data"),
        os.path.join(TARGET_DIR, "extracted", "weapons", "FMOD", "Data")
    ]

    for d in search_dirs:
        if os.path.exists(d):
            for f in os.listdir(d):
                if f.endswith(".fsb"):
                    banks_to_process.append(os.path.join(d, f))

    if not banks_to_process:
        print("[-] No FSB soundbanks found.")
        return

    all_manifest = {}
    print(f"[+] Found {len(banks_to_process)} FMOD SoundBanks to catalog.")

    total_extracted_samples = 0
    for bank_path in banks_to_process:
        res = parse_fsb5(bank_path, extract_payloads=True)
        if res:
            all_manifest[res["bank_name"]] = res
            total_extracted_samples += res["num_samples"]

    with open(MANIFEST_JSON, "w", encoding="utf-8") as f:
        json.dump(all_manifest, f, indent=2)

    print(f"\n=====================================================================")
    print(f"  AUDIO CATALOG COMPLETE: {total_extracted_samples} samples across {len(all_manifest)} banks")
    print(f"  Manifest written to: {MANIFEST_JSON}")
    print(f"=====================================================================")

if __name__ == "__main__":
    main()

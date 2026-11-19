#!/usr/bin/env python3
"""
District 187: Sin Streets — LithTech Jupiter EX Texture (.Tex00p / DTX) Header Dissector
Scans extracted .Tex00p / .dtx files in targets/district-187/extracted/ to catalog:
  - DTX header fields: res_type (0=Texture), version (-5 / -2), width, height, mipmaps, sections, flags, BPP/DXT format
  - Resolution & compression distribution (DXT1, DXT3, DXT5, RGBA8888, etc.)
Outputs:
  - targets/district-187/data/dtx_texture_catalog.json
  - notes/lithtech-dtx-texture-format.md
"""

import glob
import json
import os
import struct
import sys

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXTRACTED_DIR = os.path.join(ROOT_DIR, "targets", "district-187", "extracted")
OUT_JSON = os.path.join(ROOT_DIR, "targets", "district-187", "data", "dtx_texture_catalog.json")
OUT_NOTE = os.path.join(ROOT_DIR, "notes", "lithtech-dtx-texture-format.md")

BPP_NAMES = {
    0: "BPP_8P",
    1: "BPP_8",
    2: "BPP_16",
    3: "BPP_32 (ARGB8888)",
    4: "BPP_S3TC_DXT1",
    5: "BPP_S3TC_DXT3",
    6: "BPP_S3TC_DXT5",
    7: "BPP_32P",
}


def parse_dtx_header(path: str):
    with open(path, "rb") as f:
        hdr = f.read(32)
    if len(hdr) < 28:
        return None
    res_type, version, width, height, mipmaps, sections, flags, user_flags = struct.unpack_from("<IiHHHHII", hdr, 0)
    bpp_id = hdr[26] if len(hdr) > 26 else 0
    return {
        "file": os.path.relpath(path, EXTRACTED_DIR).replace("\\", "/"),
        "size": os.path.getsize(path),
        "res_type": res_type,
        "version": version,
        "width": width,
        "height": height,
        "mipmaps": mipmaps,
        "sections": sections,
        "flags": f"0x{flags:08x}",
        "bpp_id": bpp_id,
        "format": BPP_NAMES.get(bpp_id, f"Unknown({bpp_id})"),
    }


def parse_dds_header(path: str):
    with open(path, "rb") as f:
        hdr = f.read(128)
    if len(hdr) < 128 or hdr[:4] != b"DDS ":
        return None
    height, width, _, _, mipmaps = struct.unpack_from("<5I", hdr, 12)
    fourcc = hdr[84:88].decode("ascii", errors="ignore").strip("\x00") or "RGBA"
    return {
        "file": os.path.relpath(path, EXTRACTED_DIR).replace("\\", "/"),
        "size": os.path.getsize(path),
        "res_type": 0,
        "version": 124,
        "width": width,
        "height": height,
        "mipmaps": mipmaps,
        "sections": 0,
        "flags": "DDS",
        "bpp_id": 0,
        "format": f"DDS_{fourcc}",
    }


def main():
    files = glob.glob(os.path.join(EXTRACTED_DIR, "**", "*.Tex00p"), recursive=True)
    files += glob.glob(os.path.join(EXTRACTED_DIR, "**", "*.dtx"), recursive=True)
    dds_files = glob.glob(os.path.join(EXTRACTED_DIR, "**", "*.dds"), recursive=True)

    parsed = []
    res_dist = {}
    fmt_dist = {}
    ver_dist = {}

    for p in files:
        info = parse_dtx_header(p)
        if info:
            parsed.append(info)
    for p in dds_files:
        info = parse_dds_header(p)
        if info:
            parsed.append(info)

    for info in parsed:
        rkey = f"{info['width']}x{info['height']}"
        res_dist[rkey] = res_dist.get(rkey, 0) + 1
        fmt_dist[info["format"]] = fmt_dist.get(info["format"], 0) + 1
        ver_dist[str(info["version"])] = ver_dist.get(str(info["version"]), 0) + 1

    catalog = {
        "total_textures_scanned": len(parsed),
        "version_distribution": dict(sorted(ver_dist.items(), key=lambda kv: -kv[1])),
        "format_distribution": dict(sorted(fmt_dist.items(), key=lambda kv: -kv[1])),
        "top_resolutions": dict(sorted(res_dist.items(), key=lambda kv: -kv[1])[:20]),
        "sample_textures": parsed[:50],
    }

    os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(catalog, f, indent=2, ensure_ascii=False)

    lines = [
        "# Formato de Texturas LithTech Jupiter EX (`.Tex00p` / `DTX`)",
        "",
        f"Descoberto por: `agy` (2026-11-19) — Varredura estática em `{len(parsed)}` texturas extraídas de `targets/district-187/extracted/`.",
        "",
        "---",
        "",
        "## 1. Cabeçalho Binário DTX (`0x00..0x1F`, Little-Endian)",
        "| Offset | Tipo | Campo | Descrição |",
        "|---|---|---|---|",
        "| `+0x00` | `uint32` | `res_type` | `0` = Texture (`DTX`) |",
        "| `+0x04` | `int32` | `version` | Versão do formato DTX (ex: `-5` Jupiter EX) |",
        "| `+0x08` | `uint16` | `width` | Largura em pixels |",
        "| `+0x0A` | `uint16` | `height` | Altura em pixels |",
        "| `+0x0C` | `uint16` | `mipmaps` | Contagem de níveis de mipmap |",
        "| `+0x0E` | `uint16` | `sections` | Seções extras anexadas |",
        "| `+0x10` | `uint32` | `flags` | Flags DTX (Fullbright, 4444, CubeMap, etc.) |",
        "| `+0x14` | `uint32` | `user_flags` | Flags de usuário / material |",
        "| `+0x1A` | `uint8` | `bpp_id` | Formato de pixel (`3`=ARGB8888, `4`=DXT1, `5`=DXT3, `6`=DXT5) |",
        "",
        "## 2. Distribuição de Formatos & Resoluções",
        "| Formato | Qtd. Texturas |",
        "|---|---:|",
    ]
    for k, v in catalog["format_distribution"].items():
        lines.append(f"| `{k}` | {v} |")

    lines.extend([
        "",
        "### Top 10 Resoluções",
        "| Resolução | Qtd. Texturas |",
        "|---|---:|",
    ])
    for k, v in list(catalog["top_resolutions"].items())[:10]:
        lines.append(f"| `{k}` | {v} |")

    lines.extend([
        "",
        "## 3. Artefatos Relacionados",
        "- Dissector Python: [`scripts/inspect_dtx_textures.py`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/scripts/inspect_dtx_textures.py)",
        "- Catálogo JSON: [`targets/district-187/data/dtx_texture_catalog.json`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/targets/district-187/data/dtx_texture_catalog.json)",
        "",
    ])
    with open(OUT_NOTE, "w", encoding="utf-8") as nf:
        nf.write("\n".join(lines))

    print(f"[+] Scanned {len(parsed)} .Tex00p/.dtx textures! Formats: {catalog['format_distribution']}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()

#!/usr/bin/env python3
"""
District 187: Sin Streets — LithTech Jupiter EX Material (.Mat00) Cataloger
Scans extracted .Mat00 files in targets/district-187/extracted/ to extract referenced
shader effects (.fx/.fxc) and texture paths (.Tex00p/.dtx/.dds).
Outputs:
  - targets/district-187/data/mat00_catalog.json
"""

import glob
import json
import os
import re
import sys

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXTRACTED_DIR = os.path.join(ROOT_DIR, "targets", "district-187", "extracted")
OUT_JSON = os.path.join(ROOT_DIR, "targets", "district-187", "data", "mat00_catalog.json")


def main():
    files = glob.glob(os.path.join(EXTRACTED_DIR, "**", "*.Mat00"), recursive=True)
    shaders = {}
    textures = set()
    samples = []

    for p in files:
        with open(p, "rb") as f:
            raw = f.read()
        text = raw.decode("ascii", errors="ignore")
        fx_hits = re.findall(r"[A-Za-z0-9_\\/\-\.]+\.(?:fx|fxc)", text, flags=re.IGNORECASE)
        tex_hits = re.findall(r"[A-Za-z0-9_\\/\-\.]+\.(?:Tex00p|dtx|dds|tga)", text, flags=re.IGNORECASE)
        for fx in fx_hits:
            shaders[fx] = shaders.get(fx, 0) + 1
        for tx in tex_hits:
            textures.add(tx)
        if len(samples) < 40:
            samples.append({
                "file": os.path.relpath(p, EXTRACTED_DIR).replace("\\", "/"),
                "size": len(raw),
                "shaders": sorted(set(fx_hits)),
                "textures": sorted(set(tex_hits)),
            })

    result = {
        "total_mat00_files": len(files),
        "unique_shaders": len(shaders),
        "unique_referenced_textures": len(textures),
        "top_shaders": dict(sorted(shaders.items(), key=lambda kv: -kv[1])[:25]),
        "sample_materials": samples,
    }

    os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"[+] Cataloged {len(files)} .Mat00 materials ({len(shaders)} unique shaders, {len(textures)} unique textures)!")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()

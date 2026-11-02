#!/usr/bin/env python3
"""
Convert LithTech Jupiter EX MODL v33 (.Model00p) 3D meshes to Wavefront OBJ + MTL + PNG Textures.
Specifically reversed for District 187: Sin Streets (S2 Online).

Extracts:
- 3D Geometry (Vertices XYZ)
- Normals (Nx, Ny, Nz)
- UV Coordinates (U, V)
- Face / Triangle index buffer
- Generates .mtl material file and converts matching DDS texture to PNG via Pillow

Author: Gleidison Carvalho & Antigravity (2026-11-02)
"""
import argparse
import os
import struct
import sys
from PIL import Image

def find_texture_for_model(model_name, textures_dir):
    """Search for a matching diffuse texture (e.g. AR_AK47 -> AR_AK47_D.dds or AK47.dds)."""
    if not os.path.exists(textures_dir):
        return None
        
    base = os.path.splitext(model_name)[0]
    # Clean prefixes like MAR_M_, AR_M_, SG_M_, PV_
    clean_base = base
    for prefix in ["MAR_M_", "AR_M_", "SG_M_", "SMG_M_", "SN_M_", "PV_MAR_", "PV_AR_", "PV_SG_", "PV_SMG_", "PV_SN_", "PV_", "Custom_"]:
        if clean_base.startswith(prefix):
            clean_base = clean_base[len(prefix):]
            break
            
    candidates = [
        f"{base}_D.dds",
        f"{base}.dds",
        f"{clean_base}_D.dds",
        f"{clean_base}.dds",
        f"AR_{clean_base}_D.dds",
        f"MAR_{clean_base}_D.dds",
        f"SMG_{clean_base}_D.dds",
        f"SN_{clean_base}_D.dds",
        f"SG_{clean_base}_D.dds",
    ]
    
    for root, dirs, files in os.walk(textures_dir):
        file_map = {f.lower(): f for f in files}
        for cand in candidates:
            if cand.lower() in file_map:
                return os.path.join(root, file_map[cand.lower()])
    return None

def convert_model(model_path, obj_path, textures_dir=None):
    with open(model_path, "rb") as f:
        data = f.read()

    if len(data) < 64 or data[:4] != b"MODL":
        return False, "Not a valid MODL file"

    version, = struct.unpack("<I", data[4:8])
    if version != 33: # 0x21
        return False, f"Unsupported version: {version}"

    # Search for vertex stream
    stride = 72
    v_start = -1
    
    for cand in range(0x100, min(len(data) - stride * 10, 0x10000), 1):
        valid = 0
        p = cand
        while p + stride <= len(data) and valid < 10:
            nx, ny, nz = struct.unpack("<3f", data[p+12 : p+24])
            norm_len = (nx*nx + ny*ny + nz*nz)**0.5
            if 0.90 <= norm_len <= 1.10:
                valid += 1
                p += stride
            else:
                break
        if valid >= 10:
            v_start = cand
            break

    if v_start == -1:
        return False, "Could not find vertex buffer stream"

    # Read vertices
    pos = v_start
    verts = []
    normals = []
    uvs = []

    while pos + stride <= len(data):
        chunk = data[pos:pos+stride]
        x, y, z = struct.unpack("<3f", chunk[:12])
        nx, ny, nz = struct.unpack("<3f", chunk[12:24])
        norm_len = (nx*nx + ny*ny + nz*nz)**0.5
        if not (0.85 <= norm_len <= 1.15):
            break
        u, v = struct.unpack("<2f", chunk[24:32])
        
        # Guard against absurd coordinates
        if abs(x) > 5000 or abs(y) > 5000 or abs(z) > 5000:
            break

        verts.append((x, y, z))
        normals.append((nx, ny, nz))
        uvs.append((u, 1.0 - v))
        pos += stride

    num_verts = len(verts)
    if num_verts < 3:
        return False, f"Too few vertices ({num_verts})"

    # Read index buffer: search for largest span of uint16 indices < num_verts
    best_start = -1
    max_indices = 0
    search_start = pos
    
    # Check directly at pos first
    p = pos
    count = 0
    while p + 2 <= len(data):
        idx, = struct.unpack("<H", data[p:p+2])
        if idx >= num_verts:
            break
        count += 1
        p += 2
    if count >= 30:
        best_start = pos
        max_indices = count
    else:
        # Scan forward for the index buffer
        for cand in range(pos, min(len(data) - 60, pos + 0x40000), 2):
            count = 0
            p = cand
            while p + 2 <= len(data):
                idx, = struct.unpack("<H", data[p:p+2])
                if idx >= num_verts:
                    break
                count += 1
                p += 2
            if count > max_indices and count >= 30:
                max_indices = count
                best_start = cand
                if count > 500: # Found a very solid buffer
                    break

    indices = []
    if best_start != -1:
        p = best_start
        for _ in range(max_indices):
            idx, = struct.unpack("<H", data[p:p+2])
            indices.append(idx)
            p += 2

    num_triangles = len(indices) // 3
    if num_triangles < 1:
        return False, "No valid faces found in index buffer"

    model_name = os.path.splitext(os.path.basename(model_path))[0]
    out_dir = os.path.dirname(obj_path)
    os.makedirs(out_dir, exist_ok=True)
    
    # Try finding and converting texture
    tex_png_name = None
    if textures_dir:
        dds_tex = find_texture_for_model(model_name, textures_dir)
        if dds_tex:
            tex_png_name = f"{model_name}_D.png"
            dest_png = os.path.join(out_dir, tex_png_name)
            try:
                img = Image.open(dds_tex)
                img.save(dest_png, "PNG")
            except Exception:
                tex_png_name = None

    # Write MTL file
    mtl_filename = f"{model_name}.mtl"
    mtl_path = os.path.join(out_dir, mtl_filename)
    mat_name = f"{model_name}_Material"
    
    with open(mtl_path, "w", encoding="utf-8") as f_mtl:
        f_mtl.write(f"# Material for {model_name}\n")
        f_mtl.write(f"newmtl {mat_name}\n")
        f_mtl.write("Ka 1.000000 1.000000 1.000000\n")
        f_mtl.write("Kd 1.000000 1.000000 1.000000\n")
        f_mtl.write("Ks 0.500000 0.500000 0.500000\n")
        f_mtl.write("Ns 30.000000\n")
        f_mtl.write("illum 2\n")
        if tex_png_name:
            f_mtl.write(f"map_Kd {tex_png_name}\n")

    # Write OBJ file
    with open(obj_path, "w", encoding="utf-8") as out:
        out.write(f"# Converted from District 187: {os.path.basename(model_path)}\n")
        out.write(f"# Vertices: {num_verts}, Triangles: {num_triangles}\n")
        out.write(f"mtllib {mtl_filename}\n")
        out.write(f"o {model_name}\n\n")

        for x, y, z in verts:
            out.write(f"v {x:.6f} {y:.6f} {z:.6f}\n")
            
        for u, v in uvs:
            out.write(f"vt {u:.6f} {v:.6f}\n")
            
        for nx, ny, nz in normals:
            out.write(f"vn {nx:.6f} {ny:.6f} {nz:.6f}\n")

        out.write(f"\nusemtl {mat_name}\n")
        out.write("s 1\n")
        for t in range(num_triangles):
            i0 = indices[t*3] + 1
            i1 = indices[t*3 + 1] + 1
            i2 = indices[t*3 + 2] + 1
            out.write(f"f {i0}/{i0}/{i0} {i1}/{i1}/{i1} {i2}/{i2}/{i2}\n")

    tex_status = f"+ texture {tex_png_name}" if tex_png_name else "(no texture)"
    return True, f"Success ({num_verts} verts, {num_triangles} tris {tex_status})"

def main():
    parser = argparse.ArgumentParser(description="Convert LithTech Model00p to Wavefront OBJ + MTL + PNG")
    parser.add_argument("--src", required=True, help="Source .Model00p file or folder")
    parser.add_argument("--out", required=True, help="Destination .obj file or folder")
    parser.add_argument("--textures", help="Folder containing extracted .dds textures for automatic pairing")
    args = parser.parse_args()

    if os.path.isfile(args.src):
        ok, msg = convert_model(args.src, args.out, textures_dir=args.textures)
        print(f"[{'OK' if ok else 'FAIL'}] {args.src} -> {msg}")
    elif os.path.isdir(args.src):
        os.makedirs(args.out, exist_ok=True)
        count = 0
        for root, dirs, files in os.walk(args.src):
            for file in files:
                if file.lower().endswith(".model00p"):
                    src_f = os.path.join(root, file)
                    rel = os.path.relpath(src_f, args.src)
                    out_f = os.path.join(args.out, os.path.splitext(rel)[0] + ".obj")
                    ok, msg = convert_model(src_f, out_f, textures_dir=args.textures)
                    if ok:
                        count += 1
                        print(f"[CONVERTED] {file} ({msg})")
        print(f"\n[DONE] Successfully converted {count} models to OBJ!")

if __name__ == "__main__":
    main()

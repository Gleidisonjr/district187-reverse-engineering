#!/usr/bin/env python3
"""
ML Model Format RE — Pure-Python GGUF v3 (.gguf) & Safetensors (.safetensors)
Generator & Byte-Level Binary Dissector (Zero external dependencies).

1. GGUF v3 (llama.cpp):
   - Magic: b"GGUF" (4B), version: uint32 (3), tensor_count: uint64, metadata_kv_count: uint64
   - Metadata KV entries: gguf_string(key) + value_type(u32) + typed_value
   - Tensor infos: gguf_string(name) + n_dims(u32) + dims(u64[n_dims]) + ggml_type(u32) + offset(u64)
   - Alignment padding to 32 bytes + contiguous tensor payload
2. Safetensors (Hugging Face):
   - header_size: uint64 LE
   - UTF-8 JSON header mapping tensor names -> {dtype, shape, data_offsets: [start, end]}
   - Raw contiguous tensor buffer (zero-copy mmap safe, no pickle arbitrary code execution)
"""

import json
import os
import struct
import sys

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT_DIR, "targets", "ml-model-format-re", "data")
OUT_GGUF = os.path.join(DATA_DIR, "tiny_llm_sample.gguf")
OUT_SAFE = os.path.join(DATA_DIR, "tiny_llm_sample.safetensors")

GGUF_TYPES = {4: "UINT32", 6: "FLOAT32", 8: "STRING"}
GGML_TYPES = {0: "F32", 1: "F16", 2: "Q4_0", 8: "Q8_0", 12: "Q4_K"}


def _gguf_str(s: str) -> bytes:
    b = s.encode("utf-8")
    return struct.pack("<Q", len(b)) + b


def generate_sample_gguf(path: str) -> int:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    kv = [
        ("general.architecture", 8, "llama"),
        ("general.name", 8, "TinyRE-Llama-Sample"),
        ("llama.block_count", 4, 2),
        ("llama.embedding_length", 4, 64),
        ("llama.attention.layer_norm_rms_epsilon", 6, 1e-5),
    ]
    w0 = struct.pack("<4f", 0.25, -0.5, 0.75, 1.0)  # 16 bytes
    w1 = struct.pack("<4f", 0.1, 0.2, 0.3, 0.4)     # 16 bytes

    out = bytearray()
    out += struct.pack("<4sIQQ", b"GGUF", 3, 2, len(kv))
    for k, vtype, val in kv:
        out += _gguf_str(k) + struct.pack("<I", vtype)
        if vtype == 8:
            out += _gguf_str(val)
        elif vtype == 4:
            out += struct.pack("<I", val)
        elif vtype == 6:
            out += struct.pack("<f", val)

    # Tensor descriptors: (name, dims, ggml_type=0 F32, rel_offset)
    out += _gguf_str("blk.0.attn_q.weight") + struct.pack("<I2QIQ", 2, 2, 2, 0, 0)
    out += _gguf_str("blk.0.attn_k.weight") + struct.pack("<I2QIQ", 2, 2, 2, 0, 16)

    # Align to 32-byte boundary before tensor data
    rem = len(out) % 32
    if rem:
        out += b"\x00" * (32 - rem)
    out += w0 + w1

    with open(path, "wb") as f:
        f.write(out)
    return len(out)


def dissect_gguf(path: str) -> dict:
    with open(path, "rb") as f:
        data = f.read()

    magic, ver, n_tensors, n_kv = struct.unpack_from("<4sIQQ", data, 0)
    assert magic == b"GGUF" and ver == 3, f"Invalid GGUF: {magic!r} v{ver}"
    pos = 24

    def read_str():
        nonlocal pos
        slen = struct.unpack_from("<Q", data, pos)[0]
        pos += 8
        s = data[pos : pos + slen].decode("utf-8", errors="replace")
        pos += slen
        return s

    metadata = {}
    for _ in range(n_kv):
        k = read_str()
        vtype = struct.unpack_from("<I", data, pos)[0]
        pos += 4
        if vtype == 8:
            val = read_str()
        elif vtype == 4:
            val = struct.unpack_from("<I", data, pos)[0]
            pos += 4
        elif vtype == 6:
            val = round(struct.unpack_from("<f", data, pos)[0], 7)
            pos += 4
        else:
            raise ValueError(f"Unsupported GGUF KV type: {vtype}")
        metadata[k] = val

    tensors = []
    for _ in range(n_tensors):
        name = read_str()
        n_dims = struct.unpack_from("<I", data, pos)[0]
        pos += 4
        dims = list(struct.unpack_from(f"<{n_dims}Q", data, pos))
        pos += 8 * n_dims
        gtype, rel_off = struct.unpack_from("<IQ", data, pos)
        pos += 12
        tensors.append({"name": name, "dims": dims, "dtype": GGML_TYPES.get(gtype, str(gtype)), "rel_offset": rel_off})

    rem = pos % 32
    data_start = pos + (32 - rem if rem else 0)
    first_vals = list(struct.unpack_from("<4f", data, data_start))
    return {
        "file_size": len(data),
        "version": ver,
        "metadata": metadata,
        "tensors": tensors,
        "tensor_data_offset": data_start,
        "sample_f32_values": first_vals,
    }


def generate_sample_safetensors(path: str) -> int:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    w0 = struct.pack("<4f", 0.25, -0.5, 0.75, 1.0)
    w1 = struct.pack("<4f", 0.1, 0.2, 0.3, 0.4)
    header_obj = {
        "__metadata__": {"format": "pt", "architecture": "TinyRE-Llama-Sample"},
        "blk.0.attn_q.weight": {"dtype": "F32", "shape": [2, 2], "data_offsets": [0, 16]},
        "blk.0.attn_k.weight": {"dtype": "F32", "shape": [2, 2], "data_offsets": [16, 32]},
    }
    hdr_bytes = json.dumps(header_obj, separators=(",", ":")).encode("utf-8")
    out = struct.pack("<Q", len(hdr_bytes)) + hdr_bytes + w0 + w1
    with open(path, "wb") as f:
        f.write(out)
    return len(out)


def dissect_safetensors(path: str) -> dict:
    with open(path, "rb") as f:
        data = f.read()
    hdr_len = struct.unpack_from("<Q", data, 0)[0]
    hdr = json.loads(data[8 : 8 + hdr_len].decode("utf-8"))
    data_start = 8 + hdr_len
    meta = hdr.pop("__metadata__", {})
    sample = list(struct.unpack_from("<4f", data, data_start))
    return {
        "file_size": len(data),
        "header_bytes": hdr_len,
        "metadata": meta,
        "tensor_count": len(hdr),
        "tensors": hdr,
        "sample_f32_values": sample,
    }


def main():
    generate_sample_gguf(OUT_GGUF)
    g = dissect_gguf(OUT_GGUF)
    print(f"[+] GGUF v{g['version']} dissected ({g['file_size']} B, data_off=0x{g['tensor_data_offset']:X}):")
    print(f"    arch={g['metadata']['general.architecture']} tensors={len(g['tensors'])} sample_f32={g['sample_f32_values']}")

    generate_sample_safetensors(OUT_SAFE)
    s = dissect_safetensors(OUT_SAFE)
    print(f"[+] Safetensors dissected ({s['file_size']} B, hdr={s['header_bytes']} B):")
    print(f"    meta={s['metadata']} tensors={s['tensor_count']} sample_f32={s['sample_f32_values']}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()

#!/usr/bin/env python3
"""
Columnar Storage RE — Pure-Python Apache Arrow IPC File Format (.arrow / Feather v2)
Generator & Byte-Level FlatBuffer Dissector (Zero external dependencies).

Binary layout of Arrow IPC File Format:
  1. Magic Header (8 bytes): b"ARROW1\\x00\\x00"
  2. Encapsulated Message Stream:
       - Continuation token: 0xFFFFFFFF (uint32 LE)
       - Metadata length: int32 LE (padded to 8-byte boundary)
       - FlatBuffer Message table (Schema, DictionaryBatch, or RecordBatch)
       - Body buffers (64-byte aligned in memory / 8-byte aligned on disk)
  3. End-of-Stream Marker (8 bytes): 0xFFFFFFFF + 0x00000000
  4. FlatBuffer Footer table (version, schema, recordBatches[])
  5. Footer length (int32 LE) + Trailing Magic (6 bytes): b"ARROW1"
"""

import os
import struct
import sys

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_ARROW = os.path.join(ROOT_DIR, "targets", "columnar-storage-re", "data", "telemetry_sample.arrow")


def pad8(data: bytes) -> bytes:
    rem = len(data) % 8
    return data if rem == 0 else data + b"\x00" * (8 - rem)


def build_minimal_flatbuffer_table(fields_u32: list) -> bytes:
    """
    Constructs a minimal, valid little-endian FlatBuffer root table with `len(fields_u32)` uint32 scalar fields:
      [root_offset: u32 -> table]
      [vtable: vtable_size(u16), table_size(u16), field_offsets(u16)...]
      [table: soffset32_to_vtable(i32), field_values(u32)...]
    """
    n = len(fields_u32)
    vtable_size = 4 + 2 * n
    table_size = 4 + 4 * n
    # Place vtable at offset 4, table right after vtable (aligned to 4)
    vtable_off = 4
    table_off = vtable_off + vtable_size
    if table_off % 4 != 0:
        table_off += 4 - (table_off % 4)

    buf = bytearray(table_off + table_size)
    struct.pack_into("<I", buf, 0, table_off)
    struct.pack_into("<HH", buf, vtable_off, vtable_size, table_size)
    for i in range(n):
        struct.pack_into("<H", buf, vtable_off + 4 + i * 2, 4 + i * 4)

    # Table: soffset32 = table_off - vtable_off (positive because vtable precedes table)
    struct.pack_into("<i", buf, table_off, table_off - vtable_off)
    for i, val in enumerate(fields_u32):
        struct.pack_into("<I", buf, table_off + 4 + i * 4, val)
    return bytes(buf)


def read_flatbuffer_table(buf: bytes) -> dict:
    root_off = struct.unpack_from("<I", buf, 0)[0]
    vtable_rel = struct.unpack_from("<i", buf, root_off)[0]
    vtable_off = root_off - vtable_rel
    vtable_size, table_size = struct.unpack_from("<HH", buf, vtable_off)
    n_fields = (vtable_size - 4) // 2
    fields = []
    for i in range(n_fields):
        f_off = struct.unpack_from("<H", buf, vtable_off + 4 + i * 2)[0]
        if f_off == 0:
            fields.append(None)
        else:
            fields.append(struct.unpack_from("<I", buf, root_off + f_off)[0])
    return {
        "root_offset": root_off,
        "vtable_offset": vtable_off,
        "vtable_size": vtable_size,
        "table_size": table_size,
        "fields": fields,
    }


def generate_sample_arrow(path: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    out = bytearray()
    out += b"ARROW1\x00\x00"  # 8-byte magic header

    # Message 1: Schema (version=4 V5, header_type=1 Schema, bodyLength=0)
    schema_fb = pad8(build_minimal_flatbuffer_table([4, 1, 0]))
    out += struct.pack("<Ii", 0xFFFFFFFF, len(schema_fb))
    out += schema_fb

    # Message 2: RecordBatch (version=4 V5, header_type=3 RecordBatch, bodyLength=64)
    # Body: 8 rows x int64 timestamps (64 bytes)
    body = struct.pack("<8q", *[1700000000 + i * 60 for i in range(8)])
    rb_offset = len(out)
    rb_fb = pad8(build_minimal_flatbuffer_table([4, 3, len(body)]))
    out += struct.pack("<Ii", 0xFFFFFFFF, len(rb_fb))
    out += rb_fb
    out += body

    # End-of-Stream marker
    out += struct.pack("<II", 0xFFFFFFFF, 0)

    # Footer FlatBuffer (version=4 V5, num_record_batches=1, rb_offset, rb_meta_len, rb_body_len)
    footer_fb = build_minimal_flatbuffer_table([4, 1, rb_offset, 8 + len(rb_fb), len(body)])
    out += footer_fb
    out += struct.pack("<i", len(footer_fb))
    out += b"ARROW1"

    with open(path, "wb") as f:
        f.write(out)
    return len(out)


def dissect_arrow_ipc(path: str) -> dict:
    with open(path, "rb") as f:
        data = f.read()

    assert data[:8] == b"ARROW1\x00\x00", "Invalid Arrow IPC leading magic!"
    assert data[-6:] == b"ARROW1", "Invalid Arrow IPC trailing magic!"
    footer_len = struct.unpack_from("<i", data, len(data) - 10)[0]
    footer_start = len(data) - 10 - footer_len
    footer_parsed = read_flatbuffer_table(data[footer_start : footer_start + footer_len])

    pos = 8
    messages = []
    msg_types = {1: "Schema", 2: "DictionaryBatch", 3: "RecordBatch", 4: "Tensor"}
    while pos + 8 <= footer_start:
        cont, meta_len = struct.unpack_from("<Ii", data, pos)
        pos += 8
        assert cont == 0xFFFFFFFF, f"Expected continuation 0xFFFFFFFF at {pos-8}, got 0x{cont:08X}"
        if meta_len == 0:
            break  # End-of-stream marker
        meta_fb = read_flatbuffer_table(data[pos : pos + meta_len])
        pos += meta_len
        ver, htype, body_len = meta_fb["fields"][:3]
        body_bytes = data[pos : pos + body_len]
        pos += body_len
        messages.append({
            "version": ver,
            "header_type": msg_types.get(htype, f"Type({htype})"),
            "metadata_len": meta_len,
            "body_len": body_len,
            "flatbuffer": meta_fb,
            "sample_i64_values": list(struct.unpack_from("<8q", body_bytes, 0)) if body_len == 64 else [],
        })

    return {
        "file_size": len(data),
        "leading_magic": data[:6].decode("ascii"),
        "trailing_magic": data[-6:].decode("ascii"),
        "footer_len": footer_len,
        "footer_flatbuffer": footer_parsed,
        "message_count": len(messages),
        "messages": messages,
    }


def main():
    sz = generate_sample_arrow(OUT_ARROW)
    info = dissect_arrow_ipc(OUT_ARROW)
    print(f"[+] Generated & dissected Apache Arrow IPC file: {os.path.relpath(OUT_ARROW, ROOT_DIR)} ({sz} B)")
    print(f"    Magic: {info['leading_magic']}..{info['trailing_magic']} | Footer: {info['footer_len']} B | Messages: {info['message_count']}")
    for m in info["messages"]:
        print(f"    - {m['header_type']} (meta={m['metadata_len']}B, body={m['body_len']}B) values={m['sample_i64_values'][:3]}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()

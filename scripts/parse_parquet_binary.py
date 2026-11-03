#!/usr/bin/env python3
"""
Apache Parquet Binary Dissector & Reverse Engineering Parser
Pure-Python low-level byte inspector for Apache Parquet files.

Decodes:
  - 4-byte Magic Number (PAR1) at file start and end
  - Footer length (little-endian uint32 at offset -8)
  - Thrift Compact Protocol FileMetaData:
      * Schema hierarchy (SchemaElement, Types, Repetition)
      * Row groups count and record count
      * Column chunks, offsets, and compression codecs (SNAPPY, ZSTD, PLAIN)
      * Encodings (PLAIN, RLE_DICTIONARY, DELTA_BINARY_PACKED)
      * Column statistics (min, max, null_count)
"""

import os
import sys
import struct
import argparse
from typing import Dict, List, Any, Tuple, Optional

# Ensure UTF-8 output
sys.stdout.reconfigure(encoding='utf-8')

PARQUET_MAGIC = b"PAR1"

COMPRESSION_CODECS = {
    0: "UNCOMPRESSED",
    1: "SNAPPY",
    2: "GZIP",
    3: "LZO",
    4: "BROTLI",
    5: "LZ4",
    6: "ZSTD"
}

PHYSICAL_TYPES = {
    0: "BOOLEAN",
    1: "INT32",
    2: "INT64",
    3: "INT96",
    4: "FLOAT",
    5: "DOUBLE",
    6: "BYTE_ARRAY",
    7: "FIXED_LEN_BYTE_ARRAY"
}

ENCODINGS = {
    0: "PLAIN",
    1: "PLAIN_DICTIONARY",
    2: "RLE",
    3: "BIT_PACKED",
    4: "DELTA_BINARY_PACKED",
    5: "DELTA_LENGTH_BYTE_ARRAY",
    6: "DELTA_BYTE_ARRAY",
    7: "RLE_DICTIONARY",
    8: "BYTE_STREAM_SPLIT"
}

# Thrift Compact Protocol Types
CTYPE_STOP   = 0x00
CTYPE_TRUE   = 0x01
CTYPE_FALSE  = 0x02
CTYPE_BYTE   = 0x03
CTYPE_I16    = 0x04
CTYPE_I32    = 0x05
CTYPE_I64    = 0x06
CTYPE_DOUBLE = 0x07
CTYPE_BINARY = 0x08
CTYPE_LIST   = 0x09
CTYPE_SET    = 0x0A
CTYPE_MAP    = 0x0B
CTYPE_STRUCT = 0x0C

class CompactProtocolReader:
    def __init__(self, data: bytes):
        self.data = data
        self.pos = 0

    def read_byte(self) -> int:
        if self.pos >= len(self.data):
            raise EOFError("Unexpected end of Thrift stream")
        b = self.data[self.pos]
        self.pos += 1
        return b

    def read_varint(self) -> int:
        """Reads unsigned LEB128 varint."""
        res = 0
        shift = 0
        while True:
            b = self.read_byte()
            res |= (b & 0x7F) << shift
            if not (b & 0x80):
                break
            shift += 7
        return res

    def read_zigzag(self) -> int:
        n = self.read_varint()
        return (n >> 1) ^ (-(n & 1))

    def read_binary(self) -> bytes:
        length = self.read_varint()
        if self.pos + length > len(self.data):
            raise EOFError("Binary length exceeds buffer")
        buf = self.data[self.pos : self.pos + length]
        self.pos += length
        return buf

    def read_string(self) -> str:
        raw = self.read_binary()
        try:
            return raw.decode("utf-8")
        except UnicodeDecodeError:
            return raw.decode("latin1", errors="replace")

    def skip(self, ctype: int):
        if ctype in (CTYPE_TRUE, CTYPE_FALSE):
            return
        elif ctype == CTYPE_BYTE:
            self.read_byte()
        elif ctype in (CTYPE_I16, CTYPE_I32, CTYPE_I64):
            self.read_zigzag()
        elif ctype == CTYPE_DOUBLE:
            self.pos += 8
        elif ctype == CTYPE_BINARY:
            length = self.read_varint()
            self.pos += length
        elif ctype in (CTYPE_LIST, CTYPE_SET):
            hdr = self.read_byte()
            size = (hdr >> 4) & 0x0F
            elem_type = hdr & 0x0F
            if size == 0x0F:
                size = self.read_varint()
            for _ in range(size):
                self.skip(elem_type)
        elif ctype == CTYPE_MAP:
            size = self.read_varint()
            if size > 0:
                hdr = self.read_byte()
                ktype = (hdr >> 4) & 0x0F
                vtype = hdr & 0x0F
                for _ in range(size):
                    self.skip(ktype)
                    self.skip(vtype)
        elif ctype == CTYPE_STRUCT:
            last_id = 0
            while True:
                hdr = self.read_byte()
                if hdr == CTYPE_STOP:
                    break
                t = hdr & 0x0F
                delta = (hdr >> 4) & 0x0F
                if delta == 0:
                    last_id = self.read_zigzag()
                else:
                    last_id += delta
                self.skip(t)

    def read_struct_raw(self) -> Dict[int, Tuple[int, Any]]:
        fields = {}
        last_id = 0
        while True:
            hdr = self.read_byte()
            if hdr == CTYPE_STOP:
                break
            t = hdr & 0x0F
            delta = (hdr >> 4) & 0x0F
            if delta == 0:
                last_id = self.read_zigzag()
            else:
                last_id += delta

            # Extract basic primitives
            if t == CTYPE_TRUE:
                val = True
            elif t == CTYPE_FALSE:
                val = False
            elif t == CTYPE_BYTE:
                val = self.read_byte()
            elif t in (CTYPE_I16, CTYPE_I32, CTYPE_I64):
                val = self.read_zigzag()
            elif t == CTYPE_BINARY:
                val = self.read_binary()
            elif t == CTYPE_STRUCT:
                val = self.read_struct_raw()
            elif t in (CTYPE_LIST, CTYPE_SET):
                l_hdr = self.read_byte()
                l_size = (l_hdr >> 4) & 0x0F
                elem_type = l_hdr & 0x0F
                if l_size == 0x0F:
                    l_size = self.read_varint()
                items = []
                for _ in range(l_size):
                    if elem_type == CTYPE_STRUCT:
                        items.append(self.read_struct_raw())
                    elif elem_type == CTYPE_BINARY:
                        items.append(self.read_binary())
                    elif elem_type in (CTYPE_I16, CTYPE_I32, CTYPE_I64):
                        items.append(self.read_zigzag())
                    else:
                        self.skip(elem_type)
                        items.append("<skipped>")
                val = items
            else:
                self.skip(t)
                val = "<skipped>"

            fields[last_id] = (t, val)
        return fields

class ParquetBinaryDissector:
    def __init__(self, filepath: str):
        self.filepath = filepath
        self.file_size = os.path.getsize(filepath)

    def dissect(self) -> Dict[str, Any]:
        with open(self.filepath, "rb") as f:
            # 1. Header Magic
            head_magic = f.read(4)
            if head_magic != PARQUET_MAGIC:
                raise ValueError(f"Invalid header magic: {head_magic} (expected {PARQUET_MAGIC})")

            # 2. Footer Magic & Length
            f.seek(self.file_size - 4)
            foot_magic = f.read(4)
            if foot_magic != PARQUET_MAGIC:
                raise ValueError(f"Invalid footer magic: {foot_magic} (expected {PARQUET_MAGIC})")

            f.seek(self.file_size - 8)
            metadata_len_bytes = f.read(4)
            metadata_len = struct.unpack("<I", metadata_len_bytes)[0]

            metadata_offset = self.file_size - 8 - metadata_len
            f.seek(metadata_offset)
            raw_metadata = f.read(metadata_len)

        # 3. Parse FileMetaData via Thrift Compact Protocol
        reader = CompactProtocolReader(raw_metadata)
        root = reader.read_struct_raw()

        # Parquet FileMetaData Thrift Definition:
        # 1: version (i32)
        # 2: schema (list<SchemaElement>)
        # 3: num_rows (i64)
        # 4: row_groups (list<RowGroup>)
        # 5: key_value_metadata (list<KeyValue>)
        # 6: created_by (string)
        version = root.get(1, (0, 0))[1]
        schema_raw = root.get(2, (0, []))[1]
        num_rows = root.get(3, (0, 0))[1]
        row_groups_raw = root.get(4, (0, []))[1]
        created_by_raw = root.get(6, (0, b""))[1]
        created_by = created_by_raw.decode("utf-8", errors="ignore") if isinstance(created_by_raw, bytes) else str(created_by_raw)

        # Parse Schema Elements
        # SchemaElement:
        # 1: type (Type)
        # 2: type_length (i32)
        # 3: repetition_type (FieldRepetitionType)
        # 4: name (string)
        # 5: num_children (i32)
        schema_elements = []
        for se in schema_raw:
            if isinstance(se, dict):
                p_type = se.get(1, (0, None))[1]
                p_name_raw = se.get(4, (0, b"root"))[1]
                p_name = p_name_raw.decode("utf-8", errors="ignore") if isinstance(p_name_raw, bytes) else str(p_name_raw)
                num_children = se.get(5, (0, None))[1]
                schema_elements.append({
                    "name": p_name,
                    "physical_type": PHYSICAL_TYPES.get(p_type, f"TYPE_{p_type}") if p_type is not None else "RECORD_ROOT",
                    "num_children": num_children
                })

        # Parse Row Groups
        # RowGroup:
        # 1: columns (list<ColumnChunk>)
        # 2: total_byte_size (i64)
        # 3: num_rows (i64)
        row_groups = []
        for rg_idx, rg in enumerate(row_groups_raw):
            if isinstance(rg, dict):
                cols_raw = rg.get(1, (0, []))[1]
                rg_bytes = rg.get(2, (0, 0))[1]
                rg_rows = rg.get(3, (0, 0))[1]

                columns = []
                for c_chunk in cols_raw:
                    if isinstance(c_chunk, dict):
                        # 3: meta_data (ColumnMetaData)
                        # ColumnMetaData:
                        # 1: type (Type)
                        # 2: encodings (list<Encoding>)
                        # 3: path_in_schema (list<string>)
                        # 4: codec (CompressionCodec)
                        # 5: num_values (i64)
                        # 6: total_uncompressed_size (i64)
                        # 7: total_compressed_size (i64)
                        # 8: data_page_offset (i64)
                        # 9: index_page_offset (i64)
                        # 10: dictionary_page_offset (i64)
                        # 11: statistics (Statistics)
                        meta = c_chunk.get(3, (0, {}))[1]
                        if isinstance(meta, dict):
                            c_type = meta.get(1, (0, None))[1]
                            encs_raw = meta.get(2, (0, []))[1]
                            path_raw = meta.get(3, (0, []))[1]
                            col_name = ".".join([p.decode("utf-8", errors="ignore") if isinstance(p, bytes) else str(p) for p in path_raw])
                            codec_id = meta.get(4, (0, 0))[1]
                            uncomp_size = meta.get(6, (0, 0))[1]
                            comp_size = meta.get(7, (0, 0))[1]
                            data_offset = meta.get(8, (0, 0))[1]
                            dict_offset = meta.get(10, (0, None))[1]

                            columns.append({
                                "column_name": col_name,
                                "type": PHYSICAL_TYPES.get(c_type, f"TYPE_{c_type}"),
                                "codec": COMPRESSION_CODECS.get(codec_id, f"CODEC_{codec_id}"),
                                "encodings": [ENCODINGS.get(e, f"ENC_{e}") for e in encs_raw if isinstance(e, int)],
                                "uncompressed_bytes": uncomp_size,
                                "compressed_bytes": comp_size,
                                "compression_ratio": round(uncomp_size / comp_size, 2) if comp_size > 0 else 1.0,
                                "data_page_offset": data_offset,
                                "dictionary_page_offset": dict_offset
                            })

                row_groups.append({
                    "row_group_index": rg_idx,
                    "rows": rg_rows,
                    "total_uncompressed_bytes": rg_bytes,
                    "columns": columns
                })

        return {
            "file": os.path.basename(self.filepath),
            "file_size_bytes": self.file_size,
            "metadata_length_bytes": metadata_len,
            "metadata_offset": metadata_offset,
            "version": version,
            "created_by": created_by,
            "total_rows": num_rows,
            "schema_columns": schema_elements,
            "row_groups": row_groups
        }

def create_sample_telemetry_parquet(out_path: str):
    import pyarrow as pa
    import pyarrow.parquet as pq

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    
    # Create realistic analytical telemetry dataset
    data = {
        "event_id": [10001, 10002, 10003, 10004, 10005, 10006],
        "player_nickname": ["Gleidison", "SWAT_Alpha", "Gang_Apex", "SWAT_Delta", "Gang_Sin", "SWAT_Ghost"],
        "weapon_name": ["DSR-E1", "AWM 300", "AWM 300 Altın", "JNG-90", "M4A1 Custom", "DSR-E1"],
        "map_name": ["twoway", "twoway", "thebank", "Arrival", "Arrival", "thebank"],
        "is_headshot": [True, False, True, False, False, True],
        "damage": [250.0, 95.5, 260.0, 102.0, 88.0, 245.0],
        "distance_units": [450.2, 120.4, 680.1, 230.5, 95.0, 510.3],
        "ping_ms": [18, 24, 32, 15, 40, 22]
    }
    
    table = pa.Table.from_pydict(data)
    pq.write_table(table, out_path, compression="snappy", use_dictionary=True)
    print(f"[+] Sample analytics Parquet file generated: {out_path} ({os.path.getsize(out_path)} bytes)")

def print_dissection_report(res: Dict[str, Any]):
    print(f"\n{'='*75}")
    print(f"  APACHE PARQUET BINARY DISSECTION REPORT")
    print(f"  Target File: {res['file']} ({res['file_size_bytes']:,} bytes)")
    print(f"{'='*75}")
    print(f"  [Header / Footer Anatomy]")
    print(f"  - Magic Start:        'PAR1' (Offset 0x00000000 - 0x00000003)")
    print(f"  - Magic End:          'PAR1' (Offset 0x{res['file_size_bytes']-4:08X} - 0x{res['file_size_bytes']-1:08X})")
    print(f"  - FileMetaData Size:  {res['metadata_length_bytes']} bytes")
    print(f"  - FileMetaData Offset:0x{res['metadata_offset']:08X}")
    print(f"  - Engine / Created By:{res['created_by']}")
    print(f"  - Parquet Version:    v{res['version']}")
    print(f"  - Total Dataset Rows: {res['total_rows']:,}")

    print(f"\n  [Schema Hierarchy & Physical Types]")
    for s in res['schema_columns']:
        child_str = f"({s['num_children']} fields)" if s['num_children'] is not None else ""
        print(f"  - {s['name']:<22} | Type: {s['physical_type']:<15} {child_str}")

    print(f"\n  [Row Groups & Column Chunk Encodings]")
    for rg in res['row_groups']:
        print(f"  * RowGroup #{rg['row_group_index']} ({rg['rows']} rows, {rg['total_uncompressed_bytes']:,} uncompressed bytes)")
        for col in rg['columns']:
            enc_str = ", ".join(col['encodings'])
            dict_str = f"DictPage@0x{col['dictionary_page_offset']:04X}" if col['dictionary_page_offset'] is not None else "NoDict"
            print(f"    -> Column: {col['column_name']:<18} | {col['type']:<10} | Codec: {col['codec']:<8} ({col['compression_ratio']:.1f}x) | {dict_str} | Encs: [{enc_str}]")

    print(f"{'='*75}\n")

def main():
    parser = argparse.ArgumentParser(description="Apache Parquet Binary Dissector")
    parser.add_argument("file", nargs="?", help="Path to .parquet file")
    parser.add_argument("--create-sample", help="Generate sample telemetry parquet file at path and dissect it")
    args = parser.parse_args()

    target_path = args.file
    if args.create_sample:
        create_sample_telemetry_parquet(args.create_sample)
        target_path = args.create_sample

    if not target_path:
        default_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "targets", "columnar-storage-re", "data", "telemetry_sample.parquet")
        if not os.path.exists(default_path):
            create_sample_telemetry_parquet(default_path)
        target_path = default_path

    dissector = ParquetBinaryDissector(target_path)
    res = dissector.dissect()
    print_dissection_report(res)

if __name__ == "__main__":
    main()

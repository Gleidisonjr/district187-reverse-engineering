#!/usr/bin/env python3
"""
ONNX Protobuf (.onnx) Pure-Python Wire-Level Binary Dissector & Synthetic Generator.

Zero external dependencies (Python stdlib only). Decodes the Protocol Buffers wire
format directly according to the official ONNX schema (onnx.proto3):
  - LEB128 varints (unsigned & two's complement int64)
  - Wire types: 0 (varint), 1 (64-bit fixed), 2 (length-delimited), 5 (32-bit fixed)
  - Packed and unpacked repeated fields
  - Structured decoding of ModelProto, OperatorSetIdProto, StringStringEntryProto,
    GraphProto, NodeProto, AttributeProto, TensorProto, and ValueInfoProto (symbolic
    and static tensor shapes)
  - Parameter count, byte size, weight preview, and SHA-256 integrity hashing

CLI usage:
  python scripts/parse_onnx_binary.py <model.onnx> [--json]
  python scripts/parse_onnx_binary.py --generate-sample <output.onnx>
  python scripts/parse_onnx_binary.py --self-test
"""

import argparse
import hashlib
import json
import math
import os
import struct
import sys
import tempfile
from typing import Any, Dict, Iterator, List, Optional, Tuple

# ---------------------------------------------------------------------------
# ONNX Enum Tables (from onnx.proto3)
# ---------------------------------------------------------------------------

WIRE_VARINT = 0
WIRE_64BIT = 1
WIRE_LEN = 2
WIRE_32BIT = 5

TENSOR_DATA_TYPES: Dict[int, Tuple[str, int]] = {
    0: ("UNDEFINED", 0),
    1: ("FLOAT", 4),
    2: ("UINT8", 1),
    3: ("INT8", 1),
    4: ("UINT16", 2),
    5: ("INT16", 2),
    6: ("INT32", 4),
    7: ("INT64", 8),
    8: ("STRING", 0),
    9: ("BOOL", 1),
    10: ("FLOAT16", 2),
    11: ("DOUBLE", 8),
    12: ("UINT32", 4),
    13: ("UINT64", 8),
    14: ("COMPLEX64", 8),
    15: ("COMPLEX128", 16),
    16: ("BFLOAT16", 2),
    17: ("FLOAT8E4M3FN", 1),
    18: ("FLOAT8E4M3FNUZ", 1),
    19: ("FLOAT8E5M2", 1),
    20: ("FLOAT8E5M2FNUZ", 1),
}

ATTRIBUTE_TYPES: Dict[int, str] = {
    0: "UNDEFINED",
    1: "FLOAT",
    2: "INT",
    3: "STRING",
    4: "TENSOR",
    5: "GRAPH",
    6: "FLOATS",
    7: "INTS",
    8: "STRINGS",
    9: "TENSORS",
    10: "GRAPHS",
    11: "SPARSE_TENSOR",
    12: "SPARSE_TENSORS",
    13: "TYPE_PROTO",
    14: "TYPE_PROTOS",
}

DATA_LOCATIONS: Dict[int, str] = {
    0: "DEFAULT",
    1: "EXTERNAL",
}


# ---------------------------------------------------------------------------
# Low-Level Protobuf Wire Primitives (Decoder)
# ---------------------------------------------------------------------------

def decode_varint(buf: bytes, pos: int) -> Tuple[int, int]:
    """Decode an unsigned LEB128 varint starting at buf[pos]."""
    result = 0
    shift = 0
    length = len(buf)
    while True:
        if pos >= length:
            raise ValueError(f"Truncated varint at offset {pos}")
        b = buf[pos]
        pos += 1
        result |= (b & 0x7F) << shift
        if not (b & 0x80):
            return result, pos
        shift += 7
        if shift > 70:
            raise ValueError(f"Varint exceeds 10 bytes at offset {pos}")


def to_int64(val: int) -> int:
    """Convert unsigned 64-bit varint representation to signed int64."""
    return val - (1 << 64) if val >= (1 << 63) else val


def iter_fields(buf: bytes) -> Iterator[Tuple[int, int, Any]]:
    """Yield (field_number, wire_type, raw_value) for all fields in a protobuf message."""
    pos = 0
    end = len(buf)
    while pos < end:
        tag, pos = decode_varint(buf, pos)
        field_num = tag >> 3
        wire_type = tag & 0x07
        if field_num == 0:
            raise ValueError(f"Invalid protobuf field number 0 at offset {pos}")

        if wire_type == WIRE_VARINT:
            val, pos = decode_varint(buf, pos)
            yield field_num, wire_type, val
        elif wire_type == WIRE_64BIT:
            if pos + 8 > end:
                raise ValueError(f"Truncated 64-bit field {field_num} at offset {pos}")
            raw = buf[pos : pos + 8]
            pos += 8
            yield field_num, wire_type, raw
        elif wire_type == WIRE_LEN:
            size, pos = decode_varint(buf, pos)
            if pos + size > end:
                raise ValueError(f"Truncated length-delimited field {field_num} (need {size}B) at offset {pos}")
            raw = buf[pos : pos + size]
            pos += size
            yield field_num, wire_type, raw
        elif wire_type == WIRE_32BIT:
            if pos + 4 > end:
                raise ValueError(f"Truncated 32-bit field {field_num} at offset {pos}")
            raw = buf[pos : pos + 4]
            pos += 4
            yield field_num, wire_type, raw
        else:
            raise ValueError(f"Unsupported protobuf wire type {wire_type} (field {field_num}) at offset {pos}")


def unpack_packed_varints(raw: bytes, signed: bool = True) -> List[int]:
    """Decode a packed repeated varint field (wire type 2)."""
    vals: List[int] = []
    pos = 0
    end = len(raw)
    while pos < end:
        v, pos = decode_varint(raw, pos)
        vals.append(to_int64(v) if signed else v)
    return vals


def unpack_packed_floats(raw: bytes) -> List[float]:
    """Decode a packed repeated float32 field (wire type 2)."""
    if len(raw) % 4 != 0:
        raise ValueError(f"Packed float buffer length {len(raw)} not multiple of 4")
    count = len(raw) // 4
    return list(struct.unpack(f"<{count}f", raw))


def unpack_packed_doubles(raw: bytes) -> List[float]:
    """Decode a packed repeated float64 field (wire type 2)."""
    if len(raw) % 8 != 0:
        raise ValueError(f"Packed double buffer length {len(raw)} not multiple of 8")
    count = len(raw) // 8
    return list(struct.unpack(f"<{count}d", raw))


# ---------------------------------------------------------------------------
# Low-Level Protobuf Wire Primitives (Encoder for Synthetic Sample)
# ---------------------------------------------------------------------------

def encode_varint(value: int) -> bytes:
    """Encode an integer (signed or unsigned up to 64-bit) as LEB128 varint."""
    if value < 0:
        value += 1 << 64
    out = bytearray()
    while True:
        byte = value & 0x7F
        value >>= 7
        if value:
            out.append(byte | 0x80)
        else:
            out.append(byte)
            break
    return bytes(out)


def encode_tag(field_num: int, wire_type: int) -> bytes:
    return encode_varint((field_num << 3) | wire_type)


def encode_varint_field(field_num: int, value: int) -> bytes:
    return encode_tag(field_num, WIRE_VARINT) + encode_varint(value)


def encode_float_field(field_num: int, value: float) -> bytes:
    return encode_tag(field_num, WIRE_32BIT) + struct.pack("<f", value)


def encode_bytes_field(field_num: int, payload: bytes) -> bytes:
    return encode_tag(field_num, WIRE_LEN) + encode_varint(len(payload)) + payload


def encode_string_field(field_num: int, text: str) -> bytes:
    return encode_bytes_field(field_num, text.encode("utf-8"))


def encode_packed_int64_field(field_num: int, values: List[int]) -> bytes:
    body = b"".join(encode_varint(v) for v in values)
    return encode_bytes_field(field_num, body)


# ---------------------------------------------------------------------------
# Structured ONNX Protobuf Decoders
# ---------------------------------------------------------------------------

def parse_string_string_entry(buf: bytes) -> Tuple[str, str]:
    key = ""
    value = ""
    for fnum, wtype, val in iter_fields(buf):
        if fnum == 1 and wtype == WIRE_LEN:
            key = val.decode("utf-8", errors="replace")
        elif fnum == 2 and wtype == WIRE_LEN:
            value = val.decode("utf-8", errors="replace")
    return key, value


def parse_opset_import(buf: bytes) -> Dict[str, Any]:
    domain = ""
    version = 0
    for fnum, wtype, val in iter_fields(buf):
        if fnum == 1 and wtype == WIRE_LEN:
            domain = val.decode("utf-8", errors="replace")
        elif fnum == 2 and wtype == WIRE_VARINT:
            version = to_int64(val)
    return {"domain": domain or "ai.onnx", "version": version}


def parse_tensor_shape_proto(buf: bytes) -> List[Any]:
    dims: List[Any] = []
    for fnum, wtype, val in iter_fields(buf):
        if fnum == 1 and wtype == WIRE_LEN:
            dim_val: Any = "?"
            for dfnum, dwtype, dval in iter_fields(val):
                if dfnum == 1 and dwtype == WIRE_VARINT:
                    dim_val = to_int64(dval)
                elif dfnum == 2 and dwtype == WIRE_LEN:
                    dim_val = dval.decode("utf-8", errors="replace")
            dims.append(dim_val)
    return dims


def parse_type_proto(buf: bytes) -> Dict[str, Any]:
    elem_type_id = 0
    shape: List[Any] = []
    for fnum, wtype, val in iter_fields(buf):
        if fnum == 1 and wtype == WIRE_LEN:  # tensor_type (TypeProto.Tensor)
            for tfnum, twtype, tval in iter_fields(val):
                if tfnum == 1 and twtype == WIRE_VARINT:
                    elem_type_id = to_int64(tval)
                elif tfnum == 2 and twtype == WIRE_LEN:
                    shape = parse_tensor_shape_proto(tval)
    dtype_name = TENSOR_DATA_TYPES.get(elem_type_id, (f"UNKNOWN({elem_type_id})", 0))[0]
    return {"elem_type": dtype_name, "elem_type_id": elem_type_id, "shape": shape}


def parse_value_info_proto(buf: bytes) -> Dict[str, Any]:
    info: Dict[str, Any] = {"name": "", "elem_type": "UNDEFINED", "shape": []}
    doc_string = ""
    for fnum, wtype, val in iter_fields(buf):
        if fnum == 1 and wtype == WIRE_LEN:
            info["name"] = val.decode("utf-8", errors="replace")
        elif fnum == 2 and wtype == WIRE_LEN:
            tinfo = parse_type_proto(val)
            info["elem_type"] = tinfo["elem_type"]
            info["shape"] = tinfo["shape"]
        elif fnum == 3 and wtype == WIRE_LEN:
            doc_string = val.decode("utf-8", errors="replace")
    if doc_string:
        info["doc_string"] = doc_string
    return info


def _preview_raw_values(raw_data: bytes, data_type_id: int, limit: int = 4) -> List[Any]:
    """Decode up to `limit` scalar values from raw_data for inspection."""
    fmt_map = {
        1: ("f", 4),   # FLOAT
        2: ("B", 1),   # UINT8
        3: ("b", 1),   # INT8
        4: ("H", 2),   # UINT16
        5: ("h", 2),   # INT16
        6: ("i", 4),   # INT32
        7: ("q", 8),   # INT64
        9: ("?", 1),   # BOOL
        11: ("d", 8),  # DOUBLE
        12: ("I", 4),  # UINT32
        13: ("Q", 8),  # UINT64
    }
    if data_type_id not in fmt_map or not raw_data:
        return []
    fmt, itemsize = fmt_map[data_type_id]
    count = min(limit, len(raw_data) // itemsize)
    if count <= 0:
        return []
    vals = struct.unpack_from(f"<{count}{fmt}", raw_data, 0)
    if fmt in ("f", "d"):
        return [round(v, 6) for v in vals]
    return list(vals)


def parse_tensor_proto(buf: bytes) -> Dict[str, Any]:
    name = ""
    dims: List[int] = []
    data_type_id = 0
    raw_data = b""
    float_data: List[float] = []
    int32_data: List[int] = []
    int64_data: List[int] = []
    double_data: List[float] = []
    uint64_data: List[int] = []
    string_data_count = 0
    data_location = 0
    external_data: Dict[str, str] = {}

    for fnum, wtype, val in iter_fields(buf):
        if fnum == 1:  # dims
            if wtype == WIRE_LEN:
                dims.extend(unpack_packed_varints(val, signed=True))
            elif wtype == WIRE_VARINT:
                dims.append(to_int64(val))
        elif fnum == 2 and wtype == WIRE_VARINT:
            data_type_id = to_int64(val)
        elif fnum == 4:  # float_data
            if wtype == WIRE_LEN:
                float_data.extend(unpack_packed_floats(val))
            elif wtype == WIRE_32BIT:
                float_data.append(struct.unpack("<f", val)[0])
        elif fnum == 5:  # int32_data
            if wtype == WIRE_LEN:
                int32_data.extend(unpack_packed_varints(val, signed=True))
            elif wtype == WIRE_VARINT:
                int32_data.append(to_int64(val))
        elif fnum == 6 and wtype == WIRE_LEN:
            string_data_count += 1
        elif fnum == 7:  # int64_data
            if wtype == WIRE_LEN:
                int64_data.extend(unpack_packed_varints(val, signed=True))
            elif wtype == WIRE_VARINT:
                int64_data.append(to_int64(val))
        elif fnum == 8 and wtype == WIRE_LEN:
            name = val.decode("utf-8", errors="replace")
        elif fnum == 9 and wtype == WIRE_LEN:
            raw_data = val
        elif fnum == 10:  # double_data
            if wtype == WIRE_LEN:
                double_data.extend(unpack_packed_doubles(val))
            elif wtype == WIRE_64BIT:
                double_data.append(struct.unpack("<d", val)[0])
        elif fnum == 11:  # uint64_data
            if wtype == WIRE_LEN:
                uint64_data.extend(unpack_packed_varints(val, signed=False))
            elif wtype == WIRE_VARINT:
                uint64_data.append(val)
        elif fnum == 13 and wtype == WIRE_LEN:
            ek, ev = parse_string_string_entry(val)
            external_data[ek] = ev
        elif fnum == 14 and wtype == WIRE_VARINT:
            data_location = to_int64(val)

    dtype_name, itemsize = TENSOR_DATA_TYPES.get(data_type_id, (f"UNKNOWN({data_type_id})", 0))
    num_elements = math.prod(dims) if dims else (1 if (raw_data or float_data or int32_data or int64_data or double_data or uint64_data) else 0)

    # Determine storage encoding & byte size
    storage = "empty"
    byte_size = 0
    preview: List[Any] = []
    raw_sha256: Optional[str] = None

    if raw_data:
        storage = "raw_data"
        byte_size = len(raw_data)
        preview = _preview_raw_values(raw_data, data_type_id)
        raw_sha256 = hashlib.sha256(raw_data).hexdigest()
    elif float_data:
        storage = "float_data"
        byte_size = len(float_data) * 4
        preview = [round(v, 6) for v in float_data[:4]]
    elif int32_data:
        storage = "int32_data"
        byte_size = len(int32_data) * 4
        preview = int32_data[:4]
    elif int64_data:
        storage = "int64_data"
        byte_size = len(int64_data) * 8
        preview = int64_data[:4]
    elif double_data:
        storage = "double_data"
        byte_size = len(double_data) * 8
        preview = [round(v, 6) for v in double_data[:4]]
    elif uint64_data:
        storage = "uint64_data"
        byte_size = len(uint64_data) * 8
        preview = uint64_data[:4]
    elif string_data_count:
        storage = "string_data"
        byte_size = 0
    elif external_data:
        storage = "external_data"
        byte_size = num_elements * itemsize
    else:
        byte_size = num_elements * itemsize

    res: Dict[str, Any] = {
        "name": name,
        "dims": dims,
        "data_type": dtype_name,
        "data_type_id": data_type_id,
        "num_elements": num_elements,
        "byte_size": byte_size,
        "storage": storage,
        "data_location": DATA_LOCATIONS.get(data_location, str(data_location)),
        "preview": preview,
    }
    if raw_sha256:
        res["raw_data_sha256"] = raw_sha256
    if external_data:
        res["external_data"] = external_data
    return res


def parse_attribute_proto(buf: bytes) -> Dict[str, Any]:
    name = ""
    attr_type_id = 0
    val_f: Optional[float] = None
    val_i: Optional[int] = None
    val_s: Optional[str] = None
    val_t: Optional[Dict[str, Any]] = None
    val_floats: List[float] = []
    val_ints: List[int] = []
    val_strings: List[str] = []

    for fnum, wtype, val in iter_fields(buf):
        if fnum == 1 and wtype == WIRE_LEN:
            name = val.decode("utf-8", errors="replace")
        elif fnum == 2 and wtype == WIRE_32BIT:
            val_f = round(struct.unpack("<f", val)[0], 6)
        elif fnum == 3 and wtype == WIRE_VARINT:
            val_i = to_int64(val)
        elif fnum == 4 and wtype == WIRE_LEN:
            val_s = val.decode("utf-8", errors="replace")
        elif fnum == 5 and wtype == WIRE_LEN:
            val_t = parse_tensor_proto(val)
        elif fnum == 7:  # floats
            if wtype == WIRE_LEN:
                val_floats.extend(round(v, 6) for v in unpack_packed_floats(val))
            elif wtype == WIRE_32BIT:
                val_floats.append(round(struct.unpack("<f", val)[0], 6))
        elif fnum == 8:  # ints
            if wtype == WIRE_LEN:
                val_ints.extend(unpack_packed_varints(val, signed=True))
            elif wtype == WIRE_VARINT:
                val_ints.append(to_int64(val))
        elif fnum == 9 and wtype == WIRE_LEN:
            val_strings.append(val.decode("utf-8", errors="replace"))
        elif fnum == 20 and wtype == WIRE_VARINT:
            attr_type_id = to_int64(val)

    attr_type = ATTRIBUTE_TYPES.get(attr_type_id, f"UNKNOWN({attr_type_id})")
    value: Any = None
    if attr_type == "FLOAT" or (attr_type == "UNDEFINED" and val_f is not None):
        value = val_f
    elif attr_type == "INT" or (attr_type == "UNDEFINED" and val_i is not None):
        value = val_i
    elif attr_type == "STRING" or (attr_type == "UNDEFINED" and val_s is not None):
        value = val_s
    elif attr_type == "TENSOR" or (attr_type == "UNDEFINED" and val_t is not None):
        value = val_t
    elif attr_type == "FLOATS" or (attr_type == "UNDEFINED" and val_floats):
        value = val_floats
    elif attr_type == "INTS" or (attr_type == "UNDEFINED" and val_ints):
        value = val_ints
    elif attr_type == "STRINGS" or (attr_type == "UNDEFINED" and val_strings):
        value = val_strings

    return {"name": name, "type": attr_type, "value": value}


def parse_node_proto(buf: bytes) -> Dict[str, Any]:
    inputs: List[str] = []
    outputs: List[str] = []
    name = ""
    op_type = ""
    domain = ""
    attributes: List[Dict[str, Any]] = []

    for fnum, wtype, val in iter_fields(buf):
        if fnum == 1 and wtype == WIRE_LEN:
            inputs.append(val.decode("utf-8", errors="replace"))
        elif fnum == 2 and wtype == WIRE_LEN:
            outputs.append(val.decode("utf-8", errors="replace"))
        elif fnum == 3 and wtype == WIRE_LEN:
            name = val.decode("utf-8", errors="replace")
        elif fnum == 4 and wtype == WIRE_LEN:
            op_type = val.decode("utf-8", errors="replace")
        elif fnum == 5 and wtype == WIRE_LEN:
            attributes.append(parse_attribute_proto(val))
        elif fnum == 7 and wtype == WIRE_LEN:
            domain = val.decode("utf-8", errors="replace")

    node: Dict[str, Any] = {
        "name": name,
        "op_type": op_type,
        "input": inputs,
        "output": outputs,
        "attribute": attributes,
    }
    if domain:
        node["domain"] = domain
    return node


def parse_graph_proto(buf: bytes) -> Dict[str, Any]:
    name = ""
    doc_string = ""
    nodes: List[Dict[str, Any]] = []
    initializers: List[Dict[str, Any]] = []
    inputs: List[Dict[str, Any]] = []
    outputs: List[Dict[str, Any]] = []
    value_infos: List[Dict[str, Any]] = []

    for fnum, wtype, val in iter_fields(buf):
        if fnum == 1 and wtype == WIRE_LEN:
            nodes.append(parse_node_proto(val))
        elif fnum == 2 and wtype == WIRE_LEN:
            name = val.decode("utf-8", errors="replace")
        elif fnum == 5 and wtype == WIRE_LEN:
            initializers.append(parse_tensor_proto(val))
        elif fnum == 10 and wtype == WIRE_LEN:
            doc_string = val.decode("utf-8", errors="replace")
        elif fnum == 11 and wtype == WIRE_LEN:
            inputs.append(parse_value_info_proto(val))
        elif fnum == 12 and wtype == WIRE_LEN:
            outputs.append(parse_value_info_proto(val))
        elif fnum == 13 and wtype == WIRE_LEN:
            value_infos.append(parse_value_info_proto(val))

    total_params = sum(t["num_elements"] for t in initializers)
    total_tensor_bytes = sum(t["byte_size"] for t in initializers)

    op_histogram: Dict[str, int] = {}
    for n in nodes:
        op = n["op_type"]
        op_histogram[op] = op_histogram.get(op, 0) + 1

    graph: Dict[str, Any] = {
        "name": name,
        "node_count": len(nodes),
        "op_histogram": op_histogram,
        "initializer_count": len(initializers),
        "total_parameters": total_params,
        "total_tensor_bytes": total_tensor_bytes,
        "input": inputs,
        "output": outputs,
        "value_info": value_infos,
        "node": nodes,
        "initializer": initializers,
    }
    if doc_string:
        graph["doc_string"] = doc_string
    return graph


def parse_model_proto(buf: bytes) -> Dict[str, Any]:
    ir_version = 0
    opset_import: List[Dict[str, Any]] = []
    producer_name = ""
    producer_version = ""
    domain = ""
    model_version = 0
    doc_string = ""
    metadata_props: Dict[str, str] = {}
    graph: Optional[Dict[str, Any]] = None

    for fnum, wtype, val in iter_fields(buf):
        if fnum == 1 and wtype == WIRE_VARINT:
            ir_version = to_int64(val)
        elif fnum == 2 and wtype == WIRE_LEN:
            producer_name = val.decode("utf-8", errors="replace")
        elif fnum == 3 and wtype == WIRE_LEN:
            producer_version = val.decode("utf-8", errors="replace")
        elif fnum == 4 and wtype == WIRE_LEN:
            domain = val.decode("utf-8", errors="replace")
        elif fnum == 5 and wtype == WIRE_VARINT:
            model_version = to_int64(val)
        elif fnum == 6 and wtype == WIRE_LEN:
            doc_string = val.decode("utf-8", errors="replace")
        elif fnum == 7 and wtype == WIRE_LEN:
            graph = parse_graph_proto(val)
        elif fnum == 8 and wtype == WIRE_LEN:
            opset_import.append(parse_opset_import(val))
        elif fnum == 14 and wtype == WIRE_LEN:
            mk, mv = parse_string_string_entry(val)
            metadata_props[mk] = mv

    return {
        "ir_version": ir_version,
        "opset_import": opset_import,
        "producer_name": producer_name,
        "producer_version": producer_version,
        "domain": domain,
        "model_version": model_version,
        "doc_string": doc_string,
        "metadata_props": metadata_props,
        "graph": graph or {},
    }


def dissect_onnx(path: str) -> Dict[str, Any]:
    """Read and dissect a binary .onnx file from disk."""
    with open(path, "rb") as f:
        data = f.read()
    parsed = parse_model_proto(data)
    parsed["file"] = {
        "path": os.path.abspath(path),
        "size_bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }
    return parsed


# ---------------------------------------------------------------------------
# Synthetic Valid ONNX Binary Generator (Conv -> Relu -> Flatten -> Gemm)
# ---------------------------------------------------------------------------

def _build_dim(val: Any) -> bytes:
    if isinstance(val, int):
        return encode_varint_field(1, val)
    return encode_string_field(2, str(val))


def _build_value_info(name: str, elem_type: int, shape: List[Any]) -> bytes:
    shape_msg = b"".join(encode_bytes_field(1, _build_dim(d)) for d in shape)
    tensor_type = encode_varint_field(1, elem_type) + encode_bytes_field(2, shape_msg)
    type_proto = encode_bytes_field(1, tensor_type)
    return encode_string_field(1, name) + encode_bytes_field(2, type_proto)


def _build_tensor_f32(name: str, dims: List[int], values: List[float], packed_dims: bool = True) -> bytes:
    expected = math.prod(dims)
    assert len(values) == expected, f"Tensor {name}: expected {expected} values, got {len(values)}"
    out = bytearray()
    if packed_dims:
        out += encode_packed_int64_field(1, dims)
    else:
        for d in dims:
            out += encode_varint_field(1, d)
    out += encode_varint_field(2, 1)  # FLOAT = 1
    out += encode_string_field(8, name)
    raw = struct.pack(f"<{len(values)}f", *values)
    out += encode_bytes_field(9, raw)
    return bytes(out)


def _build_attr_ints(name: str, ints: List[int], packed: bool = True) -> bytes:
    out = bytearray(encode_string_field(1, name))
    if packed:
        out += encode_packed_int64_field(8, ints)
    else:
        for v in ints:
            out += encode_varint_field(8, v)
    out += encode_varint_field(20, 7)  # INTS = 7
    return bytes(out)


def _build_attr_int(name: str, val: int) -> bytes:
    return (
        encode_string_field(1, name)
        + encode_varint_field(3, val)
        + encode_varint_field(20, 2)  # INT = 2
    )


def _build_attr_float(name: str, val: float) -> bytes:
    return (
        encode_string_field(1, name)
        + encode_float_field(2, val)
        + encode_varint_field(20, 1)  # FLOAT = 1
    )


def _build_node(
    name: str,
    op_type: str,
    inputs: List[str],
    outputs: List[str],
    attrs: Optional[List[bytes]] = None,
) -> bytes:
    out = bytearray()
    for inp in inputs:
        out += encode_string_field(1, inp)
    for oup in outputs:
        out += encode_string_field(2, oup)
    out += encode_string_field(3, name)
    out += encode_string_field(4, op_type)
    for a in attrs or []:
        out += encode_bytes_field(5, a)
    return bytes(out)


def _build_kv(key: str, value: str) -> bytes:
    return encode_string_field(1, key) + encode_string_field(2, value)


def generate_sample_onnx(path: str) -> int:
    """
    Generate a valid binary .onnx file representing a tiny Conv + Relu + Flatten + Gemm
    classifier with real float32 weights in raw_data:
      - Input:  x [batch, 1, 4, 4] (FLOAT)
      - Conv1:  W [2, 1, 3, 3] (18 params) + B [2] (2 params) -> [batch, 2, 2, 2]
      - Relu1:  [batch, 2, 2, 2] -> [batch, 2, 2, 2]
      - Flat1:  [batch, 2, 2, 2] -> [batch, 8] (axis=1)
      - Gemm1:  W [3, 8] (24 params, transB=1) + B [3] (3 params) -> logits [batch, 3]
      Total parameters: 18 + 2 + 24 + 3 = 47 float32 weights (188 bytes raw_data).
    """
    parent = os.path.dirname(os.path.abspath(path))
    if parent:
        os.makedirs(parent, exist_ok=True)

    # Deterministic float32 weights
    conv_w = [round((i - 8.5) * 0.1, 4) for i in range(18)]
    conv_b = [0.05, -0.05]
    fc_w = [round(((i % 7) - 3) * 0.125, 4) for i in range(24)]
    fc_b = [0.1, 0.0, -0.1]

    init_conv_w = _build_tensor_f32("conv1.weight", [2, 1, 3, 3], conv_w, packed_dims=True)
    init_conv_b = _build_tensor_f32("conv1.bias", [2], conv_b, packed_dims=False)  # exercises unpacked dims
    init_fc_w = _build_tensor_f32("fc1.weight", [3, 8], fc_w, packed_dims=True)
    init_fc_b = _build_tensor_f32("fc1.bias", [3], fc_b, packed_dims=True)

    n_conv = _build_node(
        name="Conv_0",
        op_type="Conv",
        inputs=["input", "conv1.weight", "conv1.bias"],
        outputs=["conv1_out"],
        attrs=[
            _build_attr_ints("kernel_shape", [3, 3], packed=True),
            _build_attr_ints("strides", [1, 1], packed=False),  # exercises unpacked ints
            _build_attr_ints("pads", [0, 0, 0, 0], packed=True),
        ],
    )
    n_relu = _build_node(
        name="Relu_1",
        op_type="Relu",
        inputs=["conv1_out"],
        outputs=["relu1_out"],
    )
    n_flat = _build_node(
        name="Flatten_2",
        op_type="Flatten",
        inputs=["relu1_out"],
        outputs=["flat_out"],
        attrs=[_build_attr_int("axis", 1)],
    )
    n_gemm = _build_node(
        name="Gemm_3",
        op_type="Gemm",
        inputs=["flat_out", "fc1.weight", "fc1.bias"],
        outputs=["logits"],
        attrs=[
            _build_attr_float("alpha", 1.0),
            _build_attr_float("beta", 1.0),
            _build_attr_int("transB", 1),
        ],
    )

    vi_input = _build_value_info("input", 1, ["batch", 1, 4, 4])
    vi_conv = _build_value_info("conv1_out", 1, ["batch", 2, 2, 2])
    vi_flat = _build_value_info("flat_out", 1, ["batch", 8])
    vi_output = _build_value_info("logits", 1, ["batch", 3])

    graph_msg = bytearray()
    for node in (n_conv, n_relu, n_flat, n_gemm):
        graph_msg += encode_bytes_field(1, node)
    graph_msg += encode_string_field(2, "TinyConvGemmNet")
    for init in (init_conv_w, init_conv_b, init_fc_w, init_fc_b):
        graph_msg += encode_bytes_field(5, init)
    graph_msg += encode_string_field(10, "Synthetic Conv+Relu+Flatten+Gemm test graph for pure-Python ONNX RE")
    graph_msg += encode_bytes_field(11, vi_input)
    graph_msg += encode_bytes_field(12, vi_output)
    graph_msg += encode_bytes_field(13, vi_conv)
    graph_msg += encode_bytes_field(13, vi_flat)

    opset_msg = encode_string_field(1, "") + encode_varint_field(2, 17)

    model_msg = bytearray()
    model_msg += encode_varint_field(1, 9)  # ir_version = 9
    model_msg += encode_string_field(2, "pure-python-onnx-re")
    model_msg += encode_string_field(3, "1.0.0")
    model_msg += encode_string_field(4, "re.ml.synthetic")
    model_msg += encode_varint_field(5, 1)  # model_version = 1
    model_msg += encode_string_field(6, "Synthetic ONNX model generated without protobuf/onnx dependencies")
    model_msg += encode_bytes_field(7, bytes(graph_msg))
    model_msg += encode_bytes_field(8, opset_msg)
    model_msg += encode_bytes_field(14, _build_kv("author", "ml-model-format-re"))
    model_msg += encode_bytes_field(14, _build_kv("architecture", "Conv-Relu-Flatten-Gemm"))

    with open(path, "wb") as f:
        f.write(model_msg)
    return len(model_msg)


# ---------------------------------------------------------------------------
# Human-Readable Summary Formatter
# ---------------------------------------------------------------------------

def format_summary(model: Dict[str, Any]) -> str:
    finfo = model.get("file", {})
    graph = model.get("graph", {})
    opsets = ", ".join(f"{o['domain']} v{o['version']}" for o in model.get("opset_import", []))
    lines = [
        "=== ONNX Protobuf Binary Dissection ===",
        f"File:       {finfo.get('path', '<memory>')} ({finfo.get('size_bytes', 0)} bytes)",
        f"SHA-256:    {finfo.get('sha256', 'N/A')}",
        f"IR Version: {model['ir_version']} | Model Version: {model['model_version']}",
        f"Producer:   {model['producer_name']} {model['producer_version']} (domain={model['domain'] or 'default'})",
        f"Opsets:     {opsets or 'none'}",
    ]
    if model.get("doc_string"):
        lines.append(f"DocString:  {model['doc_string']}")
    if model.get("metadata_props"):
        meta_str = ", ".join(f"{k}={v}" for k, v in model["metadata_props"].items())
        lines.append(f"Metadata:   {meta_str}")

    lines.append("")
    lines.append(f"--- Graph: {graph.get('name', '<unnamed>')} ---")
    lines.append(
        f"Nodes: {graph.get('node_count', 0)} | "
        f"Initializers: {graph.get('initializer_count', 0)} | "
        f"Parameters: {graph.get('total_parameters', 0):,} "
        f"({graph.get('total_tensor_bytes', 0):,} bytes)"
    )

    lines.append("Inputs:")
    for inp in graph.get("input", []):
        lines.append(f"  - {inp['name']}: {inp['elem_type']}{inp['shape']}")

    lines.append("Outputs:")
    for oup in graph.get("output", []):
        lines.append(f"  - {oup['name']}: {oup['elem_type']}{oup['shape']}")

    if graph.get("value_info"):
        lines.append("Value Info (Intermediate):")
        for vi in graph["value_info"]:
            lines.append(f"  - {vi['name']}: {vi['elem_type']}{vi['shape']}")

    lines.append("Nodes (Topological Order):")
    for idx, node in enumerate(graph.get("node", [])):
        attrs = ", ".join(f"{a['name']}={a['value']}" for a in node.get("attribute", []))
        attr_suffix = f" [{attrs}]" if attrs else ""
        lines.append(
            f"  [{idx}] {node['op_type']} ({node['name']}): "
            f"{node['input']} -> {node['output']}{attr_suffix}"
        )

    lines.append("Initializers (Weights):")
    for t in graph.get("initializer", []):
        lines.append(
            f"  - {t['name']}: {t['data_type']}{t['dims']} "
            f"({t['num_elements']} params, {t['byte_size']} B, {t['storage']}) "
            f"preview={t['preview']}"
        )

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Self-Test Suite
# ---------------------------------------------------------------------------

def run_self_test() -> int:
    print("[*] Running pure-Python ONNX Protobuf dissector self-test...")
    with tempfile.TemporaryDirectory(prefix="onnx_re_test_") as tmpdir:
        sample_path = os.path.join(tmpdir, "synthetic_conv_gemm.onnx")
        written = generate_sample_onnx(sample_path)
        assert written > 0, "Generated ONNX file is empty"

        with open(sample_path, "rb") as f:
            expected_sha256 = hashlib.sha256(f.read()).hexdigest()

        model = dissect_onnx(sample_path)
        graph = model["graph"]

        # 1. File integrity & size
        assert model["file"]["size_bytes"] == written
        assert model["file"]["sha256"] == expected_sha256

        # 2. ModelProto metadata
        assert model["ir_version"] == 9, f"Expected IR 9, got {model['ir_version']}"
        assert model["producer_name"] == "pure-python-onnx-re"
        assert model["producer_version"] == "1.0.0"
        assert model["domain"] == "re.ml.synthetic"
        assert model["model_version"] == 1
        assert model["opset_import"] == [{"domain": "ai.onnx", "version": 17}]
        assert model["metadata_props"]["author"] == "ml-model-format-re"
        assert model["metadata_props"]["architecture"] == "Conv-Relu-Flatten-Gemm"

        # 3. GraphProto inputs, outputs, intermediate value_info (symbolic + static dims)
        assert graph["name"] == "TinyConvGemmNet"
        assert graph["input"][0] == {"name": "input", "elem_type": "FLOAT", "shape": ["batch", 1, 4, 4]}
        assert graph["output"][0] == {"name": "logits", "elem_type": "FLOAT", "shape": ["batch", 3]}
        assert len(graph["value_info"]) == 2
        assert graph["value_info"][0]["shape"] == ["batch", 2, 2, 2]

        # 4. Nodes & Attributes (packed + unpacked ints, scalar int, float)
        assert graph["node_count"] == 4
        op_types = [n["op_type"] for n in graph["node"]]
        assert op_types == ["Conv", "Relu", "Flatten", "Gemm"]
        conv_attrs = {a["name"]: a["value"] for a in graph["node"][0]["attribute"]}
        assert conv_attrs["kernel_shape"] == [3, 3]
        assert conv_attrs["strides"] == [1, 1]
        assert conv_attrs["pads"] == [0, 0, 0, 0]
        gemm_attrs = {a["name"]: a["value"] for a in graph["node"][3]["attribute"]}
        assert gemm_attrs["alpha"] == 1.0
        assert gemm_attrs["beta"] == 1.0
        assert gemm_attrs["transB"] == 1

        # 5. Initializers / Tensors, parameter count, byte size, raw_data preview
        assert graph["initializer_count"] == 4
        assert graph["total_parameters"] == 47, f"Expected 47 params, got {graph['total_parameters']}"
        assert graph["total_tensor_bytes"] == 188, f"Expected 188 bytes, got {graph['total_tensor_bytes']}"

        tensors_by_name = {t["name"]: t for t in graph["initializer"]}
        assert tensors_by_name["conv1.weight"]["dims"] == [2, 1, 3, 3]
        assert tensors_by_name["conv1.weight"]["num_elements"] == 18
        assert tensors_by_name["conv1.weight"]["byte_size"] == 72
        assert tensors_by_name["conv1.bias"]["dims"] == [2]
        assert tensors_by_name["conv1.bias"]["preview"] == [0.05, -0.05]
        assert tensors_by_name["fc1.weight"]["dims"] == [3, 8]
        assert tensors_by_name["fc1.bias"]["preview"] == [0.1, 0.0, -0.1]

        # 6. Verify negative signed int64 varint round-trip (e.g. axis=-1)
        neg_raw = encode_varint(-1)
        assert len(neg_raw) == 10, "Negative int64 varint must be 10 bytes in two's complement"
        decoded_u, _ = decode_varint(neg_raw, 0)
        assert to_int64(decoded_u) == -1

        # 7. Verify JSON serialization works cleanly
        json_out = json.dumps(model, indent=2)
        assert len(json_out) > 200

        print(format_summary(model))
        print("")
        print("[PASS] All ONNX Protobuf wire-level dissector self-tests passed!")
        return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Pure-Python ONNX Protobuf (.onnx) wire-level binary dissector (zero dependencies)."
    )
    parser.add_argument("input", nargs="?", help="Path to an .onnx binary file to dissect.")
    parser.add_argument("--json", action="store_true", help="Output structured JSON instead of terminal summary.")
    parser.add_argument("--generate-sample", metavar="PATH", help="Generate a valid synthetic .onnx file at PATH.")
    parser.add_argument("--self-test", action="store_true", help="Run end-to-end self-test in a temporary directory.")

    args = parser.parse_args()

    if args.self_test:
        return run_self_test()

    if args.generate_sample:
        nbytes = generate_sample_onnx(args.generate_sample)
        print(f"[+] Generated synthetic ONNX model: {args.generate_sample} ({nbytes} bytes)")
        if not args.input:
            return 0

    if not args.input:
        parser.print_help()
        return 1

    model = dissect_onnx(args.input)
    if args.json:
        print(json.dumps(model, indent=2))
    else:
        print(format_summary(model))
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())

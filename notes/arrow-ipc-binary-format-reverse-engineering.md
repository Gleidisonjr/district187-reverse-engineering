# Engenharia Reversa do Formato Binário Apache Arrow IPC (`.arrow` / Feather v2)

Alvo: `targets/columnar-storage-re/`  
Script: [`scripts/parse_arrow_ipc_binary.py`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/scripts/parse_arrow_ipc_binary.py)  
Data: 2026-11-19

---

## 1. Arquitetura Binária do Arrow IPC File Format (Random-Access)

Diferente do **Apache Parquet** (otimizado para compressão em disco com Thrift Compact Protocol e páginas comprimidas), o **Apache Arrow IPC** é otimizado para **zero-copy in-memory analytics** (usado em DuckDB, Polars, PyArrow, Spark e pipelines Meta/Presto):

```
+-------------------------------------------------------------------+
| 0x00: Magic Header (8 bytes): "ARROW1\x00\x00"                    |
+-------------------------------------------------------------------+
| Encapsulated Message Stream (Schema -> RecordBatch_0 -> ...):     |
|   [0xFFFFFFFF (4B LE)]  Continuation Token (IPC v5)               |
|   [metadata_len (4B i32 LE)]                                      |
|   [FlatBuffer Message Table (padded to 8-byte boundary)]          |
|   [Body Buffers: validity bitmap + offsets + values (zero-copy)]  |
+-------------------------------------------------------------------+
| End-of-Stream Marker (8 bytes): 0xFFFFFFFF + 0x00000000           |
+-------------------------------------------------------------------+
| FlatBuffer Footer Table (Version, Schema, Block[] RecordBatches)  |
+-------------------------------------------------------------------+
| Footer Length (4B i32 LE) + Trailing Magic (6B): "ARROW1"         |
+-------------------------------------------------------------------+
```

## 2. Dissecação de Tabelas FlatBuffers (Sem Dependências)
- **Root Offset (`uint32 LE` em `+0x00`):** aponta para o início da `Table`.
- **VTable Relative Offset (`int32 LE` em `root_off`):** `vtable_off = root_off - soffset32`.
- **VTable:** `[vtable_size: u16][table_size: u16][field_0_off: u16][field_1_off: u16]...` (se `field_i_off == 0`, o campo está ausente/default).
- **Acesso $O(1)$ sem desserialização:** basta somar `root_off + field_i_off` para ler qualquer campo escalar diretamente do buffer mapeado em memória (`mmap`).

## 3. Comparativo Técnico: Apache Parquet vs Apache Arrow IPC

| Dimensão | Apache Parquet (`.parquet`) | Apache Arrow IPC (`.arrow` / Feather v2) |
|---|---|---|
| **Metadados** | Apache Thrift Compact Protocol (LEB128/ZigZag) | Google FlatBuffers (acesso $O(1)$ via vtable) |
| **Foco Principal** | Armazenamento analítico compactado em disco/S3 | Troca zero-copy em memória / IPC / Flight |
| **Magic Header/Footer** | `PAR1` (4B início + 4B fim) | `ARROW1\x00\x00` (8B início) + `ARROW1` (6B fim) |
| **Dissector no Repositório** | [`scripts/parse_parquet_binary.py`](../scripts/parse_parquet_binary.py) | [`scripts/parse_arrow_ipc_binary.py`](../scripts/parse_arrow_ipc_binary.py) |

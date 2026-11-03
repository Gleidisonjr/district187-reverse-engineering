# Apache Parquet Columnar Storage — Binary Format & Thrift Protocol Dissection

## Visão Geral
O Apache Parquet é o formato colunar binário predominante no ecossistema moderno de engenharia de dados (Meta, Presto, DuckDB, Arrow, Spark, Iceberg).

Ao contrário de formatos tabulares tradicionais (como CSV ou SQLite), o Parquet organiza os dados em colunas contíguas comprimidas e emprega uma arquitetura **Footer-First** (leitura retroativa a partir do final do arquivo).

---

## 1. Anatomia Estrutural de Baixo Nível

```
+-----------------------------------+ 0x00000000
| Magic Number: 'PAR1' (4 bytes)    |
+-----------------------------------+ 0x00000004
|                                   |
| Column Chunks & Pages (Data)      |
| [Snappy/ZSTD compressed streams]  |
|                                   |
+-----------------------------------+ Offset = FileSize - 8 - MetaLen
| FileMetaData                      |
| [Thrift Compact Protocol Stream]  |
+-----------------------------------+ Offset = FileSize - 8
| Length of FileMetaData (4B uint32)|
+-----------------------------------+ Offset = FileSize - 4
| Magic Number: 'PAR1' (4 bytes)    |
+-----------------------------------+ FileSize
```

### Por que Footer-First?
Em pipelines de big data de escrita sequencial (streaming ou append-only), os encoders não sabem de antemão:
1. O número exato de linhas totais geradas.
2. Os offsets exatos onde cada página/dicionário de coluna terminará em disco.
3. Os valores mínimos e máximos globais para data skipping.

Portanto, o escritor despeja as colunas sequencialmente e, ao finalizar, empacota o catálogo completo (`FileMetaData`) e grava seu tamanho imediatamente antes do footer magic.

---

## 2. Decodificação do Thrift Compact Protocol

O `FileMetaData` não é JSON nem Protobuf; ele utiliza o protocolo binário **Thrift Compact Protocol**, projetado para máxima densidade de empacotamento:

- **Varints LEB128 & ZigZag Encoding:** Inteiros com sinal usam mapeamento ZigZag: $n \rightarrow (n \gg 1) \oplus (-(n \ \& \ 1))$, garantindo que inteiros pequenos ocupem apenas 1 byte.
- **Cabeçalho de Campos Delta-Packed:**
  - Byte único: `(delta << 4) | type_id`.
  - Se $\Delta > 15$, o byte é `(0 << 4) | type_id` seguido pelo field_id em varint.
- **Tipos Primitivos:**
  - `0x01` / `0x02`: True / False (embutidos diretamente no byte de tipo sem payload extra).
  - `0x05` / `0x06`: Inteiros I32 / I64 (ZigZag varint).
  - `0x08`: Binário/String (Varint length prefix + bytes UTF-8).
  - `0x09`: Lista (Tamanho em 4 bits ou varint seguido de tipo de elemento).
  - `0x0C`: Struct aninhado (terminado com `0x00` CTYPE_STOP).

---

## 3. Dissecação da Amostra de Telemetria (`telemetry_sample.parquet`)

Executando nosso dissector [`scripts/parse_parquet_binary.py`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/scripts/parse_parquet_binary.py) sobre uma amostra de telemetria analítica com 6 linhas e 8 colunas:

- **Tamanho Total:** 2.685 bytes
- **Tamanho do Metadado:** 1.734 bytes
- **Offset do Metadado:** `0x000003AF`
- **Versão:** Parquet v2 (`parquet-cpp-arrow version 26.0.0`)
- **Esquema:**
  - `event_id`: INT64
  - `player_nickname`: BYTE_ARRAY (String)
  - `weapon_name`: BYTE_ARRAY (String)
  - `map_name`: BYTE_ARRAY (String)
  - `is_headshot`: BOOLEAN (armazenado em bit-packing com zero overhead)
  - `damage`: DOUBLE (64-bit IEEE 754)
  - `distance_units`: DOUBLE (64-bit IEEE 754)
  - `ping_ms`: INT64
- **Compressão e Encodings:**
  - Codec: Snappy em todos os chunks.
  - Encodings: `PLAIN`, `BIT_PACKED` e `BYTE_STREAM_SPLIT`.

---

## 4. Próximos Passos
- Implementar decodificação do stream de dados das páginas (`DataPageHeaderV1` / `DataPageHeaderV2`) e descompressão Snappy pura em Python.
- Analisar a estrutura de Bloom Filters do Parquet (`SplitBlockBloomFilter`) para data skipping a nível de arquivo.

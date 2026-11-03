# Target: Apache Parquet Columnar Storage Binary Format

## Contexto
O Apache Parquet é o formato colunar padrão da indústria em big data, lakehouses e pipelines analíticos de alta performance (Meta Presto/Trino, Spark, DuckDB, Arrow).

Diferente de formatos orientados a linha (CSV, JSON, SQLite), o Parquet armazena dados verticalmente (por coluna), utilizando técnicas avançadas de compressão e codificação bit-level.

## Objetivos de Engenharia Reversa
1. **Dissecação Estrutural de Rodapé (Footer-First Architecture):**
   - Entender por que o Parquet armazena seus metadados essenciais no rodapé do arquivo em vez do cabeçalho.
   - Decodificar os 4 bytes finais do magic number (`PAR1`), os 4 bytes de tamanho do FileMetaData e o Thrift Compact Protocol.
2. **Hierarquia de Metadados e Esquemas:**
   - Deserializar `FileMetaData`, `RowGroup`, `ColumnChunk` e `PageHeader` diretamente sem bibliotecas pesadas de terceiros.
3. **Encodings e Compressão no Nível de Bits:**
   - Inspecionar streams comprimidos (Snappy, ZSTD, Gzip) e encodings bit-packing (RLE, PLAIN, DELTA).
   - Mapear dicionários de valores únicos e índices de estatísticas (min/max, null_count) para data skipping.

## Estrutura do Alvo
- `data/` — Amostras de arquivos Parquet geradas para dissecação binária.
- `scripts/` — Scripts de dissecação de bytes e deserializadores Thrift customizados.

# Engenharia Reversa do Formato Binário ONNX Protobuf (`.onnx`)

Alvo: [`targets/ml-model-format-re/README.md`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/targets/ml-model-format-re/README.md)  
Script: [`scripts/parse_onnx_binary.py`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/scripts/parse_onnx_binary.py)  
Amostra: [`tiny_conv_gemm_sample.onnx`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/targets/ml-model-format-re/data/tiny_conv_gemm_sample.onnx)  
Data: 2026-11-19

---

## 1. Layout Wire-Level Protocol Buffers (Sem Dependência de `onnx`/`protobuf`)

Um arquivo `.onnx` não possui magic bytes fixos nem cabeçalho binário próprio: ele é uma mensagem `ModelProto` serializada diretamente no formato binário **Protocol Buffers v3** (`onnx.proto3`).

Cada campo no fluxo de bytes segue a estrutura `[tag][payload]`:

```
tag        = varint_LEB128((field_number << 3) | wire_type)
field_num  = tag >> 3
wire_type  = tag & 0x07
```

### Wire Types Suportados

| `wire_type` | Nome | Tamanho / Layout | Uso em ONNX |
|---|---|---|---|
| `0` | `VARINT` | LEB128 (1–10 bytes; `int64` negativo usa complemento de 2 em 64 bits = 10 bytes) | `ir_version`, `model_version`, `data_type`, `dims` (unpacked), `AttributeProto.i` |
| `1` | `I64` | 8 bytes little-endian (`<d` / `<Q`) | `TensorProto.double_data` (unpacked) |
| `2` | `LEN` | `length (varint)` + `length` bytes | Strings UTF-8, submensagens (`GraphProto`, `NodeProto`, `TensorProto`), `raw_data`, campos repetidos **packed** |
| `5` | `I32` | 4 bytes little-endian (`<f` / `<I`) | `AttributeProto.f`, `TensorProto.float_data` (unpacked) |

> **Campos Packed vs Unpacked:** Em `proto3`, campos escalares repetidos (`dims`, `ints`, `float_data`, `int64_data`) são normalmente codificados como `wire_type = 2` (concatenação contígua precedida pelo comprimento total em bytes), mas arquivos exportados por versões legadas podem emiti-los como múltiplas ocorrências individuais (`wire_type = 0` ou `5`). O dissector trata ambas as formas de modo transparente.

---

## 2. Mapa de Field Numbers (`onnx.proto3`)

### `ModelProto` (Mensagem Raiz)

| Field # | Nome | Tipo Protobuf | Descrição |
|---|---|---|---|
| `1` | `ir_version` | `int64` (`0`) | Versão do ONNX IR (ex.: `9`) |
| `2` | `producer_name` | `string` (`2`) | Framework/exportador (ex.: `pytorch`, `pure-python-onnx-re`) |
| `3` | `producer_version` | `string` (`2`) | Versão do exportador |
| `4` | `domain` | `string` (`2`) | Domínio reverso do modelo |
| `5` | `model_version` | `int64` (`0`) | Versão semântica do modelo |
| `6` | `doc_string` | `string` (`2`) | Documentação embutida |
| `7` | `graph` | `GraphProto` (`2`) | Grafo computacional principal |
| `8` | `opset_import` | `repeated OperatorSetIdProto` (`2`) | `1: domain` (string, vazio = `ai.onnx`), `2: version` (int64) |
| `14` | `metadata_props` | `repeated StringStringEntryProto` (`2`) | Pares chave-valor (`1: key`, `2: value`) |

### `GraphProto`

| Field # | Nome | Tipo Protobuf | Descrição |
|---|---|---|---|
| `1` | `node` | `repeated NodeProto` (`2`) | Operadores em ordem topológica |
| `2` | `name` | `string` (`2`) | Nome do grafo |
| `5` | `initializer` | `repeated TensorProto` (`2`) | Pesos/constantes pré-inicializados |
| `10` | `doc_string` | `string` (`2`) | Descrição do grafo |
| `11` | `input` | `repeated ValueInfoProto` (`2`) | Entradas do grafo (com shape simbólico/estático) |
| `12` | `output` | `repeated ValueInfoProto` (`2`) | Saídas do grafo |
| `13` | `value_info` | `repeated ValueInfoProto` (`2`) | Tensores intermediários anotados |

### `NodeProto` & `AttributeProto`

- **`NodeProto`**: `1: input` (repeated string), `2: output` (repeated string), `3: name` (string), `4: op_type` (string), `5: attribute` (repeated `AttributeProto`), `7: domain` (string).
- **`AttributeProto`**: `1: name` (string), `2: f` (float32), `3: i` (int64), `4: s` (bytes), `5: t` (`TensorProto`), `7: floats` (packed/unpacked), `8: ints` (packed/unpacked), `9: strings` (repeated bytes), `20: type` (`AttributeType` enum).

### `TensorProto`

| Field # | Nome | Tipo Protobuf | Observação |
|---|---|---|---|
| `1` | `dims` | `repeated int64` (`2` ou `0`) | Dimensões do tensor (`num_elements = prod(dims)`) |
| `2` | `data_type` | `int32` (`0`) | Enum `DataType` (`1=FLOAT`, `6=INT32`, `7=INT64`, `10=FLOAT16`, `16=BFLOAT16`, etc.) |
| `4` / `5` / `7` / `10` / `11` | `*_data` | `repeated` tipado | Armazenamento alternativo para tensores pequenos |
| `8` | `name` | `string` (`2`) | Nome referenciado pelos `NodeProto.input` |
| `9` | `raw_data` | `bytes` (`2`) | Buffer contíguo little-endian dos pesos (padrão de produção) |
| `13` | `external_data` | `repeated StringStringEntryProto` (`2`) | Referência a arquivo externo (`location`, `offset`, `length`) para modelos >2 GiB |
| `14` | `data_location` | `int32` (`0`) | `0=DEFAULT` (inline), `1=EXTERNAL` |

### `ValueInfoProto` (Shapes Simbólicos e Estáticos)

```
ValueInfoProto (1: name, 2: TypeProto)
  └─ TypeProto (1: TypeProto.Tensor)
       └─ TypeProto.Tensor (1: elem_type, 2: TensorShapeProto)
            └─ TensorShapeProto (1: repeated Dimension)
                 └─ Dimension (1: dim_value [int64] | 2: dim_param [string, ex: "batch"])
```

---

## 3. Comparativo Técnico: `ONNX` vs `GGUF` v3 vs `Safetensors` vs `Pickle`

| Dimensão | `ONNX` (`.onnx`) | `GGUF` v3 (`.gguf`) | `Safetensors` (`.safetensors`) | PyTorch Pickle (`.pt`/`.bin`) |
|---|---|---|---|---|
| **Escopo** | **Grafo completo + Pesos** (arquitetura autossuficiente) | Metadados + Pesos quantizados | Apenas Pesos + Metadados leves | Objetos Python arbitrários |
| **Codificação** | Protocol Buffers v3 (varints LEB128 + `raw_data`) | Header binário fixo + KV tipado + padding 32B | Header JSON UTF-8 + buffer contíguo | ZIP + bytecode Pickle |
| **Segurança** | Sem execução de código no parse | Sem execução de código | Sem execução de código | Vulnerável a RCE (`pickle.loads`) |
| **Alinhamento `mmap`** | Não alinhado nativamente (limite Protobuf de 2 GiB exige `external_data`) | 32 bytes (alinhamento explícito) | Contíguo via `data_offsets` | Requer desserialização |
| **Uso Principal** | Interoperabilidade cross-runtime (ONNX Runtime, TensorRT, CoreML) | Inferência local LLM (`llama.cpp`) | Distribuição/treino seguro (Hugging Face) | Legado PyTorch |

---

## 4. Uso e Validação (`scripts/parse_onnx_binary.py`)

```powershell
# Self-test completo (gera .onnx sintético em temp dir e valida todos os campos)
python scripts/parse_onnx_binary.py --self-test

# Gerar amostra sintética Conv + Relu + Flatten + Gemm (47 parâmetros, 188 B raw_data)
python scripts/parse_onnx_binary.py --generate-sample targets/ml-model-format-re/data/tiny_conv_gemm_sample.onnx

# Inspecionar modelo (.onnx) com resumo legível ou saída JSON estruturada
python scripts/parse_onnx_binary.py targets/ml-model-format-re/data/tiny_conv_gemm_sample.onnx
python scripts/parse_onnx_binary.py targets/ml-model-format-re/data/tiny_conv_gemm_sample.onnx --json
```

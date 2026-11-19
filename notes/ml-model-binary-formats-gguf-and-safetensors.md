# Engenharia Reversa de Formatos Binários de Modelos ML: `GGUF` v3 vs `Safetensors`

Alvo: `targets/ml-model-format-re/`  
Script: [`scripts/parse_ml_model_formats.py`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/scripts/parse_ml_model_formats.py)  
Data: 2026-11-19

---

## 1. Layout Binário `GGUF` v3 (`.gguf` — `llama.cpp`)

```
+0x00 (4B):  magic = "GGUF" (0x46554747)
+0x04 (4B):  version = 3 (uint32 LE)
+0x08 (8B):  tensor_count (uint64 LE)
+0x10 (8B):  metadata_kv_count (uint64 LE)
+0x18 (...): Metadata KV Array: [len(u64) + utf8_key][value_type(u32)][typed_value]
+...  (...): Tensor Info Array: [len(u64) + utf8_name][n_dims(u32)][dims(u64[])][ggml_type(u32)][rel_offset(u64)]
+...  (...): Padding de alinhamento para múltiplo de 32 bytes (default general.alignment)
+...  (...): Bloco contíguo de tensores quantizados (F32, F16, Q4_0, Q8_0, Q4_K, etc.)
```

## 2. Layout Binário `Safetensors` (`.safetensors` — Hugging Face)

```
+0x00 (8B):  header_size (uint64 LE)
+0x08 (NB):  Cabeçalho JSON UTF-8: {"__metadata__": {...}, "<tensor>": {"dtype": "F32", "shape": [2,2], "data_offsets": [0,16]}}
+8+N  (...): Bloco contíguo de tensores brutos (zero-copy mmap, sem execução de código / seguro contra Pickle RCE)
```

## 3. Comparativo Técnico

| Dimensão | `GGUF` v3 (`.gguf`) | `Safetensors` (`.safetensors`) | PyTorch Pickle (`.pt`/`.bin`) |
|---|---|---|---|
| **Segurança** | Sem execução de código | Sem execução de código | Vulnerável a RCE (`pickle.loads`) |
| **Alinhamento `mmap`** | 32 bytes (configurável) | Contíguo via `data_offsets` | Requer desserialização ZIP/Pickle |
| **Quantização Nativa** | Sim (`Q4_0`, `Q4_K`, `Q8_0`, etc.) | Tipos padrão (`F32`, `F16`, `BF16`, `I8`) | Depende de código Python |
| **Uso Principal** | Inferência local CPU/GPU (`llama.cpp`) | Distribuição & treino seguro (HF/PyTorch) | Legado |

# Target: ML Model Binary Formats RE (`.gguf`, `.safetensors` & `.onnx`)

## Visão Geral
- **Alvo:** Formatos binários de serialização de grafos e pesos de modelos de ML/LLM (`GGUF` v3 do `llama.cpp`, `Safetensors` do Hugging Face e `ONNX` Protobuf).
- **Objetivo:** Dissecação byte a byte sem dependências externas (stdlib puro Python) de wire format Protobuf, metadados, alinhamento `mmap`, descritores de tensores, grafos computacionais e segurança contra execução arbitrária de código (vs `pickle`).

## Artefatos
- Dissector & Gerador (`GGUF` / `Safetensors`): [`scripts/parse_ml_model_formats.py`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/scripts/parse_ml_model_formats.py)
- Dissector & Gerador (`ONNX` Protobuf wire-level): [`scripts/parse_onnx_binary.py`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/scripts/parse_onnx_binary.py)
- Amostras Binárias: `data/tiny_llm_sample.gguf`, `data/tiny_llm_sample.safetensors` e `data/tiny_conv_gemm_sample.onnx`
- Documentação Técnica:
  - [`notes/ml-model-binary-formats-gguf-and-safetensors.md`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/notes/ml-model-binary-formats-gguf-and-safetensors.md)
  - [`notes/onnx-protobuf-binary-format-reverse-engineering.md`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/notes/onnx-protobuf-binary-format-reverse-engineering.md)

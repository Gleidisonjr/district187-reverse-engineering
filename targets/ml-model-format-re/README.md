# Target: ML Model Binary Formats RE (`.gguf` & `.safetensors`)

## Visão Geral
- **Alvo:** Formatos binários de serialização de pesos de modelos de ML/LLM (`GGUF` v3 do `llama.cpp` e `Safetensors` do Hugging Face).
- **Objetivo:** Dissecação byte a byte sem dependências externas (`struct` puro Python) de metadados, alinhamento `mmap`, descritores de tensores e segurança contra execução arbitrária de código (vs `pickle`).

## Artefatos
- Dissector & Gerador: [`scripts/parse_ml_model_formats.py`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/scripts/parse_ml_model_formats.py)
- Amostras Binárias: `data/tiny_llm_sample.gguf` e `data/tiny_llm_sample.safetensors`
- Documentação Técnica: [`notes/ml-model-binary-formats-gguf-and-safetensors.md`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/notes/ml-model-binary-formats-gguf-and-safetensors.md)

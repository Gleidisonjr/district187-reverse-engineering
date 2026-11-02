---
name: data-extraction
description: Use quando eu quiser extrair dados estruturados de um alvo já investigado — APIs, payloads de rede, formatos de arquivo, bancos embutidos.
---

# Data Extraction Workflow

## 1. Identificar fonte de dados
- **API/rede**: use REA com captura HAR/SAZ ou análise de website
- **Banco SQLite embutido**: use REA `inspect_sqlite_database`
- **Formato binário próprio**: parsing manual com Python + `struct`
- **Arquivo de modelo ML**: use REA para inspecionar GGUF/safetensors

## 2. Mapear o schema
- Documente os campos, tipos e endpoints em `notes/schema-<alvo>.md`
- Identifique campos sensíveis (tokens, IDs de usuário, eventos de analytics)

## 3. Escrever script de extração
- Crie `scripts/extract-<alvo>-data.py`
- Salve output em `targets/<alvo>/data/` como CSV ou JSON
- Documente dependências em `scripts/requirements.txt`

## 4. Analisar com Python/SQL
- Use pandas para análise exploratória dos dados extraídos
- Se relevante, construa queries SQL para padrões de uso
- Documente achados em `notes/data-analysis-<alvo>.md`

## 5. Encerrar
- Atualize `projects/now.md` com o que foi extraído
- Registre implicações de privacidade/segurança em `decisions.md`

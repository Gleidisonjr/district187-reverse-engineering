# Target: District 187: Sin Streets (S2 Online / S2 Son Silah)

## Visão Geral
- **Nome original:** S2 Online (Coreia) / District 187: Sin Streets (Global / Netmarble) / S2 Son Silah (Turquia / Joygame)
- **Desenvolvedor:** CJ GameLab / Netmarble
- **Engine:** LithTech Jupiter EX (C++ / DirectX 9)
- **Tipo de alvo:** Jogo tático multiplayer online (cliente desktop Windows x86)
- **Objetivo:** 
  1. Analisar a integridade e segurança dos arquivos recuperados (`S2.rar`).
  2. Extrair assets (modelos 3D de armas, mapas, áudio, tabelas de balanço).
  3. Mapear o protocolo de rede e pacotes do cliente para viabilizar um emulador de servidor local em Python.
  4. Apoiar a base de um FPS próprio moderno (Godot 4 / Unreal Engine 5).

## Status
- **Status:** Em progresso (extração concluída, formato de arquivos revertido, modelos 3D convertidos para OBJ, protocolo Hermit mapeado, mock server implementado e meta de balanceamento analisado)
- **Data de início:** 2026-11-02
- **Origem dos arquivos:** Comunidade `s2privateserver.com` (Google Drive / S2.rar, ~969 MB)

## Ferramentas utilizadas
- **REA (MCP):** Inspeção de PE/Imports, Native Exports, Managed Members (.NET CIL)
- **Python:**
  - Extração de containers LithTech: [`scripts/extract-lithtech-res.py`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/scripts/extract-lithtech-res.py)
  - Conversor de modelos 3D MODL para OBJ: [`scripts/convert-model00p-to-obj.py`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/scripts/convert-model00p-to-obj.py)
  - Mock Server de protocolo Hermit: [`scripts/d187-mock-server.py`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/scripts/d187-mock-server.py)
  - Análise exploratória de balanceamento (pandas): [`scripts/analyze-weapon-meta.py`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/scripts/analyze-weapon-meta.py)
  - Sincronizador de updates: [`scripts/sync-district-187-updates.py`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/scripts/sync-district-187-updates.py)
- **Antivírus:** Kaspersky CLI 21.26 (`avp.com`)

## Arquivos e Notas
- `downloads/S2.rar` — Pacote bruto compactado
- `client/S2/` — Cliente completo descompactado e sincronizado com os updates
- `extracted/tables/` — 54 tabelas CSV de balanceamento e dados de jogo
- `extracted/models/` — 585 modelos 3D (.Model00p)
- `extracted/weapons/` — 1.014 assets completos de armas extraídos com estrutura de pastas canônica original
- `extracted/converted/` — 526 modelos convertidos para Wavefront OBJ acompanhados de arquivos de material `.mtl` e texturas `.png`
- `../../projects/godot-fps/` — Base jogável em Godot 4 integrando as armas, texturas e balanceamento calibrado
- [`notes/district-187-security-scan.md`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/notes/district-187-security-scan.md) — Relatório de varredura antivírus e integridade de hashes
- [`notes/lithtech-hbek-archive-format.md`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/notes/lithtech-hbek-archive-format.md) — Engenharia reversa completa do formato LithTech Jupiter EX HBEK (.Res00 / .ResDt)
- [`notes/lithtech-directory-tree-structure.md`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/notes/lithtech-directory-tree-structure.md) — Engenharia reversa da tabela de 2.305 diretórios e mapeamento 1:1 de caminhos
- [`notes/lithtech-model00p-format.md`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/notes/lithtech-model00p-format.md) — Engenharia reversa das malhas 3D MODL v33 e conversão para OBJ
- [`notes/district-187-network-and-launch-architecture.md`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/notes/district-187-network-and-launch-architecture.md) — Parâmetros de linha de comando, portas e hooking de socket
- [`notes/district-187-client-internals-and-launch-hooks.md`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/notes/district-187-client-internals-and-launch-hooks.md) — Desarmamento de proxy DLL injetada, handler Joygame e cvars de desenvolvedor
- [`notes/district-187-weapon-balance-analysis.md`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/notes/district-187-weapon-balance-analysis.md) — Análise estatística de dano, recuo, alcance e STK das 178 armas

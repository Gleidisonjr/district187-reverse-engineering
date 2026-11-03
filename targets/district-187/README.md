# Target: District 187: Sin Streets (S2 Online / S2 Son Silah)

## Visão Geral
- **Nome original:** S2 Online (Coreia) / District 187: Sin Streets (Global / Netmarble) / S2 Son Silah (Turquia / Joygame)
- **Desenvolvedor:** CJ GameLab / Netmarble
- **Engine:** LithTech Jupiter EX (C++ / DirectX 9)
- **Tipo de alvo:** Jogo tático multiplayer online (cliente desktop Windows x86)
- **Objetivo:** 
  1. Analisar a integridade e segurança dos binários e bibliotecas nativas.
  2. Extrair assets (modelos 3D de armas, mapas, áudio, tabelas de balanço).
  3. Mapear o protocolo de rede e pacotes do cliente para viabilizar um emulador de servidor local em Python.
  4. Executar e preservar o jogo em seu motor original nativo LithTech Jupiter EX (idêntico ao S2 Rebirth).

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
  - Parser de entidades e minimapas World00p: [`scripts/inspect_world00p.py`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/scripts/inspect_world00p.py)
  - Gerador de NavMeshes e rotas A*: [`scripts/d187_navmesh_generator.py`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/scripts/d187_navmesh_generator.py)
  - Gerador de Heatmaps 2D KDE: [`scripts/generate_match_heatmap.py`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/scripts/generate_match_heatmap.py)
  - Extrator de Áudio FMOD FSB5: [`scripts/extract_fmod_audio.py`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/scripts/extract_fmod_audio.py)
  - Biblioteca serializadora de protocolo NBattle: [`scripts/d187_protocol.py`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/scripts/d187_protocol.py)
  - Sincronizador de updates: [`scripts/sync-district-187-updates.py`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/scripts/sync-district-187-updates.py)
- **Antivírus:** Kaspersky CLI 21.26 (`avp.com`)

## Arquivos e Notas
- `downloads/S2.rar` — Pacote bruto compactado
- `client/S2/` — Cliente completo descompactado e sincronizado com os updates
- `extracted/tables/` — 54 tabelas CSV de balanceamento e dados de jogo
- `extracted/models/` — 585 modelos 3D (.Model00p)
- `extracted/weapons/` — 1.014 assets completos de armas extraídos com estrutura de pastas canônica original
- `extracted/converted/` — 526 modelos convertidos para Wavefront OBJ acompanhados de arquivos de material `.mtl` e texturas `.png`
- `client-rebirth/` — Cliente nativo oficial configurado com gráficos Ultra HD 4K e emulador de servidor local
- [`notes/district-187-security-scan.md`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/notes/district-187-security-scan.md) — Relatório de varredura antivírus e integridade de hashes
- [`notes/lithtech-hbek-archive-format.md`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/notes/lithtech-hbek-archive-format.md) — Engenharia reversa completa do formato LithTech Jupiter EX HBEK (.Res00 / .ResDt)
- [`notes/lithtech-directory-tree-structure.md`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/notes/lithtech-directory-tree-structure.md) — Engenharia reversa da tabela de 2.305 diretórios e mapeamento 1:1 de caminhos
- [`notes/lithtech-model00p-format.md`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/notes/lithtech-model00p-format.md) — Engenharia reversa das malhas 3D MODL v33 e conversão para OBJ
- [`notes/district-187-network-and-launch-architecture.md`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/notes/district-187-network-and-launch-architecture.md) — Parâmetros de linha de comando, portas e hooking de socket
- [`notes/district-187-client-internals-and-launch-hooks.md`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/notes/district-187-client-internals-and-launch-hooks.md) — Desarmamento de proxy DLL injetada, handler Joygame e cvars de desenvolvedor
- [`notes/district-187-weapon-balance-analysis.md`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/notes/district-187-weapon-balance-analysis.md) — Análise estatística de dano, recuo, alcance e STK das 178 armas
- [`notes/district-187-multi-map-geometry-navmesh-and-audio-manifest.md`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/notes/district-187-multi-map-geometry-navmesh-and-audio-manifest.md) — Extração dos 29 mapas compilados, NavMeshes A*, Heatmaps 2D de telemetria e extração dos 9 SoundBanks FMOD FSB5 (901 amostras)
- [`notes/d187-login-scaleform-unlock.md`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/notes/d187-login-scaleform-unlock.md) — Engenharia reversa no assembly de `GameClient.dll` (0x10191bd0), desbloqueio do login com `0x00A40221`, Keepalive `0x20084` e Heartbeat `0x5A0101`
- [`notes/d187-apexguard-s2-320-dx-proxy.md`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/notes/d187-apexguard-s2-320-dx-proxy.md) — Causa raiz do erro `ApexGuard S2-320` e crash `R6025` (cadeia de DLLs-proxy `D3DX9_43.dll` -> `dxbase.dll` no `client-rebirth`)
- [`D187_Launcher.bat`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/D187_Launcher.bat) — Launcher gráfico próprio em Python/Tkinter com suporte a partidas Solo contra Bots de IA (Fácil/Médio/Difícil, 1v1 a 8v8, mapas oficiais) e partidas Online/LAN com amigos
- [`launch_game.bat`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/launch_game.bat) — Inicializador direto em 1 clique com verificação automática do servidor Hermit na porta 12000
- [`scripts/d187_web_portal.py`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/scripts/d187_web_portal.py) — Portal Web Standalone bilíngue (Português & English) com Arsenal de 185 armas, ranking de operativos (58 patentes) e cadastro de novas contas em SQLite

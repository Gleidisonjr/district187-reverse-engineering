# District 187: Suite de Modding HBEK (.Res00/.ResDt), MMR Adaptativo, Replay 2D (HLTV) e QoL Windows 11

## Visão Geral
Implementação completa dos 5 pilares de evolução técnica para o ecossistema nativo LithTech Jupiter EX de *District 187: Sin Streets* (`TheRaw.exe` + `GameClient.dll`), cobrindo:
1. **Compilador/Repacker Nativo HBEK (`.Res00` / `.ResDt`) & Localização PT-BR:** [`scripts/pack_lithtech_res.py`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/scripts/pack_lithtech_res.py).
2. **Motor de MMR Competitivo (Elo/TrueSkill), Ajuste Dinâmico de Dificuldade (DDA) e Replay Tático 2D (Estilo HLTV / Scope.gg):** [`scripts/d187_mmr_engine.py`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/scripts/d187_mmr_engine.py) e [`targets/district-187/analytics/match_replay.html`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/targets/district-187/analytics/match_replay.html).
3. **Extensões de Lobby: Loadouts Persistentes (Slots A/B/C), Attachments, Clãs e Comandos Slash In-Game (`/map`, `/bots`, `/give`, `/mmr`, `/loadout`, `/clan`):** [`scripts/d187_lobby_extensions.py`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/scripts/d187_lobby_extensions.py).
4. **Otimizador QoL Windows 11 (Borderless Windowed Instant Alt+Tab, FOV Unlocker 95° e Raw Mouse Input):** [`scripts/d187_qol_optimizer.py`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/scripts/d187_qol_optimizer.py).
5. **Diretor Autoritativo de Bots A* sobre UDP 27888 (`SN_Spawn`, `SN_Move`, `SN_Hit`, `SN_Kill`):** [`scripts/d187_dedicated_gateway.py`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/scripts/d187_dedicated_gateway.py).

---

## 1. Compilador HBEK v2 (`.Res00` / `.ResDt`) & Pacote `CustomMod_PTBR`
O script [`scripts/pack_lithtech_res.py`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/scripts/pack_lithtech_res.py) implementa a construção binária reversa do formato HBEK v2 (`0x4B454248`):
- Gera a tabela de strings iniciada pelo GUID de 16 bytes (`D187_MOD_ARCHIVE`), a tabela de arquivos de 48 bytes por entrada (`<IQQQI16s`) e a árvore de diretórios de 16 bytes por entrada (`<4I`), mantendo a invariante $\sum \text{file\_cnt}_i = \text{num\_files}$.
- Empacota no arquivo `targets/district-187/client-rebirth/Game/CustomMod_PTBR.Res00` (460 B) e `CustomMod_PTBR.ResDt` (2.318 B):
  - `StringDatabase\Portuguese\Game.StrDb00e` (banco binário UTF-16LE de tradução PT-BR).
  - `Database\CompetitiveWeaponBalance.csv` (tabela competitiva calibrada).
  - `Weapons\1_Main\Materials\Custom_Obsidian_Gold.Mat00` (material shader customizado).
- Montado automaticamente no `Default.archcfg` pelo otimizador QoL.

---

## 2. Motor MMR (Elo + DDA) e Replay Tático 2D (`match_replay.html`)
O módulo [`scripts/d187_mmr_engine.py`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/scripts/d187_mmr_engine.py) expande o banco SQLite `targets/district-187/data/s2rebirth.db` com 4 novas tabelas:
- `player_mmr`: Rating Elo, volatilidade, taxa de Headshot (`hs_rate`), TTK médio (`avg_ttk_ms`), patente de habilidade (`Master 187`, `Diamond`, `Platinum`, `Gold`, `Silver`, `Bronze`) e perfil adaptativo de bots (`compute_adaptive_bot_profile`).
- `player_loadouts`: Persistência dos Slots A (Assalto), B (Sniper) e C (CQB), incluindo miras (`EOTech Holographic`, `8x Ballistic Scope`, `Red Dot Reflex`), canos e carregadores.
- `clans`: Registro e ranking de clãs (`[META] Meta Data Science Ops`, `[S2BR]`, `[SWAT]`, `[SIN]`).
- `match_replays`: Gravação tick-a-tick de rounds sobre as malhas A* reais (`twoway`, `thebank`, `Arrival`, `oldtown`, `Kill_Port`), visualizável no player interativo [`targets/district-187/analytics/match_replay.html`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/targets/district-187/analytics/match_replay.html) e na rota `/replay` do Web Portal (`http://localhost:8080/replay`).

---

## 3. Comandos In-Game via Chat (`CQ_Chat` `0x210151` $\rightarrow$ `SN_Chat` `0x210152`)
Integrado ao [`scripts/d187-mock-server.py`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/scripts/d187-mock-server.py) via [`scripts/d187_lobby_extensions.py`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/scripts/d187_lobby_extensions.py):
- `/help` — Lista todos os comandos interativos no chat do lobby/sala.
- `/map <nome>` — Altera dinamicamente o mapa da sala (`twoway`, `thebank`, `Arrival`, `oldtown`, `Kill_Port`, `Ghost_Ship`, `10025_Heaven`).
- `/bots <qtd> <easy|med|hard|adaptive>` — Configura quantidade e dificuldade dos bots.
- `/give <arma>` — Equipa qualquer uma das 185 armas do banco SQLite no slot ativo.
- `/loadout <A|B|C>` — Alterna entre os 3 slots táticos persistentes.
- `/mmr` ou `/stats` — Exibe no chat o Elo atual, Skill Tier, HS%, TTK e perfil DDA.
- `/clan` — Exibe informações e Elo do clã ativo.

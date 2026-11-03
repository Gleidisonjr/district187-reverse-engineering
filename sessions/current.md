# Session Handoff

## Estado atual
- **Agente:** Antigravity (Gemini 3.8 Flash)
- **Alvo ativo:** `targets/district-187/` (District 187 / S2 Rebirth — Motor Nativo LithTech Jupiter EX)
- **Timestamp:** 2026-11-02 22:42
- **Diretriz Absoluta:** 100% foco no executável e motor original LithTech (`TheRaw.exe`, `GameClient.dll`, `Engine_Server.dll`) e emulação de rede/servidor dedicado.
- **Entregas e Correções Consolidadas:**
  1. **Resolução Definitiva do `ApexGuard S2-320` e Crash `R6025 - pure virtual function call`:**
     - Documentado em [`notes/d187-apexguard-s2-320-dx-proxy.md`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/notes/d187-apexguard-s2-320-dx-proxy.md).
     - Diferente do pacote antigo `client/S2` (onde a proxy `D3DX9_43.dll` injetava `TheRawExt.dll`), o cliente `client-rebirth` utiliza uma cadeia de 3 DLLs-proxy verificada pelo `ApexGuard.dll`:
       - `D3DX9_43.dll` (119.864 bytes) -> carrega `dxbase.dll` (ausência na memória dispara `S2-320` e aborta com `R6025`)
       - `StringEditRuntime.dll` (88.120 bytes) -> carrega `strbase.dll` (`S2-321`)
       - `GameDatabase.dll` (88.120 bytes) -> carrega `dbbase.dll` (`S2-322`)
     - A `D3DX9_43.dll` original de 119.864 bytes foi restaurada em `targets/district-187/client-rebirth/D3DX9_43.dll` (com backup da runtime limpa em `D3DX9_43.dll.clean_runtime_bak`). **Nunca substituir `client-rebirth/D3DX9_43.dll` pela DLL do SysWOW64.**
  2. **Resolução Definitiva do Loop Infinito de Login ("Please Wait") & Bind Exclusivo na Porta 12000:**
     - Desmontadas as tabelas de registro de pacotes (`0x10194800` global e `0x10132d10` `CLoginScene`) e RTTI de [`GameClient.dll`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/targets/district-187/client-rebirth/Game/GameClient.dll):
       - A função `0x10191740` é `IsPacketerrorMessage(int err, uint16 origin)` (`0` = sem erro). Quando `SA_JoyGameLogin` (`0x110112`) ou `SA_Login` (`0x110102`) recebe `err == 0`, o cliente mantém `"please wait"` ativo aguardando o término da sequência de sincronização `NLaunch`.
       - O pacote que realmente dispara `ChangeScene(0)` (`0x1004b8a0`) para sair de `LoginScene` (`Scene[10]`) é **`CDispatch_NLaunch_NLock_SN_LockEnd` (`0x10032f30`) com opcode `0x210121`** (o servidor mock anterior enviava `0x210202`, que era `SA_CreateUser`, motivo pelo qual o cliente ficava preso em `"please wait"` infinitamente!).
     - [`scripts/d187-mock-server.py`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/scripts/d187-mock-server.py) atualizado e reiniciado na porta `12000` com `SO_EXCLUSIVEADDRUSE` e todos os opcodes e layouts reais: `SN_UserInfo` (`0x210101`), `SN_RankingInfo` (`0x210105`), `SN_ItemList` (`0x210111`, 27B/item), `SN_Record` (`0x210103`, 224B payload), `SN_LockEnd` (`0x210121`), `SN_ServerInfo` (`0x220101`, 98B/servidor), `SN_ChannelList` (`0x220102`, 57B/canal), `CQ_Join`/`SA_Join` (`0x110124`/`0x110125`) e `CQ_EnterUser`/`SA_EnterUser` (`0x220111`/`0x220112`).
     - Documentado em [`notes/d187-login-scaleform-unlock.md`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/notes/d187-login-scaleform-unlock.md) e verificado com [`scripts/test_client_handshake_smoke.py`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/scripts/test_client_handshake_smoke.py).
  3. **Launchers Oficiais Unificados & Limpeza da Raiz:**
     - [`D187_Launcher.bat`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/D187_Launcher.bat) -> Abre a interface gráfica oficial [`scripts/d187_launcher.py`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/scripts/d187_launcher.py) (Tkinter Dark/Gold) com modos Solo (Bots) e Online/LAN, monitor da porta 12000 e botão para o Web Portal.
     - [`launch_game.bat`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/launch_game.bat) -> Inicializador direto em 1 clique que verifica/inicia o servidor Hermit na porta 12000 e dispara `TheRaw.exe` com `__COMPAT_LAYER=RunAsInvoker`.
     - Launchers `.bat`/`.ps1` legados movidos para `scripts/legacy_launchers/` e scripts de diagnóstico movidos para `scripts/probes/`.
  4. **Separação Limpa de Portas Web (8080 vs 8081) e Gateway UDP (27888):**
     - [`scripts/d187_web_portal.py`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/scripts/d187_web_portal.py) na porta `8080`: Portal Web Standalone bilíngue (PT-BR/EN) com Arsenal de 185 armas, Ranking (58 patentes) e registro de contas SQLite.
     - [`scripts/d187_web_panel.py`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/scripts/d187_web_panel.py) na porta `8081`: Painel Técnico de Controle com `ServiceManager` apontando para [`scripts/d187_dedicated_gateway.py`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/scripts/d187_dedicated_gateway.py) (UDP 27888) e [`launch_game.bat`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/launch_game.bat).
  5. **Suite Completa dos 5 Pilares de Evolução (`pack_lithtech_res.py`, `d187_mmr_engine.py`, `d187_lobby_extensions.py`, `d187_qol_optimizer.py`):**
     - **Compilador HBEK `.Res00` / `.ResDt` & Mod PT-BR:** [`scripts/pack_lithtech_res.py`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/scripts/pack_lithtech_res.py) gera `targets/district-187/client-rebirth/Game/CustomMod_PTBR.Res00` e `.ResDt` com tradução PT-BR (`Game.StrDb00e`), tabela de balanceamento competitivo e material customizado, montado automaticamente no `Default.archcfg`.
     - **Motor MMR (Elo + DDA), Loadouts (Slots A/B/C), Clãs & Replay 2D (HLTV / Scope.gg):** [`scripts/d187_mmr_engine.py`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/scripts/d187_mmr_engine.py) popula `player_mmr`, `player_loadouts`, `clans` e `match_replays` em `s2rebirth.db` e gera o player interativo [`targets/district-187/analytics/match_replay.html`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/targets/district-187/analytics/match_replay.html) (acessível no Launcher e em `/replay` no Web Portal).
     - **Comandos Slash In-Game via Chat (`CQ_Chat` `0x210151` -> `SN_Chat` `0x210152`):** [`scripts/d187_lobby_extensions.py`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/scripts/d187_lobby_extensions.py) integrado ao [`scripts/d187-mock-server.py`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/scripts/d187-mock-server.py) (`/map`, `/bots`, `/give`, `/loadout`, `/mmr`, `/clan`, `/help`).
     - **Otimizador QoL Windows 11:** [`scripts/d187_qol_optimizer.py`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/scripts/d187_qol_optimizer.py) aplica *Borderless Windowed Fullscreen* via Win32 API (Alt+Tab instantâneo), `Fov 95` e `UseRawMouseInput 1`.
     - **Diretor Autoritativo de Bots A* sobre UDP 27888:** `NavMeshBotDirector` em [`scripts/d187_dedicated_gateway.py`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/scripts/d187_dedicated_gateway.py) transmitindo `SN_Spawn`, `SN_Move`, `SN_Hit` e `SN_Kill` sobre os waypoints reais dos mapas.
     - Documentação em [`notes/district-187-modding-mmr-replay-and-qol-suite.md`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/notes/district-187-modding-mmr-replay-and-qol-suite.md).
  6. **Alvo Paralelo: Engenharia Reversa de Armazenamento Colunar (Apache Parquet):**
     - Dissector binário puro Python [`scripts/parse_parquet_binary.py`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/scripts/parse_parquet_binary.py) e nota [`notes/parquet-columnar-binary-format-reverse-engineering.md`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/notes/parquet-columnar-binary-format-reverse-engineering.md).

## Próximo Passo
- Para jogar ou testar o cliente nativo:
  - Executar `.\D187_Launcher.bat` (Launcher Gráfico) ou `.\launch_game.bat` (Inicialização Direta).
  - Servidor Hermit (`scripts/d187-mock-server.py`) está ativo com bind exclusivo em `127.0.0.1:12000`.
  - Confirmar no desktop que o pop-up `S2-320` / `R6025` não ocorre mais com `client-rebirth/D3DX9_43.dll` restaurada (119.864 bytes) e validar a transição pós-login para o Lobby.

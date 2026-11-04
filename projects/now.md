# Projetos Ativos

## Em andamento

### [TARGET] DDTank Clássico (DDClassico.com / 7Road v2.0.5) — Servidor Local Privado & Engenharia Reversa
- **Status:** em andamento (2026-11-03)
- **Repositório GitHub:** `https://github.com/Gleidisonjr/ddtank-reverse-engineering` (branch `main`)
- **Foco Absoluto:** Engenharia reversa completa do cliente Flash e emulação autoritativa em Python/Tailscale para execução local e multiplayer entre amigos.
- **Entregas Concluídas:**
  - **Fase 1 Concluída (Ambiente Standalone & Triplo Daemon):**
    - Criado o sub-projeto isolado em `projects/ddtank-server/` com Git independente.
    - Implementados os 3 daemons: CDN Local HTTP 8080 (`src/ddt_local_cdn.py`), Game Core Socket Server TCP 9200 (`src/ddt_server.py`) e Flash Socket Policy Server TCP 843 (`src/ddt_policy_server.py`).
    - Banco de dados SQLite de inventário e contas (`data/ddtank.db`).
    - Launcher integrado em 1 clique [`DDTank_Launcher.bat`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/projects/ddtank-server/DDTank_Launcher.bat).
  - **Fase 2 Concluída (Resolução de Tela Preta no Splash):**
    - Bytecode AVM2 descompilado em `Loading.swf`: identificada a query E4X `this._config..config[0].REQUEST_PATH.@value`.
    - Corrigido `config.xml` com hierarquia aninhada `<config><config>...</config></config>`.
  - **Fase 3 Concluída (Bypass de 33% & Descoberta do Arquivo ZIP FZip xml.png):**
    - Bytecode AVM2 descompilado em `UIModuleLoader`: comprovado que `xml.png` é um ZIP com `core.xml` do `ComponentFactory`.
    - Criado gerador [`generate_ui_xml_png.py`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/projects/ddtank-server/tools/generate_ui_xml_png.py) e roteamento de barras duplas (`//`) no CDN.
  - **Fase 4 Concluída (Bypass de 70%, Eliminação de 404s e Inicialização do Core 2.png):**
    - Bytecode AVM2 descompilado em `1.swf` (`MainFigureView.tryEnter`): diagnosticado que `<TRAINER_STANDALONE value="true">` forçava `enterTrain()` que tentava executar `3.png` (Trainer) que retornava imagem PNG inválida.
    - Desativado `TRAINER_STANDALONE` para `false` no `config.xml`, roteando diretamente para `GameLuncher.loadCore()` e `2.png` (núcleo real de 3.23 MB).
    - Gerados SWFs AS3 válidos de 31 bytes via [`generate_dummy_swfs.py`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/projects/ddtank-server/tools/generate_dummy_swfs.py) para `choicefigure.swf`, `roadcomponent.swf` e `3.png`.
    - Fallback dinâmico implementado no CDN para fornecer SWFs válidos sob demanda para qualquer módulo de interface não mapeado.
    - Explicitado `IP="127.0.0.1"` em `ServerList.xml` para conexão direta no Game Server local TCP 9200.
    - Documentação técnica em [`notes/ddtank-70-percent-preloader-and-trainer-standalone-bypass.md`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/notes/ddtank-70-percent-preloader-and-trainer-standalone-bypass.md).
- **Alvo:** `projects/ddtank-server/`

### [TARGET] District 187: Sin Streets (S2 Online / S2 Rebirth) — Motor Nativo LithTech
- **Status:** em andamento (2026-11-02)
- **Foco Absoluto:** Executável original (`TheRaw.exe`), motor nativo LithTech Jupiter EX e servidor oficial/emulador (arquitetura idêntica ao S2 Rebirth, sem engines externas).
- **Fase atual:**
  - **Fase 1 Concluída (Gráficos Ultra HD + Tradução no Motor Nativo):**
    - Baixados e validados os 1.72 GB do pacote de texturas HD oficial (`HD1.ResDt` a `HD6.ResDt`).
    - `Default.archcfg` atualizado para montagem automática das archives 2K/4K no motor LithTech.
    - `settings.cfg` e `autoexec.cfg` configurados com `GraphicQualityLevel 3`, `BindTexturesMipOffset 0` e `MaxFPS 0` (144+ FPS destravado).
    - Idioma inglês nativo ativado (3.923 strings).
    - Scripts de inicialização oficiais na raiz:
      - [`D187_Launcher.bat`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/D187_Launcher.bat) (Launcher Gráfico oficial em Tkinter [`scripts/d187_launcher.py`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/scripts/d187_launcher.py))
      - [`launch_game.bat`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/launch_game.bat) (Inicialização direta com verificação/subida automática do servidor Hermit local em `127.0.0.1:12000`)
      - Launchers `.bat`/`.ps1` antigos arquivados em `scripts/legacy_launchers/`
  - **Fase 1.5 Concluída (Data Analytics & Telemetria Web Portal):**
    - Criado pipeline ETL [`scripts/build_s2rebirth_dataset.py`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/scripts/build_s2rebirth_dataset.py) gerando `targets/district-187/data/s2rebirth.db` (185 armas com stats reais de combate, 750 itens, 58 patentes, 155 mapas, 1.524 itens de loja).
    - Criado CLI Client [`scripts/s2rebirth_api_client.py`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/scripts/s2rebirth_api_client.py) para consulta em tempo real da telemetria de 1.140 jogadores, 73 clãs e histórico de partidas.
    - Documentada a arquitetura REST em [`notes/s2-rebirth-hd-pack-and-web-portal-architecture.md`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/notes/s2-rebirth-hd-pack-and-web-portal-architecture.md).
  - **Fase 2 Concluída (Engenharia Reversa Completa do Handshake & Cifra Hermit):**
    - Mapeada a cifra de fluxo proprietária em `TheRaw.exe` (IEEE 802.3 CRC32 lookup table em `0x802a58`, chave inicial `0x0F`).
    - Descoberta a máquina de estados Hermit (`0x20080` Handshake Request -> `0x20081` Response -> `0x20082` ACK -> `0x20083` Pong).
    - Descoberto o manipulador Scaleform `0x100d74a0` em `GameClient.dll` que zera a flag de bloqueio (`mov [eax+0x64], 0` em `0x100d74db`) ao receber `SA_JoyGameLogin` (`0x110112`) cifrado com `ResultCode = 0` e `AccountID = 1001`.
    - Servidor [`scripts/d187-mock-server.py`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/scripts/d187-mock-server.py) totalmente reconstruído e ativo na porta 12000.
    - Documentação em [`notes/district-187-hermit-protocol-and-handshake.md`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/notes/district-187-hermit-protocol-and-handshake.md).
  - **Fase 3 Concluída (Protocolo Mestre, Inventário VIP, Mapas LithTech e Painel Web):**
    - Mapeados todos os 326 pacotes da engine em [`targets/district-187/data/d187_protocol_schema.json`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/targets/district-187/data/d187_protocol_schema.json) via [`scripts/map_district187_protocol.py`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/scripts/map_district187_protocol.py).
    - Criada a biblioteca mestre serializadora de pacotes [`scripts/d187_protocol.py`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/scripts/d187_protocol.py) e documentação em [`notes/district-187-full-network-protocol-specification.md`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/notes/district-187-full-network-protocol-specification.md).
    - Criado o gerador de perfil VIP e inventário de lobby [`scripts/d187_profile_service.py`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/scripts/d187_profile_service.py) (Rank 58, 185 armas, Gold/Cash infinitos, pacotes `SN_UserInfo`, `SN_ItemList`, `SN_Record`, `SN_LockEnd`).
    - Desenvolvido o parser LithTech v113 [`scripts/inspect_world00p.py`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/scripts/inspect_world00p.py) extraindo os 32 spawns oficiais de `Arrival.World00p` e gerando o minimapa tático [`targets/district-187/tactical_map_arrival.html`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/targets/district-187/tactical_map_arrival.html).
    - Desenvolvido o painel de controle web local em [`scripts/d187_web_panel.py`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/scripts/d187_web_panel.py) (porta 8080) com monitoramento em tempo real, ajuste de cvars e atalhos rápidos.
  - **Fase 4 Concluída (Matchmaking Completo, Servidor Dedicado Nativo e Simulador 8v8):**
    - `scripts/d187-mock-server.py` atualizado com o fluxo completo de lobby: `SA_JoyGameLogin` -> `SN_UserInfo` (Rank 58) -> `SN_ItemList` (185 armas VIP) -> `SN_Record` -> `SN_LockEnd` -> `SA_EnterUser` (Canal 1) -> `SA_CreateRoom` (Arrival 8v8) -> `SN_BattleStart` (127.0.0.1:27888).
    - Criado o inicializador do servidor dedicado nativo [`scripts/d187_server_runner.py`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/scripts/d187_server_runner.py) (`TheRaw.exe -arch game +serverdll Game\GameServer.dll +runworld Worlds\Arrival.World00p -dedicated -port 27888`).
    - Desenvolvido o simulador autoritativo de combate 8v8 [`scripts/d187_match_simulator.py`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/scripts/d187_match_simulator.py) com 16 bots usando os 32 spawns reais de `Arrival.World00p`, balística real do SQLite e árvore de plant/defuse de C4.
    - Documentada a arquitetura em [`notes/district-187-dedicated-server-and-matchmaking-architecture.md`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/notes/district-187-dedicated-server-and-matchmaking-architecture.md).
  - **Fase 5 Concluída (Decifragem de .ResDt, Proxy MITM Hermit, ApexGuard Stub e NavMesh A*):**
    - Desvendado o formato proprietário dos pacotes de 2.8 GB `.ResDt` (Zlib streams contínuos com Table of Contents no rodapé) via [`scripts/extract_resdt.py`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/scripts/extract_resdt.py), descobrindo os 29 mapas oficiais compilados (`twoway.World00p`, `thebank.World00p`, `10025_Heaven.World00p`, etc.).
    - Criado o Proxy Sniffer MITM em tempo real [`scripts/d187_proxy_sniffer.py`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/scripts/d187_proxy_sniffer.py) com decifragem instantânea de stream Hermit e mapeamento para os 326 opcodes.
    - Criado o emulador do Anti-Cheat ApexGuard [`scripts/apexguard_stub.py`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/scripts/apexguard_stub.py) mantendo viva a memória compartilhada `Local\ApexRing_` com heartbeat para jogatina offline sem crash.
    - Criada a malha de navegação tática A* dos bots [`scripts/d187_navmesh_generator.py`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/scripts/d187_navmesh_generator.py) e visualizador interativo [`targets/district-187/navmesh_arrival.html`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/targets/district-187/navmesh_arrival.html).
    - Documentação técnica em [`notes/resdt-archive-and-anti-cheat-decompilation-manifest.md`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/notes/resdt-archive-and-anti-cheat-decompilation-manifest.md).
  - **Fase 6 Concluída (29 Mapas Extraídos, 25 Radares/NavMeshes, Simulador Universal & Orquestrador 4-Terminais):**
    - Extraídos todos os 29 mapas oficiais `.World00p` de `Game.Res00`/`Game.ResDt` diretamente para `client-rebirth/Game/Worlds/` (`twoway.World00p`, `thebank.World00p`, `10025_Heaven.World00p`, `oldtown.World00p`, etc.).
    - Gerados todos os 25 radares táticos SVG/HTML e malhas A* de pathfinding em `targets/district-187/maps/` e `targets/district-187/navmeshes/` via [`scripts/inspect_world00p.py`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/scripts/inspect_world00p.py) e [`scripts/d187_navmesh_generator.py`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/scripts/d187_navmesh_generator.py).
    - Criado o simulador autoritativo universal [`scripts/d187_match_simulator.py`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/scripts/d187_match_simulator.py) com gravação contínua em SQLite (`match_history`) e suporte a qualquer mapa (`--map twoway`, `--map thebank`, etc.).
    - Atualizado o painel [`scripts/d187_web_panel.py`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/scripts/d187_web_panel.py) com seletor de radares, visualizador de NavMesh, simulação 8v8 com 1 clique e feed de histórico.
    - Criado o orquestrador multi-processo [`launch_4_terminals.bat`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/launch_4_terminals.bat) para subir toda a stack conectada sem conflitos de arquivo.
  - **Fase 7 Concluída (Teardown do ApexGuard & Transição 100% Autêntica Login -> Lobby):**
    - Desmontado o launcher C#/.NET `S2Launcher.exe` e confirmada a independência do fluxo de login (a tela in-game Scaleform conecta diretamente na porta 12000).
    - Removido o anticheat `ApexGuard.dll` da versão privada, restaurando as 3 DLLs originais limpas (`D3DX9_43.dll` 1.99MB DirectX 9, `StringEditRuntime.dll` e `GameDatabase.dll`), eliminando pop-ups `S2-320` e crashes `R6025`.
    - Neutralizado o hook de anel `.s2kl` em `GameClient.dll` com patch `0xC3` (`RET`) preservando os hacks de taxa de quadros 144+ FPS (`.s2fp`) e zoom (`.s2zm`).
    - Descobertos e implementados os pacotes `SN_GroupList` (`0x220107`, 66B) e `SN_ServerList` (`0x220108`, 20B) integrados ao `SN_ServerInfo` (`0x220101`, 98B) e `SN_ChannelList` (`0x220102`, 57B) com código de servidor `S2`.
    - Validado o ciclo de vida completo de 16 pacotes (Login -> ServerList -> ChannelList -> Lobby -> Room -> Match Trigger) no [`scripts/test_client_handshake_smoke.py`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/scripts/test_client_handshake_smoke.py) com 100% de sucesso.
    - Documentação em [`notes/d187-apexguard-removal-and-server-state-machine.md`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/notes/d187-apexguard-removal-and-server-state-machine.md).
  - **Fase 7 Concluída (Resolução Definitiva do Login Scaleform, Launcher Próprio & Web Portal):**
    - Desmontada a função `0x10191740` em `GameClient.dll` descobrindo a instrução `0x10191bd0: cmp edi, 0xa40221`: comprovado que o offset 18 de `SA_JoyGameLogin` DEVE ser `0x00A40221` (10748449) para zerar o overlay `"please wait"` em `0x100d752b: mov dword ptr [eax + 0x64], 0`.
    - Implementados os handlers dos pacotes `0x20084` (Keepalive Ping) e `0x5A0101` (S2Rebirth ApexGuard Heartbeat) respondendo com `0x5A0102` (48 bytes).
    - Conectada autenticação dinâmica ao banco de dados `targets/district-187/data/s2rebirth.db` (`users` com 58 patentes, EXP, Gold/Cash, Kills, Deaths, Headshots).
    - Desenvolvido o **Launcher Gráfico Próprio** [`scripts/d187_launcher.py`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/scripts/d187_launcher.py) / [`D187_Launcher.bat`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/D187_Launcher.bat) em Tkinter com tema Dark/Amber, seleção de mapas e dificuldade de bots, modo online com amigos e inicialização do servidor em 1 clique.
    - Desenvolvido o **Web Portal Standalone** [`scripts/d187_web_portal.py`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/scripts/d187_web_portal.py) (FastAPI na porta 8080) com alternância instantânea PT-BR / EN, arsenal de 185 armas com stats de balística, tabela de classificação e registro de novas contas.
  - **Fase 8 Concluída (Telemetria Espacial 2D KDE, Extração FMOD Audio FSB5 & Protocolo NBattle):**
    - Desenvolvido o pipeline de telemetria espacial e gerador de heatmaps 2D com Kernel Density Estimation (KDE) [`scripts/generate_match_heatmap.py`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/scripts/generate_match_heatmap.py) sobreposto aos radares de `twoway`, `thebank` e `Arrival`.
    - Persistência granular de cada abate na tabela `match_kills` em `s2rebirth.db` (coordenadas $x, z$, arma, hitbox, TTK, distância).
    - Extração e catalogação completa de 901 amostras de áudio dos 9 SoundBanks FMOD FSB5 via [`scripts/extract_fmod_audio.py`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/scripts/extract_fmod_audio.py) em `targets/district-187/extracted/audio/` e manifesto em `targets/district-187/data/audio_manifest.json`.
    - Biblioteca de protocolo mestre [`scripts/d187_protocol.py`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/scripts/d187_protocol.py) estendida com os serializadores de combate em tempo real (`SN_Spawn`, `SN_Fire`, `SN_Hit`, `SN_Kill`, `SN_Bomb`, `SN_RoundEnd`).
    - Documentação técnica consolidada em [`notes/district-187-multi-map-geometry-navmesh-and-audio-manifest.md`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/notes/district-187-multi-map-geometry-navmesh-and-audio-manifest.md).
  - **Fase 9 Concluída (Suíte de Desenvolvimento Profissional & Supervisor de Micro-serviços):**
    - [`scripts/d187_web_panel.py`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/scripts/d187_web_panel.py) transformado no Control Plane oficial com o `ServiceManager` gerenciando Start/Stop/Restart dos 4 daemons locais em `127.0.0.1` com detecção de portas abertas.
    - Criado o cockpit unificado do Windows Terminal [`launch_workspace_wt.bat`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/launch_workspace_wt.bat) operando em grade 2x2 sem janelas soltas.
  - **Fase 10 Concluída (Dedicated Server UDP Gateway 27888 & Suite de Heatmaps dos 25 Mapas):**
    - Desenvolvido o Gateway UDP Autoritativo [`scripts/d187_dedicated_gateway.py`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/scripts/d187_dedicated_gateway.py) escutando na porta UDP 27888, respondendo a pings LithTech, handshakes e heartbeats com 100% de sucesso nos testes de loopback.
    - Gerados os 25 heatmaps de combate espacial 2D KDE com detecção de choke points via [`scripts/generate_match_heatmap.py`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/scripts/generate_match_heatmap.py) e o Portal Mestre [`targets/district-187/analytics/index.html`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/targets/district-187/analytics/index.html).
    - Documentação técnica em [`notes/district-187-spatial-analytics-and-heatmaps.md`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/notes/district-187-spatial-analytics-and-heatmaps.md).
  - **Fase 11 Concluída (Correção ApexGuard S2-320 / R6025, `SN_LockEnd` `0x210121`, Bind Exclusivo 12000 & Reorganização):**
    - Identificada e corrigida a causa raiz do erro `S2-320` e do crash `R6025 - pure virtual function call` ([`notes/d187-apexguard-s2-320-dx-proxy.md`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/notes/d187-apexguard-s2-320-dx-proxy.md)): restaurada a proxy `targets/district-187/client-rebirth/D3DX9_43.dll` (119.864 bytes) que carrega `dxbase.dll`, exigida em memória pelo `ApexGuard.dll`.
    - Mapeados os opcodes reais de transição de cena em `GameClient.dll` ([`notes/d187-login-scaleform-unlock.md`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/notes/d187-login-scaleform-unlock.md)): `IsPacketerrorMessage(0, 0)` em `0x10191740` + `SN_LockEnd` (`0x210121`) + `SN_ServerInfo` (`0x220101`, 98B) + `SN_ChannelList` (`0x220102`, 57B).
    - Aplicado `SO_EXCLUSIVEADDRUSE` em [`scripts/d187-mock-server.py`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/scripts/d187-mock-server.py) na porta 12000.
  - **Fase 12 Concluída (Suite de Modding HBEK `.Res00`/`.ResDt`, MMR/DDA, Replay 2D HLTV, Comandos In-Game & QoL Windows 11):**
    - Criado o compilador/repacker nativo HBEK v2 [`scripts/pack_lithtech_res.py`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/scripts/pack_lithtech_res.py), gerando `CustomMod_PTBR.Res00` / `CustomMod_PTBR.ResDt` com tradução PT-BR (`Game.StrDb00e`) e balanceamento competitivo.
    - Criado o motor de MMR Competitivo (Elo + DDA), Loadouts persistentes (Slots A/B/C com attachments), Clãs e gerador do Player Interativo de Replay 2D (estilo HLTV/Scope.gg) em [`scripts/d187_mmr_engine.py`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/scripts/d187_mmr_engine.py) e [`targets/district-187/analytics/match_replay.html`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/targets/district-187/analytics/match_replay.html).
    - Criado o processador de comandos de chat in-game (`/map`, `/bots`, `/give`, `/loadout`, `/mmr`, `/clan`) em [`scripts/d187_lobby_extensions.py`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/scripts/d187_lobby_extensions.py) integrado ao `CQ_Chat` (`0x210151` -> `0x210152`) no servidor Hermit.
    - Criado o otimizador QoL Windows 11 [`scripts/d187_qol_optimizer.py`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/scripts/d187_qol_optimizer.py) (Borderless Windowed via Win32 API para Alt+Tab instantâneo, FOV 95° e Raw Mouse Input) integrado ao [`scripts/d187_launcher.py`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/scripts/d187_launcher.py).
    - Integrado o `NavMeshBotDirector` em [`scripts/d187_dedicated_gateway.py`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/scripts/d187_dedicated_gateway.py) transmitindo pacotes autoritativos UDP (`SN_Spawn`, `SN_Move`, `SN_Hit`, `SN_Kill`) sobre os waypoints A* reais.
    - Documentação consolidada em [`notes/district-187-modding-mmr-replay-and-qol-suite.md`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/notes/district-187-modding-mmr-replay-and-qol-suite.md).
  - **Fase 12 Concluída (Correção Definitiva do Loop Infinito de Login via Tabelas de Despacho de `GameClient.dll`):**
    - Desmontadas as tabelas de registro de pacotes (`0x10194800` global e `0x10132d10` `CLoginScene`) e RTTI de `GameClient.dll`: identificado que `0x10191740` é `IsPacketerrorMessage(int err, uint16 origin)` (onde `0` = sem erro) e que a transição real para fora de `LoginScene` (`Scene[10]`) ocorre em `CDispatch_NLaunch_NLock_SN_LockEnd` (`0x10032f30`) com opcode **`0x210121`** (e não `0x210202`, que era `SA_CreateUser`).
    - Atualizado [`scripts/d187-mock-server.py`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/scripts/d187-mock-server.py) com os opcodes e layouts binários exatos de `GameClient.dll`: `SN_UserInfo` (`0x210101`, 25B Nickname + 25B ClanName), `SN_RankingInfo` (`0x210105`), `SN_ItemList` (`0x210111`, 27B/item), `SN_Record` (`0x210103`, 224B payload), `SN_LockEnd` (`0x210121`, chama `ChangeScene(0)`), `SN_ServerInfo` (`0x220101`, 98B/servidor), `SN_ChannelList` (`0x220102`, 57B/canal), `CQ_Join`/`SA_Join` (`0x110124`/`0x110125`) e `CQ_EnterUser`/`SA_EnterUser` (`0x220111`/`0x220112`, chama `ChangeScene(2)`).
    - Validado fim a fim com [`scripts/test_client_handshake_smoke.py`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/scripts/test_client_handshake_smoke.py) e documentado em [`notes/d187-login-scaleform-unlock.md`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/notes/d187-login-scaleform-unlock.md).
  - **Fase 13 Concluída (Renderização D3D9 em GPU Moderna AMD RX 9060 XT, Interface Scaleform & Launcher Unificado):**
    - Identificada e resolvida a causa raiz do encerramento silencioso (saída com código 0 e `0x30` em `SetRenderMode`): em GPUs AMD modernas no Windows 11, o driver descontinuou o HAL nativo de 32-bit de Direct3D 9 retornando `D3DERR_NOTAVAILABLE` (`0x8876086a`).
    - Integrado o DXVK v3.1.1 oficial x86 ([`targets/district-187/client-rebirth/d3d9.dll`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/targets/district-187/client-rebirth/d3d9.dll)), traduzindo Direct3D 9 para Vulkan com criação instantânea de swapchain (`1920x1080` A8R8G8B8, presentation mode imediato).
    - Corrigido o erro `LT_OK != i_client_shell->OnEngineInitialized()` via extração de 2.673 arquivos de interface Flash de `Game.Res00`, `Update_1.Res00` e `Update_2.Res00` para `Interface\Flash\` e criação de espelhos `.swf`/`.gfx`.
    - Unificados todos os pontos de entrada ([`D187_Launcher.bat`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/D187_Launcher.bat), [`launch_game.bat`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/launch_game.bat) e [`scripts/d187_launcher.py`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/scripts/d187_launcher.py)) com montagem explícita de arquivos `-archcfg Default.archcfg`, elevação segura `RunAsInvoker` e auto-inicialização do servidor Hermit local.
- **Alvo:** `targets/district-187/`

### [TARGET] Columnar Storage & Parquet Binary Format RE
- **Status:** em andamento (2026-11-02)
- **Foco:** Engenharia reversa e dissecação de baixo nível dos formatos binários de armazenamento colunar (Apache Parquet e Arrow IPC) usados em pipelines analíticos de alta escala (Meta, Presto, DuckDB).
- **Entregas Concluídas:**
  - Criado o README do alvo em [`targets/columnar-storage-re/README.md`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/targets/columnar-storage-re/README.md).
  - Implementado o dissector binário puro Python [`scripts/parse_parquet_binary.py`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/scripts/parse_parquet_binary.py) com deserializador do Thrift Compact Protocol (LEB128 varints, ZigZag, esquemas, row groups e offsets).
  - Gerado dataset de telemetria analítica de teste em `targets/columnar-storage-re/data/telemetry_sample.parquet`.
  - Documentação técnica em [`notes/parquet-columnar-binary-format-reverse-engineering.md`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/notes/parquet-columnar-binary-format-reverse-engineering.md).
- **Alvo:** `targets/columnar-storage-re/`

### [SETUP] Configuração do ambiente RE
- **Status:** concluído
- **Último passo:** instalação do REA + Second Brain
- **Próximo:** escolher primeiro alvo para análise

### [TOOLING] Skills rubenmarcus/agent-skills
- **Status:** concluído (2026-11-02)
- **Instaladas:** `evidence-driven-debugging`, `source-backed-research`, `validated-coding-loop`, `gauntlet-loop`, `agent-worktree-orchestration`
- **Uso:** invocar via `/evidence-driven-debugging`, `/source-backed-research`, etc. durante análises RE

### [TOOLING] Native Control Center & Analytics Suite
- **Status:** concluído (2026-11-02)
- **Entregas Realizadas:**
  - `scripts/d187_control_center.py` — Launcher & Control Center nativo com alternador Online/Offline, toggle Ultra HD, destravamento de FPS e telemetria ao vivo.
  - `scripts/generate_weapon_analytics.py` — Gerador do dashboard visual interativo de balanceamento (`targets/district-187/weapon_analytics_dashboard.html`).
  - `scripts/extract_lithtech_cvars.py` — Extrator de 77 cvars nativas do motor e gerador do `autoexec_competitive.cfg`.
  - `notes/lithtech-engine-cvars-and-competitive-tuning.md` — Documentação técnica das cvars e otimizações de taxa de quadros e latência.

### [ARCH] Autonomous RE Agent
- **Status:** implementado (2026-11-02)
- **Referência:** `notes/autonomous-re-agent-architecture.md`
- **Script:** `scripts/re-router.py` atualizado com modo local offline (`--local <target>`) e suporte a GitHub issues.

---

## Backlog de ideias

### Analytics SDK Internals
Analisar como SDKs de analytics mobile (Amplitude, Mixpanel, Firebase Analytics) coletam e enviam dados. Relevante para o perfil Meta/Data Analyst.
- **Alvos potenciais:** app Android com SDK embutido
- **Ferramenta:** REA (APK) + captura de rede

### Data Pipeline Format RE
Entender os formatos internos de pipelines de dados (Parquet, Arrow, Delta Lake) a nível de binário.
- **Ferramenta:** REA (binários estáticos + .NET assemblies)

### BI Tool Internals
Inspecionar como ferramentas de BI (Tableau, Looker, Power BI) processam consultas e geram visualizações.
- **Ferramenta:** REA (Electron/JS) para versões desktop

### ML Model Format Analysis
Analisar formatos de modelos (.gguf, safetensors, ONNX) — estrutura interna, metadados, arquitetura embarcada.
- **Ferramenta:** REA (model files) + Python

### Autonomous RE Agent (inspirado no dsh-superagent)
Prototipar um agente autônomo que recebe um binário/APK, executa análise REA em sessão isolada e commita um relatório em `notes/` automaticamente.
- **Status:** arquitetura definida → ver `notes/autonomous-re-agent-architecture.md`
- **Stack:** Python + REA MCP + GitHub API
- **Padrão:** Router (watch issues) → Worker (sessão isolada) → PR com nota RE

### Qlib — Análise Quantitativa + RE Interno
Duas frentes: (1) usar qlib como plataforma de econometria/quant com ML; (2) RE dos formatos internos de dados (HDF5, serialização de features).
- **Referência:** `notes/microsoft-qlib-quant-platform.md`
- **Conexão:** complementa o backlog "Data Pipeline Format RE"
- **Stack:** Python + qlib + REA (para RE dos formatos)

---

## Concluídos
- **2026-11-02:** Conclusão do mapeamento da cifra de rede Hermit (CRC32), handshake de login e lançamento do Control Center nativo LithTech no GitHub ([Gleidisonjr/district187-reverse-engineering](https://github.com/Gleidisonjr/district187-reverse-engineering)).

# Projetos Ativos

## Em andamento

### [TARGET] District 187: Sin Streets (S2 Online / S2 Rebirth) — Motor Nativo LithTech
- **Status:** em andamento (2026-11-02)
- **Foco Absoluto:** Executável original (`TheRaw.exe`), motor nativo LithTech Jupiter EX e servidor oficial/emulador (arquitetura idêntica ao S2 Rebirth, sem engines externas).
- **Fase atual:**
  - **Fase 1 Concluída (Gráficos Ultra HD + Tradução no Motor Nativo):**
    - Baixados e validados os 1.72 GB do pacote de texturas HD oficial (`HD1.ResDt` a `HD6.ResDt`).
    - `Default.archcfg` atualizado para montagem automática das archives 2K/4K no motor LithTech.
    - `settings.cfg` e `autoexec.cfg` configurados com `GraphicQualityLevel 3`, `BindTexturesMipOffset 0` e `MaxFPS 0` (144+ FPS destravado).
    - Idioma inglês nativo ativado (3.923 strings).
    - Scripts de inicialização direta prontos:
      - `launch_s2rebirth_online.bat` (servidor oficial da comunidade em `179.61.147.154:12000`)
      - `launch_s2rebirth_direct.bat` (inicialização direta rápida)
      - `launch_offline_emulator.bat` (ambiente com mock server local em `127.0.0.1:12000`)
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
  - **Fase 6 (Próximo Passo):**
    - Extração seletiva dos outros mapas clássicos (`twoway.World00p`) de `Game.ResDt` e teste in-game.
- **Alvo:** `targets/district-187/`

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

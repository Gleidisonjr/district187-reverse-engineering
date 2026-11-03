# Projetos Ativos

## Em andamento

### [TARGET] District 187: Sin Streets — Servidor Privado & Ecossistema Próprio
- **Status:** em andamento (2026-11-02)
- **Fase atual:**
  - **Fase 1 Concluída (Gráficos Ultra HD + Tradução):**
    - Baixados e validados os 1.72 GB do pacote de texturas HD (`HD1.ResDt` a `HD6.ResDt`).
    - `Default.archcfg` atualizado para montagem automática das texturas 2K/4K.
    - `settings.cfg` e `autoexec.cfg` configurados com `GraphicQualityLevel 3`, `BindTexturesMipOffset 0` e `MaxFPS 0` (144+ FPS destravado).
    - Idioma inglês verificado (3.923 strings).
    - Criado launcher [`launch_game_ultra_hd.bat`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/launch_game_ultra_hd.bat).
  - **Fase 1.5 Concluída (Data Analytics & Telemetria Web Portal):**
    - Criado pipeline ETL [`scripts/build_s2rebirth_dataset.py`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/scripts/build_s2rebirth_dataset.py) gerando `targets/district-187/data/s2rebirth.db` (185 armas com stats de combate, 750 itens, 58 patentes, 155 mapas, 1.524 itens de loja).
    - Criado CLI Client [`scripts/s2rebirth_api_client.py`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/scripts/s2rebirth_api_client.py) para consulta em tempo real da telemetria de 1.140 jogadores, 73 clãs e histórico de partidas.
    - Documentada a arquitetura REST em [`notes/s2-rebirth-hd-pack-and-web-portal-architecture.md`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/notes/s2-rebirth-hd-pack-and-web-portal-architecture.md).
  - **Fase 2 Concluída (Motor de Bots Inteligentes & Sessão PvE Offline):**
    - Implementados 3 níveis de dificuldade tática (`BotDifficulty`: Fácil, Médio, Difícil) em [`projects/godot-fps/scripts/bot_controller.gd`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/projects/godot-fps/scripts/bot_controller.gd) com ajuste dinâmico de dispersão, recuo e tempo de reação.
    - Contabilização em tempo real de mortes, XP (+50 XP) e headshots críticos (+75 XP com multiplicador 2.5x) em [`projects/godot-fps/scripts/hud_manager.gd`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/projects/godot-fps/scripts/hud_manager.gd).
    - Descoberta da cifra de rede `MD5` + `RC4` e seções customizadas do Rebirth (`.s2*`), documentada em [`notes/district-187-rc4-network-crypto-and-bot-ai-engine.md`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/notes/district-187-rc4-network-crypto-and-bot-ai-engine.md).
    - Mock server atualizado com suporte ao handshake de 20 bytes em [`scripts/d187-mock-server.py`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/scripts/d187-mock-server.py).
  - **Próxima Fase (Fase 3):**
    - Mapeamento e exportação de novos mapas clássicos (`twoway`, `deathharbor`) para o ambiente Godot 4.
- **Alvo:** `targets/district-187/`

### [SETUP] Configuração do ambiente RE
- **Status:** concluído
- **Último passo:** instalação do REA + Second Brain
- **Próximo:** escolher primeiro alvo para análise

### [TOOLING] Skills rubenmarcus/agent-skills
- **Status:** concluído (2026-11-02)
- **Instaladas:** `evidence-driven-debugging`, `source-backed-research`, `validated-coding-loop`, `gauntlet-loop`, `agent-worktree-orchestration`
- **Uso:** invocar via `/evidence-driven-debugging`, `/source-backed-research`, etc. durante análises RE

### [ARCH] Autonomous RE Agent
- **Status:** arquitetura esboçada (2026-11-02)
- **Referência:** `notes/autonomous-re-agent-architecture.md`
- **Próximo:** implementar `scripts/re-router.py` + testar com primeiro alvo

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
- **2026-11-02:** Conclusão da base jogável offline em Godot 4.7 com IA tática de bots e publicação do portfólio no GitHub ([Gleidisonjr/district187-reverse-engineering](https://github.com/Gleidisonjr/district187-reverse-engineering)).

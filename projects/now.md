# Projetos Ativos

## Em andamento

### [TARGET] District 187: Sin Streets (S2 Online) — Remake Tático & Preservação
- **Status:** em andamento (2026-11-02)
- **Fase atual:**
  - **Caminho A (Concluído & Jogável):** Arena de combate tática jogável offline no Godot 4.7 (`projects/godot-fps/`) com IA de bots autônomos (`TacticalBot`), máquinas de estado (`PATROL`, `CHASE`, `ENGAGE`, `DEAD`), detecção LoS raycast, disparos em rajada, multiplicador de headshot (2.5x), respawn automático, armas autênticas (AK-47, M4A1, AWM-300), recuo procedural, mira ADS, HUD tático completo e inicializador em 1 clique (`launch_game.bat`).
  - **Portfólio GitHub (Publicado & Sincronizado):** Repositório público ativo em [`https://github.com/Gleidisonjr/district187-reverse-engineering`](https://github.com/Gleidisonjr/district187-reverse-engineering) com 5 commits atômicos estruturados e README arquitetural detalhado.
  - **Caminho B (Paralelo / Preservação):** Servidor mock Python (`scripts/d187-mock-server.py`) ativo na porta 12000; proxy DLL maliciosa desarmada; executável original pronto para avançar no handshake de login Joygame.
- **Alvo:** `targets/district-187/`
- **Próximos Passos:**
  - Testar gameplay presencial no Godot com bot skirmish.
  - Implementar resposta ao opcode de login `0x0062` no mock server Hermit para avançar a tela preta no executável original `TheRaw.exe`.

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

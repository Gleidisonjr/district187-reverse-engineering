# Projetos Ativos

## Em andamento

### [TARGET] District 187: Sin Streets — Servidor Privado & Ecossistema Próprio
- **Status:** em andamento (2026-11-02)
- **Fase atual:**
  - **Fase 1 Concluída:**
    - Baixados e validados os 1.72 GB do pacote de texturas HD (`HD1.ResDt` a `HD6.ResDt`).
    - `Default.archcfg` atualizado para montagem automática das texturas 2K/4K.
    - `settings.cfg` e `autoexec.cfg` configurados com `GraphicQualityLevel 3`, `BindTexturesMipOffset 0` e `MaxFPS 0` (144+ FPS destravado).
    - Idioma inglês verificado (3.923 strings).
    - Criado launcher [`launch_game_ultra_hd.bat`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/launch_game_ultra_hd.bat).
  - **Próxima Fase (Fase 2):**
    - Motor de Bots Inteligentes & Sessão Solo/PvE com seleção de dificuldade (Fácil, Médio, Difícil).
    - Contabilização de mortes, XP e headshots contra bots.
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

# Projetos Ativos

## Em andamento

### [TARGET] District 187: Sin Streets (S2 Online) — Abordagem Híbrida (Opção C)
- **Status:** em andamento (2026-11-02)
- **Fase atual:**
  - **Opção C Adotada:** Configuração dual completa permitindo jogo online em servidores ativos da comunidade e preservação offline em mock server local.
  - **Cliente S2 Rebirth Online (`targets/district-187/client-rebirth/`):**
    - Montado com 100% de integridade SHA-256 via CDN `https://gamefiles.mdcreative.tr`.
    - Pacote de idioma Inglês instalado (texturas Flash, áudio FSB e banco de textos).
    - Launcher oficial C# (`S2Launcher.exe`) e scripts de inicialização configurados:
      - `launch_s2rebirth_online.bat` (abre o launcher oficial da comunidade)
      - `launch_s2rebirth_direct.bat` (conecta diretamente a `179.61.147.154:12000`)
  - **Ambiente Local Mock / Emulador Offline (`targets/district-187/client/S2/`):**
    - Mock server Hermit em Python (`scripts/d187-mock-server.py`) ouvindo na porta 12000.
    - Cliente com patch atômico de IP/Porta local e idioma inglês preservado para portfólio e testes de RE.
    - `launch_offline_emulator.bat` configurado para disparo automático.
- **Alvo:** `targets/district-187/`
- **Próximos Passos:**
  - Usuário criar conta em `https://s2rebirth.com/kayit` para jogar online no servidor da comunidade.
  - Testar login e jogabilidade com `launch_s2rebirth_online.bat` ou `launch_s2rebirth_direct.bat`.
  - Continuar documentação e commits atômicos no repositório GitHub.

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

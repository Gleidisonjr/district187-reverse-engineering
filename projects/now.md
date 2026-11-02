# Projetos Ativos

## Em andamento

### [TARGET] District 187: Sin Streets (S2 Online) — Preservação do Cliente Original (Caminho B)
- **Status:** em andamento (2026-11-02)
- **Fase atual:**
  - **Foco Primário (Caminho B):** Execução do executável original autêntico `TheRaw.exe` (LithTech Jupiter EX Engine).
  - **Diagnóstico do Carregamento Infinito de Login:** Identificado que a rotina `0x100d7964` em `GameClient.dll` falhava ao ler `gs_ip` da linha de comando, abortando em `CGameServerConnectMgr::Connecting()` com `"empty szIP!!"`.
  - **Patch de Rede Local:** Aplicado patch atômico no offset `0x100d7964` forçando IP fixo `127.0.0.1` e porta `12000.0f`, garantindo que todo clique de login conecte ao servidor mock local.
  - **Mock Server Hermit Aprimorado:** `scripts/d187-mock-server.py` responde a `CQ_JoyGameLogin` com `SA_JoyGameLogin` (`ResultCode=0`, `AccountID=1001`), destravando o spinner e liberando a transição do lobby.
  - **Portfólio GitHub:** Sincronizado em [`https://github.com/Gleidisonjr/district187-reverse-engineering`](https://github.com/Gleidisonjr/district187-reverse-engineering).
- **Alvo:** `targets/district-187/`
- **Próximos Passos:**
  - Usuário executar `launch_original_game.bat` e logar com qualquer credencial.
  - Validar recebimento de pacotes no mock server e transição de tela para o lobby/servidores.

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

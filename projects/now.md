# Projetos Ativos

## Em andamento

### [TARGET] District 187: Sin Streets (S2 Online) — Preservação do Cliente Original (Caminho B)
- **Status:** em andamento (2026-11-02)
- **Fase atual:**
  - **Foco Primário (Caminho B):** Execução do executável original autêntico `TheRaw.exe` (LithTech Jupiter EX Engine).
  - **Descoberta do Protocolo Hermit:** Mapeada a tabela de despacho de pacotes (offset `0x10058498` em `GameClient.dll`), identificando `tPacket_NAccount_NIdentity_CQ_JoyGameLogin` (`0x110111`, opcode `0x0062`) e sua resposta `SA_JoyGameLogin` (`0x110112`).
  - **Bypass de UAC:** Aplicado `__COMPAT_LAYER=RunAsInvoker`, eliminando o erro de permissão administrativa.
  - **Mock Server Hermit Atualizado:** `scripts/d187-mock-server.py` ativo na porta 12000 com decodificador de cabeçalhos e emulador de resposta de login.
  - **Launcher Original:** Criado `launch_original_game.bat` para inicialização direta do jogo original com rede local.
  - **Portfólio GitHub:** Sincronizado em [`https://github.com/Gleidisonjr/district187-reverse-engineering`](https://github.com/Gleidisonjr/district187-reverse-engineering).
- **Alvo:** `targets/district-187/`
- **Próximos Passos:**
  - Testar inicialização do `TheRaw.exe` via `launch_original_game.bat` com conexão ao mock server.
  - Inspecionar a transição da janela Direct3D e carregamento da UI Flash do lobby.

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

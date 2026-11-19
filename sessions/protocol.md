# Protocolo de Coordenação — Claude Code + Antigravity

## Agentes
| ID | Ferramenta | Modelo | Contexto |
|---|---|---|---|
| `claude` | Claude Code | claude-sonnet-4-6 | 200k tokens, MCP REA ativo |
| `agy` | Antigravity CLI | Gemini 4 Neon | 1M tokens, MCP REA ativo |

## Ferramentas RE Disponíveis
| Ferramenta | Status | Descrição |
|---|---|---|
| **REA MCP** (`morluto/rea`) | ✅ ativo (ambos) | 320+ tools: binários, .NET, Android, Electron, web, firmware |
| **craft-anything** (`storytold/craft-anything`) | ⏳ não instalado | Study→Build→Check→Refine, Rust 1.97+ required |

## Regras de Trabalho

### 1. Antes de começar uma tarefa
- Mova-a de `OPEN` para `DOING` em `sessions/task-queue.md` com seu ID
- Atualize seu arquivo `sessions/agent-{id}.md` com o que está fazendo

### 2. Propriedade de arquivos
- Liste os arquivos que está modificando em `agent-{id}.md` → seção `owned_files`
- Nunca edite um arquivo que está em `owned_files` do outro agente sem avisar
- Arquivos de alto risco (edição simultânea proibida):
  - `scripts/d187-mock-server.py` — servidor principal
  - `scripts/d187_lobby_extensions.py` — handlers de chat
  - `targets/district-187/server_host/d187_server_host.cpp` — servidor nativo

### 3. Sessões REA
- Apenas **um agente por vez** abre sessão REA em um binário
- Declare em `agent-{id}.md` → `rea_session` qual binário está aberto
- Feche com `close_binary` antes de liberar para o outro

### 4. Descobertas
- Toda descoberta técnica vai em `notes/<o-que-foi-descoberto>.md`
- Inclua `Descoberto por: claude|agy` no topo da nota
- Atualize `task-queue.md` com referência à nota

### 5. Comunicação entre agentes
- Deixe mensagens em `task-queue.md` → seção `## Mensagens`
- Formato: `[claude → agy]` ou `[agy → claude]` com timestamp
- O agente destinatário responde na mesma seção

### 6. Finalização de tarefa
- Mova de `DOING` para `DONE` em `task-queue.md`
- Libere `owned_files` em seu `agent-{id}.md`
- Se gerou artefato (nota, script, HTML), cite o caminho

### 7. Commit
- Commits são feitos pelo **claude** por padrão (tem controle de git)
- Se `agy` precisar commitar: deixe mensagem em `task-queue.md` → `[agy → claude]`
- Nunca commitar `sessions/agent-*.md` — são voláteis

### 8. Handoff de sessão
- Ao encerrar uma sessão, atualize `sessions/current.md` com:
  - O que foi concluído
  - Estado de cada tarefa aberta
  - Qualquer descoberta crítica não documentada ainda

## Divisão Natural de Trabalho

| Domínio | Agente Preferido | Motivo |
|---|---|---|
| RE de binários grandes (`TheRaw.exe`, `GameClient.dll`) | `agy` | 1M tokens, sessões longas |
| Implementação Python (mock server, scripts) | `claude` | Melhor em código iterativo curto |
| Disassembly / pseudocódigo / REA deep analysis | `agy` | Contexto maior para análise extensa |
| Commits, git, PRs, CI | `claude` | Controle de ferramentas de git |
| Notas técnicas / documentação | ambos | Quem descobriu, escreve |
| Smoke tests e validação | `claude` | Execução local rápida |
| craft-anything (quando instalado) | `agy` | Fluxo Study→Build pesado |

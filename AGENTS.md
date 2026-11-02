# Reverse Engineering — Second Brain
## Quem sou eu
- Gleidison Carvalho, Senior Data Analyst na Meta
- Stack principal: Python, SQL, Data Science, ML
- Foco de RE: entender como ferramentas de analytics, pipelines de dados e apps mobile coletam/processam dados

## Onde as coisas ficam
- `targets/` — um subdiretório por alvo (app, binário, API), com README de contexto
- `notes/` — uma descoberta por arquivo, nomeado pelo que foi descoberto
- `scripts/` — scripts Python de análise, um por tarefa
- `projects/` — estado atual, onde parou, próximo passo
- `decisions.md` — toda decisão de abordagem com o motivo

## Como responder
- Antes de responder sobre um alvo, leia o arquivo em `targets/<alvo>/README.md`
- Cite qual arquivo você usou na resposta
- Se não há arquivo cobrindo o tema, diga qual criar
- Prefira Python para scripts de análise e automação
- Resultados de análise vão em `notes/`, não só no chat

## Nomenclatura
- `lowercase-with-hyphens.md`, um tópico por arquivo
- Alvos: `targets/<nome-do-app>/`
- Notas: `notes/<o-que-foi-descoberto>.md`
- Scripts: `scripts/<o-que-faz>.py`

## Sempre em foco
- Projetos ativos: @projects/now.md

## Ferramentas disponíveis
- **REA** (MCP): análise de binários, JS/Electron, APK, .NET, websites, capturas de rede
- **Python**: automação, parsing, análise de dados extraídos
- **Ghidra 12.1.4**: `C:\Users\dopamine\AppData\Local\ghidra\ghidra_12.1.4_PUBLIC`
- **Java 21 (Temurin)**: `C:\Program Files\Eclipse Adoptium\jdk-21.0.13.9-hotspot`

## Skills disponíveis (`.agents/skills/`)
- `/evidence-driven-debugging` — análise com evidências antes de conclusões
- `/source-backed-research` — pesquisa citando fontes
- `/validated-coding-loop` — loop de código com validação
- `/gauntlet-loop` — iteração agressiva até resultado
- `/agent-worktree-orchestration` — orquestração de worktrees
- `/re-investigation` — investigação RE estruturada
- `/data-extraction` — extração de dados de binários/APKs
- `/karpathy-guidelines` — cautela, simplicidade e mudanças cirúrgicas (anti-overengineering)
- `/grill-me` — entrevista implacável em árvore de decisão para estressar ideias/planos
- `/code-review` — revisão paralela em 2 eixos (Standards vs Spec) com subagentes
- `/to-spec` — sintetização de conversas e contexto em especificações técnicas
- `/improve-codebase-architecture` — análise visual de fricção e aprofundamento arquitetural
- `/codebase-design` — princípios e vocabulário estruturado de design de código

## Diretrizes de Engenharia e Execução (Karpathy Principles)
1. **Pense antes de codar**: Não assuma premissas em silêncio. Explicite incertezas, apresente alternativas e clarifique dúvidas antes de implementar.
2. **Simplicidade primeiro**: Menor volume de código que resolve o problema. Sem camadas especulativas, abstrações de uso único ou flexibilidade desnecessária.
3. **Mudanças cirúrgicas**: Modifique apenas o necessário. Não refatore nem altere estilo/formatação de código adjacente que funciona.
4. **Execução orientada a metas**: Toda alteração deve ter critério claro de sucesso e verificação (testar antes e depois).

## Handoff com Claude Code
- Estado de sessão em `sessions/current.md`
- Ao assumir de outra sessão: leia `sessions/current.md` primeiro
- Ao encerrar: atualize `sessions/current.md` com resumo do ponto de parada

## Variáveis de ambiente necessárias
```
GHIDRA_INSTALL_DIR=C:\Users\dopamine\AppData\Local\ghidra\ghidra_12.1.4_PUBLIC
JAVA_HOME=C:\Program Files\Eclipse Adoptium\jdk-21.0.13.9-hotspot
```

# Reverse Engineering — Second Brain
<!-- Gleidison Carvalho | Senior Data Analyst @ Meta | Keep under 200 lines. -->

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

## Roteamento Autônomo de Skills (Execução Proativa)
O usuário NUNCA precisa acionar skills manualmente. Detecte o contexto da tarefa e aplique a metodologia adequada automaticamente:
- **Investigação de alvo / binário / API**: Acione autonomamente `re-investigation` e `data-extraction`.
- **Bugs, falhas ou comportamentos anômalos**: Acione `evidence-driven-debugging` (colete evidências empíricas antes de alterar código).
- **Decisões técnicas / arquiteturais com alternativas**: Aplique o padrão `grill-me` (apresente perguntas numeradas com opções recomendadas).
- **Implementação e refatoração**: Aplique `karpathy-guidelines` (simplicidade, cirúrgico, sem suposições) no loop `validated-coding-loop`.
- **Conclusão de tarefas de código**: Dispare `code-review` com subagentes paralelos (Standards vs Spec).
- **Consolidação de discussões técnicas**: Acione `to-spec` para documentar especificações formalmente.

## Diretrizes de Engenharia e Execução (Karpathy Principles)
1. **Pense antes de codar**: Não assuma premissas em silêncio. Explicite incertezas e clarifique dúvidas antes de implementar.
2. **Simplicidade primeiro**: Menor volume de código que resolve o problema. Sem camadas especulativas ou flexibilidade desnecessária.
3. **Mudanças cirúrgicas**: Modifique apenas o necessário. Não refatore código adjacente que funciona.
4. **Execução orientada a metas**: Toda alteração deve ter critério claro de sucesso e verificação (antes e depois).

## Handoff entre Antigravity e Claude Code
- Estado de sessão em `sessions/current.md`
- Ao assumir uma sessão: leia `sessions/current.md` primeiro
- Ao encerrar: atualize `sessions/current.md` com resumo do ponto de parada

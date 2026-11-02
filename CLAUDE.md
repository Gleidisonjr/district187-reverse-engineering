# Reverse Engineering — Second Brain
<!-- Gleidison Carvalho | Senior Data Analyst @ Meta | Last cleaned: 2026-11-01. Keep under 200 lines. -->

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
- **Ghidra/Hopper/IDA**: descompilação (se instalado)

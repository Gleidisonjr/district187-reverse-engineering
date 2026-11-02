# RE Second Brain

**Dono:** Gleidison Carvalho — Senior Data Analyst @ Meta
**Stack:** Python · SQL · Data Science · ML
**Foco RE:** analytics tools · data pipelines · apps mobile

---

## Navegação rápida

### Projetos ativos
→ [[projects/now]]

### Notas de descoberta
→ [[notes/5-levels-ai-engineering]] — roadmap de AI Engineering (Levels 1–5)
→ [[notes/claude-second-brain-2]] — as 4 camadas de memória do Claude Code (guia completo)
→ [[notes/tokeneconomizer-microsoft]] — plugin Microsoft: reduz custo de agentes em 18–30%
→ [[notes/craft-anything-re-tool]] — ferramenta RE em Rust: estuda + reconstrói qualquer software
→ [[notes/deepseek-dsh-superagent-prototype]] — agente autônomo, referência para Level 4/5
→ [[notes/microsoft-qlib-quant-platform]] — plataforma quant + RE de formatos de dados

### Scripts
→ `scripts/ingest-twitter.py` — pipeline de ingestão técnica do Twitter/X (clipboard, arquivo, notas atômicas)
→ `scripts/save-digest.py` — salva o feed digest do Twitter/Claude Extension
→ `scripts/re-router.py` — router autônomo de tarefas RE

---

## Onde estamos nos 5 níveis

| Nível | Status | O que temos |
|-------|--------|-------------|
| 2 · Context | ✅ | CLAUDE.md · projects/now.md · notes/ |
| 3 · Harness | ✅ | Claude Code · REA MCP · hooks · skills |
| 4 · Loop | 🔄 | `/loop` disponível, falta state file + budget |
| 5 · Graph | ⬜ | meta — diamond split→fanout→verify→merge |

---

## Backlog de alvos RE

- Analytics SDK Internals (Amplitude, Mixpanel, Firebase)
- Data Pipeline Format RE (Parquet, Arrow, Delta Lake)
- BI Tool Internals (Tableau, Looker, Power BI)
- ML Model Format Analysis (.gguf, safetensors, ONNX)
- Autonomous RE Agent (baseado em [[notes/deepseek-dsh-superagent-prototype]])
- Qlib internals (baseado em [[notes/microsoft-qlib-quant-platform]])

---

## Como usar este vault

- **Ler/navegar:** Obsidian (este vault)
- **Escrever/analisar:** Claude Code CLI / Antigravity
- **Feed digest:** extensão Claude no Chrome / Clipboard → `python scripts/ingest-twitter.py --clipboard` → `notes/digest-YYYY-MM-DD.md`

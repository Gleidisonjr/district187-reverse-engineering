# The 5 Levels of AI Engineering

**Fonte:** https://x.com/L1vsun/status/2116519560631205914
**Autor:** @L1vsun / @Rel1vs337
**Descoberto:** 2026-11-01

## O framework

| Nível | Nome | O que o modelo recebe |
|-------|------|-----------------------|
| 1 | Prompt Engineering | Uma frase |
| 2 | Context Engineering | Uma janela bem preenchida |
| 3 | Harness Engineering | Um ambiente (tools, hooks, memória) |
| 4 | Loop Engineering | Um schedule — você para de digitar |
| 5 | Graph Engineering | O shape do job — uma frota roda |

---

## Onde estamos neste projeto

- **Nível 1** ✅ superado
- **Nível 2** ✅ CLAUDE.md, projects/now.md, notes/ como memória, context loading automático
- **Nível 3** ✅ Claude Code + REA MCP + hooks (GateGuard, Stop hooks) + skills
- **Nível 4** 🔄 parcial — `/loop` disponível, loops com state file ainda não configurados
- **Nível 5** ⬜ meta — [[deepseek-dsh-superagent-prototype]] e RD-Agent do [[microsoft-qlib-quant-platform]] são referências diretas

---

## As 5 ações da semana (do artigo)

1. **Prompt** — substituir "você é um especialista" por um exemplo de output ideal
2. **Context** — CLAUDE.md já cumpre esse papel ✅
3. **Harness** — adicionar Stop hook que bloqueia até verificação passar
4. **Loop** — `/loop` com state file + budget, rodar overnight
5. **Graph** — diamond: split → fan out → verify → merge

---

## Padrão diamond (Level 5) aplicado ao RE

```
APK/binário recebido
    → split: quebra em partes independentes (classes, endpoints, libs)
    → fan out: agentes REA analisam cada parte em paralelo
    → verify: agente cético tenta refutar cada descoberta
    → merge: relatório consolidado salvo em notes/
```

---

## Citações-chave

> "Context engineering is the delicate art and science of filling the context window with just the right information for the next step." — Andrej Karpathy

> "I don't prompt Claude anymore. My job now is to write loops." — Boris Cherny (criador do Claude Code)

> "Loop engineering is replacing yourself as the person who prompts the agent." — Addy Osmani

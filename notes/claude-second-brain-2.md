# Claude Second Brain 2.0 — The Complete Guide

**Fonte:** Twitter @mojeskoqq
**Descoberto:** 2026-11-01

## As 4 camadas

| Camada | Onde | Quem escreve | Quando carrega |
|--------|------|--------------|----------------|
| 1 · CLAUDE.md | raiz do projeto | você | toda sessão |
| 2 · .claude/rules/ | por pasta/tipo | você | só quando toca arquivos matching |
| 3 · .claude/skills/ | por playbook | você | só quando invocada ou relevante |
| 4 · auto memory | gerenciado pelo Claude | Claude | toda sessão (200 linhas / 25KB) |

**Regra de ouro:** coloque cada conhecimento na camada que carrega só quando necessário.

---

## Os 2 mitos desmentidos

**Mito 1:** "CLAUDE.md é carregado no system prompt."
**Realidade:** é entregue como *user message* após o system prompt. Claude tenta seguir, sem garantia estrita.

**Mito 2:** "Se a info não está lá, o agente reporta falha em vez de alucinar."
**Realidade:** Claude trata memory files como *contexto*, não configuração forçada.

→ **"Never do X" em CLAUDE.md é um desejo. Use PreToolUse hook para enforcement real.**

---

## CLAUDE.md — regras

- Manter abaixo de **200 linhas**
- HTML comments `<!-- -->` custam zero tokens
- `@arquivo` importa (mas carrega sempre — não economiza contexto)
- Sem paths: → carrega em todo launch

---

## .claude/rules/ — reflexos por path

```markdown
---
paths:
  - "notes/**"
---
```

Carregam só quando Claude toca arquivos matching. Rules em `~/.claude/rules/` → todos os projetos.

---

## Auto memory (camada 4)

- Claude escreve automaticamente com base em correções
- Carrega toda sessão (200 linhas / 25KB)
- `/memory` para ver/editar · "remember..." para forçar save

---

## Comandos essenciais

| Comando | Para que serve |
|---------|---------------|
| `/context` | Mostra o que realmente carregou |
| `/memory` | Memory files + toggle auto memory |
| `/doctor prompt-audit` | Encontra instruções conflitantes (v2.1.283+) |

---

## Armadilhas

- CLAUDE.md > 200 linhas → menos aderência
- "Never do X" só no CLAUDE.md → use PreToolUse hook
- Regra só no chat → some após `/compact`

---

[[notes/5-levels-ai-engineering]] | [[Home]]

# Autonomous RE Agent — Arquitetura

**Alvo:** qualquer binário, APK ou bundle JS depositado em `targets/`
**Inspiração:** [deepseek-ai/dsh-superagent-prototype](https://github.com/deepseek-ai/dsh-superagent-prototype)
**Stack:** Python + REA MCP + GitHub API (ou watch local)
**Descoberto:** 2026-11-02

---

## O que foi descoberto

O dsh-superagent usa isolamento Router-Worker: um Router permanente despacha tarefas, Workers isolados executam em sessão própria e entregam o resultado sem acesso ao usuário. Essa arquitetura pode ser adaptada diretamente para automação de RE.

## Evidência

Benchmark dsh-superagent:
- p50/p95 com Router-Worker: **12.4 / 15.7 min**
- p50/p95 com sessão única: **20.4 / 29.5 min**
- Custo em tokens: maior (overhead de sessão), mas throughput paralelo compensa

Arquitetura original:
```
Trigger (GitHub issue / Feishu)
  → Router (sessão permanente, só despacha)
    → Worker N (sessão isolada, ferramentas completas)
      → entrega PR → humano aprova
```

## Arquitetura adaptada para RE

```
Trigger
  ├── GitHub issue: "analisar <alvo>"
  └── (futuro) novo arquivo em targets/<alvo>/

Router (script Python permanente)
  ├── recebe trigger
  ├── valida: alvo existe? já foi analisado?
  └── despacha: claude --session worker-<alvo>

Worker (sessão Claude Code isolada)
  ├── lê targets/<alvo>/README.md
  ├── executa análise REA (binary_overview, list_strings, decompile...)
  ├── aplica /evidence-driven-debugging se necessário
  ├── gera notes/<alvo>-<o-que-foi-descoberto>.md
  └── commita + abre PR (ou push direto em repo privado)

Human checkpoint
  └── revisa PR, aprova ou solicita aprofundamento
```

## Componentes

| Componente | Implementação |
|---|---|
| Router | `scripts/re-router.py` — watch em GitHub issues ou diretório |
| Worker trigger | `claude --session worker-{alvo} --prompt "analisar {alvo}"` |
| Análise | REA MCP via `/re-investigation` skill |
| Output | `notes/{alvo}-{descoberta}.md` seguindo o template |
| Entrega | `git commit` + `gh pr create` |

## Limitações

- Claude Code não tem modo "headless daemon" nativo — Router precisa invocar `claude` como subprocess
- Sessões isoladas por alvo evitam contaminação de contexto, mas aumentam custo por token
- REA pode ter timeout em binários grandes — Worker precisa de retry logic

## Próximos passos

- [ ] Implementar `scripts/re-router.py` — watch em GitHub issues com label `re-analyze`
- [ ] Definir prompt padrão do Worker (baseado em `/re-investigation`)
- [ ] Testar com um alvo simples do backlog (sugestão: APK de analytics SDK)
- [ ] Adicionar `/gauntlet-loop` para iterar análise até cobertura mínima

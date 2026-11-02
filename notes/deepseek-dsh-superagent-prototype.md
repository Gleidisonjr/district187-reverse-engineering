# DeepSeek — dsh-superagent-prototype

**Fonte:** https://github.com/deepseek-ai/dsh-superagent-prototype
**Stars:** 7.2k · TypeScript · MIT
**Descoberto:** 2026-11-01

## O que é

Agente de codificação autônomo da DeepSeek. Monitora um repositório GitHub, recebe tarefas (via issues/PRs ou Feishu), executa em sessão isolada e entrega o resultado sem intervenção humana.

Filosofia: *"mínimo de atenção humana, máximo de valor"*

## Stack

- TypeScript + pnpm
- DeepSeek Harness (runtime de agentes)
- GitHub API + Feishu (opcional)
- Painel web para intervenção humana quando necessário

## Relevância para o projeto

**Padrão arquitetural a estudar e adaptar:**
- Sessões isoladas por tarefa → aplicável em pipelines de RE automatizado
- Ciclo: evento GitHub → agente executa → entrega PR → humano aprova
- Base para um agente que: recebe um APK/binário, roda REA automaticamente, abre issue com o relatório

**Aplicação direta:**
- Automatizar o workflow de RE: `novo alvo → análise REA → notes/ gerado automaticamente`
- Integrar com o Second Brain: agente commita notas no repositório

## Próximos passos sugeridos

- [ ] Estudar a arquitetura de sessões isoladas (`src/session/`)
- [ ] Prototipar um agente similar em Python que use REA como backend
- [ ] Ver integração com GitHub Actions para trigger automático

# TokenEconomizer (Microsoft)

**Repositório:** https://github.com/microsoft/TokenEconomizer
**Stars:** 3.9k · Python · Apache 2.0
**Descoberto:** 2026-11-01 via [[notes/digest-2026-11-01]]

## O que é

Plugin que reduz o custo de execuções de agentes de codificação sem modificar o agente. Aprende com sessões anteriores no repositório e usa esse conhecimento para otimizar futuras execuções.

"Experience-driven black-box cost control for coding agents."

## Como funciona — 3 mecanismos

1. **Micro-skills**: memoriza fatos sobre o repositório (comandos de build, variáveis de ambiente, estrutura) de sessões anteriores → injeta no contexto das próximas
2. **Tool pruning**: remove ferramentas não utilizadas das requisições → menos tokens por chamada
3. **Failure-loop intervention**: detecta quando o agente fica preso em loops de erro e sugere abordagens alternativas

Armazenamento local em `~/.tokeneconomizer` — não manda nada para fora.

## Resultados de benchmark

- **SWE-Bench**: 18,4–30,9% menos custo médio em 5 combinações agente/modelo. Mais barato em todas as 30 células (repositório × combinação). Pass@1 subiu em 4 de 5 combinações.
- **Web-Bench**: 16–21% de redução
- Benchmarks de segurança: ganhos similares

## Instalação no Claude Code

```bash
git clone https://github.com/microsoft/TokenEconomizer.git
claude plugin marketplace add "$PWD/TokenEconomizer"
claude plugin install tokeneconomizer@tokeneconomizer
```

Após instalar: `/tokeneconomizer:status` para verificar, depois `/tokeneconomizer:toolprune refresh-catalog` uma vez.

## Compatibilidade

Claude Code, Codex CLI, GitHub Copilot CLI, Pi, opencode (experimental), Cursor Agent (experimental)

## Relevância para o projeto

**Instalação imediata recomendada** — redução de 18–30% no custo de tokens de todo agente que rodarmos neste projeto. Especialmente valioso em análises longas com REA.

## Próximo passo

- [ ] Instalar no Claude Code seguindo os passos acima
- [ ] Rodar `/tokeneconomizer:status` e `/tokeneconomizer:toolprune refresh-catalog`
- [ ] Medir redução de custo em uma sessão de análise RE

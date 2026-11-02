# craft-anything — RE Tool em Rust

**Repositório:** https://github.com/storytold/craft-anything
**Stars:** 1.1k · Rust · MIT
**Descoberto:** 2026-11-01 via [[notes/digest-2026-11-01]]

## O que é

Ferramenta de engenharia reversa open-source em Rust. Foco: estudar como qualquer software funciona e usar IA para construir suas próprias versões.

Diferente do REA (que foca em entender internos), o craft-anything foca no ciclo:
**Estudar → Construir → Verificar → Refinar**

## Como funciona

4 etapas:
1. **Estudo**: inspeciona o original — páginas em cada largura, código, arquivos, como executa
2. **Construção**: agente de codificação cria novo projeto na linguagem/framework escolhido
3. **Verificação**: compara versão construída com original e lista discrepâncias
4. **Refinamento**: visualizar, testar e iterar

Dois modos:
- **Clean Room**: só o que é visível (sem ler código interno)
- **Deep**: todas as ferramentas disponíveis, incluindo Ghidra quando instalado

## Alvos suportados — 314 ferramentas

Nativos, .NET, Java, Android, Apple/iOS, Electron/JS, websites, firmware, packet captures, databases, game files

## Stack e Arquitetura

- Motor RE puro em Rust (decodificadores, disassembler, decompilador próprios)
- WebAssembly: roda no browser
- Integração com Claude Code como agente de codificação
- Ferramentas disponíveis como CLI e como MCP tools

## Instalação

```bash
# Requer Rust 1.97+
git clone https://github.com/storytold/craft-anything
cargo install --path apps/craft-anything-cli
```

## Relação com REA

| | REA | craft-anything |
|--|-----|----------------|
| Foco | Entender internos | Entender → Reconstruir |
| Motor | Proprietário (rea-agents) | Rust open source |
| MCP | Sim (já instalado) | Sim (via CLI/MCP) |
| Ghidra | Integrado | Opcional |
| Clean room | Não | Sim |

**Os dois são complementares**: REA para análise profunda, craft-anything para reconstrução/prototipagem.

## Relevância para o projeto

- Complementa o REA no workflow de RE
- Clean Room mode é valioso para análise de competidores e compliance
- 314 ferramentas como MCP = expansão do arsenal atual
- Relevante para os projetos de backlog BI Tool Internals e Analytics SDK

## Próximos passos sugeridos

- [ ] Instalar e testar em um alvo simples (website ou Electron app)
- [ ] Comparar output com REA no mesmo alvo
- [ ] Avaliar se adicionar como MCP ao projeto

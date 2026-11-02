# Microsoft Qlib — AI-Oriented Quant Investment Platform

**Fonte:** https://github.com/microsoft/qlib
**Stars:** 49.9k · Python · MIT
**Descoberto:** 2026-11-01

## O que é

Plataforma open-source da Microsoft para pesquisa e implementação de estratégias de investimento quantitativo com IA. Pipeline completo: dados → modelos → backtesting → execução.

## Stack

- Python 3.8-3.12
- ML: XGBoost, LightGBM, LSTM, Transformer, TabNet
- Frameworks: PyTorch, TensorFlow
- Dados: HDF5, MongoDB, Arctic Backend
- RL: PPO, OPDS, TWAP

## Paradigmas suportados

1. **Supervised learning** — mineração de padrões e sinais de mercado
2. **Market dynamics modeling** — modelos adaptativos à dinâmica do mercado
3. **Reinforcement learning** — otimização contínua de estratégias de execução

## Feature destaque: RD-Agent

Integração com [RD-Agent](https://github.com/microsoft/RD-Agent) — agente LLM que automatiza o ciclo de pesquisa quantitativa:
- Gera hipóteses de fatores automaticamente
- Implementa, testa e itera sem intervenção humana
- Alinhado com a filosofia de agentes autônomos do dsh-superagent

## Relevância para o projeto

**Uso direto (Data Science / Econometria):**
- Plataforma pronta para explorar econometria quantitativa com ML
- Backtesting robusto para validar estratégias baseadas em dados
- Relevante para projetos de análise financeira com o perfil Meta/Data Analyst

**Engenharia Reversa:**
- Alvo interessante para RE: analisar como o qlib serializa/processa dados de mercado (HDF5, formatos internos)
- Estudar como o RD-Agent toma decisões e estrutura o ciclo de pesquisa autônoma
- Relevante para o backlog "Data Pipeline Format RE"

## Instalação rápida

```bash
pip install pyqlib
```

## Próximos passos sugeridos

- [ ] Explorar o RD-Agent como referência para agentes autônomos de análise de dados
- [ ] Usar qlib como plataforma base para análise quantitativa / econometria
- [ ] Considerar RE do formato interno HDF5 + serialização de features (backlog "Data Pipeline Format RE")

---
name: re-investigation
description: Use quando eu pedir para investigar um app, binário, API ou website. Executa uma investigação completa de engenharia reversa com REA.
---

# RE Investigation Workflow

## 1. Criar estrutura do alvo
- Crie `targets/<nome-do-alvo>/README.md` com: objetivo, tipo, ferramentas, status = "em progresso"
- Registre a decisão de abordagem em `decisions.md`

## 2. Identificar tipo de alvo
- **APK Android** → REA: `inspect_android_apk`, `inspect_apk_signature`, capture de rede
- **App JS/Electron** → REA: `analyze_javascript_application`
- **Binário nativo** → REA: análise com Ghidra/Hopper/IDA (verificar se instalado)
- **Website** → REA: análise de página, scripts, requests de rede
- **Captura de rede** → REA: HAR ou SAZ

## 3. Executar análise com REA
- Use REA via MCP para inspecionar o alvo
- Para cada achado relevante, pergunte ao REA por evidências
- Anote limitações (ofuscação, criptografia, anti-debug)

## 4. Documentar achados
- Crie uma nota por descoberta em `notes/<o-que-foi-descoberto>.md`
- Cada nota deve ter: O que foi descoberto, Evidência, Limitações, Próximos passos
- Atualize o README do alvo com status e link para as notas

## 5. Encerrar
- Liste perguntas sem resposta no README do alvo
- Sugira scripts Python para automação se aplicável
- Atualize `projects/now.md` com o novo status

@echo off
setlocal
title Aider - Modelos 100% Gratuitos (Custo ZERO)

:: Carrega chave do .env se existir
if exist "%~dp0.env" (
    for /f "usebackq tokens=1,2 delims==" %%A in ("%~dp0.env") do (
        if "%%A"=="OPENROUTER_API_KEY" set "OPENROUTER_API_KEY=%%B"
        if "%%A"=="GROQ_API_KEY" set "GROQ_API_KEY=%%B"
    )
)

if "%OPENROUTER_API_KEY%"=="" (
    echo [ERRO] Chave OPENROUTER_API_KEY nao encontrada no .env!
    pause
    exit /b 1
)

echo =====================================================================
echo   Aider Pair Programming CLI - Modelos 100%% Gratuitos (CUSTO $0.00)
echo =====================================================================
echo   [Contexto Injetado]:
echo     - sessions/current.md (Estado atual e ponto de parada)
echo     - projects/now.md    (Fases, diretrizes e backlog ativo)
echo     - decisions.md       (Decisoes tecnicas e arquitetura)
echo     - AGENTS.md          (Regras do projeto e instrucoes)
echo =====================================================================
echo   [1] OpenRouter Auto Free (Recomendado - Roteia pro melhor free online)
echo       -> openrouter/openrouter/free
echo.
echo   [2] Cohere North Mini Code (Especialista em Codigo / 100%% Free)
echo       -> openrouter/cohere/north-mini-code:free
echo.
echo   [3] NVIDIA Nemotron 3 Nano Omni (30B Reasoning / 100%% Free)
echo       -> openrouter/nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free
echo.
echo   [4] Liquid LFM 2.5 (Ultra rapido / 100%% Free)
echo       -> openrouter/liquid/lfm-2.5-2.6b:free
echo =====================================================================
set /p choice="Escolha o modelo (1-4) [Padrao: 1]: "

if "%choice%"=="2" (
    set "MODEL=openrouter/cohere/north-mini-code:free"
) else if "%choice%"=="3" (
    set "MODEL=openrouter/nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free"
) else if "%choice%"=="4" (
    set "MODEL=openrouter/liquid/lfm-2.5-2.6b:free"
) else (
    set "MODEL=openrouter/openrouter/free"
)

echo.
echo [*] Inicializando Aider com modelo 100%% GRATUITO: %MODEL%
echo [*] Garantia de Custo ZERO ($0.00). Injetando contexto mestre...
echo.

aider --model "%MODEL%" --read sessions\current.md --read projects\now.md --read decisions.md --read AGENTS.md
pause

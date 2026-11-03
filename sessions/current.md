# Session Handoff

## Estado atual
- **Agente:** Antigravity (Gemini 3.8 Flash)
- **Alvo ativo:** `targets/district-187/` (District 187 / S2 Rebirth — Motor Nativo LithTech Jupiter EX)
- **Timestamp:** 2026-11-02 22:42
- **Diretriz Absoluta:** 100% foco no executável e motor original LithTech (`TheRaw.exe`, `GameClient.dll`, `Engine_Server.dll`) e emulação de rede/servidor dedicado.
- **Entregas e Correções Consolidadas:**
  1. **Resolução Definitiva do `ApexGuard S2-320` e Crash `R6025 - pure virtual function call`:**
     - Documentado em [`notes/d187-apexguard-s2-320-dx-proxy.md`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/notes/d187-apexguard-s2-320-dx-proxy.md).
     - Diferente do pacote antigo `client/S2` (onde a proxy `D3DX9_43.dll` injetava `TheRawExt.dll`), o cliente `client-rebirth` utiliza uma cadeia de 3 DLLs-proxy verificada pelo `ApexGuard.dll`:
       - `D3DX9_43.dll` (119.864 bytes) -> carrega `dxbase.dll` (ausência na memória dispara `S2-320` e aborta com `R6025`)
       - `StringEditRuntime.dll` (88.120 bytes) -> carrega `strbase.dll` (`S2-321`)
       - `GameDatabase.dll` (88.120 bytes) -> carrega `dbbase.dll` (`S2-322`)
     - A `D3DX9_43.dll` original de 119.864 bytes foi restaurada em `targets/district-187/client-rebirth/D3DX9_43.dll` (com backup da runtime limpa em `D3DX9_43.dll.clean_runtime_bak`). **Nunca substituir `client-rebirth/D3DX9_43.dll` pela DLL do SysWOW64.**
  2. **Bind Exclusivo na Porta 12000 (`SO_EXCLUSIVEADDRUSE`) & Desbloqueio Scaleform (`0x00A40221`):**
     - [`scripts/d187-mock-server.py`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/scripts/d187-mock-server.py) configurado com `SO_EXCLUSIVEADDRUSE` para impedir que processos Python antigos compartilhem a porta 12000 e respondam com o payload antigo (`AccountID=1001` em vez de `0x00A40221`).
     - Documentado em [`notes/d187-login-scaleform-unlock.md`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/notes/d187-login-scaleform-unlock.md).
  3. **Launchers Oficiais Unificados & Limpeza da Raiz:**
     - [`D187_Launcher.bat`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/D187_Launcher.bat) -> Abre a interface gráfica oficial [`scripts/d187_launcher.py`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/scripts/d187_launcher.py) (Tkinter Dark/Gold) com modos Solo (Bots) e Online/LAN, monitor da porta 12000 e botão para o Web Portal.
     - [`launch_game.bat`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/launch_game.bat) -> Inicializador direto em 1 clique que verifica/inicia o servidor Hermit na porta 12000 e dispara `TheRaw.exe` com `__COMPAT_LAYER=RunAsInvoker`.
     - Launchers `.bat`/`.ps1` legados movidos para `scripts/legacy_launchers/` e scripts de diagnóstico movidos para `scripts/probes/`.
  4. **Separação Limpa de Portas Web (8080 vs 8081) e Gateway UDP (27888):**
     - [`scripts/d187_web_portal.py`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/scripts/d187_web_portal.py) na porta `8080`: Portal Web Standalone bilíngue (PT-BR/EN) com Arsenal de 185 armas, Ranking (58 patentes) e registro de contas SQLite.
     - [`scripts/d187_web_panel.py`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/scripts/d187_web_panel.py) na porta `8081`: Painel Técnico de Controle com `ServiceManager` apontando para [`scripts/d187_dedicated_gateway.py`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/scripts/d187_dedicated_gateway.py) (UDP 27888) e [`launch_game.bat`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/launch_game.bat).
  5. **Extração Completa de Mapas, NavMeshes A*, Heatmaps 2D KDE e Áudio FMOD FSB5:**
     - 29 mapas `.World00p` em `targets/district-187/client-rebirth/Game/Worlds/`.
     - 25 radares táticos (`targets/district-187/maps/`), 25 NavMeshes A* (`targets/district-187/navmeshes/`) e 25 Heatmaps 2D KDE (`targets/district-187/analytics/index.html`).
     - 901 amostras de áudio FMOD FSB5 extraídas e catalogadas em `targets/district-187/data/audio_manifest.json`.
  6. **Alvo Paralelo: Engenharia Reversa de Armazenamento Colunar (Apache Parquet):**
     - Dissector binário puro Python [`scripts/parse_parquet_binary.py`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/scripts/parse_parquet_binary.py) e nota [`notes/parquet-columnar-binary-format-reverse-engineering.md`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/notes/parquet-columnar-binary-format-reverse-engineering.md).

## Próximo Passo
- Para jogar ou testar o cliente nativo:
  - Executar `.\D187_Launcher.bat` (Launcher Gráfico) ou `.\launch_game.bat` (Inicialização Direta).
  - Servidor Hermit (`scripts/d187-mock-server.py`) está ativo com bind exclusivo em `127.0.0.1:12000`.
  - Confirmar no desktop que o pop-up `S2-320` / `R6025` não ocorre mais com `client-rebirth/D3DX9_43.dll` restaurada (119.864 bytes) e validar a transição pós-login para o Lobby.

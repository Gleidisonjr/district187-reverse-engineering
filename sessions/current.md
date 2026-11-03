# Session Handoff

## Estado atual
- **Agente:** Antigravity (Gemini 3.8 Flash)
- **Alvo ativo:** `targets/district-187/` (District 187 / S2 Rebirth — Motor Nativo LithTech Jupiter EX)
- **Timestamp:** 2026-11-02 23:45
- **Diretriz Absoluta:** 100% foco no executável e motor original LithTech (`TheRaw.exe`, `GameClient.dll`, `Engine_Server.dll`) e emulação de rede/servidor dedicado.
- **Entregas e Correções Consolidadas:**
  1. **Remoção Total e Purificação do Anticheat ApexGuard:**
     - REA completa do `S2Launcher.exe` (.NET C#) e de `ApexGuard.dll` (*Apex Anti-Cheat Fortress v4.2 por Bluzer & Requ*).
     - Identificado que as credenciais do launcher são apenas para a API web/Discord e não são passadas ao jogo; a autenticação do motor LithTech ocorre 100% in-game via Scaleform UI na porta 12000.
     - Identificada a cadeia de injeção forçada de `ApexGuard.dll` via 3 DLLs-proxy (`D3DX9_43.dll` 119KB, `StringEditRuntime.dll` 88KB e `GameDatabase.dll` 88KB).
     - Como a versão é privada (para bots e LAN com amigos), as 3 DLLs-proxy foram substituídas pelas versões limpas e originais (`dxbase.dll` 1.99MB DirectX 9, `strbase.dll` 23KB e `dbbase.dll` 138KB). `ApexGuard.dll` foi desativada e renomeada para `.disabled`.
     - Neutralizado o hook de anel `.s2kl` em `targets/district-187/client-rebirth/Game/GameClient.dll` (offset `0x54D0A0` / `0x1058c0a0`) com `0xC3` (`RET`), eliminando qualquer tentativa de IPC com o guard e preservando o destravamento 144+ FPS (`.s2fp`) e zoom (`.s2zm`).
     - **Erros `S2-320` e crash `R6025` completamente extintos.**
     - Documentado em [`notes/d187-apexguard-removal-and-server-state-machine.md`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/notes/d187-apexguard-removal-and-server-state-machine.md).
  2. **Resolução da Máquina de Estados e Pacotes do Mock Server (`d187-mock-server.py`):**
     - Desmontados os handlers em assembly de `GameClient.dll` para todas as telas pós-login:
       - `SN_GroupList` (`0x220107`, 66B por grupo, `"G1"`)
       - `SN_ServerList` (`0x220108`, 20B por servidor, `"S2"` -> `"G1"`)
       - `SN_ServerInfo` (`0x220101`, 98B por servidor, `"S2"`, IP 127.0.0.1, Porta 12000)
       - `SN_ChannelList` (`0x220102`, 57B por canal, código `"S2"` no cabeçalho)
       - `SN_LockEnd` (`0x210121`, `ChangeScene(0)` para transição fora de `CLoginScene`)
       - `SA_EnterUser` (`0x220112`) + `SN_RoomList` (`0x220204`, 7B/sala)
       - `SA_CreateRoom` (`0x220202`) e `SA_EnterRoom` (`0x220232`)
       - `SA_MoveServer` (`0x220132`) e `SA_QuickJoin` (`0x220162`)
       - `SN_BattleStart` (`0x420310`)
     - Servidor [`scripts/d187-mock-server.py`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/scripts/d187-mock-server.py) atualizado e ativo em background na porta `12000` (task `task-5035`).
     - Validado o teste ponta a ponta com 100% de sucesso em [`scripts/test_client_handshake_smoke.py`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/scripts/test_client_handshake_smoke.py).
  3. **Launchers Oficiais Unificados:**
     - [`D187_Launcher.bat`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/D187_Launcher.bat) -> Launcher Gráfico Tkinter com modos Solo (Bots) e Online/LAN, monitor da porta 12000 e botão para o Web Portal.
     - [`launch_game.bat`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/launch_game.bat) -> Inicializador direto em 1 clique com verificação automática do servidor na porta 12000.

## Próximo Passo
- Para jogar ou testar o cliente nativo:
  - Executar `.\D187_Launcher.bat` ou `.\launch_game.bat`.
  - Inserir login e senha na tela inicial do jogo e clicar OK.
  - O mock server autenticará o usuário, destravará a tela de "Please Wait" e transitará diretamente para a seleção de Servidor -> Canais -> Lobby de salas.

# Session Handoff

## Estado atual
- **Agente:** Antigravity (Gemini 4 Neon)
- **Alvo ativo:** `targets/district-187/` (District 187 / S2 Rebirth — Motor Nativo LithTech Jupiter EX)
- **Timestamp:** 2026-11-19 13:40
- **Diretriz Absoluta:** 100% foco no executável e motor original LithTech (`TheRaw.exe`, `GameClient.dll`, `Engine_Server.dll`, `GameServer.dll`) e emulação de rede/servidor dedicado nativo. Toda alteração deve ser documentada em detalhes e sincronizada no GitHub (`Gleidisonjr/district187-reverse-engineering`).
- **Entregas e Correções Consolidadas:**
  1. **Remoção Total e Purificação do Anticheat ApexGuard:**
     - `ApexGuard.dll` desativada (`.disabled`), 3 DLLs limpas restauradas (`D3DX9_43.dll`, `StringEditRuntime.dll`, `GameDatabase.dll`) e hook `.s2kl` (`0x1058c0a0`) + `CApexMgr::Start` (`0x10010750`) neutralizados em `GameClient.dll` (raiz e `Game\GameClient.dll` 100% sincronizados via SHA256).
  2. **Resolução Definitiva de `LT_ERRORCOPYINGFILE`, Direct3D 9 (DXVK Vulkan) e Scaleform Flash:**
     - DXVK v3.1.1 x86 ([`targets/district-187/client-rebirth/d3d9.dll`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/targets/district-187/client-rebirth/d3d9.dll)) rodando na AMD Radeon RX 9060 XT (`1920x1080` Vulkan sem crashes/popups).
     - 2.673 arquivos Scaleform Flash extraídos em `Interface\Flash\` e patches de `FunctionList.csv` (`0x5210`) + `GDB Mission/Level DetailInfo` (`0x10408b50` / `0x10066304`) validados.
  3. **Servidor Dedicado Nativo LithTech Real (`D187_ServerHost.exe` — MSVC x86):**
     - Mapeada a ABI completa de `Engine_Server.dll` (`CreateServer(SI_VERSION=2)`, vtable `0x10158bcc` de 28 slots, **`HostGame` no slot `[25]`** -> `CUDPDriver::HostSession`, `NetHost` com `wchar_t` UTF-16LE, `ServerGameOptions` com 6 `std::string` VC10-safe passados via `SetGameInfo(&pOpts)` antes de `LoadBinaries()`, e **`LTGUID` autêntico `{DF560590-D918-4A51-9CB1-38EBBE3879AD}`** extraído de `TheRaw.exe` `CNetMgr+0x28`).
     - Compilado [`targets/district-187/server_host/D187_ServerHost.exe`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/targets/district-187/server_host/d187_server_host.cpp) carregando `Engine_Server.dll` + `Game\GameServer.dll` (`LoadBinaries -> OK, status=0x1`), abrindo **`UDP 0.0.0.0:27888`** (`HostGame -> OK`), carregando `Worlds\Arrival.World00p` (`StartWorld -> OK`) e rodando o tick loop nativo a 60Hz.
  4. **Desbloqueio Real em Tela (Login → Canal → Lobby → Create Room → Sala → Conexão UDP 27888):**
     - **`Hermit::Session::Waiter::TCP` (`0x0050BB10`):** Implementado `self.send_seq` monotônico no offset `+4` do header Hermit em `scripts/d187-mock-server.py`, desbloqueando definitivamente `Kanal Seçimi` e `Oyun Lobisi`.
     - **Patch de Mapas/Modos (`0x10408B50` / `0x10408C7E`):** Restaurado `sub esp, 0x11c` em `0x10408B50` e aplicado patch de 2 bytes `74 3f -> 74 27` (`je 0x10408ca7`) em `0x10408C7E` em `GameClient.dll` (ambas cópias sincronizadas), populando todos os mapas e modos (`TDM`, `8 vs 8`, `General`) no `Create Room`.
     - **Sala & Conexão 3D:** Implementados `SN_ServerInfo` (`+10` IP / `+26` Name), `SN_Info (0x220203)` (`0x101393A0` → `ChangeScene(3)` entrando em `Bekleme Odası`), `SN_HostConnect (0x420303)` (`0x10138EE0` → `CMissionMgr::StartGameAsClient("127.0.0.1:27888")`), `0x220314` (`F5 Başla`) e `0x240101`/`0x240102` (`Shop/Inventory`).
     - Documentação master publicada em [`notes/d187-native-server-host-and-lobby-protocol-breakthroughs.md`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/notes/d187-native-server-host-and-lobby-protocol-breakthroughs.md).
  5. **Launcher, QoL & Web Panel Integrados:**
     - [`scripts/d187_launcher.py`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/scripts/d187_launcher.py), [`D187_Launcher.bat`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/D187_Launcher.bat), [`launch_game.bat`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/launch_game.bat), [`scripts/d187_qol_optimizer.py`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/scripts/d187_qol_optimizer.py) e [`scripts/d187_web_panel.py`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/scripts/d187_web_panel.py) atualizados para subir automaticamente **Hermit Server (TCP 12000) + Native LithTech Dedicated Server (`D187_ServerHost.exe`, UDP 27888) + `TheRaw.exe`**, com thread-safety no Tkinter (`self.after`), sem `messagebox` roubando foco, 9 mapas válidos em disco e `pythonw`.

## Próximo Passo
- **Jogar agora:** Execute `.\D187_Launcher.bat` (interface gráfica) ou `.\launch_game.bat` (1 clique). Na tela de login in-game, entre com `gleidison` + qualquer senha.
- **Se quiser testar entrada em partida 3D ao vivo:** Após logar e iniciar a sala, monitore se `TheRaw.exe` conecta no `D187_ServerHost.exe` (UDP 27888) ou reporte qualquer tela/mensagem in-game para ajuste fino imediato.

---

## Coordenação Multi-Agente (Claude Code + Antigravity)

> Sistema ativo desde 2026-11-19. Ambos os agentes trabalham neste repositório em paralelo.

| Arquivo | Propósito |
|---|---|
| [`sessions/protocol.md`](sessions/protocol.md) | Regras de trabalho conjunto, ownership de arquivos, sessões REA |
| [`sessions/task-queue.md`](sessions/task-queue.md) | Fila de tarefas com estado OPEN/DOING/DONE e dono |
| [`sessions/agent-claude.md`](sessions/agent-claude.md) | Estado atual do Claude Code |
| [`sessions/agent-agy.md`](sessions/agent-agy.md) | Estado atual do Antigravity |

**Regra de ouro ao iniciar qualquer sessão:** leia `task-queue.md` antes de qualquer trabalho.

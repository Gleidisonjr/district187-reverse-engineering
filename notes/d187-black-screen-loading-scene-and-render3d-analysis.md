# District 187 — Análise RE: Tela Preta Pós-`InWorld` e `"Missing LoadingImage String"`

**Alvo:** `targets/district-187/client-rebirth/GameClient.dll` (ImageBase `0x10000000`)  
**Contexto:** `TheRaw.exe` ↔ `TheRawServer.exe` completam 100% do handshake UDP até `eClientConnectionState_InWorld` (`pkt 8` / `pkt 10` sem erros em `trace_3d_packets.log`), mas o cliente exibe o popup `"Missing LoadingImage String"` e permanece em tela preta durante toda a partida.

---

## 1. Causa Raiz do Popup `"Missing LoadingImage String"` (`0x1016D820`)

### Cadeia de execução comprovada
1. **Inicialização (`CMissionMgr::StartGameAsClient @ 0x10088070`)**:
   - Seta `CMissionMgr->m_nCurrentWorld` (`[0x10527960] + 0x04`) = **`-1` (`0xFFFFFFFF`)** em `0x10088092`.
2. **Único setter (`CMissionMgr::SetCurrentWorld @ 0x100880B0`)**:
   - Chamado exclusivamente por **`ClientConnectionMgr::HandleClientConnect_Hello` (`0x10023720`, call em `0x100237CD`)**, disparado pelo pacote UDP **`MID_CLIENTCONNECTION` (`0xEE`)**, substate **`eClientConnectionState_Hello`**.
   - Em `0x100237C0`, lê a string do mapa do `ILTMessage_Read` (`ReadString(buf, 0x208)`) e chama `CMissionMgr::SetCurrentWorld(buf)` → **`0x10407650(buf, &outIdx)`**.
3. **Formato exato esperado por `0x10407650`**:
   - Itera todos os records de mundo do GameDatabase e chama **`0x10406070(outBuf, idx, /*bIncludePath=*/1)`**, comparando o resultado com `buf` via `MSVCR100.dll!_stricmp` (`0x1048240C`).
   - **`0x10406070`** lê o atributo `"WorldFileName"` (`0x104C1110`) e chama **`0x103E4A06(worldFileName, dirBuf, fnameBuf, NULL)`** (`_splitpath` com `ext = NULL`!), concatenando `dirBuf + fnameBuf` **SEM a extensão `.World00p`** (ex: `"Worlds\\Arrival"`).
4. **Por que `[0x10527960] + 0x04` permaneceu `-1`**:
   - Em `targets/district-187/server_host/d187_server_host.cpp:305`, o servidor passa `worldName = "Worlds\\Arrival.World00p"` (COM `.World00p`) para `StartWorld(&req)`.
   - `GameServer.dll` envia `"Worlds\\Arrival.World00p"` no `Hello`.
   - `_stricmp("Worlds\\Arrival.World00p", "Worlds\\Arrival") != 0` → `0x10407650` retorna `false` → `CMissionMgr+4` fica **`-1`**.
   - Quando `SMSG_LOADWORLD` chega (`0x100883B0` → `0x10088300`), `0x10088300` abre a cena de loading **`ChangeScene(8)`** (`0x1004B8A0(8)` em `0x1008838B`) **sem alterar `CMissionMgr+4`**.
   - `CInGameLoadingHandler` (vtable `0x104A2794`, slot `+0x1C` @ `0x104A27B0` → **`0x1016D820`**) chama `0x10405AB0(-1)` → `NULL` → `"LoadingTexture"` vazio → popup `L"Missing LoadingImage String"` (`0x1016D8C1`) e `ret` antecipado (pula `Loading.setBg`).

---

## 2. Causa Raiz da Tela Preta Pós-`InWorld`

### 2.1 Gates de Renderização 3D (`CGameClientShell::Render @ 0x10234F60`)
Na vtable de `CGameClientShell` (`0x104AACC8`), **`CGameClientShell::Render()` (`0x10234F60`)** só chama **`RenderCamera()` (`0x10234280` → `ILTRenderMgr::Start3D` + renderização da câmera 3D)** se TODOS os gates abaixo passarem:

| Gate | Endereço | Condição exigida | Se falhar |
|---|---|---|---|
| **1** | `0x10234F63..0x10234F70` | `CInGameHandler::Instance()->m_pUserInfo` (`[0x10014700() + 0x84]`, RTTI `.?AVCUserInfo@HUD@@`) `!= NULL` | **Retorna imediatamente** (sem `RenderCamera` nem `FlipScreen`) |
| **2** | `0x10234F72..0x10234F79` | `pMyInfo = HUD::CUserInfo::GetMyInfo()` (`0x1018E180`) `!= NULL` | **Retorna imediatamente** (sem `RenderCamera` nem `FlipScreen`) |
| **3** | `0x10234F81..0x10234F8A` | Se `[pMyInfo + 0x10] == 0` (`!bManagerMode`): `g_pIntroFlash->m_bPlaying` (`[0x105175C4 + 0xC]`) `== 0` | Pula `RenderCamera`, chama só `FlipScreen` |
| **4** | `0x10234F8C..0x10234F96` | Se `[pMyInfo + 0x10] == 0`: `g_pPlayerMgr->IsPlayerInWorld()` (`0x10215050`: `[0x10533B94 + 0x3C] != 0`) `== 1` | Pula `RenderCamera`, chama só `FlipScreen` |

Os mesmos gates (`GetMyInfo() != NULL` e `m_ePlayerState != 0`) bloqueiam **`CGameClientShell::UpdatePlaying()` (`0x102396C0`)** (impedindo `FirstUpdate` / `PausePhysics 0` @ `0x10239090`) e **`0x10233480`** (ativação do renderer/câmera).

### 2.2 Quem Fecha a Cena de Loading (`Scene 8` → `Scene 12 / 0xC`)
O **único** código em toda a `GameClient.dll` que fecha `CInGameLoadingHandler` (Scene `8`) e ativa `CInGameHandler` (Scene `0xC` via `ChangeScene(0xC)` @ `0x1004B8A0`) é **`CInGameLoadingHandler::Update()` (`0x1016D520`, calls em `0x1016D60A` e `0x1016D630`)**.

Ele exige **todas as 6 condições simultaneamente**:
1. `CGameClientShell::m_bInWorld` (`[0x10548860] + 0x798`) `== 1` (`0x1016D526`, setado em `CGameClientShell::OnEnterWorld @ 0x10236B18`).
2. Fila de loads assíncronos `== 0` (`0x1016D558`).
3. `ClientConnectionMgr::GetState()` (`0x10023AC0`) `== 0xB` (`eClientConnectionState_InWorld`, `0x1016D56C`).
4. **`HUD::CUserInfo::GetMyInfo()` (`0x1018E180`) `!= NULL`** (`0x1016D589..0x1016D592`).
5. **`g_pPlayerMgr->m_ePlayerState` (`[0x10533B94] + 0x3C`) `!= 0` (`ePlayerState_None`)** (`0x1016D5B8..0x1016D5C8`; se `== 5`/`Spectator`, exige `[+0x40] != 0`).
   - Atualizado via pacote UDP **`MID_PLAYER_STATE_CHANGE` (`0x67` / 103)** → handler `0x10027A70` (registrado em `0x10027468`) → **`CPlayerMgr::HandleMsgPlayerStateChange` (`0x1021D8F0`)**, payload 1 byte (`1 = ePlayerState_Alive`, `2 = Dying_Start`, `3 = Dying_Stage2`, `4 = Dead`, `5 = Spectator`).
6. **`g_pPlayerMgr->m_pMoveMgr->m_pCharFX` (`[[0x10533B94 + 0x24] + 0x20]`) `!= NULL`** (`0x1016D5F6..0x1016D5FD`).
   - Setado em `0x101A0E20` → `0x1021CFC0` → `0x10200A74` quando o `CCharacterFX` do jogador local é criado com `m_bIsPlayer != 0` e `m_hServerObject == g_pLTClient->GetClientObject()`.

### 2.3 Por que `HUD::CUserInfo::GetMyInfo()` (`0x1018E180`) Falha com o Mock Server Atual
- `HUD::CUserInfo` (`[CInGameHandler + 0x84]`) é populado exclusivamente pelo pacote Hermit TCP **`SN_BaseUserList` (`0x00222112`)** → handler **`0x100CB7B0`** (registrado em `CInGameHandler::Init @ 0x1017AE85`).
- Em `0x1018E180`, `GetMyInfo()` percorre a lista procurando `word ptr [entry + 0] == [HUD::CUserInfo + 0xC]` (`m_nLocalUserID`).
- Em `0x100CB7B0`, há **três pontos de falha críticos**:
  1. **`m_nLocalUserID` (`[ebp + 0xC]`) só é atualizado em `0x100CB8C7`** se `wcscmp(HUD::CUserInfo::m_wstrMyName [ebp+0x10], nickname) == 0` (`0x100CB8AE..0x100CB8C2`). No construtor `0x1018DF32`, `m_wstrMyName` inicia vazia (`L""`) e `m_nLocalUserID` inicia em `0`, enquanto `d187-mock-server.py` envia `user_id = 1`! Se `m_wstrMyName` não bater com `nickname` (ou `user_id != 0`), `m_nLocalUserID` fica `0` enquanto a entrada tem `1` → `GetMyInfo()` retorna `NULL` para sempre!
  2. **`HUD::CUserInfo::Add` (`0x1018E3A0`)** chama `TeamMgr::0x1040EA80(team)` (`0x1018E3B9`). `0x1040EA80` retorna `TeamMgr[0x01]` (se `team == TeamMgr[0x30]`) ou `TeamMgr[0x19]` (se `team == TeamMgr[0x31]`), senão `0xFF`. Em `0x1018E3F8`: se o retorno for `0xFF`, **o usuário é descartado e não entra na lista**.
  3. **`CInGameHandler::Init` (`0x1017AB00`)** é quem aloca `[CInGameHandler + 0x84]` (`0x1017B99E`). Se `SN_BaseUserList (0x222112)` chegar antes de `[CInGameHandler + 0x84]` existir, `0x100CB7DE` descarta o pacote silenciosamente.

> **Evidência adicional em `server_host.log`**: Nas linhas 165–178, após `eClientConnectionState_InWorld`, o `GameServer.dll` autêntico já envia `packet ID 13, length 16` (2 bytes = `MID_PLAYER_STATE_CHANGE (0x67)` + `ePlayerState_Alive (1)`) e `packet ID 8` (criação de `CCharacterFX`). Portanto, o bloqueador primário da tela preta está em **`HUD::CUserInfo::GetMyInfo()` (`0x1018E180`) retornando `NULL`** (ou na ausência do `m_ePlayerState`/`m_pCharFX` caso o `GetClientObject()` não coincida com o player local).

---

## 3. Correções Cirúrgicas Recomendadas

### Correção 1 — Eliminar `"Missing LoadingImage String"` (`d187_server_host.cpp`)
- Em `targets/district-187/server_host/d187_server_host.cpp:305`:
  - Trocar `const char* worldName = "Worlds\\Arrival.World00p";` para **`"Worlds\\Arrival"`** (sem `.World00p`), pois `Engine_Server.dll` / `GameClient.dll` (`0x10088110`) adicionam `.World00p` ao abrir o arquivo e `0x10407650` compara o nome **sem extensão** via `_splitpath(..., NULL)`.
  - *(Nota: se `Engine_Server.dll::StartWorld` exigir `.World00p` no disco, o `worldName` enviado no `Hello` de `GameServer.dll` precisa vir sem `.World00p`.)*

### Correção 2 — Destravar `HUD::CUserInfo::GetMyInfo()` e Sair da Tela Preta (`d187-mock-server.py`)
1. **Teste diagnóstico instantâneo (1 linha, sem editar binários)**:
   - Rodar o cliente com CVar **`+FlashDevMode 1`** (ou setar `FlashDevMode` = `1`, handle `0x10527964`): em `0x1018E180`, quando `FlashDevMode == 1`, `GetMyInfo()` retorna imediatamente um `ST_InGameUserInfo` estático válido (`0x10530110`) com `bManagerMode = 0`.
   - Se a tela 3D aparecer imediatamente com `FlashDevMode 1`, confirma 100% que `m_ePlayerState` e `m_pCharFX` já estão OK e que o único bloqueador era `HUD::CUserInfo::GetMyInfo() == NULL`.
2. **Correção definitiva em `scripts/d187-mock-server.py`**:
   - Em `build_base_user_list_hermit` (`0x222112`): garantir que `user_id` do jogador local seja **`0`** (matching `[HUD::CUserInfo + 0xC] == 0` e `ClientID : 0` do `Engine_Server.dll`) **e** que `nickname` corresponda exatamente ao nickname autenticado na sessão, enviado **após** `SN_BaseRoomInfo (0x222111)` (que inicializa `TeamMgr[0x30/0x31/0x32]`) e com `CInGameHandler+0x84` já inicializado.
   - Se mesmo com `GetMyInfo() != NULL` o cliente ainda ficar preso em `CInGameLoadingHandler::Update`, logar o retorno de `0x1016D5DA` (`"return g_pPlayerMgr->GetPlayerState() == %d %d"`) ou verificar `[[0x10533B94 + 0x24] + 0x20]` (`CMoveMgr::m_pCharFX`) para confirmar recebimento de `MID_PLAYER_STATE_CHANGE (0x67, 1)` e criação do `CCharacterFX` local.

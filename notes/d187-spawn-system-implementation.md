# District 187 — Spawn System Implementation & Black Screen Fix

**Alvo:** `targets/district-187/client-rebirth/` (`GameClient.dll` + `GameServer.dll`)  
**Scripts modificados:** `scripts/d187-mock-server.py`, `targets/district-187/server_host/d187_server_host.cpp`  
**Baseado em:**  
- `notes/d187-gameserver-player-spawn-and-mission-state.md`  
- `notes/d187-black-screen-loading-scene-and-render3d-analysis.md`  
- `notes/district-187-full-network-protocol-specification.md`

---

## O que foi descoberto

### 1. Causa Raiz da Tela Preta Pós-InWorld

A cadeia completa de bloqueio até render 3D:

1. `CGameClientShell::Render()` (`0x10234F60`) exige `HUD::CUserInfo::GetMyInfo()` (`0x1018E180`) `!= NULL`.
2. `GetMyInfo()` percorre a lista de usuários procurando `word[entry+0] == m_nLocalUserID`. O `m_nLocalUserID` inicia em `0` (construtor `0x1018DF32`).
3. `SN_BaseUserList` (`0x222112`, handler `0x100CB7B0`) popula essa lista. O uid `0` na entrada do jogador local é o único que satisfaz `m_nLocalUserID == 0`.
4. Se `self.room_users` estava vazio quando F5 era pressionado, `SN_BaseUserList` era enviado com `count=0` → lista vazia → `GetMyInfo()` retorna sempre NULL → tela preta permanente.

### 2. Causa Raiz do Spawn Não Disparar

O spawn em `CPlayerObj::Respawn()` (`0x1007C350`) requer:
- `m_bClientLoaded (+0x934) == 1` **E** `m_bReadyToRespawn (+0x935) == 1`
- Ambos setados pelo handler de **MID 0x69** (`0x1004FE40`) no lado do `GameServer.dll`
- Com `m_bStandalone == 0` (padrão), o handler não seta `+0x935` — envia TCP `0x230103` ao RoomServer e trava
- **Correção**: `GameServerNetMgr::m_bStandalone (+0x6C) = 1` ativa o respawn imediato sem RoomServer

### 3. Causa Raiz do `"Missing LoadingImage String"`

- `eClientConnectionState_Hello` (`GameServer.dll 0x100349A0`) lê `CGameServerShell::m_sCurLevel` e envia no MID `0xED` substate 3
- `m_sCurLevel` fica `""` porque `StartWorld()` não chama `SetCurLevel()` via `CServerSaveLoadMgr::LoadNewLevel`
- `GameClient.dll 0x10407650` compara o nome recebido **sem a extensão `.World00p`** (via `_splitpath` com `ext=NULL`)
- **Correção**: chamar `SetCurLevel("Worlds\\Arrival")` (sem `.World00p`) antes de `StartWorld()`

---

## Evidência — Layouts de Pacotes

### `SN_BaseUserList` (`0x222112`) — stride 270 bytes/entry
```
+0x00  uint16  user_id    → local player DEVE ser 0 (match m_nLocalUserID=0)
+0x02  uint16  team       → ROOM_TEAM_A(0)/ROOM_TEAM_B(1)/ROOM_TEAM_OBSERVER(2)
+0x04  char[]  nickname   → DEVE ser idêntico ao enviado em SN_UserInfo (0x210101) offset +0x00
+0x06..+0x10D  zeros      → safe (restante dos 270 bytes)
```

### `MID 0x69` — cliente → GameServer.dll (via UDP)
- Handler: `0x1004FE40` (despachado em `0x10054EE2`)
- Payload: opaque (engine-internal), sem formato público conhecido
- Efeito com `m_bStandalone=1`: seta `CPlayerObj+0x934=1` e `CPlayerObj+0x935=1` → `Respawn()` no próximo tick

### `SN_HostConnect` (`0x420303`) — 35 bytes payload
```
+0x00  uint16 LE  port      (27888)
+0x02  uint8      pad       (0)
+0x03  char[]     IP ASCII  ("127.0.0.1\x00", null-terminated, padded to 32B)
```
Handler `0x10138EE0` → `CMissionMgr::StartGameAsClient("127.0.0.1:27888")` → cliente conecta ao servidor UDP.

---

## Mudanças Implementadas

### `scripts/d187-mock-server.py` — Mudança Cirúrgica

**Localização:** handler `CN_PlayStartButton (0x222103)` / `CN_StartButton (0x220301)` / `CQ_StartGame (0x220314)`

**Problema corrigido:** `self.room_users` poderia estar vazio se o jogador iniciasse batalha sem passar pelo fluxo de criação/entrada de sala. Resultado: `SN_BaseUserList` enviava count=0 → lista vazia → `GetMyInfo()` retornava NULL → tela preta.

**Mudança:** Auto-popular `self.room_users` com o jogador local SE estiver vazio, E garantir que `room_users[0]["nickname"]` sempre seja o nickname autenticado (da `SN_UserInfo`).

```python
# ANTES (linha ~1088)
users = self.room_users or []
self.send_pkt(build_base_user_list_hermit(self.session_id, users, ...))

# DEPOIS
nick = self.user_data.get("nickname", "Gleidison") if self.user_data else "Gleidison"
rank = int(self.user_data.get("rank", 58)) if self.user_data else 58
if not self.room_users:
    self.room_users = [{"user_id": 1, "nickname": nick, "rank": rank, "team": ROOM_TEAM_A, "state": 1}]
self.room_users[0]["nickname"] = nick  # Garantia: nickname sincronizado com SN_UserInfo
users = self.room_users
self.send_pkt(build_base_user_list_hermit(self.session_id, users, ...))
```

**Verificado já correto:**
- `build_base_user_list_hermit` força `uid=0` para `idx=0` (linha 690) ✅
- `SN_BaseRoomInfo` enviado antes de `SN_BaseUserList` ✅
- `SO_EXCLUSIVEADDRUSE` na porta 12000 ✅

### `targets/district-187/server_host/d187_server_host.cpp` — Já correto

Todas as 3 correções cirúrgicas já estavam implementadas (Fase 14):
- Linha 464: `pNetMgr[0x6C] = 1` — `m_bStandalone = 1` ✅
- Linhas 468-479: `SetCurLevel("Worlds\\Arrival")` sem `.World00p` ✅
- Linhas 496-503: `SetMissionState(1, 1)` após `StartWorld()` ✅

---

## O que ainda precisa ser testado

1. **Verificar `HUD::CUserInfo::GetMyInfo() != NULL`**: Adicionar log no servidor quando `SN_BaseUserList` for enviado e confirmar que `count >= 1` e `nickname` coincide com o `SN_UserInfo`.

2. **Confirmar MID 0x69 chegando ao `GameServer.dll`**: O cliente envia MID 0x69 via UDP ao servidor nativo (27888) após `eClientConnectionState_InWorld`. Com `m_bStandalone=1`, o spawn deve ocorrer. Verificar no `server_host.log` se `PS_ALIVE` ou `AddDefaultWeapons` aparece após a conexão.

3. **Avatar `engine\default.Model00p`**: Cosmético — spawn funciona com o modelo fallback. Para fixar, é necessário identificar qual pacote Hermit popula `NetClientData+0x6C` no cliente e preencher um HRECORD de operador válido do `TheRaw.Gamdb00p`.

4. **Teste com `+FlashDevMode 1`**: Se a tela 3D aparecer com esse cvar, confirma que `m_pCharFX` e `m_ePlayerState` estão OK e que o único bloqueador era `GetMyInfo() == NULL`.

5. **`m_ePlayerState` via UDP**: O servidor nativo envia `MID_PLAYER_STATE_CHANGE (0x67/103)` com `uint8=1 (PS_ALIVE)` via UDP — necessário para fechar `CInGameLoadingHandler` (Scene 8) e ativar `CInGameHandler` (Scene 0xC). Verificar se o gateway UDP (`scripts/d187_dedicated_gateway.py`) repassa esses pacotes corretamente ou se o servidor nativo em `d187_server_host.cpp` os envia diretamente.

---

## Limitações

- Análise baseada em RE estática de `GameClient.dll` e `GameServer.dll` (sem execução instrumentada)
- O `NetClientData` que o cliente envia ao servidor UDP na conexão não foi dissecado completamente — avatar permanece `engine\default.Model00p`
- MID 0x69 é interno ao motor LithTech, payload não documentado publicamente; o cpp server host depende do `GameServer.dll` autêntico para processá-lo

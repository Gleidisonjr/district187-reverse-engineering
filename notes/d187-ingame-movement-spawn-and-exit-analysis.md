# District 187 — Análise In-Game: `"Connected. Starting game."`, Trava WASD, HP=0, Câmera/Arma e `ESC → Sair` (`0x222132`)

Análise estática (somente leitura) de [`GameClient.dll`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/targets/district-187/client-rebirth/GameClient.dll) (`ImageBase = 0x10000000`), [`GameServer.dll`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/targets/district-187/client-rebirth/Game/GameServer.dll) (`ImageBase = 0x10000000`) e [`ptbr_translations.csv`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/targets/district-187/data/ptbr_translations.csv), partindo do contexto de [`targets/district-187/README.md`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/targets/district-187/README.md) e [`notes/d187-gameserver-player-spawn-and-mission-state.md`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/notes/d187-gameserver-player-spawn-and-mission-state.md).

---

## 1. Origem de `"Connected. Starting game."` e Máquina de Estados `MID 0xC4` (`m_eMissionState`)

### Cadeia exata do banner amarelo no cliente
1. **String de localização** ([`ptbr_translations.csv`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/targets/district-187/data/ptbr_translations.csv#L71)):
   - Chave: `GAME_GAMESTART` → `"Connected. Starting game."` (PT-BR: `"Conectado. Iniciando partida."`).
2. **Tabela de strings em `GameClient.dll`**:
   - `"GAME_GAMESTART"` em `0x10494C98`, referenciada em `0x100796C4` dentro de `GetStringKeyById(int id)` (`0x100785B0`, jump table `0x1007C180`), índice **`0xD3` (211)**.
   - `"GAME_WAITING"` está logo abaixo no mesmo switch (`0x10079728`, índice **`0xD8` (216)**).
3. **Mapeamento Notice ID → String (`0x1023C060`)**:
   - Notice ID **`0x18` (24)** → `0x1023C159`: `mov esi, 0xD8` (`GAME_WAITING`).
   - Notice ID **`0x19` (25)** → `0x1023C160`: `mov esi, 0xD3` (`GAME_GAMESTART`).
4. **Elemento HUD `0x11` (`HUD::CWaitingPlayGame`)**:
   - RTTI: `.?AVCWaitingPlayGame@HUD@@` (base `.?AVIPlayGameHandler@HUD@@`), vtable **`0x104A44AC`**, construtor `0x1018D690`, registrado no HUD manager sob o **ID `0x11`** em `0x1017B686`.
   - `vtable[2]` (`+0x08`) = **`0x1018D980`**: resolve o notice `0x19` (`GAME_GAMESTART`) e envia para Scaleform **`"inGame.guideMessage.status"`** (`0x1018DAAE`).

### Handler cliente `CClientMissionMgr::OnMissionStateMessage` (`0x10087A70`, `MID 0xC4`)
Registrado em `0x100273FC` (vtable `0x10485924`, thunk `0x10027A40 → 0x10087A70`) sobre `g_pClientMissionMgr` (`[0x10527960]`):

```cpp
// GameClient.dll 0x10087A70 (MID 0xC4)
uint8_t state = pMsg->Readuint8();          // 0x10087A81
this->m_eMissionState = state;              // dword [esi + 0x0C] = state
switch (state) {                            // jump table em 0x10087BD8
case 1: // 0x10087A9A (PreWait / Init)
    this->m_bFlag8 = 0;
    break;
case 2: // 0x10087AA5 (Waiting)
    GetHUD(0x10)->Show(0);                  // GAME_WAITING
    break;
case 3: // 0x10087ABC (Ready / GameStart)  <-- ESTADO ATUAL DO SERVIDOR!
    GetHUD(0x10)->Hide(0);
    GetHUD(0x11)->Show(0);                  // EXIBE "Connected. Starting game."!
    break;
case 4: // 0x10087AE3 (InPlay / Playing)   <-- ESTADO QUE LIBERA A PARTIDA!
    this->m_nRound = pMsg->Readuint8();     // byte [esi + 0]
    GetHUD()->OnRoundStart();               // 0x1017C530
    GetHUD(0x11)->Hide(0);                  // OCULTA "Connected. Starting game."!
    this->m_fTimer1 = this->m_fTimer2 = 0;  // +0x38, +0x40, +0x48
    this->OnPlayStart();                    // 0x10087240
    break;
case 5: // 0x10087B28 (RoundEnd / Pause)
case 6: // 0x10087B5B (Intermission)
case 7: // 0x10087B7B (MatchEnd)
    ...
}
```

> [!IMPORTANT]
> **`SetMissionState(3)`** é literalmente o estado `GameStart` que **exibe** `"Connected. Starting game."`. Para ocultar o banner e entrar em jogo ativo, o servidor **precisa avançar para `SetMissionState(4, 1)`** (`GameServer.dll` RVA `0xDEAA0` → case 4 em `0x100DEB97` chama `0x100DE7E0` e faz broadcast de `MID 0xC4` com `state = 4` + `uint8 nRound`).

### Gates que bloqueiam movimento WASD e ações em `GameClient.dll`
1. **`m_eMissionState == 4` (`[g_pClientMissionMgr + 0x0C] == 4`)**:
   - `0x1020A8C5` e `0x1020A926` (`CPlayerBodyMgr` — ações/disparo de arma retornam `false` se `!= 4`).
   - `0x1021F0E3` (`CPlayerMgr` — envio de `MID 0x85` / updates ao servidor aborta se `!= 4`).
   - `0x1021F376` e `0x10037A76` (aborta se `!= 4`).
2. **`CMoveMgr::Update` (`0x10202020`, chamado de `CPlayerMgr::Update` `0x1021DD58`)**:
   - **`0x10202030`**: `if (this->m_hObject == NULL /* +0x0C */ || g_pLTClient->GetClientObject() == NULL) return;` — se o objeto de física local (`m_hObject`) for nulo, todo o pipeline de WASD/física é pulado.
3. **`CMoveMgr::UpdateControlFlags` (`0x101FEB50`, branch normal `0x101FED5E..0x101FEEAC`)**:
   - **`0x101FED98`**: exige **`g_pPlayerMgr->m_ePlayerState == 1`** (`[0x10533B94] + 0x3C == 1`, `ePlayerState_Alive`). Se `!= 1`, pula a leitura de todos os comandos WASD (`0=Forward`, `1=Backward`, `2=StrafeLeft`, `3=StrafeRight`).
   - **`0x101FEB9B`**: bloqueia WASD se `g_pPlayerMgr->m_eCameraMode == 3` (`+0x40`).
   - **`0x101FEBAC`**: bloqueia WASD se HUD `0xB` (`HUD::CInGameChat`) estiver visível.
   - **`0x100964C0`** (`CInputMgr::IsCommandOn`): exige `CInputMgr->m_bEnabled != 0` (`+0x40`).

### Correção importante sobre `MID 0x67` vs `MID 0x60` (tabela `0x100273E0`)
| MID | Handler em `GameClient.dll` | Função real |
| :--- | :--- | :--- |
| **`0x67`** | `0x1021D8F0` (`CPlayerMgr::HandleMsgPlayerStateChange`) | Seta `g_pPlayerMgr->m_ePlayerState` (`+0x3C`): `0=None`, **`1=Alive`**, `2=Dead`, `3=Dying_Start`, `4=Dying_Stage2`, `5=Spectator`. Enviado por `GameServer.dll` `CPlayerObj::ChangeState` (`0x1007B300`, chamado com `(1, 1)` em `Respawn()` `0x1007C441`). |
| **`0x60`** | `0x102163D0 → 0x10216060` | Seta modo de câmera (`m_eCameraMode`, `+0x40`). `0 = FirstPerson`. |
| **`0x7A`** | `0x10215030` | Lê `bool` (1 bit) e grava em `g_pPlayerMgr + 0x1A8` (enviado por `GameServer.dll` `0x100790F0`, `[pPlayer + 0x93A]`). |
| **`0x79`** | `0x101FD630` (`CMoveMgr::HandleMsgTeleport`) | Lê `pos` (`LTVector`), `vel` (`LTVector`), `bool bSetRot`, `rot` (`LTRotation`). |

---

## 2. Causa Raiz de HP = `0`, Sem Arma Viewmodel e Câmera no Nível do Chão

Todos os três sintomas têm a **mesma origem no `GameServer.dll`** (falta de `HRECORD` de avatar e loadout de armas válidos no `NetClientData`):

### A) HP = `0` (`MID 0x66`)
- Em `GameServer.dll`, `CPlayerObj::Respawn()` (`0x1007C41F`) chama `CPlayerObj::ResetHealth` (`0x10077DA0`):
  - `0x10077DAE..0x10077DC9`: passa `CCharacter::m_hModel` (`[edi + 0x100]`) para **`ModelsDB::GetModelMaxHitPoints` (`0x1010BFB0`)**. Quando `m_hModel == NULL`, o valor default retornado é **`0.0f`** (`fldz` em `0x1010BFC7`).
  - `0x10077DD1..0x10077DE7`: passa `m_hModel` para **`ModelsDB::GetModelHitPoints` (`0x1010BF70`)**, que também retorna **`0.0f`** (`fldz` em `0x1010BF87`).
  - `0x10077E2A`: envia **`MID 0x66`** com `subId = 1, fMaxHealth = 0.0f, fHealth = 0.0f`.
- Em `GameClient.dll`:
  - **`MID 0x66`** (`0x10027FE0`) verifica `byte [g_pGameClientShell + 0x15A] != 0`, chama `CPlayerStats::UpdateMaxHealth` (`0x1009A740`, `word [g_pPlayerStats + 0x0C]`) e `CPlayerStats::UpdateHealth` (`0x1009A6F0`, `word [g_pPlayerStats + 0x04]`, **clampado a `m_nMaxHealth`**).
  - O HUD `"inGame.hp.gauge"` (`0x10174BA0..0x10174C26`) lê `word [g_pPlayerStats + 4]` e `word [g_pPlayerStats + 0xC]`, mas só atualiza se `g_pMoveMgr->m_pCharFX` (`[0x105334D4] + 0x20`) `!= NULL`.

### B) Sem arma viewmodel (`MID 0x59`)
- Em `GameServer.dll`, `CPlayerObj::AddDefaultWeapons` (`0x1007BEE0`, chamado em `Respawn()` `0x1007C436`) lê os IDs de arma do loadout em `NetClientData + 0x80 + i*4` (`0x1007BF40`) e consulta `WeaponDB::GetWeaponRecord` (`0x10118BA0`). Com slots zerados, retorna `NULL` e não equipa nenhuma arma (nem envia `MID 0x59` em `0x100E97ED..0x100EA4F4`).
- No cliente, **`MID 0x59`** (`0x10209B50`) encaminha ao `CClientWeaponMgr` (`[g_pPlayerMgr + 0x30] + 0x10`), mas exige `CPlayerBodyMgr::m_hObject != NULL` (`0x10209B67`).

### C) Câmera enterrada no nível do chão (metade inferior mostrando céu)
- Como `CPlayerObj::m_hModel == NULL`, o servidor criou o jogador com o fallback `engine\default.Model00p` (sem dimensões de altura de pé / `PlayerDims` nem sockets de câmera/olhos).
- O `CPlayerCamera::Update` (`0x102145D0 → 0x1020DC70`) posiciona a câmera em 1ª pessoa na cota `Y` do objeto/chão do `GameStartPoint`, sem offset vertical de altura de pé, fazendo o near-plane cortar o chão e expor o skybox na metade inferior da tela.

---

## 3. Desmontagem de `0x101783C0` e Payload Exato de `0x222132` (`SN_ExitButton`)

### Esclarecimento de endereços
- **`0x10178360..0x101783E0`** (que contém `0x101783C0`) é o **emissor** de **`0x222131` (`NPlay_CN_ExitButton`)**:
  - `0x101783A6`: `mov dword ptr [esi + 0x0C], 0x222131` (opcode no header de 16 bytes)
  - `0x101783AD`: `mov word ptr [esi + 0x06], 0x10` (tamanho total = 16 bytes, payload vazio)
  - `0x101783C0`: `call 0x100570D0` (log/debug) → `0x101783DD`: envia pela conexão Matchup.

### Handler receptor real de `0x222132` (`tPacket_NMatchup_NPlay_SN_ExitButton`)
- Registrado em **`0x1013C102`** (`push 0x222132`) com vtable **`0x1049EA10`**.
- Método `OnPacket(tPacket* pkt)` (`vtable[1]`) em **`0x10138BC0`** (`GameClient.dll`):

```asm
0x10138BC0: mov   eax, dword ptr [esp + 4]    ; pkt
0x10138BC4: cmp   word ptr [eax + 0x10], 0    ; payload+0x00 (uint16_t result) == 0 ?
0x10138BC9: jne   0x10138bf5                  ; se != 0, ignora!
0x10138BCB: cmp   dword ptr [eax + 0x12], 0   ; payload+0x02 (uint32_t errorCode) == 0 ?
0x10138BCF: jne   0x10138bf5                  ; se != 0, ignora!
0x10138BD1: mov   eax, dword ptr [0x10516c88] ; g_pLTClient
0x10138BD6: mov   ecx, dword ptr [eax + 0x38] ; g_pLTClient->IsConnected()
0x10138BD9: call  ecx
0x10138BDB: mov   cl, 1
0x10138BDD: cmp   al, cl                      ; IsConnected() == true ?
0x10138BDF: jne   0x10138bf5
0x10138BE1: mov   edx, dword ptr [0x1054a0f8] ; g_pClientConnectionMgr / Shell
0x10138BE7: mov   byte ptr [edx + 0x145], cl  ; marca saída solicitada = 1
0x10138BED: mov   eax, dword ptr [0x10516990] ; g_pInterfaceMgr
0x10138BF2: mov   byte ptr [eax + 0x48], cl   ; fecha "Please wait..." e retorna ao lobby!
0x10138BF5: ret   4
```

- **Payload exato para responder a `0x222131` no `d187-mock-server.py`**:
  - **Opcode:** `0x222132`
  - **Payload (6 bytes):** `struct.pack('<HI', 0, 0)` (`b'\x00\x00\x00\x00\x00\x00'`)
  - **Tamanho total do pacote:** `0x16` (22 bytes = 16 bytes header + 6 bytes payload).

---

## 4. Correções Cirúrgicas Recomendadas

1. **Em `d187_server_host.cpp` (destravar `"Connected. Starting game."`, ações/tiro e updates):**
   - Após o cliente spawnar (ou logo após `SetMissionState(3, 1)`), chamar **`CServerMissionMgr::SetMissionState(4, 1)`** (`RVA 0xDEAA0`) para avançar `m_eMissionState` de `3` (`GameStart`) → **`4` (`InPlay`)**. Isso oculta `HUD 0x11` (`"Connected. Starting game."`) e satisfaz todos os gates `m_eMissionState == 4` em `0x1020A8C5`, `0x1020A926`, `0x1021F0E3`, `0x1021F376`.
2. **Em `d187_server_host.cpp` / `d187-mock-server.py` (corrigir HP=0, câmera no chão e arma viewmodel):**
   - Garantir que `CPlayerObj::m_hModel` (`+0x100`) receba um `HRECORD` válido do `ModelsDB` (em vez de `NULL` / `engine\default.Model00p`) — seja populando o avatar no `NetClientData` enviado pelo mock/lobby ou setando um `HRECORD` padrão de modelo no `CPlayerObj` antes de `Respawn()`. Isso faz `ModelsDB::GetModelMaxHitPoints` / `GetModelHitPoints` retornarem `100.0f` (corrigindo `MID 0x66` e HP=100) e fornece `PlayerDims` / altura de câmera reais.
   - Popular ao menos 1 `WeaponID` válido nos slots de arma do `NetClientData + 0x80..+0x8C` para que `CPlayerObj::AddDefaultWeapons` (`0x1007BEE0`) entregue e equipe a arma em 1ª pessoa via `MID 0x59`.
3. **Em `d187-mock-server.py` (corrigir `ESC → Sair` preso em `"Please wait..."`):**
   - Ao receber `0x222131` (`NPlay_CN_ExitButton`), responder imediatamente com **`0x222132`** e payload **`struct.pack('<HI', 0, 0)`** (6 bytes zerados).

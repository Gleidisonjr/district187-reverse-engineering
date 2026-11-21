# District 187 — Análise de `GameServer.dll`: HP=0, Arma ViewModel, Movimento WASD & `CPlayerObj::Respawn`

Análise estática (somente leitura) de [`GameServer.dll`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/targets/district-187/client-rebirth/Game/GameServer.dll) (`ImageBase = 0x10000000`), [`GameClient.dll`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/targets/district-187/client-rebirth/Game/GameClient.dll) (`ImageBase = 0x10000000`) e [`d187_server_host.cpp`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/targets/district-187/server_host/d187_server_host.cpp) para diagnosticar os 5 sintomas observados ao vivo após o primeiro respawn em `Arrival.World00p`:
- **(a)** Banner `"Connected. Starting game."` travado na tela
- **(b)** Teclas WASD não movem o jogador
- **(c)** HP exibido como `0` no HUD
- **(d)** Nenhuma arma (viewmodel) aparece na mão
- **(e)** Metade inferior da tela corta o chão mostrando o céu (câmera sem altura de pé / `CMoveMgr` travado + `m_hModel == NULL`)

---

## Resumo Executivo (3 Causas Raiz Exatas)

| Sintoma | Causa Raiz Comprovada | Endereço Exato | Correção Cirúrgica |
|---|---|---|---|
| **HP = 0** (+ dims/skeleton nulos) | `CPlayerObj::m_hModel` (`+0x100`) é `NULL` porque `NetClientData` veio com avatar `0`. Em `ResetHealth`, `ModelsDB::GetModelMaxHitPoints(NULL)` e `GetModelHitPoints(NULL)` retornam o default `fldz` (`0.0f`) e enviam `MID 0x66` com `0.0f / 0.0f`. | `GameServer.dll`: `0x10077DA0`, `0x1010BFB0`, `0x1010BF70`, `0x100176B0` | Antes do `Respawn`, escolher um `HRECORD` válido em `g_pModelsDB` (`GetModelHitPoints > 0`) e chamar `CCharacter::SetModel(pPlayer, hModel)` (`RVA 0x176B0`). |
| **Sem arma / viewmodel** | `CPlayerObj::AddDefaultWeapons` lê 4 `HRECORD`s de arma em `pClientData + 0x80..0x8C` (preenchidos por `InWorld_OnMessage @ 0x10033B7B` a partir do loadout do cliente). Como o loadout veio `0`, `GetWeaponData(0)` retorna `NULL` e pula os 4 slots. | `GameServer.dll`: `0x1007BEE0`, `0x10033B8D..0x10033C26`, `0x1011F020` | Antes do `Respawn`, popular `pClientData + 0x80..0x8C` com `HRECORD`s válidos de `g_pWeaponDB->m_hWeaponsCat (+0x24)` (slots 0..3 via `GetWeaponSlot @ RVA 0x11F020`). |
| **WASD travado** + `"Connected. Starting game."` + **chão cortado** | `d187_server_host.cpp:617` chama `SetMissionState(pMissionMgr, 3, 1)`. **Estado `3` NÃO é `PLAYING` — é `PRE_ROUND_FREEZE`!** O estado `3` exibe `HUD 0x11` (`GAME_GAMESTART` = `"Connected. Starting game."`) e bloqueia `CMoveMgr` / `CPlayerMgr` no cliente, que exigem explicitamente `m_eMissionState == 4` (`IN_PLAY`). | `GameServer.dll`: `0x100DEAA0` (`0x100DEB54` vs `0x100DEB97`); `GameClient.dll`: `0x10087A70`, `0x1020A8C5`, `0x1020A926`, `0x1021F0E3`, `0x1021F376` | Chamar `SetMissionState(pMissionMgr, 4, 1)` (`IN_PLAY`), que envia `MID 0xC4` state `4` + byte de round, esconde `HUD 0x11` e desbloqueia WASD, tiro e atualização do `CMoveMgr`. |

---

## 1. Por que o HP ficou `0` (`CPlayerObj::ResetHealth @ 0x10077DA0`)

### Fluxo em `CPlayerObj::Respawn` (`0x1007C350`)
Em `0x1007C412..0x1007C41F`, `Respawn()` chama `ResetHealth`:
```asm
0x1007C412: fld   dword ptr [esi + 0x7c4]   ; m_fHealthMultiplier (inicializado como 1.0f em 0x1007AB5D e 0x1007BE6C)
0x1007C418: push  ecx
0x1007C419: fstp  dword ptr [esp]           ; float fMultiplier = 1.0f
0x1007C41C: push  edi                       ; bool bMaxOnly = false (0)
0x1007C41D: mov   ecx, esi
0x1007C41F: call  0x10077da0                ; CPlayerObj::ResetHealth(false, 1.0f)
```

### Disassembly de `CPlayerObj::ResetHealth` (`0x10077DA0`)
```asm
0x10077DAE: mov   eax, dword ptr [edi + 0x100]  ; CCharacter::m_hModel (HRECORD em ModelsDB)
0x10077DB4: mov   ecx, dword ptr [0x101f2a18]   ; g_pModelsDB
0x10077DBA: push  eax
0x10077DBB: call  0x1010bfb0                    ; ModelsDB::GetModelMaxHitPoints(m_hModel)
0x10077DC0: fmul  qword ptr [esp + 4]           ; * fMultiplier
0x10077DC9: fstp  dword ptr [edi + 0x43c]       ; m_damage.m_fMaxHitPoints (+0x43C)
...
0x10077DD1: mov   eax, dword ptr [edi + 0x100]  ; CCharacter::m_hModel
0x10077DD7: mov   ecx, dword ptr [0x101f2a18]   ; g_pModelsDB
0x10077DDD: push  eax
0x10077DDE: call  0x1010bf70                    ; ModelsDB::GetModelHitPoints(m_hModel)
0x10077DE3: fmul  qword ptr [esp + 4]           ; * fMultiplier
0x10077DE7: fstp  dword ptr [edi + 0x440]       ; m_damage.m_fHitPoints (+0x440)
```
Em `ModelsDB::GetModelMaxHitPoints` (`0x1010BFB0`) e `ModelsDB::GetModelHitPoints` (`0x1010BF70`):
- Ambas buscam os atributos `"MaxHitPoints"` / `"HitPoints"` em `g_pLTDatabase` (`[0x101F2A00]`) com valor default **`fldz` (`0.0f`)**.
- Como `CPlayerObj::PreCreate` (`0x1007B85B..0x1007B869`) chamou `ClientData::GetBaseModel()` (`0x1004D020`), que leu `0` em `NetClientData + 0x6C + teamIdx * 0x48` e retornou `NULL`, `CCharacter::SetModel(NULL)` (`0x100176B0`, vtable `+0xA4`) gravou:
  - **`CPlayerObj + 0x100` (`m_hModel`) = `NULL`**
  - **`CPlayerObj + 0x104` (`m_hModelSkeleton`) = `NULL`**
- Com `m_hModel == NULL`, ambas as funções retornam **`0.0f`**, gravando `0.0f` em `+0x43C` (`m_fMaxHitPoints`) e `+0x440` (`m_fHitPoints`).

### Qual `MID_*` envia o HP ao cliente
Logo em seguida (`0x10077DFA..0x10077EC6`), `ResetHealth` envia ao cliente `m_hClient` (`CPlayerObj + 0x7D8`):
- **`MID 0x66` (`MID_PLAYER_INFOCHANGE`)** — recebido em `GameClient.dll @ 0x10027FE0`:
  - `uint8`: `0x66`
  - `uint8`: `1` (`IC_HEALTH_ID`)
  - `float32` (`0x20` bits): `CDestructible::GetMaxHitPoints()` (`0x1003DC40` sobre `this + 0x3C4`, lê `[ecx + 0x78]` = `CPlayerObj + 0x43C`)
  - `float32` (`0x20` bits): `m_fHitPoints` (`CPlayerObj + 0x440`)

---

## 2. Por que nenhuma arma apareceu na mão (`CPlayerObj::AddDefaultWeapons @ 0x1007BEE0`)

### Fluxo em `CPlayerObj::AddDefaultWeapons` (`0x1007BEE0`)
Chamada em `CPlayerObj::Respawn` (`0x1007C436`):
1. `0x1007BEF0..0x1007BEFC`: obtém `pClientData = ClientDataMgr::Instance()->GetClientData(m_hClient)` (`0x10033470` → `0x10095D90`).
2. `0x1007BF0A..0x1007BF34`: copia 4 `HRECORD`s de mods/acessórios de `pClientData + 0x90..0x9C` para `CPlayerObj + 0x838..0x844`.
3. `0x1007BF3A..0x1007C007`: loop `ebx = 0..3` (4 slots: `0=Primary`, `1=Secondary`, `2=Melee`, `3=Grenade`):
   ```asm
   0x1007BF40: mov  ebp, dword ptr [edi + ebx*4 + 0x80]  ; HWEAPON do slot ebx (pClientData + 0x80..0x8C)
   0x1007BF47: mov  ecx, dword ptr [0x101f2e78]          ; g_pWeaponDB
   0x1007BF4D: push 0
   0x1007BF4F: push ebp
   0x1007BF50: call 0x10118ba0                           ; WeaponDB::GetWeaponData(hWeapon, false)
   0x1007BF55: test eax, eax
   0x1007BF57: je   0x1007c003                           ; SE hWeapon == NULL -> PULA O SLOT!
   ```
   Quando `hWeapon != NULL`, lê `"AmmoName"` → `"MaxClipInAmount"`, chama `CArsenal::AddAmmo` (`0x100EAEE0` em `this + 0x4F8`) e `CWeaponInventory::AddWeapon` (`0x10074F80` em `this + 0x7C8`).
4. `0x1007C05E..0x1007C072`: consulta o slot `0` (`0x10074EC0(0)`) e equipa a arma ativa via `CArsenal::ChangeWeapon` (`0x100E9990`).

### Origem de `pClientData + 0x80..0x8C`
Em **`InWorld_OnMessage` (`GameServer.dll @ 0x10033B7B..0x10033C5E`)**:
- Ao receber `MID 0xED` state `11` (`InWorld`) do cliente, o servidor lê 4 `HRECORD`s de arma via `ReadDatabaseRecord(g_pLTDatabase, g_pWeaponDB->m_hWeaponsCat [+0x24])` (`0x10033BA9..0x10033BC0`) e os grava em **`pClientData + 0x80, +0x84, +0x88, +0x8C`** (`0x10033C17`), ignorando a checagem de RoomServer quando `m_bStandalone (+0x6C) != 0` (`0x10033BF5`).
- Em seguida lê 4 mods (`g_pWeaponDB + 0x40..0x4C`) e grava em `pClientData + 0x90..0x9C` via `0x1004CE40`.
- **Causa**: o cliente entrou no servidor sem armas equipadas no inventário/loadout do lobby → enviou `NULL` nos 4 slots → `pClientData + 0x80..0x8C` ficaram zerados → `AddDefaultWeapons` pulou todos os 4 slots → jogador spawnou desarmado (sem viewmodel).

---

## 3. Por que WASD não anda, `"Connected. Starting game."` fica na tela e o chão corta

### Tabela real de `CServerMissionMgr::m_eMissionState` (`+0x58` no servidor / `+0x0C` no cliente)
Confirmada pela jump table de `CServerMissionMgr::SetMissionState` (`GameServer.dll @ 0x100DEAA0`, tabela `0x100DEC64`) e pelo handler de **`MID 0xC4`** em `GameClient.dll @ 0x10087A70` (tabela `0x10087BD8`):

| Estado | `GameServer.dll` (`0x100DEAA0` / `MID 0xC4 @ 0x100DE850`) | `GameClient.dll` (`0x10087A70`) | Significado Real |
|---:|---|---|---|
| `0` | Init (`0x100DF4E0`) | — | Não inicializado |
| `1` | `0x100DEAD2` | `0x10087A9A` (`[esi+8]=0`) | `WAITING` (aguardando jogadores) |
| `2` | `0x100DEAED` (timer `GameModeMgr+0x9C`) | `0x10087AA5` (`HUD::Show(0x10)`) | `WARMUP / READY` |
| **`3`** | **`0x100DEB54` (timer `GameModeMgr+0xAC`)** | **`0x10087ABC` (`HUD::Hide(0x10)`, `HUD::Show(0x11)`)** | **`PRE_ROUND_FREEZE` — exibe `GAME_GAMESTART` (`"Connected. Starting game."`), TRAVA WASD e tiro!** |
| **`4`** | **`0x100DEB97` → `0x100DE7E0` (incrementa round `+0x10`, envia `uint8 round` no `MID 0xC4`)** | **`0x10087AE3` (`HUD::OnRoundStart`, `HUD::Hide(0x11)`, `OnPlayStart 0x10087240`)** | **`IN_PLAY` — esconde banner e DESBLOQUEIA WASD, física e tiro!** |
| `5` | `0x100DEBC9` (envia 1 bit `[+0x54]` no `MID 0xC4`) | `0x10087B28` | `ROUND_END` |
| `6` | `0x100DEC17` (timers `+0x128`/`+0x178`) | `0x10087B5B` | `MATCH_END` |

### Gates exatos de WASD e tiro em `GameClient.dll`
No cliente, `CMoveMgr` e `CPlayerMgr` bloqueiam movimento e disparo se `g_pMissionMgr->m_eMissionState` (`[0x10527960] + 0x0C`) for diferente de **`4`**:
- `0x1020A8C5`: `cmp dword ptr [eax + 0xc], 4` (`CMoveMgr::UpdateControlFlags`)
- `0x1020A926`: `cmp dword ptr [eax + 0xc], 4` (`CMoveMgr::UpdateMotion` — WASD + atualização da cápsula/altura!)
- `0x1021F0E3`: `cmp dword ptr [eax + 0xc], 4` (`CPlayerMgr` — arma/disparo)
- `0x1021F376`: `cmp dword ptr [eax + 0xc], 4` (`CPlayerMgr` — input de combate)

A string `"Connected. Starting game."` vem da chave **`GAME_GAMESTART`** (`TheRaw.Strdb00p` / `english.Strdb00e`, referenciada em `GameClient.dll @ 0x100796C4`), que é exibida pelo `HUD 0x11` no estado `3` (`0x10087AD0`) e ocultada exatamente quando chega `MID 0xC4` com estado **`4`** (`0x10087B00`).

Além disso, como `CMoveMgr::UpdateMotion` (`0x1020A926`) retornava imediatamente no estado `3` (e `CPlayerObj` estava sem `m_hModel`), a cápsula de física/altura de olho nunca era aplicada sobre o `Teleport` (`MID 0x79 @ 0x100781B0`), deixando a câmera colada na altura crua do chão (metade inferior cortando a geometria e revelando o skybox).

---

## 4. Correção Cirúrgica Recomendada em `d187_server_host.cpp`

Em [`d187_server_host.cpp`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/targets/district-187/server_host/d187_server_host.cpp#L609-L625), no bloco `if (g_RespawnDelayTicks == 0)`, substituir a chamada `SetMissionState(pMissionMgr, 3, 1)` por:
1. Popular `CPlayerObj::m_hModel` (`+0x100`) + `m_hModelSkeleton` (`+0x104`) via `CCharacter::SetModel` (`RVA 0x176B0`) com o primeiro modelo de `g_pModelsDB` que tenha `GetModelHitPoints(hModel) > 0.0f` (corrige **HP = 100** via `MID 0x66` + skeleton/dims);
2. Popular `pClientData + 0x80..0x8C` (slots `0..3`: Primary, Secondary, Melee, Grenade) com `HRECORD`s válidos de `g_pWeaponDB->m_hWeaponsCat (+0x24)` classificados por `WeaponDB::GetWeaponSlot` (`RVA 0x11F020`) (corrige **arma viewmodel na mão** via `AddDefaultWeapons`);
3. Disparar o respawn nativo (`pPlr[0x934] = 1; pPlr[0x935] = 1;`);
4. Avançar a missão para o estado **`4` (`IN_PLAY`)** via `CServerMissionMgr::SetMissionState(pMissionMgr, 4, 1)` (`RVA 0xDEAA0`) (esconde `"Connected. Starting game."` e **desbloqueia WASD, tiro e `CMoveMgr`**).

### Endereços exatos usados (todos verificados em `GameServer.dll`, `ImageBase = 0x10000000`)
- `g_pLTDatabase`: `RVA 0x1F2A00` (`vtbl+0x3C = GetNumRecords(hCat)`, `vtbl+0x40 = GetRecordByIndex(hCat, idx)`)
- `g_pModelsDB`: `RVA 0x1F2A18` (`+0x24 = m_hModelsCat`, `RVA 0x10B9D0 = GetNumModels`, `RVA 0x10B9F0 = GetModel`, `RVA 0x10BF70 = GetModelHitPoints`)
- `g_pWeaponDB`: `RVA 0x1F2E78` (`+0x24 = m_hWeaponsCat`, `RVA 0x11F020 = GetWeaponSlot(hWeapon)`)
- `ClientDataMgr::Instance`: `RVA 0x33470`, `ClientDataMgr::GetClientData(hClient)`: `RVA 0x95D90` (`hClient = *(void**)(pPlr + 0x7D8)`, weapons em `pClientData + 0x80..0x8C`)
- `CCharacter::SetModel(HRECORD hModel)`: `RVA 0x176B0` (`CPlayerObj::vtbl + 0xA4`)
- `g_pServerMissionMgr`: `RVA 0x1F1D80`, `CServerMissionMgr::SetMissionState(uint32_t eState, uint8_t bForce)`: `RVA 0xDEAA0`

### Snippet C++ pronto para `d187_server_host.cpp` (linhas 611–624)
```cpp
if (g_RespawnDelayTicks == 0) {
    uint8_t* pPlr = (uint8_t*)g_LastPlayerObj;
    if (hGS) {
        void* pLTDB = *(void**)((uint8_t*)hGS + 0x1F2A00);
        void* pModelsDB = *(void**)((uint8_t*)hGS + 0x1F2A18);
        void* pWeaponDB = *(void**)((uint8_t*)hGS + 0x1F2E78);

        // 1. Garantir m_hModel (+0x100) válido -> corrige HP=0 (ResetHealth / MID 0x66) e skeleton/dims
        if (pModelsDB && *(void**)(pPlr + 0x100) == nullptr) {
            typedef uint32_t (__thiscall* GetNumModelsFn)(void*);
            typedef void*    (__thiscall* GetModelFn)(void*, uint32_t);
            typedef float    (__thiscall* GetModelHPFn)(void*, void*);
            typedef void     (__thiscall* SetModelFn)(void*, void*);

            auto pGetNumModels = (GetNumModelsFn)((uint8_t*)hGS + 0x10B9D0);
            auto pGetModel     = (GetModelFn)((uint8_t*)hGS + 0x10B9F0);
            auto pGetModelHP   = (GetModelHPFn)((uint8_t*)hGS + 0x10BF70);
            auto pSetModel     = (SetModelFn)((uint8_t*)hGS + 0x176B0);

            uint32_t nModels = pGetNumModels(pModelsDB);
            for (uint32_t i = 0; i < nModels; ++i) {
                void* hMdl = pGetModel(pModelsDB, i);
                if (hMdl && pGetModelHP(pModelsDB, hMdl) >= 50.0f) {
                    pSetModel(pPlr, hMdl);
                    LogLine("[+] Assigned fallback m_hModel=%p (idx=%u, HP=%.1f)\n",
                            hMdl, i, pGetModelHP(pModelsDB, hMdl));
                    break;
                }
            }
        }

        // 2. Popular pClientData + 0x80..0x8C (slots 0..3) se vazios -> corrige arma viewmodel em AddDefaultWeapons
        void* hClient = *(void**)(pPlr + 0x7D8);
        if (hClient && pLTDB && pWeaponDB) {
            typedef void* (__cdecl* GetClientDataMgrFn)();
            typedef void* (__thiscall* GetClientDataFn)(void*, void*);
            auto pCDM = ((GetClientDataMgrFn)((uint8_t*)hGS + 0x33470))();
            uint8_t* pCD = pCDM ? (uint8_t*)((GetClientDataFn)((uint8_t*)hGS + 0x95D90))(pCDM, hClient) : nullptr;
            if (pCD) {
                void** pSlots = (void**)(pCD + 0x80);
                if (!pSlots[0] && !pSlots[1] && !pSlots[2]) {
                    void* hWeaponsCat = *(void**)((uint8_t*)pWeaponDB + 0x24);
                    void** dbVtbl = *(void***)pLTDB;
                    typedef uint32_t (__thiscall* GetNumRecsFn)(void*, void*);
                    typedef void*    (__thiscall* GetRecByIdxFn)(void*, void*, uint32_t);
                    typedef uint32_t (__thiscall* GetWpnSlotFn)(void*, void*);
                    typedef void*    (__thiscall* GetWpnDataFn)(void*, void*, uint8_t);

                    auto pGetNumRecs = (GetNumRecsFn)dbVtbl[0x3C / 4];
                    auto pGetRecIdx  = (GetRecByIdxFn)dbVtbl[0x40 / 4];
                    auto pGetWpnSlot = (GetWpnSlotFn)((uint8_t*)hGS + 0x11F020);
                    auto pGetWpnData = (GetWpnDataFn)((uint8_t*)hGS + 0x118BA0);

                    uint32_t nWpns = pGetNumRecs(pLTDB, hWeaponsCat);
                    for (uint32_t i = 0; i < nWpns; ++i) {
                        void* hWpn = pGetRecIdx(pLTDB, hWeaponsCat, i);
                        if (!hWpn || !pGetWpnData(pWeaponDB, hWpn, 0)) continue;
                        uint32_t slot = pGetWpnSlot(pWeaponDB, hWpn);
                        if (slot < 4 && pSlots[slot] == nullptr) {
                            pSlots[slot] = hWpn;
                        }
                        if (pSlots[0] && pSlots[1] && pSlots[2] && pSlots[3]) break;
                    }
                    LogLine("[+] Populated fallback loadout slots: [0]=%p [1]=%p [2]=%p [3]=%p\n",
                            pSlots[0], pSlots[1], pSlots[2], pSlots[3]);
                }
            }
        }

        // 3. Avançar missão para estado 4 (IN_PLAY) -> oculta "Connected. Starting game." e libera WASD/tiro!
        void* pMissionMgr = *(void**)((uint8_t*)hGS + 0x1F1D80);
        if (pMissionMgr) {
            typedef void (__thiscall* SetMissionStateFn)(void*, uint32_t, uint8_t);
            auto pSetMissionState = (SetMissionStateFn)((uint8_t*)hGS + 0xDEAA0);
            pSetMissionState(pMissionMgr, 4, 1);
        }
    }

    // 4. Disparar CPlayerObj::Respawn() nativo (ResetHealth + AddDefaultWeapons + MID 0x67 + Teleport)
    pPlr[0x934] = 1; // m_bClientLoaded = true
    pPlr[0x935] = 1; // m_bReadyToRespawn = true
    LogLine("[+] Triggered SetMissionState(4 [IN_PLAY]) + native CPlayerObj::Respawn() on %p\n", g_LastPlayerObj);
}
```

> [!NOTE]
> Como `GameServerNetMgr::m_bStandalone` (`+0x6C`) já está setado como `1` em `d187_server_host.cpp:538`, o estado `4` (`IN_PLAY`) não bloqueia futuros respawns via `MID 0x69` (`0x1004FE82`).

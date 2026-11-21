# District 187 — `GameServer.dll` Player Spawn, `m_sCurLevel` e Estado da Partida

Análise estática (read-only) de [`GameServer.dll`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/targets/district-187/client-rebirth/Game/GameServer.dll) (`ImageBase = 0x10000000`) e [`d187_server_host.cpp`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/targets/district-187/server_host/d187_server_host.cpp) para diagnosticar:
1. Por que o cliente exibe `"Missing LoadingImage String"` e fica em tela preta após entrar no mundo;
2. Por que `CPlayerObj` (`objId=39`) recebeu `engine\default.Model00p`;
3. Quais campos de `ServerGameOptions` são realmente lidos por `GameServer.dll`;
4. Qual a sequência de `MID_*` e estados internos necessários para o jogador spawnar vivo (`PS_ALIVE`) com câmera 3D ativa.

---

## 1. Causa Raiz do `"Missing LoadingImage String"` (`m_sCurLevel` vazio no `MID 0xED` state `3`)

### Qual função envia o nome do mundo para `SetCurrentWorld` (`GameClient.dll` `0x100237CD`)
Em `GameClient.dll` (`0x10023750..0x100237D0`), o handler de `MID_CLIENTCONNECTION` (`0xED`) sub-estado `3` (`eClientConnectionState_Hello`) lê, nesta ordem:
1. Versão do protocolo (`word [0x104C1500]`)
2. `HRECORD` de `GameMode` (`0x103FBFB0`) + dados de `GameModeMgr` (`0x103FDD30`)
3. String do mundo (`ILTMessage_Read::ReadString(buf, 0x208)` em `0x100237BE`) → passa diretamente para `SetCurrentWorld(buf)` (`0x100237CD: call 0x100880B0`).

No lado do servidor, o emissor exato é **`eClientConnectionState_Hello` em `GameServer.dll` `0x100349A0..0x10034A82`** (`RVA 0x349A0`):
- `0x100349B0`: grava `MID 0xED` (8 bits) e estado `3` (8 bits) (`"eClientConnectionState_Hello"`).
- `0x100349F7..0x10034A1B`: grava `GameModeMgr::Instance()->m_hGameModeRecord` (`+0x25C`) e chama `GameModeMgr::WriteToMsg` (`0x1012A370`).
- `0x10034A20..0x10034A33`: chama **`CGameServerShell::GetCurLevel()` (`0x100525B0`, RVA `0x525B0`)** sobre `g_pGameServerShell` (`[0x101E57AC]`) e grava o ponteiro retornado com `ILTMessage_Write::WriteString` (`[esi]+0x38`).

### O que `GetCurLevel()` envia hoje (e por quê)
`CGameServerShell::GetCurLevel()` (`0x100525B0`) retorna `m_sCurLevel.c_str()`, armazenada como `std::string` (VC10 SSO) em **`CGameServerShell + 0xA8F8`**:
- Em `CGameServerShell::OnServerInitialized` (`0x100568C9..0x100568EA`), `m_sCurLevel` é explicitamente zerada para `""`.
- O único setter da string na DLL inteira é **`CGameServerShell::SetCurLevel(const char*)` (`0x10055D80`, RVA `0x55D80`)**, que tem **apenas 1 caller**: `CServerSaveLoadMgr::LoadNewLevel` (`0x1006A3BF`), chamada via `ServerMsg 2` (`0x10055B97` → `CServerMissionMgr::OnMessage(0xB9)` → `0x100DE9E0` → `0x1006A430` → `0x1006A330`).
- Como `d187_server_host.cpp` chama `pServer->StartWorld(&req)` diretamente na `Engine_Server.dll` sem passar por `CServerSaveLoadMgr::LoadNewLevel` (nem chamar `SetCurLevel`), **`m_sCurLevel` permanece `""` durante toda a execução**.
- Consequência: `eClientConnectionState_Hello` envia `""` → `GameClient.dll` chama `SetCurrentWorld("")` → lookup de `Mission/Level` no `TheRaw.Gamdb00p` falha → loga `"Missing LoadingImage String"` e não inicializa o contexto visual/HUD do mapa.

---

## 2. Por que `CPlayerObj` (`objId=39`) ficou com `engine\default.Model00p` e Estado de Spawn

### A) Origem do `engine\default.Model00p`
1. `CGameServerShell::CreatePlayer` (`0x100549A0`) instancia `"CPlayerObj"` via `ILTServer::CreateObject`.
2. Durante `MID_PRECREATE`, `CCharacter::EngineMessageFn` (`0x10084B70`, branch `0x10084BA7..0x10084BD8`) preenche o fallback `"engine\Default.Model00p"` (`0x10195DC4`) no `ObjectCreateStruct`.
3. Em seguida, **`CPlayerObj::PreCreate` (`0x1007B800`, chamado de `0x1007C2C8`)**:
   - `0x1007B85B`: chama **`ClientData::GetBaseModel()` (`0x1004D020`)**, que lê o `NetClientData` (`0xD8` bytes) enviado pelo cliente via `g_pLTServer->GetClientData` (`[ecx]+0x1C8`), calcula `teamIdx = CTeamMgr::GetTeamIndex(ncd + 0x38)` (`0x10110750`), lê o `HRECORD` do avatar do time em **`ncd + 0x6C + teamIdx * 0x48`** (`0x1004D091`) e busca o atributo `"BaseModel"` (`0x10074D50`).
   - `0x1007B869`: chama `CCharacter::SetModel(hModel)` (`vtable+0xA4`, salva em `this + 0x100`).
   - `0x1007B878`: chama `ModelsDB::GetModelFilename(hModel)` (`0x1010C1E0`, atributo `"ModelFile"`, default `""` em `0x1018CF97`).
   - `0x1007B880`: chama `ObjectCreateStruct::SetFileName(pszModel)` (`0x1000EC60`).
4. **Causa**: o cliente entrou com `HRECORD == 0` no slot de personagem do `NetClientData` (avatar não preenchido no lobby/mock) → `GetBaseModel()` retornou `NULL` → `GetModelFilename(NULL)` retornou `""` → `Engine_Server.dll` substituiu filename vazio pelo fallback interno `engine\default.Model00p`.

### B) Estado do Jogador (`PS_ALIVE` vs bloqueio de RoomServer TCP)
O spawn real acontece em **`CPlayerObj::Respawn()` (`0x1007C350`, vtable `0x101950DC` offset `+0x7C` / slot 31)**, que:
- Chama `CPlayerObj::AddDefaultWeapons` (`0x1007BEE0` em `0x1007C436`) — único lugar onde `AddDefaultWeapons` é chamada (o que explica a criação de `objId=40` `MAR_XM177EX_Lod.Model00p` quando `Respawn` executa);
- Seta `m_eState` (`CPlayerObj + 0x7BC`) para **`0` (`PS_ALIVE`)** (`0x1007C483`);
- Envia **`MID 0x60` (`MID_PLAYER_STATE_CHANGE`) com `uint8(0)` (`PS_ALIVE`)** ao cliente (`0x1007C4B9..0x1007C51E`);
- Chama `CPlayerObj::Teleport` (`0x10079260` em `0x1007C54F`) para mover ao ponto de spawn.

**Condição de disparo em `CPlayerObj::Update` (`0x1007B930`)**:
```cpp
// 0x1007B96A .. 0x1007B985
if (pPlayer->m_bClientLoaded == 1 /* +0x934 */ && pPlayer->m_bReadyToRespawn == 1 /* +0x935 */) {
    pPlayer->Respawn(); // vtable + 0x7C (0x1007C350)
    pPlayer->m_bReadyToRespawn = 0;
}
```
Quem seta `+0x934` e `+0x935` é o handler de **`MID 0x69` (`0x1004FE40`, despachado em `0x10054EE2`)**:
- `0x1004FE7B`: seta `pPlayer->+0x934 = 1`.
- `0x1004FE82`: verifica **`GameServerNetMgr::Instance()->m_bStandalone` (`[0x101E4078 + 0x6C]`) == 1**.
  - Se `1`: pula direto para `0x1004FED0` e seta `pPlayer->+0x935 = 1` (**respawn imediato**).
  - Se `0` (valor padrão atual!): verifica `g_pServerMissionMgr->m_eMissionState` (`[0x101F1D80 + 0x58]`):
    - Se `m_eMissionState ∈ {1, 2, 3}`: pula para `0x1004FED0` e seta `+0x935 = 1`.
    - Se `m_eMissionState == 0` (valor inicial em `CServerMissionMgr::Init` `0x100DF4E0`!) ou `4` (`InPlay`): chama `0x100DE230(pPlayer, flag)`, que tenta enviar o pacote **TCP `0x230103`** para o Matchup/RoomServer (`0x100E4700`) e **NÃO seta `+0x935 = 1`**!
- O mesmo gate existe no respawn pós-morte (`0x1007711E..0x10077139`): se `m_bStandalone == 0`, tenta pedir respawn via TCP `0x230103` em vez de setar `+0x935 = 1` localmente.

---

## 3. Campos Exatos de `ServerGameOptions` Lidos por `GameServer.dll`

Layout completo confirmado por `ServerGameOptions::operator=` (`0x10055720`, tamanho total `0xB0` bytes, copiado para `CGameServerShell + 0x30` em `OnServerInitialized` `0x100568BB`):

| Offset | Tipo | Uso em `GameServer.dll` |
| :--- | :--- | :--- |
| `+0x00` | `std::string` (`s[0]`) | Não lido no caminho de boot standalone |
| `+0x1C` | `std::string` (`s[1]`) | Não lido no caminho de boot standalone |
| `+0x38` | `std::string` (`s[2]`) | Checado em `0x10056A5F` (`.size` em `+0x48`): se vazio, usa `+0xAA` para escolher `GameMode%d` padrão no GDB |
| `+0x54` | `std::string` (`s[3]`) | Não lido no caminho de boot standalone |
| `+0x70` | `std::string` (`s[4]`) | Não lido no caminho de boot standalone |
| `+0x8C` | `std::string` (`s[5]`) | Checado em `0x1005693A` (`.size` em `+0x9C`): arquivo de customizações MP (default `"MPCustomizations.txt"`) |
| `+0xA8` | `uint8_t` | `m_bUseFixedRandomSeed` (`0x10056BC4`): `1` → `srand(123)`, `0` → `srand(time(0))` |
| `+0xA9` | `uint8_t` | `m_bUpdateMasterServer` (`0x10054989`, `0x100570C9`): se `1` e cliente entrou (`+0x2C`), chama `0x10053DD0` |
| `+0xAA` | `uint8_t` | `m_nDefaultGameModeIndex` (`0x10056A64`): índice passado a `0x10170E80` → seleciona `GameMode0..7` |
| `+0xAC` | `uint32_t` | `m_eInitStatus` (saída escrita por `OnServerInitialized`: `0` OK, `1` em `0x10056C64`, `2` falha `GetTcpIpAddress` em `0x10056C29`) |

**Conclusão importante:** `ServerGameOptions` **não** contém mapa, tempo de partida, limite de kills nem lista de usuários. Esses parâmetros vêm de `CGameServerShell::OnServerMessage` (`0x100557C0`, opcodes `0..9` recebidos via `ServerInterface::SendToServerShell`) e de `CServerMissionMgr::Reset(SN_BaseRoomInfo*)` (`0x100DDDB0`).

---

## 4. `MID 0x57` (`0x100E2FC0`) e Sequência de `MID_*` para Spawn Vivo + Câmera 3D

### O que `MID 0x57` (`0x100E2FC0`) envia
Chamada em `eClientConnectionState_InWorld` (`0x100347A4`) sobre `g_pGameServerShell->GetMissionMgr(0)` (`0x100545D0(0)`):
- Só transmite se `byte [pMissionMgr + 0x1D0] != 0` (objetivo/timer de missão ativo).
- Payload (broadcast confiável, `hClient = NULL`):
  - `uint8`: `0x57`
  - `uint8`: `0x0F` (sub-ID de sincronização de objetivo)
  - `1 bit`: `byte [pMissionMgr + 0x1D8] != 0`
  - `uint16`: `word [pMissionMgr + 0x1D4]`
  - `uint16`: `0xFFFF`
- Não bloqueia câmera nem spawn.

### Sequência mínima de `MID_*` que o cliente precisa receber do servidor
1. **`MID 0xED` state `3` (`eClientConnectionState_Hello`, `0x100349A0`)**: versão + `GameMode` + **`m_sCurLevel` não-vazia** → cliente executa `SetCurrentWorld` (`0x100237CD`) com sucesso e carrega `LoadingImage` / metadados do mapa.
2. **`MID 0xC4` (`0x100DE850`, chamado em `0x10034A94`)**: estado da missão (`m_eMissionState` em `g_pServerMissionMgr + 0x58`).
3. **`MID 0xCA` (`0x10034AA2..0x10034DF8`)**: dados de slot/ID do cliente.
4. **`MID 0xED` state `8` (`LoggedIn`, `0x10034300`) → state `9` (`Loading`, `0x100344C0`)** + `MID 0x8C` (`0x100345B8`) + `MID 0x8E` (`0x10057100`).
5. **`MID 0xED` state `11` (`InWorld`, `0x100346B0`)**: `uint8(g_pServerMissionMgr + 0x0C)`.
6. Cliente envia **`MID 0x69`** (`0x1004FE40`) → com `m_bStandalone = 1`, servidor marca `+0x934 = 1` e `+0x935 = 1`.
7. **`CPlayerObj::Respawn()` (`0x1007C350`)** dispara no próximo tick de `Update()`:
   - Envia **`MID 0x60` (`MID_PLAYER_STATE_CHANGE`) = `0` (`PS_ALIVE`)** (`0x1007C4B9`) → **ativa a câmera 3D e os controles do jogador**;
   - Executa `Teleport` (`0x10079260`) + sincroniza `CPlayerObj` (`MID 0x6D`, `MID 0xE6`) e armas (`0x1007BEE0`).

---

## 5. Correção Cirúrgica Recomendada em `d187_server_host.cpp`

Logo após `LoadBinaries()` (`d187_server_host.cpp` linha 448) e antes/depois de `StartWorld(&req)` (linha 467), aplicar **3 chamadas cirúrgicas** em `GameServer.dll` (sem precisar modificar `GameServer.dll` em disco):

```cpp
// 1. Ativar modo standalone em GameServerNetMgr::Instance()->m_bStandalone (+0x6C)
//    Evita que MID 0x69 (0x1004FE40) e Respawn (0x10077123) bloqueiem aguardando TCP 0x230103 do RoomServer.
typedef void* (__cdecl* GetNetMgrFn)();
auto pGetNetMgr = (GetNetMgrFn)((uint8_t*)hGS + 0x334D0);
uint8_t* pNetMgr = (uint8_t*)pGetNetMgr();
if (pNetMgr) {
    pNetMgr[0x6C] = 1; // GameServerNetMgr::m_bStandalone = true
}

// 2. Popular CGameServerShell::m_sCurLevel (+0xA8F8) ANTES de StartWorld(&req)
//    Assim OnWorldLoaded (0x10054820) e eClientConnectionState_Hello (0x10034A26)
//    enviam o nome real do mapa em vez de "" (corrige "Missing LoadingImage String" em SetCurrentWorld).
typedef void (__thiscall* SetCurLevelFn)(void* pShell, const char* pszLevel);
void* pShell = *(void**)((uint8_t*)hGS + 0x1E57AC); // g_pGameServerShell
auto pSetCurLevel = (SetCurLevelFn)((uint8_t*)hGS + 0x55D80);
if (pShell) {
    pSetCurLevel(pShell, worldName); // ex: "Worlds\\Arrival.World00p"
}

// 3. Após StartWorld(&req), avançar CServerMissionMgr::m_eMissionState (+0x58) de 0 -> 1 (PrePlay/Ready)
//    via CServerMissionMgr::SetMissionState(1, true) (RVA 0xDEAA0) para que MID 0xC4 informe estado válido.
typedef void (__thiscall* SetMissionStateFn)(void* pMissionMgr, uint32_t eState, uint8_t bForce);
void* pMissionMgr = *(void**)((uint8_t*)hGS + 0x1F1D80); // g_pServerMissionMgr
auto pSetMissionState = (SetMissionStateFn)((uint8_t*)hGS + 0xDEAA0);
if (pMissionMgr) {
    pSetMissionState(pMissionMgr, 1, 1);
}
```

> [!TIP]
> **Opcional (modelo de personagem real em vez de `engine\default.Model00p`):** No `d187-mock-server.py`, preencher um `HRECORD`/ID de avatar válido nos dados de personagem enviados ao cliente no lobby fará o cliente popular `NetClientData + 0x6C + teamIdx * 0x48` com um record não-nulo, fazendo `ClientData::GetBaseModel()` (`0x1004D020`) resolver o `.Model00p` real do operador. Isso é cosmético para a câmera em 1ª pessoa, mas corrige o `objId=39` em 3ª pessoa/sombras.

# District 187 — Análise Estática da Entrada 3D (`TheRaw.exe` ↔ `TheRawServer.exe`) e `OnEnterWorld`

- **Data:** 2026-11-19
- **Escopo:** Engenharia reversa estática somente-leitura (`pefile` + `capstone`) sobre `targets/district-187/client-rebirth/` (`TheRaw.exe`, `GameClient.dll`, `Engine_Server.dll`, `Game\GameServer.dll`), auditoria do `git diff` atual de `scripts/d187-mock-server.py` e `targets/district-187/server_host/d187_server_host.cpp`, e análise de `targets/district-187/traffic/server_host.log` e `disconnect_trace.log`.

---

## 1. Fluxo Hermit TCP Pós-Sala (`GameClient.dll`, `ImageBase = 0x10000000`)

### 1.1 `SN_HostConnect (0x420303)` — Handler `0x10138EE0`
- **Despacho:** `CDispatch_NHosting_NGuest_SN_HostConnect` (`vtable 0x1049E9E0`, `register_va 0x1013C389`).
- **Layout binário confirmado:**
  - `+0x10` (payload `+0x00`): `uint16_t port` (`0x10138F54: movzx edx, word ptr [esi + 0x10]`)
  - `+0x12` (payload `+0x02`): `uint8_t` (não lido / padding)
  - `+0x13` (payload `+0x03`): string ASCII null-terminated de IP (`0x10138F0F: lea ecx, [esi + 0x13]`)
  - **Validação vs `build_host_connect_hermit` (`scripts/d187-mock-server.py:694-703`):** **100% compatível.**
- **Comportamento interno:**
  1. Lê `[0x10522218][+4]` (RoomMgr, **já inicializado antes de `SN_HostConnect`**, não `CMissionMgr`). Se `[RoomMgr + 0x194] == 1`, aborta chamando `0x10022770` em `CMissionMgr` (`[0x10516990]`).
  2. Monta string `"<ip>:<port>"` (`0x10138F0F..0x10138F85`).
  3. Busca usuário local na sala via `RoomMgr::GetLocalUser @ 0x10070E80` (`0x10138F96`) e compara `[user + 8]` (team) com `[TeamMgr + 0x30]` (`0x10027DF0`), gravando o resultado booleano em `[CMissionMgr + 0x49]` (`0x10138FB9`).
  4. Invoca `CMissionMgr::StartGameAsClient("127.0.0.1:27888", 0, 0)` em `0x100242D0` (`0x10139057`), que abre `Database\TheRaw.Gamdb00p`, executa `UpdateAssetLists 0` e dispara a conexão UDP LithTech (`CClientMgr::StartShell`).

### 1.2 `SN_BattleStart (0x420310)` — Handler `0x10138B60`
- **Despacho:** `CDispatch_NHosting_NGuest_SN_BattleStart` (`vtable 0x1049E9D4`, `register_va 0x1013C2ED`).
- **Descoberta crítica:** O handler em `0x10138B60` consiste em **uma única instrução `ret 4` (`C2 04 00`)**.
- **Conclusão:** `SN_BattleStart (0x420310)` é um **NO-OP absoluto** nesta build de `GameClient.dll`. O payload montado por `build_battle_start_hermit` (`scripts/d187-mock-server.py:705-716`) jamais é lido pelo cliente; enviá-lo é inócuo, mas não dispara nenhuma transição.

### 1.3 `SN_BaseRoomInfo (0x222111)` — Handler `0x10138BA0` → `ParseBaseRoomInfo @ 0x10070240`
- **Despacho:** `CDispatch_NMatchup_NPlay_SN_BaseRoomInfo` (`vtable 0x1049EA04`, `register_va 0x1013C2C6`).
- **Alvo:** Opera sobre `[0x10522218][+4] + 0x120` (membro do RoomMgr, não `CMissionMgr`).
- **Layout binário confirmado (`0x10070240..0x100702D8`, 27 bytes de payload = `0x1B`):**
  | Offset Pacote | Offset Payload | Tipo | Destino |
  |---:|---:|---|---|
  | `+0x10` | `+0x00` | `uint32` | `[esi + 0x00]` (`room_id`) |
  | `+0x14` | `+0x04` | `uint16` | `[esi + 0x04]` e `byte` → `TeamMgr[+0x30]` (`team_A_type = 0`) |
  | `+0x16` | `+0x06` | `uint16` | `[esi + 0x06]` e `byte` → `TeamMgr[+0x31]` (`team_B_type = 1`) |
  | `+0x18` | `+0x08` | `uint16` | `[esi + 0x08]` e `byte` → `TeamMgr[+0x32]` (`team_obs_type = 2`) |
  | `+0x1A..+0x2A` | `+0x0A..+0x1A` | `uint16/uint8` | `[esi + 0x0A..0x1C]` (último byte `+0x2A` convertido em `bool != 0`) |
- **Validação vs `build_base_room_info_hermit` (`scripts/d187-mock-server.py:659-675`):** **100% byte-exato (27 bytes).**
- **Discrepância encontrada no mock server:** Em `CN_PlayStartButton` / `CN_StartButton` / `CQ_StartGame` (`scripts/d187-mock-server.py:1087-1098`), `SN_BaseRoomInfo (0x222111)` **não é enviado** (apenas em `CQ_CreateRoom` na linha 991).

### 1.4 `SN_BaseUserList (0x222112)` — Handler `0x100CB7B0`
- **Despacho:** `CDispatch_NMatchup_NPlay_SN_BaseUserList` (`vtable 0x104A33F4`, `register_va 0x1017AE75`).
- **Pré-condições verificadas:**
  - `esi = [0x10522218][+4] + 0x1A8` (lista de usuários da sala).
  - `ebp = [Singleton_10515708 + 0x84]` (`BattleUserMgr`, obtido via `0x10014700`). Se `ebp == NULL`, retorna silenciosamente em `0x100CB7E0`.
  - **Ciclo de vida confirmado:** Tanto o registro de `SN_BaseUserList` (`0x1017AE75`) quanto a alocação de `BattleUserMgr` (`0x1017B985..0x1017B99E`, `0x30` bytes, ctor `0x1018DEF0`) ocorrem dentro do mesmo método `0x1017AB00` (`vtable 0x104A37FC` slot 6). Portanto, sempre que `SN_BaseUserList` puder ser despachado, `[0x10515708 + 0x84]` já está alocado.
- **Layout binário confirmado (`0x100CB7EE..0x100CB950`):**
  - `+0x10` (payload `+0x00`): `uint8` (não lido / reservado)
  - `+0x11` (payload `+0x01`): `uint8 count` (`0x100CB7EE`, loop `0..count-1` em `0x100CB93F`)
  - `+0x12` (payload `+0x02`): início do array de entradas, **stride `0x10E` (270 bytes)** (`0x100CB944: add edi, 0x10e`; ponteiro de loop `edi` começa em `pPacket + 0x16`):
    - `entry + 0x00` (`edi - 4`, `pPacket + 0x12`): `uint16 user_id` (`0x100CB88C`)
    - `entry + 0x02` (`edi - 2`, `pPacket + 0x14`): `uint16 team` (`0x100CB893`)
    - `entry + 0x04` (`edi + 0`, `pPacket + 0x16`): `char[] nickname` ASCII null-terminated (`0x100CB804..0x100CB83E`, convertido para `std::wstring` via `0x10196780`).
- **Processamento por entrada:**
  1. Procura `nickname` na lista da sala via `FindUserByNick @ 0x10070AD0`. Caso não encontre (`eax == 0`), a build `client-rebirth` possui um patch em cave `.text` (`0x10481180`) que aponta `esi` para um buffer estático (`0x1054E140`) e volta a `0x100CB88C`, evitando crash.
  2. Compara `nickname` com `[BattleUserMgr + 0x10]` (nick local preenchido em `0x10072160`) via `wcscmp` (`0x100CB8BA`); se igual, grava `user_id` em `[BattleUserMgr + 0x0C]`.
  3. Chama `AddBattleUser @ 0x1018E3A0`, que consulta `TeamMgr::GetTeamIndex(team) @ 0x1040EA80`. Como `TeamMgr_ctor @ 0x1040FA60` inicializa `[TeamMgr + 1] = 0` e `[TeamMgr + 0x19] = 1`, e `SN_BaseRoomInfo` grava `TeamMgr[+0x30]=0, [+0x31]=1, [+0x32]=2`, `ROOM_TEAM_A = 0` e `ROOM_TEAM_B = 1` são aceitos sem rejeição (`!= 0xFF`).
- **Validação vs `build_base_user_list_hermit` (`scripts/d187-mock-server.py:677-692`):** **100% byte-exato.**

---

## 2. Desmistificação do `0x4E69` e Fluxo Real de Desconexão (`TheRaw.exe`, `ImageBase = 0x00400000`)

A análise de `targets/district-187/traffic/disconnect_trace.log` cruzada com o disassembly de `TheRaw.exe` prova:

1. **O 1º hit (`RET=0x004166A7`, stack `0x10516D00 0x00004E69`) NÃO é uma desconexão por erro `0x4E69`:**
   - `0x004166A2` está no prólogo de `CClientMgr::StartShell @ 0x00416685`. Antes de criar o novo `CClientShell` (`0x78` bytes), `StartShell` chama `CClientMgr::Disconnect @ 0x004142CA` (função `__thiscall` de **0 argumentos**). O valor `0x00004E69` na pilha é apenas lixo/dado de frame anterior, jamais lido por `Disconnect`.
2. **A desconexão real ocorre no 2º hit (`CClientMgr::ProcessError @ 0x00414820`, `RET=0x00416B61`, arg0 = `0x02000001`):**
   - `0x02000001` = `ERROR_DISCONNECT (0x02000000) | LT_ERROR (0x00000001)`.
   - Origem exata em `CClientShell::Update @ 0x00418208`:
     - `0x004182F5`: chama `CClientShell::ProcessPackets @ 0x0047E1EB` → `CClientShell::ProcessPacket @ 0x0047E18D`.
     - `0x0047E1AE`: despacha o ID de pacote UDP (8 bits) via tabela `0x0085C760` (inicializada em `0x0047E3A0`).
     - Se o handler UDP retornar não-zero (`eax = 1 = LT_ERROR`), `0x004182FE: or eax, 0x2000000` transforma o retorno em `0x02000001` → `0x00416B5C: call CClientMgr::ProcessError` → `0x00414850: call CClientMgr::Disconnect`.
   - **Tabela UDP relevante (`TheRaw.exe @ 0x0085C760`):**
     - `pkt 4` (`0x0047D624`): `OnNetProtocolVersionPacket` (`LT_INVALIDNETVERSION`)
     - `pkt 6` (`0x0047E06A`): `SMSG_LOADWORLD` → `CClientShell::DoLoadWorld @ 0x00418BFB` (retorna `1` em `"Inherit failed"` / `"CreateVisContainerObjects failed"`, `0x29` em `LT_MISSINGWORLDFILE`, `0x2A` em `LT_INVALIDWORLDFILE`; em sucesso envia pacote UDP ID `9` ao servidor).
     - `pkt 7` (`0x0047D5FE`): `OnClientObjectID`
     - `pkt 8` (`0x0047DB2D`): `SMSG_UPDATE` (chama `0x00414B76` para ler objetos/modelos)
     - `pkt 10` (`0x0047DBFF`): `SMSG_UNGUARANTEEDUPDATE` (posições/rotações)
     - `pkt 12` (`0x0047D409`): `SMSG_YOURID` (`"Got ID packet (%d)"`)
     - `pkt 13` (`0x0047E309`): `SMSG_MESSAGE` → `IClientShell::OnMessage` (`[0x85CB64]+0x4C`)

---

## 3. Entrada no Mundo 3D: `OnEnterWorld` (`GameClient.dll`) ↔ `GameServer.dll`

### 3.1 Lado Cliente (`GameClient.dll`)
1. `CGameClientShell::OnEnterWorld @ 0x10236A30` (`"call - void CGameClientShell::OnEnterWorld() call"`):
   - Executa `UpdateAssetLists 1` (se `EnablePrefetch` ativo), inicializa `StairStepHeight`, `ModelLODEnable = 1`, chama `CMissionMgr::OnEnterWorld @ 0x10086FC0` (`0x10236B89`) e aciona `CPlayerMgr::OnEnterWorld @ 0x10217B40`.
2. `CPlayerMgr::OnEnterWorld @ 0x10217B40` (`"OnEnterWorld() m_ePlayerState = ePlayerState_None"`):
   - Obtém `BattleUserMgr = [0x10515708 + 0x84]` (`0x10217BA6`), chama `GetLocalPlayerInfo @ 0x1018E180` (busca `user_id == [BattleUserMgr + 0x0C]`).
   - Se o usuário local for encontrado e `[local + 0x10] == 0` (não-observador), envia mensagem UDP garantida **`MID = 0xA8` (`168`)** via `g_pLTClient->SendToServer` (`0x10217C20`).
   - **Sem `SN_BaseUserList (0x222112)` válido**, `GetLocalPlayerInfo` retorna `NULL` e `MID 0xA8` nunca é enviado.

### 3.2 Lado Servidor (`GameServer.dll`, `ImageBase = 0x10000000`)
Mapeamento real verificado da vtable `CGameServerShell @ 0x1019220C`:
- **Slot 1 (`+0x04`, `0x10056140`):** `OnServerInitialized` — lê `ServerGameOptions*` via `g_pLTServer->GetGameInfo (+0xC8)` (`0x10056898`), copia para `[CGameServerShell + 0x30]` (`0x10055720`), grava `status` em `[pOpts + 0xAC]` (`0x100568C3`).
- **Slot 5 (`+0x14`, `0x10053490`):** `OnClientEnterWorld(HCLIENT)` → `ClientConnectionMgr::FindClientConnection @ 0x10095D90` → `0x10052BB0` → `CreatePlayer @ 0x100549A0` (`"CPlayerObj"`) ou `CreateObserver @ 0x10054A70`.
- **Slot 6 (`+0x18`, `0x1004FD70`):** `OnClientExitWorld(HCLIENT)`.
- **Slot 10 (`+0x28`, `0x10054DD0`):** `OnMessage(HCLIENT, ILTMessage_Read*)`:
  - Encaminha `MID 0xED` para `ClientConnectionMgr::OnMessage @ 0x10096660` (máquina de estados: `Hello (3)` → `KeyChallenge` → `CRCCheck` → `Overrides` → `LoggedIn` → `Loading (9)` → `InWorld (11)`).
  - Despacha `MID 0xA8` (`case 9 @ 0x10054FFB` → `0x10054140`), que responde ao cliente com `MID 0xA7`.
  - Handler de spawn (`0x1004FE40`) marca `[CPlayerObj + 0x934] = 1` e aciona `CServerMissionMgr::0x100DE230`.
- **Slot 14 (`+0x38`, `0x100557C0`):** `ServerAppMessageFn(ILTMessage_Read*)` (recebe `SendToServerShell`, switch `0..9`; `case 0` configura `[0x101E4078 + 0x6C]`).
- **Slot 15 (`+0x3C`, `0x1004FD10`):** `OnAddClient(HCLIENT)` → `ClientConnectionMgr::OnAddClient @ 0x100978C0`:
  - Carrega `ClientData` (`0xD8` bytes) via `0x1004CFD0`.
  - Verifica `m_UserInfoMap.find(userId)` (`[ebp + 0x20]`). Se não encontrar, checa `[0x101E4078 + 0x6C]` (`0x100979BD..0x100979C6`): caso seja `0`, expulsa com `"Fail to Find UserInfo"` (`eClientConnectionState_Error = 4`).
  - **Verificação positiva:** O construtor `0x100E4350` (`0x100E4395: mov word ptr [eax + 0x6c], 1`) **já inicializa `[0x101E4078 + 0x6C] = 1` por padrão**, logo o servidor dedicado standalone já faz bypass automático de `"Fail to Find UserInfo"`.

---

## 4. Auditoria de `d187_server_host.cpp` e `Engine_Server.dll`

1. **Bug Concreto Confirmado — `StartWorld` sobrescreve e zera `m_pGameInfo` (`Engine_Server.dll @ 0x10062259`):**
   - `CLTServerInterface::StartWorld @ 0x10062259` chama `CServerMgr::SetGameInfo(req->m_pGameInfo, req->m_GameInfoLen)` (`0x100689CF`), que executa `free(m_pGameInfo)` (`0x100689DA`) e sobrescreve `[CServerMgr + 0x694] = req->m_GameInfoLen`.
   - Em `targets/district-187/server_host/d187_server_host.cpp:458-462`, `StartGameRequest req` é zerado com `memset` e passado com `req.m_pGameInfo = nullptr` e `req.m_GameInfoLen = 0`, destruindo o `ServerGameOptions*` configurado em `SetGameInfo(&pOpts)` na linha 439.
   - **Correção cirúrgica recomendada:** Preencher `req.m_pGameInfo = &pOpts; req.m_GameInfoLen = sizeof(pOpts);` antes de `pServer->StartWorld(&req)`.
2. **Log `Error: Unable to open up file 'CRC\373831444d5f444f5f41524348495645.crc'` (`server_host.log:14`):**
   - Origem em `Engine_Server.dll @ 0x10011AC0`. Não-fatal (`World loaded.` e `StartWorld -> OK` executam normalmente em seguida).
3. **Hooks e Inicialização (`d187_server_host.cpp`):**
   - `LTGUID`, `AddResources` (11 arquivos alinhados com `Default.archcfg`), `HostGame` (UDP `0.0.0.0:27888`), `LoadBinaries` (`status=0x1`), hook `sm_WriteModelFiles @ 0x5DD7D`, hook `GameServerLog @ 0x5FA20` e hook `KickClient @ g_pLTServer+0x54` estão corretos e confirmados no `server_host.log`.
   - **Observação de diagnóstico:** No `server_host.log` atual (`18` linhas), `Active UDP Clients: 0` permaneceu em `0` (nenhum cliente conectou durante essa execução).

---

## 5. Resumo das Correções Cirúrgicas Recomendadas

1. **`targets/district-187/server_host/d187_server_host.cpp` (linhas 458-462):**
   - Adicionar `req.m_pGameInfo = &pOpts;` e `req.m_GameInfoLen = sizeof(pOpts);` antes de `pServer->StartWorld(&req);` para impedir que `Engine_Server.dll @ 0x10062259` zere `m_pGameInfo`.
2. **`scripts/d187-mock-server.py` (linhas 1087-1098 — `CN_PlayStartButton` / `CQ_StartGame`):**
   - Enviar `build_base_room_info_hermit(self.session_id, room_id=1, key_byte=self.key_byte)` **antes** de `SN_HostConnect` (e também antes de `SN_HostConnect` em `CQ_CreateRoom`, linhas 988-994), garantindo que `TeamMgr[+0x30/+0x31/+0x32]` esteja populado antes de `SN_HostConnect @ 0x10138FA1` e `SN_BaseUserList @ 0x100CB7B0`.
3. **`scripts/d187-mock-server.py` (`build_base_user_list_hermit` e `build_battle_start_hermit`):**
   - `build_base_user_list_hermit` (`0x222112`) está **100% correto** — nenhuma alteração necessária no layout.
   - `build_battle_start_hermit` (`0x420310`) aponta para um handler `ret 4` (no-op em `0x10138B60`) — pode permanecer por compatibilidade, sabendo que não tem efeito no cliente.

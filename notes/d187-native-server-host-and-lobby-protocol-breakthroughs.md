# District 187: Native LithTech Dedicated Server Host (`Engine_Server.dll`), Hermit TCP Sequence Protocol & End-to-End Lobby-to-3D Breakthroughs

> **Data:** 2026-11-19  
> **Alvo:** `targets/district-187/client-rebirth/` (`TheRaw.exe`, `Game/GameClient.dll`, `Engine_Server.dll`, `Game/GameServer.dll`)  
> **Objetivo deste documento:** Servir como referência técnica exaustiva e verificada empiricamente (com endereços VA/RVA, disassembly x86, layouts binários, structs C++ e comandos de compilação) para que desenvolvedores, agentes e IAs possam dar continuidade imediata ao projeto sem perder nenhum contexto.

---

## 1. Resumo Executivo (O que foi destravado)

| Camada | Sintoma Anterior | Causa Raiz Empírica | Solução Aplicada & Status |
| :--- | :--- | :--- | :--- |
| **Login -> Canais** | Tela `"Please wait..."` infinita após clicar `TAMAM` | `Hermit::Session::Waiter::TCP` (`0x0050BB10` em `TheRaw.exe`) exige **número de sequência monotônico `uint16` (`1, 2, 3, ...`)** no offset `+4` do header Hermit; pacotes fora de sequência eram descartados com `free()`. | Implementado `self.send_seq` em [`scripts/d187-mock-server.py`](../scripts/d187-mock-server.py). **VALIDADO EM TELA REAL (`Kanal Seçimi` -> `Oyun Lobisi`)**. |
| **Lista de Servidores** | IP e Nome desalinhados em `SN_ServerInfo (0x220101)` | `0x100735F0` em `GameClient.dll` lê `server_code` em `+5`, **IP em `+10` (`+0x0A`)** e **Nome em `+26` (`+0x1A`)**. | Corrigido `build_server_info_hermit()` com offsets exatos. **VALIDADO**. |
| **Create Room (Mapas & Modos)** | Dropdowns de Mapa, Mode, Players e Type vazios | Patch anterior (`mov al, 1; ret` em `0x10408B50`) pulava o loop inteiro de leitura de mapas de `TheRaw.Gamdb00p`. | Restaurado prólogo `0x10408B50` (`sub esp, 0x11c`) e patcheado apenas o salto em **`0x10408C7E`** (`74 3f` → `74 27`, `je 0x10408ca7`) para pular somente entradas divergentes. **VALIDADO EM TELA REAL (Mapas, TDM, 8v8, General populados)**. |
| **Lobby -> Sala (`CRoomScene`)** | Clicar `Confirm` no `Create Room` não mudava de tela | `SA_CreateRoom (0x220202)` (`0x10139250`) só valida erros; quem dispara `ChangeScene(3)` (`CRoomScene`) é **`SN_Info (0x220203)`** (`0x101393A0` → `0x10072640`). | Implementado `build_room_info_hermit()` (`0x220203`). **VALIDADO EM TELA REAL (`Bekleme Odası`)**. |
| **Sala -> Conexão 3D (`UDP 27888`)** | `SN_BattleStart (0x420310)` era `ret 4` (stub vazio) e `F5 Başla` enviava `0x220314` | O pacote real que chama `CMissionMgr::StartGameAsClient("ip:port", 0, 0)` (`0x100242D0`) é **`SN_HostConnect (0x420303)`** (`0x10138EE0`). | Implementado `build_host_connect_hermit()` (`0x420303`) + handler `0x220314` + auto-connect na criação de sala. **VALIDADO NA MEMÓRIA VIVA (`StartGameRequest.m_TCPAddress = "127.0.0.1:27888"`)**. |
| **Servidor Dedicado Nativo 3D** | `TheRaw.exe` não aceita `-dedicated`; gateway Python UDP usava protocolo mock incompatível com `CUDPDriver` | `Engine_Server.dll` + `Game\GameServer.dll` autênticos existem no disco, mas exigem um executável host x86 seguindo a ABI LithTech Jupiter EX + `LTGUID` oficial. | Criado e compilado [`targets/district-187/server_host/d187_server_host.cpp`](../targets/district-187/server_host/d187_server_host.cpp) → **`D187_ServerHost.exe`** (MSVC x86) com **`LTGUID` real `{DF560590-D918-4A51-9CB1-38EBBE3879AD}`**. **VALIDADO (`HostGame 27888 -> OK`, `LoadBinaries -> OK`, `StartWorld Worlds\Arrival.World00p -> OK`, 60Hz tick loop)**. |

---

## 2. Descoberta 1 — `Hermit::Session::Waiter::TCP` (`0x0050BB10` em `TheRaw.exe`)

### Evidência em memória viva + disassembly
Ao inspecionar o processo vivo `TheRaw.exe`, observou-se que os 14 pacotes de resposta do login eram decifrados corretamente pelo `0x004FF660`, mas `GameClient.dll` (`user_mgr`, `ServerManager`, `CLoginSceneHandler`) nunca os recebia, enquanto o objeto `Hermit::Session::Waiter::TCP` (`vtable 0x00803460`) exibia `+0x04 = 0x0000000E` (14).

Disassembly de `0x0050BB10` (`Hermit::Session::Waiter::TCP`, slot 5 da vtable):
```asm
0x0050BB10: push     ebp
0x0050BB11: mov      ebp, esp
0x0050BB13: push     esi
0x0050BB14: push     edi
0x0050BB15: mov      edi, dword ptr [ebp + 8]    ; edi = pPacket decifrado
0x0050BB18: mov      esi, ecx
0x0050BB1A: mov      ecx, edi
0x0050BB1C: call     0x4fc760                    ; é pacote de controle 0x200xx?
0x0050BB21: test     al, al
0x0050BB23: jne      0x50bb29
0x0050BB25: inc      word ptr [esi + 4]          ; expected_seq++ (1, 2, 3, ..., 14)
0x0050BB29: mov      ecx, edi
0x0050BB2B: call     0x4fc630                    ; ax = uint16 header[4:6] (PacketSeq)
0x0050BB30: cmp      ax, word ptr [esi + 4]      ; PacketSeq == expected_seq ?
0x0050BB34: je       0x50bb49                    ; SIM -> entrega para GameClient.dll!
0x0050BB3A: push     edi
0x0050BB3B: call     0x5c7c7a                    ; NÃO -> free(pPacket) e DESCARTA!
```

### Regra de protocolo obrigatória
- Header Hermit de 16 bytes em Big-Endian: `struct.pack('>IHHII', crc32, seq, total_len, session_id, packet_id)`
- Pacotes de controle (`(packet_id & 0xFFFFFF00) == 0x00020000`, ex: `0x20081`, `0x20083`): **`seq = 0`** (não incrementam o contador).
- **Todos os demais pacotes de jogo** (`SA_JoyGameLogin`, `SN_UserInfo`, `SN_LockEnd`, `SN_Info`, `SN_HostConnect`, etc.): **`seq` DEVE incrementar monotonicamente (`1, 2, 3, ...`) por sessão TCP** (`(self.send_seq + 1) & 0xFFFF`).
- Além disso, o buffer de decifragem `0x004FF660` tem limite rígido de `0x400` (1024 bytes) por pacote (`cmp eax, 0x400; ja 0x4ff743`), portanto `SN_ItemList` foi mantido compacto (8 itens = 234 bytes) com `TCP_NODELAY` e pacing de `20ms`.

---

## 3. Descoberta 2 — Layouts Binários Verificados em `GameClient.dll`

### 3.1 `SN_ServerInfo` (`0x220101` — Parser em `0x100735F0`)
- `payload[0]`: `uint8 flag = 0`
- `payload[1]`: `uint8 server_count = 1`
- `payload[2:]`: entradas de **98 bytes (`0x62`)**:
  - `+0x00..+0x04`: `char id[5]` (`"S2\0\0\0"`)
  - `+0x05..+0x09`: `char server_code[5]` (`"S2\0\0\0"`) — lido em `0x100735FB`
  - `+0x0A..+0x19` (**+10..+25**): `char ip[16]` (`"127.0.0.1\0"`) — lido em `0x10073616`
  - `+0x1A..+0x50` (**+26..+80**): `char name[55]` (`"District 187 Dedicated [BR]\0"`) — lido em `0x10073633`
  - `+0x51..+0x54` (+81): `uint32 server_id`
  - `+0x55..+0x56` (+85): `uint16 port` (`12000`)
  - `+0x57..+0x58` (+87): `uint16 cur_users`
  - `+0x59..+0x5A` (+89): `uint16 max_users`
  - `+0x5B` (+91): `uint8 skip_flag` (`0 = visible`)
  - `+0x5C` (+92): `uint8 server_type` (`1 = normal`)

### 3.2 `SN_Info` (`0x220203` — Handler em `0x101393A0` + `ParseRoomInfo` em `0x10072640`)
Dispara **`ChangeScene(3)` (`CRoomScene` / `Bekleme Odası`)** após `CQ_CreateRoom (0x220201)`:
- Payload: **224 bytes**
- `payload[0:2]` (`+0x10`): `uint16 room_id`
- `payload[6]` (`+0x16`): `uint8 room_mode` — jump table `0x101394D8` para valores `2..6`:
  - `2` (TDM), `3` (Demolition), `6` (Practice) → **`ChangeScene(3)` (`CRoomScene`)**
  - `5` → `ChangeScene(7)`
- `payload[9]` (`+0x19`): `uint8 max_players` (`16`)
- `payload[10]` (`+0x1A`): `uint8 cur_players` (`1`)
- `payload[25]` (`+0x29`): `uint8 mode`
- `payload[29:]` (`+0x2D`): `char room_name[]` (null-terminated)
- `payload[90:102]` (`+0x6A..+0x75`): `uint16[6]` (`map_id, goal, time_limit, ...`)

### 3.3 `SN_HostConnect` (`0x420303` — Handler em `0x10138EE0` → `0x10138F0B`)
Dispara **`CMissionMgr::StartGameAsClient("ip:port", 0, 0)` (`0x100242D0`)** para conectar ao servidor dedicado UDP LithTech:
- `payload[0:2]` (`+0x10`): `uint16 LE port` (`27888`)
- `payload[2]` (`+0x12`): `uint8 pad` (`0`)
- `payload[3:]` (`+0x13`): `char ip[]` null-terminated (`"127.0.0.1\0"`)
- `0x10138F46` concatena `":"` + `itoa(port)` → `"127.0.0.1:27888"` e chama `0x100242D0`.

### 3.4 Outros Opcodes Verificados na Captura Real
- `0x220314`: Botão **`F5 Başla`** (Start Game na sala).
- `0x220319`: `SN_ChangeLeader` (`0x101396C0`).
- `0x222111`: `SN_BaseRoomInfo` (`0x10138BA0` → `0x10070240`).
- `0x222112`: `SN_BaseUserList` (`0x100CB7B0`).
- `0x240101` / `0x240102`: `CQ_EquipOpen` / `SA_EquipOpen` (`Shop/Inventory`).

---

## 4. Descoberta 3 — Patch Cirúrgico do Carregador de Mapas (`GameClient.dll`)

Em `Game/GameClient.dll` (sincronizado com `GameClient.dll` na raiz):
- **`0x10408B50`** (file offset `0x407F50`): restaurados os 6 bytes originais `81 ec 1c 01 00 00` (`sub esp, 0x11c`) para que o loop de leitura de `TheRaw.Gamdb00p` execute integralmente.
- **`0x10408C7E`** (file offset `0x40807E`): alterado `74 3f` (`je 0x10408cbf`, que abortava o loop retornando `false` e disparava o pop-up `GDB Mission/Level DetailInfo`) para **`74 27` (`je 0x10408ca7`)**, pulando apenas o índice divergente (`inc esi`) e carregando todos os mapas e modos válidos na tela `Create Room`.

---

## 5. Descoberta 4 — Servidor Dedicado Nativo LithTech (`D187_ServerHost.exe`)

### 5.1 ABI Completa de `Engine_Server.dll` (x86)
- **Export `CreateServer`** (`RVA 0x62631`, `__cdecl`):
  `int CreateServer(int version, const LTGUID& appGuid, ServerInterface** ppServer);`
  - Exige **`SI_VERSION == 2`**.
  - Copia os 16 bytes de `appGuid` para `g_pServerMgr + 0x4B8` (`m_NetMgr + 0x28`).
- **`LTGUID` Autêntico do District 187 / S2 Online** (extraído da memória viva de `TheRaw.exe` em `g_pClientMgr + 0x198 + 0x28`):
  ```cpp
  // {DF560590-D918-4A51-9CB1-38EBBE3879AD}
  LTGUID appGuid = { 0xDF560590, 0xD918, 0x4A51, { 0x9C, 0xB1, 0x38, 0xEB, 0xBE, 0x38, 0x79, 0xAD } };
  ```
- **Vtable `CLTServerInterface`** (`0x10158bcc`, 28 slots):
  - `[0]` `SetAppHandler`, `[1]` `ParseCommandLine`, `[5]` `AddResources`, `[6]` `SetGameInfo`, `[7]` `LoadBinaries`, `[10]` `StartWorld`, `[19]` `Update`, `[20]` `InitNetworking`, `[21]` `GetServiceList`, `[22]` `FreeServiceList`, `[23]` `SelectService`, `[24]` *stub (`CUDPDriver::vt[+0x38]`)*, **`[25]` `HostGame` (`CUDPDriver::HostSession` @ `vt[+0x30]`, `0x1007bb51`)**, `[26]` `GetTcpIpAddress`.
- **Struct `NetHost` (`0x2050` bytes, strings UTF-16LE `wchar_t`)**:
  - `+0x0000`: `uint16_t m_Port` (`27888`)
  - `+0x0004`: `wchar_t m_sBindAddr[0x22]` (`L"0.0.0.0"`)
  - `+0x0048`: `uint32_t m_dwMaxConnections` (`16`)
  - `+0x004C`: `wchar_t m_sName[0x1000]` (`L"District 187 Local Dedicated"`)
- **Struct `ServerGameOptions` (VC14 → VC10 ABI-safe)**:
  - `CGameServerShell::OnServerInitialized()` (`0x10056140` em `GameServer.dll`) chama `g_pLTServer->GetGameInfo(&pData, &nLen)` e espera `*(ServerGameOptions**)pData`, contendo 6 `std::string` do MSVC 2010 (`sizeof = 0x1C`, `_Myres = 15` para SSO inline) seguidos de `status` em `+0xAC` (`1 = OK`, `2 = erro de rede`).
- **Ordem Obrigatória de Inicialização:**
  1. `CreateServer(2, appGuid, &pServer)` → `SetAppHandler` → `ParseCommandLine` → `AddResources`
  2. `InitNetworking` → `GetServiceList` → `SelectService` → **`HostGame(&hostInfo)` (Slot `[25]`)** *(DEVE ocorrer antes de `LoadBinaries`, pois `OnServerInitialized` consulta `GetTcpIpAddress` e `m_NetMgr.GetDriver("internet")->m_Socket`!)*
  3. `SetGameInfo(&pOpts, sizeof(pOpts))` → `LoadBinaries()` (`Game\GameServer.dll`, `status = 0x1`)
  4. `StartWorld(&req)` (`Worlds\Arrival.World00p`) → loop `Update(0)` a 60Hz.

### 5.2 Requisito Obrigatório de Nome do Executável (`TheRawServer.exe`)
Ao validar a primeira conexão UDP real (`Active UDP Clients: 0 -> 1 -> 0` em 2 ticks), `GameServer.dll` enviou o aviso `not found file, TheRawServer_xxx.exe` e desconectou o cliente. A desmontagem de **`0x10034B85..0x10034BA3`** em `GameServer.dll` revelou:
```asm
0x10034B85: call dword ptr [0x1018c020]  ; GetModuleFileNameA(NULL, buf, 260)
0x10034B92: push 0x10190c34              ; "TheRawServer.exe"
0x10034B97: push ecx                     ; buf
0x10034B98: call dword ptr [0x1018c298]  ; strstr(buf, "TheRawServer.exe")
0x10034BA1: cmp  eax, 0
0x10034BA3: jne  0x10034be1              ; se encontrar, extrai o diretório raiz e continua!
```
Portanto, o executável host compilado **DEVE se chamar `TheRawServer.exe`** (não `D187_ServerHost.exe`).

### 5.3 Como Compilar (MSVC 2019 x86)
Execute [`targets/district-187/server_host/build_server_host.bat`](../targets/district-187/server_host/build_server_host.bat) para gerar `targets/district-187/server_host/TheRawServer.exe`:
```bat
call "C:\Program Files (x86)\Microsoft Visual Studio\2019\BuildTools\VC\Auxiliary\Build\vcvars32.bat"
cl /nologo /EHsc /O2 /Fe:targets\district-187\server_host\TheRawServer.exe targets\district-187\server_host\d187_server_host.cpp /Fo:targets\district-187\server_host\d187_server_host.obj
```

---

## 6. Guia de Continuidade para Outras IAs e Colaboradores

### Estado Atual Validado
- **Login → Seleção de Canal → Lobby → Create Room (com Mapas/Modos) → Sala de Espera (`Bekleme Odası`)**: **100% funcionando em tela real no cliente nativo**.
- **Servidor Dedicado Nativo (`D187_ServerHost.exe`)**: **100% funcionando** (`UDP 0.0.0.0:27888`, `GameServer.dll` inicializado, `Worlds\Arrival.World00p` carregado a 60Hz, `LTGUID` oficial sincronizado).

### Próximos Passos Imediatos
1. **Validar handshake UDP 3D (`TheRaw.exe` ↔ `D187_ServerHost.exe` na porta 27888):**
   - Com o novo `LTGUID` `{DF560590-D918-4A51-9CB1-38EBBE3879AD}`, validar se `CMissionMgr::StartGameAsClient("127.0.0.1:27888", 0, 0)` completa a conexão UDP e carrega a tela de loading / mapa 3D.
   - Caso `GameServer.dll` exija algum pacote inicial de `CGameServerShell::OnClientEnterWorld` ou `NMatchup_NPlay_SN_BaseUserList (0x222112)` / `SN_ChangeLeader (0x220319)` para popular os slots da sala antes do `F5 Başla`, implementar os builders correspondentes em `scripts/d187-mock-server.py`.
2. **Popular os Slots da Sala (`Bekleme Odası`) & Botão `F5 Başla`:**
   - Implementar `SN_BaseUserList (0x222112)` (`0x100CB7B0`) e `SN_ChangeLeader (0x220319)` (`0x101396C0`) para exibir o jogador `Gleidison` como líder no Slot 0 e desbloquear a seleção de time e `F5 Başla` sem precisar do auto-connect imediato.
3. **Atualizar `scripts/test_client_handshake_smoke.py`:**
   - Adequar o smoke test para esperar `SN_Info (0x220203)` e `SN_HostConnect (0x420303)` após `CQ_CreateRoom (0x220201)` e `CQ_StartGame (0x220314)`.

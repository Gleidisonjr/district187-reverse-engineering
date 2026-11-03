# District 187: Descoberta e Resolução Definitiva do Bloqueio de Login ("Please Wait")

## Contexto e Sintoma
Ao iniciar o cliente nativo `TheRaw.exe` apontado para o servidor Hermit local (`127.0.0.1:12000`), o handshake TCP inicial completava 100%, os pacotes de autenticação (`CQ_JoyGameLogin` -> `SA_JoyGameLogin`) eram trocados, porém a interface Scaleform permanecia congelada na tela de login (`Scene[10]`) com a mensagem `"please wait"`.

---

## 1. Engenharia Reversa Completa em `GameClient.dll` (Causa Raiz Real)

A desmontagem completa das tabelas de despacho de pacotes (`0x10194800` global e `0x10132d10` `CLoginScene`) e dos descritores RTTI em `targets/district-187/client-rebirth/Game/GameClient.dll` revelou por que a tentativa anterior ainda deixava o cliente travado:

### 1.1 O Verdadeiro Papel de `0x10191740` (`IsPacketerrorMessage`)
A função `0x10191740` imprime a string de depuração `"IsPacketerrorMessage() call"` (`0x104a46f8`). Sua assinatura real é:
`bool __thiscall IsPacketerrorMessage(void* this, int errorCode, uint16 origin)`

```assembly
0x1019175e: mov edi, dword ptr [esp + 0xe8]  ; edi = errorCode (offset 18 do pacote, uint32)
0x10191765: push ebp
0x10191766: test edi, edi                    ; errorCode == 0 ?
0x10191768: je 0x1019176c                    ; SE errorCode == 0 -> RETORNA al = 0 (SEM ERRO!)
```

No handler `SA_JoyGameLogin` (`0x110112` em `0x100d74a0`) e `SA_Login` (`0x110102` em `0x100d7450`):
- Quando `errorCode == 0`, `IsPacketerrorMessage` retorna `al = 0` (**nenhum erro**).
- O handler faz `test al, al; je 0x100d74e2` (retorna imediatamente **mantendo `[eax + 0x64] == 1`**, ou seja, mantendo `"please wait"` ativo enquanto aguarda a sequência de pacotes de sincronização de conta `NLaunch`!).
- Apenas quando ocorre um **erro** (`al == 1`) é que `0x100d74a0` limpa `[eax + 0x64] = 0` para destravar o formulário de login na mesma cena (`Scene[10]`).
- Além disso, a constante `0x00A40221` em `0x10191bd0` era na verdade o código de erro `UI_SYS_ROOM_NeedWeaponChange` (`0x10495ac0`), e não um `AccountID`! Tanto o `uint16` no offset `0x10` (16) quanto o `uint32` no offset `0x12` (18) devem ser **`0`**.

### 1.2 O Pacote que Realmente Faz a Transição de Cena: `SN_LockEnd` (`0x210121`)
Na tabela global de despacho (`0x10194800`), em `0x10194a87`:
```assembly
0x10194a87: mov dword ptr [eax], 0x104a48bc  ; vtable de CDispatch_NLaunch_NLock_SN_LockEnd (handler 0x10032f30)
0x10194a92: push 0x210121                    ; Packet ID REAL = 0x210121
0x10194a99: call 0x10041800
```
- O servidor mock anterior enviava `PACKET_SN_LOCK_END = 0x210202`, que em `GameClient.dll` é na verdade `SA_CreateUser` (`0x10031bc0`)!
- Como o opcode `0x210121` nunca era enviado, o handler `CDispatch_NLaunch_NLock_SN_LockEnd` (`0x10032f30`) nunca era executado, `ChangeScene(0)` (`0x1004b8a0`) nunca era chamado, e o cliente ficava preso em `Scene[10]` (`LoginScene`) aguardando infinitamente!

---

## 2. Tabela Oficial de Opcodes e Layouts Binários (`GameClient.dll`)

| Nome do Pacote (RTTI) | Opcode Antigo (Errado) | **Opcode Real (`GameClient.dll`)** | Handler VA | Estrutura Exata do Payload (Offset `0x10` = início após header Hermit de 16B) |
| :--- | :--- | :--- | :--- | :--- |
| `SA_Login` | `0x110102` | **`0x110102`** | `0x100D7450` | `word[0x10] = 0`, `dword[0x12] = 0` (64B payload) |
| `SA_JoyGameLogin` | `0x110112` | **`0x110112`** | `0x100D74A0` | `word[0x10] = 0`, `dword[0x12] = 0` (64B payload) |
| `CQ_Join` / `SA_Join` | *(ausente)* | **`0x110124` / `0x110125`** | `0x10030C90` | Enviado ao selecionar um servidor na `ServerList` (`Scene[0]`). Responde `SA_Join` (`0x110125`) + `SN_ChannelList` (`0x220102`) + `SN_LockEnd` (`0x210121`). |
| `SN_UserInfo` | `0x210101` | **`0x210101`** | `0x100D7A70` | `char[0x10..0x28]` (25B Nickname null-terminated), `char[0x29..0x41]` (25B ClanName null-terminated). Registrado em `CLoginScene` (enviar antes de `SN_LockEnd`). |
| `SN_Record` | `0x210203` | **`0x210103`** | `0x10031140` | Lê `dword` stats até `[eax + 0xd6]` -> requer no mínimo 218B totais (usamos 224B de payload). |
| `SN_RankingInfo` | *(ausente)* | **`0x210105`** | `0x10031110` | Lê `dword[eax + 0x16]` (Rank) e `dword[eax + 0x1a]` (Exp) -> 16B payload. |
| `SN_ItemList` | `0x210201` | **`0x210111`** | `0x10031000` | `byte[0x10] = 0` (page flag), `byte[0x11] = count`. Em `0x12`, cada item tem **27 bytes (`0x1B`)**: `<QBIIIHI`. |
| `SN_SlotInfo` | *(ausente)* | **`0x210113`** | `0x100312B0` | 260B totais (`0x41 * 4` = 244B payload) com UIDs equipados. |
| `SN_LockEnd` | `0x210202` | **`0x210121`** | `0x10032F30` | `word[0x10] = 0`, `dword[0x12] = 0` (16B zeros). Dispara `ChangeScene(0)` (`CServerListScene`) ou `ChangeScene(1)` (`CChannelListScene`)! |
| `SN_ServerInfo` | `0x220101` | **`0x220101`** | `0x1011EB80` | `byte[0x10] = 0`, `byte[0x11] = server_count`. Em `0x12`, cada entrada de servidor tem **98 bytes (`0x62`)**: `+5`: region tag (5B), `+10`: IP string (16B `"127.0.0.1\x00"`), `+26`: Server Name (55B), `+81`: `uint32 id`, `+85`: `uint16 port` (`12000`), `+87`: `uint16 cur_users`, `+89`: `uint16 max_users`, `+91`: `uint8 skip_flag = 0`, `+92`: `uint8 type = 1`. |
| `SN_ChannelList` | `0x220102` | **`0x220102`** | `0x100BA790` | `byte[0x10] = 0`, `byte[0x11] = count`, `0x12..0x16`: 5B header (`uint32 server_id`, `uint8 0`). Em `0x17`, entradas de **57 bytes (`0x39`)**: `+0`: `uint8 id`, `+1`: `uint16 cur`, `+3`: `uint16 max`, `+5`: `uint8 type`, `+10`: `uint32 status = 0`, `+14`: 43B Channel Name. |
| `CQ_EnterUser` / `SA_EnterUser` | `0x220101` / `0x220102` | **`0x220111` / `0x220112`** | `0x100BA640` | `word[0x10] = 0`, `dword[0x12] = 0`, `byte[0x18] = channel_id`. Dispara `ChangeScene(2)` (`CLobbyScene`)! |
| `SN_BattleStart` | `0x230104` | **`0x420310`** | `0x10138B60` | `CDispatch_NHosting_NGuest_SN_BattleStart` (redireciona para o gateway UDP `27888`). |

---

## 3. Tabela de Cenas (`0x104ee4c0` em `GameClient.dll`)
- `Scene[0]` = `CServerListScene` (`0x10049be0`)
- `Scene[1]` = `CChannelListScene` (`0x10049d00`)
- `Scene[2]` = `CLobbyScene` (`0x10049bb0`)
- `Scene[3]` = `CRoomScene` (`0x10021030`)
- `Scene[4]` = `CShopInvenScene` (`0x10030b70`)
- `Scene[10]` = `CLoginScene` (`0x10030b10`)
- `Scene[11]` = `CCharCreateScene` (`0x10030bd0`)
- `Scene[12]` = `CInGameScene` (`0x1004a940`)

---

## 4. Verificação Empírica (`scripts/test_client_handshake_smoke.py`)
O servidor `scripts/d187-mock-server.py` foi atualizado com todos os opcodes e estruturas binárias reais e reiniciado na porta `12000`. O teste automatizado `scripts/test_client_handshake_smoke.py` validou 100% da sequência:
1. Handshake Hermit (`0x20080` -> `0x20081`, `0x20082` -> `0x20083`).
2. Login (`0x110111` -> `0x110112` com `Origin=0, ErrorCode=0`).
3. Sincronização `NLaunch` completa (`0x210101` `SN_UserInfo`, `0x210105` `SN_RankingInfo`, `0x210111` `SN_ItemList`, `0x210103` `SN_Record`).
4. População de Servidores e Canais (`0x220101` `SN_ServerInfo` 98B/entry, `0x220102` `SN_ChannelList` 57B/entry).
5. Transição de Cena (`0x210121` `SN_LockEnd` -> `ChangeScene(0)`).
6. Entrada no Canal e Lobby (`0x220111` `CQ_EnterUser` -> `0x220112` `SA_EnterUser` -> `ChangeScene(2)`).

# D187 — Wait-room slots, Room Interactions, Leader Protocol & Equipment/Shop Scenes

Descoberto por: agy (sessão 2, 2026-11-19) — RE estático somente-leitura (pefile + capstone) em `client-rebirth/Game/GameClient.dll`.

## 1. Correção de premissa: `SN_UserList (0x220233)` vs `SN_BaseUserList (0x222112)`
A task original supunha que `SN_BaseUserList (0x222112)` povoava os slots da sala. **Não povoa.**
É da família `NPlay` (início de partida) e só *atualiza* usuários que já existem na lista da sala
(lookup por nickname em `0x10070AD0`) e cria objetos de jogador (`0x1018E3A0`).
Quem povoa os slots da `Bekleme Odası` é **`NRoom_SN_UserList (0x220233)`**.

## 2. Tabela completa de dispatch `NRoom` / `NTeam` / `NUser` / `NPlay` / `NEquipment`
Offsets abaixo são relativos ao início do pacote (header Hermit de 16 bytes incluso; payload começa em `0x10`).

| Opcode | Direção | Classe / Função | Handler / Sender VA |
|---|---|---|---|
| `0x220203` | SN | `NRoom_SN_Info` (`ChangeScene(3)` + `ParseRoomInfo`) | `0x101393A0` → `0x10072640` |
| `0x220233` | SN | `NRoom_SN_UserList` (49B/usuário → slots da sala) | `0x101394F0` → `0x100720C0` |
| `0x220317` / `0x220319` | CQ / SN | `NRoom_CQ_ChangeLeader` / `SN_ChangeLeader` | `0x101381A2` / `0x101396C0` |
| `0x220311` / `0x220312` / `0x220313` | CQ / SA / SN | `NTeam_CQ_Change` / `SA_Change` / `SN_Change` (Red/Blue) | `0x1013B970` / `0x10138B80` / `0x10138CB0` |
| `0x220315` / `0x220316` | SA / SN | `NTeam_SA_ExchangeTeam` / `SN_ExchangeTeam` | `0x10138C40` / `0x10138C60` |
| `0x222101` / `0x220401` | CN / SN | `NPlay_CN_ReadyButton` (não-líder) → `NUser_SN_State` | `0x1013B6E0` / `0x10138D50` |
| **`0x222103`** | CN | **`NPlay_CN_StartButton` (`F5 Başla` do Líder da Sala!)** | **`0x1013B779`** (chamado por `0x10136960`) |
| `0x220234` / `0x220235` / `0x220236` | CQ / SA / SN | `NRoom_CQ_LeaveUser` / `SA_LeaveUser` (`ChangeScene(2)`) / `SN_LeaveUser` | `0x1013B670` / `0x101392A0` / `0x10139E40` |
| `0x220221` / `0x220222` / `0x220223` | CQ / SA / SN | `NRoom_CQ_ChangeMapInfo` / `SA_ChangeMapInfo` / `SN_ChangeMapInfo` | `0x1013B867` / `0x10139210` / `0x10139A10` |
| `0x220211` / `0x220212` / `0x220213` | CQ / SA / SN | `NRoom_CQ_ChangeBoundary` / `SA_ChangeBoundary` / `SN_ChangeBoundary` | `0x1013B8A9` / `0x10139540` / `0x101392F0` |
| `0x220215` / `0x220216` / `0x220217` | CQ / SA / SN | `NRoom_CQ_ChangeOption` / `SA_ChangeOption` / `SN_ChangeOption` | `0x1013B90E` / `0x101391F0` / `0x10139CB0` |
| `0x220218` / `0x220219` / `0x22021A` | CQ / SA / SN | `NRoom_CQ_ChangeName` / `SA_ChangeName` / `SN_ChangeName` | — / `0x101391E0` / `0x10139B90` |
| `0x240101` / `0x240102` | CQ / SA | `NEquipment_CQ_Open` / `SA_Open` (`ChangeScene(4/5/13)`) | `0x1011D610` / `0x10031770` |
| `0x240103` / `0x240104` | CQ / SA | `NEquipment_CQ_Close` / `SA_Close` (`ChangeScene(3/2)`) | `0x1011D772` / `0x10031890` |
| `0x240107` / `0x240108` | CQ / SA | `NEquipment_CQ_ChangePart` / `SA_ChangePart` | — / `0x10030F80` |
| `0x240121` / `0x240122` | CQ / SA | `TCP_CQ_ActiveItem` / `SA_ActiveItem` | — / `0x1003D880` |
| `0x240125` / `0x240126` | CQ / SA | `TCP_CQ_UseItem` / `SA_UseItem` | `0x10043C04` / `0x100420B0` |
| `0x240201` / `0x240202` | CQ / SA | `TCP_CQ_BuyItem` / `SA_BuyItem` (Gold) | `0x1011180A` / `0x10148DF0` |
| `0x240203` / `0x240204` | CQ / SA | `TCP_CQ_BuyCashItem` / `SA_BuyCashItem` (Cash) | — / `0x10149290` |
| `0x210113` | SN | `NLaunch_NLock_SN_SlotInfo` | `0x100312B0` |

## 3. `SN_Info (0x220203)` — Desbloqueio dos 8 slots por time e Team Indices
1. **Slots abertos por time (`0x1A`, payload `+10`)**:
   - `ParseRoomInfo (0x10072640)` grava `byte[0x19]` em `[room + 0]` (`cur_players`) e `byte[0x1A]` em `[room + 1]` (`max_players`) — confirmado também por `SN_ChangeBoundary (0x101392F0)`.
   - `CWaitRoomScene::UpdateSlots (0x1013DDCC)` lê `al = [room + 1]`, calcula `esi = al >> 1` (`max_players / 2`) e, se `esi < 8`, faz um loop de `esi..7` **fechando/bloqueando os slots** nas listas A e B!
   - Antes `payload[10]` estava como `1` (`1 >> 1 = 0`), bloqueando todos os 8 slots (`0..7`). Com `payload[10] = max_players` (`16`), `16 >> 1 = 8` (`jae 0x1013DF36`) mantém todos os 8 slots de cada time abertos.
2. **Team Indices (`0x6A`, `0x6C`, `0x6E`, payload `+90/+92/+94`)**:
   - Copiados para `TeamMgr(0x105169FC)+0x30` (Time A = `0`), `+0x31` (Time B = `1`), `+0x32` (Observador = `2`).

## 4. `SN_UserList (0x220233)` — Layout completo de 49 bytes (`CRoomUser::Deserialize @ 0x10071F30`)
- `0x11` (payload `+1`): `uint8 count`; entradas a partir de `0x12` (payload `+2`), stride `0x31` (49 B).

| Offset na entrada | Tipo | Destino em `CRoomUser` | Função confirmada no assembly |
|---|---|---|---|
| `+0x00` | `u16` | `+0x00` | `user_id` (chave de `SN_ChangeLeader`/`SN_State`, `0x10070AA0`) |
| **`+0x02`** | **`u32`** | **`+0x04`** | **`rank_level` (1..58)** — passado em `0x1013E236` para `0x10047470(0x17, rank)` (ícone da patente na tabela GDB `0x17`!) |
| `+0x06` | `u32` | `+0x3C` | repassado para criação do player in-game (`0x100CB8CD`) |
| **`+0x0A`** | **`u16`** | **`+0x08`** | **`team`** — deve pertencer a `{ROOM_TEAM_A, ROOM_TEAM_B, ROOM_TEAM_OBSERVER}`, senão exibe `"Missing nTeamIndex error!"` |
| **`+0x0C`** | **`u32`** | **`+0x0C`** | **`state`** (`0x1006F9F0` + tabela `0x104F5A60`): **`1` = Waiting (normal)**, **`2` = Ready (`L"ready"`)**, **`3` = Playing (`L"play"`)**, **`6 -> 4` = Shop/Inven (`L"shop"`)**. *Nota crítica:* `TeamChange_Red` (`0x101367F3`), `TeamChange_Blue` (`0x101367A3`) e `ReadyBtnClick` (`0x10136A20`) exigem `[esi + 0x0C] == 1`! |
| `+0x10` | `u32` | `+0x10` | campo auxiliar |
| `+0x14` | `u32` | `+0x40` | repassado para criação do player in-game (`0x100CB8CA`) |
| **`+0x18`** | `char[25]` | `+0x44` (`wstring`) | `nickname` — comparado ao nick do `SN_UserInfo` para identificar o jogador local |

## 5. Como o cliente identifica o Líder e dispara `F5 Başla` (`0x222103`)
- Em `CWaitRoomScene::UpdateSlots` (`0x1013E077` e `0x1013E39E`), o cliente compara `word[room + 0x60]` (definido por `SN_ChangeLeader 0x220319`) com `word[user + 0x00]`. Quando são iguais, marca `isLeader = true` e exibe a tag `0x1049C5FC` (`MASTER`/`HOST`).
- Quando o jogador clica em `F5 Başla` (`Flash_RoomScene_ReadyBtnClick @ 0x10136A60 → 0x10136960`):
  1. Busca o jogador local pelo nickname (`0x10070AD0`) e o líder pelo `room->m_wLeaderID` (`0x10070AA0`).
  2. Compara os dois nicknames (`0x10016B40`).
  3. Se o jogador local **é o líder**, chama `0x1013B760 → 0x1013B779`, que envia **`0x222103` (`NPlay_CN_StartButton`)**!
  4. Se **não é o líder** e `user->state == 1`, chama `0x1013B6E0`, que envia **`0x222101` (`NPlay_CN_ReadyButton`)**!

## 6. Abertura e Fechamento de Inventário / Loja (`0x240101..0x240104`)
- `Send_CQ_EquipOpen (0x1011D610)` envia `0x240101` com `uint32 target_mode` em `0x10` (`payload + 0`).
- `NEquipment_SA_Open (0x240102 @ 0x10031770)` lê:
  - `0x10` (`u16`): `origin = 0`
  - `0x12` (`u32`): `error_code = 0`
  - `0x16` (`u32`): `gold` → gravado em `[user + 0x80]`
  - `0x1A` (`u32`): `cash` → gravado em `[user + 0x84]`
  - `0x1E` (`u32`): `target_mode` (`1..5`):
    - `1` → `[inven + 0x64] = 0`, `ChangeScene(4)` (Inventário — Armas)
    - `2` → `[inven + 0x64] = 1`, `ChangeScene(4)` (Inventário — Personagem/Partes)
    - `3` → `[inven + 0x64] = 3`, `ChangeScene(4)` (Inventário — Itens)
    - `4` → `ChangeScene(5)` (**Loja / Shop Scene**)
    - `5` → `ChangeScene(13)` (**LuckyShop / Remodeling Scene**)
  - *(Antes `0x1E` era `0`, então `dec eax = 0xFFFFFFFF > 4` abortava sem chamar `ChangeScene`!)*
- `NEquipment_SA_Close (0x240104 @ 0x10031890)` recebe `<HI` (`0, 0`) e retorna para `ChangeScene(3)` (se estava em sala) ou `ChangeScene(2)` (Lobby).

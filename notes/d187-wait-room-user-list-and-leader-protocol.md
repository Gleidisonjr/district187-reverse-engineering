# D187 — Wait-room slots: SN_UserList, SN_ChangeLeader, SN_BaseUserList e team indices

Descoberto por: agy (sessão 2, 2026-11-19) — RE estático somente-leitura (pefile + capstone) em `client-rebirth/Game/GameClient.dll`.

## Correção de premissa
A task original supunha que `SN_BaseUserList (0x222112)` povoava os slots da sala. **Não povoa.**
É da família `NPlay` (início de partida) e só *atualiza* usuários que já existem na lista da sala
(lookup por nickname em `0x10070AD0`) e cria objetos de jogador (`0x1018E3A0`).
Quem povoa os slots da `Bekleme Odası` é **`NRoom_SN_UserList (0x220233)`**.

## Tabela de dispatch NRoom/NTeam (registro em `0x1013BF00..0x1013C520`, RTTI via vtable)
| Opcode | Classe | Handler |
|---|---|---|
| `0x220203` | `NRoom_SN_Info` | `0x101393A0` |
| `0x220233` | `NRoom_SN_UserList` | `0x101394F0` → `0x100720C0` |
| `0x220236` | `NRoom_SN_LeaveUser` | `0x10139E40` |
| `0x220319` | `NRoom_SN_ChangeLeader` | `0x101396C0` |
| `0x220401` | `NUser_SN_State` (ready etc.) | `0x10138D50` |
| `0x220313` / `0x220316` | `NTeam_SN_Change` / `SN_ExchangeTeam` | `0x10138CB0` / `0x10138C60` |
| `0x220214` | `NRoom_SN_ChangeRoomState` | `0x10139350` |
| `0x222111` / `0x222112` | `NPlay_SN_BaseRoomInfo` / `SN_BaseUserList` | `0x10138BA0` / `0x100CB7B0` |
| `0x222104` / `0x222102` | `NPlay_SN_StartButtonFail` / `ReadyButtonFail` | `0x10138C20` / `0x10138EC0` |

Offsets abaixo são relativos ao início do pacote (header de 16 bytes incluso; payload começa em `0x10`).

## SN_Info (0x220203) — team indices
`ParseRoomInfo (0x10072640)` copia `word[0x6A]`, `word[0x6C]`, `word[0x6E]` para room+6/+8/+0xA e o byte baixo
para `TeamMgr(0x105169FC)+0x30` (time A), `+0x31` (time B), `+0x32` (observador). `SN_ExchangeTeam` troca `+0x30/+0x31`.
O mock antes escrevia `map_id=10001, 100, 10` ali (rótulo errado) → times virariam `0x11/100/10`.
Agora: `ROOM_TEAM_A=0`, `ROOM_TEAM_B=1`, `ROOM_TEAM_OBSERVER=2`.

## SN_UserList (0x220233) — slots da sala
- `0x11`: `uint8 count`; entradas a partir de `0x12`, stride `0x31` (49 B); reader limitado a `0x3EE` B (~20 entradas).
- Entrada (`CRoomUser::Deserialize 0x10071F30`):

| Off | Tipo | Destino | Nota |
|---|---|---|---|
| `+0x00` | u16 | `CRoomUser+0x00` | user_id (chave de `SN_ChangeLeader`/`SN_State`, `0x10070AA0`) |
| `+0x02` | u32 | `+0x04` | desconhecido |
| `+0x06` | u32 | `+0x3C` | repassado para criação do player in-game |
| `+0x0A` | u16 | `+0x08` | **team** — deve ser um dos team indices, senão MessageBox `"Missing nTeamIndex error!"` |
| `+0x0C` | u32 | `+0x0C` | state (`SetState 0x1006F9F0`: 0,1,2,3 mantidos; 6→4, 8→5, 9→6) |
| `+0x10` | u32 | `+0x10` | desconhecido |
| `+0x14` | u32 | `+0x40` | repassado para criação do player in-game |
| `+0x18` | char[25] | `+0x44` (wide) | nickname — comparado ao nick do `SN_UserInfo` para identificar o jogador local |

## SN_ChangeLeader (0x220319)
- `0x10`: `u16 leader user_id` → `room+0x60`; `0x12`: `u32` (lido para local, 0).
- Fora da cena 7 atualiza a UI da sala (`0x1013DD80`) e imprime a string `0x18D` (mensagem de novo líder).

## SN_BaseUserList (0x222112)
- `0x11`: count; entradas a partir de `0x12`, stride `0x10E` (270 B): `+0 u16 user_id`, `+2 u16 team`, `+4 char[] nickname`.
- Usuário não encontrado → o `jne` em `0x100CB877` já foi patchado para um *code cave* (`0x10481180`) que aponta `esi`
  para um buffer estático `0x1054E140` e segue. Builder existe no mock mas **não está no fluxo** (afeta início de partida 3D,
  frente da outra sessão).

## Implementação
- [`scripts/d187-mock-server.py`](../scripts/d187-mock-server.py): `build_room_user_list_hermit`, `build_change_leader_hermit`,
  `build_base_user_list_hermit`; `CQ_CreateRoom` agora envia `SA_Create → SN_Info → SN_UserList → SN_ChangeLeader → SN_HostConnect`.
- [`scripts/test_client_handshake_smoke.py`](../scripts/test_client_handshake_smoke.py): valida layouts (team ∈ team indices,
  tamanho `0x12+n*0x31`, nick, leader == slot 0) e `F5 Başla (0x220314) → SN_HostConnect + SN_BattleStart`. Aceita porta como argumento.

## Em aberto
- Validar em tela: Gleidison no Slot 0 com coroa de líder e `F5 Başla` habilitado.
- Campos desconhecidos `+0x02/+0x06/+0x10/+0x14` (provável rank/clan/emblema).
- Como o cliente decide "eu sou líder" (provável `room+0x60` vs. id local) — não confirmado.

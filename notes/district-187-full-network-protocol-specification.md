# Especificação Técnica Completa do Protocolo de Rede — District 187: Sin Streets (326/326 Opcodes)

Descoberto e atualizado por: `agy` (2026-11-19) — Micro-interpretação da árvore de switch x86 (`0x100570D0..0x1005845D`) e varredura RTTI `CDispatch_*` em `GameClient.dll`.

---

## 1. Camada de Transporte e Enquadramento Hermit (`TheRaw.exe`)

1. **Cifra de Fluxo (Hermit Stream Cipher):**
   - Polinômio IEEE 802.3 CRC32 (`0xEDB88320`, tabela em `TheRaw.exe @ 0x00802A58`), chave base `0x0F`.
   - Os bytes `4..N-1` são cifrados com `C[i] = P[i] ^ (CRC_TABLE[i & 0xFF] & 0xFF) ^ 0x0F`, e os bytes `0..3` armazenam o `CRC32(C[4..N-1])` em Big-Endian.
2. **Cabeçalho Hermit Real de 16 Bytes (Validado em `Hermit::Session::Waiter::TCP @ 0x0050BB10`):**
   ```
   +0x00 (4B, uint32 BE): CRC32 sobre o pacote cifrado [4..Len-1]
   +0x04 (2B, uint16 BE): Sequence Number monotônico (1, 2, 3...) para pacotes de jogo (0 para 0x2008x)
   +0x06 (2B, uint16 BE): Total Packet Length (16 + tamanho do payload)
   +0x08 (4B, uint32 BE): Session ID (ex: 0x04034992)
   +0x0C (4B, uint32 BE): Packet Opcode (326 opcodes de aplicação + opcodes de transporte 0x20080..0x20090)
   +0x10 (N bytes)      : Payload binário específico do pacote (Little-Endian)
   ```

---

## 2. Sumário de Cobertura (`d187_protocol_schema.json`)

- **Total de Pacotes da Camada de Aplicação:** `326` (`100%` com opcode hexadecimal resolvido)
- **Handlers `CDispatch_*` Mapeados no Cliente (`SA`/`SN`/`NN`):** `251`
- **Rotinas Emissoras Mapeadas no Cliente (`CQ`/`CN` via `0x100570D0`):** `38`

### Distribuição por Família
| Família | Qtd. Pacotes |
|---|---|
| `NMatchup` | 118 |
| `NGuild` | 66 |
| `NHangar` | 43 |
| `NMessanger` | 23 |
| `NMailBox` | 17 |
| `NTournament` | 15 |
| `NLaunch` | 12 |
| `NAccount` | 11 |
| `NHosting` | 7 |
| `NBattle` | 6 |
| `Hanger` | 3 |
| `NAchivement` | 3 |
| `NInsperctor` | 2 |

---

## 3. Tabela Mestra dos 326 Opcodes (`0x110101` .. `0x510203`)

| Opcode | Dir | Família / Subfamília | Nome Oficial (`tPacket_*`) | Handler VA (`fn1`) / Sender VA | Classe RTTI (`CDispatch_*`) |
|---|---|---|---|---|---|
| `0x110101` | `CQ` | `NAccount/NIdentity` | `tPacket_NAccount_NIdentity_CQ_Login` | `—` | `—` |
| `0x110102` | `SA` | `NAccount/NIdentity` | `tPacket_NAccount_NIdentity_SA_Login` | `0x100d7450` | `CDispatch_NAccount_NIdentity_SA_Login` |
| `0x110111` | `CQ` | `NAccount/NIdentity` | `tPacket_NAccount_NIdentity_CQ_JoyGameLogin` | `—` | `—` |
| `0x110112` | `SA` | `NAccount/NIdentity` | `tPacket_NAccount_NIdentity_SA_JoyGameLogin` | `0x100d74a0` | `CDispatch_NAccount_NIdentity_JoyGameLogin` |
| `0x110121` | `CN` | `NAccount/NIdentity` | `tPacket_NAccount_NIdentity_CN_NetmarbleLoginData` | `—` | `—` |
| `0x110122` | `CN` | `NAccount/NIdentity` | `tPacket_NAccount_NIdentity_CN_NetmarbleLoginPCInfo` | `—` | `—` |
| `0x110123` | `SA` | `NAccount/NIdentity` | `tPacket_NAccount_NIdentity_SA_NetmarbleLogin` | `0x100d7540` | `CDispatch_NAccount_NIdentity_SA_NetmarbleLogin` |
| `0x110124` | `CQ` | `NAccount/NIdentity` | `tPacket_NAccount_NIdentity_CQ_Join` | `—` | `—` |
| `0x110125` | `SA` | `NAccount/NIdentity` | `tPacket_NAccount_NIdentity_SA_Join` | `0x10030c90` | `CDispatch_NAccount_NIdentity_SA_Join` |
| `0x110151` | `CQ` | `NAccount/NIdentity` | `tPacket_NAccount_NIdentity_CQ_MenaLogin` | `—` | `—` |
| `0x110152` | `SA` | `NAccount/NIdentity` | `tPacket_NAccount_NIdentity_SA_MenaLogin` | `0x100d74f0` | `CDispatch_NAccount_NIdentity_SA_MenaLogin` |
| `0x210101` | `SN` | `NLaunch/NLock` | `tPacket_NLaunch_NLock_SN_UserInfo` | `0x100d7a70` | `CDispatch_NLaunch_NLock_SN_UserInfo` |
| `0x210103` | `SN` | `NLaunch/NLock` | `tPacket_NLaunch_NLock_SN_Record` | `0x10031140` | `CDispatch_NLaunch_NLock_SN_Record` |
| `0x210105` | `SN` | `NLaunch/NLock` | `tPacket_NLaunch_NLock_SN_RankingInfo` | `0x10031110` | `CDispatch_NLaunch_NLock_SN_RankingInfo` |
| `0x210111` | `SN` | `NLaunch/NLock` | `tPacket_NLaunch_NLock_SN_ItemList` | `0x10031000` | `CDispatch_NLaunch_NLock_SN_ItemList` |
| `0x210113` | `SN` | `NLaunch/NLock` | `tPacket_NLaunch_NLock_SN_SlotInfo` | `0x100312b0` | `CDispatch_NLaunch_NLock_SN_SlotInfo` |
| `0x210121` | `SN` | `NLaunch/NLock` | `tPacket_NLaunch_NLock_SN_LockEnd` | `0x10032f30` | `CDispatch_NLaunch_NLock_SN_LockEnd` |
| `0x210123` | `SN` | `NLaunch/NLock` | `tPacket_NLaunch_NLock_SN_RecordMapList` | `0x10031200` | `CDispatch_NLaunch_NLock_SN_RecordMapList` |
| `0x210131` | `SN` | `NLaunch/NLock` | `tPacket_NLaunch_NLock_SN_ShotdownToYouth` | `0x10030340` | `CDispatch_NLaunch_NLock_SN_ShotdownToYouth` |
| `0x210141` | `SN` | `NLaunch/NLock` | `tPacket_NLaunch_NLock_SN_NetCafeInfo` | `0x10030cc0` | `CDispatch_NLaunch_NLock_SN_NetCafeInfo` |
| `0x210151` | `SN` | `NLaunch/NLock` | `tPacket_NLaunch_NLock_SN_ChatPunishInfo` | `0x10031730` | `CDispatch_NLaunch_NLock_SN_ChatPunishInfo` |
| `0x210152` | `SN` | `NMatchup/NUser` | `tPacket_NMatchup_NUser_SN_ChangeNickNameColor` | `0x10033520` | `CDispatch_NMatchup_NUser_SN_ChangeNickNameColor` |
| `0x210201` | `CQ` | `NLaunch/NFactory` | `tPacket_NLaunch_NFactory_CQ_CreateUser` | `—` | `—` |
| `0x210202` | `SA` | `NLaunch/NFactory` | `tPacket_NLaunch_NFactory_SA_CreateUser` | `0x10031bc0` | `CDispatch_NLaunch_NFactory_SA_CreateUser` |
| `0x220101` | `SN` | `NMatchup/NChannel` | `tPacket_NMatchup_NChannel_SN_ServerInfo` | `0x1011eb80` | `CDispatch_Channel_Hermit_SN_ServerInfo` |
| `0x220102` | `SN` | `NMatchup/NChannel` | `tPacket_NMatchup_NChannel_SN_ChannelList` | `0x100ba790` | `CDispatch_Channel_Hermit_SN_ChannelList` |
| `0x220107` | `SN` | `NMatchup/NChannel` | `tPacket_NMatchup_NChannel_SN_GroupList` | `0x100326f0` | `CDispatch_NMatchup_NChannel_SN_GroupList` |
| `0x220108` | `SN` | `NMatchup/NChannel` | `tPacket_NMatchup_NChannel_SN_ServerList` | `0x10032810` | `CDispatch_NMatchup_NChannel_SN_ServerList` |
| `0x220111` | `CQ` | `NMatchup/NChannel` | `tPacket_NMatchup_NChannel_CQ_EnterUser` | `0x10051f2e` | `—` |
| `0x220112` | `SA` | `NMatchup/NChannel` | `tPacket_NMatchup_NChannel_SA_EnterUser` | `0x100ba640` | `CDispatch_Channel_Hermit_SA_EnterUser` |
| `0x220113` | `SN` | `NMatchup/NChannel` | `tPacket_NMatchup_NChannel_SN_UserList` | `0x100ba860` | `CDispatch_Channel_Hermit_SN_UserList` |
| `0x220114` | `CQ` | `NMatchup/NChannel` | `tPacket_NMatchup_NChannel_CQ_LeaveUser` | `0x10174593` | `—` |
| `0x220115` | `SA` | `NMatchup/NChannel` | `tPacket_NMatchup_NChannel_SA_LeaveUser` | `0x100ba6a0` | `CDispatch_Channel_Hermit_SA_LeaveUser` |
| `0x220116` | `SN` | `NMatchup/NChannel` | `tPacket_NMatchup_NChannel_SN_LeaveUser` | `0x100f8fc0` | `CDispatch_TCP_NMatchup_NChannel_SN_LeaveUser` |
| `0x220121` | `CQ` | `NMatchup/NChannel` | `tPacket_NMatchup_NChannel_CQ_SearchUser` | `—` | `—` |
| `0x220122` | `SA` | `NMatchup/NChannel` | `tPacket_NMatchup_NChannel_SA_SearchUser` | `0x100d6bf0` | `CDispatch_NMatchup_NChannel_SA_SearchUser` |
| `0x220131` | `CQ` | `NMatchup/NChannel` | `tPacket_NMatchup_NChannel_CQ_AwayUser` | `—` | `—` |
| `0x220132` | `SA` | `NMatchup/NChannel` | `tPacket_NMatchup_NChannel_SA_AwayUser` | `0x100324c0` | `CDispatch_NMatchup_NChannel_SA_AwayUser` |
| `0x220151` | `CQ` | `NMatchup/NChannel` | `tPacket_NMatchup_NChannel_CQ_ViewDetailInfo` | `—` | `—` |
| `0x220152` | `SA` | `NMatchup/NChannel` | `tPacket_NMatchup_NChannel_SA_ViewDetailInfo` | `0x100313c0` | `CDispatch_NMatchup_NChannel_SA_ViewDetailInfo` |
| `0x220153` | `SN` | `NMatchup/NChannel` | `tPacket_NMatchup_NChannel_SN_ViewDetailInfo_Diary` | `0x101489c0` | `CDispatch_TCP_NChannel_SN_ViewDetailInfo_Diary` |
| `0x220154` | `SN` | `NMatchup/NChannel` | `tPacket_NMatchup_NChannel_SN_ViewDetailInfo_Progress` | `0x10148ac0` | `CDispatch_TCP_NChannel_SN_ViewDetailInfo_Progress` |
| `0x220161` | `CQ` | `NMatchup/NChannel` | `tPacket_NMatchup_NChannel_CQ_QuickJoin` | `0x10131ed2` | `—` |
| `0x220162` | `SA` | `NMatchup/NChannel` | `tPacket_NMatchup_NChannel_SA_QuickJoin` | `0x100d28a0` | `CDispatch_NMatchup_NChannel_SA_QuickJoin` |
| `0x220201` | `CQ` | `NMatchup/NRoom` | `tPacket_NMatchup_NRoom_CQ_Create` | `—` | `—` |
| `0x220202` | `SA` | `NMatchup/NRoom` | `tPacket_NMatchup_NRoom_SA_Create` | `0x10139250` | `CDispatch_NMatchup_NRoom_SA_Create` |
| `0x220203` | `SN` | `NMatchup/NRoom` | `tPacket_NMatchup_NRoom_SN_Info` | `0x101393a0` | `CDispatch_NMatchup_NRoom_SN_Info` |
| `0x220204` | `SN` | `NMatchup/NRoom` | `tPacket_NMatchup_NRoom_SN_UpdateInfoToChannelUser` | `0x100d59f0` | `CDispatch_NMatchup_NRoom_SN_UpdateInfoToChannelUser` |
| `0x220211` | `CQ` | `NMatchup/NRoom` | `tPacket_NMatchup_NRoom_CQ_ChangeBoundary` | `0x1013b8c6` | `—` |
| `0x220212` | `SA` | `NMatchup/NRoom` | `tPacket_NMatchup_NRoom_SA_ChangeBoundary` | `0x10139540` | `CDispatch_NMatchup_NRoom_SA_ChangeBoundary` |
| `0x220213` | `SN` | `NMatchup/NRoom` | `tPacket_NMatchup_NRoom_SN_ChangeBoundary` | `0x101392f0` | `CDispatch_NMatchup_NRoom_SN_ChangeBoundary` |
| `0x220215` | `CQ` | `NMatchup/NRoom` | `tPacket_NMatchup_NRoom_CQ_ChangeOption` | `0x1013b942` | `—` |
| `0x220216` | `SA` | `NMatchup/NRoom` | `tPacket_NMatchup_NRoom_SA_ChangeOption` | `0x101391f0` | `CDispatch_NMatchup_NRoom_SA_ChangeOption` |
| `0x220217` | `SN` | `NMatchup/NRoom` | `tPacket_NMatchup_NRoom_SN_ChangeOption` | `0x10139cb0` | `CDispatch_NMatchup_NRoom_SN_ChangeOption` |
| `0x220218` | `CQ` | `NMatchup/NRoom` | `tPacket_NMatchup_NRoom_CQ_ChangeName` | `—` | `—` |
| `0x220219` | `SA` | `NMatchup/NRoom` | `tPacket_NMatchup_NRoom_SA_ChangeName` | `0x101391e0` | `CDispatch_NMatchup_NRoom_SA_ChangeName` |
| `0x22021A` | `SN` | `NMatchup/NRoom` | `tPacket_NMatchup_NRoom_SN_ChangeName` | `0x10139b90` | `CDispatch_NMatchup_NRoom_SN_ChangeName` |
| `0x22021B` | `CQ` | `NMatchup/NRoom` | `tPacket_NMatchup_NRoom_CQ_ChangePassword` | `—` | `—` |
| `0x22021C` | `SA` | `NMatchup/NRoom` | `tPacket_NMatchup_NRoom_SA_ChangePassword` | `0x10139230` | `CDispatch_NMatchup_NRoom_SA_ChangePassword` |
| `0x220221` | `CQ` | `NMatchup/NRoom` | `tPacket_NMatchup_NRoom_CQ_ChangeMapInfo` | `0x1013b86c` | `—` |
| `0x220222` | `SA` | `NMatchup/NRoom` | `tPacket_NMatchup_NRoom_SA_ChangeMapInfo` | `0x10139210` | `CDispatch_NMatchup_NRoom_SA_ChangeMapInfo` |
| `0x220223` | `SN` | `NMatchup/NRoom` | `tPacket_NMatchup_NRoom_SN_ChangeMapInfo` | `0x10139a10` | `CDispatch_NMatchup_NRoom_SN_ChangeMapInfo` |
| `0x220231` | `CQ` | `NMatchup/NRoom` | `tPacket_NMatchup_NRoom_CQ_EnterUser` | `—` | `—` |
| `0x220232` | `SA` | `NMatchup/NRoom` | `tPacket_NMatchup_NRoom_SA_EnterUser` | `0x10139270` | `CDispatch_NMatchup_NRoom_SA_EnterUser` |
| `0x220233` | `SN` | `NMatchup/NRoom` | `tPacket_NMatchup_NRoom_SN_UserList` | `0x101394f0` | `CDispatch_NMatchup_NRoom_SN_UserList` |
| `0x220234` | `CQ` | `NMatchup/NRoom` | `tPacket_NMatchup_NRoom_CQ_LeaveUser` | `0x1013b6b1` | `—` |
| `0x220235` | `SA` | `NMatchup/NRoom` | `tPacket_NMatchup_NRoom_SA_LeaveUser` | `0x101392a0` | `CDispatch_NMatchup_NRoom_SA_LeaveUser` |
| `0x220236` | `SN` | `NMatchup/NRoom` | `tPacket_NMatchup_NRoom_SN_LeaveUser` | `0x10139e40` | `CDispatch_NMatchup_NRoom_SN_LeaveUser` |
| `0x220237` | `CQ` | `NMatchup/NRoom` | `tPacket_NMatchup_NRoom_CQ_CompulsionAway` | `—` | `—` |
| `0x220238` | `SA` | `NMatchup/NRoom` | `tPacket_NMatchup_NRoom_SA_CompulsionAway` | `0x10139650` | `CDispatch_NMatchup_NRoom_SA_CompulsionAway` |
| `0x220239` | `SN` | `NMatchup/NRoom` | `tPacket_NMatchup_NRoom_SN_UserColorNickInfo` | `0x10138e50` | `CDispatch_NMatchup_NRoom_SN_UserColorNickInfo` |
| `0x220311` | `CQ` | `NMatchup/NTeam` | `tPacket_NMatchup_NTeam_CQ_Change` | `0x1013b9a8` | `—` |
| `0x220312` | `SA` | `NMatchup/NTeam` | `tPacket_NMatchup_NTeam_SA_Change` | `0x10138b80` | `CDispatch_NMatchup_NTeam_SA_Change` |
| `0x220313` | `SN` | `NMatchup/NTeam` | `tPacket_NMatchup_NTeam_SN_Change` | `0x10138cb0` | `CDispatch_NMatchup_NTeam_SN_Change` |
| `0x220317` | `CQ` | `NMatchup/NTeam` | `tPacket_NMatchup_NTeam_CQ_ChangeLeader` | `0x101381a2` | `—` |
| `0x220319` | `SN` | `NMatchup/NTeam` | `tPacket_NMatchup_NTeam_SN_ChangeLeader` | `0x101396c0` | `CDispatch_NMatchup_NRoom_SN_ChangeLeader` |
| `0x22031A` | `SN` | `NMatchup/NTeam` | `tPacket_NMatchup_NTeam_SN_ChangeTeamLeader` | `0x100c1f30` | `CDispatch_TCP_NMatchup_NTeam_SN_ChangeTeamLeader` |
| `0x220401` | `SN` | `NMatchup/NUser` | `tPacket_NMatchup_NUser_SN_State` | `0x10138d50` | `CDispatch_NMatchup_NUser_SN_State` |
| `0x220411` | `SN` | `NMatchup/NUser` | `tPacket_NMatchup_NUser_SN_UserLevel` | `0x1011ae80` | `CDispatch_TCP_Result_SN_UserLevelUp` |
| `0x220412` | `SN` | `NMatchup/NUser` | `tPacket_NMatchup_NUser_SN_Record` | `0x100314d0` | `CDispatch_NMatchup_NUser_SN_Record` |
| `0x220421` | `SN` | `NMatchup/NUser` | `tPacket_NMatchup_NUser_SN_ChangeNickName` | `0x100d5850` | `CDispath_NMatchup_NUser_SN_ChangeNickName` |
| `0x220431` | `SN` | `NMatchup/NUser` | `tPacket_NMatchup_NUser_SN_ChangeTitle` | `0x100d2990` | `CDispath_NMatchup_NUser_SN_ChangeTitle` |
| `0x220501` | `NN` | `NMatchup/NChat` | `tPacket_NMatchup_NChat_NN_WaitRoom` | `0x100bbbe0` | `CDispatch_NMatchup_NChat_NN_WaitRoom` |
| `0x220502` | `NN` | `NMatchup/NChat` | `tPacket_NMatchup_NChat_NN_ChattingFail` | `0x100bbd70` | `CDispatch_NMatchup_NChat_NN_ChattingFail` |
| `0x220503` | `NN` | `NMatchup/NChat` | `tPacket_NMatchup_NChat_NN_NotBattleTeam` | `0x100bc5f0` | `CDispatch_NMatchup_NChat_NN_NotBattleTeam` |
| `0x220505` | `NN` | `NMatchup/NChat` | `tPacket_NMatchup_NChat_NN_NotBattleAll` | `0x100bc840` | `CDispatch_NMatchup_NChat_NN_NotBattleAll` |
| `0x220507` | `NN` | `NMatchup/NChat` | `tPacket_NMatchup_NChat_NN_BattleTeam` | `0x100bd090` | `CDispatch_NMatchup_NChat_NN_BattleTeam` |
| `0x220509` | `NN` | `NMatchup/NChat` | `tPacket_NMatchup_NChat_NN_BattleAll` | `0x100bce20` | `CDispatch_NMatchup_NChat_NN_BattleAll` |
| `0x220510` | `NN` | `NMatchup/NChat` | `tPacket_NMatchup_NChat_NN_BattleTeamRadio` | `0x100bd310` | `CDispatch_NMatchup_NChat_NN_BattleTeamRadio` |
| `0x220511` | `CQ` | `NMatchup/NChat` | `tPacket_NMatchup_NChat_CQ_Whisper` | `—` | `—` |
| `0x220513` | `SN` | `NMatchup/NChat` | `tPacket_NMatchup_NChat_SN_Whisper` | `0x100bbe50` | `CDispatch_NMatchup_NChat_SN_Whisper` |
| `0x220522` | `CN` | `NMatchup/NChat` | `tPacket_NMatchup_NChat_CN_DevCommand` | `—` | `—` |
| `0x220523` | `SN` | `NMatchup/NChat` | `tPacket_NMatchup_NChat_SN_DevCommandFail` | `0x1058a351` | `CDispatch_NMatchup_NChat_SN_DevCommandFail` |
| `0x220531` | `SN` | `NMatchup/NChat` | `tPacket_NMatchup_NChat_SN_ChatPunish` | `0x100334a0` | `CDispatch_NMatchup_NChat_SN_ChatPunish` |
| `0x221102` | `SA` | `NMatchup/NInvite` | `tPacket_NMatchup_NInvite_SA_UserList` | `0x101092a0` | `CDispatch_TCP_SA_UserList` |
| `0x221103` | `SN` | `NMatchup/NInvite` | `tPacket_NMatchup_NInvite_SN_UserList` | `0x10109e50` | `CDispatch_TCP_SN_UserList` |
| `0x221105` | `SN` | `NMatchup/NInvite` | `tPacket_NMatchup_NInvite_SN_Invite` | `0x1010a220` | `CDispatch_TCP_SN_Invite` |
| `0x221107` | `SN` | `NMatchup/NInvite` | `tPacket_NMatchup_NInvite_SN_Reject` | `0x10109040` | `CDispatch_TCP_SN_Reject` |
| `0x221111` | `CQ` | `NMatchup/NInvite` | `tPacket_NMatchup_NInvite_CQ_Together` | `—` | `—` |
| `0x221112` | `SA` | `NMatchup/NInvite` | `tPacket_NMatchup_NInvite_SA_Together` | `0x10033250` | `CDispatch_NMatchup_NInvite_SA_Together` |
| `0x221401` | `SN` | `NMatchup/NAdvertise` | `tPacket_NMatchup_NAdvertise_SN_Notice` | `0x100e6140` | `CDispatch_TCP_SN_Notice` |
| `0x221501` | `SN` | `NMatchup/NEvent` | `tPacket_NMatchup_NEvent_SN_MapEventInfo` | `0x10031550` | `CDispatch_NMatchup_NEvent_SN_MapEventInfo` |
| `0x221502` | `SN` | `NMatchup/NEvent` | `tPacket_NMatchup_NEvent_SN_EventMap` | `0x100316b0` | `CDispatch_NMatchup_NEvent_SN_EventMap` |
| `0x222101` | `CN` | `NMatchup/NPlay` | `tPacket_NMatchup_NPlay_CN_ReadyButton` | `0x1013b731` | `—` |
| `0x222102` | `SN` | `NMatchup/NPlay` | `tPacket_NMatchup_NPlay_SN_ReadyButtonFail` | `0x10138ec0` | `CDispatch_NMatchup_NPlay_SN_ReadyButtonFail` |
| `0x222103` | `CN` | `NMatchup/NPlay` | `tPacket_NMatchup_NPlay_CN_StartButton` | `0x1013b7af` | `—` |
| `0x222104` | `SN` | `NMatchup/NPlay` | `tPacket_NMatchup_NPlay_SN_StartButtonFail` | `0x10138c20` | `CDispatch_NMatchup_NPlay_SN_StartButtonFail` |
| `0x222111` | `SN` | `NMatchup/NPlay` | `tPacket_NMatchup_NPlay_SN_BaseRoomInfo` | `0x10138ba0` | `CDispatch_NMatchup_NPlay_SN_BaseRoomInfo` |
| `0x222112` | `SN` | `NMatchup/NPlay` | `tPacket_NMatchup_NPlay_SN_BaseUserList` | `0x100cb7b0` | `CDispatch_NMatchup_NPlay_SN_BaseUserList` |
| `0x222114` | `SN` | `NMatchup/NPlay` | `tPacket_NMatchup_NPlay_SN_BattleInfo` | `0x100ca860` | `CDispatch_NMatchup_NPlay_SN_BattleInfo` |
| `0x222121` | `SN` | `NMatchup/NPlay` | `tPacket_NMatchup_NPlay_SN_ExchangeTeam` | `0x10031480` | `CDispatch_NMatchup_NPlay_SN_ExchangeTeam` |
| `0x222122` | `SN` | `NMatchup/NPlay` | `tPacket_NMatchup_NPlay_SN_ExchangeRule` | `0x10030360` | `CDispatch_NMatchup_NPlay_SN_ExchangeRule` |
| `0x222131` | `CN` | `NMatchup/NPlay` | `tPacket_NMatchup_NPlay_CN_ExitButton` | `0x101783c0` | `—` |
| `0x222132` | `SN` | `NMatchup/NPlay` | `tPacket_NMatchup_NPlay_SN_ExitButton` | `0x10138bc0` | `CDispatch_NMatchup_NPlay_SN_ExitButton` |
| `0x222141` | `CQ` | `NMatchup/NPlay` | `tPacket_NMatchup_NPlay_CQ_ChangeWeapon` | `0x102171d3, 0x10217ee0` | `—` |
| `0x222142` | `SA` | `NMatchup/NPlay` | `tPacket_NMatchup_NPlay_SA_ChangeWeapon` | `0x100cb5c0` | `CDispatch_NMatchup_NPlay_SA_ChangeWeapon` |
| `0x222143` | `SN` | `NMatchup/NPlay` | `tPacket_NMatchup_NPlay_SN_ChangeWeapon` | `0x100ca2d0` | `CDispatch_NMatchup_NPlay_SN_ChangeWeapon` |
| `0x222151` | `CQ` | `NMatchup/NPlay` | `tPacket_NMatchup_NPlay_CQ_ItemUse` | `0x100cafd8` | `—` |
| `0x222152` | `SA` | `NMatchup/NPlay` | `tPacket_NMatchup_NPlay_SA_ItemUse` | `0x100caaa0` | `CDispatch_NMatchup_NPlay_SA_ItemUse` |
| `0x222153` | `SN` | `NMatchup/NPlay` | `tPacket_NMatchup_NPlay_SN_EndRoundPlayTime` | `—` | `—` |
| `0x222214` | `SN` | `NMatchup/NResult` | `tPacket_NMatchup_NResult_SN_UserScore` | `0x100caba0` | `CDispatch_NMatchup_NResult_SN_UserScore` |
| `0x222221` | `SN` | `NMatchup/NResult` | `tPacket_NMatchup_NResult_SN_GameFinalResult` | `0x100314b0` | `CDispatch_NMatchup_NResult_SN_GameFinalResult` |
| `0x222241` | `SN` | `NMatchup/NResult` | `tPacket_NMatchup_NResult_SN_MapEventReward` | `0x100320e0` | `CDispatch_NMatchup_NResult_SN_MapEventReward` |
| `0x222251` | `SN` | `NMatchup/NResult` | `tPacket_NMatchup_NResult_SN_PCRoomMileage` | `0x10033410` | `CDispatch_NMatchup_NResult_SN_PCRoomMileage` |
| `0x222401` | `CQ` | `NTournament/NGame` | `tPacket_NTournament_NGame_CQ_JoinTournamentList` | `0x1012508c` | `—` |
| `0x222402` | `SA` | `NTournament/NGame` | `tPacket_NTournament_NGame_SA_JoinTournamentList` | `0x10124b20` | `CTournamentPopupHandler_Dispatch_SA_JoinTournamentList` |
| `0x222403` | `SN` | `NTournament/NGame` | `tPacket_NTournament_NGame_SN_JoinTournamentList` | `0x10126eb0` | `CTournamentPopupHandler_Dispatch_SN_JoinTournamentList` |
| `0x222404` | `SN` | `NTournament/NGame` | `tPacket_NTournament_NGame_SN_JoinClannerList` | `0x1012b690` | `CTournamentPopupHandler_Dispatch_SN_JoinClannerList` |
| `0x222405` | `CQ` | `NTournament/NGame` | `tPacket_NTournament_NGame_CQ_TournamentUpdate` | `—` | `—` |
| `0x222406` | `SA` | `NTournament/NGame` | `tPacket_NTournament_NGame_SA_TournamentUpdate` | `0x10124ba0` | `CTournamentPopupHandler_Dispatch_SA_TournamentUpdate` |
| `0x222411` | `CQ` | `NTournament/NGame` | `tPacket_NTournament_NGame_CQ_ProgressTournamentList` | `0x101252bf` | `—` |
| `0x222412` | `SA` | `NTournament/NGame` | `tPacket_NTournament_NGame_SA_ProgressTournamentList` | `0x10124bc0` | `CTournamentPopupHandler_Dispatch_SA_ProgressTournamentList` |
| `0x222413` | `SN` | `NTournament/NGame` | `tPacket_NTournament_NGame_SN_ProgressTournamentList` | `0x10127830` | `CTournamentPopupHandler_Dispatch_SN_ProgressTournamentList` |
| `0x222414` | `CQ` | `NTournament/NGame` | `tPacket_NTournament_NGame_CQ_ProgressTournament` | `—` | `—` |
| `0x222415` | `SA` | `NTournament/NGame` | `tPacket_NTournament_NGame_SA_ProgressTournament` | `0x10124be0` | `CTournamentPopupHandler_Dispatch_SA_ProgressTournament` |
| `0x222416` | `SN` | `NTournament/NGame` | `tPacket_NTournament_NGame_SN_ProgressTournament` | `—` | `—` |
| `0x222421` | `SN` | `NTournament/NGame` | `tPacket_NTournament_NGame_SN_ExecuteRoomFail` | `0x10138ea0` | `CDispatch_NMatchup_NRoom_SN_TournamentExecuteRoomFail` |
| `0x222422` | `SN` | `NTournament/NGame` | `tPacket_NTournament_NGame_SN_NoticeList` | `0x10127230` | `CTournamentPopupHandler_Dispatch_SN_NoticeList` |
| `0x222423` | `SN` | `NTournament/NGame` | `tPacket_NTournament_NGame_SN_RewardList` | `0x10127440` | `CTournamentPopupHandler_Dispatch_SN_RewardList` |
| `0x223101` | `CN` | `NMatchup/NQuickMatch` | `tPacket_NMatchup_NQuickMatch_CN_RegisterMatching` | `0x100c0e41` | `—` |
| `0x223102` | `SN` | `NMatchup/NQuickMatch` | `tPacket_NMatchup_NQuickMatch_SN_RegisterMatching` | `0x100c13b0` | `CDispatch_TCP_ClanQuickMatch_SN_RegisterMatching` |
| `0x223103` | `SN` | `NMatchup/NQuickMatch` | `tPacket_NMatchup_NQuickMatch_SN_CompleteMatching` | `0x100c0a50` | `CDispatch_TCP_ClanQuickMatch_SN_CompleteMatching` |
| `0x223104` | `SN` | `NMatchup/NQuickMatch` | `tPacket_NMatchup_NQuickMatch_SN_MatchingConditionList` | `0x100c25e0` | `CDispatch_TCP_ClanQuickMatch_SN_MatchingConditionList` |
| `0x223111` | `CN` | `NMatchup/NQuickMatch` | `tPacket_NMatchup_NQuickMatch_CN_CancelMatching` | `0x100c127f, 0x100c137f` | `—` |
| `0x223112` | `SN` | `NMatchup/NQuickMatch` | `tPacket_NMatchup_NQuickMatch_SN_CancelMatching` | `0x100c1570` | `CDispatch_TCP_ClanQuickMatch_SN_CancelMatching` |
| `0x223113` | `SN` | `NMatchup/NQuickMatch` | `tPacket_NMatchup_NQuickMatch_SN_InitializeMatching` | `0x100c17c0` | `CDispatch_TCP_ClanQuickMatch_SN_InitializeMatching` |
| `0x223114` | `CN` | `NMatchup/NQuickMatch` | `tPacket_NMatchup_NQuickMatch_CN_BreakArenaRoom` | `—` | `—` |
| `0x223115` | `SN` | `NMatchup/NQuickMatch` | `tPacket_NMatchup_NQuickMatch_SN_BreakArenaRoom` | `0x100c3710` | `CDispatch_TCP_ClanQuickMatch_SN_BreakArenaRoom` |
| `0x223116` | `SN` | `NMatchup/NQuickMatch` | `tPacket_NMatchup_NQuickMatch_SN_InitializeArenaRoom` | `0x100c3830` | `CDispatch_TCP_ClanQuickMatch_SN_InitializeArenaRoom` |
| `0x223121` | `CQ` | `NMatchup/NQuickMatch` | `tPacket_NMatchup_NQuickMatch_CQ_DetailView` | `—` | `—` |
| `0x223122` | `SA` | `NMatchup/NQuickMatch` | `tPacket_NMatchup_NQuickMatch_SA_DetailView` | `0x100c0b10` | `CDispatch_TCP_ClanQuickMatch_SA_DetailView` |
| `0x223131` | `CN` | `NMatchup/NQuickMatch` | `tPacket_NMatchup_NQuickMatch_CN_ManualMatching` | `—` | `—` |
| `0x223132` | `SN` | `NMatchup/NQuickMatch` | `tPacket_NMatchup_NQuickMatch_SN_ManualMatching` | `0x100c0b60` | `CDispatch_TCP_ClanQuickMatch_SN_ManualMatching` |
| `0x223133` | `SN` | `NMatchup/NQuickMatch` | `tPacket_NMatchup_NQuickMatch_SN_ManualMatchingRequest` | `0x100c19d0` | `CDispatch_TCP_ClanQuickMatch_SN_ManualMatchingRequest` |
| `0x223134` | `CN` | `NMatchup/NQuickMatch` | `tPacket_NMatchup_NQuickMatch_CN_ManualMatchingResponse` | `0x100c0214, 0x100c109f` | `—` |
| `0x223135` | `SN` | `NMatchup/NQuickMatch` | `tPacket_NMatchup_NQuickMatch_SN_ManualMatchingResponseFail` | `0x100c0b80` | `CDispatch_TCP_ClanQuickMatch_SN_ManualMatchingResponseFail` |
| `0x230104` | `SN` | `NBattle/NGame` | `tPacket_NBattle_NGame_SN_Revive` | `0x100cb960` | `CDispatch_NBattle_NGame_SN_Revive` |
| `0x230124` | `SN` | `NBattle/NGame` | `tPacket_NBattle_NGame_SN_Kill` | `0x100ca700` | `CDispatch_NBattle_NGame_SN_Kill` |
| `0x230136` | `SN` | `NBattle/NGame` | `tPacket_NBattle_NGame_SN_Bomb` | `0x100ca610` | `CDispatch_NBattle_NGame_SN_Bomb` |
| `0x230142` | `SN` | `NBattle/NGame` | `tPacket_NBattle_NGame_SN_FlexibleCapture` | `0x100ca670` | `CDispatch_NBattle_NGame_SN_FlexibleCapture` |
| `0x230151` | `SN` | `NBattle/NGame` | `tPacket_NBattle_NGame_SN_Captin` | `0x100ca2e0` | `CDispatch_NBattle_NGame_SN_Captin` |
| `0x230162` | `SN` | `NBattle/NGame` | `tPacket_NBattle_NGame_SN_Escape` | `—` | `—` |
| `0x240101` | `CQ` | `NHangar/NEquipment` | `tPacket_NHangar_NEquipment_CQ_Open` | `0x1011d667` | `—` |
| `0x240102` | `SA` | `NHangar/NEquipment` | `tPacket_NHangar_NEquipment_SA_Open` | `0x10031770` | `CDispatch_TCP_NEquipment_SA_Open` |
| `0x240103` | `CQ` | `NHangar/NEquipment` | `tPacket_NHangar_NEquipment_CQ_Close` | `0x1011d772` | `—` |
| `0x240104` | `SA` | `NHangar/NEquipment` | `tPacket_NHangar_NEquipment_SA_Close` | `0x10031890` | `CDispatch_TCP_NEquipment_SA_Close` |
| `0x240107` | `CQ` | `NHangar/NEquipment` | `tPacket_NHangar_NEquipment_CQ_ChangePart` | `—` | `—` |
| `0x240108` | `SA` | `NHangar/NEquipment` | `tPacket_NHangar_NEquipment_SA_ChangePart` | `0x10030f80` | `CDispatch_NHangar_NEquipment_SA_ChangePart` |
| `0x240121` | `CQ` | `NHangar/NEquipment` | `tPacket_NHangar_NEquipment_CQ_ActiveItem` | `—` | `—` |
| `0x240122` | `SA` | `NHangar/NEquipment` | `tPacket_NHangar_NEquipment_SA_ActiveItem` | `0x1003d880` | `CDispatch_TCP_SA_ActiveItem` |
| `0x240123` | `CQ` | `NHangar/NEquipment` | `tPacket_NHangar_NEquipment_CQ_DeleteItem` | `0x1014a811` | `—` |
| `0x240124` | `SA` | `NHangar/NEquipment` | `tPacket_NHangar_NEquipment_SA_DeleteItem` | `0x10149170` | `CDispatch_TCP_NEquipment_SA_DeleteItem` |
| `0x240125` | `CQ` | `Hanger/NEquiment` | `tPacket_Hanger_NEquiment_CQ_UseItem` | `0x10043c04` | `—` |
| `0x240126` | `SA` | `Hanger/NEquiment` | `tPacket_Hanger_NEquiment_SA_UseItem` | `0x100420b0` | `CDispatch_TCP_SA_UseItem` |
| `0x240131` | `SN` | `Hanger/NEquiment` | `tPacket_Hanger_NEquiment_SN_PackageItem` | `0x10148b80` | `CDispatch_TCP_BuyItem` |
| `0x240161` | `CQ` | `NHangar/NEquipment` | `tPacket_NHangar_NEquipment_CQ_Unequip` | `—` | `—` |
| `0x240162` | `SA` | `NHangar/NEquipment` | `tPacket_NHangar_NEquipment_SA_Unequip` | `0x10149070` | `CDispatch_TCP_UnEquipNotify` |
| `0x240201` | `CQ` | `NHangar/NPurchase` | `tPacket_NHangar_NPurchase_CQ_Buy` | `0x1011180a` | `—` |
| `0x240202` | `SA` | `NHangar/NPurchase` | `tPacket_NHangar_NPurchase_SA_Buy` | `0x10148df0` | `CDispatch_TCP_SA_BuyItem` |
| `0x240203` | `CQ` | `NHangar/NPurchase` | `tPacket_NHangar_NPurchase_CQ_CashBuy` | `—` | `—` |
| `0x240204` | `SA` | `NHangar/NPurchase` | `tPacket_NHangar_NPurchase_SA_CashBuy` | `0x10149290` | `CDispatch_TCP_SA_BuyCashItem` |
| `0x240301` | `SN` | `NHangar/NDestroy` | `tPacket_NHangar_NDestroy_SN_LimitItemDestory` | `0x10032d90` | `CDispatch_NHangar_NDestory_SN_LimitItemDestory` |
| `0x240511` | `CQ` | `NHangar/NGift` | `tPacket_NHangar_NGift_CQ_Send` | `—` | `—` |
| `0x240512` | `SA` | `NHangar/NGift` | `tPacket_NHangar_NGift_SA_Send` | `0x10148f90` | `CDispatch_TCP_Shop_Gift_SA_Send` |
| `0x240513` | `SN` | `NHangar/NGift` | `tPacket_NHangar_NGift_SN_Send` | `0x100e4230` | `CDispatch_TCP_Gift_SN_Send` |
| `0x240601` | `ChangeNickName` | `NHangar/CQ` | `tPacket_NHangar_CQ_ChangeNickName` | `—` | `—` |
| `0x240602` | `ChangeNickName` | `NHangar/SA` | `tPacket_NHangar_SA_ChangeNickName` | `—` | `—` |
| `0x240603` | `CheckNickName` | `NHangar/CQ` | `tPacket_NHangar_CQ_CheckNickName` | `—` | `—` |
| `0x240604` | `CheckNickName` | `NHangar/SA` | `tPacket_NHangar_SA_CheckNickName` | `0x10045020` | `CDispatch_TCP_SA_CheckNickName` |
| `0x240701` | `CQ` | `NHangar/NRandomBox` | `tPacket_NHangar_NRandomBox_CQ_RewardList` | `0x10043eb4` | `—` |
| `0x240702` | `SA` | `NHangar/NRandomBox` | `tPacket_NHangar_NRandomBox_SA_RewardList` | `0x100442e0` | `CDispatch_TCP_SA_RewardList` |
| `0x240703` | `SN` | `NHangar/NRandomBox` | `tPacket_NHangar_NRandomBox_SN_RewardItem` | `0x10043f00` | `CDispatch_TCP_SN_RewardItem` |
| `0x240801` | `CQ` | `NHangar/NConvert` | `tPacket_NHangar_NConvert_CQ_MainSkinUse` | `—` | `—` |
| `0x240802` | `SA` | `NHangar/NConvert` | `tPacket_NHangar_NConvert_SA_MainSkinUse` | `0x10111b50` | `CDispatch_TCP_SA_PartItemUse` |
| `0x240901` | `CQ` | `NHangar/NMarble` | `tPacket_NHangar_NMarble_CQ_WinnerList` | `0x100c82b6` | `—` |
| `0x240902` | `SA` | `NHangar/NMarble` | `tPacket_NHangar_NMarble_SA_WinnerList` | `0x100c8700` | `CDispatch_TCP_NMarble_SA_WinnerList` |
| `0x240903` | `SN` | `NHangar/NMarble` | `tPacket_NHangar_NMarble_SN_WinnerList` | `0x100c9b10` | `CDispatch_TCP_NMarble_SN_WinnerList` |
| `0x240904` | `SN` | `NHangar/NMarble` | `tPacket_NHangar_NMarble_SN_RewardItem` | `0x100c8e50` | `CDispatch_TCP_NMarble_SN_RewardItem` |
| `0x240905` | `SN` | `NHangar/NMarble` | `tPacket_NHangar_NMarble_SN_Winner` | `0x100c9220` | `CDispatch_TCP_NMarble_SN_Winner` |
| `0x240906` | `CQ` | `NHangar/NMarble` | `tPacket_NHangar_NMarble_CQ_SelectGamble` | `0x100c8855, 0x100dae3a` | `—` |
| `0x240907` | `SA` | `NHangar/NMarble` | `tPacket_NHangar_NMarble_SA_SelectGamble` | `0x100c8720` | `CDispatch_TCP_NMarble_SA_SelectGamble` |
| `0x240908` | `CQ` | `NHangar/NMarble` | `tPacket_NHangar_NMarble_CQ_UsePointLuckyShop` | `0x100d9dd2` | `—` |
| `0x240909` | `SA` | `NHangar/NMarble` | `tPacket_NHangar_NMarble_SA_UsePointLuckyShop` | `0x100d9e70` | `CDispatch_TCP_NMarble_SA_UsePointLuckyShop` |
| `0x240910` | `CQ` | `NHangar/NMarble` | `tPacket_NHangar_NMarble_CQ_UseCashLuckyShop` | `—` | `—` |
| `0x240911` | `SA` | `NHangar/NMarble` | `tPacket_NHangar_NMarble_SA_UseCashLuckyShop` | `0x100d9f00` | `CDispatch_TCP_NMarble_SA_UseCashLuckyShop` |
| `0x240912` | `SN` | `NHangar/NMarble` | `tPacket_NHangar_NMarble_SN_LuckyRewardItem` | `0x100da620` | `CDispatch_TCP_NMarble_SN_LuckyRewardItem` |
| `0x240913` | `SN` | `NHangar/NMarble` | `tPacket_NHangar_NMarble_SN_LuckyWinnerList` | `0x100da460` | `CDispatch_TCP_NMarble_SN_LuckyWinnerList` |
| `0x240914` | `SN` | `NHangar/NMarble` | `tPacket_NHangar_NMarble_SN_LuckyWInner` | `0x100da550` | `CDispatch_TCP_NMarble_SN_LuckyWInner` |
| `0x2A0101` | `SN` | `NAchivement/NData` | `tPacket_NAchivement_NData_SN_BaseInfo` | `0x100b33a0` | `CDispatch_TCP_NAchievement_NData_SN_BaseInfo` |
| `0x2A0102` | `SN` | `NAchivement/NData` | `tPacket_NAchivement_NData_SN_Diary` | `0x100ba270` | `CDispatch_TCP_NAchievement_NData_SN_Diary` |
| `0x2A0103` | `SN` | `NAchivement/NData` | `tPacket_NAchivement_NData_SN_Progress` | `0x100b33d0` | `CDispatch_TCP_NAchievement_NData_SN_Progress` |
| `0x310201` | `SN` | `NMailBox/NMail` | `tPacket_NMailBox_NMail_SN_Info` | `0x100e0750` | `CDispatch_TCP_Note_SN_Info` |
| `0x310202` | `SN` | `NMailBox/NMail` | `tPacket_NMailBox_NMail_SN_Mail` | `0x100e50d0` | `CDispatch_TCP_SN_Mail` |
| `0x310211` | `CQ` | `NMailBox/NMail` | `tPacket_NMailBox_NMail_CQ_Send` | `—` | `—` |
| `0x310212` | `SA` | `NMailBox/NMail` | `tPacket_NMailBox_NMail_SA_Send` | `0x100e42d0` | `CDispatch_TCP_Note_SA_Send` |
| `0x310213` | `SN` | `NMailBox/NMail` | `tPacket_NMailBox_NMail_SN_Send` | `0x100e4390` | `CDispatch_TCP_Note_SN_Send` |
| `0x310214` | `CQ` | `NMailBox/NMail` | `tPacket_NMailBox_NMail_CQ_ReadTag` | `—` | `—` |
| `0x310215` | `SA` | `NMailBox/NMail` | `tPacket_NMailBox_NMail_SA_ReadTag` | `0x100e1a40` | `CDispatch_TCP_Note_SA_ReadTag` |
| `0x310216` | `CQ` | `NMailBox/NMail` | `tPacket_NMailBox_NMail_CQ_Refresh` | `—` | `—` |
| `0x310218` | `CQ` | `NMailBox/NMail` | `tPacket_NMailBox_NMail_CQ_Delete` | `—` | `—` |
| `0x310219` | `SA` | `NMailBox/NMail` | `tPacket_NMailBox_NMail_SA_Delete` | `0x100e1fc0` | `CDispatch_TCP_Note_SA_Delete` |
| `0x310301` | `SN` | `NMailBox/NGift` | `tPacket_NMailBox_NGift_SN_Info` | `0x100e0710` | `CDispatch_TCP_Gift_SN_Info` |
| `0x310302` | `SN` | `NMailBox/NGift` | `tPacket_NMailBox_NGift_SN_Gift` | `0x100e4d00` | `CDispatch_TCP_SN_Gift` |
| `0x310316` | `CQ` | `NMailBox/NGift` | `tPacket_NMailBox_NGift_CQ_ReceiveItem` | `—` | `—` |
| `0x310317` | `SA` | `NMailBox/NGift` | `tPacket_NMailBox_NGift_SA_ReceiveItem` | `0x100e4140` | `CDispatch_TCP_Gift_SA_ReceiveItem` |
| `0x310318` | `CQ` | `NMailBox/NGift` | `tPacket_NMailBox_NGift_CQ_Refresh` | `—` | `—` |
| `0x31031A` | `CQ` | `NMailBox/NGift` | `tPacket_NMailBox_NGift_CQ_Delete` | `—` | `—` |
| `0x31031B` | `SA` | `NMailBox/NGift` | `tPacket_NMailBox_NGift_SA_Delete` | `0x100e1e70` | `CDispatch_TCP_Gift_SA_Delete` |
| `0x320101` | `SN` | `NMessanger/NData` | `tPacket_NMessanger_NData_SN_FriendList` | `0x100f8f20` | `CDispatch_TCP_NMessanger_NData_SN_FriendList` |
| `0x320102` | `SN` | `NMessanger/NData` | `tPacket_NMessanger_NData_SN_NotHaveFriend` | `0x100c7420` | `CDispatch_NMessanger_NData_SN_NotHaveFriend` |
| `0x320103` | `SN` | `NMessanger/NData` | `tPacket_NMessanger_NData_SN_NotLoad` | `0x100c7430` | `CDispatch_NMessanger_NData_SN_NotLoad` |
| `0x320104` | `CN` | `NMessanger/NData` | `tPacket_NMessanger_NData_CN_Load` | `0x1016f0e3` | `—` |
| `0x320201` | `CN` | `NMessanger/NFriend` | `tPacket_NMessanger_NFriend_CN_Add` | `—` | `—` |
| `0x320202` | `SN` | `NMessanger/NFriend` | `tPacket_NMessanger_NFriend_SN_AddResult` | `0x100c7450` | `CDispatch_NMessanger_NFriend_SN_AddResult` |
| `0x320203` | `SN` | `NMessanger/NFriend` | `tPacket_NMessanger_NFriend_SN_AddRequestToTarget` | `0x100fa0f0` | `CDispatch_TCP_NMessanger_NFriend_SN_AddRequestToTarget` |
| `0x320204` | `CN` | `NMessanger/NFriend` | `tPacket_NMessanger_NFriend_CN_AddResponseFromTarget` | `—` | `—` |
| `0x320205` | `SN` | `NMessanger/NFriend` | `tPacket_NMessanger_NFriend_SN_AddResponseToTarget` | `0x100fa1e0` | `CDispatch_TCP_NMessanger_NFriend_SN_AddResponseToTarget` |
| `0x320206` | `SN` | `NMessanger/NFriend` | `tPacket_NMessanger_NFriend_SN_AddNotifyToRequester` | `0x100f9ff0` | `CDispatch_TCP_NMessanger_NFriend_SN_AddNotifyToRequester` |
| `0x320208` | `CQ` | `NMessanger/NFriend` | `tPacket_NMessanger_NFriend_CQ_Delete` | `—` | `—` |
| `0x320209` | `SA` | `NMessanger/NFriend` | `tPacket_NMessanger_NFriend_SA_Delete` | `0x100fb790` | `CDispatch_TCP_NMessanger_NFriend_SA_Delete` |
| `0x320210` | `SN` | `NMessanger/NFriend` | `tPacket_NMessanger_NFriend_SN_DeleteNotify` | `0x100fc070` | `CDispatch_TCP_NMessanger_NFriend_SN_DeleteNotify` |
| `0x320211` | `CN` | `NMessanger/NFriend` | `tPacket_NMessanger_NFriend_CN_Chat` | `—` | `—` |
| `0x320212` | `SN` | `NMessanger/NFriend` | `tPacket_NMessanger_NFriend_SN_Chat` | `0x100c7440` | `CDispatch_NMessanger_NFriend_SN_Chat` |
| `0x320213` | `SN` | `NMessanger/NFriend` | `tPacket_NMessanger_NFriend_SN_Online` | `0x100fa3a0` | `CDispatch_TCP_NMessanger_NFriend_SN_Online` |
| `0x320214` | `SN` | `NMessanger/NFriend` | `tPacket_NMessanger_NFriend_SN_Offline` | `0x100fa300` | `CDispatch_TCP_NMessanger_NFriend_SN_Offline` |
| `0x320221` | `SN` | `NMessanger/NFriend` | `tPacket_NMessanger_NFriend_SN_ChangeClanInfo` | `0x100fb9d0` | `CDispatch_TCP_NMessanger_NFriend_SN_ChangeClanInfo` |
| `0x320231` | `SN` | `NMessanger/NFriend` | `tPacket_NMessanger_NFriend_SN_ChangeNickName` | `0x100fbd40` | `CDispatch_TCP_NMessanger_NFriend_SN_ChangeNickName` |
| `0x320232` | `SN` | `NMessanger/NFriend` | `tPacket_NMessanger_NFriend_SN_ChangeLevel` | `0x100fbba0` | `CDispatch_TCP_NMessanger_NFriend_SN_ChangeLevel` |
| `0x320233` | `SN` | `NMessanger/NFriend` | `tPacket_NMessanger_NFriend_SN_ChangeColor` | `0x100fbf80` | `CDispatch_TCP_NMessanger_NFriend_SN_ChangeColor` |
| `0x320301` | `CN` | `NMessanger/NGame` | `tPacket_NMessanger_NGame_CN_Together` | `—` | `—` |
| `0x320302` | `SN` | `NMessanger/NGame` | `tPacket_NMessanger_NGame_SN_Together` | `0x10032b10` | `CDispatch_NMessanger_NGame_SN_Together` |
| `0x360102` | `SN` | `NGuild/NInit` | `tPacket_NGuild_NInit_SN_LoadFail` | `0x10030330` | `CDispath_NGuild_NInit_SN_LoadFail` |
| `0x360103` | `SN` | `NGuild/NInit` | `tPacket_NGuild_NInit_SN_NotClanner` | `0x10030d70` | `CDispatch_NGuild_NInit_SN_NotClanner` |
| `0x360105` | `SN` | `NGuild/NInit` | `tPacket_NGuild_NInit_SN_ClanServerDisconnect` | `0x10032a90` | `CDispatch_NGuild_NInit_SN_ClanServerDisconnect` |
| `0x360111` | `CQ` | `NGuild/NInit` | `tPacket_NGuild_NInit_CQ_Open` | `0x100d4c0a` | `—` |
| `0x360112` | `SA` | `NGuild/NInit` | `tPacket_NGuild_NInit_SA_Open` | `0x100d2950` | `CDispath_NGuild_NInit_SA_Open` |
| `0x360121` | `CQ` | `NGuild/NInit` | `tPacket_NGuild_NInit_CQ_Close` | `0x1015fa03` | `—` |
| `0x360122` | `SA` | `NGuild/NInit` | `tPacket_NGuild_NInit_SA_Close` | `0x100d2970` | `CDispath_NGuild_NInit_SA_Close` |
| `0x360201` | `CQ` | `NGuild/NFactory` | `tPacket_NGuild_NFactory_CQ_Search` | `—` | `—` |
| `0x360202` | `SA` | `NGuild/NFactory` | `tPacket_NGuild_NFactory_SA_Search` | `0x10163490` | `CDispatch_TCP_ClanSearch` |
| `0x360211` | `CQ` | `NGuild/NFactory` | `tPacket_NGuild_NFactory_CQ_CheckName` | `—` | `—` |
| `0x360212` | `SA` | `NGuild/NFactory` | `tPacket_NGuild_NFactory_SA_CheckName` | `0x101630b0` | `CDispatch_TCP_ClanName_Check` |
| `0x360241` | `CQ` | `NGuild/NFactory` | `tPacket_NGuild_NFactory_CQ_SignupList` | `0x1016164f, 0x1016aa85` | `—` |
| `0x360242` | `SA` | `NGuild/NFactory` | `tPacket_NGuild_NFactory_SA_SignupList` | `0x10164810` | `CDispatch_TCP_SA_SignupList` |
| `0x360251` | `CQ` | `NGuild/NFactory` | `tPacket_NGuild_NFactory_CQ_Signup` | `—` | `—` |
| `0x360252` | `SA` | `NGuild/NFactory` | `tPacket_NGuild_NFactory_SA_Signup` | `0x10161b80` | `CDispatch_TCP_SA_Signup` |
| `0x360253` | `SN` | `NGuild/NFactory` | `tPacket_NGuild_NFactory_SN_Signup` | `0x10161620` | `CDispatch_TCP_SN_SignUp` |
| `0x360261` | `CQ` | `NGuild/NFactory` | `tPacket_NGuild_NFactory_CQ_Accept` | `—` | `—` |
| `0x360262` | `SA` | `NGuild/NFactory` | `tPacket_NGuild_NFactory_SA_Accept` | `—` | `—` |
| `0x360263` | `SN` | `NGuild/NFactory` | `tPacket_NGuild_NFactory_SN_Accept` | `0x101613c0` | `CDispatch_TCP_SN_Accept` |
| `0x360264` | `SN` | `NGuild/NFactory` | `tPacket_NGuild_NFactory_SN_SignerAccept` | `0x10161c20` | `CDispatch_TCP_ClanApplyToMember_SN` |
| `0x360271` | `CQ` | `NGuild/NFactory` | `tPacket_NGuild_NFactory_CQ_Delete` | `—` | `—` |
| `0x360272` | `SA` | `NGuild/NFactory` | `tPacket_NGuild_NFactory_SA_Delete` | `0x10162170` | `CDispatch_TCP_ClanApplyReject_SA` |
| `0x360273` | `SN` | `NGuild/NFactory` | `tPacket_NGuild_NFactory_SN_Delete` | `0x10161430` | `CDispatch_TCP_SN_Delete` |
| `0x360274` | `SN` | `NGuild/NFactory` | `tPacket_NGuild_NFactory_SN_Reject` | `0x10161460` | `CDispatch_Clan_TCP_SN_Reject` |
| `0x360275` | `SN` | `NGuild/NFactory` | `tPacket_NGuild_NFactory_SN_SignerReject` | `0x10162340` | `CDispatch_TCP_ClanRejected_SN` |
| `0x360302` | `SN` | `NGuild/NData` | `tPacket_NGuild_NData_SN_ClannerList` | `0x10165840` | `CDispatch_TCP_ClanMemberInfo_SN` |
| `0x360303` | `SN` | `NGuild/NData` | `tPacket_NGuild_NData_SN_SignupList` | `0x10165530` | `CDispatch_TCP_SN_SignupList` |
| `0x360401` | `SN` | `NGuild/Nclanner` | `tPacket_NGuild_Nclanner_SN_Online` | `0x10164280` | `CDispatch_TCP_ClanOnline_SN` |
| `0x360402` | `SN` | `NGuild/NClanner` | `tPacket_NGuild_NClanner_SN_Offline` | `0x101631b0` | `CDispatch_TCP_ClanOffline_SN` |
| `0x360414` | `SN` | `NGuild/NClanner` | `tPacket_NGuild_NClanner_SN_AddClanner` | `0x101653f0` | `CDispatch_TCP_AddClanMember_SN` |
| `0x360416` | `SN` | `NGuild/NClanner` | `tPacket_NGuild_NClanner_SN_ChangeTitle` | `0x10164130` | `CDispatch_NGuild_NClanner_SN_ChangeTitle` |
| `0x360417` | `SN` | `NGuild/NClanner` | `tPacket_NGuild_NClanner_SN_ChangeColor` | `0x101640e0` | `CDispatch_NGuild_NClanner_SN_ChangeColor` |
| `0x360421` | `CQ` | `NGuild/NClanner` | `tPacket_NGuild_NClanner_CQ_Delete` | `—` | `—` |
| `0x360422` | `SA` | `NGuild/NClanner` | `tPacket_NGuild_NClanner_SA_Delete` | `0x10161490` | `CDispatch_TCP_ClanMemberDelete_SA` |
| `0x360423` | `SN` | `NGuild/NClanner` | `tPacket_NGuild_NClanner_SN_Secede` | `0x10163990` | `CDispatch_TCP_ClanSecede` |
| `0x360424` | `SN` | `NGuild/NClanner` | `tPacket_NGuild_NClanner_SN_Kick` | `0x10162bc0` | `CDispatch_TCP_ClanKick_SN` |
| `0x360461` | `SN` | `NGuild/NClanner` | `tPacket_NGuild_NClanner_SN_ClannerListInChannel` | `0x100d4eb0` | `CDispatch_Lobby_SN_ClannerListInChannel` |
| `0x360462` | `SN` | `NGuild/NClanner` | `tPacket_NGuild_NClanner_SN_ClannerListInRoom` | `0x100d5350` | `CDispatch_Lobby_SN_ClannerListInRoom` |
| `0x360463` | `SN` | `NGuild/NClanner` | `tPacket_NGuild_NClanner_SN_DeleteClannerInfoInChannel` | `0x100d5160` | `CDispatch_Lobby_SN_DeleteClannerInfoInChannel` |
| `0x360464` | `SN` | `NGuild/NClanner` | `tPacket_NGuild_NClanner_SN_DeleteClannerInfoInRoom` | `0x100d5680` | `CDispatch_Lobby_SN_DeleteClannerInfoInRoom` |
| `0x360521` | `CQ` | `NGuild/NUpdate` | `tPacket_NGuild_NUpdate_CQ_ChangeClanMarkPreCheck` | `—` | `—` |
| `0x360522` | `SA` | `NGuild/NUpdate` | `tPacket_NGuild_NUpdate_SA_ChangeClanMarkPreCheck` | `—` | `—` |
| `0x360523` | `CQ` | `NGuild/NUpdate` | `tPacket_NGuild_NUpdate_CQ_ChangeClanMark` | `—` | `—` |
| `0x360524` | `SA` | `NGuild/NUpdate` | `tPacket_NGuild_NUpdate_SA_ChangeClanMark` | `—` | `—` |
| `0x360525` | `SN` | `NGuild/NUpdate` | `tPacket_NGuild_NUpdate_SN_ChangeClanMark` | `—` | `—` |
| `0x360531` | `CQ` | `NGuild/NUpdate` | `tPacket_NGuild_NUpdate_CQ_ChangeClanNamePreCheck` | `—` | `—` |
| `0x360532` | `SA` | `NGuild/NUpdate` | `tPacket_NGuild_NUpdate_SA_ChangeClanNamePreCheck` | `—` | `—` |
| `0x360533` | `CQ` | `NGuild/NUpdate` | `tPacket_NGuild_NUpdate_CQ_ChangeClanName` | `—` | `—` |
| `0x360534` | `SA` | `NGuild/NUpdate` | `tPacket_NGuild_NUpdate_SA_ChangeClanName` | `—` | `—` |
| `0x360535` | `SN` | `NGuild/NUpdate` | `tPacket_NGuild_NUpdate_SN_ChangeClanName` | `—` | `—` |
| `0x360551` | `SN` | `NGuild/NUpdate` | `tPacket_NGuild_NUpdate_SN_ChangeNickName` | `0x10164060` | `CDispatch_NGuild_NUpdate_SN_ChangeNickName` |
| `0x360571` | `SN` | `NGuild/NUpdate` | `tPacket_NGuild_NUpdate_SN_UpdateClanLevel` | `—` | `—` |
| `0x360572` | `SN` | `NGuild/NUpdate` | `tPacket_NGuild_NUpdate_SN_ResetClanRecord` | `0x101615c0` | `CDispatch_TCP_NGuild_NUpdate_SN_ResetClanRecord` |
| `0x360712` | `SA` | `NGuild/NInvite` | `tPacket_NGuild_NInvite_SA_Invite` | `0x10162680` | `CDispatch_TCP_ClanInvite` |
| `0x360713` | `SN` | `NGuild/NInvite` | `tPacket_NGuild_NInvite_SN_InviteToUser` | `0x10162700` | `CDispatch_TCP_ClanInvite_SN` |
| `0x360714` | `CN` | `NGuild/NInvite` | `tPacket_NGuild_NInvite_CN_InviteReject` | `—` | `—` |
| `0x360715` | `SN` | `NGuild/NInvite` | `tPacket_NGuild_NInvite_SN_InviteReject` | `0x10162910` | `CDispatch_TCP_SN_InviteReject` |
| `0x360801` | `SN` | `NGuild/NBattle` | `tPacket_NGuild_NBattle_SN_ClanRecordNotify` | `—` | `—` |
| `0x360802` | `SN` | `NGuild/NBattle` | `tPacket_NGuild_NBattle_SN_ClannerRecordNotify` | `—` | `—` |
| `0x360901` | `CN` | `NGuild/NGame` | `tPacket_NGuild_NGame_CN_Invite` | `—` | `—` |
| `0x360902` | `SN` | `NGuild/NGame` | `tPacket_NGuild_NGame_SN_Invite` | `0x100c3900` | `CDispatch_TCP_ClanQuickMatch_SN_Invite` |
| `0x360903` | `SN` | `NGuild/NGame` | `tPacket_NGuild_NGame_SN_InviteFail` | `0x10138e10` | `CDispatch_NGuild_NGame_SN_InviteFail` |
| `0x360911` | `CN` | `NGuild/NGame` | `tPacket_NGuild_NGame_CN_Reject` | `—` | `—` |
| `0x360912` | `SN` | `NGuild/NGame` | `tPacket_NGuild_NGame_SN_Reject` | `—` | `—` |
| `0x360921` | `CQ` | `NGuild/NGame` | `tPacket_NGuild_NGame_CQ_Together` | `—` | `—` |
| `0x360922` | `SA` | `NGuild/NGame` | `tPacket_NGuild_NGame_SA_Together` | `0x101629f0` | `CDispatch_TCP_ClanJoin` |
| `0x420201` | `CanHostSyn` | `NHosting/NHost` | `tPacket_NHosting_NHost_CanHostSyn` | `—` | `—` |
| `0x420301` | `SN` | `NHosting/NGuest` | `tPacket_NHosting_NGuest_SN_Waiting` | `0x10138b70` | `CDispatch_NHosting_NGuest_SN_Waiting` |
| `0x420302` | `SN` | `NHosting/NGuest` | `tPacket_NHosting_NGuest_SN_HostingFail` | `0x101390c0` | `CDispatch_NHosting_NGuest_SN_HostingFail` |
| `0x420303` | `SN` | `NHosting/NGuest` | `tPacket_NHosting_NGuest_SN_HostConnect` | `0x10138ee0` | `CDispatch_NHosting_NGuest_SN_HostConnect` |
| `0x420310` | `SN` | `NHosting/NGuest` | `tPacket_NHosting_NGuest_SN_BattleStart` | `0x10138b60` | `CDispatch_NHosting_NGuest_SN_BattleStart` |
| `0x420320` | `SN` | `NHosting/NGuest` | `tPacket_NHosting_NGuest_SN_UserExit` | `0x100cb3d0` | `CDispatch_NHosting_NGuest_SN_UserExit` |
| `0x420321` | `SN` | `NHosting/NGuest` | `tPacket_NHosting_NGuest_SN_HostDisConnect` | `0x100ca850` | `CDispatch_NHosting_NGuest_SN_HostDisconnect` |
| `0x510101` | `SN` | `NInsperctor/NInit` | `tPacket_NInsperctor_NInit_SN_Login` | `0x10030d00` | `CDispatch_NInsperctor_NInit_SN_Login` |
| `0x510203` | `SN` | `NInsperctor/NChannel` | `tPacket_NInsperctor_NChannel_SN_AllNotify` | `0x10032930` | `CDispatch_NInsperctor_NChannel_SN_AllNotify` |

---

## 4. Artefatos Relacionados
- Extrator Estático: [`scripts/map_district187_protocol.py`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/scripts/map_district187_protocol.py)
- Schema JSON Completo: [`targets/district-187/data/d187_protocol_schema.json`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/targets/district-187/data/d187_protocol_schema.json)
- Protocolo de Sala & Líder: [`notes/d187-wait-room-user-list-and-leader-protocol.md`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/notes/d187-wait-room-user-list-and-leader-protocol.md)

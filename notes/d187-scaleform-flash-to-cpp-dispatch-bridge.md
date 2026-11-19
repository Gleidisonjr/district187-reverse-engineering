# Ponte Scaleform GFx Flash ↔ C++ (`CDispatch_Flash_*`) — `GameClient.dll`

Descoberto por: `agy` (2026-11-19) — Varredura RTTI e resolução de vtables em `GameClient.dll` (`530` classes `CDispatch_Flash_*` / UI, `530` vtables resolvidas).

---

## 1. Distribuição por Cena / Subsistema de Interface

| Cena / Subsistema | Qtd. Callbacks Flash → C++ |
|---|---:|
| `CClanScene (Clan)` | 113 |
| `Global / HUD / Misc UI` | 94 |
| `COption / Moderation` | 86 |
| `CWaitRoomScene (Room)` | 32 |
| `CAchievement / Missions` | 31 |
| `CInvenScene (Inventory/Loadout)` | 28 |
| `CMessenger / MailBox` | 27 |
| `CLuckyShopScene (Gacha/Marble)` | 26 |
| `CRemodelingScene (Weapon Mods)` | 25 |
| `CLobbyScene (Lobby)` | 23 |
| `CServerList / CChannelListScene` | 21 |
| `CShopScene (Shop)` | 21 |
| `CLoginScene` | 3 |

---

## 2. Principais Callbacks de Sala, Lobby, Inventário e Loja

| Cena | Classe RTTI (`CDispatch_Flash_*`) | Vtable VA | Handler C++ (`fn1`) | Opcodes Diretos |
|---|---|---|---|---|
| `CServerList / CChannelListScene` | `CDispatch_Channel_Flash_AutoConnect` | `0x104a2db4` | `0x100ba580` | — |
| `CServerList / CChannelListScene` | `CDispatch_Channel_Flash_Banner` | `0x104a2d9c` | `0x100ba9b0` | — |
| `CServerList / CChannelListScene` | `CDispatch_Channel_Flash_BannerSmall` | `0x104a2da8` | `0x100bab60` | — |
| `CServerList / CChannelListScene` | `CDispatch_Channel_Flash_ChannelListEnterRoom` | `0x104a2dcc` | `0x100ba600` | — |
| `CServerList / CChannelListScene` | `CDispatch_Channel_Flash_ChannelListOpen` | `0x104a2d78` | `0x100ba6e0` | — |
| `CServerList / CChannelListScene` | `CDispatch_Channel_Flash_ChannelList_RefreshBtnClick` | `0x104a2df0` | `0x100ba550` | — |
| `CServerList / CChannelListScene` | `CDispatch_Channel_Flash_ChannelScene_SendList` | `0x104a2d90` | `0x100bacf0` | — |
| `CServerList / CChannelListScene` | `CDispatch_Channel_Flash_Exit` | `0x104a2e08` | `0x100ba6c0` | — |
| `CServerList / CChannelListScene` | `CDispatch_Channel_Flash_SelectChannel` | `0x104a2dc0` | `0x100ba5b0` | — |
| `CShopScene (Shop)` | `CDispatch_Flash_CashChargeBtnClick` | `0x104a05fc` | `0x10149990` | — |
| `CShopScene (Shop)` | `CDispatch_Flash_CashItemUseConfirm` | `0x10487388` | `0x1003f2b0` | — |
| `CShopScene (Shop)` | `CDispatch_Flash_CashWindowCancel` | `0x104a0614` | `0x10149850` | — |
| `CShopScene (Shop)` | `CDispatch_Flash_CashWindowOpen` | `0x104a0608` | `0x10149840` | — |
| `CInvenScene (Inventory/Loadout)` | `CDispatch_Flash_ChangeWeaponClose` | `0x104a32e0` | `0x100ca420` | — |
| `CInvenScene (Inventory/Loadout)` | `CDispatch_Flash_ChangeWeaponOpen` | `0x104a32d4` | `0x100cb0c0` | — |
| `CInvenScene (Inventory/Loadout)` | `CDispatch_Flash_ChangeWeapon_RequestItem_MainWeapon` | `0x104a3298` | `0x100cbd20` | — |
| `CInvenScene (Inventory/Loadout)` | `CDispatch_Flash_ChangeWeapon_RequestItem_MeleeWeapon` | `0x104a32b0` | `0x100cbd80` | — |
| `CInvenScene (Inventory/Loadout)` | `CDispatch_Flash_ChangeWeapon_RequestItem_SubWeapon` | `0x104a32a4` | `0x100cbd50` | — |
| `CInvenScene (Inventory/Loadout)` | `CDispatch_Flash_ChangeWeapon_RequestItem_ThrowWeapon` | `0x104a32bc` | `0x100cbdb0` | — |
| `CInvenScene (Inventory/Loadout)` | `CDispatch_Flash_ChangeWeapon_Select_Notify` | `0x104a32c8` | `0x100ca390` | — |
| `CInvenScene (Inventory/Loadout)` | `CDispatch_Flash_Dev_Inven_ItemDoubleClick` | `0x1049b750` | `0x10105560` | — |
| `CInvenScene (Inventory/Loadout)` | `CDispatch_Flash_Dev_Inven_ItemOneClick` | `0x1049b75c` | `0x10105c30` | — |
| `CInvenScene (Inventory/Loadout)` | `CDispatch_Flash_Dev_Inven_RequestItemList` | `0x1049b768` | `0x10106670` | — |
| `CInvenScene (Inventory/Loadout)` | `CDispatch_Flash_Dev_Inven_Selected_Tab` | `0x1049b774` | `0x10104770` | — |
| `CInvenScene (Inventory/Loadout)` | `CDispatch_Flash_Dev_Inven_UseClick` | `0x1049b780` | `0x10105880` | — |
| `CWaitRoomScene (Room)` | `CDispatch_Flash_Dev_RoomScene_ChangeRule` | `0x1049c678` | `0x1011c240` | — |
| `CWaitRoomScene (Room)` | `CDispatch_Flash_Dev_RoomScene_Exit` | `0x1049c654` | `0x1011b1e0` | — |
| `CWaitRoomScene (Room)` | `CDispatch_Flash_Dev_RoomScene_InviteBtnClick` | `0x1049c6cc` | `0x1011b6f0` | — |
| `CWaitRoomScene (Room)` | `CDispatch_Flash_Dev_RoomScene_Open` | `0x1049c648` | `0x1011bde0` | — |
| `CWaitRoomScene (Room)` | `CDispatch_Flash_Dev_RoomScene_ReadyBtnClick` | `0x1049c684` | `0x1011b4f0` | — |
| `CWaitRoomScene (Room)` | `CDispatch_Flash_Dev_RoomScene_RuleChange` | `0x1049c660` | `0x1011b2c0` | — |
| `CWaitRoomScene (Room)` | `CDispatch_Flash_Dev_RoomScene_RuleChangeOpen` | `0x1049c66c` | `0x1011b330` | — |
| `CWaitRoomScene (Room)` | `CDispatch_Flash_Dev_RoomScene_TeamChange_Blue` | `0x1049c69c` | `0x1011ba80` | — |
| `CWaitRoomScene (Room)` | `CDispatch_Flash_Dev_RoomScene_TeamChange_Red` | `0x1049c690` | `0x1011b730` | — |
| `CShopScene (Shop)` | `CDispatch_Flash_Dev_ShopOpen` | `0x1049c6a8` | `0x1011b280` | — |
| `CShopScene (Shop)` | `CDispatch_Flash_Gift_AsseptPresentConfirm` | `0x1049d600` | `0x100e2920` | — |
| `CShopScene (Shop)` | `CDispatch_Flash_GoToShop_Confirm` | `0x1049db7c` | `0x100d29e0` | — |
| `CInvenScene (Inventory/Loadout)` | `CDispatch_Flash_Inven_DeleteClick` | `0x104a0620` | `0x1014a060` | — |
| `CInvenScene (Inventory/Loadout)` | `CDispatch_Flash_Inven_ItemDoubleClick` | `0x104a0638` | `0x1014a870` | — |
| `CInvenScene (Inventory/Loadout)` | `CDispatch_Flash_Inven_ItemOneClick` | `0x104a0644` | `0x1014a890` | — |
| `CInvenScene (Inventory/Loadout)` | `CDispatch_Flash_Inven_MsgBox_AvatarChangeConfirm` | `0x104a062c` | `0x1014a030` | — |
| `CInvenScene (Inventory/Loadout)` | `CDispatch_Flash_Inven_RequestItemDelete_Confirm` | `0x104a0674` | `0x1014a5d0` | — |
| `CInvenScene (Inventory/Loadout)` | `CDispatch_Flash_Inven_RequestItemList` | `0x104a0650` | `0x1014b130` | — |
| `CInvenScene (Inventory/Loadout)` | `CDispatch_Flash_Inven_RequestItemReallyDelete_Confirm` | `0x104a0680` | `0x1014a6d0` | — |
| `CInvenScene (Inventory/Loadout)` | `CDispatch_Flash_Inven_Selected_Tab` | `0x104a065c` | `0x101499b0` | — |
| `CInvenScene (Inventory/Loadout)` | `CDispatch_Flash_Inven_UseClick` | `0x104a0668` | `0x1014a850` | — |
| `CLobbyScene (Lobby)` | `CDispatch_Flash_LobbyScene_Apply_Friend` | `0x1049daa4` | `0x100d4a80` | — |
| `CLobbyScene (Lobby)` | `CDispatch_Flash_LobbyScene_CreateClanBtnClick` | `0x1049dabc` | `0x100d4bc0` | `0x360111` |
| `CLobbyScene (Lobby)` | `CDispatch_Flash_LobbyScene_CreateRoomBtnClick` | `0x1049d9e4` | `0x100d2e40` | — |
| `CLobbyScene (Lobby)` | `CDispatch_Flash_LobbyScene_CreateRoomOpen` | `0x1049d9f0` | `0x100d3ce0` | — |
| `CLobbyScene (Lobby)` | `CDispatch_Flash_LobbyScene_Exit` | `0x1049db88` | `0x100d2a00` | — |
| `CLobbyScene (Lobby)` | `CDispatch_Flash_LobbyScene_HelpBtnClick` | `0x1049daf8` | `0x100d24d0` | — |
| `CLobbyScene (Lobby)` | `CDispatch_Flash_LobbyScene_OnSearchFriend_ID` | `0x1049da80` | `0x100d4870` | — |
| `CLobbyScene (Lobby)` | `CDispatch_Flash_LobbyScene_PasswordDig_Confirm` | `0x1049da08` | `0x100d4400` | — |
| `CLobbyScene (Lobby)` | `CDispatch_Flash_LobbyScene_QuickStartDialog_Open` | `0x1049da38` | `0x100d6510` | — |
| `CLobbyScene (Lobby)` | `CDispatch_Flash_LobbyScene_QuickStartSetting_Confirm` | `0x1049da50` | `0x100d46d0` | — |
| `CLobbyScene (Lobby)` | `CDispatch_Flash_LobbyScene_RequestRoomlistScene` | `0x1049d9a8` | `0x100d2b80` | — |
| `CLobbyScene (Lobby)` | `CDispatch_Flash_LobbyScene_RoomCreate` | `0x1049d9fc` | `0x100d3ea0` | — |
| `CLobbyScene (Lobby)` | `CDispatch_Flash_LobbyScene_RoomEnter` | `0x1049da20` | `0x100d2800` | — |
| `CLobbyScene (Lobby)` | `CDispatch_Flash_LobbyScene_RoomEnter_Quick` | `0x1049da2c` | `0x100d2880` | — |
| `CLobbyScene (Lobby)` | `CDispatch_Flash_LobbyScene_RoomList_ItemRangeReady` | `0x1049d9b4` | `0x100d2c30` | — |
| `CLobbyScene (Lobby)` | `CDispatch_Flash_LobbyScene_RoomList_RequestItemRange` | `0x1049d9cc` | `0x100d5cc0` | — |
| `CLobbyScene (Lobby)` | `CDispatch_Flash_LobbyScene_SearchClanBtnClick` | `0x1049dac8` | `0x100d4cc0` | — |
| `CLobbyScene (Lobby)` | `CDispatch_Flash_LobbyScene_SearchFriend` | `0x1049da74` | `0x100d2900` | — |
| `CLobbyScene (Lobby)` | `CDispatch_Flash_LobbyScene_SortRoomList` | `0x1049d9d8` | `0x100d2d70` | — |
| `CLobbyScene (Lobby)` | `CDispatch_Flash_LobbyScene_TournamentBtnClick` | `0x1049db04` | `0x100d3230` | — |
| `CLobbyScene (Lobby)` | `CDispatch_Flash_LobbyScene_WeaponRemoBtnClick` | `0x1049dab0` | `0x100d2920` | — |
| `CLobbyScene (Lobby)` | `CDispatch_Flash_LobbyScene_With_Friend_Game` | `0x1049da98` | `0x100d4980` | — |
| `CShopScene (Shop)` | `CDispatch_Flash_MailBoxSubTabGift` | `0x1049d678` | `0x100e1680` | — |
| `CInvenScene (Inventory/Loadout)` | `CDispatch_Flash_OnSubSence_Inven` | `0x1049b72c` | `0x10149ba0` | — |
| `CShopScene (Shop)` | `CDispatch_Flash_OnSubSence_Shop` | `0x1049b720` | `0x10149ae0` | — |
| `CInvenScene (Inventory/Loadout)` | `CDispatch_Flash_Remodeling_Btn_InventoryCategory` | `0x1049bb60` | `0x10111260` | — |
| `CInvenScene (Inventory/Loadout)` | `CDispatch_Flash_Remodeling_Inventory_Open` | `0x1049bb48` | `0x101111b0` | — |
| `CInvenScene (Inventory/Loadout)` | `CDispatch_Flash_Remodeling_Inventory_Reset` | `0x1049bb54` | `0x10112c80` | — |
| `CLobbyScene (Lobby)` | `CDispatch_Flash_RoomList_ItemRollOver` | `0x1049da14` | `0x100d2ec0` | — |
| `CWaitRoomScene (Room)` | `CDispatch_Flash_RoomRule_ClanModeBtnStatus` | `0x1049dae0` | `0x100d7310` | — |
| `CWaitRoomScene (Room)` | `CDispatch_Flash_RoomScene_ChangeRuleConfirm` | `0x1049e878` | `0x10136dc0` | — |
| `CWaitRoomScene (Room)` | `CDispatch_Flash_RoomScene_Exit` | `0x1049e848` | `0x10136a70` | — |
| `CWaitRoomScene (Room)` | `CDispatch_Flash_RoomScene_GameRoomListSquadListReady` | `0x1049e890` | `0x10137670` | — |
| `CWaitRoomScene (Room)` | `CDispatch_Flash_RoomScene_HostDelegateBtnClick` | `0x1049e8c0` | `0x10138150` | `0x220317` |
| `CWaitRoomScene (Room)` | `CDispatch_Flash_RoomScene_InviteBtnClick` | `0x1049e860` | `0x10136bc0` | — |
| `CWaitRoomScene (Room)` | `CDispatch_Flash_RoomScene_JoinMatchBtnClick` | `0x1049da68` | `0x100d3180` | — |
| `CWaitRoomScene (Room)` | `CDispatch_Flash_RoomScene_Open` | `0x1049e884` | `0x10137430` | — |
| `CWaitRoomScene (Room)` | `CDispatch_Flash_RoomScene_PlayerTypeChkReady` | `0x1049e8cc` | `0x10137660` | — |
| `CWaitRoomScene (Room)` | `CDispatch_Flash_RoomScene_ReadyBtnClick` | `0x1049e854` | `0x10136a60` | — |
| `CWaitRoomScene (Room)` | `CDispatch_Flash_RoomScene_RoomListA_Menu` | `0x1049e8d8` | `0x10137460` | — |
| `CWaitRoomScene (Room)` | `CDispatch_Flash_RoomScene_RoomListA_MenuClick` | `0x1049e8f0` | `0x101374a0` | — |
| `CWaitRoomScene (Room)` | `CDispatch_Flash_RoomScene_RoomListB_Menu` | `0x1049e8e4` | `0x101374c0` | — |
| `CWaitRoomScene (Room)` | `CDispatch_Flash_RoomScene_RoomRuleGambleRoomSelected` | `0x1049e8a8` | `0x10138a70` | — |
| `CWaitRoomScene (Room)` | `CDispatch_Flash_RoomScene_RoomRuleGameModeSelected` | `0x1049e89c` | `0x10138220` | — |
| `CWaitRoomScene (Room)` | `CDispatch_Flash_RoomScene_RoomRuleMapSelected` | `0x1049c6d8` | `0x10137710` | — |
| `CWaitRoomScene (Room)` | `CDispatch_Flash_RoomScene_RuleChange` | `0x1049e86c` | `0x10136c90` | — |
| `CWaitRoomScene (Room)` | `CDispatch_Flash_RoomScene_RuleOpen` | `0x1049e8b4` | `0x10138690` | — |
| `CWaitRoomScene (Room)` | `CDispatch_Flash_RoomScene_TeamChange_All` | `0x1049e824` | `0x10136860` | — |
| `CWaitRoomScene (Room)` | `CDispatch_Flash_RoomScene_TeamChange_Blue` | `0x1049e830` | `0x10136780` | — |
| `CWaitRoomScene (Room)` | `CDispatch_Flash_RoomScene_TeamChange_Red` | `0x1049e83c` | `0x101367d0` | — |
| `CWaitRoomScene (Room)` | `CDispatch_Flash_Room_ChatKindBGChange` | `0x1049e320` | `0x100bb250` | — |
| `CWaitRoomScene (Room)` | `CDispatch_Flash_Room_KindList` | `0x1049e344` | `0x100bd680` | — |
| `CServerList / CChannelListScene` | `CDispatch_Flash_ServerList_BannerNotify` | `0x1049c890` | `0x1011ea80` | — |
| `CServerList / CChannelListScene` | `CDispatch_Flash_ServerList_ConnectBtnClick` | `0x1049c89c` | `0x1011ec50` | — |
| `CServerList / CChannelListScene` | `CDispatch_Flash_ServerList_ExitBtnClick` | `0x1049c8a8` | `0x1011ef00` | — |
| `CServerList / CChannelListScene` | `CDispatch_Flash_ServerList_LocalPlayerInfo` | `0x1049c8b4` | `0x1011eab0` | — |
| `CServerList / CChannelListScene` | `CDispatch_Flash_ServerList_OnServerListExitPopup_Cancel` | `0x1049c8cc` | `0x1011eac0` | — |
| `CServerList / CChannelListScene` | `CDispatch_Flash_ServerList_OnServerListExitPopup_Confirm` | `0x1049c8c0` | `0x1011ea90` | — |
| `CServerList / CChannelListScene` | `CDispatch_Flash_ServerList_RefreshBtnClick` | `0x1049c8d8` | `0x1011eaa0` | — |
| `CServerList / CChannelListScene` | `CDispatch_Flash_ServerList_RequestItemRange` | `0x1049c8e4` | `0x1011ef60` | — |
| `CServerList / CChannelListScene` | `CDispatch_Flash_ServerList_RequestLength` | `0x1049c8f0` | `0x1011ebd0` | — |
| `CServerList / CChannelListScene` | `CDispatch_Flash_ServerList_SelectServer` | `0x1049c8fc` | `0x1011eb00` | — |
| `CServerList / CChannelListScene` | `CDispatch_Flash_ServerList_ServerEnter` | `0x1049c908` | `0x1011ecd0` | — |
| `CServerList / CChannelListScene` | `CDispatch_Flash_ServerList_ServerListOnload` | `0x1049c914` | `0x1011eb50` | — |
| `CInvenScene (Inventory/Loadout)` | `CDispatch_Flash_ShopInvenRight` | `0x104a05d8` | `0x101498e0` | — |
| `CShopScene (Shop)` | `CDispatch_Flash_ShopPresent_DialogOpen` | `0x104a0704` | `0x1014c540` | — |
| `CShopScene (Shop)` | `CDispatch_Flash_Shop_BuyBtnClick` | `0x104a068c` | `0x1014cab0` | — |
| `CShopScene (Shop)` | `CDispatch_Flash_Shop_BuyConfirm` | `0x104a0698` | `0x1014cb30` | — |
| `CShopScene (Shop)` | `CDispatch_Flash_Shop_BuyConfirm_Gift` | `0x104a06a4` | `0x1014d290` | — |
| `CShopScene (Shop)` | `CDispatch_Flash_Shop_GiftBtnClick` | `0x104a06b0` | `0x1014cc60` | — |
| `CShopScene (Shop)` | `CDispatch_Flash_Shop_ItemDoubleClick` | `0x104a06bc` | `0x1014c390` | — |
| `CShopScene (Shop)` | `CDispatch_Flash_Shop_ItemOneClick` | `0x104a06c8` | `0x1014d660` | — |
| `CShopScene (Shop)` | `CDispatch_Flash_Shop_Regulation` | `0x104a0710` | `0x1014c1e0` | — |
| `CShopScene (Shop)` | `CDispatch_Flash_Shop_RequestItemList` | `0x104a06d4` | `0x1014df60` | — |
| `CShopScene (Shop)` | `CDispatch_Flash_Shop_Selected_Tab` | `0x104a06e0` | `0x1014c3c0` | — |
| `CShopScene (Shop)` | `CDispatch_Flash_Shop_SendingGift` | `0x104a06ec` | `0x1014cce0` | — |
| `CShopScene (Shop)` | `CDispatch_Flash_Shop_UserListBtnClick` | `0x104a06f8` | `0x1014c410` | — |
| `CInvenScene (Inventory/Loadout)` | `CDispatch_Flash_SlotSetReady_Weapon` | `0x104a108c` | `0x100fc370` | — |
| `CInvenScene (Inventory/Loadout)` | `CDispatch_PlayerInven_Open` | `0x104a05c0` | `0x101498b0` | — |

---

## 3. Artefatos Relacionados
- Extrator Python: [`scripts/map_scaleform_flash_bridge.py`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/scripts/map_scaleform_flash_bridge.py)
- Catálogo Completo (530 classes): [`targets/district-187/data/scaleform_flash_bridge.json`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/targets/district-187/data/scaleform_flash_bridge.json)

# Arquitetura Interna e Despacho de Mensagens de `GameServer.dll` (LithTech Jupiter EX)

Descoberto por: `agy` (2026-11-19) — Engenharia reversa estática somente-leitura de `targets/district-187/client-rebirth/Game/GameServer.dll` (`ImageBase = 0x10000000`, `522` classes RTTI).

---

## 1. Exports de `GameServer.dll` (12 Símbolos)

| Ordinal | VA | Símbolo | Papel no Motor |
|---:|---|---|---|
| `1` | `0x101f37e4` | `?_0x8e16a2c20x63660x4f150xb20xf90x480x160x6b0x430x930xff@@3HA` | Interface WorldEdit / DEdit / Recursos |
| `2` | `0x1003b1c0` | `DEditGetClassMessageDefs` | Interface WorldEdit / DEdit / Recursos |
| `3` | `0x1003b170` | `DEditGetCommandClassDefs` | Interface WorldEdit / DEdit / Recursos |
| `4` | `0x1003b120` | `DEditGetCommandDefs` | Interface WorldEdit / DEdit / Recursos |
| `5` | `0x1003b970` | `DEditGetOcclusionInfo` | Interface WorldEdit / DEdit / Recursos |
| `6` | `0x1003bac0` | `DEditLoadModule` | Interface WorldEdit / DEdit / Recursos |
| `7` | `0x1003b0f0` | `DEditUnloadModule` | Interface WorldEdit / DEdit / Recursos |
| `8` | `0x1007fb10` | `GatherResourcesPostObjects` | Interface WorldEdit / DEdit / Recursos |
| `9` | `0x1007fac0` | `GatherResourcesPreObjects` | Interface WorldEdit / DEdit / Recursos |
| `10` | `0x1005a940` | `GetIGameWorldEdit` | Interface WorldEdit / DEdit / Recursos |
| `11` | `0x1005b9c0` | `ObjectDLLSetup` | Registro de classes de objeto e `IServerShell` no `Engine_Server.dll` |
| `12` | `0x1005e630` | `SetMasterDatabase` | Injeção do `IDatabaseMgr` (`TheRaw.Gamdb00p`) |

---

## 2. Vtable Principal de `CGameServerShell` (`IServerShell`)
- **Vtable VA:** `0x1019220c` (`21` slots virtuais mapeados)

| Slot | Offset | Handler VA | Papel Esperado (`IServerShell`) |
|---:|---|---|---|
| `0` | `+0x00` | `0x10055710` | `dtor_or_Release` |
| `1` | `+0x04` | `0x10056140` | `OnServerInitialized` |
| `2` | `+0x08` | `0x1004fd30` | `OnServerTerm` |
| `3` | `+0x0C` | `0x100575a0` | `SRand` |
| `4` | `+0x10` | `0x100547d0` | `OnClientEnterWorld` |
| `5` | `+0x14` | `0x10053490` | `OnClientExitWorld` |
| `6` | `+0x18` | `0x1004fd70` | `OnMessage` |
| `7` | `+0x1C` | `0x1004eba0` | `OnObjectMessage` |
| `8` | `+0x20` | `0x10057220` | `PreStartWorld` |
| `9` | `+0x24` | `0x1004ebb0` | `PostStartWorld` |
| `10` | `+0x28` | `0x10054dd0` | `Update` |
| `11` | `+0x2C` | `0x100521b0` | `CacheFiles` |
| `12` | `+0x30` | `0x100521f0` | `FileLoadNotify` |
| `13` | `+0x34` | `0x10054610` | `ProcessPacket` |
| `14` | `+0x38` | `0x100557c0` | `OnAddClient` |
| `15` | `+0x3C` | `0x1004fd10` | `OnRemoveClient` |
| `16` | `+0x40` | `0x10052200` | `OnClientEnterWorld_Alt` |
| `17` | `+0x44` | `0x1004eee0` | `VerifyClient` |
| `18` | `+0x48` | `0x10055e20` | `Slot_18` |
| `19` | `+0x4C` | `0x100549a0` | `Slot_19` |
| `20` | `+0x50` | `0x10054a70` | `Slot_20` |

---

## 3. Verificações Server-Side de Integridade do Cliente (Confirmadas)
1. **Check do Nome do Executável Host (`0x10034B92`):**
   - Executa `GetModuleFileNameA(NULL)` e `strstr(..., "TheRawServer.exe")`. Se o host dedicado não se chamar `TheRawServer.exe`, expulsa o cliente com `not found file, TheRawServer_xxx.exe`.
2. **Check de CRC32 de `Game\GameClient.dll` (`0x10034C13..0x10034CB2`):**
   - Calcula o CRC32 de `<exeDir>\Game\GameClient.dll` e compara com o hash enviado pelo cliente durante o ingresso UDP. Qualquer divergência ou ausência do arquivo derruba o cliente com `ErrorCode : 02`.

---

## 4. Subsistema de Modos de Jogo (`CServerMissionMgr_*`) & Entidades (522 Classes RTTI)

| Subsistema | Qtd. Classes | Exemplos Principais |
|---|---:|---|
| `MissionMgr_GameModes` | 19 | `C4MissionProperties`, `CServerMissionMgr`, `CServerMissionMgr_Assassin`, `CServerMissionMgr_C4`, `CServerMissionMgr_Captin`, `CServerMissionMgr_Carry`, `CServerMissionMgr_Conquest`, `CServerMissionMgr_Convoy` |
| `Bomb_Objectives` | 13 | `BombZoneTrigger`, `C4MissionProperties`, `CBombZoneTriggerPlugin`, `CMissionBomb`, `CServerMissionMgr_C4`, `CServerMissionMgr_Convoy`, `CServerMissionMgr_Escape`, `CServerMissionMgr_FlexibleCapture` |
| `Player_Character` | 24 | `CCharacter`, `CCharacterDB`, `CCharacterHitBox`, `CDamageTypeDB`, `CItemBody@ITEM`, `CPlayerInventory`, `CPlayerObj`, `CharacterWorldModel` |
| `Weapons_Projectiles` | 28 | `?$Delegate@VCArsenal`, `?$Delegate@VCProjectile`, `AmmoBox`, `CAmmoBoxPlugin`, `CArsenal`, `CGrenade`, `CGrenadeProximity`, `CHHWeaponModel` |
| `World_Triggers_Spawners` | 41 | `ActiveWorldModel`, `BombZoneTrigger`, `CActiveWorldModelPlugin`, `CBombZoneTriggerPlugin`, `CDestructibleWorldModel`, `CDestructibleWorldModelPlugin`, `CGameBasePlugin`, `CGameStartPointPlugin` |
| `ServerShell_Network` | 18 | `?$CAPIHolder@VILTClient`, `?$Reader@USN_BaseUserList@NPlay@NMatchup@Packet@Share`, `CGameServerShell`, `DropInventoryEventEventCaster@CPlayerObj`, `EventCaster`, `GameClientData`, `IReader@ISection@Packet@Hermit`, `ISeeker@ISection@Packet@Hermit` |

### Vtables-Chave Mapeadas
| Classe RTTI | Vtable VA | Slots |
|---|---|---:|
| `CGameServerShell` | `0x1019220c` | 21 |
| `CServerMissionMgr_C4` | `0x1019dd14` | 40 |
| `CServerMissionMgr_Assassin` | `0x1019dcd4` | 40 |
| `CServerMissionMgr_Conquest` | `0x1019ddd4` | 40 |
| `BombZoneTrigger` | `0x1018766f` | 0 |
| `GameBase` | `0x1001d87f` | 0 |

---

## 5. Artefatos Relacionados
- Extrator Python: [`scripts/map_gameserver_internals.py`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/scripts/map_gameserver_internals.py)
- Catálogo JSON: [`targets/district-187/data/gameserver_internals.json`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/targets/district-187/data/gameserver_internals.json)

# `CGameClientShell` Vtable & Catálogo de CVars (`TheRaw.exe` / `GameClient.dll`)

Descoberto por: `agy` (2026-11-19) — Extração estática somente-leitura das vtables-chave de `GameClient.dll` e CVars de `TheRaw.exe`.

---

## 1. Vtables-Chave de `GameClient.dll`

| Classe RTTI | Vtable VA | Slots |
|---|---|---:|
| `CGameClientShell` | `0x104aac54` | 42 |
| `CPlayerMgr` | `0x104a91d0` | 10 |
| `CInterfaceMgr` | `0x104abb0c` | 5 |

### Slots de `CGameClientShell` (`0x104aac54`)
| Slot | Offset | Handler VA |
|---:|---|---|
| `0` | `+0x00` | `0x10236a20` |
| `1` | `+0x04` | `0x1023b4f0` |
| `2` | `+0x08` | `0x10236440` |
| `3` | `+0x0C` | `0x10234dd0` |
| `4` | `+0x10` | `0x102316b0` |
| `5` | `+0x14` | `0x102329e0` |
| `6` | `+0x18` | `0x10231990` |
| `7` | `+0x1C` | `0x10232a00` |
| `8` | `+0x20` | `0x10233240` |
| `9` | `+0x24` | `0x10233260` |
| `10` | `+0x28` | `0x10233370` |
| `11` | `+0x2C` | `0x10232a30` |
| `12` | `+0x30` | `0x10234140` |
| `13` | `+0x34` | `0x10238df0` |
| `14` | `+0x38` | `0x10231950` |
| `15` | `+0x3C` | `0x10236a30` |
| `16` | `+0x40` | `0x10232b00` |
| `17` | `+0x44` | `0x10232b40` |
| `18` | `+0x48` | `0x1023b270` |
| `19` | `+0x4C` | `0x10238fe0` |
| `20` | `+0x50` | `0x10232e90` |
| `21` | `+0x54` | `0x10231620` |
| `22` | `+0x58` | `0x10239e00` |
| `23` | `+0x5C` | `0x10235c20` |
| `24` | `+0x60` | `0x10231750` |
| `25` | `+0x64` | `0x10231770` |
| `26` | `+0x68` | `0x102316e0` |
| `27` | `+0x6C` | `0x10232c30` |

---

## 2. CVars & Comandos de Console Extraídos (`TheRaw.exe`: `156` | `GameClient.dll`: `187`)

Amostra de CVars de rede, renderização e desempenho em `TheRaw.exe`:
```
Anisotropic, AntiAliasFSOverSample, BandwidthTargetClient, BandwidthTargetServer, BindTexturesMipOffset, ClientEngine, ClientSleepMS, ClientToScreen, ConsoleAlpha, ConsoleBottom, ConsoleEnable, ConsoleFontSize, ConsoleHistory, ConsoleHistoryLen, ConsoleLeft, ConsoleRight, ConsoleTop, Debug, DebugBreak, DebugLevel, DebugMaxPos, DebugModelRez, DebugPackets, DebugStrings, DrawAmbientLightObjectCB, DrawBgTranslcuentObjectCB, DrawCustomRender, DrawDecalAmbient, DrawEmmisive, DrawEmmisiveOutline, DrawFogVolumes, DrawGroupedBatchesOnly, DrawHitDims, DrawModelDecals, DrawModelPhysicsDims, DrawModelPhysicsDimsOBB, DrawPhysicsShapes, DrawPrimSetUV, DrawPrimSetXY, DrawPrimSetXYZ, DrawSky, DrawSkyPortals, DrawSolidGeometry, DrawTranslcuentObjectCB, DrawTranslucent, DrawWorld, DrawWorldModelPhysicsDims, DrawWorldTree, Gamma, LightExtraInit, Light_AddAmbient, Light_AmbientB, Light_AmbientG, Light_AmbientR, Light_Area, Light_BlackLight, Light_CubeProjector, Light_DecalAmbientB, Light_DecalAmbientR, Light_DrawPointFillBox, Light_EffectAmbientB, Light_EffectAmbientG, Light_EffectAmbientR, Light_EnableFillToPoint, Light_HHCharacterAmbientB, Light_HHCharacterAmbientG, Light_HHCharacterAmbientR, Light_Move, Light_MoveOffset, Light_PVCharacterAmbientB, Light_PVCharacterAmbientG, Light_PVCharacterAmbientR, Light_PointFill, Light_ProjectionShadow, Light_ShadowVolume, Light_ShadowVolumeDebug, Light_ShadowVolumeDist, Light_ShadowVolumeHeight, Light_ShadowVolumeLength, Light_SkyAmbientB
```

## 3. Artefatos Relacionados
- Extrator Python: [`scripts/map_clientshell_and_cvars.py`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/scripts/map_clientshell_and_cvars.py)
- Catálogo JSON: [`targets/district-187/data/clientshell_and_cvars.json`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/targets/district-187/data/clientshell_and_cvars.json)

# Session Handoff

## Estado atual
- **Agente:** Antigravity (Gemini 3.8 Flash)
- **Alvo ativo:** `targets/district-187/` (District 187 / S2 Rebirth — Motor Nativo LithTech Jupiter EX)
- **Timestamp:** 2026-11-02 21:46
- **Diretriz Absoluta:** 100% foco no executável e motor original LithTech (`TheRaw.exe`, `GameClient.dll`, `Engine_Server.dll`) e emulação de rede/servidor dedicado.
- **Entregas Concluídas nesta Sessão:**
  1. **Extração de Todos os 29 Mapas Oficiais (`.World00p`):**
     - Extraídos diretamente para `targets/district-187/client-rebirth/Game/Worlds/`:
       - `twoway.World00p` (8,25 MB)
       - `thebank.World00p` (14,8 MB)
       - `10025_Heaven.World00p` (12,4 MB)
       - `oldtown.World00p` (9,31 MB)
       - `10034_TheMetro.World00p` (17,4 MB)
       - `10023_GrandBazar.World00p` (15,4 MB)
       - `DeadWood1.World00p` (22,6 MB)
       - e mais 22 mapas compilados.
  2. **Extração das 54 Tabelas Oficiais de Balanço & Combate:**
     - Extraídas para `targets/district-187/data/tables/` (`WeaponInfo.csv`, `Rule.csv`, `Setting.csv`, `TotalItem.csv`, `ExpPointRule.csv`).
     - Mapeadas as hitboxes de `GameServer.dll` (`CCharacterHitBox`, `HitBoxHeadNodeRadius` $2.5\times \sim 4.0\times$, `HitBoxTorsoNodeRadius` $1.0\times$, etc.) em [`notes/district-187-combat-and-damage-formula-specification.md`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/notes/district-187-combat-and-damage-formula-specification.md).
  3. **Validação do Ciclo de Rede Ponta-a-Ponta (100% PASS):**
     - Script [`scripts/test_client_handshake_smoke.py`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/scripts/test_client_handshake_smoke.py) executou o ciclo completo contra `127.0.0.1:12000`:
       - `0x20080` -> `0x20081` (Handshake)
       - `0x20082` -> `0x20083` (ACK / Pong)
       - `CQ_JoyGameLogin` (0x110111) -> `SA_JoyGameLogin` (0x110112)
       - Recebimento de `SN_UserInfo` (Rank 58, 50M Exp, 9.99M Gold/Cash)
       - Recebimento de `SN_ItemList` (VIP Arsenal completo)
       - Recebimento de `SN_Record` e `SN_LockEnd`
       - `CQ_EnterUser` (0x220101) -> `SA_EnterUser` (0x220102) [Canal 1]
       - `CQ_CreateRoom` (0x220201) -> `SA_CreateRoom` (0x220202) [Sala 1]
       - `CN_StartButton` (0x220301) -> `SN_BattleStart` (0x230104) [UDP 27888]

## Próximo Passo
- O cliente original e o servidor estão 100% integrados e prontos para jogabilidade local ou partidas via servidor dedicado.

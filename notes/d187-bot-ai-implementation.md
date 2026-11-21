# District 187 — Bot AI Implementation: PS_ALIVE, Character Models, Gameplay Loop & /bots IPC

**Data:** 2026-11-20  
**Alvo:** `targets/district-187/client-rebirth/` (`TheRaw.exe`, `GameClient.dll`, `d187_dedicated_gateway.py`)  
**Scripts modificados:** [`scripts/d187_dedicated_gateway.py`](../scripts/d187_dedicated_gateway.py), [`scripts/d187_lobby_extensions.py`](../scripts/d187_lobby_extensions.py)  
**Ferramenta:** Análise estática de `GameClient.dll` + RE de `d187-black-screen-loading-scene-and-render3d-analysis.md`

---

## 1. O Que Foi Descoberto

### 1.1 Correção Crítica: MID_PLAYER_STATE_CHANGE é `0x67`, NÃO `0x60`

A instrução da tarefa dizia `MID 0x60` com `PS_ALIVE=0`. Isso é a visão do **servidor** (`CPlayerObj::m_eState` no `GameServer.dll`). O MID real enviado ao cliente via UDP é **`0x67`** (103 decimal).

**Evidência em `GameClient.dll`:**
- Handler registrado em `0x10027468` para MID `0x67`.
- Roteia para `CPlayerMgr::HandleMsgPlayerStateChange` (`0x1021D8F0`).
- Payload: 1 byte com enum **`ePlayerState` do lado do cliente**:
  - `1` = `Alive`, `2` = `Dying_Start`, `3` = `Dying_Stage2`, `4` = `Dead`, `5` = `Spectator`
- Verificado também em `d187-black-screen-loading-scene-and-render3d-analysis.md` §2.2 condição 5: `g_pPlayerMgr->m_ePlayerState != 0` é gate para `CInGameLoadingHandler::Update` fechar a tela de carregamento.

### 1.2 Gates de Render 3D que PS_ALIVE desbloqueia

`CGameClientShell::Render (0x10234F60)` só chama `RenderCamera()` se:
1. `HUD::CUserInfo::GetMyInfo() != NULL`
2. `g_pIntroFlash->m_bPlaying == 0`
3. `g_pPlayerMgr->IsPlayerInWorld() == 1`

`CInGameLoadingHandler::Update (0x1016D520)` exige, além dos acima:
- `g_pPlayerMgr->m_ePlayerState != 0` — settado pelo MID `0x67` com `state=1`
- `g_pPlayerMgr->m_pMoveMgr->m_pCharFX != NULL` — criado quando `CCharacterFX` do jogador local recebe `m_hServerObject == g_pLTClient->GetClientObject()`

### 1.3 Formato dos Pacotes Implementados

| Pacote | Opcode Gateway | Formato (LE) | Propósito |
|---|---|---|---|
| `SN_Spawn` | `0x31` | `BB I B H fff + NetClientData(0xD8)` | Spaw bot + envia NetClientData |
| `MID_PS_ALIVE` | `0x67` | `BB BB` = `{0x67, seq, bot_id, 0x01}` | Seta ePlayerState=Alive no cliente |
| `SN_Move` | `0x32` | `BB I fff H` | Posição + HP |
| `SN_Fire` | `0x41` | `BB II H I` | Ataque direcional |
| `SN_Hit` | `0x42` | `BB II HH B` | Dano aplicado |
| `SN_Kill` | `0x43` | `BB II H B` | Kill confirmado |
| `MID_PS_DEAD` | `0x67` | `BB BB` = `{0x67, seq, bot_id, 0x04}` | Seta ePlayerState=Dead |

**`build_mid_player_state_packet(seq, player_id, state)`** — função helper adicionada em `d187_dedicated_gateway.py` (linha ~86).

### 1.4 NetClientData dos Bots (0xD8 bytes)

Formato verificado em `GameServer.dll CPlayerObj::PreCreate (0x1007B800)` e `ClientData::GetBaseModel (0x1004D020)`:

```
+0x00 (4B): bot_id (uint32 LE)
+0x04 (4B): team index (uint32 LE)
+0x08 (25B): nickname (null-padded)
+0x38 (5B): team string ('SWAT\0' ou 'GANG\0')
+0x6C + teamIdx*0x48 (4B): avatar HRECORD
  HRECORD == 0 -> fallback engine\default.Model00p
  HRECORD != 0 -> resolve ModelFile via ModelsDB (0x1010C1E0)
```

**Status dos modelos:** `HRECORD = 0` enviado por ora, resultando em `engine\default.Model00p`. Ver §4 abaixo para o que falta.

---

## 2. Máquina de Estados dos Bots

```
SPAWN ──────────────────────────────────────────────────┐
  │  SN_Spawn + NetClientData                           │
  │  MID_PS_ALIVE (0x67, state=1)                       │ RESPAWN_WAIT
  ▼                                                     │  (após BOT_RESPAWN_DELAY_S=3s)
MOVE ──────── distância <= BOT_WEAPON_RANGE ──────► ENGAGE
  │  SN_Move (10Hz)                                     │  SN_Fire + SN_Hit + SN_Move
  │                                                     │  se victim HP==0:
  │◄────────── distância > BOT_WEAPON_RANGE ────────────┤    SN_Kill
                                                        │    MID_PS_DEAD (0x67, state=4)
                                                        ▼
                                                       DEAD
                                                        │  aguarda 3 segundos
                                                        ▼
                                                   RESPAWN_WAIT ──────────────────► loop
```

**Detalhe:** `RESPAWN_WAIT` retorna ao waypoint de spawn do time (`team_spawns[team][i % len(candidates)]`) e reenvia `SN_Spawn + MID_PS_ALIVE` antes de transicionar para `MOVE`.

---

## 3. Como `/bots N` Conecta ao Gateway

**Mecanismo: arquivo IPC `targets/district-187/data/bots_ipc.json`**

1. `d187_lobby_extensions.py` — `process_chat_command("/bots 4")`:
   - Atualiza `self.bot_count = 4`
   - Chama `_write_bots_ipc(4, "twoway", "adaptive")` → escreve `bots_ipc.json`

2. `d187_dedicated_gateway.py` — loop principal (`DedicatedUDPGateway.run()`):
   - A cada 1 segundo chama `_check_bots_ipc()`
   - Detecta mudança via `os.path.getmtime(BOTS_IPC_PATH)`
   - Se `map_name` mudou: recria `NavMeshBotDirector` inteiro
   - Se só `bot_count` mudou: chama `bot_director.set_bot_count(N)`
     - Adiciona novos bots (com `state=SPAWN`) ou remove os últimos

3. Mesmo mecanismo funciona para `/map <nome>` — atualiza `bots_ipc.json` com `map_name`.

**Formato do arquivo IPC:**
```json
{"bot_count": 8, "map_name": "twoway", "difficulty": "adaptive"}
```

---

## 4. O que Ainda Falta para Modelos de Personagem Reais

O `engine\default.Model00p` (caixa cinza) persiste porque `HRECORD == 0` em `NetClientData + 0x6C + teamIdx * 0x48`.

Para corrigir, são necessários **dois passos**:

### Passo A — Extrair o HRECORD correto do GADB (`TheRaw.Gamdb00p`)

O `ClientData::GetBaseModel (0x1004D020)` chama `ModelsDB::GetModelFilename(hModel)` (`0x1010C1E0`). `hModel` é um `HRECORD` (handle de record do GameDatabase). O GADB contém tabelas de `Characters` com atributo `BaseModel` → `ModelFile`.

**Script disponível:** `scripts/inspect_gamdb00p.py` — já disseca o formato GADB v3. Executar sobre `TheRaw.Gamdb00p` para listar todos os records de personagem e seus `ModelFile`:

```python
# Exemplo esperado de output:
# Record 0x002A: BaseModel="characters\player\male\swat_assault" ModelFile="..."
# Record 0x002B: BaseModel="characters\player\male\gang_grunt"   ModelFile="..."
```

### Passo B — Enviar o HRECORD correto no NetClientData do lobby

Em `scripts/d187-mock-server.py`, na construção de `SN_UserInfo (0x210101)` ou nos dados de personagem enviados no handshake, preencher:

```python
# No NetClientData do bot (ou do jogador humano):
struct.pack_into("<I", ncd_buf, 0x6C + team_idx * 0x48, hrecord_id)
```

Onde `hrecord_id` é o valor extraído do GADB para o personagem correto do time.

### Caminhos de modelos esperados (hipotéticos até extração confirmada)

```
characters\player\male\swat_assault.Model00p    (SWAT team)
characters\player\male\gang_grunt.Model00p      (Gangster team)
```

Esses caminhos existem dentro dos pacotes `.Res00`/`.ResDt`. O script `scripts/extract_resdt.py` pode extraí-los para `client-rebirth/Game/characters/`.

---

## 5. Limitações

- **MID `0x67` via gateway Python**: O gateway Python (porta 27888) opera sobre UDP raw, NÃO sobre o protocolo LithTech Jupiter EX real (`Engine_Server.dll`). Quando o cliente conectar ao `TheRawServer.exe` nativo (compilado de `d187_server_host.cpp`), o `GameServer.dll` é quem enviará `MID_PLAYER_STATE_CHANGE` internamente via `CPlayerObj::Respawn (0x1007C350)`. O gateway Python é relevante apenas no modo autônomo (sem `TheRawServer.exe`).
- **PS_ALIVE em bots vs jogador humano**: O MID `0x67` enviado pelo gateway afeta apenas o estado de render do **jogador local**. Bots aparecem como `CCharacterFX` (objeto de rede), não como `CPlayerMgr`. O render de bots depende do `m_hServerObject` correto vindo do `Engine_Server.dll`.
- **IPC por arquivo**: O mecanismo de IPC (`bots_ipc.json`) funciona apenas localmente (mesmo disco). Em uma sessão multiplayer real, seria necessário um socket ou pipe nomeado.

---

## 6. Próximos Passos

1. Executar `scripts/inspect_gamdb00p.py` sobre `TheRaw.Gamdb00p` para listar HRECORDs dos personagens.
2. Em `scripts/d187-mock-server.py`, preencher `NetClientData + 0x6C + teamIdx * 0x48` com o HRECORD correto do GADB → modelos reais no servidor nativo.
3. Verificar `d187_server_host.cpp` §5 (Correção `worldName` sem `.World00p`) e compilar `TheRawServer.exe` para testar PS_ALIVE com o servidor LithTech nativo.
4. Testar `/bots N` em sessão real: iniciar `d187_dedicated_gateway.py`, depois emitir `/bots 4` via chat in-game, verificar que o gateway loga `[IPC] Bot count changed`.

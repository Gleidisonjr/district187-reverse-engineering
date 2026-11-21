# District 187: Shop/Inventory System, Progression & Post-Match Results Implementation

> **Data:** 2026-11-20
> **Alvo:** `targets/district-187/` — `scripts/d187-mock-server.py`
> **Scripts modificados:** [`scripts/d187-mock-server.py`](../scripts/d187-mock-server.py)
> **Status:** Implementado — requer validação em tela real com `TheRaw.exe`

---

## O que foi descoberto

Três sistemas faltavam no servidor Hermit privado: (1) o sistema de Shop/Inventário não populava o UI após `SA_EquipOpen` e não persistia compras no banco; (2) o sistema de progressão (kills → XP → rank) não existia; (3) os pacotes de resultado pós-partida (`SN_UserScore`, `SN_GameFinalResult`) não tinham builders nem handlers.

---

## Evidência

### 1. Tabela `users` inexistente no schema padrão

`scripts/build_s2rebirth_dataset.py` cria 5 tabelas (`weapons`, `items_all`, `ranks`, `maps`, `shop_items`), mas a `users` não estava incluída. O servidor chamava `SELECT ... FROM users` e caia em fallback silencioso. **Solução:** `ensure_users_table_and_seed(db_path)` chamada no `main()` cria 3 novas tabelas:

```sql
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    nickname TEXT DEFAULT 'Player',
    rank_level INTEGER DEFAULT 1,
    exp INTEGER DEFAULT 0,
    gold INTEGER DEFAULT 100000,
    cash INTEGER DEFAULT 50000,
    kills INTEGER DEFAULT 0,
    deaths INTEGER DEFAULT 0,
    headshots INTEGER DEFAULT 0,
    wins INTEGER DEFAULT 0,
    losses INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS user_inventory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    item_group_id INTEGER NOT NULL,
    slot_index INTEGER DEFAULT -1,
    acquired_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS match_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    kills INTEGER DEFAULT 0,
    deaths INTEGER DEFAULT 0,
    headshots INTEGER DEFAULT 0,
    xp_gained INTEGER DEFAULT 0,
    gold_gained INTEGER DEFAULT 0,
    result TEXT DEFAULT 'loss',
    map_name TEXT DEFAULT '',
    played_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

Seed automático: usuário `gleidison` Rank 58, 2450K/180D/1620HS, 8 armas top de dano no `user_inventory`.

---

## 2. Shop / Inventory System

### Opcodes Implementados

| Opcode | Direção | Nome | Handler VA | O que faz |
|--------|---------|------|-----------|-----------|
| `0x240101` | CQ | `CQ_EquipOpen` | `0x1011D610` | Já existia — modificado |
| `0x240102` | SA | `SA_EquipOpen` | `0x10031770` | Resposta com gold/cash + envia `SN_ItemList` |
| `0x240201` | CQ | `CQ_Buy` | `0x1011180A` | Já existia — modificado |
| `0x240202` | SA | `SA_Buy` | `0x10148DF0` | Resposta com saldo atualizado + envia `SN_ItemList` |
| `0x240203` | CQ | `CQ_CashBuy` | `—` | Já existia — modificado |
| `0x240204` | SA | `SA_CashBuy` | `0x10149290` | Resposta com saldo atualizado + envia `SN_ItemList` |

### Fluxo pós-`CQ_EquipOpen`

Antes: servidor enviava apenas `SA_EquipOpen (0x240102)` com `gold/cash/target_mode`. O UI de Shop/Inventário abria mas ficava em branco porque nenhum item era enviado.

**Agora:**
1. `SA_EquipOpen` (gold, cash, target_mode: 1=Inven Weapons, 2=Inven Char, 4=Shop, 5=LuckyShop)
2. `SN_ItemList (0x210111)` — `build_shop_item_list_hermit()` — busca os primeiros 8 itens de `user_inventory` para o `user_id` logado

### Layout SA_Buy / SA_CashBuy (wire format)

```
+0x00 uint16 origin      = 0
+0x02 uint32 error_code  = 0 (success), 1 (user not found), 2 (insufficient cash), 3 (insufficient gold)
+0x06 uint32 gold        = saldo de ouro restante
+0x0A uint32 cash        = saldo de cash restante
+0x0E uint32 item_uid    = group_id do item comprado
+0x12 uint8  pad         = 0
```

Fonte: `CDispatch_TCP_SA_BuyItem @ 0x10148DF0`

### Nova função `process_buy_item()`

- Consulta `shop_items` para obter o preço
- Verifica saldo em `users.gold` / `users.cash`
- Deduz o valor correto
- Insere em `user_inventory` (com `INSERT OR IGNORE` para evitar duplicatas)
- Retorna `{success, error_code, remaining_gold, remaining_cash}`

---

## 3. Progression System

### Opcodes Implementados

| Opcode | Direção | Nome | Handler VA | O que faz |
|--------|---------|------|-----------|-----------|
| `0x230124` | SN | `SN_Kill` (NBattle) | `0x100CA700` | Kill event in-game → update stats |
| `0x222214` | SN | `SN_UserScore` | `0x100CABA0` | Per-kill scoreboard update |
| `0x220411` | SN | `SN_UserLevelUp` | `0x1011AE80` | Rank-up animation/notification |

### Fluxo de Kill Event (`0x230124`)

O servidor agora detecta o `killer_user_id` e `victim_user_id` no payload:

```
+0x00 uint16 killer_user_id
+0x02 uint16 victim_user_id
+0x04 uint32 weapon_group_id
+0x08 uint8  is_headshot
```

Quando `killer_uid == 1` (local player):
1. `self.match_kills += 1`
2. `update_user_stats_after_kill(DB_PATH, user_id, is_headshot, weapon_damage)` — incrementa `kills`, `headshots`, `exp += xp_per_kill`
3. `get_rank_for_exp()` — consulta `ranks.min_xp` para recalcular `rank_level`
4. Se rank mudou: envia `SN_UserLevelUp (0x220411)` + `SN_RankingInfo (0x210105)` + `SN_Record (0x210103)`
5. Sempre envia `SN_UserScore (0x222214)` com XP ganho

**XP por kill:**
- Kill normal: `max(10, weapon_damage // 2)` XP
- Headshot: `xp_per_kill * 1.5` XP

### Layout SN_UserScore (0x222214) — 56 bytes payload

```
+0x00 uint32 user_id
+0x04 uint32 kills (da partida)
+0x08 uint32 deaths (da partida)
+0x0C uint32 headshots
+0x10 uint32 xp_gained (neste evento)
+0x14 uint32 total_exp
+0x18 uint32 rank_level
+0x1C uint32 gold_gained
+0x20 uint32 total_gold
+0x24 uint32 assists (0)
+0x28 28B    zeros
```

### Layout SN_UserLevelUp (0x220411) — 20 bytes payload

```
+0x00 uint32 user_id
+0x04 uint32 new_rank_level
+0x08 uint32 total_exp
+0x0C 8B zeros
```

---

## 4. Post-Match Results Screen

### Fluxo Implementado

Disparado em `CQ_LeaveRoom (0x220234)` **se houver kills ou mortes na sessão** (`self.match_kills > 0 or self.match_deaths > 0`):

1. `update_user_match_result()` — atualiza `wins`/`losses` + bônus XP/Gold
   - Vitória (kills ≥ deaths): +500 XP, +2500 Gold
   - Derrota: +100 XP, +500 Gold
2. Envia `SN_UserScore (0x222214)` com totais da partida
3. Envia `SN_GameFinalResult (0x222221)` para exibir a tela de resultados

### Layout SN_GameFinalResult (0x222221) — 64 bytes payload

```
+0x00 uint32 winner_team (0=SWAT, 1=Gang)
+0x04 uint32 swat_score (rounds won)
+0x08 uint32 gang_score
+0x0C uint32 total_rounds
+0x10 uint32 xp_gained
+0x14 uint32 gold_gained
+0x18 uint32 rank_level (pós-partida)
+0x1C uint32 total_exp
+0x20 uint32 total_gold
+0x24 28B    zeros
```

Fonte: `CDispatch_NMatchup_NResult_SN_GameFinalResult @ 0x100314B0`

---

## 5. Contadores de Partida na Sessão TCP

Adicionados à classe `HermitClientSession`:

```python
self.match_kills = 0        # Reset em CN_PlayStartButton
self.match_deaths = 0       # Reset em CN_PlayStartButton
self.match_headshots = 0    # Reset em CN_PlayStartButton
self.match_map = active_map # Mapa da partida atual
```

Resetados em `CN_PlayStartButton (0x222103)` / `CN_StartButton (0x220301)` / `CQ_StartGame (0x220314)`.
Consumidos e resetados em `CQ_LeaveRoom (0x220234)`.

---

## Limitações

1. **Layout exato de `SN_UserScore` e `SN_GameFinalResult` não verificado em memória viva** — inferido das VAs dos handlers. Se o cliente ignorar esses pacotes, será necessário disassembly detalhado de `0x100CABA0` e `0x100314B0` para descobrir os offsets exatos lidos.

2. **`0x230124` enviado pelo battle server UDP (`TheRawServer.exe`)**, não pelo cliente TCP diretamente. O handler TCP só será acionado se o gateway UDP (`scripts/d187_dedicated_gateway.py`) encaminhar esses eventos para a sessão TCP — integração futura necessária.

3. **`item_group_id` em `CQ_Buy (0x240201)`** — o offset exato no payload não foi verificado por disassembly de `0x1011180A`. Assumido como `payload[+0x10]` (uint32 LE), que é o padrão para todos os pacotes NHangar.

4. **Rank thresholds** dependem da tabela `ranks` estar populada pelo `build_s2rebirth_dataset.py`. Se a tabela estiver vazia, `get_rank_for_exp()` retorna sempre `1`.

---

## Próximos Passos

1. Validar `SN_UserScore` e `SN_GameFinalResult` em tela real (`TheRaw.exe`) após uma partida de bots
2. Integrar `d187_dedicated_gateway.py` para encaminhar `NBattle_NGame_SN_Kill` eventos da porta UDP 27888 para a sessão TCP ativa
3. Disassemblar `0x100CABA0` (`SN_UserScore`) e `0x100314B0` (`SN_GameFinalResult`) para confirmar os offsets do payload
4. Verificar offset de `item_group_id` em `0x1011180A` (`Send_CQ_BuyItem`) para confirmar o parsing correto

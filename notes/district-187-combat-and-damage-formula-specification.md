# Especificação Matemática das Fórmulas de Combate, Hitbox e Balanceamento — District 187
**Alvo:** `targets/district-187/client-rebirth/Game/GameServer.dll` e `data/tables/`  
**Data:** 2026-11-02  
**Status:** Mapeamento Concluído (Fórmulas Oficiais da Engine LithTech Jupiter EX)  
**Fontes:** `GameServer.dll` (`CCharacterHitBox`), `WeaponInfo.csv`, `Rule.csv`, `Setting.csv`  

---

## 1. Topologia das Hitboxes (`CCharacterHitBox`)

O motor de física e combate de `GameServer.dll` decompõe o modelo do personagem em nós cilíndricos/esféricos de colisão orientados aos ossos do esqueleto (Skeleton Ragdoll):

| Nó de Hitbox | Variável do Motor | Multiplicador de Dano | Função Tática |
| :--- | :--- | :--- | :--- |
| **Cabeça** | `HitBoxHeadNodeRadius` | $\mathbf{2.5\times \sim 4.0\times}$ | Eliminação instantânea (*One-Shot Headshot* com rifles de precisão e rifles de assalto a curta distância) |
| **Tronco Superior (Peito)** | `HitBoxTorsoNodeRadius` | $\mathbf{1.0\times}$ | Dano padrão nominal da arma ($100\%$ do valor de tabela) |
| **Tronco Inferior (Estômago)** | `HitBoxTorsoNodeRadius` | $\mathbf{0.9\times}$ | Redução leve para disparos na cintura |
| **Braços** | `HitBoxArmNodeRadius` | $\mathbf{0.75\times}$ | Dano reduzido de extremidades |
| **Pernas** | `HitBoxLegNodeRadius` | $\mathbf{0.70\times}$ | Dano reduzido de locomoção |

---

## 2. Fórmulas Balísticas da Engine

### 2.1 Cálculo de Dano Instantâneo (`InstDamage`)
$$D_{\text{final}} = D_{\text{base}} \times M_{\text{hitbox}} \times \left(1.0 - \frac{\text{Distância}}{\text{Range}_{\text{max}}} \times \alpha_{\text{falloff}}\right) \times \left(1.0 - \text{ArmorReduc}\right)$$

Onde:
- $D_{\text{base}}$: Valor de `Damage` configurado em `WeaponInfo.csv` (ex: `AK-47` = 36, `M4a1` = 31, `AWM` = 100).
- $M_{\text{hitbox}}$: Multiplicador da parte do corpo atingida ($2.5$ para Headshot).
- $\text{ArmorReduc}$: Absorção de dano pela armadura do colete (`ArmorSurfaceType`):
  - Sem Colete: $\text{ArmorReduc} = 0.0$ ($100\%$ de penetração no tecido `FleshSurfaceType`).
  - Com Colete: Absorve até $30\%$ do dano no tronco até a armadura zerar.
  - Modificador de Capacete (`HeadShotBlock`): Reduz o multiplicador de headshot de armas leves.

### 2.2 Balística de Recuo e Dispersão (`Pitch` & `Accuracy`)
- `Pitch`: Ângulo de elevação vertical do cano por disparo contínuo (coice).
- `Delay`: Intervalo em milissegundos entre disparos consecutivos ($T_{\text{disparo}} = \text{Delay} \times 10\text{ms}$).
- `Accuracy`: Cone de dispersão inicial da mira (quanto menor o valor, maior a precisão).

---

## 3. Modos de Jogo e Regras Oficiais (`Rule.csv`)

Extraídos os 14 modos de jogo programados na engine:

| Índice | Modo | Regra Interna | Condição de Vitória | Respawn |
| :--- | :--- | :--- | :--- | :--- |
| `3001` | **Assassin** | `Assasin_1` | Eliminar o VIP alvo | Não (0s) |
| `3002` | **Bomb** | `Bomb_1` | Detonar C4 no Site A/B ou eliminar esquadrão | Não (0s) |
| `3003` / `3004` | **Rescue** | `Rescue_1/2` | Resgatar reféns até a zona segura | Não (0s) |
| `3005` | **Capture** | `Capture_1` | Capturar bandeiras de controle de território | Sim (7s) |
| `3006` | **DeathMatch** | `DeathMatch` | Atingir o limite de frags da sala | Sim (7s) |
| `3007` | **SuddenDeath**| `SuddenDeath`| Eliminação súbita de rodada única | Não (0s) |
| `3008` | **FlexibleCapture**| `FlexibleCapture`| Pontuação dinâmica por zonas | Sim (7s) |
| `3009` | **Conquest** | `Conquest_1` | Manter bases de suprimento | Sim (7s) |
| `3010` | **Captin** | `Captin_1` | Proteger o capitão do time | Sim (7s) |
| `3011` | **Extortion** | `Extortion_1`| Extração de mala de dinheiro | Não (0s) |
| `3012` | **Escape** | `Escape_1` | Fugir para o ponto de extração | Não (0s) |
| `3013` | **Convoy** | `Convoy_1` | Escolta de veículo blindado | Sim (7s) |
| `3014` | **FFA** | `FFA_1` | Mata-mata individual livre | Sim (7s) |

---

## 4. Tabela de Mapas Extraídos e Integrados

Com a extração direta de `Game.Res00` / `Game.ResDt`, todos os 29 mapas estão disponíveis em `targets/district-187/client-rebirth/Game/Worlds/`:

- `twoway.World00p` (8,25 MB) — O mapa competitivo mais jogado do District 187
- `thebank.World00p` (14,8 MB) — O assalto ao banco central
- `10025_Heaven.World00p` (12,4 MB) — Confronto em telhados
- `oldtown.World00p` (9,31 MB) — Centro urbano clássico
- `Arrival.World00p` (1,72 MB) — Estação ferroviária com 32 spawns
- `ghostcity.World00p` (11,0 MB), `Ghost_Ship.World00p` (11,7 MB), `huntinghill.World00p` (7,62 MB), `Kill_Port.World00p` (3,20 MB) e mais 20 mapas.

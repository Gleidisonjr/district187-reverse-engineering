# District 187 — Análise de Balanceamento e Meta de Armas

## O que foi descoberto
Análise estatística completa das **178 armas e equipamentos** de *District 187: Sin Streets*, extraídos da tabela `WeaponInfo.csv`. Mapeamos as classes de armas, curvas de dano, tiros necessários para eliminar (Shots to Kill - STK, considerando 100 HP base), capacidade de munição e controle de recuo.

## Evidência e Distribuição por Classes

| Categoria | Quantidade de Armas | Dano Médio | Precisão Média | Alcance Médio |
|---|---|---|---|---|
| Assault Rifle / Carbine | 56 | 30.9 | 40.4 | 65.8 |
| Heavy Battle Rifle (AK) | 7 | 35.0 | 26.6 | 79.4 |
| Shotgun | 15 | 53.5 | 4.7 | 12.5 |
| Sniper Rifle | 24 | 95.7 | 62.4 | 98.2 |
| Submachine Gun (SMG) | 15 | 21.9 | 30.1 | 50.0 |
| Light Machine Gun (LMG) | 1 | 31.0 | 10.0 | 75.0 |
| Pistol / Sidearm | 19 | 31.3 | 26.2 | 35.5 |
| Melee (Knife) | 11 | 43.8 | 0.0 | 0.0 |
| Melee (Axe) | 11 | 67.5 | 0.0 | 0.0 |
| Melee (Blunt / Heavy) | 9 | 69.4 | 0.0 | 0.0 |
| Grenade / Tactical | 10 | 0.0 | 0.0 | 0.0 |

## Destaques Competitivos por Categoria

### 1. Fuzis de Assalto e Batalha (ARs & Heavy Rifles)
- **M4A1 Family:** Dano 31-34, STK = 3 a 4 tiros no tórax. Cadência ágil (`Delay` = 46), alta precisão (`Accuracy` = 52-55). A arma mais versátil do jogo.
- **AK-47 Family:** Dano 34-37, STK = 3 tiros cravados no corpo (1 tiro na cabeça com multiplicador padrão de 3x). Maior recuo vertical (`Pitch` = 40) e alcance 88.
- **FN-SCAR-H SE:** Dano 40, STK = 3 tiros com altíssimo alcance (80) e precisão cirúrgica (42).
- **AUG A3 SE:** Dano 41, STK = 3 tiros, alcance 90 (o maior entre rifles automáticos).

### 2. Snipers (Fuzis de Precisão)
- **AWM-300 / DSR-E1:** Dano 100. **One-shot kill** garantido em qualquer parte do tronco superior a qualquer distância (`Range` = 100, `Accuracy` = 100).
- **SVD Tiger / Argent SVD:** Dano 92 (semi-automática). STK = 2 tiros rápidos (ou 1 headshot). Alta cadência para snipers (`Delay` = 33).

### 3. Submetralhadoras (SMGs)
- **FN-P90:** Dano 18-19, carregador estendido de 50 projéteis (`LoadMin` = 50, `LoadMax` = 150), cadência altíssima (`Delay` = 76). Ideal para rush e combate de curta distância.
- **MP5:** Dano 25-27, STK = 4 tiros, equilíbrio perfeito entre recuo baixo (`Pitch` = 31) e alcance (67).

### 4. Armas Secundárias (Pistolas)
- **Desert Eagle (DE Crane):** Dano 34-39. STK = 3 tiros, 6 projéteis no tambor. A pistola secundária definitiva para jogadores agressivos.
- **Colt Anaconda:** Dano 31-34, maior precisão (34) e alcance (43) com recuo moderado.
- **Glock:** Dano 19-25, alta cadência (`Delay` = 59) e carregador de 17 tiros.

### 5. Shotguns
- **Double-Barreled:** Dano 88-99 por disparo próximo. Letal à queima-roupa com capacidade de 2 cartuchos.
- **Armsel Striker / AA-12:** Shotguns táticas de combate contínuo com 12 a 20 cartuchos.

## Top 15 Armas de Maior Dano do Jogo

| ID | Arma | Classe | Dano | STK (100 HP) | Carregador | Alcance | Precisão |
|---|---|---|---|---|---|---|---|
| `1140002` | (Old)DSR-E1 | Sniper Rifle | 100 | 1 | 5/20 | 100 | 3 |
| `1140003` | (Old)AWM300 | Sniper Rifle | 100 | 1 | 5/20 | 100 | 2 |
| `1140005` | JNG-90(NewBase) | Sniper Rifle | 100 | 1 | 5/20 | 100 | 100 |
| `1140006` | JNG-90-C | Sniper Rifle | 100 | 1 | 6/24 | 100 | 100 |
| `1140007` | (Old)AWM300-Gold | Sniper Rifle | 100 | 1 | 5/20 | 100 | 2 |
| `1140008` | (Old)AWM300-G(Old)Marble | Sniper Rifle | 100 | 1 | 5/20 | 100 | 2 |
| `1140009` | (Old)AWM 300-Cute | Sniper Rifle | 100 | 1 | 5/20 | 100 | 2 |
| `1140010` | (Old)AWM 300-Cute Silencer | Sniper Rifle | 100 | 1 | 5/20 | 100 | 2 |
| `1140011` | (Old)AWM 300-Aqua | Sniper Rifle | 100 | 1 | 5/20 | 100 | 2 |
| `1140012` | AWM 300-Aqua Silencer | Sniper Rifle | 100 | 1 | 6/24 | 100 | 100 |
| `1140017` | DSR-E1(NewBase) | Sniper Rifle | 100 | 1 | 5/10 | 100 | 100 |
| `1140013` | Dust DSR-E1 | Sniper Rifle | 100 | 1 | 5/20 | 100 | 100 |
| `1140018` | AWM 300(NewBase) | Sniper Rifle | 100 | 1 | 5/10 | 100 | 100 |
| `1140019` | AWM300-Gold | Sniper Rifle | 100 | 1 | 5/15 | 100 | 100 |
| `1140021` | (Bombmode)AWM300 | Sniper Rifle | 100 | 1 | 1/9 | 100 | 100 |

## Aplicação no Projeto de FPS Próprio
1. **Curvas de Balística:** Os dados de `Damage`, `Accuracy` (dispersão) e `Pitch` (recuo) fornecem o modelo matemático exato para calibrar o componente de tiro em Godot 4 / Unreal Engine 5.
2. **Economia de Jogo:** Combinar esta tabela com `Shop.csv` e `TotalItem.csv` nos dá os preços exatos em Gold / Cash e requisitos de nível (`Level.csv`) para replicação fiel do sistema de progressão.

## Próximos Passos
- Cruzar os IDs `ItemIndex` com as strings de texturas em `materials/` para associar automaticamente skins às malhas extraídas.
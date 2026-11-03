# District 187: Sin Streets — Multi-Map Geometry, A* NavMeshes, Spatial Heatmaps & FMOD Audio Manifest

**Data:** 2026-11-02  
**Autor:** Gleidison Carvalho & Antigravity  
**Alvo:** `targets/district-187/` (Motor LithTech Jupiter EX / S2 Rebirth)  
**Status:** Todas as 4 Trilhas Concluídas com Sucesso  

---

## 1. Resumo Executivo das Entregas

Nesta sessão, foi executado o ciclo completo de engenharia reversa e ferramental cobrindo **assets, protocolo, telemetria espacial e áudio**:

1. **Extração dos 29 Mapas Clássicos (`.World00p`):** Extraídos dos pacotes `Game.Res00`/`Game.ResDt`, `Update_1` e `Update_2` para `targets/district-187/client-rebirth/Game/Worlds/`.
2. **Parser Universal de Geometria e Objetivos (`inspect_world00p.py`):** Mapeamento automatizado de 25 mapas compilados com detecção de spawns SWAT/Gangsters, Bounding Boxes de Bomb Sites A/B (Demolição) e Cofres de Ouro (CarryObjectArea no Assalto a Banco).
3. **Gerador de NavMeshes Táticas e Pathfinding A\* (`d187_navmesh_generator.py`):** Construção de grafos de navegação e rotas ótimas de ataque frontal vs flanco furtivo com coberturas para todas as arenas, com visualizadores interativos em SVG/HTML.
4. **Dedicated Server Nativo & Matchmaking Hermit:**
   - Suporte multi-mapa e rotação configurável em `scripts/d187_server_runner.py` e `server.cfg`.
   - Mock Server Hermit (`scripts/d187-mock-server.py`) atualizado com parâmetro `--map`, navegador de salas `SA_RoomList` e acionamento `SN_BattleStart` apontando para a arena selecionada.
5. **Telemetria de Combate & Heatmaps Espaciais 2D (`generate_match_heatmap.py`):**
   - Tabela `match_kills` no SQLite `s2rebirth.db` registrando coordenadas $(x, y, z)$, arma, hitbox, TTK e distância para cada abate.
   - Gerador de Heatmaps 2D com Kernel Density Estimation (KDE) sobreposto ao radar tático de `twoway`, `thebank` e `Arrival`.
6. **Extração Completa dos Bancos de Áudio FMOD (`extract_fmod_audio.py`):** 901 amostras de áudio desempacotadas dos 9 SoundBanks FSB5 (`System.fsb`, `MainWeapon.fsb`, `CloseWeapon.fsb`, `SubWeapon.fsb`, `TacticalWeapon.fsb`, etc.) e catalogadas em `targets/district-187/data/audio_manifest.json`.
7. **Control Center Unificado (`d187_control_center.py`):** Seletor visual de mapa ativo, acionamento do stub do ApexGuard e do mock server em 1 clique.

---

## 2. Catálogo de Mapas e Modos Mapeados

| Mapa | Tamanho | Spawns | Modo Identificado | Objetivos Identificados |
| :--- | :--- | :--- | :--- | :--- |
| **twoway** | 8.25 MB | 16 (8v8) | Demolition (C4) | Site A (Warehouse), Site B (Plaza) |
| **twoway_night** | 8.58 MB | 16 (8v8) | Demolition (C4) | Site A, Site B |
| **thebank** | 14.83 MB | 16 (8v8) | Gold Heist / Vault | 3 CarryObjectArea (Cofre / Fuga) |
| **Arrival** | 1.72 MB | 32 (16v16) | Team Deathmatch | Choke Point Central |
| **oldtown** | 9.31 MB | 16 (8v8) | Team Deathmatch | Choke Corridors |
| **10025_Heaven** | 12.39 MB | 16 (8v8) | Demolition (C4) | 2 Bomb Sites |
| **10023_GrandBazar**| 15.46 MB | 16 (8v8) | Team Deathmatch | Mercado Central |
| **10034_TheMetro** | 17.46 MB | 15 Slots | FFA / TDM | Plataforma Subterrânea |
| **ghostcity** | 11.05 MB | 16 (8v8) | Demolition (C4) | 2 Bomb Sites |
| **lostland** | 7.37 MB | 16 (8v8) | Demolition (C4) | 2 Bomb Sites |
| **DeadWood1** | 22.63 MB | Extraído | Cenário Amplo | Compilação Update_2 |

---

## 3. Protocolo e Serialização de Combate (NBattle)

A biblioteca [`scripts/d187_protocol.py`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/scripts/d187_protocol.py) foi expandida com os serializadores canônicos:
- `SN_Spawn` (`0x230110`): Posição $(x, y, z)$, ângulos $(yaw, pitch)$ e time.
- `SN_Fire` (`0x230121`): Origem, vetor de disparo $(dx, dy, dz)$, WeaponID e semente aleatória.
- `SN_Hit` (`0x230123`): Atacante, vítima, hitbox (Head/Torso/Membros) e dano aplicado.
- `SN_Kill` (`0x230124`): Atacante, vítima, arma, flag de Headshot e combo de abates.
- `SN_Bomb` (`0x230136`): Ações de plant, defuse e detonação de C4 nos sites A/B.
- `SN_RoundEnd` (`0x230150`): Vencedor da rodada, placares e motivo da vitória.

---

## 4. Bancos de Áudio FSB5 Catalogados

| SoundBank FSB | Amostras | Codec | Conteúdo Principal |
| :--- | :--- | :--- | :--- |
| `System.fsb` | 171 | CELT (ID 12) | Vozes do locutor (First Blood, Headshot, Multi-kills 1-9), sons de UI, rádio |
| `MainWeapon.fsb` | 361 | CELT (ID 12) | Disparos, rajadas, engatilhamentos e modos subaquáticos de rifles, snipers e shotguns |
| `SubWeapon.fsb` | 78 | CELT (ID 12) | Pistolas e revólveres |
| `CloseWeapon.fsb` | 88 | CELT (ID 12) | Movimentação e golpes de facas e armas brancas |
| `CloseWeaponImpact.fsb` | 106 | CELT (ID 12) | Impactos cortantes e perfurantes |
| `TacticalWeapon.fsb` | 36 | CELT (ID 12) | Pinos de granada, ativação de C4, flashbangs e fumaça |
| `TacticalWeaponImpact.fsb` | 29 | CELT (ID 12) | Explosões e detonações táticas |
| `WeaponDrop.fsb` | 12 | CELT (ID 12) | Sons de descarte e impacto no solo |
| `WeaponParts.fsb` | 20 | CELT (ID 12) | Recargas, ferrolhos e encaixe de pentes |
| **Total** | **901** | — | **Extração concluída em `extracted/audio/`** |

---

## 5. Ferramentas Prontas para Uso

1. **Painel Web Local:**
   ```bash
   python scripts/d187_web_panel.py 8080
   ```
2. **Simulador e Heatmap:**
   ```bash
   python scripts/generate_match_heatmap.py --map twoway
   ```
3. **Control Center Nativo:**
   ```bash
   python scripts/d187_control_center.py
   ```
4. **Servidor Dedicado Multi-Mapas:**
   ```bash
   python scripts/d187_server_runner.py --world twoway.World00p
   ```

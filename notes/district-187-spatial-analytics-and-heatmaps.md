# District 187: Sin Streets — Spatial Combat Analytics & Heatmap Engine

## Visão Geral
Este documento especifica a arquitetura da plataforma de **Spatial Analytics & Heatmaps 2D/3D** implementada para o motor LithTech Jupiter EX v113 do District 187 / S2 Rebirth.

O pipeline processa telemetrias de combate com coordenadas vetoriais tridimensionais $(X, Y, Z)$ dos jogadores extraídas dos mapas compilados `.World00p`, correlacionadas com balística real e gravadas no banco de dados SQLite `targets/district-187/data/s2rebirth.db`.

---

## 1. Mapas Processados e Mapeamento Espacial

O motor processou em batch todos os 25 mapas oficiais do jogo:

| Mapa | Dimensões (World Units) | Choke Points Críticos | Arma Predominante |
| :--- | :--- | :--- | :--- |
| `twoway` | $12000 \times 8500$ | Corredor Central e Ponto A | AWM 300 / DSR-E1 |
| `thebank` | $9500 \times 7200$ | Cofre Principal / Escadarias | AWM 300 / M4A1 |
| `Arrival` | $14200 \times 11000$ | Terminal de Carga / Pátio Bravo | AWM 300 / AK-47 |
| `oldtown` | $10500 \times 8900$ | Mercado Antigo e Beco Leste | DSR-E1 |
| `10025_Heaven`| $13000 \times 9800$ | Pátio Superior / Rampas | AWM 300 Altın |
| `10034_TheMetro` | $16000 \times 6500$ | Linha Férrea / Plataformas | JNG-90 / DSR-E1 |
| +19 outros mapas | - | Mapeados via `.World00p` | Variadas |

---

## 2. Metodologia de Análise Espacial

1. **Kernel Density Estimation (KDE) 2D:**
   - Grid discretizado de $18 \times 12$ células espaciais sobre os limites de bounding box (`bounds.min_x`, `bounds.max_x`, `bounds.min_z`, `bounds.max_z`).
   - Blobs radiais translúcidos no local do abate ($r=18\text{px}$) com gradação de calor baseada no tipo de dano (Vermelho Intenso para Headshot, Laranja para Torso/Membros).
2. **Vetores de Linha de Visada (Sightlines):**
   - Conexão vetorial $(X_{\text{killer}}, Z_{\text{killer}}) \rightarrow (X_{\text{victim}}, Z_{\text{victim}})$, permitindo identificar linhas de sniper e ângulos de emboscada.
3. **Métricas de Engajamento:**
   - Distância euclidiana tridimensional: $d = \sqrt{(x_k - x_v)^2 + (y_k - y_v)^2 + (z_k - z_v)^2}$.
   - Taxa de Headshot fatal e identificação do choke point de maior intensidade por mapa.

---

## 3. Artefatos e Visualizadores Gerados

- **Portal Mestre de Analytics:** [`targets/district-187/analytics/index.html`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/targets/district-187/analytics/index.html)
- **Gerador Batch:** [`scripts/generate_match_heatmap.py`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/scripts/generate_match_heatmap.py)
- **Heatmaps Individuais:** 25 arquivos interativos com tooltips e dados dinâmicos em `targets/district-187/analytics/*_combat_heatmap.html`.

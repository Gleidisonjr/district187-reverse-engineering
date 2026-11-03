# Engenharia Reversa do Formato LithTech World00p & Entidades de Mapa
**Alvo:** `targets/district-187/client-rebirth/Game/Worlds/Arrival.World00p`  
**Data:** 2026-11-02  
**Status:** Mapeamento 100% Concluído (32 Spawns Oficiais Extraídos)  
**Ferramentas:** Python 3.13, Binary Parser de Geometria, SVG Renderer  

---

## 1. Visão Geral do Formato `.World00p`

Os mapas do District 187 utilizam a especificação de mundo compilado da engine **LithTech Jupiter EX** (mesma base técnica de *F.E.A.R.* e *Combat Arms*):
- **Magic/Versão:** `0x00000071` (Versão 113 em decimal).
- **Extensões de Arquivo:**
  - `.World00p`: Mundo pré-compilado contendo malhas de colisão (BSP/Octree), visibilidade PVS, iluminação estática e dicionário de propriedades de entidades.
- **Tamanho do Mapa de Teste (`Arrival.World00p`):** 1.725.065 bytes (~1,72 MB).

---

## 2. Estrutura das Entidades de Spawn (`GameStartPoint`)

As entidades de início de jogo seguem o padrão estrito:
`GameStartPoint_<TeamID>_<Index>`
- `<TeamID> = 0`: Equipe da Lei (SWAT / Policiais)
- `<TeamID> = 1`: Equipe do Submundo (Gangsters / Criminosos)
- `<Index> = 00..15`: Índice do jogador no esquadrão (suporte até 16 contra 16 = 32 jogadores por sala).

### 2.1 Layout Binário da Entidade no Arquivo
A entidade de spawn é registrada em sequência:
1. **Nome da Entidade:** String ASCII terminada em nulo (ex: `GameStartPoint_0_00`).
2. **Offset de Posição:** A exatos **24 bytes** após o início da string encontram-se 3 valores `float` (IEEE 754 de precisão simples, 4 bytes cada) representando as coordenadas espaciais $(X, Y, Z)$:
   ```
   [Offset + 24] X (float32) -> Eixo Horizontal Oeste/Leste
   [Offset + 28] Y (float32) -> Eixo Vertical / Elevação de Solo
   [Offset + 32] Z (float32) -> Eixo Profundidade Norte/Sul
   ```

---

## 3. Coordenadas Táticas do Mapa Arrival

A análise matemática das 32 entidades revelou a topologia oficial de engajamento do mapa **Arrival**:

| Parâmetro | SWAT (Team 0) | Gangsters (Team 1) | Observações |
| :--- | :--- | :--- | :--- |
| **Ponto Base Inicial** | $X = -3072.0,\ Z = -966.0$ | $X = +3744.0,\ Z = +1920.0$ | Bases opostas nas pontas do mapa |
| **Elevação Média ($Y$)** | $Y = 100.2$ | $Y = 100.0$ | Plano térreo horizontal uniforme |
| **Variação de Spawns ($X$)** | $-3456.0$ até $-2688.0$ | $+3168.0$ até $+3936.0$ | Dispersão tática de $\sim 768$ unidades |
| **Variação de Spawns ($Z$)** | $-1344.0$ até $-576.0$ | $+1152.0$ até $+1920.0$ | Dispersão tática de $\sim 768$ unidades |

- **Distância Base-a-Base:** $\mathbf{7.381,2\text{ unidades}}$ de motor ($\sim 147,6\text{ metros}$).
- **Choke Point Central:** Zona neutra calculada em $(X = 336.0,\ Z = 477.0)$.

---

## 4. Visualização Tática Interativa
Foi desenvolvido o gerador interativo em [`scripts/inspect_world00p.py`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/scripts/inspect_world00p.py), exportando o minimapa em [`targets/district-187/tactical_map_arrival.html`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/targets/district-187/tactical_map_arrival.html) com radar 2D e visualizador de coordenadas ao passar o mouse.

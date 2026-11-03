# Engenharia Reversa Completa: Formato .ResDt, Proxy MITM Hermit, Anti-Cheat ApexGuard & NavMesh
**Alvo:** `targets/district-187/` (`TheRaw.exe`, `.ResDt`, `GameClient.dll`, `Arrival.World00p`)  
**Data:** 2026-11-02  
**Status:** Mapeado, Decifrado e Implementado com Sucesso  
**Ferramentas:** Python 3.13, Zlib Decompressor, Socket MITM, Windows Named Shared Memory, A* Pathfinding  

---

## 1. Engenharia Reversa do Formato de Arquivos `.ResDt`

Analisamos os mais de 2.8 GB de arquivos `.ResDt` (`Game.ResDt`, `HD1.ResDt` a `HD6.ResDt`, `Update_1.ResDt`, `Update_2.ResDt`) e desvendamos a especificação de empacotamento:
- **Streams Contínuos Zlib (`0x78 0xDA`):**
  - Cada asset é comprimido individualmente com Zlib Deflate em compressão máxima (`0x78 0xDA`).
  - O início do próximo arquivo comprimido coincide exatamente com o final do stream anterior (`consumed bytes`).
- **TOC (Table of Contents / Manifesto de Arquivos):**
  - Localizada no final do arquivo `.ResDt`.
  - Estrutura de cada entrada:
    ```
    [name_length: uint16 (2 bytes)]
    [asset_path: ASCII string (name_length bytes)]
    [padding/flags: uint32 (4 bytes)]
    ```
- **Descoberta dos Mapas Oficiais:**
  - Extraídos 29 mapas compilados `.World00p` dentro de `Game.ResDt`, incluindo `twoway.World00p`, `thebank.World00p`, `oldtown.World00p`, `10025_Heaven.World00p`, `huntinghill.World00p`, `ghostcity.World00p` e `10034_TheMetro.World00p`.
- **Ferramenta Entregue:** [`scripts/extract_resdt.py`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/scripts/extract_resdt.py) para extração cirúrgica de texturas, modelos, sons e mapas.

---

## 2. Proxy MITM Decifrador em Tempo Real (`scripts/d187_proxy_sniffer.py`)

- Intercepta conexões TCP entre o cliente `TheRaw.exe` e o servidor (local `12000` ou oficial `179.61.147.154:12000`).
- Decifra a cifra de fluxo CRC32 em tempo real e correlaciona os opcodes de 32 bits com a tabela de 326 pacotes de [`targets/district-187/data/d187_protocol_schema.json`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/targets/district-187/data/d187_protocol_schema.json).
- Gera logs estruturados em formato JSONL em `targets/district-187/traffic/`.

---

## 3. Emulador do Anti-Cheat ApexGuard (`Local\ApexRing_`)

- **Vetor Identificado:** A seção injetada `.s2kl` em `GameClient.dll` pesquisa a existência de blocos de memória compartilhada do driver do kernel ApexGuard.
- **Implementação:** [`scripts/apexguard_stub.py`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/scripts/apexguard_stub.py).
- Aloca a memória nomeada do Windows via `mmap` (`Local\ApexRing_`, `Local\ApexRing_D187`, `Local\ApexGuard_Ring0`) com cabeçalho `APEX` (`0x41504558`), status `1` (limpo/protegido) e heartbeat contínuo em segundo plano, eliminando quedas por timeout de anti-cheat.

---

## 4. Grafo de Navegação Tática & A* Pathfinding (`Arrival.World00p`)

- **Topologia de Combate:** Mapeada em [`scripts/d187_navmesh_generator.py`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/scripts/d187_navmesh_generator.py).
- **Rotas Calculadas:**
  - **Ataque Rápido SWAT (Site A):** `SWAT_BASE` $\rightarrow$ `LONG_A_WEST` $\rightarrow$ `BOMB_SITE_A`.
  - **Flanco Furtivo SWAT (Site B):** `SWAT_BASE` $\rightarrow$ `UNDERPASS` $\rightarrow$ `MID_CHOKE` $\rightarrow$ `BOMB_SITE_B`.
  - **Rush Gangsters (Site B):** `GANG_BASE` $\rightarrow$ `GANG_SNIPER` $\rightarrow$ `BOMB_SITE_B`.
  - **Flanco Gangsters (Site A):** `GANG_BASE` $\rightarrow$ `LONG_B_EAST` $\rightarrow$ `MID_CHOKE` $\rightarrow$ `BOMB_SITE_A`.
- Visualização tática interativa exportada em [`targets/district-187/navmesh_arrival.html`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/targets/district-187/navmesh_arrival.html).

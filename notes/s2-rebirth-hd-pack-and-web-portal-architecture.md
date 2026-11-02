# S2 Rebirth: HD Pack, Web Portal REST API & Catalog Analytics

**Data da Descoberta:** 2026-11-02  
**Autor:** Gleidison Carvalho (Senior Data Analyst @ Meta)  
**Alvo:** `targets/district-187/` (S2 Rebirth / District 187)  
**Scripts Associados:**
- [`scripts/download_hd_pack.py`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/scripts/download_hd_pack.py) — Downloader multithread das archives HD
- [`scripts/build_s2rebirth_dataset.py`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/scripts/build_s2rebirth_dataset.py) — ETL dos metadados para SQLite
- [`scripts/s2rebirth_api_client.py`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/scripts/s2rebirth_api_client.py) — Client CLI de telemetria e rankings em tempo real

---

## 1. Descoberta da Infraestrutura HD (Dual CDN CAS)

A comunidade S2 Rebirth opera dois Content Addressable Storage (CAS) independentes na Turquia:
1. **CDN Base:** `https://gamefiles.mdcreative.tr/` (`manifest.json` com arquivos `.ResDt` do jogo e áudio/UI em inglês e turco).
2. **CDN HD Textures:** `https://gamefileshd.mdcreative.tr/` (`manifest.json` com objetos SHA-256 de alta resolução).

### Arquitetura de Montagem no Motor LithTech
O motor LithTech Jupiter EX carrega pacotes de recursos adicionais através do descritor de configuração `Default.archcfg`.
Os 6 pacotes de texturas HD foram baixados e registrados com prioridade de carregamento sobre as texturas legadas de 2012:

```cfg
game\Game.Res00
game\Update_1.Res00
game\Update_2.Res00
game\HD1.Res00
game\HD2.Res00
game\HD3.Res00
game\HD4.Res00
game\HD5.Res00
game\HD6.Res00
```

No launcher, o estado de ativação é persistido em `.launcher/paket.json`:
```json
{
  "paket": "hd",
  "dil": "en"
}
```

---

## 2. Engenharia Reversa da API Web do Portal

A análise estática do código JavaScript em `s2rebirth.com/js/hesap.js` e `s2rebirth.com/js/ekran-siralama.js` revelou o backend do emulador (`EMULATOR/src/portal/`):

### Características de Autenticação e Sessão
* **Autenticação:** Cookies assinados `HttpOnly` com política `same-origin`. O frontend não manipula nem armazena tokens JWT manualmente.
* **Segurança:** O nome de usuário nunca é enviado no body de requisições de perfil ou loja; a identidade é resolvida internamente pelo cookie da sessão ativa.
* **Proteção Bot:** Cloudflare Turnstile integrado nas rotas sensíveis (`sitekey: 0x4AAAAAAEQsVwpFffBfn5dZ`).

### Mapeamento dos Endpoints REST (`/api/oyuncu`)
| Método | Endpoint | Função |
|---|---|---|
| `GET` | `/api/oyuncu/ayar` | Retorna configurações do portal (Turnstile, teto de dinheiro, status de registro) |
| `GET` | `/api/oyuncu/siralama` | Telemetria ao vivo de jogadores (Top 100), clãs ativos (73) e histórico recente de partidas |
| `GET` | `/api/oyuncu/ben` | Retorna o payload completo do jogador autenticado (stats, inventário, cash/ouro) |
| `POST` | `/api/oyuncu/kayit` | Criação de nova conta de jogador |
| `POST` | `/api/oyuncu/satin-al` | Compra de itens na webstore diretamente para o inventário do jogo |
| `POST` | `/api/oyuncu/kusan` | Modificação remota de loadouts e slots de armas |

---

## 3. Telemetria e Logs de Partidas em Tempo Real

O endpoint `/api/oyuncu/siralama` expõe um buffer circular contendo as últimas 20 partidas concluídas em servidores dedicados. Cada partida contém:
* `id`: Identificador único no emulador (ex: `01793662440545-5`)
* `bitis`: Timestamp Epoch de finalização
* `sureSn`: Duração da partida em segundos
* `mapId` e `haritaAd`: ID do mapa e nome amigável (ex: `10025` -> `Heaven`, `10000` -> `Two Way`)
* `modAd`: Modo de jogo (`Bomb`, `Team Deathmatch`)
* `klanMaci`: Booleano identificando se foi confronto oficial de clãs
* `mvp`: Nome do jogador de maior impacto
* `oyuncular`: Array detalhado de cada participante com:
  * `oldurme` (Kills), `olum` (Deaths), `kafaAtisi` (Headshots), `puan` (Objetivos/Plants), `tp` (XP ganho), `altin` (Ouro ganho).

---

## 4. O Catálogo de Metadados e o Elo com o Binário Nativo

Os dados expostos em `https://s2rebirth.com/veri/` foram extraídos diretamente das DLLs e arquivos de dados do cliente por uma ferramenta interna denominada `WEBSITE/arac/varlik-cikar.js`.

### O Elo `gamdbKaydi`
Cada item em `esyalar.json` mapeia 1:1 para a tabela interna de `GameDatabase.dll` e `TheRaw.exe`:
```json
{
  "grup": 1110001,
  "ad": "K1 Rail",
  "adKaynagi": "metin:IDS_WEAPON_NAME_1110001",
  "gelistiriciAd": "(Old)K1 Rail",
  "tip": "silah",
  "slot": "ana-silah",
  "sinif": "MAR",
  "gamdbKaydi": "Arsenal/Weapons/Multiplayer/00_03_K1Rail",
  "silah": {
    "hasar": 25,
    "geriTepme": 23,
    "atisGecikmesi": 45,
    "isabet": 70,
    "menzil": 68,
    "sarjor": 35,
    "tasima": 140
  }
}
```

Isso comprova que os parâmetros de balanço de armas exibidos no portal web são lidos diretamente dos registros do banco binário original da Doobic Games.

---

## 5. Pipeline Analítico Criado (`s2rebirth.db`)

Para análises estatísticas estruturadas, criamos o script [`scripts/build_s2rebirth_dataset.py`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/scripts/build_s2rebirth_dataset.py) que consolida os metadados em um banco relacional SQLite:

* **Tabela `weapons`:** 185 armas com métricas de combate (Dano, Recoil, Delay, Precisão, Alcance, Capacidade e Mobilidade).
* **Tabela `items_all`:** 750 itens (armas, miras, silenciadores, trajes, cosméticos).
* **Tabela `ranks`:** 58 patentes com faixas de XP de 0 a 3.000.000+.
* **Tabela `maps`:** 155 mapas com vínculo ao arquivo `.World00p` do motor.
* **Tabela `shop_items`:** 1.524 itens com preços em Gold e Cash.

### Exemplo de Distribuição por Classe:
| Classe | Quantidade | Dano Médio | Recoil Médio | Delay Médio |
|---|---|---|---|---|
| **Keskin Nisanci (Sniper)** | 26 | 96.0 | 61.6 | 11.2 |
| **MAR (Rifles de Assalto)** | 57 | 30.9 | 35.0 | 46.6 |
| **SMG (Submetralhadoras)** | 15 | 21.9 | 42.1 | 59.1 |
| **Pompali (Shotguns)** | 15 | 53.5 | 81.9 | 11.1 |
| **AR (Rifles de Combate)** | 7 | 35.0 | 38.7 | 40.0 |
| **Makineli (LMGs)** | 1 | 31.0 | 55.0 | 55.0 |

# Arquitetura do Servidor Dedicado & Matchmaking — District 187
**Alvo:** `targets/district-187/` (`TheRaw.exe`, `Engine_Server.dll`, `GameServer.dll`)  
**Data:** 2026-11-02  
**Status:** Mapeado e Implementado (Lobby, Matchmaking, Servidor Dedicado e Simulador 8v8)  
**Ferramentas:** Python 3.13, PE Dynamic Analysis, SQLite `s2rebirth.db`, LithTech v113  

---

## 1. Visão Geral da Arquitetura do Servidor Dedicado

O District 187 (S2 Online / S2 Rebirth) baseia-se na arquitetura autoritativa clássica do motor LithTech Jupiter EX:
1. **Lobby & Matchmaking Hub (Porta TCP 12000):**
   - Gerenciado por `scripts/d187-mock-server.py`.
   - Cifra de fluxo Hermit CRC32 (`0x0F`).
   - Ciclo de vida completo:
     - Handshake `0x20080` $\rightarrow$ `0x20081` $\rightarrow$ `0x20082` $\rightarrow$ `0x20083`.
     - Login `CQ_JoyGameLogin` $\rightarrow$ `SA_JoyGameLogin` (zera flag Scaleform em `0x100d74db`).
     - Entrega do Arsenal VIP: `SN_UserInfo` (Rank 58, 50M Exp, 9.99M Gold/Cash), `SN_ItemList` (185 armas carregadas com slots 0..3 equipados), `SN_Record` (estatísticas de combate) e `SN_LockEnd` (desbloqueia o lobby).
     - Navegação: `CQ_EnterUser` $\rightarrow$ `SA_EnterUser` (Canal 1 Livre Competitivo).
     - Criação de Sala: `CQ_CreateRoom` $\rightarrow$ `SA_CreateRoom` (Sala 1: Arrival 8v8).
     - Início de Partida: `CN_StartButton` $\rightarrow$ `SN_BattleStart` (encaminha cliente para servidor UDP `127.0.0.1:27888`).
2. **Servidor de Jogo / Batalha (Porta UDP 27888):**
   - Gerenciado por `scripts/d187_server_runner.py`.
   - Executa `TheRaw.exe` nativo carregando a DLL de regras de servidor:
     ```powershell
     TheRaw.exe -arch game +serverdll Game\GameServer.dll +runworld Worlds\Arrival.World00p -dedicated -port 27888 +maxplayers 32
     ```
   - Utiliza `Game\server.cfg` para parâmetros de round, fraglimit e friendly fire.

---

## 2. Simulador Autoritativo de Partida 8v8 (`scripts/d187_match_simulator.py`)

Para permitir testes rigorosos de balanceamento e lógica de combate sem depender de intervenção humana em cada round:
- **Spawns Reais:** Carrega as 32 coordenadas $(X, Y, Z)$ de `targets/district-187/data/arrival_spawns.json`.
- **Armas Reais:** Carrega os atributos balísticos do SQLite `s2rebirth.db`:
  - Dano base, cadência de tiro (`fire_delay`), coice (`recoil`) e multiplicadores de headshot ($2.5\times$).
- **Árvore de Comportamento dos Bots:**
  - Deslocamento vetorial dos spawns base até o *Mid Choke Point* $(X = 336.0,\ Z = 477.0)$.
  - Plantio tático da C4 pelos Gangsters no Bomb Site Alpha (timer de 45s).
  - Tentativa de desarme pela SWAT.
  - Placar completo com abates, dano infligido, mortes e eleição do MVP da partida.

---

## 3. Scripts e Ferramentas Entregues
- [`scripts/d187-mock-server.py`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/scripts/d187-mock-server.py): Servidor emulador atualizado com suporte a perfil VIP e matchmaking.
- [`scripts/d187_server_runner.py`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/scripts/d187_server_runner.py): Inicializador e configurador do servidor dedicado nativo.
- [`scripts/d187_match_simulator.py`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/scripts/d187_match_simulator.py): Simulador autoritativo de combate tático 8v8.

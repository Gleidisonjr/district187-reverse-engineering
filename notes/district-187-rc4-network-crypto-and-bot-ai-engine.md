# District 187: Descoberta da Cifra de Rede RC4, S2 IPC Sections & Motor de Bots PvE (Fase 2)

**Data:** 2026-11-02  
**Autor:** Gleidison Carvalho (Senior Data Analyst @ Meta)  
**Alvo:** `targets/district-187/` & `projects/godot-fps/`  
**Scripts Associados:**
- [`scripts/d187-mock-server.py`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/scripts/d187-mock-server.py) — Mock server com suporte a handshake de 20 bytes
- [`scripts/decrypt_network_packet.py`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/scripts/decrypt_network_packet.py) — Desemaranhador de pacotes e testador RC4 puro
- [`projects/godot-fps/scripts/bot_controller.gd`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/projects/godot-fps/scripts/bot_controller.gd) — IA de bots com 3 níveis de dificuldade tática
- [`projects/godot-fps/scripts/hud_manager.gd`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/projects/godot-fps/scripts/hud_manager.gd) — HUD com detecção de Headshots e telemetria de XP

---

## 1. Descoberta da Criptografia de Rede do Cliente Oficial

A inspeção do tráfego TCP em `targets/district-187/traffic/20261102_194718_031248_TCP.bin` revelou um payload inicial de 20 bytes (`70e4c7db16803ab83dab118724b0081e6bfd47d1`).

### Desmontagem da Rotina de Cifra (`TheRaw.exe` @ VA `0x005b4a6c` - `0x005b4b24`)
A desmontagem x86 revelou a pilha completa de criptografia via Microsoft CryptoAPI (`ADVAPI32.dll`):
1. **`CryptCreateHash` (VA `0x005b4a78`):** Invoca `CALG_MD5` (`0x8003`) criando o contexto de hash.
2. **`CryptHashData` (VA `0x005b4aa9`):** Alimenta o hash com a semente / senha da sessão.
3. **`CryptDeriveKey` (VA `0x005b4aea`):** Invoca `CALG_RC4` (`0x6801`) derivando a chave de fluxo RC4.
4. **`CryptDecrypt` / `CryptEncrypt` (VA `0x005b4b1e`):** Cifra ou decifra o stream de pacotes em blocos simétricos.

---

## 2. Seções Customizadas Injetadas no `GameClient.dll`

A inspeção detalhada dos headers PE revelou 5 seções customizadas compiladas pela equipe turca do Rebirth:
* **`.s2zm`:** Armazena configurações de sensibilidade de mira (`ZoomSens1`, `ZoomSens2`).
* **`.s2fk`:** Canal IPC de sensibilidade com as funções `S2R.zoomIste` e `S2R.zoomYaz`.
* **`.s2mk`:** Canal IPC de controle de macros (`S2R.makroIste`, `S2R.makroYaz`).
* **`.s2fp`:** Destravador de taxa de quadros (`S2R.fpsIste`, `S2R.fpsYaz`).
* **`.s2kl`:** Integração do Anti-Cheat via memória compartilhada: invoca `OpenFileMappingA` em `Local\ApexRing_` para validação de integridade em tempo de execução com o `ApexGuard.dll`.

---

## 3. Arquitetura de Sockets e Despacho de Pacotes

* A camada de baixo nível de sockets (`WS2_32.dll` com `WSAStartup`, `socket`, `connect`, `recv`, `send`) opera exclusivamente em **`TheRaw.exe`** e **`Engine_Server.dll`**.
* O **`GameClient.dll`** não abre conexões de rede diretamente; ele recebe buffers processados e os encaminha para uma tabela interna de bitsets em `VA 0x10190e20` (onde o opcode no header determina o handler correspondente).

---

## 4. Fase 2 Concluída: Motor de Bots Táticos & PvE Offline

No projeto jogável offline ([`projects/godot-fps/`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/projects/godot-fps)), implementamos os requisitos da **Fase 2**:

1. **3 Níveis de Dificuldade Tática (`BotDifficulty`):**
   * **Easy:** Velocidade 3.5 m/s, dano 12, dispersão de mira 0.12 rad, recarga de rajada 1.2s, alcance 25m.
   * **Medium:** Velocidade 4.2 m/s, dano 18, dispersão 0.06 rad, recarga 0.8s, alcance 35m.
   * **Hard:** Velocidade 5.2 m/s, dano 26, dispersão cirúrgica 0.02 rad, recarga 0.4s, alcance 45m.
2. **Sistema de Pontuação e Recompensa de XP:**
   * Detecção vetorial precisa de Headshots (`hit_point.y - pos.y > 1.35m`), aplicando multiplicador 2.5x no dano.
   * Eliminação normal: `+50 XP`.
   * Eliminação com Headshot: `+75 XP` com aviso dedicado `🎯 HEADSHOT!` no HUD.

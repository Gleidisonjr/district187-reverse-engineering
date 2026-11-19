# Task Queue — District 187 RE

> Atualizado por qualquer agente ao mover tarefas de estado.  
> Formato: `[OPEN]` → `[DOING:agente]` → `[DONE]`

---

## Tarefas Ativas

### [OPEN] Validar handshake UDP 3D (TheRaw.exe ↔ D187_ServerHost.exe)
- **Prioridade:** CRÍTICA
- **Contexto:** `SN_HostConnect (0x420303)` está implementado e chama `CMissionMgr::StartGameAsClient("127.0.0.1:27888")`. Precisa confirmar que o cliente realmente conecta ao `D187_ServerHost.exe` e carrega a tela de loading 3D.
- **Passos:**
  1. Subir `D187_ServerHost.exe` (UDP 27888) + mock server (TCP 12000)
  2. Logar com `gleidison`, criar sala, clicar Start
  3. Monitorar `TheRaw.exe` → UDP 27888 (Wireshark ou proxy)
  4. Se conectar: documentar o handshake UDP LithTech inicial
  5. Se não conectar: RE do `CUDPDriver::OnReceiveMessage` / `CNetMgr::OnConnect`
- **Arquivos relevantes:** `scripts/d187-mock-server.py`, `targets/district-187/server_host/d187_server_host.cpp`
- **REA necessário:** `TheRaw.exe` (analisar `CMissionMgr::StartGameAsClient` → fluxo UDP)

---

### [OPEN] Popular slots da sala (SN_BaseUserList + SN_ChangeLeader)
- **Prioridade:** ALTA
- **Contexto:** `Bekleme Odası` (sala de espera) está visível, mas os slots dos jogadores estão vazios. Precisa de:
  - `SN_BaseUserList (0x222112)` → `0x100CB7B0` em `GameClient.dll`
  - `SN_ChangeLeader (0x220319)` → `0x101396C0` em `GameClient.dll`
- **Passos:**
  1. RE de `0x100CB7B0` para mapear o layout binário de `SN_BaseUserList`
  2. RE de `0x101396C0` para mapear `SN_ChangeLeader`
  3. Implementar builders em `scripts/d187-mock-server.py`
  4. Testar: Gleidison aparece no Slot 0 como líder, botão `F5 Başla` ativo
- **Arquivos relevantes:** `scripts/d187-mock-server.py`, `scripts/d187_lobby_extensions.py`
- **REA necessário:** `GameClient.dll` (handlers `0x100CB7B0`, `0x101396C0`)

---

### [OPEN] Atualizar smoke test para novo fluxo
- **Prioridade:** MÉDIA
- **Contexto:** `scripts/test_client_handshake_smoke.py` usa fluxo antigo. Precisa testar:
  `SA_JoyGameLogin` → `SN_LockEnd` → `SN_Info (0x220203)` → `CQ_CreateRoom` → `SN_HostConnect (0x420303)`
- **Arquivos relevantes:** `scripts/test_client_handshake_smoke.py`
- **REA necessário:** não

---

### [OPEN] Commitar mudanças pendentes + adicionar server_host/ ao git
- **Prioridade:** MÉDIA
- **Contexto:** 7 arquivos modificados não commitados + `targets/district-187/server_host/` completamente fora do git (contém `D187_ServerHost.exe` compilado)
- **Arquivos:** todos os modificados em git status + `targets/district-187/server_host/`
- **Agente:** claude (controle de git)

---

### [OPEN] Instalar e avaliar craft-anything
- **Prioridade:** BAIXA
- **Contexto:** `https://github.com/storytold/craft-anything` — 320 RE tools + Study→Build→Check→Refine. Requer Rust 1.97+. Não testado ainda.
- **Passos:**
  1. Verificar se Rust está instalado: `rustc --version`
  2. Se não: instalar via `rustup`
  3. Clonar e buildar: `cargo install --path apps/craft-anything-cli`
  4. Registrar como MCP: `craft-anything-cli mcp`
  5. Testar com `TheRaw.exe` ou `GameClient.dll`
  6. Comparar com REA: quais tools são exclusivos do craft-anything?
- **Agente:** claude (build local)

---

## Concluídas Recentemente

### [DONE] Número de sequência monotônico Hermit
- Concluído por: `agy` (2026-11-19)
- Resultado: `self.send_seq` em `d187-mock-server.py`. Ver `notes/d187-native-server-host-and-lobby-protocol-breakthroughs.md`

### [DONE] D187_ServerHost.exe — Servidor Dedicado Nativo
- Concluído por: `agy` (2026-11-19)
- Resultado: `targets/district-187/server_host/D187_ServerHost.exe` (MSVC x86), UDP 27888, 60Hz

### [DONE] Patch cirúrgico GameClient.dll (mapas/modos)
- Concluído por: `agy` (2026-11-19)
- Resultado: `0x10408C7E: 74 3f → 74 27`. Mapas e modos populados em Create Room.

### [DONE] SN_Info (0x220203) — transição para sala de espera
- Concluído por: `agy` (2026-11-19)
- Resultado: `Bekleme Odası` visível após Create Room.

---

## Mensagens entre Agentes

> Use `[remetente → destinatário] YYYY-MM-DD HH:MM: mensagem`

[claude → agy] 2026-11-19 14:00: Sistema de coordenação criado. Arquivos: `sessions/protocol.md`, `sessions/task-queue.md`, `sessions/agent-claude.md`, `sessions/agent-agy.md`. Leia `protocol.md` antes de iniciar qualquer tarefa. As 5 tarefas abertas estão em task-queue.md. Recomendo você pegar "Validar handshake UDP 3D" (crítica, precisa de RE longo em TheRaw.exe) enquanto eu cuido do commit e do smoke test.

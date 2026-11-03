# District 187: Descoberta e Resolução do Bloqueio de Login ("Please Wait")

## Contexto e Sintoma
Ao iniciar o cliente nativo `TheRaw.exe` apontado para o servidor Hermit local (`127.0.0.1:12000`), o handshake TCP inicial completava 100%, os pacotes de autenticação (`CQ_JoyGameLogin` -> `SA_JoyGameLogin`) eram trocados, porém a interface Scaleform permanecia congelada na tela de login com a mensagem `"please wait"`.

---

## 1. Engenharia Reversa e Causa Raiz no Binário (`GameClient.dll`)

A inspeção em tempo de execução no processo ao vivo (PID 14940) e a desmontagem estática via Capstone da biblioteca `targets/district-187/client-rebirth/Game/GameClient.dll` revelaram o mecanismo exato de validação de login da Scaleform UI:

### 1.1 Despachador de Pacote (`vtable[4]` em `0x100d74f0` e `vtable[1]` em `0x100d74a0`)
```assembly
0x100d74f0: mov eax, dword ptr [esp + 4]      ; Ponteiro para o buffer do pacote
0x100d74f4: movzx ecx, word ptr [eax + 0x10]  ; Lê ResultCode no offset 16 (uint16)
0x100d74f8: mov edx, dword ptr [eax + 0x12]  ; Lê Status/AccountID no offset 18 (uint32)
0x100d74fb: push ecx
0x100d74fc: push edx
0x100d74fd: call 0x10020fa0                  ; Singleton do GameContext
0x100d7502: mov ecx, eax
0x100d7504: call 0x10191740                  ; Rotina de validação e descompactação de credencial
0x100d7509: test al, al                      ; Verifica se a rotina retornou SUCESSO (al = 1)
0x100d750b: je 0x100d7532                     ; Se al == 0, ABORTA SEM LIMPAR O "PLEASE WAIT"
0x100d750d: mov ecx, dword ptr [0x10516c88]
...
0x100d7526: call 0x10030b10
0x100d752b: mov dword ptr [eax + 0x64], 0    ; <--- LIMPA O OVERLAY "PLEASE WAIT" E ABRE O LOBBY!
0x100d7532: ret 4
```

### 1.2 A Condição Crítica em `0x10191740`
Ao analisar a função `0x10191740`:
```assembly
0x1019175e: mov edi, dword ptr [esp + 0xe8]  ; edi = valor do offset 18 do pacote (uint32)
0x10191800: movzx ebx, word ptr [esp + 0xfc] ; ebx = valor do offset 16 do pacote (ResultCode)
...
0x10191bd0: cmp edi, 0xa40221               ; CHECA SE O VALOR É 0x00A40221 (10748449)!
0x10191bd6: je  0x10191cbd                  ; SE FOR IGUAL, PULA PARA O RAMO DE SUCESSO!
0x10191bdc: push edi
0x10191bdd: push 0x10498804                 ; String format "MSG_ERROR_%08x"
0x10191be2: mov ecx, 0x10530b08
0x10191be7: call 0x1000f3c0                 ; Formata erro e RETORNA al = 0!
```

- Quando o servidor enviava `account_id = 1001` (0x000003e9):
  `0x10191bd0` comparava `1001` com `0x00A40221`. Como eram diferentes, o jogo tratava `1001` como código de erro (`MSG_ERROR_000003e9`), retornava `al = 0`, e pulava a instrução `mov dword ptr [eax + 0x64], 0`.
- O valor obrigatório no offset 18 é **`0x00A40221` (uint32 Little-Endian `b'\x21\x02\xa4\x00'`)**, acompanhado de `ResultCode = 0` no offset 16.
- Ao receber `0x00A40221`, o cliente entra no ramo `0x10191cbd`, executa a transição de estado da tela para o Lobby e retorna `al = 1`, limpando imediatamente o overlay `"please wait"`.

---

## 2. Pacotes Adicionais Descobertos e Mapeados

### 2.1 Keepalive Ping (`0x20084`)
- Desmontado em `TheRaw.exe` VA `0x004fd6f0` e `0x004fdcb0`.
- Tamanho: 24 bytes (16 bytes cabeçalho Hermit + 2 DWORDs com timestamps do cliente).
- Resposta exigida pelo servidor: `0x20083` (Pong, 20 bytes).

### 2.2 S2Rebirth ApexGuard Heartbeat (`0x5A0101` e `0x5A0102`)
- Localizado na seção injetada `.s2kl` de `GameClient.dll` em VA `0x1058c1f0` e `0x1058c310`.
- A cada 5 segundos, o cliente envia `0x5A0101` (62 bytes) contendo o nonce e PID da sessão.
- O handler registrado em `0x1058c310` espera a resposta do servidor com ID `0x5A0102` (48 bytes: 16 cabeçalho + 32 payload).
- O cliente copia os 32 bytes para a memória compartilhada `[edi + 0x50]` e executa `inc dword ptr [edi + 0x40]` para manter o watchdog do jogo vivo.

---

## 3. Implementação das Correções

1. **Servidor Hermit (`scripts/d187-mock-server.py`)**:
   - Definido `ACCOUNT_ID_SUCCESS = 0x00A40221`.
   - `build_login_success_response` empacota `0x00A40221` no offset 18 e `0` no offset 16.
   - Adicionado handler de Ping `0x20084` respondendo com Pong `0x20083`.
   - Adicionado handler de Heartbeat `0x5A0101` respondendo com `0x5A0102` (48 bytes).
   - Integração com o banco de dados `targets/district-187/data/s2rebirth.db`: consulta dados reais de usuários (`users`) carregando Nickname, Patente (Rank 1 a 58), EXP, Gold, Cash, Kills, Deaths e Headshots.

2. **Launcher Gráfico Moderno (`scripts/d187_launcher.py` e `iniciar_launcher.bat`)**:
   - Interface Tkinter nativa com tema Dark/Amber estilo District 187.
   - Alternância entre **Modo Solo (Bots de IA)** e **Modo Online / LAN (Amigos)**.
   - Seletor de mapas (Arrival, Two Way, Kill Port, Old Town, Ghost Ship, Dust 2, etc.).
   - Seletor de dificuldade dos bots (Recruta, Veterano, Elite).
   - Verificador de status em tempo real do Servidor Hermit com botão de reinício automático.
   - Botão direto para o Web Portal.

3. **Web Portal Standalone (`scripts/d187_web_portal.py` na porta 8080)**:
   - Construído com FastAPI e Tailwind CSS.
   - 100% bilíngue (Alternância instantânea PT-BR / EN).
   - Arsenal VIP com 185 armas extraídas do banco com estatísticas de dano, precisão, cadência e pente.
   - Tabela de classificação (Leaderboard) com dados de K/D, EXP e patentes militares.
   - Registro de novas contas conectado diretamente ao banco SQLite.

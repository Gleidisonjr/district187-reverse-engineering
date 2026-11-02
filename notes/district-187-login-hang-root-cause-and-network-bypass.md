# Análise de Engenharia Reversa: Diagnóstico do Carregamento Infinito de Login e Bypass de Rede Hermit

## 1. Contexto e Sintoma
Ao iniciar o cliente nativo do *District 187: Sin Streets* (`TheRaw.exe`) via `launch_original_game.bat`, a interface visual autêntica em Scaleform Flash (`Menu.gfx`) carregou perfeitamente. No entanto, ao inserir qualquer credencial nos campos de usuário/senha e clicar no botão "Login", o jogo entrava em um estado de carregamento infinito (*infinite loading spinner*), sem disparar pacotes de rede para o servidor mock local (`127.0.0.1:12000`).

---

## 2. Investigação e Descoberta da Causa-Raiz (Root Cause)

### 2.1 Análise do fluxo em `GameClient.dll`
O evento de clique do Scaleform Flash aciona a chamada C++ em `GameClient.dll`:
- Método de delegate: `0x100d73d0`
- Leitura dos parâmetros de rede em `0x100d7964`:
  ```assembly
  0x100d796e: mov edx, [ecx]
  0x100d7970: mov eax, [0x10548a08]  ; CVar gs_port
  0x100d7975: mov edx, [edx + 0x134] ; GetConsoleVarFloat(gs_port)
  0x100d797c: call edx
  0x100d797e: fstp dword ptr [esp + 0x6c] ; porta como float
  ...
  0x100d7999: mov edx, [0x105489fc]  ; CVar gs_ip
  0x100d799f: mov eax, [eax + 0x13c] ; GetConsoleVarString(gs_ip)
  0x100d79a6: call eax
  0x100d79a8: mov edi, eax           ; ponteiro para a string IP
  0x100d79aa: test eax, eax
  0x100d79ac: jne 0x100d79b3
  0x100d79ae: mov edi, 0x10482c87    ; Fallback para string VAZIA ("")!
  ```

### 2.2 Por que os argumentos de linha de comando foram ignorados?
A engine LithTech Jupiter EX (`TheRaw.exe`) **não faz parsing de variáveis de console arbitrárias com prefixo `+`** diretamente da linha de comando na inicialização. As variáveis de console (`CVars`) são lidas estritamente de arquivos de configuração (`settings.cfg` e `autoexec.cfg`).
Como `gs_ip` não estava presente no `settings.cfg`, a variável de console permaneceu nula (`0x0`).

### 2.3 O Abort Silencioso em `CGameServerConnectMgr::Connecting()`
Em `0x100528b0` (`CGameServerConnectMgr::Connecting()`), a função valida o tamanho da string IP recebida:
```assembly
0x100528f0: mov cl, byte ptr [eax]
0x100528f2: inc eax
0x100528f3: test cl, cl
0x100528f5: jne 0x100528f0
0x100528f7: sub eax, edx ; strlen(szIP)
0x100528f9: jne 0x1005292c ; se strlen != 0, conecta!
; Se strlen == 0:
0x10052904: push 0x10488868 ; "CGameServerConnectMgr::Connecting() - empty szIP!!"
0x10052909: call eax       ; Debug log
; Retorna imediatamente sem abrir socket TCP e sem emitir erro para a UI PureMVC Flash!
```
Como resultado, a UI Flash permanecia indefinidamente no estado `CLIENT_REQUEST_LOG_IN` / `loadingScreenOpen`.

---

## 3. Solução Implementada

### 3.1 Patch Binário Atômico em `GameClient.dll`
Para garantir que o cliente **sempre** direcione a conexão para o backend mock local `127.0.0.1:12000`, independente de configurações externas ou parâmetros de linha de comando:
1. **Endereço do Patch:** `0x100d7964` (offset em arquivo: `0xd6d64`)
2. **Bytecode Original (79 bytes):** rotina de leitura de CVars `gs_port` e `gs_ip` com fallbacks nulos.
3. **Bytecode Patcheado (79 bytes):**
   ```assembly
   0x100d7964: bf 5c c8 49 10          mov edi, 0x1049c85c    ; Ponteiro fixo para string "127.0.0.1"
   0x100d7969: c7 44 24 6c 00 80 3b 46 mov [esp+0x6c], 12000.0f ; Porta 12000 em float IEEE 754
   0x100d7971..0x100d79b2: 90 ... 90   nop (66 bytes)
   ```
4. **Preservação:** Backup original criado em `targets/district-187/client/S2/Game/GameClient.dll.original`.

### 3.2 Criação do `autoexec.cfg`
Criado arquivo `autoexec.cfg` no diretório raiz do cliente LithTech (`targets/district-187/client/S2/autoexec.cfg`) contendo:
```ini
"gs_ip" "127.0.0.1"
"gs_port" "12000"
"LoginDevMode" "0"
```

### 3.3 Aprimoramento do Mock Server Hermit (`scripts/d187-mock-server.py`)
- Mapeado o pacote `CQ_JoyGameLogin` (`0x110111`, Opcode `0x0062`):
  - Extrai e exibe o nome de usuário autenticado diretamente do buffer de 33 bytes.
- Mapeado o pacote de resposta `SA_JoyGameLogin` (`0x110112`, Opcode `0x0062`):
  - `ResultCode` = 0 (Sucesso)
  - `AccountID` = 1001 (campo obrigatório validado por `IsPacketerrorMessage` em `0x10191768`)
  - `ServerIP` = 127.0.0.1
  - `ServerPort` = 12000
  - `SessionKey` = `D187_SESSION_KEY`
  - Ao receber este pacote, o client executa `0x100d74db`, definindo a flag de carregamento para 0 e fechando o spinner de loading para liberar a transição de telas.

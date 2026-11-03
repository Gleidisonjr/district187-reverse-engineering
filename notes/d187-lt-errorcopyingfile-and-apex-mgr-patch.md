# Resolução de LT_ERRORCOPYINGFILE e Neutralização do CApexMgr no District 187

## 1. Erro LT_ERRORCOPYINGFILE DLL Error : 0

### Sintoma
Ao iniciar `TheRaw.exe`, uma caixa de diálogo nativa do motor LithTech Jupiter EX exibia:
```text
Title: InitClientShellDE
Message: LT_ERRORCOPYINGFILE  DLL Error : 0
```

### Investigação e Engenharia Reversa (Assembly de `TheRaw.exe`)
A rotina `InitClientShellDE` (`0x492f6e` a `0x493045`) processa a inicialização da DLL de cliente:
```assembly
0x492f9d: push 0x7f21f8                ; "+clientdll"
0x492fa2: call dword ptr [eax + 0x14]  ; Procura argumento +clientdll
0x492fa5: mov dword ptr [0x85fe7c], eax ; Salva ponteiro da string
0x492faa: cmp dword ptr [0x85fe7c], ebx
0x492fb0: jne 0x492fbc
0x492fb2: mov dword ptr [0x85fe7c], 0x7f21e8 ; Default: "GameClient.dll"
0x492fbc: lea eax, [ebp - 4]
0x492fbf: push eax
0x492fc0: push 0x105
0x492fc5: lea eax, [ebp - 0x110]
0x492fcb: push eax
0x492fcc: push dword ptr [0x85fe7c]   ; Nome da DLL
0x492fd5: call 0x4236e0
0x492fdc: call 0x423019                ; Busca nos arquivos montados e diretório raiz
0x492fe1: test al, al
0x492fe3: jne 0x49304a                 ; Sucesso -> avança para LoadLibrary
0x492fe5: call GetLastError            ; Retorna 0
0x492ff2: push 0x7f21a0                ; "LT_ERRORCOPYINGFILE  DLL Error : %d"
0x492ff8: call wsprintfW
0x49303a: call MessageBoxW            ; Exibe pop-up de erro
```

### Causa Raiz
1. `GameClient.dll` estava localizada estritamente na subpasta `targets/district-187/client-rebirth/Game/GameClient.dll`.
2. Não havia uma cópia de `GameClient.dll` na pasta raiz (`targets/district-187/client-rebirth/GameClient.dll`).
3. Quando `TheRaw.exe` assumia o padrão `GameClient.dll` (ou recebia `-arch game` em vez de `-archcfg Default.archcfg`), a função de montagem `0x423019` procurava o arquivo no diretório raiz e nos arquivos compactados `.Res00`. Como não encontrava, retornava `0` e gerava o pop-up `LT_ERRORCOPYINGFILE  DLL Error : 0`.

### Solução Aplicada
1. Cópia cirúrgica de `GameClient.dll` para o diretório raiz de `client-rebirth`:
   - `targets/district-187/client-rebirth/GameClient.dll`
2. Configuração explícita de `-archcfg Default.archcfg +clientdll Game\GameClient.dll` em todos os scripts inicializadores:
   - [`launch_game.bat`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/launch_game.bat)
   - [`targets/district-187/client-rebirth/launch_game_ultra_hd.bat`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/targets/district-187/client-rebirth/launch_game_ultra_hd.bat)
   - [`scripts/d187_launcher.py`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/scripts/d187_launcher.py)

---

## 2. REA do Launcher do S2 Rebirth e Anticheat

### Análise de Fontes do `S2Launcher.exe` (.NET C#)
Localizado em `targets/district-187/s2rebirth-launcher-src/kaynak/`:
1. **Credenciais no Launcher:** O launcher do S2 Rebirth apenas solicita login para o vínculo com o Discord (`DiscordBaglaPenceresi` em `AnaPencere.cs` e `DiscordVarlik.cs`). Ele **não** passa credenciais nem tokens via linha de comando para o jogo.
2. **Execução do Jogo:** A função `OyunuBaslat()` em `AnaPencere.cs` simplesmente dispara `TheRaw.exe` com:
   ```cmd
   TheRaw.exe -arch game -windowtitle "D187" +gs_ip <ip> +gs_port 12000
   ```
   A tela de login com usuário e senha roda 100% nativa em Scaleform Flash dentro de `TheRaw.exe`.
3. **Ponte de Anticheat (`ApexKanal.cs`):**
   - O launcher mantinha um processo sentinela em segundo plano (`ApexKanal`) escutando uma memória compartilhada `Local\ApexRing_%u` gravada pelo `ApexGuard.dll` injetado no jogo.
   - O `ApexKanal` enviava os batimentos cardíacos para o site `https://s2rebirth.com/apex-rapor` via requisições HTTP POST a cada 5 segundos.

---

## 3. Neutralização Definitiva do CApexMgr no Jogo

### Descoberta em `GameClient.dll`
No despacho do pacote `SN_LockEnd` (`0x210121`), a função de callback em `0x10032f30` executa:
```assembly
0x10032f73: call 0x1004b8a0    ; CSceneMgr::SetScene (muda de CLoginScene para CServerListScene)
0x10032f78: call 0x10030c30
0x10032f7d: mov ecx, eax
0x10032f7f: call 0x10010750    ; CApexMgr::Start()
0x10032f84: test al, al
0x10032f86: jne 0x10033239     ; Sucesso -> Prossegue para o Lobby
0x10032f8c: push edi
0x10032f8d: push 0x104870a4    ; "Error"
0x10032f92: push 0x10487074    ; "Failed CApexMgr.Start"
0x10032f97: push edi
0x10032f98: call MessageBoxW   ; Trava ou aborta se CApexMgr falhar
```

Internamente, `0x10010750` (`CApexMgr::Start()`):
- Imprimia `[Apex] Start1!`.
- Disparava thread de rede em `0x103e6050` (`0x100106d0`), que tentava se conectar ao pipe do ApexGuard.
- Sem o anticheat ativo, essa thread ficava bloqueada ou fazia o login ficar na tela de carregamento infinito.

### Patch Cirúrgico de Bypass
Modificado o ponto de entrada de `CApexMgr::Start` (`0x10010750`, offset de arquivo `0xfb50` em `GameClient.dll`):
```text
Antes:  56 8b f1 80 3e 00 75 3d ...
Depois: b0 01 c3 (mov al, 1; ret)
```
- Efeito: `CApexMgr::Start()` retorna imediatamente `TRUE` (1). Nenhuma thread secundária do Apex é criada, nenhuma chamada de IPC para o anel é feita, `m_bIsStart` permanece `0`, e `CApexMgr::Update()` / `Flush()` ignoram o processamento sem consumir CPU.
- Aplicado simultaneamente em:
  - `targets/district-187/client-rebirth/Game/GameClient.dll`
  - `targets/district-187/client-rebirth/GameClient.dll`

---

## 4. Resumo da Purificação de Runtimes

| Componente | Estado Anterior | Estado Final Purificado |
|---|---|---|
| `D3DX9_43.dll` | Proxy ApexGuard de 119 KB | DirectX 9 genuíno Microsoft de 1.998.168 bytes (`DxBase.dll`) |
| `StringEditRuntime.dll` | Proxy ApexGuard | Runtime nativo LithTech de 23.568 bytes (`strbase.dll`) |
| `GameDatabase.dll` | Proxy ApexGuard | Runtime nativo LithTech de 138.768 bytes (`dbbase.dll`) |
| `ApexGuard.dll` | Ativo em memória | Desativado e renomeado para `ApexGuard.dll.disabled` |
| `GameClient.dll` (`0x54D0A0`) | Chamada IPC `.s2kl` ao ApexRing | Neutralizado com `0xC3` (`RET`) |
| `GameClient.dll` (`0xfb50`) | `CApexMgr::Start` (criação de threads) | Neutralizado com `\xb0\x01\xc3` (`mov al, 1; ret`) |

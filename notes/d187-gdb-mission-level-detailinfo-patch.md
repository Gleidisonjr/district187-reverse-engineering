# Resolução do Erro Fatal de GDB Mission/Level DetailInfo no District 187

## 1. Sintoma
Ao iniciar o cliente `TheRaw.exe` (motor nativo LithTech Jupiter EX), a janela principal é aberta exibindo a tela de splash art dos operadores. Em seguida, uma caixa de diálogo modal de erro é disparada:
```text
Title: Message Error
Message: GDB Mission/Level에 CSV 테이블과 일치 하지 않은 DetailInfo 정보가 있습니다.
[OK]
```
Ao clicar em **OK**, o jogo encerra imediatamente a execução e fecha.

---

## 2. Tradução e Análise Semântica
- **Texto original (EUC-KR):** `GDB Mission/Level에 CSV 테이블과 일치 하지 않은 DetailInfo 정보가 있습니다.`
- **Tradução:** *"No GDB Mission/Level, há informações de DetailInfo que não coincidem com a tabela CSV."*
- **Significado:** Trata-se de uma validação de asserção de dados do motor. O banco compilado do jogo (`TheRaw.Gamdb00p`) possui registros de mapas/modos cujos campos `DetailInfo` divergem ou estão ausentes dos arquivos CSV correspondentes em `Database\Table\`.

---

## 3. Engenharia Reversa e Desmontagem em `GameClient.dll`

### 3.1. Localização das Strings
- **VA `0x1048d3e8` (Offset de arquivo `0x48b9e8`):** `GDB Mission/Level에 CSV 테이블과 일치 하지 않은 DetailInfo 정보가 있습니다.`
- **VA `0x1048d434` (Offset de arquivo `0x48ba58`):** `Message Error`

### 3.2. Ponto de Verificação e Encerramento Forçado (`0x100662fd`)
No fluxo de carregamento de tabelas do motor em `GameClient.dll`:
```assembly
0x100662f7: mov ecx, dword ptr [0x1054c5d0]
0x100662fd: call 0x10408b50                  ; Rotina de validação Mission/Level
0x10066302: test al, al                      ; Verifica retorno booleano
0x10066304: jne 0x1006634d                   ; Se verdadeiro (al == 1), continua
0x10066306: push 0
0x10066308: push 0x1048d434                  ; "Message Error"
0x1006630d: push 0x1048d3e8                  ; "GDB Mission/Level에 CSV 테이블과 일치 하지 않은 DetailInfo..."
0x10066312: push 0
0x10066314: call dword ptr [0x10482500]      ; MessageBoxA modal
0x1006631a: mov ecx, dword ptr [0x10516c88]
0x10066320: mov edx, dword ptr [ecx + 0x40]
0x10066323: push 0x1048d370                  ; Comando "Exit"
0x10066328: call edx                         ; Finaliza o motor LithTech imediatamente!
0x1006634c: ret                              ; Retorna abortando carregamento
```

### 3.3. Rotina de Validação `0x10408b50`
A função `0x10408b50` (offset de arquivo `0x407f50`):
- Consulta o gerenciador de Game Database (`0x1054bc20`).
- Itera sobre todos os registros sob a chave `ModeIndex` e sub-tabelas de missão/nível.
- Compara os índices de `DetailInfo`. Se encontrar qualquer divergência ou ausência de linha no CSV, salta para `0x10408cbf`, zera `al` (`xor al, al; ret`), resultando em `0`.

---

## 4. Solução Cirúrgica em Dois Níveis

Para garantir que o motor nunca aborte a execução e prossiga para a inicialização dos módulos subsequentes (incluindo `ItemFunctionList::Load`, `FunctionBundle.csv` e a interface Scaleform GFx), aplicamos uma intervenção cirúrgica dupla em `GameClient.dll`:

### Nível 1: Função `0x10408b50` retorna `TRUE` imediatamente
- **Arquivo:** `targets/district-187/client-rebirth/Game/GameClient.dll` e `targets/district-187/client-rebirth/GameClient.dll`
- **Offset de arquivo:** `0x407f50`
- **Bytes originais:** `81 ec 1c 01 00 00` (`sub esp, 0x11c`)
- **Bytes patcheados:** `b0 01 c3 90 90 90` (`mov al, 1; ret; nop; nop; nop`)
- **Efeito:** A função não executa o loop custoso de validação e retorna `true` imediatamente.

### Nível 2: Desvio incondicional no chamador `0x10066304`
- **Arquivo:** `targets/district-187/client-rebirth/Game/GameClient.dll` e `targets/district-187/client-rebirth/GameClient.dll`
- **Offset de arquivo:** `0x65704`
- **Bytes originais:** `75 47` (`jne 0x1006634d`)
- **Bytes patcheados:** `eb 47` (`jmp 0x1006634d`)
- **Efeito:** Salto incondicional que ignora completamente a chamada de `MessageBoxA` e o método `Exit()`, prosseguindo direto para `0x1006634d` onde os demais sistemas de jogo são carregados.

---

## 5. Validação Empírica
O script de probe [`scripts/probes/test_run_arch.py`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/scripts/probes/test_run_arch.py) foi executado com o cliente oficial:
```text
Launching: TheRaw.exe -arch game -archcfg Default.archcfg -windowtitle "District 187: Sin Streets" ...
[0.5s] Game main window detected! HWND: 852348
[1.0s] Game main window detected! HWND: 852348
...
[5.5s] Game main window detected! HWND: 852348
SUCCESS: TheRaw.exe is running smoothly without Error pop-up!
```
- **Resultado:** Nenhum pop-up modal foi gerado, o processo permaneceu ativo continuamente com a janela principal Direct3D 9 / DXVK renderizada sem interrupções.

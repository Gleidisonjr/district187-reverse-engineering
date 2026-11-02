# District 187 — Engenharia Reversa do Fluxo de Execução, Proxy DLL e Redirecionamento

## O que foi descoberto
Investigação detalhada via trace de depuração em tempo real (`ctypes.windll.kernel32`) e inspeção de PE do cliente `TheRaw.exe` e DLLs satélites.

Identificou-se a cadeia de injeção utilizada pela comunidade de servidores privados, o manipulador de saída do cliente Joygame e as flags internas de desenvolvimento para inicialização e conexão.

## Evidência e Mecanismos

### 1. Injeção por Proxy DLL (`D3DX9_43.dll` -> `TheRawExt.dll`)
- A DLL `D3DX9_43.dll` distribuída com o cliente privado não é o runtime original da Microsoft. Ela foi modificada com uma entrada de importação extra apontando para `TheRawExt.dll` (função `load`).
- Quando `TheRaw.exe` inicializa o Direct3D 9, ele carrega localmente `D3DX9_43.dll`, que por sua vez aciona o `DllMain` de `TheRawExt.dll`.
- `TheRawExt.dll` contém código virtualizado/ofuscado e um servidor HTTP embarcado (`httplib::Server`) para interceptação de tráfego.
- **Resolução:** Substituição pelo binário limpo e oficial `C:\Windows\SysWOW64\d3dx9_43.dll`, removendo a dependência da DLL ofuscada e evitando acessos inválidos de memória (`0xC0000005`).

### 2. O Handler de Saída Joygame (`ShellExecuteA`)
- No procedimento de término de sessão em `GameClient.dll` (offset `0x2359f1`), a engine executa:
  ```assembly
  push 5                                ; SW_SHOW
  push 0x10482c87                       ; lpDirectory = ""
  push 0x10482c87                       ; lpParameters = ""
  push 0x104aa2b0                       ; lpFile = "http://www.joygame.com/games.aspx?g=17"
  push 0x10495fe4                       ; lpOperation = "open"
  push 0                                ; hwnd = NULL
  call [ShellExecuteA]
  ```
- Isso explica por que qualquer encerramento do cliente (inclusive ausência de sessão) abria o navegador no site da publicadora turca Joygame.

### 3. Modos de Inicialização e Flags de Desenvolvedor
No endereço `0x104ab58c` de `GameClient.dll`, foram mapeadas variáveis de console (cvars) exclusivas para testes de engine:
- `+LoginDevMode 1`: Ativa o modo de login local para depuração interna de desenvolvedor, ignorando requisições web do launcher.
- `+Windowed 1`: Força a janela Direct3D em modo janela em vez de fullscreen exclusivo.
- `+ScreenWidth 1024 +ScreenHeight 768`: Resolução configurável diretamente na linha de comando.
- `+gs_ip <IP>` e `+gs_port <PORT>`: Redireciona o tráfego do socket para o servidor de partidas.

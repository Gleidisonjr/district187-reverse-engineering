# District 187 — Arquitetura de Inicialização e Parâmetros de Rede

## O que foi descoberto
Engenharia reversa do fluxo de inicialização e comunicação do cliente *District 187* através da inspeção do executável gerenciado `LauncherApp.exe`, da DLL nativa `TheRawExt.dll` e do executável central `TheRaw.exe`.

Descobriu-se a linha de comando exata esperada pelo motor do jogo para conexão a servidores de partida, além de todo o catálogo de balanceamento de armas em formato CSV limpo.

## Evidência

### 1. Linha de Comando do Jogo (`TheRaw.exe`)
A partir da inspeção dos endpoints remotos consultados pelo launcher em `https://raw.githubusercontent.com/cdgame-w/conf/main/args`, a sintaxe oficial de inicialização do executável foi recuperada:

```powershell
TheRaw.exe -arch game -windowtitle "D187" +gs_ip <SERVER_IP> +gs_port <SERVER_PORT>
```

- `-arch game`: especifica a montagem dos pacotes descritos em `Default.archcfg` (`game\Game.Res00`, `game\Update_1.Res00`, `game\Update_2.Res00`).
- `-windowtitle "D187"`: título da janela Direct3D.
- `+gs_ip`: IP do servidor de jogo (Game Server IP). Valor padrão de teste da comunidade privada: `93.158.236.130`.
- `+gs_port`: Porta UDP/TCP do Game Server. Porta oficial: `12000`.

### 2. Papel de `TheRawExt.dll` (Hooking em Tempo de Execução)
- Arquivo compilado em 2025 (`3449B226841C31967E488BAEDF43A3CE7E2153EC7C91FFD7566E42C354BAFBCB`).
- Exporta a função `load`.
- Importa funções de injeção e manipulação de memória de `KERNEL32.dll` (`VirtualProtect`, `FlushInstructionCache`, `CreateToolhelp32Snapshot`, `Thread32First`, `Thread32Next`, `SuspendThread`, `ResumeThread`, `GetThreadContext`, `SetThreadContext`) e resolução de socket `WS2_32.dll` (`inet_addr`, `inet_ntoa`).
- **Conclusão:** Atua como um proxy/hook em memória carregado para interceptar e redirecionar chamadas de socket do `TheRaw.exe` sem necessidade de alterar o código estático original do jogo.

### 3. Tabela de Armas Extraída (`WeaponInfo.csv`)
- Todas as armas do jogo foram extraídas com atributos detalhados:
  - `ItemIndex`: Identificador numérico do item (ex: `1110002` = M4A1, `1120001` = AK47, `1140003` = AWM300).
  - `Damage`: Dano base por projétil.
  - `Pitch` e `Delay`: Cadência e recuo vertical.
  - `Accuracy` e `Range`: Dispersão e alcance efetivo.
  - `LoadMin` e `LoadMax`: Capacidade do carregador e munição reserva.

## Limitações
- As structs de pacotes de dados de login (handshake, autenticação e seleção de canais/salas) ainda precisam ser mapeadas inspecionando os procedimentos de `WSASend` / `WSARecv` no `TheRaw.exe` e `GameClient.dll`.

## Próximos Passos
1. Criar um mock em Python de socket UDP/TCP ouvindo na porta `12000` para capturar os primeiros pacotes de handshake emitidos por `TheRaw.exe`.
2. Analisar no Ghidra/REA os manipuladores de pacotes de `GameClient.dll` e `GameServer.dll`.

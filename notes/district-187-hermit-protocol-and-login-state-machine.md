# District 187 — Engenharia Reversa do Protocolo de Rede Hermit e Máquina de Estados de Login

## O que foi descoberto
Engenharia reversa profunda do subsistema de rede e despacho de pacotes em `TheRaw.exe` e `GameClient.dll`.
Identificou-se a biblioteca proprietária de rede da engine LithTech/CJ GameLab, denominada **Hermit Network Runtime**, os opcodes exatos dos pacotes de autenticação e o mecanismo interno de transição para o lobby.

## Evidência e Arquitetura

### 1. Biblioteca de Rede Hermit (`Hermit::Runtime`)
A engine utiliza classes orientadas a objetos da arquitetura Hermit:
- `Hermit::Runtime::TCPES::Provider`: Provedor central de socket TCP assíncrono (Winsock2 `WSAConnect` / `WSASend` / `WSARecv`).
- `Hermit::Session::States::HandShake`: Estado inicial de negociação de chave criptográfica e sincronização de tempo.
- `Hermit::Session::States::Connect`: Estado de conexão estabelecida.
- `Hermit::Session::States::Online` / `Hermit::Session::States::Offline`: Ciclo de vida da sessão.
- `Hermit::Object::Crypt::CRC::Factory`: Gerador de checagem de integridade e criptografia básica dos payloads de pacotes.

### 2. Tabela de Opcodes e Mapeamento de Pacotes de Identidade (`tPacket_NAccount_NIdentity`)
No endereço de memória `0x10058498` em `GameClient.dll`, recuperou-se a tabela de despacho completa de pacotes:

| Packet ID (Hex) | Opcode Interno | Nome do Pacote Canônico | Direção | Finalidade |
|-----------------|----------------|--------------------------|---------|------------|
| `0x110101` | `0x034d` | `tPacket_NAccount_NIdentity_CQ_Login` | Cliente -> Servidor | Login em modo desenvolvedor (`+LoginDevMode 1`) |
| `0x110102` | — | `tPacket_NAccount_NIdentity_SA_Login` | Servidor -> Cliente | Resposta de login modo desenvolvedor |
| `0x110111` | `0x0062` | `tPacket_NAccount_NIdentity_CQ_JoyGameLogin` | Cliente -> Servidor | Login oficial de produção (Joygame / Netmarble) |
| `0x110112` | — | `tPacket_NAccount_NIdentity_SA_JoyGameLogin` | Servidor -> Cliente | Resposta de autenticação oficial com credenciais |
| `0x110121` | — | `tPacket_NAccount_NIdentity_CN_NetmarbleLoginData` | Notificação | Metadados de sessão do usuário |
| `0x110122` | — | `tPacket_NAccount_NIdentity_CN_NetmarbleLoginPCInfo` | Notificação | Informações de hardware/MAC da máquina cliente |
| `0x110123` | — | `tPacket_NAccount_NIdentity_SA_NetmarbleLogin` | Servidor -> Cliente | Confirmação de login Netmarble Global |
| `0x110124` | — | `tPacket_NAccount_NIdentity_CQ_Join` | Cliente -> Servidor | Requisição de ingresso em canal/sala de jogo |
| `0x110125` | — | `tPacket_NAccount_NIdentity_SA_Join` | Servidor -> Cliente | Confirmação de entrada na sala |
| `0x110151` | — | `tPacket_NAccount_NIdentity_CQ_MenaLogin` | Cliente -> Servidor | Autenticação no gateway MENA (Oriente Médio) |
| `0x110152` | — | `tPacket_NAccount_NIdentity_SA_MenaLogin` | Servidor -> Cliente | Resposta no gateway MENA |

### 3. Mecanismo de Inicialização e Bypass de Privilégios
- `TheRaw.exe` embute um manifesto UAC exigindo elevação de Administrador (`requireAdministrator`), gerando `WinError 740` em execuções padrão.
- **Bypass comprovado:** Definir a variável de ambiente `__COMPAT_LAYER=RunAsInvoker` desativa o pedido de elevação e permite execução transparente.
- A linha de comando canônica oficial é:
  ```powershell
  TheRaw.exe -arch game -windowtitle "D187" +gs_ip 127.0.0.1 +gs_port 12000
  ```

### 4. Ciclo de Vida do Cliente e Transição de Tela
- O cliente inicializa 11 gerenciadores principais em sequência (`FunctionTimer`, `Stock`, `User`, `ActivateItem`, `GameAddiction`, `StringTable`, `FlashState`, `NMCrypt`, `WebBrowser`, `SteamWebBrowser`).
- Os dados do perfil do jogador são persistidos com sucesso em `Profiles/Profile000.gdb`.
- Em seguida, o cliente aciona o socket Hermit conectando à porta `12000` via TCP. Ao receber `SA_JoyGameLogin` (`0x110112`), o cliente transiciona da tela de introdução para o menu principal/lobby.

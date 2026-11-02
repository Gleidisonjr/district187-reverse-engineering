# S2 Rebirth: Arquitetura do Cliente e Abordagem Híbrida (Opção C)

## Contexto & Descoberta
O executável antigo obtido de um arquivo do YouTube apresentava congelamento infinito no login devido a cvars de rede não inicializadas (`+gs_ip` vazio em `CGameServerConnectMgr::Connecting()`) e proxies injetados apontando para IPs extintos (`93.158.236.130`).

Ao investigar o projeto ativo da comunidade [S2 Rebirth](https://s2rebirth.com/), realizamos a engenharia reversa completa da infraestrutura de distribuição do cliente, do launcher open-source em C# e do protocolo de autenticação.

---

## 1. Engenharia Reversa da Infraestrutura S2 Rebirth

- **CDN & Armazenamento de Objetos:**
  - Endpoint de manifesto: `https://gamefiles.mdcreative.tr/manifest.json` (Versão `2026.11.02.2013`, 291 arquivos).
  - Todos os arquivos são armazenados com compactação Gzip no padrão CAS (Content-Addressed Storage): `https://gamefiles.mdcreative.tr/objects/{sha256}`.
  - O instalador oficial `S2RebirthKurulum.exe` é um stub compilado em .NET que consome este manifesto.

- **Reutilização Inteligente de Dados:**
  - O arquivo primário de dados `Game/Game.ResDt` (1.031.940.994 bytes / 984 MB) e os arquivos de patch `Update_1.ResDt` (26 MB) e `Update_2.ResDt` (67 MB) são **100% idênticos em hash SHA-256** aos arquivos originais do LithTech Jupiter EX.
  - Implementamos um montador multithread em Python ([`scripts/setup_s2rebirth_client.py`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/scripts/setup_s2rebirth_client.py)) que reutiliza via hardlink NTFS os 1,07 GB de dados locais já existentes e baixa apenas os 36,29 MB de executáveis e DLLs atualizados.

- **Pacote de Idioma Inglês:**
  - O projeto S2 Rebirth hospeda um pacote oficial em inglês em `https://gamefiles.mdcreative.tr/en/manifest.json` (246 arquivos).
  - O pacote substitui diretamente as texturas da interface Flash (`Game/Interface/Flash/*.dds`, `Menu.gfx`), o áudio de locução (`Game/FMOD/Data/System.fsb`) e injeta os textos em inglês em `Game/StringDatabase/Turkey/TheRaw.Strdb00p`.
  - Ativamos a configuração global em `.launcher/paket.json` com `{"dil": "en"}` para inicializar o launcher e jogo em inglês por padrão.

---

## 2. Diferenças Binárias & Mecanismo de Anti-Cheat ApexGuard

- **`TheRaw.exe`:**
  - Comparação byte-a-byte revelou apenas **1 byte de diferença** no cabeçalho PE (`0x146`): de `0x0002` para `0x0022` (`IMAGE_FILE_LARGE_ADDRESS_AWARE`), permitindo alocação de até 4 GB de memória RAM em sistemas x64.
- **`ApexGuard.dll` e `D3DX9_43.dll`:**
  - `D3DX9_43.dll` atua como proxy DLL na inicialização do executável, carregando o módulo de integridade `ApexGuard.dll`.
  - `ApexGuard` monitora integridade em memória e reporta via memória compartilhada IPC para o `S2Launcher.exe` através da classe `ApexKanal.cs`.
- **Servidor Ativo da Comunidade:**
  - Endereço oficial: `179.61.147.154:12000`
  - Portal de Cadastro: `https://s2rebirth.com/kayit`

---

## 3. Abordagem Híbrida Implementada (Opção C)

Para atender simultaneamente à **jogabilidade autêntica online** e à **preservação offline / engenharia reversa para portfólio**:

1. **Ambiente Online (S2 Rebirth):**
   - Diretório: `targets/district-187/client-rebirth/`
   - Inicializador: [`launch_s2rebirth_online.bat`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/launch_s2rebirth_online.bat) (abre `S2Launcher.exe`) ou [`launch_s2rebirth_direct.bat`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/launch_s2rebirth_direct.bat) (conecta diretamente a `179.61.147.154:12000`).
   - Idioma: Inglês completo configurado.

2. **Ambiente Offline (Hermit Mock Server / Local Testbed):**
   - Diretório: `targets/district-187/client/S2/`
   - Servidor Mock: [`scripts/d187-mock-server.py`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/scripts/d187-mock-server.py) emulando o handshake de pacotes Hermit (`0x110111` / `0x110112`).
   - Inicializador: [`launch_offline_emulator.bat`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/launch_offline_emulator.bat) conectando a `127.0.0.1:12000`.

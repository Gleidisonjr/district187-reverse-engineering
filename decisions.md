# Decisions

<!-- Um registro por decisão: o que, por quê, quando -->

| Data | Decisão | Motivo |
|------|---------|--------|
| 2026-11-01 | Usar REA como MCP principal para análise | Suporte nativo a binários, APK, JS/Electron, .NET, websites e capturas de rede em um único tool |
| 2026-11-01 | Second Brain com 4 camadas (CLAUDE.md + rules + skills + auto memory) | Evitar reexplicar contexto a cada sessão; manter aderência das regras sem inflar contexto |
| 2026-11-01 | Foco inicial em análise de apps de analytics e coleta de dados | Alinhado ao perfil Meta/Data Analyst — entender como ferramentas concorrentes funcionam internamente |
| 2026-11-02 | Iniciar RE do District 187 (S2 Online) para preservação e base de FPS próprio | Alvo nostálgico do usuário com LithTech engine; viabiliza server emulation e extração de assets para port em engine moderna |
| 2026-11-02 | Desenvolver unpacker Python nativo para o formato LithTech HBEK (.Res00/.ResDt) | Reverter o cabeçalho e estrutura de compressão zlib permitiu extração direta de todos os 13.824 assets sem depender de tools legadas desatualizadas |
| 2026-11-02 | Inspecionar LauncherApp.exe (.NET) para extrair parâmetros de rede | Mais rápido e direto do que desassemblar o TheRaw.exe; revelou porta 12000, argumento `+gs_ip`, `-arch game` e repositório de tabelas CSV |
| 2026-11-02 | Desenvolver conversor MODL v33 (.Model00p) para Wavefront OBJ em Python | Permite portar armas, personagens e mapas diretamente para Godot 4 / Blender preservando coordenadas UV e normais |
| 2026-11-02 | Criar mock server Hermit TCP/UDP na porta 12000 | Capturar em trânsito o handshake do cliente para permitir emulação de login e lobbies sem depender de servidores externos |
| 2026-11-02 | Analisar balanceamento de armas com pandas em script dedicado | Estrutura métricas de dano, alcance e STK das 178 armas em um modelo quantitativo replicável para o projeto de FPS |
| 2026-11-02 | Reconstruir hierarquia canônica de pastas usando a Tabela de Diretórios do .Res00 | A tabela de 2.305 diretórios armazena os caminhos canônicos exatos de todos os 13.824 arquivos em ordem sequencial |
| 2026-11-02 | Substituir proxy DLL modificada D3DX9_43.dll pelo runtime limpo do SysWOW64 | A versão da comunidade continha injeção de TheRawExt.dll que causava crash 0xC0000005 em Windows 11 moderno |
| 2026-11-02 | Aprimorar conversor 3D com busca em byte-alignment e rastreio dinâmico de índice | Permitiu converter 526 de 585 modelos (89.9%) com texturas PNG e materiais MTL automáticos |
| 2026-11-02 | Estruturar projeto base Godot 4 em `projects/godot-fps/` | Integra os modelos 3D convertidos, texturas e parâmetros balísticos calibrados diretamente em um FPS jogável |
| 2026-11-02 | Construir arena de combate tática com IA de Bots (TacticalBot) no Godot 4.7 | Fornece experiência jogável offline imediata (Caminho A) com máquinas de estado, LoS raycast, headshots críticos e respawn |
| 2026-11-02 | Publicar repositório público no GitHub com 5 commits atômicos estruturados | Documentação e apresentação profissional do portfólio de Engenharia Reversa, Data Analytics e Gamedev (@Gleidisonjr) |
| 2026-11-02 | Priorizar Caminho B (execução e preservação do cliente original TheRaw.exe) | O usuário validou que recriações genéricas não possuem a fidelidade autêntica do District 187; foco total em fazer o cliente original rodar |
| 2026-11-02 | Aplicar bypass `__COMPAT_LAYER=RunAsInvoker` para inicialização do TheRaw.exe | Contorna o manifesto embutido com `requireAdministrator` sem necessitar de privilégios elevados |
| 2026-11-02 | Reverter a tabela de despacho do protocolo Hermit (offset 0x10058498 em GameClient.dll) | Identificou o mapeamento dos opcodes CQ_JoyGameLogin (0x110111 / 0x0062) e SA_JoyGameLogin (0x110112) para emulação do mock server |

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
| 2026-11-02 | Patch no offset 0x100d7964 de GameClient.dll para forçar 127.0.0.1:12000 | TheRaw.exe ignora `+gs_ip` na linha de comando e abortava silenciosamente com "empty szIP!!", travando o login. O patch garante conexão ao mock server local |
| 2026-11-02 | Patch no offset 0x46e8a6 de GameClient.dll para trocar idioma padrão de Turco para Inglês | Altera a instrução de carregamento do banco de textos de `StringDatabase\Turkey\` para `StringDatabase\English\`, exibindo toda a interface em inglês |
| 2026-11-02 | Adoção da Opção C (Híbrida): Cliente limpo S2 Rebirth online + Mock server local offline | Permite ao usuário jogar online nos servidores ativos da comunidade (179.61.147.154) e ao mesmo tempo preserva o ambiente local mock/emulator no repositório para portfólio |
| 2026-11-02 | Execução da Fase 1: Texturas Ultra HD (1.72 GB), 144+ FPS e gráficos máximos | Ativação dos 6 volumes HD (HD1-HD6) no Default.archcfg, remoção de MipOffset e desbloqueio de MaxFPS para monitores de alta frequência |
| 2026-11-02 | Desenvolver gateway dedicado UDP autoritativo (porta 27888) | Permite responder aos datagramas e pings do cliente LithTech após SN_BattleStart e registrar telemetrias |
| 2026-11-02 | Pipeline em batch de Spatial Combat Heatmaps para todos os 25 mapas | Gera visualizações 2D KDE de densidade de combate, sightlines e choke points com portal unificado de analytics |
| 2026-11-02 | Abertura do alvo de engenharia reversa de formatos colunares (Apache Parquet) | Permite dissecação no nível de bytes do Thrift Compact Protocol e encodings bit-packing alinhados a big data analytics |
| 2026-11-02 | Eliminação de multi-terminais e criação do Launcher Gráfico unificado (Tkinter) | Centraliza seleção de bots, mapas, servidor e gráficos em uma janela moderna Dark/Gold sem poluição de múltiplos terminais |
| 2026-11-02 | Descoberta do código mágico de login 0x00A40221 e Heartbeats 0x20084 / 0x5A0102 | A instrução `0x10191bd0` em `GameClient.dll` exige `0x00A40221` para desativar a flag de bloqueio e entrar no Lobby |
| 2026-11-02 | Criação de Web Portal Standalone bilíngue (FastAPI + Tailwind na porta 8080) | Reproduz o portal do S2 Rebirth de forma independente com alternância instantânea PT-BR/EN, 185 armas, Leaderboard e cadastro |
| 2026-11-02 | Arquivamento de 80 scripts de probe em `scripts/probes/` e `.bat` legados em `legacy_launchers/` | Mantém a raiz do projeto e a pasta de scripts limpas, organizadas e com documentação estruturada |

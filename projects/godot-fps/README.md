# District Tactical FPS (Godot 4.7 Base)

Projeto de shooter tático em primeira pessoa construído no **Godot 4.7**, utilizando a geometria 3D, texturas e tabelas de balanceamento extraídas e revertidas do jogo tático *District 187: Sin Streets* (engine LithTech Jupiter EX).

## Destaques do Projeto
- **IA Tática Completa:** Bots controlados por máquina de estados (`PATROL`, `CHASE`, `ENGAGE`, `TAKE_COVER`, `DEAD`) com detecção por linha de visão (LoS), disparos em rajada tática e multiplicador de headshot (2.5x).
- **Modelos 3D e Texturas Oficiais:** Malhas extraídas dos binários `.Model00p` e texturas `.ResDt` da CJ Games / Netmarble (AK-47, M4A1, AWM-300).
- **Balística e Recuo Procedural:** Sistema de recuo angular vertical e horizontal com mola de recuperação proporcional, dispersão dinâmica dependente do movimento (parado, correndo, no ar, mirando ADS).
- **Interface e HUD Tático:** Retícula com dispersão dinâmica, barra de HP em tempo real, contador de munição pente/reserva, killfeed de eliminações e tela de respawn.

## Estrutura do Projeto
- `project.godot`: Configuração do projeto com action maps configurados (WASD, Mouse Look, Tiro, ADS, Recarga, Pulo, Corrida, Agachamento, 1/2/3 Troca de Arma).
- `launch_game.bat`: Script de inicialização com um clique para Windows.
- `assets/weapons/`:
  - `ak47/`: Malha 3D `AR_AK47.obj`, material `AR_AK47.mtl` e textura `AR_AK47_D.png`.
  - `m4a1/`: Malha 3D `Custom_MAR_M4A1.obj` e textura `Custom_MAR_M4A1_D.png`.
  - `awm/`: Malha 3D `SN_AWM300.obj` e textura `SN_AWM300_D.png`.
- `data/WeaponInfo.csv`: Tabela original de atributos de armas extraída de `Game.Res00`.
- `scripts/`:
  - `fps_controller.gd`: Controlador do jogador com sistema de vida (100 HP), recuo procedural, troca de armas em tempo real, visualização ADS e impacto de dano.
  - `bot_controller.gd`: IA tática para bots (`TacticalBot`) com navegação autônoma `NavigationAgent3D`, mira preditiva e rajadas de tiro.
  - `hud_manager.gd`: Gerenciador de interface de usuário (HUD) para vida, munição, killfeed e overlay de dano.
  - `weapon_data.gd`: Custom Resource definindo dano, cadência (RPM), recuo vertical/horizontal e alcance efetivo.
  - `weapons_loader.gd`: Predefinições calibradas a partir da análise exploratória de dados (AK-47, M4A1, AWM-300).
  - `target_dummy.gd`: Alvos estáticos para teste de registro de dano e alcance efetivo.
- `scenes/`:
  - `player.tscn`: Cena do jogador com corpo de colisão, câmera e montagem do modelo da AK-47.
  - `bot.tscn`: Cena instanciável do bot tático com modelo 3D, colisão e sensores visuais.
  - `main.tscn`: Arena de combate completa com malha de navegação 3D (`NavigationRegion3D`), caixas de cobertura tática, 3 bots ativos em patrulha e dummies de treino.

## Controles Padrão
| Ação | Tecla / Botão |
|---|---|
| Movimentação | W, A, S, D |
| Olhar / Mirar | Movimento do Mouse |
| Disparar | Botão Esquerdo do Mouse |
| Mirar (ADS) | Botão Direito do Mouse |
| Pular / Renascer | Barra de Espaço |
| Correr | Shift Esquerdo |
| Agachar | Ctrl Esquerdo |
| Recarregar | R |
| Trocar para AK-47 | Tecla 1 |
| Trocar para M4A1 | Tecla 2 |
| Trocar para AWM | Tecla 3 |
| Liberar / Capturar Cursor | ESC |

## Calibração de Armas
Os valores de recuo, dano base e cadência foram calculados com base na engenharia reversa de `WeaponInfo.csv`:
- **AK-47:** 34 de dano base (STK 3 em 100 HP), 600 RPM, recuo vertical forte (2.4°), recuperação 7.5.
- **M4A1:** 28 de dano base (STK 4 em 100 HP), 680 RPM, recuo suave (1.6°), alta precisão.
- **AWM-300:** 115 de dano base (STK 1 / One-shot kill), 42 RPM, recuo vertical pesado (6.0°).

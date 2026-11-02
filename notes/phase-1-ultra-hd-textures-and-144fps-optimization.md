# Fase 1: Otimizações Visuais Ultra HD, 144+ FPS e Localização em Inglês

## 1. Visão Geral
Na avaliação inicial do cliente pelo usuário, o jogo apresentava aspecto visual desatualizado e textos em turco. A engenharia reversa das variáveis de console (cvars) e dos arquivos de configuração revelou as causas exatas:
1. `settings.cfg` vinha de fábrica com `"BindTexturesMipOffset" "1.000000"`, o que forçava a engine LithTech a reduzir a resolução de todas as texturas pela metade (mipmap blur).
2. `"GraphicQualityLevel"` estava configurado em nível `1` (Baixo).
3. Efeitos dinâmicos de luz e projeção (`Light_SpotProjector`) estavam desativados (`0`).
4. O cliente não estava carregando o pacote de texturas de alta definição.

---

## 2. Pacote Oficial de Texturas HD (1.72 GB)
Localizamos o repositório oficial de texturas HD em `https://gamefileshd.mdcreative.tr/manifest.json`. O pacote é composto por 12 arquivos (6 pares de arquivos `.Res00` e `.ResDt`):
- `Game/HD1.ResDt` (277.9 MB)
- `Game/HD2.ResDt` (257.6 MB)
- `Game/HD3.ResDt` (322.7 MB)
- `Game/HD4.ResDt` (262.4 MB)
- `Game/HD5.ResDt` (366.6 MB)
- `Game/HD6.ResDt` (234.2 MB)

### Integração na Engine LithTech:
Desenvolvemos o script de download paralelo [`scripts/download_hd_pack.py`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/scripts/download_hd_pack.py), que baixou e validou por SHA-256 os 1.72 GB de texturas e registrou os arquivos no [`Default.archcfg`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/targets/district-187/client-rebirth/Default.archcfg):

```ini
game\\Game.Res00
game\\Update_1.Res00
game\\Update_2.Res00
game\\HD1.Res00
game\\HD2.Res00
game\\HD3.Res00
game\\HD4.Res00
game\\HD5.Res00
game\\HD6.Res00
```
Com essa montagem, a engine Jupiter EX carrega as texturas em alta resolução 2K/4K sobrepostas às texturas originais de 2012.

---

## 3. Desbloqueio de 144+ FPS & Ajustes Ultra
Criamos [`autoexec.cfg`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/targets/district-187/client-rebirth/autoexec.cfg) e atualizamos [`settings.cfg`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/targets/district-187/client-rebirth/settings.cfg) com as seguintes diretrizes:

* **`MaxFPS "0"` e `FpsLimit "0"`:** Remove o limitador de 60 FPS da engine, permitindo taxas de quadros acima de 144 FPS / 240 FPS de acordo com o hardware.
* **`VSyncOnFlip "0"`:** Desliga a sincronização vertical para eliminar latência de entrada (input lag).
* **`ShowFrameRate "1"`:** Exibe o contador de FPS na tela para monitoramento em tempo real.
* **`BindTexturesMipOffset "0"`:** Texturas 1:1 sem compressão de mipmap (elimina borrões).
* **`GraphicQualityLevel "3"`:** Habilita qualidade gráfica máxima da engine.
* **`BFovYWidescreen "1"`:** Cálculo correto de campo de visão (FOV) para monitores 16:9 e ultrawide 21:9.
* **`Light_SpotProjector "1"`:** Projeção realista de luz dinâmica (lanternas, explosões e muzzle flash).

---

## 4. Confirmação do Idioma em Inglês
Inspecionamos os 3.923 registros do banco de strings em [`TheRaw.Strdb00p`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/targets/district-187/client-rebirth/Game/StringDatabase/Turkey/TheRaw.Strdb00p):
- Todos os termos de armas, categorias de menu, acessórios e mensagens de jogo estão 100% em **Inglês** (ex.: *"Change Weapon"*, *"Desert Beret"*, *"Pistol"*, *"Not enough Gold"*).
- A interface Flash (`Menu.gfx`, `Ingame_*.dds`) e os arquivos de voz FMOD (`System.fsb`) estão alinhados e validados.

---

## 5. Como Executar
Basta executar o atalho na raiz:
- [`launch_game_ultra_hd.bat`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/launch_game_ultra_hd.bat)

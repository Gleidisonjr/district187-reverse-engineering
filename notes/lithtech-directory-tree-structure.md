# LithTech Jupiter EX — Arquitetura da Tabela de Diretórios e Extração Canônica (.Res00)

## O que foi descoberto
Engenharia reversa da tabela de diretórios do container LithTech Jupiter EX HBEK (`Game.Res00`). Descobriu-se como a engine organiza internamente a hierarquia de pastas de todos os 13.824 arquivos do jogo, permitindo reconstruir com 100% de precisão o layout canônico de pastas original do projeto.

## Evidência e Estrutura Binária

### 1. Tabela de Diretórios
No cabeçalho de 32 bytes de `Game.Res00`, o campo `num_dirs` armazena o valor `2305`.
A tabela de diretórios está localizada logo após a tabela de arquivos (`32 + str_table_size + (num_files * 48)`).

Cada entrada de diretório possui exatamente **16 bytes**:
- `str_off` (`uint32`): Offset na tabela de strings (após o GUID base de 16 bytes). Aponta para a string ASCII do caminho completo do diretório (ex: `animations\weapons\1_Main`, `weapons\1_main\textures`).
- `child_idx` (`uint32`): Índice do primeiro subdiretório filho (`0xFFFFFFFF` se folha).
- `next_idx` (`uint32`): Índice do diretório irmão (`0xFFFFFFFF` se último).
- `file_cnt` (`uint32`): Quantidade de arquivos contidos sequencialmente neste diretório.

### 2. Mapeamento 1:1 com a Tabela de Arquivos
A soma de todos os `file_cnt` das 2.305 pastas é exatamente `13.824`:
$$\sum_{i=0}^{2304} \text{file\_cnt}_i = 13824 = \text{num\_files}$$

Isso comprova matematicamente que os arquivos na tabela de arquivos de 48 bytes estão dispostos em blocos contíguos ordenados diretório por diretório.

### 3. Implementação e Resultados
Atualizamos [`scripts/extract-lithtech-res.py`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/scripts/extract-lithtech-res.py) para ler a tabela de diretórios e extrair os arquivos reconstruindo automaticamente os caminhos completos.

- Extraídos 1.014 assets completos de armas com integridade de diretórios:
  - `weapons\1_main\world_models\` — malhas 3D
  - `weapons\1_main\textures\` — texturas DDS em alta resolução (DXT5 1024x1024)
  - `weapons\1_main\materials\` — materiais LithTech (`.Mat00`) apontando para as texturas
  - `animations\weapons\1_Main\` — esqueletos e animações das armas

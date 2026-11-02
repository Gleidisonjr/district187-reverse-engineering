# LithTech Jupiter EX — Especificação Reversa do Formato HBEK (.Res00 / .ResDt)

## O que foi descoberto
Engenharia reversa completa do formato de pacotes de assets utilizado pela engine LithTech Jupiter EX em *District 187: Sin Streets* (`Game.Res00` / `Game.ResDt`, `Update_1`, `Update_2`).

Os arquivos de extensão `.Res00` atuam como índice binário (TOC - Table of Contents), enquanto os arquivos `.ResDt` contêm os streams de dados brutos comprimidos via algoritmo zlib/Deflate.

## Evidência e Estrutura Binária

### 1. Cabeçalho do Índice (`.Res00`) — 32 Bytes
O arquivo `.Res00` inicia com um cabeçalho fixo de 32 bytes composto por 8 inteiros de 32 bits little-endian:

| Offset | Campo | Tipo | Valor Observado em `Game.Res00` | Descrição |
|---|---|---|---|---|
| `0x00` | `magic` | `uint32` | `0x4B454248` (`"HBEK"`) | Identificador mágico LithTech HBEK |
| `0x04` | `version` | `uint32` | `2` | Versão do formato de arquivo |
| `0x08` | `str_table_size` | `uint32` | `278.116` bytes | Tamanho da tabela de strings (nomes) |
| `0x0C` | `num_dirs` | `uint32` | `2.305` | Quantidade de diretórios na árvore |
| `0x10` | `num_files` | `uint32` | `13.824` | Quantidade de arquivos arquivados |
| `0x14` | `extra1` | `uint32` | `0` | Reservado / flags de compilação |
| `0x18` | `extra2` | `uint32` | `0` | Reservado |
| `0x1C` | `extra3` | `uint32` | `1` | Reservado / flag de montagem |

### 2. Tabela de Strings
- Inicia imediatamente no offset `0x20` (32 bytes).
- Contém sequências ASCII terminadas em nulo (`\x00`) com caminhos de diretórios e nomes de arquivos.

### 3. Tabela de Arquivos — 48 Bytes por Entrada
Localizada após a tabela de strings (`num_files` × 48 bytes = 663.552 bytes em `Game.Res00`):

| Offset Relativo | Campo | Tipo | Descrição |
|---|---|---|---|
| `0x00` | `str_offset` | `uint32` | Ponteiro para o nome na tabela de strings |
| `0x04` | `res_offset` | `uint64` | Offset absoluto dos dados no arquivo `.ResDt` |
| `0x0C` | `comp_size` | `uint64` | Tamanho dos dados comprimidos no `.ResDt` |
| `0x14` | `uncomp_size` | `uint64` | Tamanho dos dados após descompressão |
| `0x1C` | `flags` | `uint32` | Flags de compressão (`0x09` = zlib Deflate) |
| `0x20` | `reserved` | `16 bytes` | Padding / hash de integridade zerado |

### 4. Tabela de Diretórios — 16 Bytes por Entrada
Localizada no final do arquivo `.Res00` (`num_dirs` × 16 bytes = 36.880 bytes):

| Offset Relativo | Campo | Tipo | Descrição |
|---|---|---|---|
| `0x00` | `str_offset` | `uint32` | Offset do nome do diretório na tabela de strings |
| `0x04` | `first_child` | `int32` | Índice do primeiro subdiretório filho (`-1` se nenhum) |
| `0x08` | `next_sibling` | `int32` | Índice do próximo diretório irmão (`-1` se nenhum) |
| `0x0C` | `file_count` | `uint32` | Quantidade de arquivos pertencentes a esta pasta |

### 5. Formato dos Dados (`.ResDt`)
- Os streams de dados iniciam com headers padrão zlib (`0x78 0xDA`, `0x78 0x9C`, `0x78 0x01`).
- Teste prático de validação:
  - Entrada: `twoway_night.World00p`
  - Offset `.ResDt`: `0x00344564`, Tamanho Comprimido: 7.977 bytes, Tamanho Descomprimido: 72.128 bytes.
  - Resultado: Descompressão instantânea com header textual `b'[Automatic Assets]\r\n;Warning: All modifications...'`.

### 6. Inventário de Tipos de Assets Identificados no Pacote
- **5.577** `.mat00` (definições de materiais e shaders LithTech)
- **4.552** `.dds` (texturas DirectDraw Surface)
- **533** `.model00p` (modelos 3D de armas, personagens, acessórios e veículos)
- **214** `.fxo` (efeitos e shaders compilados DirectX 9)
- **39** `.csv` (tabelas de balanço de armas, modos de jogo, clãs, itens, cash)
- **27** `.world00p` (arquivos completos de mapas e geometria de fases)
- **21** `.fsb` (bancos de áudio FMOD SoundBank)
- **12** `.strdb00e` (bancos de strings e localização)
- **10** `.anmtree00p` (árvores de animação esquelética)

## Limitações
- Alguns modelos `.model00p` utilizam a estrutura interna proprietária de mesh do LithTech Jupiter EX (vértices, normais, pesos de esqueleto, submeshes). A extração do arquivo bruto está 100% resolvida; a conversão de `.model00p` para `.obj` / `.gltf` demandará mapeamento da struct de vértices.

## Próximos Passos
1. Usar o script [`scripts/extract-lithtech-res.py`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/scripts/extract-lithtech-res.py) para extração seletiva de armas e mapas.
2. Inspecionar o formato interno de `.model00p` e `.world00p` para importação no Godot 4 / Blender.

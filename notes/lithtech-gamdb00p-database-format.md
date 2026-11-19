# Engenharia Reversa do Formato LithTech Jupiter EX GameDatabase v3 (`GADB` / `.Gamdb00p`)

Descoberto por: `agy` (sessão 2, 2026-11-19) — Dissecação estática somente-leitura de `GameDatabase.dll` (`0x1000B772` → `0x1000B68D` → `0x1000B55A` → `0x100094A9` → `0x1001013A`) e validação 100% byte-exata (`diff = 0`) nos 5 arquivos `.Gamdb00p` do cliente.

---

## 1. Visão Geral e Arquitetura em `GameDatabase.dll`

O motor **LithTech Jupiter EX** armazena todas as definições estruturadas de gameplay (arsenal, balística, modelos de personagens, esqueletos, animações, mapas, modos de missão, layout de HUD e bindings de perfil) em bancos binários compilados `.Gamdb00p` gerenciados por `GameDatabase.dll` (138.768 bytes, `ImageBase = 0x10000000`), que exporta:
- `GetIDatabaseMgr` (`0x100029A5`)
- `GetIDatabaseCreatorMgr` (`0x10001E0B`)
- `GetIDatabaseCreatorUnpackedMgr` (`0x1000153C`)

### Cadeia de Deserialização em `GameDatabase.dll`
1. **`CDatabaseLoader::OpenDatabase` (`0x1000B772`):**
   - Lê o cabeçalho fixo de **28 bytes (`0x1C`)** e valida `magic == 0x42444147` (`"GADB"`) e `version == 3`.
   - Aloca o bloco contíguo de memória para o `String Pool` + arrays de `Category` (`0x18` B/item), `Record` (`0x18` B/item), `Attribute` (`0x14` B/item) e `Values` (`0x04` B/item):
     $$\text{AllocBytes} = \text{StringPoolBytes} + 4 \times \left(6 \times (\text{NumCats} + \text{NumRecs}) + 5 \times \text{NumAttrs} + \text{NumVals}\right) + 29$$
   - Lê os `StringPoolBytes` diretamente para a base do bloco (`esi`).
2. **`CDatabase::Unpack` (`0x1000B68D`):**
   - Lê `uint32 cat_count` e itera sobre cada categoria chamando `CCategory::Unpack` (`0x1000B55A`).
3. **`CCategory::Unpack` (`0x1000B55A`):**
   - Lê `8 bytes` (`uint32 name_str_off`, `uint32 record_count`).
   - Para cada registro, lê `8 bytes` (`uint32 rec_name_str_off`, `uint32 attrib_count`) e itera sobre os atributos chamando `CAttribute::Unpack` (`0x100094A9`).
4. **`CAttribute::Unpack` (`0x100094A9`) & `IsStringAttributeType` (`0x10002117` → `0x1001013A`):**
   - Lê `16 bytes` (`uint32 name_str_off`, `uint32 attr_type`, `uint32 attr_usage`, `uint32 value_count`).
   - Lê `value_count` inteiros de 32 bits (`4 bytes` cada).
   - Chama `0x1001013A(attr_type)`: se `4 <= attr_type <= 8`, o valor de 32 bits é um **offset em bytes dentro do `String Pool`** (`add eax, ebx`); caso contrário, é armazenado como valor bruto de 32 bits (`float32`, `int32`, `RecordLink`, ou componentes float de `Vector2/3/4`).

---

## 2. Layout Binário `GADB` v3

### 2.1 Cabeçalho de 28 Bytes (`0x00..0x1B`, Little-Endian)

| Offset | Tipo | Nome | Descrição |
|---|---|---|---|
| `+0x00` | `char[4]` | `magic` | `"GADB"` (`0x42444147`) |
| `+0x04` | `uint32` | `version` | `3` |
| `+0x08` | `uint32` | `string_pool_bytes` | Tamanho total em bytes do `String Pool` imediatamente após o header |
| `+0x0C` | `uint32` | `num_categories` | Total de categorias na base |
| `+0x10` | `uint32` | `num_records` | Soma de todos os registros em todas as categorias |
| `+0x14` | `uint32` | `num_attributes` | Soma de todos os atributos em todos os registros |
| `+0x18` | `uint32` | `num_values` | Soma de todos os elementos de 32 bits (`value_count`) em todos os atributos |

### 2.2 Tipos de Atributos (`eAttributeType`)

| `attr_type` | Tipo | Representação no Fluxo de Valores (`4B * value_count`) |
|---|---|---|
| `1` | `Float32` | `IEEE 754 float32` |
| `2` | `Int32` | `int32` / `bool` (`0` ou `1`) |
| `3` | `RecordLink` | `uint32` handle (`(cat_idx << 16) | rec_idx`, ou `0xFFFFFFFF` para `<none>`) |
| `4..8` | `String / WString / Res / Path` | `uint32` offset para string null-terminated dentro do `String Pool` (`4 <= attr_type <= 8` em `0x1001013A`) |
| `9` | `Vector2` | 2 `float32` por vetor |
| `10` | `Vector3` | 3 `float32` por vetor |

---

## 3. Catálogo dos 5 Bancos `.Gamdb00p` do Cliente (`diff = 0`)

Todos os 5 arquivos `.Gamdb00p` foram dissecados até o último byte (`parsed_bytes == file_size`):

| Arquivo | Tamanho | `String Pool` | Categorias | Registros | Atributos | Valores (32-bit) |
|---|---:|---:|---:|---:|---:|---:|
| `Game/Database/TheRaw.Gamdb00p` | `2.258.252 B` | `365.444 B` | `179` | `2.886` | `91.436` | `101.320` |
| `Database/TheRaw.Gamdb00p` | `3.119.616 B` | `363.620 B` | `194` | `2.862` | `134.430` | `145.159` |
| `AnimationDatabase/S2_anim.Gamdb00p` | `136.456 B` | `16.540 B` | `194` | `357` | `5.537` | `6.721` |
| `Game/DatabaseLocalized/TheRawL.Gamdb00p` | `89.716 B` | `23.796 B` | `16` | `124` | `3.111` | `3.748` |
| `ProfileDatabase/Defaults.Gamdb00p` | `13.240 B` | `2.048 B` | `9` | `56` | `532` | `532` |

### 3.1 Diferença Estrutural entre `Database/TheRaw.Gamdb00p` (3,11 MB) e `Game/Database/TheRaw.Gamdb00p` (2,25 MB)
- `Database/TheRaw.Gamdb00p` contém **15 categorias adicionais** de armas (`42.994` atributos extras) que não estão em `Game/Database/TheRaw.Gamdb00p`:
  - `Arsenal/Weapons/AI/00_Main`, `01_Sub`, `02_Melee`, `03_Item1`, `04_Item2`
  - `Arsenal/Weapons/Multiplayer/00_Main` (+ `Old_Weapon`), `01_Sub` (+ `Old_Weapon`), `02_Melee` (+ `Old_Weapon`), `03_Item1` (+ `Old_Weapon`), `04_Item2` (+ `Old_Weapon`)

### 3.2 Causa Raiz Exata no Banco da Asserção `GDB Mission/Level DetailInfo` (`0x10408C7E`)
Na categoria `Missions/Level` de `Game/Database/TheRaw.Gamdb00p` (`162` registros):
- **156 registros** possuem `DetailInfo >= 10000` (ex.: `08_twoway -> 10000`, `09_Kill_Port -> 10001`, `07_huntinghill -> 10003`, `02_Ghost_City -> 10011`), mapeando diretamente para `MapInfo.csv`.
- **Apenas 6 registros legados de teste** possuem **`DetailInfo == 0`**:
  1. `01_DummyHouse2` (`DetailInfo: 0`)
  2. `03_OldWarLoad` (`DetailInfo: 0`)
  3. `04_UnderGround` (`DetailInfo: 0`)
  4. `05_Heaven` (`DetailInfo: 0`)
  5. `10009_DummyHouse` (`DetailInfo: 0`)
  6. `161_Tutorial` (`DetailInfo: 0`)
- Isso explica por que o patch cirúrgico de 2 bytes em `GameClient.dll @ 0x10408C7E` (`74 3f -> 74 27`, `je next_record`) resolveu 100% da lista de mapas/modos: ele simplesmente pula esses 6 registros com `DetailInfo == 0` e carrega os 156 registros válidos!

---

## 4. Artefatos Gerados
- Dissector Python: [`scripts/inspect_gamdb00p.py`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/scripts/inspect_gamdb00p.py)
- Catálogo JSON Exportado: [`targets/district-187/data/gamdb00p_catalog.json`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/targets/district-187/data/gamdb00p_catalog.json)

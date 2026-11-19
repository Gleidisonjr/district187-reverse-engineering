# Engenharia Reversa do Subsistema de Localização LithTech Jupiter EX (`StringEditRuntime.dll`, `.Strdb00e` & `SKDB` v2 `.Strdb00p`)

Descoberto por: `agy` (2026-11-19) — Dissecação estática completa somente-leitura de [`StringEditRuntime.dll`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/targets/district-187/client-rebirth/StringEditRuntime.dll) (`0x10001000` → `0x10001D1D` → `0x100010EF` → `0x100018BB` → `0x1000208F`) e validação 100% byte-exata (`diff = 0`) nos **13 arquivos-fonte `.Strdb00e`**, no manifesto de projeto **`TheRaw.Strdb00s`** e nos **7 bancos compilados `SKDB` v2 (`.Strdb00p`)** do cliente.

---

## 1. Arquitetura do Subsistema `StringEditRuntime.dll`

O motor **LithTech Jupiter EX** separa o pipeline de localização (`JupiterEX StringEdit Runtime`, versão `0.18.731.1253`, compilado pela CJGameLab com PDB `D:\work\trunk\built\Final\StringEditRuntime.pdb`) em três camadas de arquivos em disco:

1. **Manifesto de Projeto (`.Strdb00s` — `StringDatabase/TheRaw.Strdb00s`):**
   - Arquivo INI em **UTF-16LE com BOM (`FF FE`)** que define o GUID do banco (`{3C11E843-ED99-43f5-A94A-26E1A376E5AE}`), idiomas ativos (`English=en`, `Turkey=tr`), o `PostBuildStep` (`xcopy "%DATABASEDIR%\Turkey\TheRaw.Strdb00p" "%DATABASEDIR%" /Y /I /F`) e a lista de `[External Files]` apontando para `source/*.Strdb00e`.
2. **Tabelas-Fonte Descompactadas por Coluna/Idioma (`.Strdb00e` — `StringDatabase/source/*.Strdb00e`):**
   - 13 arquivos **UTF-16LE com BOM (`FF FE`)** onde cada arquivo representa uma coluna do editor `StringEdit` (`category.Strdb00e`, `voice.Strdb00e`, `english.Strdb00e`, `turkey.Strdb00e`, `kor.Strdb00e`, `Arabic.strdb00e` e 7 colunas de metadados de dublagem/cinemática).
3. **Banco Binário Compilado de Runtime (`.Strdb00p` — Magic `SKDB` v2):**
   - Formato binário empacotado (`String Keeper Database v2`, extensão `.Strdb00p` = *String Database Packed*), carregado em tempo de execução por `StringEditRuntime.dll` via `CStringKeeper::LoadFromStream` (`0x100010EF`).

---

## 2. Dissecação de `StringEditRuntime.dll` (`ImageBase = 0x10000000`)

### 2.1 Export Único e Singleton Global

`StringEditRuntime.dll` (23.568 bytes) possui exatamente 1 símbolo exportado:
- **`GetIStringEditMgr` (`Ordinal 1` @ `0x10001000`):**
  - Verifica a flag de inicialização estática `byte ptr [0x10004080] & 1`.
  - Na primeira chamada, zera `+0x04` (`0x10004074`) e `+0x08` (`0x10004078`), grava o ponteiro da vtable `0x100030F4` em `0x10004070` e retorna `eax = 0x10004070` (`CStringEditMgr*`, derivado de `IStringEditMgr`, conforme RTTI `.?AVCStringEditMgr@@` em `0x10004028` e `.?AVIStringEditMgr@@` em `0x10004008`).

### 2.2 Layout de Memória das Classes (`CStringEditMgr` e `CStringKeeper`)

#### `CStringEditMgr` (`0x10004070`, `sizeof = 0x10` / 16 bytes)
| Offset | Tipo | Nome | Descrição |
|---|---|---|---|
| `+0x00` | `void**` | `vftable` | `0x100030F4` (26 métodos virtuais de `IStringEditMgr`) |
| `+0x04` | `pfnErrorCb` | `m_pfnErrorCallback` | `void (__cdecl*)(const char* szKey, const char* szErr, void* pUser)` |
| `+0x08` | `void*` | `m_pErrorUserData` | Contexto opaco passado ao callback de erro |
| `+0x0C` | `CStringKeeper*` | `m_pLastCreatedKeeper` | Último `CStringKeeper` alocado por `CreateStringKeeper` (`0x10001D1D`) |

#### `CStringKeeper` (`sizeof = 0x28` / 40 bytes, alocado em `0x10001D24`)
| Offset | Tipo | Nome | Descrição |
|---|---|---|---|
| `+0x00` | `IStringEditMgr*` | `m_pOwnerMgr` | Ponteiro para `CStringEditMgr` (`0x10004070`), usado para disparar `vtable[+0x64]` em erros |
| `+0x04` | `SRecordEntry*` | `m_pRecordTable` | Array de `num_ids` pares `{int32 val_idx, int32 voice_idx}` (`8 bytes` por registro) |
| `+0x08` | `char*` | `m_pStringPool` | Buffer contíguo contendo o `String Pool` bruto lido do arquivo (`pool_bytes`) |
| `+0x0C` | `const char**` | `m_ppStringIDs` | Array de `num_ids` ponteiros para as strings ANSI de IDs dentro de `m_pStringPool` |
| `+0x10` | `const wchar_t**` | `m_ppStringValues` | Array de `num_ids_plus_values` slots (primeiros `num_wvalues` preenchidos com `wchar_t*`) |
| `+0x14` | `const char**` | `m_ppVoicePaths` | Array de `num_voices` ponteiros para as strings ANSI de voz dentro de `m_pStringPool` |
| `+0x18` | `uint32` | `m_nNumIDs` | Número total de IDs de strings no banco (`header.num_ids`) |
| `+0x1C` | `uint32` | `m_nNumIDsPlusValues` | Soma `num_ids + num_wvalues` (`header.num_ids_plus_values`) |
| `+0x20` | `uint32` | `m_nNumVoices` | Número de strings únicas de áudio/voz no pool (`header.num_voices`) |
| `+0x24` | `IStringFilter*` | `m_pStringFilter` | Filtro/decodificador opcional de runtime (invocado em `0x1000136C` / `0x100019C9` com buffer estático de `0x400` bytes em `0x10004088` / `0x10004488`) |

### 2.3 Tabela Completa de Métodos Virtuais (`CStringEditMgr` vtable @ `0x100030F4`)

| Índice | Offset VTable | VA da Função | Assinatura Reconstruída / Papel |
|---:|---|---|---|
| `0` | `+0x00` | `0x10001D1D` | `HSTRINGKEEPER CreateStringKeeper(ILTInStream* pStream)` — Aloca `0x28` B (`0x1000102E`) e chama `CStringKeeper::LoadFromStream(pStream)` (`0x100010EF`) |
| `1` | `+0x04` | `0x1000148E` | `void DestroyStringKeeper(HSTRINGKEEPER hKeeper)` — Chama `CStringKeeper::FreeAll` (`0x10001050`) e `operator delete` |
| `2` | `+0x08` | `0x100014A9` | `bool SetErrorCallback(pfnErrorCallback fn, void* pUserData)` |
| `3` | `+0x0C` | `0x100014BC` | `bool ClearErrorCallback(pfnErrorCallback fn)` |
| `4` | `+0x10` | `0x10001D74` | `int32 GetIndex(HSTRINGKEEPER hKeeper, const char* szStringID)` (`-> 0x1000190B`) |
| `5` | `+0x14` | `0x100014D6` | `const char* GetStringID(HSTRINGKEEPER hKeeper, uint32 nIndex)` (`-> 0x100012CC`) |
| `6` | `+0x18` | `0x100014F1` | `const wchar_t* GetString(HSTRINGKEEPER hKeeper, uint32 nIndex)` (`-> 0x1000130A`) |
| `7` | `+0x1C` | `0x10001D8D` | `const wchar_t* GetString(HSTRINGKEEPER hKeeper, const char* szStringID)` (`-> 0x10001945`) |
| `8` | `+0x20` | `0x10001E12` | `int32 GetFormattedStringV(HSTRINGKEEPER hKeeper, uint32 nIndex, wchar_t* pBuf, uint32 cchBuf, va_list args)` (`-> 0x10001A54` via `_vsnwprintf`) |
| `9` | `+0x24` | `0x10001DEF` | `int32 GetFormattedString(HSTRINGKEEPER hKeeper, uint32 nIndex, wchar_t* pBuf, uint32 cchBuf, ...)` (`-> 0x10001A54`) |
| `10` | `+0x28` | `0x10001DCB` | `int32 GetFormattedStringV(HSTRINGKEEPER hKeeper, const char* szID, wchar_t* pBuf, uint32 cchBuf, va_list args)` (`-> 0x10001A33`) |
| `11` | `+0x2C` | `0x10001DA8` | `int32 GetFormattedString(HSTRINGKEEPER hKeeper, const char* szID, wchar_t* pBuf, uint32 cchBuf, ...)` (`-> 0x10001A33`) |
| `12` | `+0x30` | `0x100025E9` | `bool FormatMessageByIndexV(HSTRINGKEEPER hKeeper, uint32 nIndex, wchar_t* pBuf, uint32 cchBuf, va_list args)` (`-> 0x1000208F` `LTFormatMessageT`) |
| `13` | `+0x34` | `0x100025BE` | `bool FormatMessageByIndex(HSTRINGKEEPER hKeeper, uint32 nIndex, wchar_t* pBuf, uint32 cchBuf, ...)` (`-> 0x1000208F`) |
| `14` | `+0x38` | `0x10002592` | `bool FormatMessageByIDV(HSTRINGKEEPER hKeeper, const char* szID, wchar_t* pBuf, uint32 cchBuf, va_list args)` (`-> 0x1000208F`) |
| `15` | `+0x3C` | `0x10002567` | `bool FormatMessageByID(HSTRINGKEEPER hKeeper, const char* szID, wchar_t* pBuf, uint32 cchBuf, ...)` (`-> 0x1000208F`) |
| `16` | `+0x40` | `0x1000150C` | `const char* GetVoicePath(HSTRINGKEEPER hKeeper, uint32 nIndex)` (`-> 0x100013C1`) |
| `17` | `+0x44` | `0x10001E36` | `const char* GetVoicePath(HSTRINGKEEPER hKeeper, const char* szStringID)` (`-> 0x10001A75`) |
| `18` | `+0x48` | `0x10001E51` | `bool DoesStringExist(HSTRINGKEEPER hKeeper, const char* szStringID)` (`-> 0x10001AF3`) |
| `19` | `+0x4C` | `0x10001527` | `bool HasStringValue(HSTRINGKEEPER hKeeper, uint32 nIndex)` (`-> 0x10001427`) |
| `20` | `+0x50` | `0x10001E69` | `bool HasStringValue(HSTRINGKEEPER hKeeper, const char* szStringID)` (`-> 0x10001B3E`) |
| `21` | `+0x54` | `0x1000153F` | `bool HasVoicePath(HSTRINGKEEPER hKeeper, uint32 nIndex)` (`-> 0x1000145A`) |
| `22` | `+0x58` | `0x10001E81` | `bool HasVoicePath(HSTRINGKEEPER hKeeper, const char* szStringID)` (`-> 0x10001B8E`) |
| `23` | `+0x5C` | `0x10001E99` | `bool EnumerateStringsByPrefix(HSTRINGKEEPER hKeeper, const char* szPrefix, pfnEnumCb fn, void* pUser)` (`-> 0x10001C66`) |
| `24` | `+0x60` | `0x10001575` | `void SetStringFilter(IStringFilter* pFilter)` — Grava `pFilter` em `m_pLastCreatedKeeper->m_pStringFilter` (`+0x24`) |
| `25` | `+0x64` | `0x10001557` | `void ReportError(HSTRINGKEEPER hKeeper, const char* szKey, const char* szErrorMsg)` — Dispara `m_pfnErrorCallback` |

### 2.4 Algoritmo de Deserialização em `CStringKeeper::LoadFromStream` (`0x100010EF`)

1. **Leitura e Validação do Cabeçalho (`0x10001118`..`0x10001136`):**
   - Invoca `pStream->Read(&hdr, 0x18)` (`call dword ptr [eax + 4]`).
   - Verifica `hdr.magic == 0x42444B53` (`"SKDB"`) em `0x10001129` e `hdr.version == 2` em `0x10001132`.
2. **Alocação e Leitura do `String Pool` (`0x10001138`..`0x10001167`):**
   - Salva `num_ids` (`[ebp-0x14]`) em `[esi+0x18]`, `num_ids_plus_values` (`[ebp-0x10]`) em `[esi+0x1C]`, e `num_voices` (`[ebp-0x0C]`) em `[esi+0x20]`.
   - Aloca `string_pool_bytes` (`[ebp-0x08]`) via `operator new[]` (`0x10002615`), salva em `[esi+0x08]` e lê o bloco inteiro do stream.
3. **Alocação dos 3 Vetores de Ponteiros (`0x10001172`..`0x100011CD`):**
   - `[esi+0x0C]` (`m_ppStringIDs`): `num_ids * 4` bytes.
   - `[esi+0x10]` (`m_ppStringValues`): `num_ids_plus_values * 4` bytes.
   - `[esi+0x14]` (`m_ppVoicePaths`): `num_voices * 4` bytes.
4. **Varredura Sequencial Alinhada a 4 Bytes do `String Pool` (`0x100011CF`..`0x1000127C`):**
   - Ponteiro cursor `edi` inicia em `m_pStringPool` (`[esi+0x08]`).
   - **Loop 1 (`0x100011E0`..`0x10001203`) — `num_ids` Strings ANSI (IDs):**
     - `m_ppStringIDs[i] = edi`
     - Calcula `len = LT_strlen(edi)` (`0x100010B4`) e avança `edi` com alinhamento de 4 bytes:
       $$\text{step}_{\text{ANSI}} = (\text{len} + 4) \ \& \ \text{0xFFFFFFFC}$$
   - **Loop 2 (`0x10001208`..`0x10001241`) — `num_wvalues = num_ids_plus_values - num_ids` Strings UTF-16LE (Valores):**
     - Calcula `num_wvalues = [ebp-0x10] - [ebp-0x14]` (`sub eax, dword ptr [ebp - 0x14]` em `0x1000120B`).
     - `m_ppStringValues[j] = (const wchar_t*)edi`
     - Calcula `wlen = LT_wcslen(edi)` (`0x100010CC`) e avança `edi` com `lea eax, [eax + eax + 5]; and eax, 0xFFFFFFFC`:
       $$\text{step}_{\text{UTF16}} = (2 \times \text{wlen} + 5) \ \& \ \text{0xFFFFFFFC}$$
   - **Loop 3 (`0x10001246`..`0x1000127A`) — `num_voices` Strings ANSI (Caminhos/Cues de Voz):**
     - `m_ppVoicePaths[k] = edi`
     - Calcula `len = LT_strlen(edi)` (`0x100010B4`) e avança `edi` por $(\text{len} + 4) \ \& \ \text{0xFFFFFFFC}$.
5. **Leitura da Tabela de Registros (`0x1000127F`..`0x100012B4`):**
   - Aloca `num_ids * 8` bytes para `m_pRecordTable` (`[esi+0x04]`) e lê `num_ids << 3` bytes diretamente do stream.

### 2.5 Busca Binária (`0x100018BB`), Valores Especiais (`<none>`) e `LTFormatMessageT` (`0x1000208F`)

- **Sentinela `<none>` (`0x1000315C`):**
  - `GetIndexByID` (`0x1000190B`), `GetValueByID` (`0x10001945`) e `GetVoicePathByID` (`0x10001A75`) testam primeiro se `strcmp(szID, "<none>") == 0` (`0x10001831`). Se verdadeiro, `GetIndexByID` retorna `-2` (`0xFFFFFFFE`), e `GetValue`/`GetVoicePath` retornam string vazia (`L""` em `0x100031F0` ou `""` em `0x10003255`).
- **Busca Binária Case-Insensitive (`CStringKeeper::BinarySearchID` @ `0x100018BB`):**
  - Como os `num_ids` no `String Pool` são pré-ordenados lexicograficamente de forma case-insensitive na compilação do `.Strdb00p`, `0x100018BB` executa busca binária $O(\log N)$ em `m_ppStringIDs[0 .. num_ids-1]` usando `_stricmp` (`0x10001873` → `MSVCR100._stricmp`).
- **Busca Binária por Prefixo (`CStringKeeper::BinarySearchPrefix` @ `0x10001BDF` & `EnumerateIDsByPrefix` @ `0x10001C66`):**
  - Usa `_strnicmp(szPrefix, m_ppStringIDs[mid], strlen(szPrefix))` (`0x10001897`) para encontrar o intervalo `[first_idx, last_idx]` de todos os IDs que começam com determinado prefixo e invoca o callback para cada ID.
- **Formatador Posicional `LTFormatMessageT` (`0x1000208F`):**
  - Implementa substituição posicional estilo Win32 `FormatMessage` para placeholders `%1!s!`, `%1!d!`, `%2!ls!`, etc. (até 15 campos, validando `!` de abertura/fechamento com `0x10001F40` e `0x10001EB9`).

---

## 3. Especificação Byte-Exata dos Formatos (`.Strdb00p` e `.Strdb00e`)

### 3.1 Banco Binário Compilado `.Strdb00p` (`SKDB` v2)

#### Cabeçalho Fixo de 24 Bytes (`0x00..0x17`, Little-Endian `<4s5I`)
| Offset | Tipo | Nome | Descrição |
|---|---|---|---|
| `+0x00` | `char[4]` | `magic` | `"SKDB"` (`0x42444B53`) |
| `+0x04` | `uint32` | `version` | `2` |
| `+0x08` | `uint32` | `num_ids` | Quantidade de IDs ANSI (e de registros na tabela final) |
| `+0x0C` | `uint32` | `num_ids_plus_values` | Soma `num_ids + num_wvalues` (onde `num_wvalues` é o número de strings UTF-16LE únicas no pool) |
| `+0x10` | `uint32` | `num_voices` | Quantidade de strings ANSI únicas de áudio/voz no pool |
| `+0x14` | `uint32` | `string_pool_bytes` | Tamanho exato em bytes do `String Pool` que começa em `+0x18` |

#### `String Pool` (`+0x18 .. +0x18 + string_pool_bytes - 1`)
Dividido em 3 regiões contíguas sem cabeçalhos intermediários, onde **toda string é terminada em nulo e preenchida com bytes `0x00` até o próximo múltiplo de 4 bytes**:
1. **Região 1 — `num_ids` Strings ANSI (IDs):**
   - Ordenadas por `_stricmp`.
   - Tamanho de cada entrada: `(strlen(id) + 4) & ~3` bytes (1 byte `0x00` terminador + `0..3` bytes `0x00` de alinhamento).
2. **Região 2 — `num_wvalues` (`= num_ids_plus_values - num_ids`) Strings UTF-16LE (Valores):**
   - Strings UTF-16LE deduplicadas (o índice `0` é sempre a string vazia `L""`, ocupando 4 bytes `00 00 00 00`).
   - Tamanho de cada entrada: `(wcslen(val) * 2 + 5) & ~3` bytes (2 bytes `00 00` terminador + `0..2` bytes `0x00` de alinhamento).
3. **Região 3 — `num_voices` Strings ANSI (Voz/Áudio):**
   - Strings ANSI deduplicadas (o índice `0` é sempre a string vazia `""`, ocupando 4 bytes `00 00 00 00`).
   - Tamanho de cada entrada: `(strlen(voice) + 4) & ~3` bytes.

#### Tabela de Registros (`+0x18 + string_pool_bytes .. EOF`, `num_ids * 8` bytes)
Array de `num_ids` estruturas `SRecordEntry` (`<ii`, 8 bytes cada), indexadas na mesma ordem dos IDs da Região 1:
| Offset | Tipo | Nome | Descrição |
|---|---|---|---|
| `+0x00` | `int32` | `val_idx` | Índice (`0 .. num_wvalues-1`) na Região 2 (`m_ppStringValues`), ou `-1` se inexistente |
| `+0x04` | `int32` | `voice_idx` | Índice (`0 .. num_voices-1`) na Região 3 (`m_ppVoicePaths`, onde `0` = `""`), ou `-1` |

$$\text{FileSize} = 24 + \text{string\_pool\_bytes} + 8 \times \text{num\_ids}$$

### 3.2 Tabelas-Fonte do Editor `.Strdb00e` (UTF-16LE BOM Key-Value)

Cada arquivo `.Strdb00e` em `StringDatabase/source/` segue a gramática exata (`diff = 0` na reconstrução dos 13 arquivos):
1. **BOM UTF-16LE:** 2 bytes (`FF FE`).
2. **Cabeçalho de Seção:** `[Data]\r\n` codificado em UTF-16LE (`16 bytes`).
3. **Linhas `Chave=Valor`:** Cada entrada em uma única linha física `<StringID>=<Valor>\r\n` (quebras de linha dentro do texto são escapadas literalmente como os 2 caracteres `\n`, convertidos para `U+000A` real ao compilar o `.Strdb00p`).
4. **Terminador de Arquivo:** Uma linha em branco adicional `\r\n` ao final (`\r\n\r\n` após o último registro, ou `[Data]\r\n\r\n` = `22 bytes` nos 7 arquivos vazios).

---

## 4. Catálogo Completo e Comparativo dos Bancos (`diff = 0`)

### 4.1 Os 7 Bancos Compilados `.Strdb00p` (`SKDB` v2)

| Arquivo (`.Strdb00p`) | Tamanho | SHA-256 (10 chars) | `num_ids` | `num_wvalues` (Únicos) | `num_voices` (Únicos) | `String Pool` | Regs c/ Voz | `diff` |
|---|---:|---|---:|---:|---:|---:|---:|---:|
| `Game/StringDatabase/Turkey/TheRaw.Strdb00p` | `340.112 B` | `744cd8bffa` | **3.525** | `3.255` | `55` | `311.888 B` | `61` | `0 B` |
| `StringDatabase/English/TheRaw.Strdb00p` | `314.092 B` | `132bda0459` | **3.492** | `3.083` | `49` | `286.132 B` | `55` | `0 B` |
| `StringDatabase/Turkey/TheRaw.Strdb00p` | `303.332 B` | `6d6bbcf9dd` | **3.492** | `3.050` | `49` | `275.372 B` | `55` | `0 B` |
| `StringDatabase/TheRaw.Strdb00p` | `303.332 B` | `6d6bbcf9dd` | **3.492** | `3.050` | `49` | `275.372 B` | `55` | `0 B` |
| `StringDatabase/Turkey/1.Strdb00p` | `303.004 B` | `3fb0123d37` | **3.488** | `3.046` | `45` | `275.076 B` | `51` | `0 B` |
| `StringDatabase/Korea/TheRaw.Strdb00p` | `255.200 B` | `06590e6591` | **3.487** | `3.196` | `44` | `227.280 B` | `50` | `0 B` |
| `StringDatabase/Arabic/TheRaw.Strdb00p` | `245.324 B` | `2b2be07ce5` | **3.487** | `2.564` | `44` | `217.404 B` | `50` | `0 B` |

### 4.2 Os 13 Arquivos-Fonte `.Strdb00e` (`StringDatabase/source/`)

| Arquivo (`.Strdb00e`) | Tamanho | Entradas | Valores Não-Vazios | Papel no Projeto `TheRaw.Strdb00s` | `diff` |
|---|---:|---:|---:|---|---:|
| `english.Strdb00e` | `387.472 B` | `3.488` | `3.486` | Textos fonte em Inglês (Netmarble Global) | `0 B` |
| `turkey.Strdb00e` | `377.560 B` | `3.488` | `3.486` | Textos fonte em Turco (Joygame S2 Son Silah) | `0 B` |
| `kor.Strdb00e` | `318.430 B` | `3.481` | `3.481` | Textos fonte em Coreano (CJ GameLab S2 Online) | `0 B` |
| `Arabic.strdb00e` | `274.438 B` | `2.877` | `2.877` | Textos fonte em Árabe (611 strings ainda não traduzidas) | `0 B` |
| `category.Strdb00e` | `240.176 B` | `3.492` | `3.492` | Mapeamento de cada ID para uma das 20 categorias (`Enum`) | `0 B` |
| `voice.Strdb00e` | `5.180 B` | `55` | `55` | Mapeamento de IDs para tags de rádio/sistema FMOD (`[System][...]`) | `0 B` |
| `comment.Strdb00e` (+ 6 outros) | `22 B` cada | `0` | `0` | `comment`, `Character`, `Cinematic`, `Context`, `Direction`, `Level`, `VoiceFX` | `0 B` |

### 4.3 Distribuição por Categoria (`category.Strdb00e` — 3.492 IDs)

| Categoria | Qtd. IDs | Exemplos de Prefixos |
|---|---:|---|
| `ErrorMsg` | `1.124` | `DB_MSG_ERROR_*`, `MSG_ERROR_*` |
| `ItemName` | `676` | `IDS_WEAPON_NAME_*`, `IDS_AVATAR_NAME_*`, `IDS_PARTS_NAME_*` |
| `ItemDescription` | `667` | `IDS_WEAPON_DESCRIP_*`, `IDS_AVATAR_DESCRIPT_*` |
| `GlobalStr` | `369` | `GlobalUI_*`, `FunctionName_*` |
| `Lobby` | `151` | `UI_SYS_LOBBY_*`, `UI_SYS_CHANNEL_*` |
| `Clan` | `135` | `UI_SYS_CLAN_*` |
| `InGame` | `124` | `GAME_BOMB_*`, `GAME_CAPTAIN_*`, `GAME_MONEY_*`, `GAME_VOICE_*` |
| `Shop` | `84` | `UI_SYS_SHOP_*`, `UI_SYS_INVEN_*` |
| `Setting` | `62` | `UI_SYS_OPT_*` |
| `Room` | `39` | `UI_SYS_ROOM_*`, `UI_SYS_MODE_*` |
| `Post` | `32` | `UI_SYS_POST_*` |
| `MapName` | `24` | `IDS_MAP_NAME_10000` .. `IDS_MAP_NAME_10034` |
| `Menu` | `5` | `UI_SYS_MENU_*` |

### 4.4 Descoberta Crítica: O Banco Ativo `Game/StringDatabase/Turkey/TheRaw.Strdb00p` é o Banco Customizado Inglês do **S2 Rebirth**

A comparação cruzada entre os 7 arquivos `.Strdb00p` revelou por que o jogo exibe textos em inglês refinado mesmo carregando o caminho `Game/StringDatabase/Turkey/TheRaw.Strdb00p`:
1. **`StringDatabase/TheRaw.Strdb00p` e `StringDatabase/Turkey/TheRaw.Strdb00p` são bit-a-bit idênticos** (`SHA-256 = 6d6bbcf9dd...`, 3.492 IDs em Turco), resultado direto do `PostBuildStep` definido em `TheRaw.Strdb00s` (`xcopy "%DATABASEDIR%\Turkey\TheRaw.Strdb00p" "%DATABASEDIR%"`).
2. **`Game/StringDatabase/Turkey/TheRaw.Strdb00p` (`340.112 B`, 3.525 IDs)** foi substituído pela equipe do **S2 Rebirth** por uma versão **100% em Inglês expandida e corrigida**:
   - **33 IDs novos exclusivos do S2 Rebirth** (ausentes nos bancos originais de 3.492 IDs):
     - **7 Armas Customizadas (`1337001..1337008`):** `IDS_WEAPON_NAME_1337001` (`"PDW K101 Glitch"`), `1337002` (`"AWM 300 Fire"`), `1337003` (`"Hand Axe Glitch"`), `1337005` (`"Karambit"`), `1337006` (`"Glock-Lightning"`), `1337007` (`"Dragon Flame"`), `1337008` (`"AWM 300 Fire-S"`).
     - **2 Mapas Novos:** `IDS_MAP_NAME_10035` (`"Plaza"`), `IDS_MAP_NAME_10036` (`"White Night"`), além de mapas customizados reescritos nos IDs `10051..10056` (`"Dummy House (wide)"`, `"AWP Lego"`, `"Aim RedLine"`, `"AWP Lego (R)"`, `"Dead Forest"`, `"Dust 2"`).
     - **3 Modos de Armas:** `UI_SYS_MODE_RiflePistol` (`"Rifle / Pistol"`), `UI_SYS_MODE_SniperOnly` (`"Sniper Only"`), `UI_SYS_MODE_SniperPistol` (`"Sniper/ Pistol"`).
     - **21 Mensagens de Erro de Rede/Lobby/Anti-Cheat (`MSG_ERROR_00a3*`):** incluindo `MSG_ERROR_00A30199` (`"<font color='#DC143C'>You must verify your Discord account before you can access this channel.</font>"`) e `MSG_ERROR_00a30ac1` (`"Anti-cheat protection is not running. Close and reopen the launcher, then start the game from it."`).
   - **584 Strings Revisadas em relação a `StringDatabase/English/TheRaw.Strdb00p`:**
     - Tradução para o inglês de dezenas de strings que ainda estavam em coreano no banco `English/TheRaw.Strdb00p` original (como `GAME_Supplies_GetSelf`, `GlobalUI_PCRoomBonusGold`, `GlobalUI_ShutDownMsg1..4`, `GlobalUI_strRegion`).
     - Correções ortográficas e de terminologia (`"EXP"` → `"XP"`, `"SWAT"` → `"S.W.A.T."`, `"Increase reloding speed"` → `"Increase reloading speed"`, `"Free for All"` → `"Feast of Wolves!"`).

---

## 5. Artefatos Gerados
- Script Dissector e Validador (`diff = 0`): [`scripts/inspect_strdb00e.py`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/scripts/inspect_strdb00e.py)
- Catálogo JSON Completo: [`targets/district-187/data/strdb00e_catalog.json`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/targets/district-187/data/strdb00e_catalog.json)

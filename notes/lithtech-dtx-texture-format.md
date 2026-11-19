# Formato de Texturas LithTech Jupiter EX (`.Tex00p` / `DTX`)

Descoberto por: `agy` (2026-11-19) — Varredura estática em `459` texturas extraídas de `targets/district-187/extracted/`.

---

## 1. Cabeçalho Binário DTX (`0x00..0x1F`, Little-Endian)
| Offset | Tipo | Campo | Descrição |
|---|---|---|---|
| `+0x00` | `uint32` | `res_type` | `0` = Texture (`DTX`) |
| `+0x04` | `int32` | `version` | Versão do formato DTX (ex: `-5` Jupiter EX) |
| `+0x08` | `uint16` | `width` | Largura em pixels |
| `+0x0A` | `uint16` | `height` | Altura em pixels |
| `+0x0C` | `uint16` | `mipmaps` | Contagem de níveis de mipmap |
| `+0x0E` | `uint16` | `sections` | Seções extras anexadas |
| `+0x10` | `uint32` | `flags` | Flags DTX (Fullbright, 4444, CubeMap, etc.) |
| `+0x14` | `uint32` | `user_flags` | Flags de usuário / material |
| `+0x1A` | `uint8` | `bpp_id` | Formato de pixel (`3`=ARGB8888, `4`=DXT1, `5`=DXT3, `6`=DXT5) |

## 2. Distribuição de Formatos & Resoluções
| Formato | Qtd. Texturas |
|---|---:|
| `DDS_DXT5` | 415 |
| `DDS_RGBA` | 35 |
| `DDS_DXT3` | 7 |
| `DDS_DXT1` | 2 |

### Top 10 Resoluções
| Resolução | Qtd. Texturas |
|---|---:|
| `256x128` | 108 |
| `1024x1024` | 84 |
| `512x512` | 82 |
| `256x64` | 56 |
| `128x32` | 52 |
| `167x80` | 19 |
| `256x256` | 12 |
| `128x64` | 9 |
| `64x64` | 7 |
| `64x32` | 6 |

## 3. Artefatos Relacionados
- Dissector Python: [`scripts/inspect_dtx_textures.py`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/scripts/inspect_dtx_textures.py)
- Catálogo JSON: [`targets/district-187/data/dtx_texture_catalog.json`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/targets/district-187/data/dtx_texture_catalog.json)

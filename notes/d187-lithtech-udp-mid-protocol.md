# Protocolo UDP de Combate 3D LithTech (`MID_*`) — `CGameServerShell::OnMessage`

Descoberto por: `agy` (2026-11-19) — Dissecação estática da rotina `CGameServerShell::OnMessage` (`0x1004FD70`, slot `[6]` da vtable `0x1019220C` em `GameServer.dll`).

---

## 1. Sumário do Despachante UDP (`UDP 27888`)
- **Handler Principal:** `CGameServerShell::OnMessage` @ `0x1004FD70`
- **Tabelas de Salto (`switch`) Identificadas:** `1`
- **Message IDs (`MID_*`) Ativos Mapeados:** `7` (excluindo fallthrough default `0x10050947`)

---

## 2. Tabela de Message IDs UDP (`MID_*` → Handler VA em `GameServer.dll`)

| MID (Hex) | MID (Dec) | Handler VA em `GameServer.dll` |
|---|---:|---|
| `0xE9` | `233` | `0x100509a3` |
| `0xEA` | `234` | `0x10050a05` |
| `0xEB` | `235` | `0x10050a5b` |
| `0xEC` | `236` | `0x10050c6c` |
| `0xED` | `237` | `0x10050a97` |
| `0xEE` | `238` | `0x10050b23` |
| `0xEF` | `239` | `0x10050bc0` |

---

## 3. Artefatos Relacionados
- Extrator Python: [`scripts/map_lithtech_udp_messages.py`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/scripts/map_lithtech_udp_messages.py)
- Catálogo JSON: [`targets/district-187/data/lithtech_udp_mid_protocol.json`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/targets/district-187/data/lithtech_udp_mid_protocol.json)

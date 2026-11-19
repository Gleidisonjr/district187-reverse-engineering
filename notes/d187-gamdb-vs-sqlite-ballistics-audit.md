# Auditoria de Balística: `TheRaw.Gamdb00p` (Motor Nativo) vs `s2rebirth.db` (SQLite)

Gerado por: [`scripts/analyze_gamdb_vs_sqlite.py`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/scripts/analyze_gamdb_vs_sqlite.py) (2026-11-19).

---

## 1. Comparativo de Cobertura
| Fonte | Munições MP | Armas MP | Modos de Jogo |
|---|---:|---:|---:|
| `Database/TheRaw.Gamdb00p` (`GADB` v3) | `180` | `97` ({'00_Main': 67, '01_Sub': 11, '02_Melee': 17, '03_Item1': 2, '04_Item2': 0}) | `20` |
| `s2rebirth.db` (`weapons` table) | — | `185` | — |

## 2. Top 15 Munições por Dano Instantâneo (`InstDamage` em `TheRaw.Gamdb00p`)
| Registro `Arsenal/Ammo/MultiPlayer` | `InstDamage` | `Range` |
|---|---:|---:|

## 3. Top 15 Armas por Dano no SQLite (`s2rebirth.db`)
| Arma | Slot | Dano |
|---|---|---:|
| `DSR-E1` | `ana-silah` | `100` |
| `AWM 300` | `ana-silah` | `100` |
| `JNG-90` | `ana-silah` | `100` |
| `test` | `ana-silah` | `100` |
| `AWM 300 Altın` | `ana-silah` | `100` |
| `AWM Altın Sustrc` | `ana-silah` | `100` |
| `AWM 300 Şirin` | `ana-silah` | `100` |
| `AWM Şirin Silencer` | `ana-silah` | `100` |
| `AWM 300 Turkuaz` | `ana-silah` | `100` |
| `AWM Turkuaz Silencer` | `ana-silah` | `100` |
| `DSR-E1 Toz` | `ana-silah` | `100` |
| `DSR E1` | `ana-silah` | `100` |
| `AWM 300` | `ana-silah` | `100` |
| `AWM 300 Altın` | `ana-silah` | `100` |
| `AWM 300` | `ana-silah` | `100` |

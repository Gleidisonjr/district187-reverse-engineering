# Relatório de Varredura de Segurança e Integridade: District 187 (S2 Online)

## O que foi descoberto
O arquivo compactado `S2.rar` obtido da comunidade `s2privateserver.com` foi descompactado com sucesso e submetido a varredura antivírus completa em todos os 63 arquivos extraídos na pasta `targets/district-187/client/S2/`.

Nenhuma ameaça, cavalo de Troia, minerador ou código malicioso foi detectado pelos motores heurísticos e assinaturas atualizadas.

## Evidência
### 1. Hashes do Arquivo Fonte (`targets/district-187/downloads/S2.rar`)
- **Tamanho:** 1.016.699.272 bytes (~969 MB)
- **SHA-256:** `04510fceff04c8786a6a799497190ffeda3cc72200f6d499f91e9f98bb38ebec`
- **MD5:** `f11eb84f849a3b432034548fccef4a83`

### 2. Relatório do Mecanismo Antivírus (Kaspersky CLI 21.26 - `avp.com`)
```
;  --- Statistics ---
; Time Start:       2026-11-02 11:50:08
; Time Finish:      2026-11-02 11:50:20
; Processed objects: 63
; Total OK:         63
; Total detected:   0
; Suspicions:       0
; Total skipped:    0
; Password protected: 0
; Corrupted:        0
; Errors:           0
```
Todos os binários críticos foram aprovados:
- `TheRaw.exe` (Executável do cliente, 4.81 MB) — **OK**
- `TheRawExt.dll` (Extensão/Hook do cliente, 595 KB) — **OK**
- `LauncherApp.exe` (Launcher do cliente, 437 KB) — **OK**
- `Game/GameClient.dll` (Lógica cliente, 5.56 MB) — **OK**
- `Game/GameServer.dll` (Lógica servidor, 2.06 MB) — **OK**
- `Engine_Server.dll` (Engine de servidor LithTech, 1.63 MB) — **OK**
- `Game/Game.ResDt` (Arquivo principal de assets, 1.03 GB) — **OK**

## Limitações
- A varredura de assinatura estática garante ausência de malware conhecido, mas não audita comportamento de rede dinâmico caso os executáveis sejam disparados. Execuções dinâmicas devem ser realizadas em ambiente monitorado ou com proxies locais / Wireshark.

## Próximos Passos
1. Iniciar inspeção estática com **REA** nos binários principais (`TheRaw.exe`, `GameClient.dll`, `GameServer.dll`).
2. Mapear o formato do arquivo `.Res00` / `.ResDt` para extração de modelos 3D, mapas e áudios.
3. Identificar portas, endpoints e structs de rede no `GameClient.dll` e `GameServer.dll`.

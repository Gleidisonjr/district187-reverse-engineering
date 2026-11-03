# Apex Guard S2-320 e R6025: proxies DirectX do S2 Rebirth

## Sintoma
- Pop-up "S2 APEX GUARD S2-320": "Oyun guvenlik kutuphaneleri (DirectX) degistirilmis veya silinmis".
- Em seguida, crash `R6025 - pure virtual function call`.

## Causa (evidencia: strings de `ApexGuard.dll`)
O cliente S2 Rebirth usa DLLs-proxy:

| Proxy (nome do jogo) | Runtime real | Codigo de erro se faltar na memoria |
|---|---|---|
| `D3DX9_43.dll` (119 KB) | `dxbase.dll` | S2-320 |
| `StringEditRuntime.dll` | `strbase.dll` | S2-321 |
| `GameDatabase.dll` | `dbbase.dll` | S2-322 |

O `ApexGuard.dll` confere se `dxbase.dll`, `strbase.dll` e `dbbase.dll` estao carregados. Mais cedo substitui `D3DX9_43.dll` pela runtime limpa do `SysWOW64` (1,99 MB, identica a `dxbase.dll`). Com isso `dxbase.dll` nunca era carregado e o guard acusava S2-320.

## Correcao
Restaurado o proxy original de `D3DX9_43.dll.proxy_bak` (119.864 bytes). A versao limpa ficou em `D3DX9_43.dll.clean_runtime_bak`.

## Pendente
- Confirmar no desktop do usuario que o S2-320 sumiu.
- O R6025 pode ser consequencia do guard abortando. Reavaliar se persistir.
- A decisao antiga de trocar o proxy foi motivada por crash 0xC0000005 com o pacote da comunidade (`client/S2`), que e outro pacote. Reavaliar no rebirth.

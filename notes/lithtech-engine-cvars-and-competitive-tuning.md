# LithTech Jupiter EX Engine — Console Variables (Cvars) & Competitive Tuning

**Data:** 2026-11-02  
**Autor:** Gleidison Carvalho (Senior Data Analyst @ Meta)  
**Alvo:** `targets/district-187/client-rebirth/` (TheRaw.exe & Engine_Server.dll)  
**Configuração Gerada:** [`targets/district-187/client-rebirth/autoexec_competitive.cfg`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/targets/district-187/client-rebirth/autoexec_competitive.cfg)

---

## 1. Variáveis de Console Identificadas no Motor Nativo

O motor LithTech Jupiter EX expõe um conjunto de variáveis de console embutidas no subsistema de renderização e rede. As seguintes variáveis foram mapeadas através da varredura estática de `TheRaw.exe`, `Engine_Server.dll` e `GameClient.dll`:

| Cvar / Comando | Binário de Origem | Função no Motor |
|---|---|---|
| `MaxFPS` | `Engine_Server.dll` | Limite de taxa de quadros (0 = ilimitado para 144Hz/240Hz) |
| `ShowFrameRate` | `Engine_Server.dll` | Exibe contador numérico de FPS no canto da tela |
| `BindTexturesMipOffset` | `TheRaw.exe` / `GameClient.dll` | Offset de Mipmaps das texturas (0 = resolução nativa 2K/4K) |
| `GraphicQualityLevel` | `GameClient.dll` | Nível geral de detalhes gráficos e shaders (0 a 3) |
| `HardwareCursor` | `GameClient.dll` | Cursor do mouse acelerado por hardware para eliminação de input lag |
| `ConsoleEnable` | `TheRaw.exe` / `GameClient.dll` | Habilita o console de desenvolvedor in-game |
| `ConsoleAlpha` | `TheRaw.exe` | Transparência de renderização da janela de console |
| `ConsoleBufferLen` | `TheRaw.exe` | Tamanho do histórico de mensagens do console |
| `Decal` / `DecalModel` | `TheRaw.exe` / `GameClient.dll` | Habilita marcas de tiro e impactos no cenário e personagens |
| `MouseSensitivity` | `GameClient.dll` | Multiplicador de escala de sensibilidade do mouse |

---

## 2. Configuração Competitiva Calibrada (`autoexec_competitive.cfg`)

O arquivo foi estruturado e colocado na raiz do cliente para inicialização automática com o motor:

```cfg
// Display & Framerate
MaxFPS 0                      // Taxa de quadros destravada
ShowFrameRate 1               // Contador de FPS nativo ativo

// Qualidade de Textura Ultra HD
GraphicQualityLevel 3         // Shaders máximos
BindTexturesMipOffset 0       // Texturas nítidas em 2K/4K

// Latência & Input
HardwareCursor 1              // Zero atraso de cursor

// Console de Depuração
ConsoleEnable 1               // Console liberado
ConsoleBufferLen 500          // Histórico expandido
```

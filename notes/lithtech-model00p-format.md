# LithTech Jupiter EX — Especificação Reversa do Formato 3D .Model00p (MODL v33)

## O que foi descoberto
Engenharia reversa completa da geometria, esqueleto e buffers de renderização dos arquivos `.Model00p` (formato de malhas 3D da engine LithTech Jupiter EX em *District 187*).

Desenvolvemos com sucesso o conversor [`scripts/convert-model00p-to-obj.py`](file:///C:/Users/dopamine/Desktop/Projetos/Reverse%20Engineering/scripts/convert-model00p-to-obj.py) que extrai e converte os modelos proprietários em malhas Wavefront `.obj` prontas para importação no Blender, Godot 4 ou Unreal Engine 5.

## Evidência e Estrutura Binária

### 1. Cabeçalho do Arquivo (88 Bytes)
- **Magic:** `4D 4F 44 4C` (`"MODL"`)
- **Versão:** `33` (`0x00000021`)
- **Campos do Header:**
  - `h[02]`: Quantidade de nós / ossos do esqueleto (ex: 22 nós na AK-47, 24 nós na M4A1, 70 nós no SCAR)
  - `h[03]`: Quantidade de submeshes / peças (`num_pieces`)
  - `h[05]`: Níveis de LOD (`num_lods`)
  - `h[09]`: Tamanho em bytes da tabela de nomes de ossos e sockets

### 2. Tabela de Nomes de Ossos e Sockets
Inicia no offset `0x60` (96 bytes). Contém strings ASCII terminadas em nulo:
- Estrutura esquelética: `Bip01`, `Bip01 Spine`, `Bip01 R Hand`, etc.
- Pontos de acoplamento (sockets de gameplay):
  - `flash`: Posição do muzzle flash (labareda do cano)
  - `empty_cartridge`: Posição de ejeção de cápsulas deflagradas
  - `clip`: Posição de encaixe do carregador (animações de recarga)
  - `Top_gun_soket`: Trilho Picatinny superior para miras ópticas / lunetas
  - `hold`: Posição da empunhadura para a mão do operador

### 3. Hierarquia de Ossos (28 Bytes por Nó)
Armazena a matriz de transformação do bind pose (vetor de posição `float3`, rotação e escala).

### 4. Vertex Buffer Skinned (Stride de 72 Bytes)
A geometria utiliza vértices formatados para normal mapping em espaço tangente e animação esquelética por GPU:

| Offset no Vértice | Tipo | Descrição |
|---|---|---|
| `0x00 - 0x0B` | `float3` (12 bytes) | Posição no espaço tridimensional (`X, Y, Z`) |
| `0x0C - 0x17` | `float3` (12 bytes) | Vetor normal (`Nx, Ny, Nz`) com comprimento unitário (`1.0`) |
| `0x18 - 0x1F` | `float2` (8 bytes) | Coordenadas de textura UV (`U, V`) |
| `0x20 - 0x2B` | `float3` (12 bytes) | Vetor Tangente (`Tx, Ty, Tz`) |
| `0x2C - 0x37` | `float3` (12 bytes) | Vetor Binormal / Bitangente (`Bx, By, Bz`) |
| `0x38 - 0x47` | `16 bytes` | Pesos de influência óssea (`BlendWeights`) e índices (`BoneIndices`) |

### 5. Index Buffer (Triângulos)
- Sequência contínua de inteiros de 16 bits sem sinal (`uint16`).
- Cada conjunto de 3 índices forma uma face triangular da malha.
- Validação prática no modelo `AR_AK47.Model00p`:
  - 4.941 vértices
  - 970 triângulos (LOD0)
  - Exportado com sucesso para `targets/district-187/extracted/converted/AR_AK47.obj` (467 KB).

## Limitações
- Alguns modelos estáticos (cenários e props) utilizam variações de stride (64 ou 68 bytes) sem pesos esqueléticos. O conversor inclui detecção heurística de fluxo de vértices para compatibilidade ampla.

## Próximos Passos
1. Executar a conversão em lote dos modelos prioritários (personagens, armas secundárias e mapas).
2. Mapear a leitura dos arquivos de material `.mat00` para conectar automaticamente as texturas `.dds` nos arquivos `.mtl` correspondentes.

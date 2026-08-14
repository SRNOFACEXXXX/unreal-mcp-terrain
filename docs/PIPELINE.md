# Pipeline técnico

Referência de arquitetura: como as peças se encaixam e as fórmulas que
precisam bater exatamente.

---

## Visão geral

```
   [ local, numpy ]                    [ Unreal Engine 5.8 ]

   gen_v2.py                           UnrealEditor
     fbm espectral                       -ExecCmds="py apply_v2.py"
     biomas (voronoi + warp)                 |
     EROSAO HIDRAULICA  ---------------> import_heightmap_from_render_target
     recorte central                          |
     sitios (media local)                import_weightmap_from_render_target
     weightmaps                               |
        |                                 save_current_level
        v                                      |
   Heightmaps/*.png  ------------------->  ChernarusTerrain.umap
                                               |
                                          shoot3.py (via MCP HTTP)
                                               |
                                          docs/img/*.png
```

---

## Números que precisam bater

O Landscape herdado do pack tem:

| Propriedade | Valor |
|---|---|
| Componentes | 5 × 5 = 25 |
| Quads por componente | 127 |
| Quads totais | 5 × 127 = 635 |
| **Resolução do heightmap** | **636 × 636** |
| Escala X/Y | 200 cm por quad |
| **Tamanho no mundo** | 635 × 200 cm = **1270 m** |
| Origem | (-31700, -31700) cm |
| Escala Z (definida por nós) | 100 |

> Regra: `resolucao = componentes × quads_por_componente + 1`.
> O heightmap **precisa** ter exatamente essa resolução, senão vira um remendo
> num canto (erro 7).

---

## Codificação da altura (R+G)

`landscape_import_heightmap_from_render_target(rt, bImportHeightFromRGChannel=True, 0)`
lê um uint16 dividido em dois canais de 8 bits.

Conversão do Landscape:
```
WorldZ_cm = (H16 - 32768) / 128 * ScaleZ
```

Com `ScaleZ = 100`, invertendo para obter metros diretos:
```
H16 = 32768 + elevacao_m * 128
```

Em numpy:
```python
h16 = np.clip(32768 + (elev_m - BASELINE_M) * 128.0, 0, 65535).astype(np.uint16)
R = (h16 >> 8).astype(np.uint8)     # byte alto
G = (h16 & 0xFF).astype(np.uint8)   # byte baixo
```

**Faixa útil:** com baseline 100 m, `H16` vai de 0 a 65535 →
elevação de -156 m a +412 m. Sobra folga para o pico de 235 m.

---

## Weightmaps (pintura do material)

O material `Landscape_01` do pack expõe 4 camadas. Os `LayerInfo` seguem a
convenção `<Nome>_LayerInfo`, e o nome interno é o `<Nome>`:

| Camada | Regra de pintura |
|---|---|
| `Rock_01` | inclinação > 30° **ou** altitude > 185 m |
| `Grass_Ivy_01` | **chão padrão** — tudo que não é rocha nem encosta forte |
| `Dead_Leaves_01` | sub-bosque: peso do bioma floresta × encosta suave |
| `Dry_Ground_01` | margens de água (escoamento) + transição para rocha |

Os pesos são normalizados para somar 1 antes de exportar. Cada camada vira um
PNG em tons de cinza (peso 0–255 replicado em RGB).

> Lição: definir uma camada como "o que sobra" faz ela dominar o mapa (erro 6).
> Melhor é eleger uma camada como padrão e derivar as outras por condição.

---

## Erosão hidráulica — parâmetros

Do [terrain-erosion-3-ways](https://github.com/dandrino/terrain-erosion-3-ways).
**Só funcionam em espaço normalizado 0–1 num mundo de 200 unidades** (erro 2).

```python
FULL_WIDTH = 200.0
cell_width = FULL_WIDTH / GEN        # GEN = 848
cell_area  = cell_width ** 2

rain_rate                  = 0.0008 * cell_area
evaporation_rate           = 0.0005
min_height_delta           = 0.05
repose_slope               = 0.03     # angulo de repouso
gravity                    = 30.0
sediment_capacity_constant = 50.0
dissolving_rate            = 0.25
deposition_rate            = 0.001

ITER = 320   # o paper usa 1.4*dim; 320 ja da drenagem clara
```

Loop por iteração:
1. chuva uniforme
2. gradiente normalizado do terreno
3. capacidade de sedimento = f(desnível, velocidade, água)
4. erode ou deposita conforme sedimento vs. capacidade
5. desloca água e sedimento pelo gradiente
6. aplica ângulo de repouso (suaviza encostas impossíveis)
7. atualiza velocidade, evapora

Converter para metros **depois** do loop: `terrain *= RELIEF_M` (300 m).

Custo: ~90 s para 848² × 320 iterações.

---

## Regras de ouro para automação da UE

1. **Python entra por `-ExecCmds`**, nunca digitado no console (crash — erro 1).
2. **Render targets exigem RHI real** → editor GUI, não commandlet (erro 10).
3. **Contexto de mundo nunca é `None`** → passar um ator do nível.
4. **Todo campo do schema MCP é obrigatório**, mesmo com default (erro 14).
5. **`toolset_name` completo, `tool_name` sem prefixo** (erro 13).
6. **Screenshots via MCP estouram tokens** → decodificar do `.txt` salvo (erro 12).
7. **Log incremental**: gravar o relatório a cada passo, para sobreviver a crash.

---

## Como reproduzir do zero

```bash
# 1. gerar o terreno (local, ~90s)
python3 scripts/gen/gen_v2.py

# 2. criar o mapa base a partir do template do pack (headless)
/caminho/UnrealEditor-Cmd MCPTest.uproject \
  -run=pythonscript -script=$PWD/scripts/ue/build_map.py -unattended -nosplash

# 3. aplicar altura + pesos (precisa de RHI: editor GUI)
DISPLAY=:0 /caminho/UnrealEditor MCPTest.uproject \
  -ExecCmds="ModelContextProtocol.StartServer 8000, py $PWD/scripts/ue/apply_v2.py"

# 4. capturar as vistas (com o editor aberto)
python3 scripts/mcp/shoot3.py
```

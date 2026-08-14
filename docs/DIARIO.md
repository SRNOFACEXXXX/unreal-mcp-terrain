# Diário — passo a passo do que fizemos

Ordem cronológica real, incluindo os caminhos que não deram certo.
Detalhe técnico de cada erro está em [ERROS_E_ARMADILHAS.md](ERROS_E_ARMADILHAS.md).

---

## Fase 0 — Validar o MCP nativo da Unreal

**Objetivo:** provar que dá para controlar a UE 5.8 por IA via o plugin
`ModelContextProtocol` da Epic, com custo baixo de token.

1. Projeto `MCPTest` criado (Blueprint-only, template em branco).
2. Plugins habilitados direto no `.uproject` (mais barato que pela UI):
   `ModelContextProtocol`, `AllToolsets`, `ToolsetRegistry`.
3. Editor lançado com
   `-ExecCmds="ModelContextProtocol.StartServer 8000"` — servidor MCP sobe
   junto com o editor, sem precisar digitar no console.
4. `.mcp.json` apontando para `http://127.0.0.1:8000/mcp`.
5. **Validado:** cubo criado e screenshot capturado via ferramentas MCP nativas.

**Aprendizado:** as ferramentas reais ficam atrás de 3 meta-tools
(`list_toolsets`, `describe_toolset`, `call_tool`).

---

## Fase 1 — Terreno com dados de elevação REAIS

**Objetivo:** recriar a topografia que inspirou o mapa Chernarus (DayZ/Arma).

1. Pesquisa em [longcreek.me/blog/2021/chernarus-irl](https://longcreek.me/blog/2021/chernarus-irl):
   a referência real **não é Ucrânia/Rússia** — é o **norte da Boêmia,
   República Tcheca**, entre Ústí nad Labem e Děčín (~`50.7215, 14.1411`).
2. Baixados tiles DEM do Mapzen/AWS Terrain Tiles (formato *terrarium*),
   zoom 15 (~3 m/px) → recorte de 256×256 = ~774 m × 774 m, desnível 120 m.
   Script preservado em [`scripts/gen/gen_v1_dem.py`](../scripts/gen/gen_v1_dem.py).

**Por que foi abandonado:** 774 m é pequeno demais para 4 biomas, e o relevo
real da região é suave demais para dar contraste entre eles. O DEM real fica
como opção para quando quisermos fidelidade geográfica.

---

## Fase 2 — A batalha com a UI do Landscape (fracasso)

Tentativa de importar o heightmap pelo painel *Modo Paisagem → Novo →
Importar de arquivo*, automatizando cliques via `SlateInspectorToolset`.

Chegou perto: resolução reconhecida (256×256), escala configurada, botão
"Importar" habilitado. Mas empilhou problemas — campo concatenando texto,
botão fora da área visível, Slate perdendo o registro de janelas após mudança
de resolução do display (erros 9 e 1).

**Decisão:** abandonar a UI. Python via `-ExecCmds` é determinístico.

---

## Fase 3 — Desbloqueio: Python na Unreal

1. `PythonScriptPlugin` + `EditorScriptingUtilities` habilitados no `.uproject`.
2. Dois modos de execução, ambos confiáveis:
   - **Headless:** `UnrealEditor-Cmd <proj> -run=pythonscript -script=x.py`
   - **Com RHI:** `UnrealEditor <proj> -ExecCmds="py /caminho/x.py"`
3. **CRASH descoberto:** executar `py` digitando no console do editor derruba
   a engine (erro 1). Nunca mais.

**Mapeamento da API** (`scripts/ue/inspect_api.py`): `ALandscape::Import` é
C++ puro, **não exposto ao Python**. Mas existe:
```
landscape_import_heightmap_from_render_target(rt, bFromRG, editLayer)
landscape_import_weightmap_from_render_target(rt, layerName, editLayer)
```
Ou seja: dá para **escrever altura e pesos** num Landscape existente — só não
dá para criar um do zero.

**Consequência:** herdar o Landscape do mapa `Demo` do pack (que já vem com
material e iluminação configurados) e sobrescrever altura/pesos.

---

## Fase 4 — Primeiro terreno procedural (rejeitado)

Gerador com ruído fbm + 4 biomas em quadrantes + rio desenhado à mão.

**Resultado:** "cratera plana cercada de montanhas". Rejeitado — geologicamente
impossível (erro 3). Ruído sozinho não faz terreno.

---

## Fase 5 — v2: erosão hidráulica (o que funcionou)

Pesquisa da solução consolidada da comunidade:
[dandrino/terrain-erosion-3-ways](https://github.com/dandrino/terrain-erosion-3-ways)
(cópia de referência em `scripts/gen/ref_terrain_erosion_3_ways/`).

**Pipeline final** ([`scripts/gen/gen_v2.py`](../scripts/gen/gen_v2.py)):

| # | Etapa | Detalhe |
|---|---|---|
| 1 | fbm espectral | base continental (power-law noise via FFT) |
| 2 | Biomas orgânicos | voronoi com coordenadas deformadas por ruído — sem quadrantes |
| 3 | Modulação | cada bioma tem altura-base, amplitude e rugosidade próprias |
| 4 | **Erosão hidráulica** | 320 iterações: chuva → gradiente → sedimento → deposição → ângulo de repouso |
| 5 | Recorte | gera 848², recorta o centro 636² (mata wrap do FFT) |
| 6 | Sítios | 10 assentamentos aplainados para a **média local** |
| 7 | Weightmaps | rocha/grama/folhas/terra por inclinação + altitude + bioma |

Três bugs resolvidos aqui: escala da erosão (erro 2), wrap de borda (erro 4),
discos artificiais (erro 5).

**Resultado do terreno:**

| Bioma | Posição | Altitude | Assentamentos |
|---|---|---|---|
| Montanha | NE | até 235 m | Vila de Montanha, Posto de Mineração |
| Floresta | NO | ~105 m | Vilarejo da Floresta, Serraria, Abrigo de Caçadores |
| Planície | SO | ~42 m | Cidade da Planície, Fazenda Coletiva, Silo Ferroviário |
| Pântano | SE | ~15 m | Vila do Pântano, Cais de Pesca |

---

## Fase 6 — Aplicação no engine

1. `new_level_from_template` para criar `ChernarusTerrain` a partir do `Demo`
   (herda material `Landscape_01` + iluminação), e limpeza dos 156 props do
   vendor. Detalhe: `duplicate_asset` **não** serve (erro 11).
2. `ScaleZ = 100` no Landscape. Com isso a codificação fecha exatamente:
   ```
   WorldZ_cm = (H16 - 32768) / 128 * ScaleZ
   →  H16 = 32768 + elevacao_m * 128
   ```
3. Altura e 4 weightmaps escritos via render target
   ([`scripts/ue/apply_v2.py`](../scripts/ue/apply_v2.py)).
4. Rebalanceamento do material — grama como chão padrão (erro 6) e remoção das
   splines flutuantes (erro 8), em
   [`scripts/ue/apply_v3.py`](../scripts/ue/apply_v3.py).

---

## Fase 7 — Câmeras e verificação

[`scripts/mcp/shoot3.py`](../scripts/mcp/shoot3.py) fala com o editor pelo
servidor MCP (cliente mínimo em `scripts/mcp/mcp.py`), limpa atores órfãos e
captura 6 vistas com look-at real (`pitch = atan2(dz, hypot(dx,dy))`).

Imagens em [`docs/img/`](img/).

---

## Estado atual

**Pronto:** terreno erodido de 1270 m × 1270 m, 4 biomas com fronteiras
orgânicas, material pintado proceduralmente, 10 sítios aplainados, 6 câmeras.

**Próximo:** vegetação por bioma (a do pack foi removida porque estava nas
posições do terreno antigo) e construções nos 10 sítios.

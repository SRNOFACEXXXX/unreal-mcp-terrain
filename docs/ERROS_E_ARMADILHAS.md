# Erros e armadilhas — o que deu errado e por quê

Registro honesto de tudo que quebrou. Cada item tem **sintoma → causa → solução**,
para não repetirmos.

---

## 1. CRASH: digitar no console do editor derruba a engine

**Sintoma:** editor morre com `SIGSEGV` ao executar `py <script>` pelo campo
"Cmd" do rodapé, via automação Slate.

**Stack real:**
```
SlateInspectorToolset::Type
  -> SMultiLineEditableText::OnKeyDown
     -> SIGSEGV (signal 11)
```

**Causa:** o campo de console é um `SMultiLineEditableText`; a injeção de
eventos de tecla do `SlateInspectorToolset.Type` não é segura nele em UE 5.8.
Reproduzido **duas vezes**.

**Solução:** NUNCA digitar no console. Executar Python sempre por
`-ExecCmds="py /caminho/script.py"` na linha de lançamento, ou por commandlet
headless. Digitar em campos de texto de *painéis normais* (Details, etc.)
funciona sem problema — o bug é específico do console.

---

## 2. Erosão hidráulica achatou a montanha (302 m → 113 m)

**Sintoma:** depois da erosão, todo o relevo virava um planalto morno; a
montanha desaparecia.

**Causa:** os parâmetros do
[terrain-erosion-3-ways](https://github.com/dandrino/terrain-erosion-3-ways)
são calibrados para **terreno normalizado 0–1 num mundo de 200 unidades**.
Eu alimentei altura em **metros** (0–300) com `cell_width` em metros. A razão
`height_delta / cell_width` ficou ~100× maior que o previsto, explodindo
`sediment_capacity` → erosão brutal → tudo aplainado.

**Solução:** rodar a erosão inteiramente em espaço normalizado
(`FULL_WIDTH = 200.0`, `cell_width = 200/GEN`) e só converter para metros
**depois** da simulação (`terrain *= RELIEF_M`).

---

## 3. Terreno virava "cratera cercada de montanhas"

**Sintoma:** centro plano com montanhas ao redor — geologicamente impossível.
Foi o feedback que forçou a reescrita.

**Causa:** terreno feito só de **ruído** (fbm/valor). Ruído sozinho produz
bacias e bolhas aleatórias. Terreno real é esculpido por **água**, não por
ruído: é a erosão que cria cristas ramificadas, vales em V e redes de drenagem.

**Solução:** adicionar a simulação de erosão hidráulica (chuva → escoamento
pelo gradiente → transporte de sedimento → deposição → ângulo de repouso).
320 iterações já dão drenagem dendrítica clara.

---

## 4. Artefato de wrap nas bordas do mapa

**Sintoma:** faixa borrada/esticada na borda superior do heightmap.

**Causa:** o `fbm` é baseado em FFT e a erosão usa `np.roll` — ambos são
**periódicos**. A borda "vaza" para o lado oposto.

**Solução:** gerar em resolução maior (`GEN = 848`) e recortar o centro
(`DIM = 636`). As bordas contaminadas ficam fora do recorte.

---

## 5. Sítios de cidade viravam discos artificiais

**Sintoma:** clareiras apareciam como discos perfeitamente planos recortados
no relevo — parecia bug, não clareira.

**Causa:** aplainava para um **valor único** (`terrain = target`), criando um
platô de altura constante com borda circular nítida.

**Solução:** aplainar para a **média local** (gaussiana com sigma ≈ raio):
remove as ondulações mas preserva a inclinação geral do terreno. Lê como
terraço/clareira natural. Blend mais largo (1.6× o raio) também ajuda.

---

## 6. Mapa inteiro marrom (material sem vegetação)

**Sintoma:** terreno todo em tom de barro, sem verde.

**Causa:** na primeira versão dos weightmaps, `Dry_Ground` era calculado como
"o que sobra" (`1 - rock - grass - leaves`). Como grama tinha condições
restritivas, sobrava muito → terra seca dominava (média 196/255).

**Solução:** inverter a lógica — **grama é o chão padrão** (tudo que não é
rocha nem encosta íngreme), e terra seca aparece só em margens de água e
transição para rocha. Resultado: grama média 196, rocha 15.

---

## 7. Landscape gigante do pack + patch pequeno

**Sintoma:** o heightmap de 256×256 aplicado num Landscape de 636×636 virava
um "remendo" deformado num canto do terreno.

**Causa:** reaproveitei o Landscape do mapa `Demo` do pack (5×5 componentes de
127 quads = 636×636 vértices, 1270 m) mas gerei heightmap de 256².

**Solução:** gerar o heightmap **exatamente** em 636×636 para cobrir o
Landscape inteiro. Regra: `resolucao = componentes × quads_por_componente + 1`.

---

## 8. Splines de estrada flutuando no céu

**Sintoma:** faixas verdes/estradas pairando sobre o terreno.

**Causa:** o mapa `Demo` do pack tem `LandscapeSplinesComponent` com pontos de
controle no Z do terreno **antigo**. Trocar a altura do Landscape não move as
splines.

**Solução:** destruir o componente:
```python
for c in land.get_components_by_class(unreal.LandscapeSplinesComponent):
    c.destroy_component(land)
```
Remover só atores não resolve — a spline é *componente do Landscape*.

---

## 9. UI do Landscape: import travava no meio

**Sintoma:** botão "Importar" ficava desabilitado, ou clicava e nada acontecia.

**Causas (várias, empilhadas):**
- Digitar o caminho **repetidas vezes** concatenava o texto → caminho inválido
  (`.../a.png/home/.../a.png`). Sintoma revelador: botão "Restaurar para o
  padrão" **habilitado** (valor não-default) mas resolução `(inválido)`.
- O botão "Importar" ficava **fora da área visível** do painel (janela de
  724 px de altura). Cliques em widget com `pos=0,0 size=0,0` não funcionam.
- Mudar a resolução do display **no meio da sessão** fez o Slate perder o
  registro de janelas (`Windows list` retornava vazio).

**Soluções:**
- Antes de digitar, clicar em "Restaurar para o padrão" para **limpar** o campo.
- Digitar na textbox **interna** (`tb5`), não no wrapper.
- Aumentar a resolução do X **antes** de lançar o editor
  (`xrandr --output HDMI-0 --mode 1920x1200`), nunca no meio.
- Refazer `Observe()` depois de qualquer mudança de layout: os snapshots vêm
  de cache e geometria velha causa cliques no lugar errado.

**Decisão final:** abandonar a UI para essa tarefa. Python via `-ExecCmds` é
determinístico e repetível.

---

## 10. `create_render_target2d(None, ...)` → segfault

**Sintoma:** commandlet headless morria com signal 11.

**Causa:** passar `None` como *world context object*.
Aviso no log antes do crash:
```
RenderingLibrary: A null object was passed as a world context object
```

**Solução:** passar um ator válido do nível (usei o próprio `land`).
Bônus: operações de render target precisam de **RHI real** — não rodam bem em
commandlet. Fazer isso no editor GUI via `-ExecCmds`.

---

## 11. Save falhava por referência ao blueprint do mapa original

**Sintoma:**
```
Can't save ChernarusTerrain.umap: Illegal reference to private object:
BlueprintGeneratedClass /Game/Forest/Maps/Demo.Demo_C
```

**Causa:** `duplicate_asset` copiou o Level Blueprint mantendo referência ao
`Demo_C` do mapa de origem.

**Solução:** usar `LevelEditorSubsystem.new_level_from_template(dst, src)`,
que faz o fixup correto de referências. E destruir o ator `Demo_C_1`.

---

## 12. Resultados MCP grandes estouram o limite de tokens

**Sintoma:** `CaptureViewport` retorna erro de tamanho; screenshot vira
arquivo `.txt` de ~1–2 MB.

**Causa:** PNG em base64 dentro do JSON de resposta.

**Solução:** ler o `.txt` salvo, extrair `returnValue.image.data` e decodificar:
```python
j = json.load(open(path))
open("out.png","wb").write(base64.b64decode(j["returnValue"]["image"]["data"]))
```
Nunca copiar base64 manualmente — corrompe (padding inválido).

---

## 13. Nomes de toolset/tool no MCP

**Sintoma:** `Toolset 'editor_toolset.toolsets.scene' not found`.

**Causa:** `toolset_name` precisa do caminho **completo incluindo a classe**
(`editor_toolset.toolsets.scene.SceneTools`), enquanto `tool_name` vai **sem**
esse prefixo (`add_to_scene_from_asset`).

---

## 14. Schema MCP exige todos os campos

**Sintoma:** `input param "x" needs a default value` / `is required`.

**Causa:** as ferramentas deste plugin exigem **todos** os campos do schema
explicitamente, inclusive os que têm default declarado.

**Exemplo** — `CaptureViewport` sem anotações:
```json
{"bShowUI": false,
 "captureTransform": {"location":{...},"rotation":{...},"scale":{...}},
 "annotations": {"gridSpacing":0,"gridExtent":0,"gridHeight":0,
                 "maxLabelDistance":0,"classFilter":{"refPath":""},"maxLabels":0}}
```

---

## 15. Outros

| Sintoma | Causa | Solução |
|---|---|---|
| `EditorFoliageLibrary` não existe | API imaginada | Remover `InstancedFoliageActor` direto |
| `component_size_quads` não encontrado | não exposto ao Python | Deduzir por `get_actor_bounds` e nº de componentes |
| Câmeras mirando o céu | pitch chutado | `pitch = atan2(dz, hypot(dx,dy))` (look-at real) |
| Editor recusa rodar como root | política da engine | Rodar como usuário `user` |
| `Setup.sh` baixa tudo | default da engine | Excluir Win64/Mac/iOS/tvOS/Android/HoloLens |
| Console in-editor via xdotool instável | barra "Cmd" é display, não campo | `-ExecCmds` no lançamento |

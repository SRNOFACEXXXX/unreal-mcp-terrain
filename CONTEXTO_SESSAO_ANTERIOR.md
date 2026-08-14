# Contexto para a próxima sessão

> Documentação completa: [README.md](README.md) ·
> [docs/DIARIO.md](docs/DIARIO.md) ·
> [docs/ERROS_E_ARMADILHAS.md](docs/ERROS_E_ARMADILHAS.md) ·
> [docs/PIPELINE.md](docs/PIPELINE.md)

## Onde estamos

Terreno procedural de 1270 m × 1270 m com 4 biomas **pronto e aplicado** no
mapa `/Game/Maps/ChernarusTerrain`:

- erosão hidráulica real (drenagem dendrítica, cristas, vales)
- biomas com fronteiras orgânicas: montanha 235 m (NE), floresta ~105 m (NO),
  planície ~42 m (SO), pântano ~15 m (SE)
- material pintado por inclinação/altitude (4 weightmaps)
- 10 sítios aplainados para cidades/vilarejos (lista em `Heightmaps/v2_sites.json`)
- 6 câmeras de verificação, imagens em `docs/img/`

## Regras que NÃO podem ser quebradas

1. **Nunca** rodar `py <script>` digitando no console do editor — crash
   (`SMultiLineEditableText::OnKeyDown` → SIGSEGV). Sempre `-ExecCmds`.
2. Render target exige **RHI real** → editor GUI, não commandlet.
3. Contexto de mundo nunca `None` → passar um ator do nível.
4. Todo campo do schema MCP é obrigatório, mesmo com default.
5. `toolset_name` com caminho completo; `tool_name` sem prefixo.
6. Heightmap **precisa** ter 636×636 (5 componentes × 127 quads + 1).
7. `ScaleZ = 100` no Landscape → `H16 = 32768 + elevacao_m * 128`.
8. Erosão só funciona em espaço **normalizado 0–1** (converter p/ metros depois).
9. `Content/` não vai para o git (pack pago da Leartes, licença proíbe).

## Comandos úteis

```bash
# gerar terreno (local, ~90s)
python3 scripts/gen/gen_v2.py

# aplicar no engine + subir MCP
DISPLAY=:0 /root/UnrealEngine/Engine/Binaries/Linux/UnrealEditor \
  /home/user/projetogame/MCPTest/MCPTest.uproject \
  -ExecCmds="ModelContextProtocol.StartServer 8000, py /home/user/projetogame/MCPTest/scripts/ue/apply_v2.py"

# capturar vistas (editor aberto)
python3 scripts/mcp/shoot3.py
```

## Próximo passo

**Vegetação por bioma.** A vegetação do pack foi removida porque estava nas
posições do terreno antigo. Assets disponíveis em
`Content/Forest/Assets/`: Trees (Fir ×5, Scots Pine ×6, Birch ×3), Grass (×6),
Ground_Plants (×11, incluindo juncos para o pântano), Props, Buildings (×22).

Regras de custo já acordadas: vegetação sempre por **instancing** (nunca atores
individuais), sombra seletiva, distância de corte explícita, medir antes de
otimizar (`stat unit/gpu/rhi`).

Depois: construções nos 10 sítios, água no rio/lago, estradas por splines.

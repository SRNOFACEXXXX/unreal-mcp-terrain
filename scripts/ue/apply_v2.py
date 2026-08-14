"""Aplica o terreno v2 (erodido, 4 biomas) no Landscape:
  - altura  (v2_height_rg.png, codificada em R+G)
  - pesos   (v2_w_<Layer>.png) que pintam o material Landscape_01
Precisa de RHI real: rodar via -ExecCmds no editor GUI.
"""
import json
import unreal

LEVEL = "/Game/Maps/ChernarusTerrain"
HM_DIR = "/home/user/projetogame/MCPTest/Heightmaps"
OUT = "/home/user/projetogame/MCPTest/py_report.txt"
DIM = 636

lines = []


def log(m):
    lines.append(str(m))
    unreal.log("[V2] %s" % m)
    with open(OUT, "w") as f:
        f.write("\n".join(lines) + "\n")


log("inicio apply v2")

les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
eal = unreal.EditorAssetLibrary

les.load_level(LEVEL)
log("nivel: %s" % les.get_current_level().get_outer().get_path_name())

land = None
for a in eas.get_all_level_actors():
    if isinstance(a, unreal.Landscape):
        land = a
        break

if land is None:
    log("ERRO: sem landscape")
    raise SystemExit

log("landscape: %s" % land.get_name())

# escala Z = 100 -> H = 32768 + elev_m * 128 (bate com o gerador)
t = land.get_actor_transform()
land.set_actor_scale3d(unreal.Vector(t.scale3d.x, t.scale3d.y, 100.0))
log("scale: %s" % land.get_actor_transform().scale3d)


def blit_png_to_rt(png_path, size):
    """Importa o PNG e desenha 1:1 numa render target do mesmo tamanho."""
    tex = unreal.RenderingLibrary.import_file_as_texture2d(None, png_path)
    if tex is None:
        log("  !! falha ao importar %s" % png_path)
        return None
    rt = unreal.RenderingLibrary.create_render_target2d(
        land, size, size, unreal.TextureRenderTargetFormat.RTF_RGBA8)
    canvas, _sz, ctx = unreal.RenderingLibrary.begin_draw_canvas_to_render_target(land, rt)
    canvas.draw_texture(tex,
                        unreal.Vector2D(0, 0), unreal.Vector2D(size, size),
                        unreal.Vector2D(0, 0), unreal.Vector2D(1, 1),
                        unreal.LinearColor.WHITE,
                        unreal.BlendMode.BLEND_OPAQUE)
    unreal.RenderingLibrary.end_draw_canvas_to_render_target(land, ctx)
    return rt


# ------------------------------------------------------------ 1. ALTURA
rt = blit_png_to_rt("%s/v2_height_rg.png" % HM_DIR, DIM)
if rt is not None:
    ok = land.landscape_import_heightmap_from_render_target(rt, True, 0)
    log("import heightmap -> %s" % ok)
    unreal.RenderingLibrary.release_render_target2d(rt)

# --------------------------------------------------- 2. NOMES DAS CAMADAS
LAYER_ASSETS = {
    "Rock_01": "/Game/Forest/Materials/Landscape/Rock_01_LayerInfo",
    "Grass_Ivy_01": "/Game/Forest/Materials/Landscape/Grass_Ivy_01_LayerInfo",
    "Dead_Leaves_01": "/Game/Forest/Materials/Landscape/Dead_Leaves_01_LayerInfo",
    "Dry_Ground_01": "/Game/Forest/Materials/Landscape/Dry_Ground_01_LayerInfo",
}

resolved = {}
for key, path in LAYER_ASSETS.items():
    try:
        li = eal.load_asset(path)
        if li is None:
            log("  layerinfo nao carregou: %s" % path)
            continue
        try:
            lname = str(li.get_editor_property("layer_name"))
        except Exception:
            lname = key
        resolved[key] = lname
        log("  layer %-16s -> nome interno '%s'" % (key, lname))
    except Exception as e:
        log("  erro layerinfo %s: %r" % (key, e))

# ------------------------------------------------------------ 3. PESOS
for key, lname in resolved.items():
    png = "%s/v2_w_%s.png" % (HM_DIR, key)
    rt = blit_png_to_rt(png, DIM)
    if rt is None:
        continue
    try:
        ok = land.landscape_import_weightmap_from_render_target(rt, lname, 0)
        log("import weightmap %-16s (%s) -> %s" % (key, lname, ok))
    except Exception as e:
        log("weightmap %s falhou: %r" % (key, e))
    unreal.RenderingLibrary.release_render_target2d(rt)

# ------------------------------------------------------------ 4. SALVAR
log("save_current_level -> %s" % les.save_current_level())
log("FIM V2")

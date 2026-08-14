"""Fase 2 (precisa de RHI real - rodar via -ExecCmds no editor GUI, nunca
digitando no console do editor, que trava a engine em UE 5.8):
Importa o heightmap real (DEM codificado em R+G) no Landscape do mapa de
teste ChernarusTerrain.
"""
import unreal

LEVEL = "/Game/Maps/ChernarusTerrain"
PNG = "/home/user/projetogame/MCPTest/Heightmaps/chernarus_rg_encoded_256.png"
OUT = "/home/user/projetogame/MCPTest/py_report.txt"

lines = []


def log(m):
    lines.append(str(m))
    unreal.log("[PHASE2] %s" % m)
    with open(OUT, "w") as f:
        f.write("\n".join(lines) + "\n")


log("inicio fase 2")

les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)

cur = les.get_current_level().get_outer().get_path_name()
if not cur.startswith(LEVEL):
    les.load_level(LEVEL)
    log("nivel carregado: %s" % LEVEL)
else:
    log("nivel ja ativo: %s" % cur)

land = None
for a in eas.get_all_level_actors():
    if isinstance(a, unreal.Landscape):
        land = a
        break

if land is None:
    log("ERRO: Landscape nao encontrado")
else:
    log("landscape alvo: %s" % land.get_name())

    tex = unreal.RenderingLibrary.import_file_as_texture2d(None, PNG)
    log("textura importada: %s (%sx%s)" % (
        tex is not None,
        tex.blueprint_get_size_x() if tex else None,
        tex.blueprint_get_size_y() if tex else None))

    rt = unreal.RenderingLibrary.create_render_target2d(
        land, 256, 256, unreal.TextureRenderTargetFormat.RTF_RGBA8)
    log("render target criado: %s" % (rt is not None))

    canvas, ctx_size, ctx = unreal.RenderingLibrary.begin_draw_canvas_to_render_target(land, rt)
    canvas.draw_texture(
        tex,
        unreal.Vector2D(0, 0),
        unreal.Vector2D(256, 256),
        unreal.Vector2D(0, 0),
        unreal.Vector2D(1, 1),
        unreal.LinearColor.WHITE,
        unreal.BlendMode.BLEND_OPAQUE,
    )
    unreal.RenderingLibrary.end_draw_canvas_to_render_target(land, ctx)
    log("textura desenhada na render target")

    ok = land.landscape_import_heightmap_from_render_target(rt, True, 0)
    log("landscape_import_heightmap_from_render_target -> %s" % ok)

    unreal.RenderingLibrary.release_render_target2d(rt)

    t = land.get_actor_transform()
    log("pos-import transform: loc=%s scale=%s" % (t.translation, t.scale3d))

    saved = les.save_current_level()
    log("save_current_level -> %s" % saved)

log("FIM FASE 2")

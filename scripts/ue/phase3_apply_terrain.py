"""Aplica o heightmap procedural de 4 biomas (636x636, cobre o Landscape
inteiro) no mapa ChernarusTerrain. Limpa foliage/atores antigos que nao
fazem mais sentido com a nova altura. Precisa de RHI real (-ExecCmds no
editor GUI, nunca digitar no console)."""
import unreal

LEVEL = "/Game/Maps/ChernarusTerrain"
PNG = "/home/user/projetogame/MCPTest/Heightmaps/chernarus_4biome_rg_636.png"
OUT = "/home/user/projetogame/MCPTest/py_report.txt"

lines = []


def log(m):
    lines.append(str(m))
    unreal.log("[PHASE3] %s" % m)
    with open(OUT, "w") as f:
        f.write("\n".join(lines) + "\n")


log("inicio fase 3")

les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)

les.load_level(LEVEL)
log("nivel: %s" % les.get_current_level().get_outer().get_path_name())

land = None
for a in eas.get_all_level_actors():
    if isinstance(a, unreal.Landscape):
        land = a
        break

if land is None:
    log("ERRO: sem landscape")
else:
    log("landscape: %s" % land.get_name())

    # ajusta ScaleZ para 100 (bate com a codificacao do heightmap: Height =
    # 32768 + WorldZ_cm * 128/ScaleZ)
    t = land.get_actor_transform()
    log("scale antes: %s" % t.scale3d)
    new_scale = unreal.Vector(t.scale3d.x, t.scale3d.y, 100.0)
    land.set_actor_scale3d(new_scale)
    log("scale depois: %s" % land.get_actor_transform().scale3d)

    # limpa foliage antigo (nao bate mais com a nova altura)
    removed_foliage = 0
    for a in eas.get_all_level_actors():
        if isinstance(a, unreal.InstancedFoliageActor):
            try:
                a.get_editor_property  # noop, apenas valida
            except Exception:
                pass
    # remove foliage via subsystem dedicado (mais confiavel que mexer no ator)
    try:
        foliage_types = unreal.EditorFoliageLibrary.get_foliage_types_in_level(
            les.get_current_level())
        log("tipos de foliage no nivel: %d" % len(foliage_types))
        for ft in foliage_types:
            n = unreal.EditorFoliageLibrary.remove_foliage_type(
                les.get_current_level(), [ft], False, False)
            removed_foliage += 1
    except Exception as e:
        log("remocao de foliage falhou: %r" % (e,))
    log("tipos de foliage removidos: %d" % removed_foliage)

    # importa o heightmap novo cobrindo TODO o landscape (636x636)
    tex = unreal.RenderingLibrary.import_file_as_texture2d(None, PNG)
    log("textura importada: %s (%sx%s)" % (
        tex is not None,
        tex.blueprint_get_size_x() if tex else None,
        tex.blueprint_get_size_y() if tex else None))

    rt = unreal.RenderingLibrary.create_render_target2d(
        land, 636, 636, unreal.TextureRenderTargetFormat.RTF_RGBA8)
    log("render target 636x636 criado: %s" % (rt is not None))

    canvas, ctx_size, ctx = unreal.RenderingLibrary.begin_draw_canvas_to_render_target(land, rt)
    canvas.draw_texture(
        tex,
        unreal.Vector2D(0, 0),
        unreal.Vector2D(636, 636),
        unreal.Vector2D(0, 0),
        unreal.Vector2D(1, 1),
        unreal.LinearColor.WHITE,
        unreal.BlendMode.BLEND_OPAQUE,
    )
    unreal.RenderingLibrary.end_draw_canvas_to_render_target(land, ctx)
    log("textura desenhada na RT")

    ok = land.landscape_import_heightmap_from_render_target(rt, True, 0)
    log("landscape_import_heightmap_from_render_target(636) -> %s" % ok)

    unreal.RenderingLibrary.release_render_target2d(rt)

    saved = les.save_current_level()
    log("save_current_level -> %s" % saved)

log("FIM FASE 3")

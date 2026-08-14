"""Reaplica os weightmaps rebalanceados e remove as splines de estrada do pack
(que ficaram flutuando com o Z do terreno antigo)."""
import unreal

LEVEL = "/Game/Maps/ChernarusTerrain"
HM_DIR = "/home/user/projetogame/MCPTest/Heightmaps"
OUT = "/home/user/projetogame/MCPTest/py_report.txt"
DIM = 636

lines = []


def log(m):
    lines.append(str(m))
    unreal.log("[V3] %s" % m)
    with open(OUT, "w") as f:
        f.write("\n".join(lines) + "\n")


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
    log("ERRO sem landscape")
    raise SystemExit

# ---------------------------------------------- remove splines de estrada
try:
    splines = land.get_components_by_class(unreal.LandscapeSplinesComponent)
    log("componentes de spline encontrados: %d" % len(splines))
    for c in splines:
        try:
            c.set_visibility(False, True)
            c.destroy_component(land)
            log("  spline destruida")
        except Exception as e:
            log("  falha ao destruir spline: %r" % (e,))
except Exception as e:
    log("busca de splines falhou: %r" % (e,))

# tambem remove atores de spline soltos
removed = 0
for a in list(eas.get_all_level_actors()):
    cn = a.get_class().get_name()
    if "Spline" in cn:
        try:
            eas.destroy_actor(a)
            removed += 1
        except Exception:
            pass
log("atores de spline removidos: %d" % removed)


def blit(png, size):
    tex = unreal.RenderingLibrary.import_file_as_texture2d(None, png)
    if tex is None:
        return None
    rt = unreal.RenderingLibrary.create_render_target2d(
        land, size, size, unreal.TextureRenderTargetFormat.RTF_RGBA8)
    canvas, _s, ctx = unreal.RenderingLibrary.begin_draw_canvas_to_render_target(land, rt)
    canvas.draw_texture(tex, unreal.Vector2D(0, 0), unreal.Vector2D(size, size),
                        unreal.Vector2D(0, 0), unreal.Vector2D(1, 1),
                        unreal.LinearColor.WHITE, unreal.BlendMode.BLEND_OPAQUE)
    unreal.RenderingLibrary.end_draw_canvas_to_render_target(land, ctx)
    return rt


# ---------------------------------------------- reaplica pesos
for layer in ("Rock_01", "Grass_Ivy_01", "Dead_Leaves_01", "Dry_Ground_01"):
    rt = blit("%s/v2_w_%s.png" % (HM_DIR, layer), DIM)
    if rt is None:
        log("  %s: textura nao importou" % layer)
        continue
    ok = land.landscape_import_weightmap_from_render_target(rt, layer, 0)
    log("weightmap %-16s -> %s" % (layer, ok))
    unreal.RenderingLibrary.release_render_target2d(rt)

log("save -> %s" % les.save_current_level())
log("FIM V3")

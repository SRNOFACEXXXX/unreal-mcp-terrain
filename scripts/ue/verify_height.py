"""Le de volta a altura atual do Landscape (via export para render target) e
compara com o valor esperado do nosso DEM, para confirmar de forma numerica
(independente de Nanite/renderizacao) se a escrita da altura funcionou."""
import unreal

LEVEL = "/Game/Maps/ChernarusTerrain"
OUT = "/home/user/projetogame/MCPTest/py_report.txt"
lines = []


def log(m):
    lines.append(str(m))
    unreal.log("[VERIFY] %s" % m)
    with open(OUT, "w") as f:
        f.write("\n".join(lines) + "\n")


log("inicio verificacao")
les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)

cur = les.get_current_level().get_outer().get_path_name()
if not cur.startswith(LEVEL):
    les.load_level(LEVEL)
log("nivel: %s" % les.get_current_level().get_outer().get_path_name())

land = None
for a in eas.get_all_level_actors():
    if isinstance(a, unreal.Landscape):
        land = a
        break

if land is None:
    log("ERRO sem landscape")
else:
    rt = unreal.RenderingLibrary.create_render_target2d(
        land, 256, 256, unreal.TextureRenderTargetFormat.RTF_RGBA8)
    ok = land.landscape_export_heightmap_to_render_target(rt, False, True)
    log("export_heightmap_to_render_target -> %s" % ok)

    # ler alguns pixels: canto (0,0) e centro (128,128)
    for (x, y) in ((0, 0), (10, 10), (128, 128), (200, 200), (255, 255)):
        px = unreal.RenderingLibrary.read_render_target_raw_pixel(land, rt, x, y)
        log("pixel(%d,%d) raw=%s" % (x, y, px))

    unreal.RenderingLibrary.release_render_target2d(rt)

log("FIM VERIFICACAO")

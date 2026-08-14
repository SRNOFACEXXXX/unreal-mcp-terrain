"""Fase 1 (headless): cria o mapa base do terreno a partir do Demo do pack,
limpa os props do vendor e salva. Sem render target (isso exige RHI real e
roda na fase 2, dentro do editor GUI).

  UnrealEditor-Cmd <uproject> -run=pythonscript -script=build_map.py
"""
import unreal

SRC = "/Game/Forest/Maps/Demo"
DST = "/Game/Maps/ChernarusTerrain"
OUT = "/home/user/projetogame/MCPTest/py_report.txt"

lines = []


def log(m):
    """Grava incrementalmente: se a engine crashar, o diagnostico sobrevive."""
    lines.append(str(m))
    unreal.log("[BUILD] %s" % m)
    with open(OUT, "w") as f:
        f.write("\n".join(lines) + "\n")


eal = unreal.EditorAssetLibrary
les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)

log("inicio")

if eal.does_asset_exist(DST):
    eal.delete_asset(DST)
    log("destino anterior removido")

log("new_level_from_template -> %s" % les.new_level_from_template(DST, SRC))
log("nivel atual: %s" % les.get_current_level().get_outer().get_path_name())

KEEP_CLASSES = (
    unreal.Landscape,
    unreal.DirectionalLight,
    unreal.SkyLight,
    unreal.SkyAtmosphere,
    unreal.ExponentialHeightFog,
    unreal.PostProcessVolume,
    unreal.PlayerStart,
    unreal.WorldSettings,
    unreal.LightmassImportanceVolume,
    unreal.InstancedFoliageActor,
)
KEEP_NAMES = ("BP_Sky_Sphere_C", "SkySphere", "AtmosphericFog")

removed = 0
for a in eas.get_all_level_actors():
    try:
        if isinstance(a, KEEP_CLASSES):
            continue
        if a.get_class().get_name() in KEEP_NAMES:
            continue
        eas.destroy_actor(a)
        removed += 1
    except Exception:
        pass
log("atores removidos: %d" % removed)
log("restantes: %s" % [a.get_name() for a in eas.get_all_level_actors()])

land = None
for a in eas.get_all_level_actors():
    if isinstance(a, unreal.Landscape):
        land = a
        break

if land is None:
    log("ERRO: sem Landscape")
else:
    t = land.get_actor_transform()
    log("landscape=%s location=%s scale=%s"
        % (land.get_name(), t.translation, t.scale3d))
    comps = land.get_components_by_class(unreal.LandscapeComponent)
    log("componentes=%d" % len(comps))
    if comps:
        c = comps[0]
        for p in ("component_size_quads", "subsection_size_quads",
                  "num_subsections"):
            try:
                log("comp.%s = %s" % (p, c.get_editor_property(p)))
            except Exception:
                log("comp.%s -> indisponivel" % p)
        # bounds dao a extensao real do terreno
        try:
            o, ext = land.get_actor_bounds(False)
            log("bounds origin=%s extent=%s" % (o, ext))
        except Exception as e:
            log("bounds falhou: %r" % (e,))

log("save_current_level -> %s" % les.save_current_level())
log("FIM OK")

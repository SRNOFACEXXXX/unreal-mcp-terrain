"""Duplica o mapa Demo do pack (que ja traz Landscape + iluminacao configurados)
para servir de base do nosso mapa de teste, e reporta a geometria do landscape."""
import unreal

SRC = "/Game/Forest/Maps/Demo"
DST = "/Game/Maps/ChernarusTerrain"
OUT = "/home/user/projetogame/MCPTest/py_report.txt"

lines = []


def log(m):
    lines.append(str(m))
    unreal.log("[STEP1] %s" % m)


eal = unreal.EditorAssetLibrary
les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)

if eal.does_asset_exist(DST):
    log("destino ja existe, removendo")
    eal.delete_asset(DST)

ok = eal.duplicate_asset(SRC, DST)
log("duplicate_asset -> %s" % (ok is not None))

les.load_level(DST)
log("nivel aberto: %s" % DST)

eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
actors = eas.get_all_level_actors()
log("total de atores: %d" % len(actors))

for a in actors:
    if isinstance(a, unreal.Landscape):
        log("--- Landscape: %s" % a.get_name())
        comps = a.get_components_by_class(unreal.LandscapeComponent)
        log("componentes: %d" % len(comps))
        t = a.get_actor_transform()
        log("escala: %s" % t.scale3d)
        log("local: %s" % t.translation)
        try:
            log("ComponentSizeQuads=%s" % a.get_editor_property("component_size_quads"))
            log("SubsectionSizeQuads=%s" % a.get_editor_property("subsection_size_quads"))
            log("NumSubsections=%s" % a.get_editor_property("num_subsections"))
        except Exception as e:
            log("props: %r" % (e,))

with open(OUT, "w") as f:
    f.write("\n".join(lines) + "\n")
unreal.log("[STEP1] fim")

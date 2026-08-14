import unreal

OUT = "/home/user/projetogame/MCPTest/py_report.txt"
lines = []


def log(m):
    lines.append(str(m))
    with open(OUT, "w") as f:
        f.write("\n".join(lines) + "\n")


les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
les.load_level("/Game/Maps/ChernarusTerrain")

eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
land = None
for a in eas.get_all_level_actors():
    if isinstance(a, unreal.Landscape):
        land = a
        break

if land is None:
    log("sem landscape no nivel atual: %s" % unreal.get_editor_subsystem(
        unreal.LevelEditorSubsystem).get_current_level().get_outer().get_path_name())
else:
    comps = land.get_components_by_class(unreal.LandscapeComponent)
    log("num componentes=%d" % len(comps))
    xs, ys = [], []
    sizes = set()
    for c in comps:
        try:
            sx = c.get_editor_property("section_base_x")
            sy = c.get_editor_property("section_base_y")
            csq = c.get_editor_property("component_size_quads")
            xs.append(sx)
            ys.append(sy)
            sizes.add(csq)
        except Exception as e:
            log("erro comp: %r" % (e,))
    if xs:
        log("section_base_x range: %d..%d" % (min(xs), max(xs)))
        log("section_base_y range: %d..%d" % (min(ys), max(ys)))
        log("component_size_quads set: %s" % sizes)
        comp_quads = sizes.pop() if len(sizes) == 1 else max(sizes)
        total_quads_x = (max(xs) - min(xs)) + comp_quads
        total_quads_y = (max(ys) - min(ys)) + comp_quads
        log("total_quads = %d x %d" % (total_quads_x, total_quads_y))
        log("heightmap_resolution = %d x %d" % (total_quads_x + 1, total_quads_y + 1))

log("fim")

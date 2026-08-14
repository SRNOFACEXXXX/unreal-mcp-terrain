import unreal

OUT = "/home/user/projetogame/MCPTest/py_report.txt"
lines = []


def log(m):
    lines.append(str(m))
    with open(OUT, "w") as f:
        f.write("\n".join(lines) + "\n")


log("RenderingLibrary: %s" % [m for m in dir(unreal.RenderingLibrary) if not m.startswith('_')])
log("")
log("LandscapeProxy height/import methods: %s" % [m for m in dir(unreal.LandscapeProxy) if 'height' in m.lower() or 'import' in m.lower()])
log("")
log("TextureFactory: %s" % [m for m in dir(unreal.TextureFactory) if not m.startswith('_')])
log("")
log("AssetImportTask attrs: %s" % [m for m in dir(unreal.AssetImportTask) if not m.startswith('_')])
log("")
try:
    log("AssetToolsHelpers has import_assets: %s" % hasattr(unreal.AssetToolsHelpers.get_asset_tools(), 'import_assets_automated'))
except Exception as e:
    log("AssetTools err: %r" % (e,))
log("done")

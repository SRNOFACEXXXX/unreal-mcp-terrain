"""Limpeza final dos restos do pack + capturas com enquadramento correto."""
import base64
import json
import math
import os

import mcp

OUTDIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "shots")
os.makedirs(OUTDIR, exist_ok=True)

SCENE = "editor_toolset.toolsets.scene.SceneTools"
EDITOR = "EditorToolset.EditorAppToolset"

mcp.connect()

res = mcp.call(SCENE, "find_actors", {"name": "", "tag": "", "collision_channels": []})
actors = mcp.result_json(res)["returnValue"]
print("atores no nivel: %d" % len(actors))
for a in actors:
    print("   ", a["refPath"].split("PersistentLevel.")[-1])

DROP_SUBSTR = ("Spline", "LightmassImportanceVolume", "PostProcessVolume",
               "InstancedFoliageActor", "LandscapeGizmo", "Demo_C", "Brush_")
removed = 0
for a in actors:
    p = a["refPath"]
    tail = p.split("PersistentLevel.")[-1]
    if any(d in tail for d in DROP_SUBSTR):
        mcp.call(SCENE, "remove_from_scene", {"actor": {"refPath": p}})
        print("removido:", tail)
        removed += 1
print("removidos: %d" % removed)

meta = json.load(open("/home/user/projetogame/MCPTest/Heightmaps/v2_sites.json"))
OX, OY = meta["landscape_origin_cm"]
W = meta["world_m"] * 100.0


def world(x_cm, y_cm):
    return OX + x_cm, OY + y_cm


def shoot(name, eye, target):
    dx, dy, dz = (target[i] - eye[i] for i in range(3))
    horiz = math.hypot(dx, dy)
    yaw = math.degrees(math.atan2(dy, dx))
    pitch = math.degrees(math.atan2(dz, horiz))
    args = {
        "bShowUI": False,
        "captureTransform": {
            "location": {"x": eye[0], "y": eye[1], "z": eye[2]},
            "rotation": {"pitch": pitch, "yaw": yaw, "roll": 0},
            "scale": {"x": 1, "y": 1, "z": 1}},
        "annotations": {"gridSpacing": 0, "gridExtent": 0, "gridHeight": 0,
                        "maxLabelDistance": 0, "classFilter": {"refPath": ""},
                        "maxLabels": 0},
    }
    j = mcp.result_json(mcp.call(EDITOR, "CaptureViewport", args))
    try:
        b64 = j["returnValue"]["image"]["data"]
    except Exception:
        print("  %s FALHOU %s" % (name, str(j)[:160]))
        return
    path = os.path.join(OUTDIR, "%s.png" % name)
    with open(path, "wb") as f:
        f.write(base64.b64decode(b64))
    print("  %s  pitch=%.0f yaw=%.0f (%dKB)" % (name, pitch, yaw,
                                                os.path.getsize(path) // 1024))


CX, CY = world(W / 2, W / 2)

# panoramicas: camera afastada nas diagonais, olhando o centro do terreno
shoot("A_pano_sudoeste", (CX - 88000, CY - 88000, 52000), (CX, CY, 7000))
shoot("B_pano_nordeste", (CX + 82000, CY + 78000, 46000), (CX, CY, 7000))

# biomas: camera DENTRO do mapa, olhando o assentamento com o bioma ao fundo
SHOTS = [
    # nome,           alvo_x, alvo_y, alvo_z_m, olho_x, olho_y, olho_z_m
    ("C_montanha",  27600, 108000, 170.9, 60000,  75000, 235.0),
    ("D_floresta",  20400,  43000, 105.9, 62000,  60000, 175.0),
    ("E_planicie",  70600,  22800,  39.8, 40000,  60000, 110.0),
    ("F_pantano",  106400, 115000,  14.6, 72000,  78000, 105.0),
]
for (name, tx0, ty0, tz_m, ex0, ey0, ez_m) in SHOTS:
    tx, ty = world(tx0, ty0)
    ex, ey = world(ex0, ey0)
    shoot(name, (ex, ey, ez_m * 100), (tx, ty, tz_m * 100))

print("fim")

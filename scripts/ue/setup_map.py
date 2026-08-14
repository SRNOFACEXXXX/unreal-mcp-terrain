"""Cria o nivel de teste vazio para o mapa Chernarus-like e reporta o que a
API de Landscape expoe ao Python. Executado via `py <este arquivo>`."""
import unreal

OUT = "/home/user/projetogame/MCPTest/py_report.txt"
LEVEL = "/Game/Maps/ChernarusTest"

lines = []


def log(msg):
    lines.append(str(msg))
    unreal.log("[SETUP] %s" % msg)


try:
    les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    log("LevelEditorSubsystem OK")
    try:
        les.new_level(LEVEL)
        log("new_level criado: %s" % LEVEL)
    except Exception as e:
        log("new_level falhou: %r" % (e,))
except Exception as e:
    log("LevelEditorSubsystem indisponivel: %r" % (e,))

# O que existe para landscape?
for name in ("Landscape", "LandscapeProxy", "LandscapeSubsystem"):
    log("has unreal.%s = %s" % (name, hasattr(unreal, name)))

try:
    meths = [m for m in dir(unreal.LandscapeProxy)
             if any(k in m.lower() for k in ("import", "height", "creat"))]
    log("LandscapeProxy metodos relevantes: %s" % meths)
except Exception as e:
    log("introspeccao LandscapeProxy falhou: %r" % (e,))

with open(OUT, "w") as f:
    f.write("\n".join(lines) + "\n")

unreal.log("[SETUP] relatorio escrito em %s" % OUT)

import unreal
with open("/home/user/projetogame/MCPTest/probe_out.txt", "w") as f:
    f.write("console python OK\n")
    f.write("level=%s\n" % unreal.get_editor_subsystem(
        unreal.LevelEditorSubsystem).get_current_level().get_outer().get_path_name())
unreal.log("[PROBE] ok")

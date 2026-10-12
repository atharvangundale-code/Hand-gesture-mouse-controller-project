"""
Helper utility to generate Windows desktop/folder shortcuts (.lnk)
with the custom application icon.
"""

import os
import subprocess


def create_windows_shortcut(target_path: str, shortcut_path: str, icon_path: str, description: str):
    target_path = os.path.abspath(target_path)
    shortcut_path = os.path.abspath(shortcut_path)
    icon_path = os.path.abspath(icon_path)
    working_dir = os.path.dirname(target_path)

    vbs_content = f"""Set oWS = WScript.CreateObject("WScript.Shell")
sLinkFile = "{shortcut_path}"
Set oLink = oWS.CreateShortcut(sLinkFile)
oLink.TargetPath = "{target_path}"
oLink.WorkingDirectory = "{working_dir}"
oLink.Description = "{description}"
oLink.IconLocation = "{icon_path}, 0"
oLink.Save
"""
    vbs_temp = os.path.join(working_dir, "_temp_shortcut.vbs")
    with open(vbs_temp, "w", encoding="utf-8") as f:
        f.write(vbs_content)

    subprocess.run(["cscript", "//nologo", vbs_temp], check=True)
    if os.path.exists(vbs_temp):
        os.remove(vbs_temp)


if __name__ == "__main__":
    base_dir = os.path.abspath(os.path.dirname(__file__))
    icon_file = os.path.join(base_dir, "app_icon.ico")

    # 1. Shortcut to Launch_Controller.bat (Direct launch)
    bat_target = os.path.join(base_dir, "Launch_Controller.bat")
    lnk_direct = os.path.join(base_dir, "Start AI Gesture Mouse.lnk")
    create_windows_shortcut(bat_target, lnk_direct, icon_file, "Launch AI Hand Gesture Mouse Controller")

    # 2. Shortcut to activator.py (GUI Activation Panel)
    activator_target = os.path.join(base_dir, "Launch_Activator.bat")
    lnk_gui = os.path.join(base_dir, "AI Gesture Mouse Activator.lnk")
    create_windows_shortcut(activator_target, lnk_gui, icon_file, "Open AI Gesture Controller Activation Panel")

    print(f"[SUCCESS] Shortcuts created successfully in {base_dir}:")
    print(f"  - {os.path.basename(lnk_direct)}")
    print(f"  - {os.path.basename(lnk_gui)}")

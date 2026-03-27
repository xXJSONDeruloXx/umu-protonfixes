"""Game fix for Caravan SandWitch"""

import os
from pathlib import Path
from protonfixes import util


def main() -> None:
    """Install OptiScaler and configure UE5 settings for frame generation."""

    # Install OptiScaler as dxgi.dll to the UE5 executable directory
    game_path = util.get_game_install_path()
    exe_path = os.path.join(game_path, 'CaravanSandWitch', 'Binaries', 'Win64')
    util.install_optiscaler(target_path=exe_path, dll_name='dxgi.dll')

    # Create Engine.ini with OptiScaler-compatible settings
    # This enables DLSS/Streamline/XeFG motion vector paths in UE5
    prefix_path = os.environ.get('STEAM_COMPAT_DATA_PATH', '')
    if not prefix_path:
        return

    engine_ini = Path(prefix_path) / 'pfx/drive_c/users/steamuser/AppData/Local/CaravanSandWitch/Saved/Config/Windows/Engine.ini'
    engine_ini.parent.mkdir(parents=True, exist_ok=True)

    # Make writable if it exists (may have been set read-only previously)
    if engine_ini.exists():
        engine_ini.chmod(0o644)

    engine_config = """\
[SystemSettings]
; OptiScaler - enable OutputScaling & XeFG motion vector path
r.NGX.DLSS.DilateMotionVectors=0
r.Streamline.DilateMotionVectors=0

; OptiScaler - enable DLSS / Streamline / DLSS-G / Reflex
r.ngx.dlss.enable=1
r.Streamline.InitializePlugin=1
r.Streamline.DLSSG.Enable=1
t.Streamline.Reflex.Enable=1

; OptiScaler - enable UE upscaler plugin
r.AntiAliasingMethod=4        ; TSR
r.TemporalAA.Upscaler=1       ; Enable upscaler plugin
"""

    # Write config and make read-only to prevent game from overwriting
    engine_ini.write_text(engine_config, encoding='utf-8')
    engine_ini.chmod(0o444)

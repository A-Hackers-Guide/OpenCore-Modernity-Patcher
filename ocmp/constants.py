"""
constants.py: Global state for OpenCore Modernity Patcher

Mirrors the role of OpenCore Legacy Patcher's constants.py: one object that
every builder and GUI frame reads from and writes to.
"""

import os
import sys
import platform
from pathlib import Path
from typing import Optional

from .datasets import os_data
from . import _version


APP_NAME     = "OpenCore Modernity Patcher"
APP_ID       = "OpenCore-Modernity-Patcher"
APP_VERSION  = _version.VERSION
APP_CHANNEL  = _version.CHANNEL
REPO_URL     = "https://github.com/A-Hackers-Guide/OpenCore-Modernity-Patcher"
COPYRIGHT    = "Copyright © 2026 A Hacker's Guide and contributors"


def _data_root() -> Path:
    """
    Per-user data directory (cache, logs, settings); OCMP_DATA_DIR overrides it
    """
    if os.environ.get("OCMP_DATA_DIR"):
        return Path(os.environ["OCMP_DATA_DIR"])
    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    return base / APP_ID


class Constants:

    def __init__(self) -> None:
        self.patcher_version: str = APP_VERSION
        self.channel:         str = APP_CHANNEL
        self.copyright_date:  str = COPYRIGHT
        self.repo_url:        str = REPO_URL

        # Host
        self.host_os:   str = {"win32": "Windows", "darwin": "macOS"}.get(sys.platform, "Linux")
        self.host_arch: str = platform.machine()

        # Paths
        self.data_path:    Path = _data_root()
        self.cache_path:   Path = self.data_path / "cache"
        self.build_path:   Path = self.data_path / "Build-Folder"
        self.log_filepath: Path = self.data_path / "ocmp.log"
        self.settings_path: Path = self.data_path / "settings.json"

        # Detected / overridden hardware (hardware.HardwareProfile)
        self.computer = None
        self.custom_profile_path: Optional[Path] = None

        # Build settings (exposed in Settings window)
        self.target_os:          int  = os_data.os_data.sequoia
        self.custom_smbios:      str  = ""      # empty = automatic
        self.verbose_debug:      bool = True    # -v
        self.kext_debug:         bool = False   # keepsyms / debug=0x100
        self.opencore_debug:     bool = False   # DEBUG build + logging
        self.showpicker:         bool = True
        self.oc_timeout:         int  = 5
        self.opencanopy:         bool = False   # GUI picker
        self.sip_status:         bool = True
        self.secure_boot_model:  bool = True    # SecureBootModel=Default
        self.vault:              bool = False
        self.cfg_lock_unlocked:  bool = False   # True = AppleXcpmCfgLock off
        self.resizable_bar:      bool = False
        self.disable_dgpu:       bool = False   # -wegnoegpu
        self.alc_layout_id:      int  = 1
        self.custom_serial:      str  = ""
        self.custom_board_serial: str = ""
        self.custom_uuid:        str  = ""
        self.custom_rom:         str  = ""
        self.include_wifi:       bool = True
        self.include_bluetooth:  bool = True
        self.usb_toolbox:        bool = True
        self.extra_boot_args:    str  = ""
        self.github_token:       str  = os.environ.get("GITHUB_TOKEN", "")

        # Runtime
        self.thread_sleep_interval: float = 0.01
        self.last_build_path: Optional[Path] = None

    @property
    def opencore_build(self) -> str:
        return "DEBUG" if self.opencore_debug else "RELEASE"

    def ensure_paths(self) -> None:
        for path in (self.data_path, self.cache_path):
            path.mkdir(parents=True, exist_ok=True)

# -*- mode: python ; coding: utf-8 -*-
#
# PyInstaller spec for OpenCore Modernity Patcher
#   Windows: one-file windowed .exe
#   Linux:   one-folder build that build_appimage.sh wraps into an .AppImage
#
# Run from the repository root:  pyinstaller packaging/ocmp.spec

import sys
from pathlib import Path

ROOT = Path(SPECPATH).parent
ICON = ROOT / "packaging" / "build" / ("icon.ico" if sys.platform == "win32" else "icon.png")

# macrecovery.py is downloaded at runtime and run in-process, so the
# stdlib modules it imports must be bundled even though we never import them.
hidden = ["argparse", "hashlib", "linecache", "random", "struct", "string",
          "urllib.request", "urllib.parse", "http.client"]

a = Analysis(
    [str(ROOT / "packaging" / "launcher.py")],
    pathex=[str(ROOT)],
    hiddenimports=hidden,
    excludes=["tkinter", "unittest", "pytest"],
    noarchive=False,
)
pyz = PYZ(a.pure)

if sys.platform == "win32":
    exe = EXE(
        pyz, a.scripts, a.binaries, a.datas, [],
        name="OpenCore-Modernity-Patcher",
        icon=str(ICON) if ICON.exists() else None,
        console=False,
        upx=False,
        version=str(ROOT / "packaging" / "build" / "version_info.txt") if (ROOT / "packaging" / "build" / "version_info.txt").exists() else None,
    )
else:
    exe = EXE(
        pyz, a.scripts, [],
        exclude_binaries=True,
        name="OpenCore-Modernity-Patcher",
        console=False,
        upx=False,
    )
    coll = COLLECT(exe, a.binaries, a.datas, name="OpenCore-Modernity-Patcher", upx=False)

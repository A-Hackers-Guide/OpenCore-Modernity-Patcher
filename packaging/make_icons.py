"""
make_icons.py: Render the app icon to packaging/build/icon.ico and icon.png

Uses the same drawing code as the GUI, so the .exe/.AppImage icon
matches what the app shows.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import wx  # noqa: E402

from ocmp.wx_gui import gui_icons  # noqa: E402

out = ROOT / "packaging" / "build"
out.mkdir(parents=True, exist_ok=True)
app = wx.App(False)
gui_icons.bitmap("app", 256).ConvertToImage().SaveFile(str(out / "icon.png"), wx.BITMAP_TYPE_PNG)
gui_icons.bitmap("app", 256).ConvertToImage().SaveFile(str(out / "icon.ico"), wx.BITMAP_TYPE_ICO)
print(f"Wrote {out / 'icon.png'} and {out / 'icon.ico'}")

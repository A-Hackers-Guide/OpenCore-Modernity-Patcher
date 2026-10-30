"""
gui_entry.py: Entry point for the wxPython GUI
"""

import sys
import logging

import wx

from .. import constants
from . import gui_main_menu


class EntryPoint:

    def __init__(self, global_constants: constants.Constants) -> None:
        self.app: wx.App = None
        self.constants = global_constants

    def start(self) -> None:
        self.app = wx.App()
        if sys.platform == "win32":
            # Crisp text on high-DPI displays
            try:
                import ctypes
                ctypes.windll.shcore.SetProcessDpiAwareness(1)
            except Exception:
                pass
        logging.info(f"{constants.APP_NAME} {constants.APP_VERSION} on {self.constants.host_os}")
        frame = gui_main_menu.MainFrame(None, title=f"{constants.APP_NAME} ({self.constants.patcher_version})",
                                        global_constants=self.constants)
        frame.Show()
        self.app.MainLoop()

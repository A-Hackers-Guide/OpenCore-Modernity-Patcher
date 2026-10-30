"""
gui_support.py: Utilities for interacting with wxPython GUI

Layout helpers follow OpenCore Legacy Patcher's wx_gui/gui_support.py.
"""

import os
import sys
import time
import logging
import threading
import subprocess

import wx

from .. import constants


def get_font_face():
    if not get_font_face.font_face:
        get_font_face.font_face = wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT).GetFaceName() or "Segoe UI"
    return get_font_face.font_face

get_font_face.font_face = None


def font_factory(size: int, weight):
    """
    OCLP sizes are macOS points; Windows/GTK render the same number larger
    """
    if sys.platform != "darwin":
        size = max(7, round(size * 0.78))
    return wx.Font(size, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, weight, False, get_font_face())


def frame_style():
    return wx.DEFAULT_FRAME_STYLE & ~(wx.RESIZE_BORDER | wx.MAXIMIZE_BOX)


def reveal(path) -> None:
    path = str(path)
    if sys.platform == "win32":
        subprocess.run(["explorer", "/select,", path])
    elif sys.platform == "darwin":
        subprocess.run(["open", "--reveal", path])
    else:
        folder = path if os.path.isdir(path) else os.path.dirname(path)
        subprocess.run(["xdg-open", folder])


def wait_for_thread(thread: threading.Thread, sleep_interval: float = 0.01) -> None:
    while thread.is_alive():
        wx.Yield()
        time.sleep(sleep_interval)


def human_fmt(num: float) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(num) < 1000.0:
            return f"{num:3.1f} {unit}"
        num /= 1000.0
    return f"{num:.1f} PB"


def place(widget: wx.Window, y: int) -> int:
    """
    Centre a widget horizontally at y; return the y just below it
    """
    widget.SetPosition((-1, y))
    widget.Centre(wx.HORIZONTAL)
    return y + widget.GetSize()[1]


class GenerateMenubar:

    def __init__(self, frame: wx.Frame, global_constants: constants.Constants) -> None:
        self.frame = frame
        self.constants = global_constants

    def generate(self) -> wx.MenuBar:
        from . import gui_about
        menubar = wx.MenuBar()
        file_menu = wx.Menu()
        about_item = file_menu.Append(wx.ID_ABOUT, f"&About {constants.APP_NAME}")
        file_menu.AppendSeparator()
        log_item = file_menu.Append(wx.ID_ANY, "&Reveal Log File")
        if sys.platform != "darwin":
            file_menu.AppendSeparator()
            quit_item = file_menu.Append(wx.ID_EXIT, "&Quit\tCtrl+Q")
            self.frame.Bind(wx.EVT_MENU, lambda event: wx.GetApp().ExitMainLoop(), quit_item)
        menubar.Append(file_menu, "&File")
        self.frame.SetMenuBar(menubar)
        self.frame.Bind(wx.EVT_MENU, lambda event: gui_about.AboutFrame(self.constants), about_item)
        self.frame.Bind(wx.EVT_MENU, lambda event: reveal(self.constants.log_filepath), log_item)
        return menubar


class ThreadHandler(logging.Handler):
    """
    Logging handler that appends records to a wx.TextCtrl from any thread
    """

    def __init__(self, text_box: wx.TextCtrl) -> None:
        logging.Handler.__init__(self)
        self.text_box = text_box

    def emit(self, record: logging.LogRecord) -> None:
        msg = self.format(record) + "\n"
        wx.CallAfter(self._append, msg)

    def _append(self, msg: str) -> None:
        if self.text_box and not self.text_box.IsBeingDeleted():
            self.text_box.AppendText(msg)


class RelaunchAsAdmin:
    """
    Writing EFI partitions and USB drives needs Administrator/root
    """

    @staticmethod
    def is_admin() -> bool:
        if sys.platform == "win32":
            try:
                import ctypes
                return bool(ctypes.windll.shell32.IsUserAnAdmin())
            except Exception:
                return False
        return os.geteuid() == 0

    @staticmethod
    def explain(parent: wx.Window) -> None:
        if sys.platform == "win32":
            how = "Right-click the app and choose \"Run as administrator\"."
        else:
            how = "Start it from a terminal with: sudo -E ./OpenCore-Modernity-Patcher.AppImage"
        wx.MessageDialog(parent, f"This step writes directly to a disk and needs administrator rights.\n\n{how}",
                         "Administrator rights required", style=wx.OK | wx.ICON_WARNING).ShowModal()

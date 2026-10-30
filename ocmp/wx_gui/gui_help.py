"""
gui_help.py: GUI Help Menu
"""

import webbrowser

import wx

from .. import constants
from . import gui_support


class HelpFrame(wx.Frame):
    """
    Append to main menu through a modal dialog
    """

    def __init__(self, parent: wx.Frame, title: str, global_constants: constants.Constants, screen_location: tuple = None) -> None:
        self.dialog = wx.Dialog(parent, title=title, size=(300, 200))
        self.constants: constants.Constants = global_constants
        self.title: str = title
        self._generate_elements(self.dialog)
        self.dialog.Centre()
        self.dialog.ShowModal()

    def _generate_elements(self, frame: wx.Frame = None) -> None:
        """
        Format:
            - Title: Patcher Resources
            - Text:  Following resources are available:
            - Button: Official Guide
            - Button: ...
            - Button: Return to Main Menu
        """
        frame = self if not frame else frame

        title_label = wx.StaticText(frame, label="Patcher Resources", pos=(-1, 5))
        title_label.SetFont(gui_support.font_factory(19, wx.FONTWEIGHT_BOLD))
        title_label.Centre(wx.HORIZONTAL)

        text_label = wx.StaticText(frame, label="Following resources are available:", pos=(-1, 30))
        text_label.SetFont(gui_support.font_factory(13, wx.FONTWEIGHT_NORMAL))
        text_label.Centre(wx.HORIZONTAL)

        buttons = {
            "Dortania Install Guide":    "https://dortania.github.io/OpenCore-Install-Guide/",
            "Post-Install Guide":        "https://dortania.github.io/OpenCore-Post-Install/",
            "Troubleshooting":           "https://dortania.github.io/OpenCore-Install-Guide/troubleshooting/troubleshooting.html",
            "USB Mapping (USBToolBox)":  "https://github.com/USBToolBox/tool",
            "AMD_Vanilla Patches":       "https://github.com/AMD-OSX/AMD_Vanilla",
            "Project Repository":        self.constants.repo_url,
        }

        buttons["Compatibility Report"] = self.on_compatibility
        buttons["Check a macOS Install"] = self.on_inspect_macos
        buttons["Check an Existing EFI"] = self.on_check_efi

        for i, (button, target) in enumerate(buttons.items()):
            help_button = wx.Button(frame, label=button, pos=(-1, text_label.GetPosition()[1] + text_label.GetSize()[1] + (i * 30) + 5), size=(200, 30))
            if callable(target):
                help_button.Bind(wx.EVT_BUTTON, target)
            else:
                help_button.Bind(wx.EVT_BUTTON, lambda event, u=target: webbrowser.open(u))
            help_button.Centre(wx.HORIZONTAL)

        return_button = wx.Button(frame, label="Return to Main Menu", pos=(-1, help_button.GetPosition()[1] + help_button.GetSize()[1]), size=(150, 30))
        return_button.Bind(wx.EVT_BUTTON, lambda event: frame.EndModal(wx.ID_OK))
        return_button.Centre(wx.HORIZONTAL)

        frame.SetSize((-1, return_button.GetPosition()[1] + return_button.GetSize()[1] + 40))

    def _show_text(self, title: str, text: str) -> None:
        dialog = wx.Dialog(self.dialog, title=title, size=(640, 420), style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        sizer = wx.BoxSizer(wx.VERTICAL)
        box = wx.TextCtrl(dialog, value=text, style=wx.TE_READONLY | wx.TE_MULTILINE | wx.TE_DONTWRAP)
        box.SetFont(wx.Font(11, wx.FONTFAMILY_TELETYPE, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
        sizer.Add(box, 1, wx.EXPAND | wx.ALL, 10)
        close = wx.Button(dialog, wx.ID_CLOSE, label="Close")
        close.Bind(wx.EVT_BUTTON, lambda event: dialog.EndModal(wx.ID_CLOSE))
        sizer.Add(close, 0, wx.ALIGN_CENTRE | wx.BOTTOM, 10)
        dialog.SetSizer(sizer)
        dialog.ShowModal()
        dialog.Destroy()

    def on_compatibility(self, event: wx.Event = None) -> None:
        from .. import compatibility
        self._show_text("Compatibility Report", compatibility.report(self.constants.computer, self.constants))

    def on_inspect_macos(self, event: wx.Event = None) -> None:
        """
        Point at a mounted or copied macOS system volume (on a Mac: "/")
        """
        from pathlib import Path
        from .. import macos_inspector
        default = "/" if self.constants.host_os == "macOS" else ""
        with wx.DirDialog(self.dialog, "Choose the root of a macOS system volume", defaultPath=default, style=wx.DD_DIR_MUST_EXIST) as dd:
            if dd.ShowModal() != wx.ID_OK:
                return
            root = Path(dd.GetPath())
        if not (root / "System/Library/CoreServices/SystemVersion.plist").exists():
            wx.MessageBox("That folder isn't the root of a macOS system volume.", "Not macOS", wx.OK | wx.ICON_ERROR)
            return
        wx.BeginBusyCursor()
        try:
            text = macos_inspector.inspect(root).report()
        finally:
            wx.EndBusyCursor()
        self._show_text("macOS Install Check", text)

    def on_check_efi(self, event: wx.Event = None) -> None:
        """
        Pick any EFI folder (or the drive/folder containing it)
        """
        from .. import efi_checker
        with wx.DirDialog(self.dialog, "Choose an EFI folder", style=wx.DD_DIR_MUST_EXIST) as dd:
            if dd.ShowModal() != wx.ID_OK:
                return
            path = dd.GetPath()
        wx.BeginBusyCursor()
        try:
            text = efi_checker.check(path, self.constants).text()
        except Exception as e:
            text = f"Couldn't check that EFI: {e}"
        finally:
            wx.EndBusyCursor()
        self._show_text("EFI Check", text)

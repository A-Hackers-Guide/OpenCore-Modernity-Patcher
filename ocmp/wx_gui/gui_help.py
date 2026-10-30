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

        for i, (button, url) in enumerate(buttons.items()):
            help_button = wx.Button(frame, label=button, pos=(-1, text_label.GetPosition()[1] + text_label.GetSize()[1] + (i * 30) + 5), size=(200, 30))
            help_button.Bind(wx.EVT_BUTTON, lambda event, u=url: webbrowser.open(u))
            help_button.Centre(wx.HORIZONTAL)

        return_button = wx.Button(frame, label="Return to Main Menu", pos=(-1, help_button.GetPosition()[1] + help_button.GetSize()[1]), size=(150, 30))
        return_button.Bind(wx.EVT_BUTTON, lambda event: frame.EndModal(wx.ID_OK))
        return_button.Centre(wx.HORIZONTAL)

        frame.SetSize((-1, return_button.GetPosition()[1] + return_button.GetSize()[1] + 40))

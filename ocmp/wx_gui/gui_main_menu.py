"""
gui_main_menu.py: Generate GUI for main menu

Layout reproduces OpenCore Legacy Patcher's main menu: 600px wide, title,
version and model lines, then two columns of icon + button + description,
with Settings/Credits centred in the second column.
"""

import wx

from .. import constants, hardware
from ..datasets import os_data
from . import (
    gui_build,
    gui_help,
    gui_settings,
    gui_support,
    gui_icons,
    gui_macos_installer_download,
)


class MainFrame(wx.Frame):

    def __init__(self, parent: wx.Frame, title: str, global_constants: constants.Constants, screen_location: tuple = None):
        super(MainFrame, self).__init__(parent, title=title, size=(600, 400), style=gui_support.frame_style())
        gui_support.GenerateMenubar(self, global_constants).generate()

        self.constants: constants.Constants = global_constants
        self.title: str = title

        self.model_label: wx.StaticText = None
        self.build_button: wx.Button = None

        if self.constants.computer is None:
            self.constants.computer = hardware.detect()

        self._generate_elements()

        self.Centre()
        if screen_location:
            self.SetPosition(screen_location)

    def _generate_elements(self) -> None:
        """
        Format:
            - Title label:   OpenCore Modernity Patcher
            - Version label: Version: x.y.z
            - Model label:   Model: {PC name}
            - Buttons:
                - Build and Install OpenCore
                - Create macOS Installer
                - Settings / Credits
                - Detect or Load Hardware
                - Support
            - Copyright label
        """
        title_label = wx.StaticText(self, label=constants.APP_NAME, pos=(-1, 128))
        title_label.SetFont(gui_support.font_factory(25, wx.FONTWEIGHT_BOLD))
        title_label.Centre(wx.HORIZONTAL)

        # Banner icon sits above the title like OCLP's
        banner = wx.StaticBitmap(self, bitmap=gui_icons.bitmap("app", 100), pos=(-1, 20), size=(100, 100))
        banner.Centre(wx.HORIZONTAL)

        version_label = wx.StaticText(self, label=f"Version {self.constants.patcher_version}{'' if self.constants.channel == 'Stable' else f' ({self.constants.channel})'}", pos=(-1, title_label.GetPosition()[1] + 32))
        version_label.SetFont(gui_support.font_factory(13, wx.FONTWEIGHT_NORMAL))
        version_label.Centre(wx.HORIZONTAL)

        model_label = wx.StaticText(self, label=self._model_text(), pos=(-1, version_label.GetPosition()[1] + 30))
        model_label.SetFont(gui_support.font_factory(13, wx.FONTWEIGHT_NORMAL))
        model_label.Centre(wx.HORIZONTAL)
        self.model_label = model_label

        menu_buttons = {
            "Build and Install OpenCore": {
                "function": self.on_build_and_install,
                "description": [
                    "Prepares provided drive to be able",
                    "to boot macOS on this PC.",
                    "Use on installers or internal drives.",
                ],
                "icon": "build",
            },
            "Create macOS Installer": {
                "function": self.on_create_macos_installer,
                "description": [
                    "Download and flash a macOS",
                    "Installer for your system.",
                ],
                "icon": "installer",
            },
            "⚙️ Settings": {
                "function": self.on_settings,
                "description": [
                ],
            },
            "Detect Hardware": {
                "function": self.on_detect_hardware,
                "description": [
                    "Re-scan this PC, or load and save",
                    "a hardware profile to build",
                    "for a different machine.",
                ],
                "icon": "hardware",
            },
            "Support": {
                "function": self.on_help,
                "description": [
                    "Resources for OpenCore Modernity",
                    "Patcher.",
                ],
                "icon": "support",
            },
        }

        button_x = 30
        button_y = model_label.GetPosition()[1] + 30
        rollover = len(menu_buttons) / 2
        if rollover % 1 != 0:
            rollover = int(rollover) + 1
        index = 0
        max_height = 0
        for button_name, button_function in menu_buttons.items():
            if "icon" in button_function:
                icon = wx.StaticBitmap(self, bitmap=gui_icons.bitmap(button_function["icon"], 64), pos=(button_x - 10, button_y), size=(64, 64))
                if button_name == "Detect Hardware":
                    icon.SetPosition((-1, button_y + 7))
                if button_name in ("Create macOS Installer", "Support"):
                    icon.SetPosition((button_x - 5, button_y + 3))
            if button_name == "⚙️ Settings":
                button_y += 5

            button = wx.Button(self, label=button_name, pos=(button_x + 70, button_y), size=(180, 30))
            button.SetFont(gui_support.font_factory(13, wx.FONTWEIGHT_NORMAL))
            button.Bind(wx.EVT_BUTTON, lambda event, function=button_function["function"]: function(event))
            button_y += 30

            description_label = wx.StaticText(self, label='\n'.join(button_function["description"]), pos=(button_x + 75, button.GetPosition()[1] + button.GetSize()[1] + 3))
            description_label.SetFont(gui_support.font_factory(10, wx.FONTWEIGHT_NORMAL))

            for i, line in enumerate(button_function["description"]):
                if line == "":
                    continue
                if i == 0:
                    button_y += 11
                else:
                    button_y += 13

            button_y += 25

            if button_name == "Build and Install OpenCore":
                self.build_button = button
            elif button_name == "⚙️ Settings":
                button.SetSize((100, -1))
                credits_button = wx.Button(self, label="Credits", pos=(-1, button.GetPosition()[1]), size=(100, 30))
                credits_button.SetFont(gui_support.font_factory(13, wx.FONTWEIGHT_NORMAL))
                credits_button.Bind(wx.EVT_BUTTON, self.on_credits)
                button_x_position = (self.GetClientSize()[0] - button.GetSize()[0] - credits_button.GetSize()[0] - 12) // 2
                button.SetPosition((button_x_position, button.GetPosition()[1]))
                credits_button.SetPosition((button_x_position + button.GetSize()[0] + 12, button.GetPosition()[1]))
                description_label.Centre(wx.HORIZONTAL)

            index += 1
            if index == rollover:
                max_height = button_y
                button_x = 320
                button_y = model_label.GetPosition()[1] + 30

        copy_label = wx.StaticText(self, label=self.constants.copyright_date, pos=(-1, max_height - 15))
        copy_label.SetFont(gui_support.font_factory(10, wx.FONTWEIGHT_NORMAL))
        copy_label.Centre(wx.HORIZONTAL)

        self.SetSize((-1, copy_label.GetPosition()[1] + 50 + (30 if wx.Platform != "__WXMAC__" else 0)))

    def _model_text(self) -> str:
        pc = self.constants.computer
        target = os_data.name(self.constants.target_os)
        return f"Model: {pc.short_model()}  •  Target: {target}"

    def _reopen(self) -> None:
        frame = MainFrame(None, title=self.title, global_constants=self.constants, screen_location=self.GetPosition())
        frame.Show()
        self.Destroy()

    # ---- buttons ----

    def on_build_and_install(self, event: wx.Event = None):
        self.Hide()
        gui_build.BuildFrame(parent=None, title=self.title, global_constants=self.constants, screen_location=self.GetPosition())
        self.Destroy()

    def on_create_macos_installer(self, event: wx.Event = None):
        gui_macos_installer_download.macOSInstallerDownloadFrame(parent=self, title=self.title, global_constants=self.constants,
                                                                 screen_location=self.GetPosition())

    def on_settings(self, event: wx.Event = None):
        gui_settings.SettingsFrame(parent=self, title=self.title, global_constants=self.constants, screen_location=self.GetPosition())
        self._reopen()

    def on_detect_hardware(self, event: wx.Event = None):
        dialog = wx.MessageDialog(self, self._hardware_summary(), "Detected Hardware", style=wx.YES_NO | wx.CANCEL | wx.ICON_INFORMATION)
        dialog.SetYesNoCancelLabels("Re-scan this PC", "Load profile...", "Save profile...")
        result = dialog.ShowModal()
        if result == wx.ID_YES:
            self.constants.computer = hardware.detect()
            self.constants.custom_profile_path = None
            self._reopen()
        elif result == wx.ID_NO:
            with wx.FileDialog(self, "Load hardware profile", wildcard="Hardware profile (*.json)|*.json",
                               style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST) as fd:
                if fd.ShowModal() == wx.ID_OK:
                    try:
                        self.constants.computer = hardware.HardwareProfile.load(fd.GetPath())
                        self.constants.custom_profile_path = fd.GetPath()
                    except Exception as e:
                        wx.MessageBox(f"Couldn't load that profile:\n{e}", "Error", wx.OK | wx.ICON_ERROR)
                    self._reopen()
        elif result == wx.ID_CANCEL:
            with wx.FileDialog(self, "Save hardware profile", wildcard="Hardware profile (*.json)|*.json",
                               defaultFile="hardware-profile.json", style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT) as fd:
                if fd.ShowModal() == wx.ID_OK:
                    self.constants.computer.save(fd.GetPath())

    def _hardware_summary(self) -> str:
        pc = self.constants.computer
        lines = [f"Source: {pc.source}", f"CPU: {pc.summary()}",
                 f"Cores/Threads: {pc.cpu_cores}/{pc.cpu_threads}"]
        if pc.board:
            lines.append(f"Board: {pc.board}")
        lines += [f"GPU: {g.name or g.pci_id} [{g.arch}]" for g in pc.gpus]
        lines += [f"{n.kind.title()}: {n.name or n.pci_id}" for n in pc.nics]
        return "\n".join(lines)

    def on_credits(self, event: wx.Event = None):
        from . import gui_about
        gui_about.CreditsDialog(self)

    def on_help(self, event: wx.Event = None):
        gui_help.HelpFrame(parent=self, title=self.title, global_constants=self.constants, screen_location=self.GetPosition())

"""
gui_about.py: About and Credits windows
"""

import wx

from .. import constants
from . import gui_support, gui_icons


CREDITS = [
    ("OpenCorePkg, Lilu, VirtualSMC, WhateverGreen, AppleALC,\nRestrictEvents, NVMeFix, IntelMausi, VoodooPS2, BrcmPatchRAM", "Acidanthera"),
    ("OpenCore Legacy Patcher (interface and app structure)", "Dortania: Dhinak G, Mykola Grymalyuk and contributors"),
    ("OpenCore Install Guide and prebuilt SSDTs", "Dortania"),
    ("AMD_Vanilla kernel patches", "AMD-OSX: algrey, Shaneee, Goldfish64, CaseySJ and others"),
    ("KVM-Opencore (approach for the KVM profile)", "Leoyzen"),
    ("SMCAMDProcessor / AMDRyzenCPUPowerManagement", "trulyspinach"),
    ("NootedRed", "ChefKissInc"),
    ("RealtekRTL8111, LucyRTL8125, AtherosE2200", "Mieze"),
    ("itlwm, IntelBluetoothFirmware", "OpenIntelWireless (zxystd and contributors)"),
    ("CpuTopologyRebuild", "b00t0x"),
    ("USBToolBox", "dhinakg and contributors"),
]


class AboutFrame(wx.Frame):

    def __init__(self, global_constants: constants.Constants) -> None:
        if wx.FindWindowByName("About"):
            return
        self.constants = global_constants
        super(AboutFrame, self).__init__(None, title="About", size=(350, 350), style=gui_support.frame_style(), name="About")
        self.SetPosition(wx.DefaultPosition)
        self._generate_elements(self)
        self.Centre()
        self.Show()

    def _generate_elements(self, frame: wx.Frame) -> None:
        icon = wx.StaticBitmap(frame, bitmap=gui_icons.bitmap("app", 80), pos=(-1, 10), size=(80, 80))
        icon.Centre(wx.HORIZONTAL)

        title = wx.StaticText(frame, label=constants.APP_NAME, pos=(-1, 95))
        title.SetFont(gui_support.font_factory(19, wx.FONTWEIGHT_BOLD))
        title.Centre(wx.HORIZONTAL)

        version = wx.StaticText(frame, label=f"Version: {self.constants.patcher_version}", pos=(-1, title.GetPosition()[1] + title.GetSize()[1] + 5))
        version.SetFont(gui_support.font_factory(11, wx.FONTWEIGHT_NORMAL))
        version.Centre(wx.HORIZONTAL)

        lines = [
            "Builds OpenCore EFIs for PCs and KVM",
            "virtual machines, from Windows and Linux.",
            "",
            "This product includes software developed by",
            "Dortania and OpenCore Legacy Patcher contributors.",
            "",
            self.constants.copyright_date,
        ]
        spacer = 5
        for line in lines:
            desc = wx.StaticText(frame, label=line, pos=(-1, version.GetPosition()[1] + version.GetSize()[1] + 5 + spacer))
            desc.SetFont(gui_support.font_factory(11, wx.FONTWEIGHT_NORMAL))
            desc.Centre(wx.HORIZONTAL)
            spacer += 16
        frame.SetSize((-1, version.GetPosition()[1] + spacer + 80))


class CreditsDialog:

    def __init__(self, parent: wx.Window) -> None:
        dialog = wx.Dialog(parent, title="Credits", size=(700, 600), style=wx.DEFAULT_DIALOG_STYLE)
        sizer = wx.BoxSizer(wx.VERTICAL)
        title = wx.StaticText(dialog, label="Credits")
        title.SetFont(gui_support.font_factory(19, wx.FONTWEIGHT_BOLD))
        sizer.Add(title, 0, wx.ALIGN_CENTRE | wx.TOP, 10)
        scroll = wx.ScrolledWindow(dialog)
        scroll.SetScrollRate(0, 10)
        inner = wx.BoxSizer(wx.VERTICAL)
        for work, who in CREDITS:
            label = wx.StaticText(scroll, label=work)
            label.SetFont(gui_support.font_factory(13, wx.FONTWEIGHT_BOLD))
            by = wx.StaticText(scroll, label=who)
            by.SetFont(gui_support.font_factory(11, wx.FONTWEIGHT_NORMAL))
            inner.Add(label, 0, wx.LEFT | wx.TOP, 12)
            inner.Add(by, 0, wx.LEFT, 24)
        scroll.SetSizer(inner)
        sizer.Add(scroll, 1, wx.EXPAND | wx.ALL, 10)
        close = wx.Button(dialog, wx.ID_CLOSE, label="Close")
        close.Bind(wx.EVT_BUTTON, lambda event: dialog.EndModal(wx.ID_CLOSE))
        sizer.Add(close, 0, wx.ALIGN_CENTRE | wx.BOTTOM, 10)
        dialog.SetSizer(sizer)
        dialog.Centre()
        dialog.ShowModal()
        dialog.Destroy()

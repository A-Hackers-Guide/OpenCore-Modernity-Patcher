"""
gui_settings.py: Settings window

Structure follows OCLP's gui_settings.py: a 600x685 modal, a "Target"
choice at the top, a notebook of categories built from a settings
dictionary (checkbox / spinctrl / choice / button, each with a
description), and a Return button. Changes are saved on return.
"""

import wx

from .. import constants, settings
from ..datasets import os_data, smbios_data
from . import gui_support


class SettingsFrame(wx.Frame):

    def __init__(self, parent: wx.Frame, title: str, global_constants: constants.Constants, screen_location: tuple = None):
        self.constants: constants.Constants = global_constants
        self.title: str = title
        self.parent: wx.Frame = parent

        self.frame_modal = wx.Dialog(parent, title=title, size=(600, 685))
        self._generate_elements(self.frame_modal)
        self.frame_modal.Centre()
        self.frame_modal.ShowModal()
        self.frame_modal.Destroy()

    def _generate_elements(self, frame: wx.Frame = None) -> None:
        """
        Format:
            - Target macOS (choice) + description
            - Notebook: one page per category
            - Return button
        """
        sizer = wx.BoxSizer(wx.VERTICAL)

        target_label = wx.StaticText(frame, label="Target macOS")
        target_label.SetFont(gui_support.font_factory(13, wx.FONTWEIGHT_BOLD))
        sizer.Add(target_label, 0, wx.ALIGN_CENTRE | wx.TOP, 10)

        self.versions = sorted(os_data.MARKETING_NAMES.keys(), reverse=True)
        target_choice = wx.Choice(frame, choices=[os_data.label(v) + ("" if os_data.pc_supported(v) else " - Apple silicon only")
                                                  for v in self.versions], size=(300, -1))
        target_choice.SetSelection(self.versions.index(os_data.os_data(self.constants.target_os)))
        target_choice.Bind(wx.EVT_CHOICE, lambda event: self.on_target(event, target_choice))
        sizer.Add(target_choice, 0, wx.ALIGN_CENTRE | wx.TOP, 4)

        target_desc = wx.StaticText(frame, label="macOS version the EFI is built for. Kexts, SMBIOS and quirks adjust to it.")
        target_desc.SetFont(gui_support.font_factory(11, wx.FONTWEIGHT_NORMAL))
        sizer.Add(target_desc, 0, wx.ALIGN_CENTRE | wx.TOP, 2)

        notebook = wx.Notebook(frame)
        for category, entries in self._settings().items():
            panel = wx.ScrolledWindow(notebook)
            panel.SetScrollRate(0, 10)
            self._populate(panel, entries)
            notebook.AddPage(panel, category)
        sizer.Add(notebook, 1, wx.EXPAND | wx.ALL, 10)

        return_button = wx.Button(frame, label="Return", size=(100, 30))
        return_button.Bind(wx.EVT_BUTTON, self.on_return)
        sizer.Add(return_button, 0, wx.ALIGN_CENTRE | wx.BOTTOM, 15)

        frame.SetSizer(sizer)

    def _populate(self, panel: wx.Window, entries: dict) -> None:
        sizer = wx.BoxSizer(wx.VERTICAL)
        for name, setting in entries.items():
            kind = setting["type"]
            if kind == "title":
                title = wx.StaticText(panel, label=name)
                title.SetFont(gui_support.font_factory(17, wx.FONTWEIGHT_BOLD))
                sizer.Add(title, 0, wx.LEFT | wx.TOP, 10)
                continue
            if kind == "checkbox":
                control = wx.CheckBox(panel, label=name)
                control.SetValue(bool(getattr(self.constants, setting["variable"])))
                control.SetFont(gui_support.font_factory(13, wx.FONTWEIGHT_BOLD))
                control.Bind(wx.EVT_CHECKBOX, lambda event, s=setting: self.on_checkbox(event, s))
                sizer.Add(control, 0, wx.LEFT | wx.TOP, 12)
            elif kind == "spinctrl":
                row = wx.BoxSizer(wx.HORIZONTAL)
                control = wx.SpinCtrl(panel, value=str(getattr(self.constants, setting["variable"])), min=setting["min"], max=setting["max"], size=(70, -1))
                control.Bind(wx.EVT_SPINCTRL, lambda event, s=setting: setattr(self.constants, s["variable"], event.GetPosition()))
                label = wx.StaticText(panel, label=name)
                label.SetFont(gui_support.font_factory(13, wx.FONTWEIGHT_BOLD))
                row.Add(control, 0, wx.RIGHT, 8)
                row.Add(label, 0, wx.ALIGN_CENTRE_VERTICAL)
                sizer.Add(row, 0, wx.LEFT | wx.TOP, 12)
            elif kind == "choice":
                row = wx.BoxSizer(wx.HORIZONTAL)
                label = wx.StaticText(panel, label=name)
                label.SetFont(gui_support.font_factory(13, wx.FONTWEIGHT_BOLD))
                current = getattr(self.constants, setting["variable"]) or setting["choices"][0]
                control = wx.Choice(panel, choices=setting["choices"], size=(200, -1))
                control.SetStringSelection(current if current in setting["choices"] else setting["choices"][0])
                control.Bind(wx.EVT_CHOICE, lambda event, s=setting: self.on_choice(event, s))
                row.Add(label, 0, wx.ALIGN_CENTRE_VERTICAL | wx.RIGHT, 8)
                row.Add(control, 0)
                sizer.Add(row, 0, wx.LEFT | wx.TOP, 12)
            elif kind == "text":
                row = wx.BoxSizer(wx.HORIZONTAL)
                label = wx.StaticText(panel, label=name)
                label.SetFont(gui_support.font_factory(13, wx.FONTWEIGHT_BOLD))
                control = wx.TextCtrl(panel, value=getattr(self.constants, setting["variable"]), size=(260, -1))
                control.Bind(wx.EVT_TEXT, lambda event, s=setting: setattr(self.constants, s["variable"], event.GetString().strip()))
                row.Add(label, 0, wx.ALIGN_CENTRE_VERTICAL | wx.RIGHT, 8)
                row.Add(control, 0)
                sizer.Add(row, 0, wx.LEFT | wx.TOP, 12)
            elif kind == "button":
                control = wx.Button(panel, label=name, size=(200, -1))
                control.Bind(wx.EVT_BUTTON, setting["function"])
                sizer.Add(control, 0, wx.LEFT | wx.TOP, 12)
            description = wx.StaticText(panel, label="\n".join(setting.get("description", [])))
            description.SetFont(gui_support.font_factory(11, wx.FONTWEIGHT_NORMAL))
            sizer.Add(description, 0, wx.LEFT, 34)
        panel.SetSizer(sizer)

    def _settings(self) -> dict:
        smbios_choices = ["Automatic"] + list(smbios_data.SMBIOS.keys())
        return {
            "Build": {
                "General": {"type": "title"},
                "Verbose": {"type": "checkbox", "variable": "verbose_debug",
                            "description": ["Boot macOS in verbose mode (-v).", "Recommended until your setup boots reliably."]},
                "Kernel Debugging": {"type": "checkbox", "variable": "kext_debug",
                                     "description": ["Add keepsyms=1 debug=0x100 so panics stay on screen."]},
                "OpenCore DEBUG Build": {"type": "checkbox", "variable": "opencore_debug",
                                         "description": ["Use the DEBUG OpenCore release and write logs", "to the EFI partition."]},
                "Show OpenCore Picker": {"type": "checkbox", "variable": "showpicker",
                                         "description": ["Show the boot picker on every boot.", "If off, hold Esc/Option at startup to see it."]},
                "Picker Timeout": {"type": "spinctrl", "variable": "oc_timeout", "min": 0, "max": 60,
                                   "description": ["Seconds before the default entry boots (0 = wait)."]},
                "GUI Boot Picker (OpenCanopy)": {"type": "checkbox", "variable": "opencanopy",
                                                 "description": ["Graphical picker instead of the text menu.", "Needs OcBinaryData resources added by hand."]},
            },
            "Hardware": {
                "Hardware": {"type": "title"},
                "CFG Lock disabled in BIOS": {"type": "checkbox", "variable": "cfg_lock_unlocked",
                                              "description": ["Tick only if you turned off CFG Lock in your BIOS.", "Otherwise AppleXcpmCfgLock stays on (Intel)."]},
                "Resizable BAR": {"type": "checkbox", "variable": "resizable_bar",
                                  "description": ["Let macOS use Resizable BAR (ResizeAppleGpuBars=0).", "Leave off unless ReBAR is on in BIOS."]},
                "Disable discrete GPU": {"type": "checkbox", "variable": "disable_dgpu",
                                         "description": ["Add -wegnoegpu (e.g. laptops with NVIDIA Optimus)."]},
                "Audio Layout ID": {"type": "spinctrl", "variable": "alc_layout_id", "min": 1, "max": 100,
                                    "description": ["AppleALC layout for your codec (alcid=).", "See AppleALC's supported codecs list."]},
                "Wi-Fi drivers": {"type": "checkbox", "variable": "include_wifi",
                                  "description": ["Add itlwm for Intel Wi-Fi cards."]},
                "Bluetooth drivers": {"type": "checkbox", "variable": "include_bluetooth",
                                      "description": ["Add IntelBluetoothFirmware/BlueToolFixup."]},
                "USBToolBox": {"type": "checkbox", "variable": "usb_toolbox",
                               "description": ["Include USBToolBox.kext for USB port mapping."]},
            },
            "Security": {
                "Security": {"type": "title"},
                "System Integrity Protection": {"type": "checkbox", "variable": "sip_status",
                                                "description": ["Keep SIP enabled (recommended).", "Off sets csr-active-config to 0x803."]},
                "Apple Secure Boot": {"type": "checkbox", "variable": "secure_boot_model",
                                      "description": ["SecureBootModel=Default. Turn off if macOS", "won't boot or updates fail."]},
                "OpenCore Vault": {"type": "checkbox", "variable": "vault",
                                   "description": ["Require a signed vault (advanced; needs", "CreateVault run on the built EFI)."]},
            },
            "SMBIOS": {
                "SMBIOS": {"type": "title"},
                "Model": {"type": "choice", "variable": "custom_smbios", "choices": smbios_choices,
                          "description": ["Mac model to spoof. Automatic picks the best", "match for your CPU, GPU and target macOS."]},
                "Serial Number": {"type": "text", "variable": "custom_serial",
                                  "description": ["Leave empty to generate a new one each build."]},
                "Board Serial (MLB)": {"type": "text", "variable": "custom_board_serial",
                                       "description": ["Must be set together with the serial number."]},
                "System UUID": {"type": "text", "variable": "custom_uuid", "description": ["Leave empty to generate."]},
                "ROM (MAC address)": {"type": "text", "variable": "custom_rom",
                                      "description": ["12 hex digits. Empty = your Ethernet MAC or a random one."]},
                "Generate new serial": {"type": "button", "function": self.on_new_serial,
                                        "description": ["Serials are saved and reused on every rebuild.", "Clear them to get new ones on the next build."]},
            },
            "Advanced": {
                "Advanced": {"type": "title"},
                "Extra boot-args": {"type": "text", "variable": "extra_boot_args",
                                    "description": ["Added to the generated boot-args, space separated."]},
                "Open data folder": {"type": "button", "function": lambda event: gui_support.reveal(self.constants.data_path),
                                     "description": ["Cache, logs, settings and the last build."]},
                "Clear download cache": {"type": "button", "function": self.on_clear_cache,
                                         "description": ["Re-download OpenCore and kexts on the next build."]},
            },
        }

    def on_target(self, event: wx.Event, choice: wx.Choice) -> None:
        kernel = int(self.versions[event.GetSelection()])
        if not os_data.pc_supported(kernel):
            wx.MessageBox(os_data.GOLDEN_GATE_DIAGNOSIS, "Not available on PCs", wx.OK | wx.ICON_INFORMATION)
            choice.SetSelection(self.versions.index(os_data.os_data(self.constants.target_os)))
            return
        self.constants.target_os = kernel

    def on_new_serial(self, event: wx.Event) -> None:
        import shutil
        shutil.rmtree(self.constants.data_path / "smbios", ignore_errors=True)
        wx.MessageBox("Saved serial numbers cleared. The next build generates new ones.\n\n"
                      "Only do this before installing macOS, or iMessage/FaceTime will see a new Mac.",
                      "Serials cleared", wx.OK | wx.ICON_INFORMATION)

    def on_checkbox(self, event: wx.Event, setting: dict) -> None:
        setattr(self.constants, setting["variable"], event.IsChecked())

    def on_choice(self, event: wx.Event, setting: dict) -> None:
        value = event.GetString()
        setattr(self.constants, setting["variable"], "" if value == "Automatic" else value)

    def on_clear_cache(self, event: wx.Event) -> None:
        import shutil
        shutil.rmtree(self.constants.cache_path, ignore_errors=True)
        self.constants.ensure_paths()
        wx.MessageBox("Download cache cleared.", "Done", wx.OK | wx.ICON_INFORMATION)

    def on_return(self, event: wx.Event) -> None:
        settings.save(self.constants)
        self.frame_modal.EndModal(wx.ID_OK)

"""
gui_install_oc.py: Frame for installing OpenCore to disk

Same three steps as OCLP: fetch disks, pick a disk, pick its EFI
partition, then copy with a live log.
"""

import wx
import logging
import threading
import traceback

from .. import constants, disk_handler
from . import gui_main_menu, gui_support


class InstallOCFrame(wx.Frame):

    def __init__(self, parent: wx.Frame, title: str, global_constants: constants.Constants, screen_location: tuple = None):
        logging.info("Initializing Install OpenCore Frame")
        super(InstallOCFrame, self).__init__(parent, title=title, size=(300, 120), style=gui_support.frame_style())
        gui_support.GenerateMenubar(self, global_constants).generate()

        self.constants: constants.Constants = global_constants
        self.title: str = title
        self.result: bool = False
        self.available_disks: list = None
        self.disk_error: str = ""
        self.stock_output = None

        self._generate_elements()
        if screen_location:
            self.SetPosition(screen_location)
        else:
            self.Centre()
        self.Show()

        if not self._preflight():
            return
        self._display_disks()

    def _generate_elements(self) -> None:
        """
        Display indeterminate progress bar while fetching disks
        """
        title_label = wx.StaticText(self, label="Install OpenCore", pos=(-1, 5))
        title_label.SetFont(gui_support.font_factory(19, wx.FONTWEIGHT_BOLD))
        title_label.Centre(wx.HORIZONTAL)

        text_label = wx.StaticText(self, label="Fetching information on local disks...", pos=(-1, 30))
        text_label.SetFont(gui_support.font_factory(13, wx.FONTWEIGHT_NORMAL))
        text_label.Centre(wx.HORIZONTAL)
        self.text_label = text_label

        progress_bar = wx.Gauge(self, range=100, pos=(-1, text_label.GetPosition()[1] + text_label.GetSize()[1]), size=(150, 30),
                                style=wx.GA_HORIZONTAL | wx.GA_SMOOTH)
        progress_bar.Centre(wx.HORIZONTAL)
        progress_bar.Pulse()
        self.progress_bar = progress_bar

    def _preflight(self) -> bool:
        if self.constants.last_build_path is None or not (self.constants.last_build_path / "OC" / "config.plist").exists():
            wx.MessageBox("Build OpenCore first, then install it.", "Nothing to install", wx.OK | wx.ICON_INFORMATION)
            self.on_return_to_main_menu()
            return False
        if self.constants.host_os == "macOS":
            wx.MessageBox("Installing to disk is supported on Windows and Linux. Copy the EFI folder manually on a Mac.",
                          "Not available on macOS", wx.OK | wx.ICON_INFORMATION)
            gui_support.reveal(self.constants.last_build_path)
            self.on_return_to_main_menu()
            return False
        if not gui_support.RelaunchAsAdmin.is_admin():
            gui_support.RelaunchAsAdmin.explain(self)
            self.on_return_to_main_menu()
            return False
        return True

    def _fetch_disks(self) -> None:
        def _fetch():
            try:
                self.available_disks = disk_handler.handler().list()
            except Exception as e:
                self.disk_error = str(e)
                self.available_disks = []

        thread = threading.Thread(target=_fetch)
        thread.start()
        gui_support.wait_for_thread(thread, self.constants.thread_sleep_interval)

    def _display_disks(self) -> None:
        """
        Display disks that have an EFI partition
        """
        self._fetch_disks()
        disks = [d for d in self.available_disks if d.esps]

        dialog = wx.Dialog(self, title=self.title, size=(380, -1))

        title_label = wx.StaticText(dialog, label="Install OpenCore", pos=(-1, 5))
        title_label.SetFont(gui_support.font_factory(19, wx.FONTWEIGHT_BOLD))
        title_label.Centre(wx.HORIZONTAL)

        text_label = wx.StaticText(dialog, label="Select disk to install OpenCore onto:", pos=(-1, title_label.GetPosition()[1] + title_label.GetSize()[1] + 5))
        text_label.SetFont(gui_support.font_factory(13, wx.FONTWEIGHT_NORMAL))
        text_label.Centre(wx.HORIZONTAL)

        gpt_note = wx.StaticText(dialog, label="Missing disks? Ensure they're formatted as GUID/GPT with an EFI partition", pos=(-1, text_label.GetPosition()[1] + text_label.GetSize()[1] + 5))
        gpt_note.SetFont(gui_support.font_factory(11, wx.FONTWEIGHT_NORMAL))
        gpt_note.Centre(wx.HORIZONTAL)

        disk_label = gpt_note
        if disks:
            labels = [f"{d.identifier} - {d.name} - {gui_support.human_fmt(d.size)}" + (" (this PC's boot disk)" if d.is_system else "") for d in disks]
            longest_label = max(len(label) for label in labels) * 9 + 20
            spacer = 0
            for disk, label in zip(disks, labels):
                disk_button = wx.Button(dialog, label=label, size=(max(longest_label, 300), 30),
                                        pos=(-1, gpt_note.GetPosition()[1] + gpt_note.GetSize()[1] + spacer + 5))
                disk_button.Centre(wx.HORIZONTAL)
                disk_button.Bind(wx.EVT_BUTTON, lambda event, d=disk: self._display_volumes(d))
                if disk.removable:
                    disk_button.SetForegroundColour((25, 113, 255))
                spacer += 25
                disk_label = disk_button
            note = wx.StaticText(dialog, label="Note: Blue represents removable (USB) disks", pos=(-1, disk_label.GetPosition()[1] + disk_label.GetSize()[1] + 5))
            note.SetFont(gui_support.font_factory(11, wx.FONTWEIGHT_NORMAL))
            note.Centre(wx.HORIZONTAL)
            disk_label = note
        else:
            message = "Failed to find any applicable disks" + (f"\n{self.disk_error}" if self.disk_error else "")
            disk_label = wx.StaticText(dialog, label=message, pos=(-1, gpt_note.GetPosition()[1] + gpt_note.GetSize()[1] + 5))
            disk_label.SetFont(gui_support.font_factory(13, wx.FONTWEIGHT_BOLD))
            disk_label.Centre(wx.HORIZONTAL)

        search_button = wx.Button(dialog, label="Search for disks again", size=(150, 30), pos=(-1, disk_label.GetPosition()[1] + disk_label.GetSize()[1] + 5))
        search_button.Centre(wx.HORIZONTAL)
        search_button.Bind(wx.EVT_BUTTON, self.on_reload_frame)

        return_button = wx.Button(dialog, label="Return to Main Menu", size=(150, 30), pos=(-1, search_button.GetPosition()[1] + 30))
        return_button.Centre(wx.HORIZONTAL)
        return_button.Bind(wx.EVT_BUTTON, self.on_return_to_main_menu)

        dialog.SetSize((-1, return_button.GetPosition()[1] + return_button.GetSize()[1] + 40))
        dialog.ShowWindowModal() if wx.Platform == "__WXMAC__" else dialog.Show()
        self.dialog = dialog

    def _display_volumes(self, disk: disk_handler.Disk) -> None:
        """
        Display EFI partitions on the chosen disk
        """
        dialog = wx.Dialog(self.dialog, title=f"Volumes on {disk.name}", size=(300, 300))

        text_label = wx.StaticText(dialog, label=f"Volumes on {disk.name}", pos=(-1, 10))
        text_label.SetFont(gui_support.font_factory(13, wx.FONTWEIGHT_BOLD))
        text_label.Centre(wx.HORIZONTAL)

        disk_button = text_label
        spacer = 0
        for part in disk.esps:
            label = f"{part.identifier} - {part.label or 'EFI'} - {gui_support.human_fmt(part.size)}"
            disk_button = wx.Button(dialog, label=label, size=(260, 30), pos=(-1, text_label.GetPosition()[1] + text_label.GetSize()[1] + spacer + 5))
            disk_button.Centre(wx.HORIZONTAL)
            disk_button.Bind(wx.EVT_BUTTON, lambda event, p=part, d=disk: self._install_oc_process(d, p, dialog))
            spacer += 25

        return_button = wx.Button(dialog, label="Return to Main Menu", size=(150, 30), pos=(-1, disk_button.GetPosition()[1] + disk_button.GetSize()[1] + 5))
        return_button.Centre(wx.HORIZONTAL)
        return_button.Bind(wx.EVT_BUTTON, self.on_return_to_main_menu)

        dialog.SetSize((-1, return_button.GetPosition()[1] + return_button.GetSize()[1] + 40))
        dialog.Show()

    def _install_oc_process(self, disk: disk_handler.Disk, partition: disk_handler.Partition, parent: wx.Dialog) -> None:
        if disk.is_system:
            warn = wx.MessageDialog(parent, "This is the disk this PC boots from. OpenCore will be added next to the existing "
                                    "boot loaders, which are left in place, and the old EFI/OC folder is backed up.\n\nContinue?",
                                    "Install to boot disk?", style=wx.YES_NO | wx.ICON_WARNING)
            if warn.ShowModal() != wx.ID_YES:
                return
        parent.Destroy()
        self.dialog.Destroy()

        dialog = wx.Dialog(self, title=f"Installing OpenCore to {partition.identifier}", size=(370, 200))

        text_label = wx.StaticText(dialog, label=f"Installing OpenCore to {partition.identifier}", pos=(-1, 10))
        text_label.SetFont(gui_support.font_factory(13, wx.FONTWEIGHT_BOLD))
        text_label.Centre(wx.HORIZONTAL)

        text_box = wx.TextCtrl(dialog, value="", pos=(-1, text_label.GetPosition()[1] + text_label.GetSize()[1] + 10), size=(350, 200),
                               style=wx.TE_READONLY | wx.TE_MULTILINE | wx.TE_RICH2)
        text_box.SetFont(gui_support.font_factory(11, wx.FONTWEIGHT_NORMAL))
        text_box.Centre(wx.HORIZONTAL)

        return_button = wx.Button(dialog, label="Return to Main Menu", size=(150, 30), pos=(-1, text_box.GetPosition()[1] + text_box.GetSize()[1] + 10))
        return_button.Centre(wx.HORIZONTAL)
        return_button.Bind(wx.EVT_BUTTON, self.on_return_to_main_menu)
        return_button.Disable()

        dialog.SetSize((-1, return_button.GetPosition()[1] + return_button.GetSize()[1] + 40))
        dialog.Show()

        logger = logging.getLogger()
        handler = gui_support.ThreadHandler(text_box)
        logger.addHandler(handler)

        def _install():
            try:
                disk_handler.install_efi(self.constants.last_build_path, partition)
                self.result = True
            except Exception as e:
                logging.error(f"Failed to install OpenCore: {e}")
                logging.debug(traceback.format_exc())

        thread = threading.Thread(target=_install)
        thread.start()
        gui_support.wait_for_thread(thread, self.constants.thread_sleep_interval)
        logger.removeHandler(handler)
        return_button.Enable()

        if self.result:
            wx.MessageDialog(dialog, "OpenCore has finished installing to disk.\n\nReboot, open your firmware's boot menu "
                             "(often F8, F11 or F12) and choose the drive you installed to.",
                             "Success", style=wx.OK | wx.ICON_INFORMATION).ShowModal()
        else:
            wx.MessageDialog(dialog, "OpenCore failed to install to disk. See the log for details.",
                             "Error", style=wx.OK | wx.ICON_ERROR).ShowModal()

    def on_reload_frame(self, event: wx.Event = None) -> None:
        self.dialog.Destroy()
        self._display_disks()

    def on_return_to_main_menu(self, event: wx.Event = None) -> None:
        frame = gui_main_menu.MainFrame(None, title=self.title, global_constants=self.constants, screen_location=self.GetScreenPosition())
        frame.Show()
        for child in self.GetChildren():
            if isinstance(child, wx.Dialog):
                child.Destroy()
        self.Destroy()

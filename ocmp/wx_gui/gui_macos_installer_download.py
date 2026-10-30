"""
gui_macos_installer_download.py: macOS Installer acquisition and flashing

Mirrors OCLP's "Create macOS Installer" flow (choose download or existing,
pick a version from a list, download with progress, pick a USB disk, flash).
On Windows/Linux the image is Apple's recovery (BaseSystem.dmg); the
installer fetches the full OS from Apple during installation.
"""

import wx
import logging
import threading
import traceback
from pathlib import Path

from .. import constants, disk_handler, macos_installer_handler, network_handler
from ..datasets import os_data
from . import gui_support


class macOSInstallerDownloadFrame(wx.Frame):
    """
    Create a frame for downloading and creating macOS installers
    Uses a Modal Dialog for smoother transition from other frames
    """

    def __init__(self, parent: wx.Frame, title: str, global_constants: constants.Constants, screen_location: tuple = None):
        logging.info("Initializing macOS Installer Download Frame")
        self.constants: constants.Constants = global_constants
        self.title: str = title
        self.parent: wx.Frame = parent
        self.images: list = []
        self.image: macos_installer_handler.RecoveryImage = None
        self.recovery_path: Path = None
        self.macrecovery_dir: Path = None
        self.error: str = ""

        self.frame_modal = wx.Dialog(parent, title=title, size=(330, 200))
        self._generate_elements(self.frame_modal)
        self.frame_modal.ShowModal()

    def _generate_elements(self, frame: wx.Frame = None) -> None:
        """
        Format:
            - Title:  Create macOS Installer
            - Button: Download macOS Installer
            - Button: Use existing macOS Recovery
            - Button: Return to Main Menu
        """
        frame = self if not frame else frame

        title_label = wx.StaticText(frame, label="Create macOS Installer", pos=(-1, 5))
        title_label.SetFont(gui_support.font_factory(19, wx.FONTWEIGHT_BOLD))
        title_label.Centre(wx.HORIZONTAL)

        download_button = wx.Button(frame, label="Download macOS Installer", pos=(-1, title_label.GetPosition()[1] + title_label.GetSize()[1] + 5), size=(200, 30))
        download_button.Bind(wx.EVT_BUTTON, self.on_download)
        download_button.Centre(wx.HORIZONTAL)

        existing_button = wx.Button(frame, label="Use existing macOS Recovery", pos=(-1, download_button.GetPosition()[1] + download_button.GetSize()[1] - 5), size=(200, 30))
        existing_button.Bind(wx.EVT_BUTTON, self.on_existing)
        existing_button.Centre(wx.HORIZONTAL)

        return_button = wx.Button(frame, label="Return to Main Menu", pos=(-1, existing_button.GetPosition()[1] + existing_button.GetSize()[1] + 5), size=(150, 30))
        return_button.Bind(wx.EVT_BUTTON, self.on_return_to_main_menu)
        return_button.Centre(wx.HORIZONTAL)

        frame.SetSize((-1, return_button.GetPosition()[1] + return_button.GetSize()[1] + 40))

    # ---- catalog ----

    def _progress_dialog(self, title: str, subtitle: str = "") -> tuple:
        dialog = wx.Dialog(self.parent, title=self.title, size=(300, 200))
        title_label = wx.StaticText(dialog, label=title, pos=(-1, 5))
        title_label.SetFont(gui_support.font_factory(19, wx.FONTWEIGHT_BOLD))
        title_label.Centre(wx.HORIZONTAL)
        y = title_label.GetPosition()[1] + title_label.GetSize()[1] + 5
        sub = wx.StaticText(dialog, label=subtitle or " ", pos=(-1, y))
        sub.SetFont(gui_support.font_factory(13, wx.FONTWEIGHT_NORMAL))
        sub.Centre(wx.HORIZONTAL)
        gauge = wx.Gauge(dialog, range=100, pos=(-1, sub.GetPosition()[1] + sub.GetSize()[1] + 5), size=(250, 30))
        gauge.Centre(wx.HORIZONTAL)
        gauge.Pulse()
        dialog.SetSize((-1, gauge.GetPosition()[1] + gauge.GetSize()[1] + 40))
        dialog.Centre()
        dialog.Show()
        return dialog, sub, gauge

    def _fetch_catalog(self) -> bool:
        dialog, _, _ = self._progress_dialog("Finding Available Software")

        def _fetch():
            try:
                net = network_handler.NetworkHandler(self.constants)
                ocpkg = net.extract(net.release_asset("acidanthera/OpenCorePkg", lambda n: n.endswith("-RELEASE.zip")))
                self.macrecovery_dir = ocpkg / "Utilities" / "macrecovery"
                self.images = macos_installer_handler.available_images(self.macrecovery_dir)
            except Exception as e:
                self.error = str(e)

        thread = threading.Thread(target=_fetch)
        thread.start()
        gui_support.wait_for_thread(thread, self.constants.thread_sleep_interval)
        dialog.Destroy()
        if not self.images:
            wx.MessageBox(f"Couldn't get the list of macOS versions:\n{self.error}", "Error", wx.OK | wx.ICON_ERROR)
            return False
        return True

    def _display_available_installers(self) -> None:
        dialog = wx.Dialog(self.parent, title="Select macOS Installer", size=(550, 500))
        title_label = wx.StaticText(dialog, label="Select macOS Installer", pos=(-1, 5))
        title_label.SetFont(gui_support.font_factory(19, wx.FONTWEIGHT_BOLD))
        title_label.Centre(wx.HORIZONTAL)

        listctrl = wx.ListCtrl(dialog, style=wx.LC_REPORT | wx.LC_SINGLE_SEL | wx.BORDER_SUNKEN, pos=(-1, 40), size=(520, 330))
        listctrl.InsertColumn(0, "Title", width=190)
        listctrl.InsertColumn(1, "Version", width=80)
        listctrl.InsertColumn(2, "Board ID", width=170)
        listctrl.InsertColumn(3, "Fits build", width=80)
        listctrl.Centre(wx.HORIZONTAL)
        selected_index = 0
        for i, image in enumerate(self.images):
            listctrl.InsertItem(i, image.name)
            listctrl.SetItem(i, 1, image.version)
            listctrl.SetItem(i, 2, image.board_id)
            listctrl.SetItem(i, 3, "✓" if image.kernel == self.constants.target_os else "")
            if image.kernel == self.constants.target_os:
                selected_index = i
        listctrl.Select(selected_index)
        listctrl.EnsureVisible(selected_index)

        note = wx.StaticText(dialog, label="Recovery images download macOS from Apple during install (internet required).",
                             pos=(-1, listctrl.GetPosition()[1] + listctrl.GetSize()[1] + 5))
        note.SetFont(gui_support.font_factory(11, wx.FONTWEIGHT_NORMAL))
        note.Centre(wx.HORIZONTAL)

        select_button = wx.Button(dialog, label="Download", pos=(-1, note.GetPosition()[1] + note.GetSize()[1] + 8), size=(150, -1))
        select_button.Centre(wx.HORIZONTAL)
        return_button = wx.Button(dialog, label="Return to Main Menu", pos=(-1, select_button.GetPosition()[1] + select_button.GetSize()[1] + 2), size=(150, -1))
        return_button.Centre(wx.HORIZONTAL)

        def on_select(event):
            index = listctrl.GetFirstSelected()
            if index == -1:
                return
            self.image = self.images[index]
            dialog.EndModal(wx.ID_OK)

        select_button.Bind(wx.EVT_BUTTON, on_select)
        listctrl.Bind(wx.EVT_LIST_ITEM_ACTIVATED, on_select)
        return_button.Bind(wx.EVT_BUTTON, lambda event: dialog.EndModal(wx.ID_CANCEL))
        dialog.SetSize((-1, return_button.GetPosition()[1] + return_button.GetSize()[1] + 40))
        dialog.Centre()
        result = dialog.ShowModal()
        dialog.Destroy()
        if result == wx.ID_OK:
            if self.image.kernel != self.constants.target_os:
                wx.MessageBox(f"Your EFI is set to build for {os_data.name(self.constants.target_os)}. "
                              f"It will be rebuilt for {self.image.name} before flashing.", "Target changed", wx.OK | wx.ICON_INFORMATION)
                self.constants.target_os = self.image.kernel
            self._download()

    def _download(self) -> None:
        dialog, sub, gauge = self._progress_dialog(f"Downloading: {self.image.name}", "Preparing download")
        target = self.constants.data_path / "Recovery" / f"{self.image.name.replace(' ', '-')}-{self.image.version}" / "com.apple.recovery.boot"

        def _run():
            try:
                self.recovery_path = macos_installer_handler.download(self.macrecovery_dir, self.image, target)
            except Exception as e:
                self.error = str(e)
                logging.error(traceback.format_exc())

        thread = threading.Thread(target=_run)
        thread.start()
        while thread.is_alive():
            size = sum(f.stat().st_size for f in target.glob("*") if f.is_file()) if target.exists() else 0
            sub.SetLabel(f"{gui_support.human_fmt(size)} downloaded")
            sub.Centre(wx.HORIZONTAL)
            gauge.Pulse()
            wx.MilliSleep(200)
            wx.Yield()
        dialog.Destroy()
        if self.recovery_path is None:
            wx.MessageBox(f"Download failed:\n{self.error}", "Error", wx.OK | wx.ICON_ERROR)
            return
        self._select_disk()

    # ---- flashing ----

    def _select_disk(self) -> None:
        if self.constants.host_os == "macOS":
            wx.MessageBox(f"Recovery downloaded to:\n{self.recovery_path}\n\nFlashing USB drives is available on Windows and Linux.",
                          "Downloaded", wx.OK | wx.ICON_INFORMATION)
            gui_support.reveal(self.recovery_path)
            return
        if not gui_support.RelaunchAsAdmin.is_admin():
            gui_support.RelaunchAsAdmin.explain(self.parent)
            return
        try:
            disks = [d for d in disk_handler.handler().list() if d.removable and not d.is_system]
        except Exception as e:
            wx.MessageBox(f"Couldn't list disks:\n{e}", "Error", wx.OK | wx.ICON_ERROR)
            return

        dialog = wx.Dialog(self.parent, title=self.title, size=(350, 200))
        title_label = wx.StaticText(dialog, label="Select local disk", pos=(-1, 5))
        title_label.SetFont(gui_support.font_factory(19, wx.FONTWEIGHT_BOLD))
        title_label.Centre(wx.HORIZONTAL)
        warning_label = wx.StaticText(dialog, label="Selected USB will be erased, please backup any data", pos=(-1, title_label.GetPosition()[1] + title_label.GetSize()[1] + 5))
        warning_label.SetFont(gui_support.font_factory(13, wx.FONTWEIGHT_NORMAL))
        warning_label.Centre(wx.HORIZONTAL)

        last = warning_label
        chosen = {}
        for disk in disks:
            button = wx.Button(dialog, label=f"{disk.identifier}: {disk.name} - {gui_support.human_fmt(disk.size)}",
                               pos=(-1, last.GetPosition()[1] + last.GetSize()[1] + 5), size=(300, 30))
            button.Centre(wx.HORIZONTAL)
            button.Bind(wx.EVT_BUTTON, lambda event, d=disk: (chosen.setdefault("disk", d), dialog.EndModal(wx.ID_OK)))
            last = button
        if not disks:
            last = wx.StaticText(dialog, label="No USB disks found", pos=(-1, warning_label.GetPosition()[1] + warning_label.GetSize()[1] + 5))
            last.SetFont(gui_support.font_factory(13, wx.FONTWEIGHT_BOLD))
            last.Centre(wx.HORIZONTAL)

        search_button = wx.Button(dialog, label="Search for disks again", pos=(-1, last.GetPosition()[1] + last.GetSize()[1] + 5), size=(150, 30))
        search_button.Centre(wx.HORIZONTAL)
        search_button.Bind(wx.EVT_BUTTON, lambda event: dialog.EndModal(wx.ID_RETRY))
        cancel_button = wx.Button(dialog, label="Return to Main Menu", pos=(-1, search_button.GetPosition()[1] + search_button.GetSize()[1] - 5), size=(150, 30))
        cancel_button.Centre(wx.HORIZONTAL)
        cancel_button.Bind(wx.EVT_BUTTON, lambda event: dialog.EndModal(wx.ID_CANCEL))
        dialog.SetSize((-1, cancel_button.GetPosition()[1] + cancel_button.GetSize()[1] + 40))
        dialog.Centre()
        result = dialog.ShowModal()
        dialog.Destroy()
        if result == wx.ID_RETRY:
            return self._select_disk()
        if result == wx.ID_OK:
            disk = chosen["disk"]
            confirm = wx.MessageDialog(self.parent, f"Erase {disk.name} ({gui_support.human_fmt(disk.size)}) and create a "
                                       f"{self.image.name} installer on it?\n\nEverything on this drive will be lost.",
                                       "Erase disk?", style=wx.YES_NO | wx.NO_DEFAULT | wx.ICON_WARNING)
            confirm.SetYesNoLabels("Erase and create", "Cancel")
            if confirm.ShowModal() == wx.ID_YES:
                self._flash(disk)

    def _flash(self, disk: disk_handler.Disk) -> None:
        dialog = wx.Dialog(self.parent, title=self.title, size=(370, 300))
        title_label = wx.StaticText(dialog, label=f"Creating Installer: {self.image.name}", pos=(-1, 5))
        title_label.SetFont(gui_support.font_factory(19, wx.FONTWEIGHT_BOLD))
        title_label.Centre(wx.HORIZONTAL)
        text_box = wx.TextCtrl(dialog, pos=(-1, 40), size=(350, 200), style=wx.TE_READONLY | wx.TE_MULTILINE | wx.TE_RICH2)
        text_box.Centre(wx.HORIZONTAL)
        dialog.SetSize((-1, 300))
        dialog.Centre()
        dialog.Show()

        logger = logging.getLogger()
        handler = gui_support.ThreadHandler(text_box)
        logger.addHandler(handler)
        state = {"ok": False}

        def _work():
            try:
                from ..efi_builder import build
                logging.info(f"Building OpenCore for {self.image.name}...")
                efi = build.BuildOpenCore(self.constants.computer, self.constants).build()
                logging.info(f"Writing installer to {disk.name}...")
                disk_handler.create_installer(efi, self.recovery_path, disk)
                state["ok"] = True
            except Exception as e:
                logging.error(f"Failed: {e}")

        thread = threading.Thread(target=_work)
        thread.start()
        gui_support.wait_for_thread(thread, self.constants.thread_sleep_interval)
        logger.removeHandler(handler)
        if state["ok"]:
            wx.MessageDialog(dialog, "Your macOS installer USB is ready.\n\nBoot from it, then choose the \"macOS Base System\" "
                             "entry in the OpenCore picker.", "Installer ready", style=wx.OK | wx.ICON_INFORMATION).ShowModal()
        else:
            wx.MessageDialog(dialog, "Creating the installer failed. See the log for details.", "Error",
                             style=wx.OK | wx.ICON_ERROR).ShowModal()
        dialog.Destroy()

    # ---- buttons ----

    def on_download(self, event: wx.Event) -> None:
        self.frame_modal.EndModal(wx.ID_OK)
        self.frame_modal.Destroy()
        if self._fetch_catalog():
            self._display_available_installers()

    def on_existing(self, event: wx.Event = None) -> None:
        with wx.DirDialog(self.frame_modal, "Choose a com.apple.recovery.boot folder", style=wx.DD_DIR_MUST_EXIST) as dd:
            if dd.ShowModal() != wx.ID_OK:
                return
            path = Path(dd.GetPath())
        if not list(path.glob("*.dmg")):
            wx.MessageBox("That folder has no BaseSystem.dmg or RecoveryImage.dmg.", "Not a recovery folder", wx.OK | wx.ICON_ERROR)
            return
        self.frame_modal.EndModal(wx.ID_OK)
        self.frame_modal.Destroy()
        self.recovery_path = path
        self.image = macos_installer_handler.RecoveryImage(self.constants.target_os, "", "existing", "default")
        self._select_disk()

    def on_return_to_main_menu(self, event: wx.Event = None) -> None:
        self.frame_modal.EndModal(wx.ID_CANCEL)
        self.frame_modal.Destroy()

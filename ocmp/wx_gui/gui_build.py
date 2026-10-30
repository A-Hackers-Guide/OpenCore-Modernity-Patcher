"""
gui_build.py: Generate UI for Building OpenCore

Same flow as OCLP: a modal with the build log, then an offer to install.
"""

import wx
import logging
import threading
import traceback

from .. import constants
from ..efi_builder import build, planner
from . import gui_main_menu, gui_install_oc, gui_support


class BuildFrame(wx.Frame):
    """
    Create a frame for building OpenCore
    Uses a Modal Dialog for smoother transition from other frames
    """

    def __init__(self, parent: wx.Frame, title: str, global_constants: constants.Constants, screen_location: tuple = None) -> None:
        logging.info("Initializing Build Frame")
        super(BuildFrame, self).__init__(parent, title=title, size=(350, 200), style=gui_support.frame_style())
        gui_support.GenerateMenubar(self, global_constants).generate()

        self.build_successful: bool = False
        self.build_error: str = ""
        self.install_button: wx.Button = None
        self.text_box: wx.TextCtrl = None
        self.frame_modal: wx.Dialog = None

        self.constants: constants.Constants = global_constants
        self.title: str = title

        self.frame_modal = wx.Dialog(self, title=title, size=(400, 200))

        self._generate_elements(self.frame_modal)
        self.Centre()
        if screen_location:
            self.SetPosition(screen_location)
        self.frame_modal.CentreOnScreen()
        self.frame_modal.Show()
        self._invoke_build()

    def _generate_elements(self, frame: wx.Frame = None) -> None:
        """
        Format:
            - Title label:        Build and Install OpenCore
            - Text:               Model: {Detected or Profile Model}
            - Button:             Install OpenCore
            - Read-only text box: {empty}
            - Button:             Return to Main Menu
        """
        frame = self if not frame else frame

        title_label = wx.StaticText(frame, label="Build and Install OpenCore", pos=(-1, 5))
        title_label.SetFont(gui_support.font_factory(19, wx.FONTWEIGHT_BOLD))
        title_label.Centre(wx.HORIZONTAL)

        model_label = wx.StaticText(frame, label=f"Model: {self.constants.computer.short_model()}", pos=(-1, 30))
        model_label.SetFont(gui_support.font_factory(13, wx.FONTWEIGHT_NORMAL))
        model_label.Centre(wx.HORIZONTAL)

        install_button = wx.Button(frame, label="🔩 Install OpenCore", pos=(-1, model_label.GetPosition()[1] + model_label.GetSize()[1]), size=(150, 30))
        install_button.Bind(wx.EVT_BUTTON, self.on_install)
        install_button.Centre(wx.HORIZONTAL)
        install_button.Disable()
        self.install_button = install_button

        text_box = wx.TextCtrl(frame, value="", pos=(-1, install_button.GetPosition()[1] + install_button.GetSize()[1] + 10), size=(380, 350),
                               style=wx.TE_READONLY | wx.TE_MULTILINE | wx.TE_RICH2)
        text_box.SetFont(gui_support.font_factory(11, wx.FONTWEIGHT_NORMAL))
        text_box.Centre(wx.HORIZONTAL)
        self.text_box = text_box

        return_button = wx.Button(frame, label="Return to Main Menu", pos=(-1, text_box.GetPosition()[1] + text_box.GetSize()[1] + 5), size=(150, 30))
        return_button.Bind(wx.EVT_BUTTON, self.on_return_to_main_menu)
        return_button.Centre(wx.HORIZONTAL)
        return_button.Disable()
        self.return_button = return_button

        frame.SetSize((-1, return_button.GetPosition()[1] + return_button.GetSize()[1] + 40))

    def _invoke_build(self) -> None:
        """
        Invokes build function and waits for it to finish
        """
        thread = threading.Thread(target=self._build)
        thread.start()
        gui_support.wait_for_thread(thread, self.constants.thread_sleep_interval)

        self.return_button.Enable()
        if self.build_successful is False:
            wx.MessageDialog(
                parent=self.frame_modal,
                message=f"An error occurred while building OpenCore:\n\n{self.build_error}",
                caption="Error building OpenCore",
                style=wx.OK | wx.ICON_ERROR
            ).ShowModal()
            return

        dialog = wx.MessageDialog(
            parent=self.frame_modal,
            message="Would you like to install OpenCore now?",
            caption="Finished building your OpenCore configuration!",
            style=wx.YES_NO | wx.CANCEL | wx.ICON_QUESTION
        )
        dialog.SetYesNoCancelLabels("Install to disk", "View build log", "Open EFI folder")
        result = dialog.ShowModal()
        if result == wx.ID_YES:
            self.on_install()
            return
        if result == wx.ID_CANCEL:
            gui_support.reveal(self.constants.last_build_path)
        self.install_button.Enable()

    def _build(self) -> None:
        """
        Calls build function and redirects log output to the text box
        """
        logger = logging.getLogger()
        handler = gui_support.ThreadHandler(self.text_box)
        logger.addHandler(handler)
        try:
            build.BuildOpenCore(self.constants.computer, self.constants).build()
            self.build_successful = True
        except (planner.PlanError, build.BuildError) as e:
            self.build_error = str(e)
            logging.error(f"Build failed: {e}")
        except Exception as e:
            self.build_error = str(e)
            logging.error("An internal error occurred while building:\n")
            logging.error(traceback.format_exc())
        logger.removeHandler(handler)

    def on_return_to_main_menu(self, event: wx.Event = None) -> None:
        self.frame_modal.Hide()
        main_menu_frame = gui_main_menu.MainFrame(None, title=self.title, global_constants=self.constants,
                                                  screen_location=self.GetScreenPosition())
        main_menu_frame.Show()
        self.frame_modal.Destroy()
        self.Destroy()

    def on_install(self, event: wx.Event = None) -> None:
        self.frame_modal.Destroy()
        self.Destroy()
        install_oc_frame = gui_install_oc.InstallOCFrame(None, title=self.title, global_constants=self.constants,
                                                         screen_location=self.GetScreenPosition())
        install_oc_frame.Show()

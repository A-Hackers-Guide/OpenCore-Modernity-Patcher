"""
OpenCore Modernity Patcher entry point

No arguments: launch the GUI. With --build (or other flags): run headless.
"""

import sys
import logging
import argparse
from pathlib import Path

from . import constants, hardware, settings
from .datasets import os_data


def _logging(c: constants.Constants) -> None:
    c.ensure_paths()
    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s",
        handlers=[logging.StreamHandler(sys.stdout), logging.FileHandler(c.log_filepath, encoding="utf-8")],
    )


def _target(value: str) -> int:
    for kernel, (marketing, number) in os_data.MARKETING_NAMES.items():
        if value.lower() in (marketing.lower(), marketing.split()[-1].lower(), number, str(int(kernel))):
            return int(kernel)
    raise argparse.ArgumentTypeError(f"unknown macOS version '{value}'")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="ocmp", description=constants.APP_NAME)
    parser.add_argument("--build", action="store_true", help="build an OpenCore EFI without the GUI")
    parser.add_argument("--profile", type=Path, help="build for a saved hardware profile (JSON) instead of this PC")
    parser.add_argument("--save-profile", type=Path, help="detect this PC and save its profile to a JSON file")
    parser.add_argument("--target", type=_target, help="macOS to target, e.g. sequoia, 15, tahoe")
    parser.add_argument("--smbios", help="override the SMBIOS model, e.g. MacPro7,1")
    parser.add_argument("--output", type=Path, help="where to write the EFI folder")
    parser.add_argument("--debug-opencore", action="store_true", help="use the DEBUG OpenCore build")
    parser.add_argument("--version", action="version", version=f"{constants.APP_NAME} {constants.APP_VERSION}")
    args = parser.parse_args(argv)

    c = constants.Constants()
    settings.load(c)
    _logging(c)

    if args.target:
        c.target_os = args.target
    if args.smbios:
        c.custom_smbios = args.smbios
    if args.debug_opencore:
        c.opencore_debug = True
    if args.output:
        c.build_path = args.output.resolve()

    if args.save_profile:
        profile = hardware.detect()
        profile.save(args.save_profile)
        print(f"Saved hardware profile to {args.save_profile}")
        print(profile.to_json())
        return 0

    c.computer = hardware.HardwareProfile.load(args.profile) if args.profile else hardware.detect()
    if args.profile:
        c.custom_profile_path = args.profile

    if args.build:
        from .efi_builder import build, planner
        try:
            build.BuildOpenCore(c.computer, c).build()
        except (planner.PlanError, build.BuildError) as e:
            logging.error(f"Build failed: {e}")
            return 1
        return 0

    from .wx_gui import gui_entry
    gui_entry.EntryPoint(c).start()
    return 0


if __name__ == "__main__":
    sys.exit(main())

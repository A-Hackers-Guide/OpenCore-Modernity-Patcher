"""
macos_installer_handler.py: Download macOS Recovery from Apple

On Windows and Linux a full InstallAssistant.pkg can't be unpacked, so,
like the Dortania guide, we fetch the recovery image (BaseSystem.dmg +
.chunklist) with OpenCorePkg's macrecovery.py. The installer then
downloads the rest of macOS over the network during install.
"""

import io
import sys
import json
import runpy
import logging
import contextlib
from pathlib import Path
from typing import Dict, List

from .datasets import os_data


class RecoveryImage:

    def __init__(self, kernel: int, version: str, board_id: str, os_type: str) -> None:
        self.kernel = kernel
        self.version = version
        self.board_id = board_id
        self.os_type = os_type

    @property
    def name(self) -> str:
        return os_data.name(self.kernel)

    def __repr__(self) -> str:
        return f"{self.name} {self.version} ({self.board_id})"


MAJOR_TO_KERNEL = {
    "10.13": os_data.os_data.high_sierra, "10.14": os_data.os_data.mojave, "10.15": os_data.os_data.catalina,
    "11": os_data.os_data.big_sur, "12": os_data.os_data.monterey, "13": os_data.os_data.ventura,
    "14": os_data.os_data.sonoma, "15": os_data.os_data.sequoia, "26": os_data.os_data.tahoe,
    "27": os_data.os_data.golden_gate,
}


def _major(version: str) -> str:
    parts = version.split(".")
    return ".".join(parts[:2]) if parts[0] == "10" else parts[0]


def available_images(macrecovery_dir: Path) -> List[RecoveryImage]:
    """
    One entry per macOS version: a board ID whose newest OS is that version
    """
    boards: Dict[str, str] = json.loads((macrecovery_dir / "boards.json").read_text(encoding="utf-8"))
    newest_major = max((_major(v) for v in boards.values() if _major(v) in MAJOR_TO_KERNEL),
                       key=lambda m: MAJOR_TO_KERNEL[m])
    best: Dict[str, tuple] = {}
    for board, version in boards.items():
        major = _major(version)
        if major not in MAJOR_TO_KERNEL:
            continue
        key = tuple(int(x) for x in version.split(".") if x.isdigit())
        if major not in best or key > best[major][0]:
            best[major] = (key, board, version)
    images = []
    for major, (_, board, version) in best.items():
        os_type = "latest" if major == newest_major else "default"
        images.append(RecoveryImage(int(MAJOR_TO_KERNEL[major]), version, board, os_type))
    images.sort(key=lambda i: i.kernel, reverse=True)
    return images


def download(macrecovery_dir: Path, image: RecoveryImage, outdir: Path) -> Path:
    """
    Run macrecovery.py in-process (works inside the frozen .exe/.AppImage too)
    """
    outdir.mkdir(parents=True, exist_ok=True)
    script = macrecovery_dir / "macrecovery.py"
    argv = [str(script), "-b", image.board_id, "-m", "00000000000000000", "-os", image.os_type,
            "-o", str(outdir), "download"]
    logging.info(f"- Requesting {image.name} recovery from Apple ({image.board_id}, {image.os_type})")
    old_argv, old_path = sys.argv, list(sys.path)
    buffer = io.StringIO()
    try:
        sys.argv = argv
        sys.path.insert(0, str(macrecovery_dir))
        with contextlib.redirect_stdout(buffer):
            try:
                runpy.run_path(str(script), run_name="__main__")
            except SystemExit as e:
                if e.code not in (0, None):
                    raise RuntimeError(f"macrecovery exited with {e.code}: {buffer.getvalue()[-500:]}")
    finally:
        sys.argv, sys.path = old_argv, old_path
    for line in buffer.getvalue().splitlines():
        if line.strip() and not line.startswith("\r"):
            logging.info(f"  {line.strip()[:120]}")
    dmg = next(outdir.glob("*.dmg"), None)
    if dmg is None:
        raise RuntimeError("macrecovery finished without producing a .dmg")
    return outdir

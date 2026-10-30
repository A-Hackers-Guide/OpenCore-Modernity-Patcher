"""
disk_handler.py: List disks, mount EFI partitions and prepare USB installers

Windows uses PowerShell's Storage module and diskpart; Linux uses lsblk,
parted, mkfs.vfat and mount. Every destructive action is limited to the
disk the user picked, and USB erasing only accepts removable/USB disks.
"""

import os
import sys
import json
import shutil
import string
import logging
import tempfile
import subprocess
from pathlib import Path
from dataclasses import dataclass, field
from typing import List

ESP_GUID = "c12a7328-f81f-11d2-ba4b-00a0c93ec93b"
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


class DiskError(Exception):
    pass


@dataclass
class Partition:
    identifier: str            # Linux: /dev/sdb1   Windows: "disk:partition" e.g. "2:1"
    number: int
    size: int
    fstype: str = ""
    label: str = ""
    is_esp: bool = False
    mountpoint: str = ""


@dataclass
class Disk:
    identifier: str            # Linux: /dev/sdb    Windows: disk number as string
    name: str
    size: int
    removable: bool = False
    bus: str = ""
    is_system: bool = False
    partitions: List[Partition] = field(default_factory=list)

    @property
    def esps(self) -> List[Partition]:
        return [p for p in self.partitions if p.is_esp or (p.fstype.lower() in ("vfat", "fat32") and p.label.upper() == "EFI")]


def _run(cmd: List[str], check: bool = True, input_text: str = None) -> str:
    logging.debug(f"$ {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True, input=input_text, creationflags=NO_WINDOW)
    if check and result.returncode != 0:
        raise DiskError(f"{cmd[0]} failed: {(result.stderr or result.stdout).strip()[:400]}")
    return result.stdout


# ---------------------------------------------------------------------------
# Linux
# ---------------------------------------------------------------------------

class LinuxDisks:

    def list(self) -> List[Disk]:
        out = _run(["lsblk", "-J", "-b", "-o", "NAME,PATH,SIZE,TYPE,FSTYPE,PARTTYPE,PARTN,LABEL,MOUNTPOINT,MODEL,VENDOR,RM,TRAN,HOTPLUG"])
        disks = []
        for dev in json.loads(out).get("blockdevices", []):
            if dev.get("type") != "disk" or dev["path"].startswith(("/dev/loop", "/dev/zram", "/dev/sr")):
                continue
            name = " ".join(x.strip() for x in (dev.get("vendor") or "", dev.get("model") or "") if x and x.strip()) or dev["name"]
            disk = Disk(dev["path"], name, int(dev["size"] or 0), bool(dev.get("rm")) or bool(dev.get("hotplug")), dev.get("tran") or "")
            for part in dev.get("children", []) or []:
                mount = part.get("mountpoint") or ""
                if mount in ("/", "/boot", "/boot/efi", "/efi", "/usr", "/home"):
                    disk.is_system = True
                disk.partitions.append(Partition(
                    part["path"], int(part.get("partn") or 0), int(part.get("size") or 0), part.get("fstype") or "",
                    part.get("label") or "", (part.get("parttype") or "").lower() == ESP_GUID, mount))
            disks.append(disk)
        return disks

    def mount(self, part: Partition) -> Path:
        if part.mountpoint:
            return Path(part.mountpoint)
        target = Path(tempfile.mkdtemp(prefix="ocmp-esp-"))
        _run(["mount", "-t", "vfat", part.identifier, str(target)])
        return target

    def unmount(self, part: Partition, path: Path) -> None:
        if part.mountpoint:
            return
        subprocess.run(["sync"])
        _run(["umount", str(path)], check=False)
        shutil.rmtree(path, ignore_errors=True)

    def format_usb(self, disk: Disk) -> Partition:
        for part in disk.partitions:
            if part.mountpoint:
                _run(["umount", part.identifier], check=False)
        _run(["wipefs", "-a", disk.identifier])
        _run(["parted", "-s", disk.identifier, "mklabel", "gpt", "mkpart", "OCMP", "fat32", "1MiB", "100%", "set", "1", "esp", "on"])
        _run(["udevadm", "settle"], check=False)
        part_path = disk.identifier + ("p1" if disk.identifier[-1].isdigit() else "1")
        _run(["mkfs.vfat", "-F", "32", "-n", "OCMP", part_path])
        return Partition(part_path, 1, disk.size, "vfat", "OCMP", True)


# ---------------------------------------------------------------------------
# Windows
# ---------------------------------------------------------------------------

WIN_LIST = r"""
$ErrorActionPreference = 'SilentlyContinue'
$sys = (Get-Partition | Where-Object { $_.IsBoot -or $_.IsSystem } | Select-Object -ExpandProperty DiskNumber -Unique)
@(Get-Disk | ForEach-Object {
  $d = $_
  [pscustomobject]@{
    Number = $d.Number; Name = $d.FriendlyName; Size = $d.Size; Bus = "$($d.BusType)"
    IsSystem = ($sys -contains $d.Number) -or $d.IsBoot -or $d.IsSystem
    Partitions = @(Get-Partition -DiskNumber $d.Number | ForEach-Object {
      $v = $_ | Get-Volume
      [pscustomobject]@{ Number = $_.PartitionNumber; Size = $_.Size; GptType = "$($_.GptType)"; Letter = "$($_.DriveLetter)"; Fs = "$($v.FileSystem)"; Label = "$($v.FileSystemLabel)" }
    })
  }
}) | ConvertTo-Json -Depth 5 -Compress
"""


class WindowsDisks:

    def _ps(self, script: str) -> str:
        return _run(["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", script])

    def _diskpart(self, commands: List[str]) -> str:
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
            f.write("\n".join(commands) + "\n")
            script = f.name
        try:
            return _run(["diskpart", "/s", script])
        finally:
            os.unlink(script)

    def list(self) -> List[Disk]:
        data = json.loads(self._ps(WIN_LIST) or "[]")
        if isinstance(data, dict):
            data = [data]
        disks = []
        for d in data:
            disk = Disk(str(d["Number"]), d.get("Name") or f"Disk {d['Number']}", int(d.get("Size") or 0),
                        d.get("Bus") in ("USB", "SD", "MMC"), d.get("Bus") or "", bool(d.get("IsSystem")))
            parts = d.get("Partitions") or []
            if isinstance(parts, dict):
                parts = [parts]
            for p in parts:
                letter = (p.get("Letter") or "").strip("\x00 ")
                disk.partitions.append(Partition(
                    f"{d['Number']}:{p['Number']}", int(p["Number"]), int(p.get("Size") or 0), p.get("Fs") or "",
                    p.get("Label") or "", ESP_GUID in (p.get("GptType") or "").lower(), f"{letter}:\\" if letter else ""))
            disks.append(disk)
        return disks

    @staticmethod
    def _free_letter() -> str:
        used = {Path(f"{l}:\\").exists() and l for l in string.ascii_uppercase}
        for letter in reversed(string.ascii_uppercase[3:]):
            if letter not in used:
                return letter
        raise DiskError("No free drive letter")

    def mount(self, part: Partition) -> Path:
        if part.mountpoint:
            return Path(part.mountpoint)
        disk, number = part.identifier.split(":")
        letter = self._free_letter()
        self._diskpart([f"select disk {disk}", f"select partition {number}", f"assign letter={letter}"])
        part.mountpoint = ""      # we assigned it, so unmount() removes it
        return Path(f"{letter}:\\")

    def unmount(self, part: Partition, path: Path) -> None:
        if part.mountpoint:
            return
        disk, number = part.identifier.split(":")
        self._diskpart([f"select disk {disk}", f"select partition {number}", f"remove letter={str(path)[0]}"])

    def format_usb(self, disk: Disk) -> Partition:
        letter = self._free_letter()
        # diskpart only formats FAT32 up to 32 GB; recovery + EFI need ~1 GB
        size_mb = min(disk.size // (1024 * 1024) - 64, 16384)
        self._diskpart([
            f"select disk {disk.identifier}", "clean", "convert gpt",
            f"create partition primary size={size_mb}", 'format fs=fat32 quick label="OCMP"', f"assign letter={letter}",
        ])
        part = Partition(f"{disk.identifier}:1", 1, size_mb * 1024 * 1024, "FAT32", "OCMP", False, f"{letter}:\\")
        return part


# ---------------------------------------------------------------------------

def handler():
    if sys.platform == "win32":
        return WindowsDisks()
    if sys.platform.startswith("linux"):
        return LinuxDisks()
    raise DiskError("Disk operations are only available on Windows and Linux")


def install_efi(efi_folder: Path, part: Partition) -> Path:
    """
    Copy a built EFI folder onto an EFI partition, keeping a backup of the old one
    """
    h = handler()
    mount = h.mount(part)
    try:
        dest = mount / "EFI"
        if (dest / "OC").exists():
            backup = mount / "EFI-backup-ocmp"
            shutil.rmtree(backup, ignore_errors=True)
            shutil.copytree(dest, backup)
            logging.info(f"- Backed up existing EFI to {backup}")
        dest.mkdir(exist_ok=True)
        # Leave other boot loaders (Microsoft, Linux) alone; replace BOOT and OC only
        for sub in ("BOOT", "OC"):
            shutil.rmtree(dest / sub, ignore_errors=True)
            shutil.copytree(efi_folder / sub, dest / sub)
        logging.info(f"- Copied OpenCore to {dest}")
        return dest
    finally:
        h.unmount(part, mount)


def create_installer(efi_folder: Path, recovery_folder: Path, disk: Disk) -> None:
    """
    Erase a USB disk, then add com.apple.recovery.boot and the EFI folder
    """
    if disk.is_system:
        raise DiskError("Refusing to erase the disk this computer is running from")
    if not disk.removable:
        raise DiskError("Only USB/removable disks can be used for an installer")
    h = handler()
    logging.info(f"- Erasing {disk.name} ({disk.identifier})")
    part = h.format_usb(disk)
    mount = h.mount(part)
    try:
        shutil.copytree(recovery_folder, mount / "com.apple.recovery.boot", dirs_exist_ok=True)
        logging.info("- Copied macOS Recovery")
        shutil.copytree(efi_folder, mount / "EFI", dirs_exist_ok=True)
        logging.info("- Copied OpenCore EFI")
    finally:
        h.unmount(part, mount)

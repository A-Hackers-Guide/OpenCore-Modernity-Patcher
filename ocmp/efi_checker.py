"""
efi_checker.py: Check an existing OpenCore EFI for updates and problems

Works on any EFI folder (ours or hand-made): reads OpenCore's version,
every kext's version, compares them with the latest upstream releases,
flags kexts listed in config.plist but missing on disk, and runs
ocvalidate from the matching OpenCorePkg when available.
"""

import re
import json
import plistlib
import logging
import subprocess
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Optional

from . import network_handler
from .datasets import kext_data, os_data, smbios_data


@dataclass
class KextStatus:
    name: str
    installed: str
    latest: str = ""
    enabled: bool = True
    missing: bool = False

    @property
    def state(self) -> str:
        if self.missing:
            return "MISSING on disk"
        if not self.latest:
            return "not tracked"
        return "up to date" if _ver(self.installed) >= _ver(self.latest) else f"update available ({self.latest})"


@dataclass
class EFIReport:
    root: Path
    opencore: str = ""
    opencore_latest: str = ""
    smbios: str = ""
    kexts: List[KextStatus] = field(default_factory=list)
    validation: Optional[str] = None
    problems: List[str] = field(default_factory=list)

    def text(self) -> str:
        oc_state = ""
        if self.opencore and self.opencore_latest:
            oc_state = "up to date" if _ver(self.opencore) >= _ver(self.opencore_latest) else f"update available ({self.opencore_latest})"
        lines = [f"EFI:      {self.root}",
                 f"OpenCore: {self.opencore or 'unknown (in macOS run: nvram 4D1FDA02-38C7-4A6A-9CC6-4BCCA8B30102:opencore-version)'}  {oc_state}".rstrip(),
                 f"SMBIOS:   {self.smbios or 'unknown'}"
                 + (f"  (newest macOS for this model: {os_data.name(smbios_data.max_os(self.smbios))})" if self.smbios in smbios_data.SMBIOS else ""),
                 "", "Kexts:"]
        width = max([len(k.name) for k in self.kexts] + [4])
        for k in self.kexts:
            lines.append(f"  {k.name:<{width}}  {k.installed:<10} {k.state}{'' if k.enabled else '  (disabled)'}")
        if self.validation is not None:
            lines += ["", "ocvalidate:", "  " + self.validation.replace("\n", "\n  ")]
        if self.problems:
            lines += ["", "Problems:"] + [f"  - {p}" for p in self.problems]
        outdated = [k for k in self.kexts if k.state.startswith("update")]
        lines += ["", f"Summary: {len(outdated)} kext update(s) available, {len(self.problems)} problem(s)."]
        return "\n".join(lines)


def _ver(value: str) -> tuple:
    return tuple(int(x) for x in re.findall(r"\d+", value or "")[:3]) or (0,)


def _opencore_version(efi: Path) -> str:
    """
    OpenCore.efi only holds a "REL-XXX-YYYY-MM-DD" placeholder (the real
    version is set at build time in compressed data), so we read the
    marker our builder writes; other EFIs report it at boot in NVRAM.
    """
    marker = efi / "OC" / ".ocmp-build.json"
    try:
        return json.loads(marker.read_text(encoding="utf-8")).get("opencore", "")
    except (OSError, ValueError):
        return ""


def check(efi: Path, constants, online: bool = True) -> EFIReport:
    efi = Path(efi)
    if (efi / "EFI").is_dir():
        efi = efi / "EFI"
    report = EFIReport(root=efi)
    config_path = efi / "OC" / "config.plist"
    if not config_path.exists():
        report.problems.append("No OC/config.plist; this isn't an OpenCore EFI folder.")
        return report
    with open(config_path, "rb") as f:
        config = plistlib.load(f)
    report.opencore = _opencore_version(efi)
    report.smbios = config.get("PlatformInfo", {}).get("Generic", {}).get("SystemProductName", "")

    net = network_handler.NetworkHandler(constants) if online else None
    for entry in config.get("Kernel", {}).get("Add", []):
        bundle = entry.get("BundlePath", "")
        name = Path(bundle).stem
        path = efi / "OC" / "Kexts" / bundle
        status = KextStatus(name, "", enabled=bool(entry.get("Enabled", True)))
        info_plist = path / "Contents" / "Info.plist"
        if not info_plist.exists():
            status.missing = True
            if status.enabled:
                report.problems.append(f"{bundle} is enabled in config.plist but not in OC/Kexts.")
        else:
            with open(info_plist, "rb") as f:
                status.installed = plistlib.load(f).get("CFBundleVersion", "")
        if net and name in kext_data.KEXTS and "PlugIns" not in bundle:
            try:
                status.latest = net.latest_release(kext_data.KEXTS[name]["repo"])["tag_name"].lstrip("v.").replace("V", "")
            except network_handler.DownloadError as e:
                logging.info(f"- Couldn't check {name}: {e}")
        report.kexts.append(status)

    for entry in config.get("UEFI", {}).get("Drivers", []):
        driver = entry.get("Path", "") if isinstance(entry, dict) else entry
        if driver and entry.get("Enabled", True) and not (efi / "OC" / "Drivers" / driver).exists():
            report.problems.append(f"Driver {driver} is enabled in config.plist but missing from OC/Drivers.")
    for entry in config.get("ACPI", {}).get("Add", []):
        table = entry.get("Path", "")
        if entry.get("Enabled", True) and table and not (efi / "OC" / "ACPI" / table).exists():
            report.problems.append(f"ACPI table {table} is enabled in config.plist but missing from OC/ACPI.")

    if net:
        try:
            report.opencore_latest = net.latest_release("acidanthera/OpenCorePkg")["tag_name"]
            report.validation = _ocvalidate(net, config_path)
        except network_handler.DownloadError as e:
            logging.info(f"- Couldn't fetch OpenCorePkg: {e}")
    return report


def _ocvalidate(net, config_path: Path) -> Optional[str]:
    from .efi_builder.build import _host_binary
    ocpkg = net.extract(net.release_asset("acidanthera/OpenCorePkg", lambda n: n.endswith("-RELEASE.zip")))
    binary = _host_binary(ocpkg / "Utilities" / "ocvalidate", "ocvalidate")
    if binary is None:
        return None
    result = subprocess.run([str(binary), str(config_path)], capture_output=True, text=True, timeout=60,
                            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    text = (result.stdout + result.stderr).strip()
    lines = [l for l in text.splitlines() if l.strip() and not l.startswith("NOTE:")]
    return "\n".join(lines[-12:]) or "no output"


def update_kexts(efi: Path, constants) -> List[str]:
    """
    Replace outdated tracked kexts with the latest releases, after backing up the EFI

    config.plist is left alone: bundle names and paths don't change between
    kext releases, and plug-ins come along inside their parent bundle.
    """
    import shutil
    import time
    from .efi_builder.build import BuildOpenCore

    report = check(efi, constants)
    outdated = [k for k in report.kexts if k.enabled and not k.missing and k.state.startswith("update")]
    if not outdated:
        return []
    root = report.root
    backup = root.parent / f"EFI-backup-{time.strftime('%Y%m%d-%H%M%S')}"
    shutil.copytree(root, backup)
    logging.info(f"- Backed up EFI to {backup}")

    net = network_handler.NetworkHandler(constants)
    updated = []
    for kext in outdated:
        info = kext_data.KEXTS[kext.name]
        source = BuildOpenCore._find_bundle(net.extract(net.release_asset(info["repo"], info["asset"])), f"{kext.name}.kext")
        if source is None:
            logging.info(f"- {kext.name}.kext not found in its latest release; left as is")
            continue
        target = root / "OC" / "Kexts" / f"{kext.name}.kext"
        shutil.rmtree(target)
        shutil.copytree(source, target)
        updated.append(f"{kext.name} {kext.installed} -> {kext.latest}")
        logging.info(f"- Updated {kext.name} {kext.installed} -> {kext.latest}")
    return updated

"""
build.py: Assemble a complete OpenCore EFI folder

Equivalent of OCLP's efi_builder/build.py: download payloads, plan,
write config.plist, copy files, then validate with ocvalidate.
"""

import re
import json
import sys
import uuid
import shutil
import secrets
import logging
import plistlib
import subprocess
from pathlib import Path
from typing import Dict, List, Optional

from .. import network_handler
from ..datasets import kext_data, os_data
from ..hardware import HardwareProfile
from .planner import Planner, BuildPlan, ACPI_URLS
from .config import ConfigBuilder, amd_patches


AMD_VANILLA_URL = "https://raw.githubusercontent.com/AMD-OSX/AMD_Vanilla/master/patches.plist"


class BuildError(Exception):
    pass


def _host_binary(folder: Path, name: str) -> Optional[Path]:
    """
    OpenCorePkg ships Utilities/<tool>/<tool>(.exe|.linux); pick ours
    """
    if sys.platform == "win32":
        candidate = folder / f"{name}.exe"
    elif sys.platform.startswith("linux"):
        candidate = folder / f"{name}.linux"
    else:
        candidate = folder / name
    if not candidate.exists():
        return None
    if sys.platform != "win32":
        candidate.chmod(0o755)
    return candidate


class BuildOpenCore:

    def __init__(self, profile: HardwareProfile, constants, progress=None) -> None:
        self.hw = profile
        self.c = constants
        self.net = network_handler.NetworkHandler(constants, progress)
        self.plan: Optional[BuildPlan] = None
        self.output: Path = constants.build_path
        self.validation_output: str = ""

    def build(self) -> Path:
        logging.info(f"Building OpenCore for: {self.hw.short_model()}")
        logging.info(f"- CPU: {self.hw.summary()}")
        for gpu in self.hw.gpus:
            logging.info(f"- GPU: {gpu.pci_id} {gpu.name} [{gpu.arch}]")
        logging.info(f"- Target: {os_data.label(self.c.target_os)}")

        self.plan = Planner(self.hw, self.c).plan()
        logging.info(f"- Platform: {self.plan.platform}")
        logging.info(f"- SMBIOS: {self.plan.smbios}")

        ocpkg = self._opencorepkg()
        efi = self._prepare_output(ocpkg)

        acpi_files = self._acpi(ocpkg, efi)
        kext_entries = self._kexts(efi)
        patches = self._amd_patches()
        smbios = self._smbios(ocpkg)

        config = ConfigBuilder(ocpkg / "Docs" / "Sample.plist", self.plan, self.c).build(kext_entries, acpi_files, patches, smbios)
        self._prune_drivers(efi)
        config_path = efi / "OC" / "config.plist"
        with open(config_path, "wb") as f:
            plistlib.dump(config, f, sort_keys=True)
        logging.info("- Wrote config.plist")

        self._validate(ocpkg, config_path)
        self._write_report(efi.parent)
        (efi / "OC" / ".ocmp-build.json").write_text(json.dumps({
            "app_version": self.c.patcher_version, "opencore": self.opencore_version, "build": self.c.opencore_build,
            "target": int(self.plan.target_os), "smbios": self.plan.smbios, "platform": self.plan.platform,
        }, indent=2), encoding="utf-8")

        for warning in self.plan.warnings:
            logging.info(f"WARNING: {warning}")
        for note in self.plan.notes:
            logging.info(f"Note: {note}")
        logging.info(f"Your OpenCore EFI has been built at:\n    {efi}")
        self.c.last_build_path = efi
        return efi

    # ---- payloads ----

    def _opencorepkg(self) -> Path:
        build = self.c.opencore_build
        archive = self.net.release_asset("acidanthera/OpenCorePkg", lambda n: n.endswith(f"-{build}.zip"))
        folder = self.net.extract(archive)
        self.opencore_version = self.net.latest_release("acidanthera/OpenCorePkg")["tag_name"]
        logging.info(f"- Using {archive.name}")
        return folder

    def _prepare_output(self, ocpkg: Path) -> Path:
        if self.output.exists():
            shutil.rmtree(self.output)
        efi = self.output / "EFI"
        shutil.copytree(ocpkg / "X64" / "EFI", efi)
        # Start from an empty set of tools/kexts/ACPI; drivers are pruned later
        for sub in ("Kexts", "ACPI", "Tools"):
            target = efi / "OC" / sub
            shutil.rmtree(target, ignore_errors=True)
            target.mkdir(parents=True)
        if not self.c.opencanopy:
            shutil.rmtree(efi / "OC" / "Resources", ignore_errors=True)
            (efi / "OC" / "Resources").mkdir()
        return efi

    def _prune_drivers(self, efi: Path) -> None:
        drivers = efi / "OC" / "Drivers"
        for driver in drivers.iterdir():
            if driver.name not in self.plan.drivers:
                driver.unlink()
        missing = [d for d in self.plan.drivers if not (drivers / d).exists()]
        if missing:
            raise BuildError(f"Drivers missing from OpenCorePkg: {', '.join(missing)}")

    def _acpi(self, ocpkg: Path, efi: Path) -> List[str]:
        files = []
        for name in self.plan.acpi_ocpkg:
            shutil.copy(ocpkg / "Docs" / "AcpiSamples" / "Binaries" / name, efi / "OC" / "ACPI" / name)
            files.append(name)
        for name in self.plan.acpi_dortania:
            data = self.net.fetch_text(ACPI_URLS[name], f"acpi/{name}")
            (efi / "OC" / "ACPI" / name).write_bytes(data)
            files.append(name)
        logging.info(f"- Added {len(files)} ACPI tables: {', '.join(files) or 'none'}")
        return files

    def _kexts(self, efi: Path) -> List[dict]:
        entries = []
        extracted: Dict[Path, Path] = {}
        for name in kext_data.load_order(self.plan.kexts):
            info = kext_data.KEXTS[name]
            archive = self.net.release_asset(info["repo"], info["asset"])
            if archive not in extracted:
                extracted[archive] = self.net.extract(archive)
            bundle = self._find_bundle(extracted[archive], f"{name}.kext")
            if bundle is None:
                raise BuildError(f"{name}.kext not found in the {info['repo']} release")
            dest = efi / "OC" / "Kexts" / bundle.name
            shutil.copytree(bundle, dest)
            entries.append(self._kext_entry(dest, bundle.name))
            for plugin in info.get("plugins", []):
                plugin_path = dest / "Contents" / "PlugIns" / f"{plugin}.kext"
                if plugin_path.exists():
                    entries.append(self._kext_entry(plugin_path, f"{bundle.name}/Contents/PlugIns/{plugin}.kext"))
                else:
                    logging.info(f"- Note: {plugin}.kext not inside {bundle.name}, skipped")
        logging.info(f"- Added {len(self.plan.kexts)} kexts: {', '.join(kext_data.load_order(self.plan.kexts))}")
        return entries

    @staticmethod
    def _find_bundle(root: Path, bundle: str) -> Optional[Path]:
        matches = [p for p in root.rglob(bundle) if p.is_dir() and "PlugIns" not in p.parent.parts[-2:] and "__MACOSX" not in p.parts]
        matches.sort(key=lambda p: len(p.parts))   # shallowest wins (skips dSYM copies)
        return matches[0] if matches else None

    @staticmethod
    def _kext_entry(path: Path, bundle_path: str) -> dict:
        with open(path / "Contents" / "Info.plist", "rb") as f:
            info = plistlib.load(f)
        executable = info.get("CFBundleExecutable", "")
        exec_path = f"Contents/MacOS/{executable}" if executable and (path / "Contents" / "MacOS" / executable).exists() else ""
        return {
            "Arch": "x86_64",
            "BundlePath": bundle_path,
            "Comment": f"{Path(bundle_path).stem} {info.get('CFBundleVersion', '')}".strip(),
            "Enabled": True,
            "ExecutablePath": exec_path,
            "MaxKernel": "",
            "MinKernel": "",
            "PlistPath": "Contents/Info.plist",
        }

    def _amd_patches(self) -> List[dict]:
        if not self.plan.amd_patches:
            return []
        data = self.net.fetch_text(AMD_VANILLA_URL, "AMD_Vanilla/patches.plist")
        return amd_patches(data, self.plan.amd_core_count, self.plan.target_os)

    # ---- SMBIOS ----

    def _smbios(self, ocpkg: Path) -> dict:
        """
        Serial, MLB, UUID and ROM are saved per model and reused on rebuilds,
        so iMessage/FaceTime keep seeing the same Mac
        """
        model = self.plan.smbios
        store = self.c.data_path / "smbios" / f"{model.replace(',', '_')}.json"
        saved = {}
        if store.exists():
            try:
                saved = json.loads(store.read_text(encoding="utf-8"))
            except ValueError:
                saved = {}
        serial, mlb = self.c.custom_serial, self.c.custom_board_serial
        if not (serial and mlb):
            serial, mlb = saved.get("serial", ""), saved.get("mlb", "")
        reused = bool(serial and mlb) and not self.c.custom_serial
        if not (serial and mlb):
            serial, mlb = self._macserial(ocpkg, model)
        system_uuid = self.c.custom_uuid or saved.get("uuid") or str(uuid.uuid4()).upper()
        rom = self._rom() if (self.c.custom_rom or not saved.get("rom")) else bytes.fromhex(saved["rom"])
        store.parent.mkdir(parents=True, exist_ok=True)
        store.write_text(json.dumps({"model": model, "serial": serial, "mlb": mlb, "uuid": system_uuid, "rom": rom.hex()},
                                    indent=2), encoding="utf-8")
        logging.info(f"- {'Reused saved' if reused else 'Generated'} SMBIOS for {model} (serial {serial[:4]}…)")
        return {
            "SystemProductName": model,
            "SystemSerialNumber": serial,
            "MLB": mlb,
            "SystemUUID": system_uuid,
            "ROM": rom,
        }

    def _macserial(self, ocpkg: Path, model: str):
        binary = _host_binary(ocpkg / "Utilities" / "macserial", "macserial")
        if binary is None:
            raise BuildError("macserial not found for this OS in OpenCorePkg/Utilities")
        out = subprocess.run([str(binary), "-m", model, "-g", "-n", "1"], capture_output=True, text=True, timeout=30,
                             creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)).stdout
        m = re.search(r"^\s*([A-Z0-9]{12})\s*\|\s*([A-Z0-9]{14,17})\s*$", out, re.M)
        if not m:
            raise BuildError(f"macserial returned no serial for {model}: {out.strip()[:200]}")
        return m.group(1), m.group(2)

    def _rom(self) -> bytes:
        value = (self.c.custom_rom or self.hw.mac_address or "").replace(":", "").replace("-", "")
        if re.fullmatch(r"[0-9A-Fa-f]{12}", value):
            return bytes.fromhex(value)
        # Random, locally administered unicast MAC
        rom = bytearray(secrets.token_bytes(6))
        rom[0] = (rom[0] & 0xFC) | 0x02
        return bytes(rom)

    # ---- checks ----

    def _validate(self, ocpkg: Path, config_path: Path) -> None:
        binary = _host_binary(ocpkg / "Utilities" / "ocvalidate", "ocvalidate")
        if binary is None:
            logging.info("- ocvalidate not available on this OS, skipping validation")
            return
        result = subprocess.run([str(binary), str(config_path)], capture_output=True, text=True, timeout=60,
                                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        self.validation_output = (result.stdout + result.stderr).strip()
        if result.returncode != 0:
            logging.info(self.validation_output)
            raise BuildError("ocvalidate reported problems with the generated config.plist")
        logging.info("- ocvalidate: config.plist is valid")

    def _write_report(self, folder: Path) -> None:
        p = self.plan
        lines = [
            f"OpenCore Modernity Patcher {self.c.patcher_version} build report",
            "",
            f"Machine:   {self.hw.short_model()}",
            f"CPU:       {self.hw.summary()}",
            f"Platform:  {p.platform}",
            f"SMBIOS:    {p.smbios}",
            f"Target:    {os_data.label(p.target_os)}",
            f"Boot-args: {' '.join(p.boot_args)}",
            "",
            "Kexts:     " + ", ".join(kext_data.load_order(p.kexts)),
            "ACPI:      " + ", ".join(p.acpi_ocpkg + p.acpi_dortania),
            "Drivers:   " + ", ".join(p.drivers),
            "",
        ]
        lines += [f"WARNING: {w}" for w in p.warnings]
        lines += [f"Note: {n}" for n in p.notes]
        (folder / "BuildReport.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")

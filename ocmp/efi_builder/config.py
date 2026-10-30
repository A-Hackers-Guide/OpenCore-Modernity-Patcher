"""
config.py: Turn a BuildPlan into config.plist

Starts from the Sample.plist shipped in the same OpenCorePkg release, so
every key exists and has the right type for that OpenCore version, then
clears the sample entries and fills in our own.
"""

import copy
import plistlib
import logging
from pathlib import Path
from typing import List

from .planner import BuildPlan


class ConfigBuilder:

    def __init__(self, sample_plist: Path, plan: BuildPlan, constants) -> None:
        with open(sample_plist, "rb") as f:
            self.config = plistlib.load(f)
        self.plan = plan
        self.c = constants
        # Entry templates, so keys added in newer OpenCore versions come along
        self.templates = {
            "acpi":   dict(self.config["ACPI"]["Add"][0]),
            "kext":   dict(self.config["Kernel"]["Add"][0]),
            "driver": dict(self.config["UEFI"]["Drivers"][0]),
        }

    def _entry(self, kind: str, **values) -> dict:
        entry = copy.deepcopy(self.templates[kind])
        for key in values:
            if key not in entry:
                raise KeyError(f"{key} is not a valid {kind} key for this OpenCore version")
        entry.update(values)
        return entry

    def build(self, kext_entries: List[dict], acpi_files: List[str], amd_patches: List[dict],
              smbios: dict) -> dict:
        c = self.config
        self._reset()

        # ACPI
        c["ACPI"]["Add"] = [self._entry("acpi", Comment=name, Enabled=True, Path=name) for name in acpi_files]

        # Booter
        c["Booter"]["Quirks"].update(self.plan.booter_quirks)

        # DeviceProperties
        c["DeviceProperties"]["Add"] = copy.deepcopy(self.plan.device_properties)

        # Kernel
        c["Kernel"]["Add"] = [self._entry("kext", **entry) for entry in kext_entries]
        c["Kernel"]["Block"] = self.plan.kernel_block
        c["Kernel"]["Patch"] = amd_patches
        c["Kernel"]["Quirks"].update(self.plan.kernel_quirks)
        for key, value in self.plan.kernel_emulate.items():
            c["Kernel"]["Emulate"][key] = value

        # Misc
        boot = c["Misc"]["Boot"]
        boot["HideAuxiliary"] = True
        boot["ShowPicker"]    = self.c.showpicker
        boot["Timeout"]       = int(self.c.oc_timeout)
        boot["PickerMode"]    = "External" if self.c.opencanopy else "Builtin"
        boot["PickerAttributes"] = 17 if self.c.opencanopy else boot.get("PickerAttributes", 17)
        debug = c["Misc"]["Debug"]
        debug["AppleDebug"]      = self.c.opencore_debug
        debug["ApplePanic"]      = True
        debug["DisableWatchDog"] = True
        debug["Target"]          = 67 if self.c.opencore_debug else 3
        sec = c["Misc"]["Security"]
        sec["AllowSetDefault"]      = True
        sec["BlacklistAppleUpdate"] = True
        sec["ExposeSensitiveData"]  = 6
        sec["ScanPolicy"]           = 0
        sec["Vault"]                = "Secure" if self.c.vault else "Optional"
        sec["SecureBootModel"]      = self.plan.secure_boot_model
        c["Misc"]["Tools"] = []
        c["Misc"]["Entries"] = []

        # NVRAM
        apple = "7C436110-AB2A-4BBB-A880-FE41995C9F82"
        nvram = c["NVRAM"]["Add"].setdefault(apple, {})
        nvram["boot-args"] = " ".join(self.plan.boot_args)
        nvram["csr-active-config"] = bytes.fromhex("00000000" if self.c.sip_status else "03080000")
        nvram["prev-lang:kbd"] = b"en-US:0"
        nvram.pop("run-efi-updater", None)
        c["NVRAM"]["Delete"][apple] = sorted(set(c["NVRAM"]["Delete"].get(apple, []) + ["boot-args", "csr-active-config", "prev-lang:kbd"]))
        c["NVRAM"]["WriteFlash"] = True

        # PlatformInfo
        generic = c["PlatformInfo"]["Generic"]
        generic.update(smbios)
        c["PlatformInfo"]["UpdateSMBIOSMode"] = self.plan.update_smbios_mode
        c["PlatformInfo"]["Automatic"] = True
        c["PlatformInfo"]["UpdateDataHub"] = True
        c["PlatformInfo"]["UpdateNVRAM"] = True
        c["PlatformInfo"]["UpdateSMBIOS"] = True

        # UEFI
        c["UEFI"]["Drivers"] = [self._driver(d) for d in self.plan.drivers]
        c["UEFI"]["Quirks"].update(self.plan.uefi_quirks)
        c["UEFI"]["ConnectDrivers"] = True
        c["UEFI"]["Output"]["ProvideConsoleGop"] = True

        return c

    def _reset(self) -> None:
        c = self.config
        c["ACPI"]["Add"] = []
        c["ACPI"]["Delete"] = []
        c["ACPI"]["Patch"] = []
        c["Booter"]["MmioWhitelist"] = []
        c["Booter"]["Patch"] = []
        c["DeviceProperties"]["Add"] = {}
        c["DeviceProperties"]["Delete"] = {}
        c["Kernel"]["Add"] = []
        c["Kernel"]["Block"] = []
        c["Kernel"]["Force"] = []
        c["Kernel"]["Patch"] = []
        c["UEFI"]["ReservedMemory"] = []
        # Sample.plist ships a few illustrative NVRAM vars; keep only Apple/OC defaults
        for guid in list(c["NVRAM"]["Add"].keys()):
            if guid.startswith("4D1FDA02"):     # OC_VENDOR_GUID: keep OpenCore's own vars
                continue
            if guid != "7C436110-AB2A-4BBB-A880-FE41995C9F82":
                c["NVRAM"]["Add"].pop(guid)

    def _driver(self, name: str) -> dict:
        return self._entry("driver", Arguments="", Comment=name, Enabled=True, LoadEarly=name == "OpenVariableRuntimeDxe.efi", Path=name)


def amd_patches(patches_plist: bytes, core_count: int, target_os: int) -> List[dict]:
    """
    Load AMD_Vanilla patches.plist and fill in the core count

    The four "Force cpuid_cores_per_package" patches carry the core count in
    byte 1 of Replace (the immediate of a mov), per the AMD_Vanilla README.
    """
    data = plistlib.loads(patches_plist)
    patches = []
    for patch in data["Kernel"]["Patch"]:
        patch = dict(patch)
        if "cpuid_cores_per_package" in patch.get("Comment", ""):
            replace = bytearray(patch["Replace"])
            replace[1] = core_count & 0xFF
            patch["Replace"] = bytes(replace)
        patches.append(patch)
    logging.info(f"- Loaded {len(patches)} AMD_Vanilla patches (core count {core_count})")
    return patches

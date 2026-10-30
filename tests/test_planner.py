"""
Planner and detection tests (offline: no downloads)
"""

import plistlib
from pathlib import Path

import pytest

from ocmp import constants, hardware
from ocmp.datasets import os_data
from ocmp.efi_builder import planner
from ocmp.efi_builder.config import amd_patches

PROFILES = Path(__file__).resolve().parent.parent / "examples" / "profiles"


def plan_for(name: str, target: int):
    c = constants.Constants()
    c.target_os = target
    return planner.Planner(hardware.HardwareProfile.load(PROFILES / f"{name}.json"), c).plan()


def test_coffee_lake_desktop_sequoia():
    p = plan_for("intel-coffeelake-rx580", os_data.os_data.sequoia)
    assert p.platform == planner.Platform.INTEL_DESKTOP
    assert p.smbios == "iMac19,1"
    assert p.kexts[:2] == ["Lilu", "VirtualSMC"]
    assert "IntelMausi" in p.kexts
    # dGPU present -> iGPU headless platform-id
    assert p.device_properties["PciRoot(0x0)/Pci(0x2,0x0)"]["AAPL,ig-platform-id"] == bytes.fromhex("0300913E")


@pytest.mark.parametrize("profile,expected", [
    ("intel-coffeelake-rx580", "iMac20,1"),
    ("amd-ryzen5600x-rx6600", "MacPro7,1"),
    ("intel-cometlake-laptop", "MacBookPro16,1"),
])
def test_tahoe_uses_tahoe_capable_smbios(profile, expected):
    p = plan_for(profile, os_data.os_data.tahoe)
    assert p.smbios == expected
    assert "-no_compat_check" not in p.boot_args


def test_amd_desktop():
    p = plan_for("amd-ryzen5600x-rx6600", os_data.os_data.tahoe)
    assert p.amd_patches and p.amd_core_count == 6
    assert "SSDT-CPUR.aml" in p.acpi_dortania          # B550 board
    assert p.kernel_block[0]["Identifier"] == "com.apple.driver.AppleMCEReporter"
    assert "agdpmod=pikera" in p.boot_args               # Navi 23
    assert {"itlwm", "IntelBluetoothFirmware", "LucyRTL8125Ethernet"} <= set(p.kexts)


def test_kvm():
    p = plan_for("kvm-amd-host", os_data.os_data.sequoia)
    assert p.platform == planner.Platform.KVM
    assert p.amd_patches
    assert "vmhide=on" in p.boot_args and "RestrictEvents" in p.kexts


def test_unsupported_gpu_is_refused():
    with pytest.raises(planner.PlanError, match="No usable GPU"):
        plan_for("intel-alderlake-rtx3060", os_data.os_data.sequoia)


def test_amd_core_count_patch():
    data = plistlib.dumps({"Kernel": {"Patch": [
        {"Comment": "algrey | Force cpuid_cores_per_package to constant (user-specified) | 13.3+", "Replace": bytes.fromhex("ba00000000")},
        {"Comment": "other", "Replace": bytes.fromhex("9090")},
    ]}})
    patches = amd_patches(data, 12, os_data.os_data.tahoe)
    assert patches[0]["Replace"] == bytes.fromhex("ba0c000000")
    assert patches[1]["Replace"] == bytes.fromhex("9090")


def test_windows_probe_parse():
    data = {
        "Manufacturer": "GenuineIntel", "Name": "Intel(R) Core(TM) i5-10400 CPU @ 2.90GHz",
        "Description": "Intel64 Family 6 Model 165 Stepping 3", "Cores": 6, "Threads": 12,
        "SysVendor": "Micro-Star International Co., Ltd.", "SysModel": "MS-7C82", "Board": "B460M PRO-VDH WIFI",
        "Chassis": [3], "Batteries": 0, "Mac": "00-D8-61-AA-BB-CC",
        "Devices": [
            {"Name": "Intel(R) UHD Graphics 630", "DeviceID": "PCI\\VEN_8086&DEV_9BC8&SUBSYS_7C821462&REV_03", "PNPClass": "Display", "Location": "PCIROOT(0)#PCI(0200)"},
            {"Name": "Intel(R) Wi-Fi 6 AX201 160MHz", "DeviceID": "PCI\\VEN_8086&DEV_06F0&SUBSYS_02748086", "PNPClass": "Net", "Location": ""},
            {"Name": "Intel(R) Ethernet Connection (11) I219-V", "DeviceID": "PCI\\VEN_8086&DEV_0D4D&SUBSYS_7C821462", "PNPClass": "Net", "Location": ""},
        ],
    }
    p = hardware.WindowsProbe.parse(data)
    assert p.cpu_generation == 10        # Comet Lake
    assert p.igpu.location == "PciRoot(0x0)/Pci(0x2,0x0)"
    assert [n.kind for n in p.nics] == ["wifi", "ethernet"]
    assert p.mac_address == "00:D8:61:AA:BB:CC"
    assert not p.is_laptop and not p.is_vm


def test_placeholder_model_uses_board():
    p = hardware.HardwareProfile(manufacturer="ASUS", model="System Product Name", board="ROG STRIX B550-F GAMING")
    assert p.short_model() == "ASUS ROG STRIX B550-F GAMING"

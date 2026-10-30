"""
kext_data.py: Where each kext comes from

Each entry: the GitHub repo that releases it, how to pick the release
asset, and (optionally) which plug-ins inside the bundle to enable.
Load order follows this dictionary's order, so Lilu must stay first.
"""

def _release(prefix: str):
    return lambda name: name.startswith(prefix) and name.endswith("RELEASE.zip")


def _exact(asset: str):
    return lambda name: name == asset


def _startswith(prefix: str):
    return lambda name: name.startswith(prefix) and name.endswith(".zip")


KEXTS = {
    # Lilu must load before all of its plug-ins
    "Lilu":                       {"repo": "acidanthera/Lilu",          "asset": _release("Lilu-")},
    "VirtualSMC":                 {"repo": "acidanthera/VirtualSMC",    "asset": _release("VirtualSMC-")},
    "SMCProcessor":               {"repo": "acidanthera/VirtualSMC",    "asset": _release("VirtualSMC-")},
    "SMCSuperIO":                 {"repo": "acidanthera/VirtualSMC",    "asset": _release("VirtualSMC-")},
    "SMCBatteryManager":          {"repo": "acidanthera/VirtualSMC",    "asset": _release("VirtualSMC-")},
    "WhateverGreen":              {"repo": "acidanthera/WhateverGreen", "asset": _release("WhateverGreen-")},
    "NootedRed":                  {"repo": "ChefKissInc/NootedRed",     "asset": _release("NootedRed-")},
    "AppleALC":                   {"repo": "acidanthera/AppleALC",      "asset": _release("AppleALC-")},
    "RestrictEvents":             {"repo": "acidanthera/RestrictEvents","asset": _release("RestrictEvents-")},
    "CryptexFixup":               {"repo": "acidanthera/CryptexFixup",  "asset": _release("CryptexFixup-")},
    "NVMeFix":                    {"repo": "acidanthera/NVMeFix",       "asset": _release("NVMeFix-")},
    "CpuTopologyRebuild":         {"repo": "b00t0x/CpuTopologyRebuild", "asset": _release("CpuTopologyRebuild-")},
    "AMDRyzenCPUPowerManagement": {"repo": "trulyspinach/SMCAMDProcessor", "asset": _exact("AMDRyzenCPUPowerManagement.kext.zip")},
    "SMCAMDProcessor":            {"repo": "trulyspinach/SMCAMDProcessor", "asset": _exact("SMCAMDProcessor.kext.zip")},
    # Networking
    "IntelMausi":                 {"repo": "acidanthera/IntelMausi",    "asset": _release("IntelMausi-")},
    "RealtekRTL8111":             {"repo": "Mieze/RTL8111_driver_for_OS_X", "asset": _startswith("RealtekRTL8111-")},
    "LucyRTL8125Ethernet":        {"repo": "Mieze/LucyRTL8125Ethernet", "asset": _startswith("LucyRTL8125Ethernet-")},
    "AtherosE2200Ethernet":       {"repo": "Mieze/AtherosE2200Ethernet","asset": _startswith("AtherosE2200Ethernet-")},
    "itlwm":                      {"repo": "OpenIntelWireless/itlwm",   "asset": _startswith("itlwm_")},
    "IntelBluetoothFirmware":     {"repo": "OpenIntelWireless/IntelBluetoothFirmware", "asset": _startswith("IntelBluetooth-")},
    "IntelBTPatcher":             {"repo": "OpenIntelWireless/IntelBluetoothFirmware", "asset": _startswith("IntelBluetooth-")},
    "BlueToolFixup":              {"repo": "acidanthera/BrcmPatchRAM",  "asset": _release("BrcmPatchRAM-")},
    # Input / USB
    "VoodooPS2Controller":        {"repo": "acidanthera/VoodooPS2",     "asset": _release("VoodooPS2Controller-"),
                                   "plugins": ["VoodooPS2Keyboard", "VoodooPS2Mouse", "VoodooPS2Trackpad", "VoodooInput"]},
    "USBToolBox":                 {"repo": "USBToolBox/kext",           "asset": _release("USBToolBox-")},
}


def load_order(names) -> list:
    wanted = set(names)
    return [name for name in KEXTS if name in wanted]

"""
igpu_data.py: Intel iGPU framebuffer settings (from the Dortania guide)

Values are the raw little-endian bytes OpenCore expects in DeviceProperties.
"""

from .os_data import os_data
from .cpu_data import Intel

IGPU_PATH = "PciRoot(0x0)/Pci(0x2,0x0)"

# generation -> newest macOS with native iGPU drivers
IGPU_MAX_OS = {
    Intel.haswell:     os_data.monterey,
    Intel.broadwell:   os_data.monterey,
    Intel.skylake:     os_data.monterey,
    Intel.kaby_lake:   os_data.ventura,
    Intel.coffee_lake: os_data.tahoe,
    Intel.comet_lake:  os_data.tahoe,
    Intel.ice_lake:    os_data.tahoe,
}

# generation -> (desktop with display, desktop headless, laptop)
PLATFORM_IDS = {
    Intel.haswell:     ("0300220D", "04001204", "0600260A"),
    Intel.broadwell:   ("07002216", "04001616", "06002616"),
    Intel.skylake:     ("00001219", "01001219", "00001619"),
    Intel.kaby_lake:   ("00001259", "03001259", "00001B59"),
    Intel.coffee_lake: ("07009B3E", "0300913E", "0900A53E"),
    Intel.comet_lake:  ("07009B3E", "0300C89B", "0900A53E"),
    Intel.ice_lake:    (None,       None,       "0000528A"),
}

# Laptop/desktop iGPUs Apple never shipped need a device-id spoof
DEVICE_ID_SPOOF = {
    0x3E98: "923E0000",   # UHD 630 (9th gen desktop) -> 0x3E92
    0x591E: "16590000",   # HD 615 -> HD 620
    0x5917: "16590000",   # UHD 620 (Kaby Lake R) -> HD 620
    0x3EA0: "A53E0000",   # UHD 620 (Whiskey) -> 0x3EA5
    0x9B41: "9B3E0000",   # UHD (Comet Lake U)
}


def properties(gen: int, device_id: int, laptop: bool, headless: bool) -> dict:
    ids = PLATFORM_IDS.get(gen)
    if not ids:
        return {}
    platform_id = ids[2] if laptop else (ids[1] if headless else ids[0])
    if not platform_id:
        return {}
    props = {"AAPL,ig-platform-id": bytes.fromhex(platform_id)}
    if not headless:
        # Common framebuffer fixes for desktops/laptops driving a display
        props["framebuffer-patch-enable"] = bytes.fromhex("01000000")
        props["framebuffer-stolenmem"]    = bytes.fromhex("00003001")
        if not laptop and gen in (Intel.skylake, Intel.kaby_lake):
            props["framebuffer-fbmem"]    = bytes.fromhex("00009000")
    spoof = DEVICE_ID_SPOOF.get(device_id)
    if spoof and spoof[:4].lower() != f"{device_id & 0xFF:02x}{device_id >> 8:02x}":
        props["device-id"] = bytes.fromhex(spoof)
    return props

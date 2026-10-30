"""
pci_data.py: PCI vendor/device tables for GPUs and network controllers

Each GPU entry gives the newest macOS (Darwin major) with native drivers,
plus the oldest one where relevant. None = no native support at all.
"""

from . import os_data

VENDOR_INTEL   = 0x8086
VENDOR_AMD     = 0x1002
VENDOR_NVIDIA  = 0x10DE
VENDOR_REALTEK = 0x10EC
VENDOR_ATHEROS = 0x1969
VENDOR_BROADCOM = 0x14E4
VENDOR_REDHAT  = 0x1AF4   # VirtIO
VENDOR_QEMU    = 0x1234   # QEMU std VGA
VENDOR_VMWARE  = 0x15AD


class GPUArch:
    # AMD
    POLARIS   = "Polaris"
    VEGA      = "Vega"
    NAVI10    = "Navi 10"
    NAVI14    = "Navi 14"
    NAVI21    = "Navi 21"
    NAVI22    = "Navi 22"
    NAVI23    = "Navi 23"
    NAVI24    = "Navi 24"
    RDNA3     = "RDNA 3"
    RDNA4     = "RDNA 4"
    AMD_APU   = "Vega APU"
    # NVIDIA
    KEPLER    = "Kepler"
    MAXWELL   = "Maxwell"
    PASCAL    = "Pascal"
    TURING    = "Turing"
    AMPERE    = "Ampere"
    ADA       = "Ada Lovelace"
    BLACKWELL = "Blackwell"
    # Intel
    INTEL_IGPU = "Intel iGPU"
    # Virtual
    VIRTUAL   = "Virtual"
    UNKNOWN   = "Unknown"


# arch -> (min darwin, max darwin, note)
GPU_SUPPORT = {
    GPUArch.POLARIS:   (os_data.os_data.high_sierra, os_data.os_data.tahoe, ""),
    GPUArch.VEGA:      (os_data.os_data.high_sierra, os_data.os_data.tahoe, ""),
    GPUArch.NAVI10:    (os_data.os_data.catalina,    os_data.os_data.tahoe, "Needs agdpmod=pikera"),
    GPUArch.NAVI14:    (os_data.os_data.catalina,    os_data.os_data.tahoe, "Needs agdpmod=pikera"),
    GPUArch.NAVI21:    (os_data.os_data.big_sur,     os_data.os_data.tahoe, "Needs agdpmod=pikera"),
    GPUArch.NAVI22:    (os_data.os_data.monterey,    os_data.os_data.tahoe, "12.1+; needs agdpmod=pikera"),
    GPUArch.NAVI23:    (os_data.os_data.monterey,    os_data.os_data.tahoe, "Needs agdpmod=pikera"),
    GPUArch.AMD_APU:   (os_data.os_data.catalina,    os_data.os_data.sequoia, "Via NootedRed (community kext)"),
    GPUArch.KEPLER:    (os_data.os_data.high_sierra, os_data.os_data.big_sur, "Monterey+ needs root patching"),
    GPUArch.MAXWELL:   (os_data.os_data.high_sierra, os_data.os_data.high_sierra, "Needs NVIDIA Web Drivers"),
    GPUArch.PASCAL:    (os_data.os_data.high_sierra, os_data.os_data.high_sierra, "Needs NVIDIA Web Drivers"),
    GPUArch.VIRTUAL:   (os_data.os_data.high_sierra, os_data.os_data.tahoe, "Basic framebuffer only"),
}

UNSUPPORTED_NOTE = {
    GPUArch.NAVI24:    "Navi 24 (RX 6400/6500) has no macOS drivers",
    GPUArch.RDNA3:     "RDNA 3 (RX 7000) has no macOS drivers",
    GPUArch.RDNA4:     "RDNA 4 (RX 9000) has no macOS drivers",
    GPUArch.TURING:    "NVIDIA Turing (GTX 16/RTX 20) has no macOS drivers",
    GPUArch.AMPERE:    "NVIDIA Ampere (RTX 30) has no macOS drivers",
    GPUArch.ADA:       "NVIDIA Ada (RTX 40) has no macOS drivers",
    GPUArch.BLACKWELL: "NVIDIA Blackwell (RTX 50) has no macOS drivers",
}

AMD_GPU_IDS = {
    **{d: GPUArch.POLARIS for d in (0x67C0, 0x67C4, 0x67C7, 0x67DF, 0x67E0, 0x67E3, 0x67E8, 0x67EB, 0x67EF, 0x67FF, 0x6FDF, 0x699F)},
    **{d: GPUArch.VEGA    for d in (0x6860, 0x6861, 0x6862, 0x6863, 0x6867, 0x6868, 0x686C, 0x687F, 0x66A0, 0x66A1, 0x66A2, 0x66A3, 0x66AF)},
    **{d: GPUArch.NAVI10  for d in (0x7310, 0x7312, 0x7318, 0x7319, 0x731A, 0x731B, 0x731E, 0x731F)},
    **{d: GPUArch.NAVI14  for d in (0x7340, 0x7341, 0x7347, 0x734F)},
    **{d: GPUArch.NAVI21  for d in (0x73A0, 0x73A1, 0x73A2, 0x73A3, 0x73A5, 0x73AB, 0x73AF, 0x73BF)},
    **{d: GPUArch.NAVI22  for d in (0x73C0, 0x73C1, 0x73C3, 0x73DA, 0x73DB, 0x73DC, 0x73DD, 0x73DE, 0x73DF)},
    **{d: GPUArch.NAVI23  for d in (0x73E0, 0x73E1, 0x73E3, 0x73E8, 0x73E9, 0x73EA, 0x73EB, 0x73EC, 0x73ED, 0x73EF, 0x73FF)},
    **{d: GPUArch.NAVI24  for d in (0x7420, 0x7421, 0x7422, 0x7423, 0x7424, 0x743F)},
    **{d: GPUArch.RDNA3   for d in (0x7448, 0x744C, 0x745E, 0x7460, 0x7461, 0x7470, 0x747E, 0x7480, 0x7483, 0x7489)},
    **{d: GPUArch.RDNA4   for d in (0x7550, 0x7551, 0x7590)},
    # Ryzen APUs (Raven, Picasso, Renoir, Lucienne, Cezanne, Barcelo)
    **{d: GPUArch.AMD_APU for d in (0x15D8, 0x15DD, 0x15E7, 0x1636, 0x1638, 0x164C)},
}

# NVIDIA: classify by device-id ranges (coarse but reliable enough)
def nvidia_arch(device_id: int) -> str:
    if 0x0FC0 <= device_id <= 0x12FF:
        return GPUArch.KEPLER
    if 0x1340 <= device_id <= 0x13FF or 0x1400 <= device_id <= 0x17FF:
        return GPUArch.MAXWELL
    if 0x1B00 <= device_id <= 0x1DFF:
        return GPUArch.PASCAL
    if 0x1E00 <= device_id <= 0x21FF:
        return GPUArch.TURING
    if 0x2200 <= device_id <= 0x25FF:
        return GPUArch.AMPERE
    if 0x2600 <= device_id <= 0x28FF:
        return GPUArch.ADA
    if 0x2900 <= device_id <= 0x2FFF:
        return GPUArch.BLACKWELL
    return GPUArch.UNKNOWN


def gpu_arch(vendor_id: int, device_id: int) -> str:
    if vendor_id == VENDOR_AMD:
        return AMD_GPU_IDS.get(device_id, GPUArch.UNKNOWN)
    if vendor_id == VENDOR_NVIDIA:
        return nvidia_arch(device_id)
    if vendor_id == VENDOR_INTEL:
        return GPUArch.INTEL_IGPU
    if vendor_id in (VENDOR_REDHAT, VENDOR_QEMU, VENDOR_VMWARE):
        return GPUArch.VIRTUAL
    return GPUArch.UNKNOWN


def gpu_supported(arch: str, target_os: int) -> bool:
    if arch not in GPU_SUPPORT:
        return False
    low, high, _ = GPU_SUPPORT[arch]
    return low <= target_os <= high


# Ethernet: (vendor, device) -> kext name
ETHERNET_KEXTS = {
    VENDOR_INTEL: {
        # I219/I218/I217/82579/82574 (IntelMausi)
        **{d: "IntelMausi" for d in (
            0x153A, 0x153B, 0x155A, 0x1559, 0x15A0, 0x15A1, 0x15A2, 0x15A3, 0x156F, 0x1570,
            0x15B7, 0x15B8, 0x15B9, 0x15BB, 0x15BC, 0x15BD, 0x15BE, 0x15D6, 0x15D7, 0x15D8,
            0x15E3, 0x15FA, 0x15FB, 0x15FC, 0x15F9, 0x0D4C, 0x0D4D, 0x0D4E, 0x0D4F, 0x0D53,
            0x0D55, 0x1502, 0x1503, 0x10D3, 0x10F6, 0x1A1C, 0x1A1D, 0x550A, 0x550B, 0x550C,
            0x550D, 0x550E, 0x550F, 0x5510, 0x5511, 0x0DC5, 0x0DC6, 0x0DC7, 0x0DC8, 0x57A0, 0x57A1,
        )},
        # I225-V / I226-V use Apple's built-in AppleIntelI210Ethernet with a device-id spoof
        **{d: "I225" for d in (0x15F2, 0x15F3, 0x0D9F, 0x125B, 0x125C, 0x125D)},
        # I210/I211
        **{d: "AppleIntelI210Ethernet" for d in (0x1533, 0x1536, 0x1537, 0x1538, 0x157B, 0x157C, 0x1539)},
    },
    VENDOR_REALTEK: {
        0x8168: "RealtekRTL8111", 0x8161: "RealtekRTL8111", 0x8136: "RealtekRTL8111",
        0x8125: "LucyRTL8125Ethernet", 0x3000: "LucyRTL8125Ethernet",
    },
    VENDOR_ATHEROS: {
        0x1091: "AtherosE2200Ethernet", 0xE091: "AtherosE2200Ethernet", 0xE0A1: "AtherosE2200Ethernet",
        0xE0B1: "AtherosE2200Ethernet",
    },
}


def ethernet_kext(vendor_id: int, device_id: int):
    return ETHERNET_KEXTS.get(vendor_id, {}).get(device_id)


# Intel Wi-Fi supported by itlwm (AX200/201/210/211, 9260/9560/8265/8260/7265/3168 ...)
INTEL_WIFI_IDS = {
    0x2723, 0x2725, 0x51F0, 0x51F1, 0x54F0, 0x7A70, 0x7AF0, 0x7E40, 0xA0F0, 0x02F0, 0x06F0, 0x34F0,
    0x43F0, 0x3DF0, 0x2526, 0x271B, 0x271C, 0x30DC, 0x31DC, 0x9DF0, 0xA370, 0x24FD, 0x24F3, 0x24F4,
    0x24FB, 0x095A, 0x095B, 0x3165, 0x3166, 0x24F5, 0x08B1, 0x08B2, 0x08B3, 0x08B4,
}

# Broadcom Wi-Fi with native macOS drivers (Fenvi-style cards)
BROADCOM_NATIVE_WIFI = {0x43A0, 0x43A3, 0x43BA, 0x43B1, 0x4331, 0x4353, 0x4357}

"""
smbios_data.py: Mac models we can spoof, and the newest macOS each one runs
"""

from .os_data import os_data
from .cpu_data import Intel

# model -> (max darwin, description)
SMBIOS = {
    "iMac14,4":       (os_data.big_sur,  "iMac (21.5-inch, Mid 2014) - Haswell, iGPU"),
    "iMac15,1":       (os_data.big_sur,  "iMac (Retina 5K, 27-inch, Late 2014) - Haswell"),
    "iMac16,2":       (os_data.monterey, "iMac (Retina 4K, 21.5-inch, Late 2015) - Broadwell"),
    "iMac17,1":       (os_data.monterey, "iMac (Retina 5K, 27-inch, Late 2015) - Skylake"),
    "iMac18,1":       (os_data.ventura,  "iMac (21.5-inch, 2017) - Kaby Lake, iGPU"),
    "iMac18,3":       (os_data.ventura,  "iMac (Retina 5K, 27-inch, 2017) - Kaby Lake"),
    "iMac19,1":       (os_data.sequoia,  "iMac (Retina 5K, 27-inch, 2019) - Coffee Lake"),
    "iMac20,1":       (os_data.tahoe,    "iMac (Retina 5K, 27-inch, 2020) - Comet Lake"),
    "iMac20,2":       (os_data.tahoe,    "iMac (Retina 5K, 27-inch, 2020) - Comet Lake i9"),
    "iMacPro1,1":     (os_data.sequoia,  "iMac Pro (2017) - Xeon W"),
    "MacPro7,1":      (os_data.tahoe,    "Mac Pro (2019) - Xeon W"),
    "MacBookPro11,1": (os_data.big_sur,  "MacBook Pro (13-inch, Late 2013) - Haswell"),
    "MacBookPro12,1": (os_data.monterey, "MacBook Pro (13-inch, Early 2015) - Broadwell"),
    "MacBookPro13,1": (os_data.monterey, "MacBook Pro (13-inch, 2016) - Skylake"),
    "MacBookPro14,1": (os_data.ventura,  "MacBook Pro (13-inch, 2017) - Kaby Lake"),
    "MacBookPro15,2": (os_data.sequoia,  "MacBook Pro (13-inch, 2018) - Coffee Lake"),
    "MacBookPro16,1": (os_data.tahoe,    "MacBook Pro (16-inch, 2019) - Coffee Lake H"),
    "MacBookPro16,2": (os_data.tahoe,    "MacBook Pro (13-inch, 2020) - Ice Lake"),
    "MacBookPro16,3": (os_data.sequoia,  "MacBook Pro (13-inch, 2020) - Comet Lake"),
    "MacBookAir9,1":  (os_data.sequoia,  "MacBook Air (Retina, 13-inch, 2020) - Ice Lake"),
}

# Native choices, oldest-supported first. (iGPU-only, with dGPU)
INTEL_DESKTOP = {
    Intel.haswell:     ("iMac14,4", "iMac15,1"),
    Intel.broadwell:   ("iMac16,2", "iMac16,2"),
    Intel.skylake:     ("iMac17,1", "iMac17,1"),
    Intel.kaby_lake:   ("iMac18,1", "iMac18,3"),
    Intel.coffee_lake: ("iMac19,1", "iMac19,1"),
    Intel.comet_lake:  ("iMac20,1", "iMac20,1"),
    Intel.rocket_lake: (None,       "iMac20,1"),
    Intel.alder_lake:  (None,       "MacPro7,1"),
    Intel.raptor_lake: (None,       "MacPro7,1"),
    Intel.arrow_lake:  (None,       "MacPro7,1"),
    Intel.meteor_lake: (None,       "MacPro7,1"),
    Intel.haswell_e:   (None,       "iMacPro1,1"),
    Intel.broadwell_e: (None,       "iMacPro1,1"),
    Intel.skylake_x:   (None,       "iMacPro1,1"),
}

INTEL_LAPTOP = {
    Intel.haswell:     "MacBookPro11,1",
    Intel.broadwell:   "MacBookPro12,1",
    Intel.skylake:     "MacBookPro13,1",
    Intel.kaby_lake:   "MacBookPro14,1",
    Intel.coffee_lake: "MacBookPro15,2",
    Intel.comet_lake:  "MacBookPro16,3",
    Intel.ice_lake:    "MacBookAir9,1",
}

# When the native model is too old for the target macOS
LAPTOP_TAHOE = {
    Intel.coffee_lake: "MacBookPro16,1",
    Intel.comet_lake:  "MacBookPro16,1",
    Intel.ice_lake:    "MacBookPro16,2",
}


def max_os(model: str) -> int:
    return SMBIOS[model][0]


def supports(model: str, target_os: int) -> bool:
    return model in SMBIOS and SMBIOS[model][0] >= target_os

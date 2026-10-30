"""
cpu_data.py: CPU generations, keyed by CPUID family/model

Intel generations follow the Dortania OpenCore Install Guide's naming.
"""

import enum


class Intel(enum.IntEnum):
    unknown       = 0
    penryn        = 1   # Core 2 and older: unsupported
    nehalem       = 2
    sandy_bridge  = 3
    ivy_bridge    = 4
    haswell       = 5
    broadwell     = 6
    skylake       = 7
    kaby_lake     = 8
    coffee_lake   = 9
    comet_lake    = 10
    ice_lake      = 11
    rocket_lake   = 12
    alder_lake    = 13
    raptor_lake   = 14
    meteor_lake   = 15
    arrow_lake    = 16
    haswell_e     = 20
    broadwell_e   = 21
    skylake_x     = 22  # Skylake-X / Cascade Lake-X


class AMD(enum.IntEnum):
    unknown   = 0
    bulldozer = 0x15
    jaguar    = 0x16
    zen       = 0x17    # Zen, Zen+, Zen 2
    zen3_4    = 0x19    # Zen 3, Zen 4
    zen5      = 0x1A


# family 6 model -> generation
INTEL_MODELS = {
    0x17: Intel.penryn,       0x1D: Intel.penryn,
    0x1A: Intel.nehalem,      0x1E: Intel.nehalem,     0x1F: Intel.nehalem,
    0x25: Intel.nehalem,      0x2C: Intel.nehalem,     0x2E: Intel.nehalem,
    0x2A: Intel.sandy_bridge, 0x2D: Intel.sandy_bridge,
    0x3A: Intel.ivy_bridge,   0x3E: Intel.ivy_bridge,
    0x3C: Intel.haswell,      0x45: Intel.haswell,     0x46: Intel.haswell,
    0x3F: Intel.haswell_e,
    0x3D: Intel.broadwell,    0x47: Intel.broadwell,
    0x4F: Intel.broadwell_e,  0x56: Intel.broadwell_e,
    0x4E: Intel.skylake,      0x5E: Intel.skylake,
    0x55: Intel.skylake_x,
    0x8E: Intel.kaby_lake,    # refined below by stepping
    0x9E: Intel.kaby_lake,    # refined below by stepping
    0xA5: Intel.comet_lake,   0xA6: Intel.comet_lake,
    0x7D: Intel.ice_lake,     0x7E: Intel.ice_lake,
    0xA7: Intel.rocket_lake,
    0x97: Intel.alder_lake,   0x9A: Intel.alder_lake,  0xBE: Intel.alder_lake,
    0xB7: Intel.raptor_lake,  0xBA: Intel.raptor_lake, 0xBF: Intel.raptor_lake,
    0xAA: Intel.meteor_lake,  0xAC: Intel.meteor_lake,
    0xC5: Intel.arrow_lake,   0xC6: Intel.arrow_lake,  0xBD: Intel.arrow_lake,
}

NAMES = {
    Intel.unknown: "Unknown Intel", Intel.penryn: "Penryn", Intel.nehalem: "Nehalem/Westmere",
    Intel.sandy_bridge: "Sandy Bridge", Intel.ivy_bridge: "Ivy Bridge", Intel.haswell: "Haswell",
    Intel.broadwell: "Broadwell", Intel.skylake: "Skylake", Intel.kaby_lake: "Kaby Lake",
    Intel.coffee_lake: "Coffee Lake", Intel.comet_lake: "Comet Lake", Intel.ice_lake: "Ice Lake",
    Intel.rocket_lake: "Rocket Lake", Intel.alder_lake: "Alder Lake", Intel.raptor_lake: "Raptor Lake",
    Intel.meteor_lake: "Meteor Lake", Intel.arrow_lake: "Arrow Lake", Intel.haswell_e: "Haswell-E",
    Intel.broadwell_e: "Broadwell-E", Intel.skylake_x: "Skylake-X/Cascade Lake-X",
}

AMD_NAMES = {
    AMD.unknown: "Unknown AMD", AMD.bulldozer: "Bulldozer (15h)", AMD.jaguar: "Jaguar (16h)",
    AMD.zen: "Zen/Zen+/Zen 2 (17h)", AMD.zen3_4: "Zen 3/Zen 4 (19h)", AMD.zen5: "Zen 5 (1Ah)",
}

HEDT = (Intel.haswell_e, Intel.broadwell_e, Intel.skylake_x)


def intel_generation(family: int, model: int, stepping: int = 0) -> Intel:
    if family != 6:
        return Intel.unknown
    gen = INTEL_MODELS.get(model, Intel.unknown)
    if model == 0x9E and stepping >= 10:
        return Intel.coffee_lake        # 8th/9th gen desktop
    if model == 0x8E:
        if stepping >= 12:
            return Intel.comet_lake     # Comet/Whiskey/Amber mobile
        if stepping >= 10:
            return Intel.coffee_lake    # Coffee/Whiskey mobile
    return gen


def amd_generation(family: int) -> AMD:
    try:
        return AMD(family)
    except ValueError:
        return AMD.unknown


def generation_name(vendor: str, gen: int) -> str:
    if vendor == "AMD":
        return AMD_NAMES.get(AMD(gen) if gen in AMD._value2member_map_ else AMD.unknown, "Unknown AMD")
    return NAMES.get(Intel(gen) if gen in Intel._value2member_map_ else Intel.unknown, "Unknown Intel")

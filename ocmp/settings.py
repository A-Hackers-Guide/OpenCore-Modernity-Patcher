"""
settings.py: Persist user settings between launches (JSON in the data directory)
"""

import json
import logging

# Constants attributes that the Settings window can change and we keep
PERSISTED = [
    "target_os", "custom_smbios", "verbose_debug", "kext_debug", "opencore_debug", "showpicker",
    "oc_timeout", "opencanopy", "sip_status", "secure_boot_model", "vault", "cfg_lock_unlocked",
    "resizable_bar", "disable_dgpu", "alc_layout_id", "include_wifi", "include_bluetooth",
    "usb_toolbox", "extra_boot_args",
]


def load(c) -> None:
    try:
        data = json.loads(c.settings_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return
    for key in PERSISTED:
        if key in data and isinstance(data[key], type(getattr(c, key))):
            setattr(c, key, data[key])


def save(c) -> None:
    try:
        c.ensure_paths()
        c.settings_path.write_text(json.dumps({key: getattr(c, key) for key in PERSISTED}, indent=2), encoding="utf-8")
    except OSError:
        logging.exception("Failed to save settings")

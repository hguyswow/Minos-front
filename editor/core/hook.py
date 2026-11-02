"""Pandora auto-hook inspection module (read-only)."""
import os
from dataclasses import dataclass

from editor.core.card import validate_card_path

HOOK_OFFSET = 0xE9C24
HOOK_STRING = b"sh /mnt/sdcard/pandory/auto.sh"


@dataclass
class HookStatus:
    pandory_bin_exists: bool
    hook_installed: bool
    auto_sh_exists: bool
    patch_txt_exists: bool
    details: str


def check_hook(card_path: str) -> HookStatus:
    """Check the status of the auto-patch hook on the card (read-only).
    - Checks whether pandory/pandory exists.
    - Inspects offset 0xe9c24 for the hook command string.
    - Checks whether auto.sh and patch.txt exist.
    Never modifies any file.
    Returns HookStatus.
    """
    card_path = validate_card_path(card_path)

    pandory_bin = os.path.join(card_path, "pandory", "pandory")
    auto_sh = os.path.join(card_path, "pandory", "auto.sh")
    patch_txt = os.path.join(card_path, "pandory", "patch.txt")

    bin_exists = os.path.isfile(pandory_bin)
    auto_exists = os.path.isfile(auto_sh)
    patch_exists = os.path.isfile(patch_txt)
    hook_installed = False
    details_list = []

    if bin_exists:
        try:
            with open(pandory_bin, "rb") as f:
                f.seek(HOOK_OFFSET)
                chunk = f.read(len(HOOK_STRING))
                if chunk == HOOK_STRING:
                    hook_installed = True
        except Exception as e:
            hook_installed = False
            details_list.append(f"Error reading binary: {e}")
    else:
        details_list.append("pandory binary not found")

    if hook_installed:
        details_list.append("Hook string detected at 0xe9c24")
    elif bin_exists:
        details_list.append("Original or unpatched pandory binary")

    if not auto_exists:
        details_list.append("auto.sh missing")
    if not patch_exists:
        details_list.append("patch.txt missing")

    return HookStatus(
        pandory_bin_exists=bin_exists,
        hook_installed=hook_installed,
        auto_sh_exists=auto_exists,
        patch_txt_exists=patch_exists,
        details="; ".join(details_list) if details_list else "Hook operational",
    )


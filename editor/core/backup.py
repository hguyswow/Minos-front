"""Backup and safe write module."""
import os
import shutil


def get_backup_path(target_path: str) -> str:
    """Return next available backup path (.bak, .bak1, .bak2, ...)."""
    base = target_path + ".bak"
    if not os.path.exists(base):
        return base
    i = 1
    while True:
        candidate = f"{base}{i}"
        if not os.path.exists(candidate):
            return candidate
        i += 1


def write_with_backup(target_path: str, data: str | bytes, *, forbid_nul: bool = False) -> str | None:
    """Write data to target_path with backup of existing file.
    - If forbid_nul is True and data contains NUL, raises ValueError without modifying file.
    - If target_path does not exist: writes data, returns None.
    - If target_path exists and content is identical: does nothing, returns None.
    - If target_path exists and content differs: backs up existing to .bak/.bakN, writes data, returns backup path.
    - Text (str) is always encoded as UTF-8 with LF line endings.
    """
    if forbid_nul:
        if isinstance(data, str) and "\x00" in data:
            raise ValueError("NUL character is forbidden in data.")
        if isinstance(data, (bytes, bytearray)) and b"\x00" in data:
            raise ValueError("NUL byte is forbidden in data.")

    if isinstance(data, str):
        # Normalize newlines to LF only
        text = data.replace("\r\n", "\n").replace("\r", "\n")
        raw = text.encode("utf-8")
    else:
        raw = bytes(data)

    backup_path = None
    if os.path.exists(target_path):
        with open(target_path, "rb") as f:
            existing = f.read()
        if existing == raw:
            return None
        backup_path = get_backup_path(target_path)
        shutil.copy2(target_path, backup_path)

    parent = os.path.dirname(os.path.abspath(target_path))
    if parent and not os.path.exists(parent):
        os.makedirs(parent, exist_ok=True)

    with open(target_path, "wb") as f:
        f.write(raw)

    return backup_path


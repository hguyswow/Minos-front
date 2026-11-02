"""Card validation module."""
import os


class CardValidationError(Exception):
    """Raised when the card path or structure is invalid."""
    pass


def validate_card_path(path: str) -> str:
    """Validate Pandora card path.
    Rejects:
      - Empty or non-string input
      - System drive root (e.g. C:, C:\\, %SystemDrive%)
      - Missing essential folders/files (pandory/pandory.xml, roms/, roms_pandory/)
    Returns normalized absolute path.
    """
    if not path or not isinstance(path, str):
        raise CardValidationError("Card path is required.")

    clean_p = path.strip().rstrip("\\/")
    if clean_p.upper() == "C:":
        raise CardValidationError("System drive cannot be used.")

    abs_p = os.path.abspath(path)
    norm = os.path.normcase(abs_p)

    sys_drive = os.path.normcase(os.environ.get("SystemDrive", "C:"))
    if not sys_drive.endswith("\\"):
        sys_drive_root = sys_drive + "\\"
    else:
        sys_drive_root = sys_drive

    if norm == os.path.normcase(sys_drive_root) or norm == os.path.normcase("C:\\"):
        raise CardValidationError("System drive root cannot be used.")

    xml_p = os.path.join(abs_p, "pandory", "pandory.xml")
    roms_p = os.path.join(abs_p, "roms")
    rp_p = os.path.join(abs_p, "roms_pandory")

    if not os.path.isfile(xml_p) or not os.path.isdir(roms_p) or not os.path.isdir(rp_p):
        raise CardValidationError(f"Invalid card structure at: {abs_p}")

    return abs_p


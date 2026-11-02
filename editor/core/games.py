"""Game installation and rom management module."""
import os
import re
import shutil
from dataclasses import dataclass

from editor.core.backup import write_with_backup
from editor.core.card import validate_card_path
from editor.core.names import pretty

BAD_EXTS = {".txt", ".exe", ".bat", ".cmd", ".dll", ".com", ".scr", ".msi"}


@dataclass
class AddGameResult:
    dest_path: str
    folder: str
    filename: str
    title: str


def add_game(
    card_path: str,
    src_file: str,
    target_folder: str,
    display_title: str | None = None
) -> AddGameResult:
    """Add a game ROM to the card under roms_pandory/<target_folder>.
    - Validates card path.
    - Validates that target_folder is defined in pandory.xml.
    - Checks forbidden extensions (.txt, .exe, .bat, etc.).
    - Refuses to overwrite existing files (FileExistsError).
    - Copies src_file using shutil.copy2 (source is preserved).
    - Appends/updates entry in names_map.txt via write_with_backup.
    Returns AddGameResult.
    """
    card_path = validate_card_path(card_path)

    if not os.path.isfile(src_file):
        raise FileNotFoundError(f"Source file not found: {src_file}")

    xml_p = os.path.join(card_path, "pandory", "pandory.xml")
    with open(xml_p, "r", encoding="utf-8", errors="replace") as f:
        xml = f.read()

    allowed_folders = set(re.findall(r'<emulator [^>]*folder="([^"]+)"', xml))
    if target_folder not in allowed_folders:
        raise ValueError(f"Folder '{target_folder}' is not registered in pandory.xml")

    filename = os.path.basename(src_file)
    ext = os.path.splitext(filename)[1].lower()
    if ext in BAD_EXTS:
        raise ValueError(f"Extension '{ext}' is forbidden.")

    dest_dir = os.path.join(card_path, "roms_pandory", target_folder)
    dest_path = os.path.join(dest_dir, filename)

    if os.path.exists(dest_path):
        raise FileExistsError(f"Target file already exists: {dest_path}")

    # All validations passed; ensure target directory exists and copy
    os.makedirs(dest_dir, exist_ok=True)
    shutil.copy2(src_file, dest_path)

    title = display_title if display_title is not None else pretty(os.path.splitext(filename)[0])

    # Update names_map.txt
    mp = os.path.join(card_path, "pandory", "names_map.txt")
    lines = []
    found = False
    if os.path.exists(mp):
        with open(mp, "r", encoding="utf-8") as f:
            for line in f:
                stripped = line.rstrip("\r\n")
                if "|" in stripped and not stripped.startswith("#"):
                    k, v = stripped.split("|", 1)
                    if k.strip() == filename:
                        lines.append(f"{filename} | {title}")
                        found = True
                        continue
                lines.append(stripped)
    else:
        lines.append("# file name | title shown in the menu (edit the title; keep it under about 24 characters)")

    if not found:
        lines.append(f"{filename} | {title}")

    write_with_backup(mp, "\n".join(lines) + "\n")

    return AddGameResult(
        dest_path=dest_path,
        folder=target_folder,
        filename=filename,
        title=title,
    )


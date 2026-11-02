"""Name patch generator and list module."""
import os
import re
from dataclasses import dataclass

from editor.core.backup import write_with_backup
from editor.core.card import validate_card_path

BS = chr(92)
STOCK = 9882                 # menu's visible stock entries (live value)
NAME_BASE = 0xBB9A3C         # live name table
REC = 0x580                  # name record size
MAX_GAMES = 240              # name table / list headroom

SYS_TAG = {                  # folder -> tag shown before the title ('' = none)
    '32x': '[32X]', 'amiga': '[AMIGA]', 'amiga1200': '[AMIGA]', 'atari2600': '[2600]', 'atarist': '[ST]',
    'gb': '[GB]', 'gba': '[GBA]', 'gbc': '[GBC]', 'gblink': '[GB]', 'genesis': '[MD]', 'pce': '[PCE]',
    'ports': '[PORT]', 'scripts': '[SCRIPT]', 'megadrive': '[MD]', 'snes': '[SFC]', 'nes': '[FC]',
}

CODE_PATCHES = [
    (0x2f618, '000'),
    (0x2f728, '000'),
    (0x2fa68, '000'),
    (0x31330, '000' + BS + '000' + BS + '240' + BS + '341'),
]


@dataclass
class PatchResult:
    patch_path: str
    games_count: int
    rows: list[tuple[int, str, str, str]]  # (menu_no, folder, shown_title, file_name)
    warnings: list[str]
    added_to_map: list[str]


def octal(bs: bytes) -> str:
    """Format bytes as 8-bit octal escapes with backslash."""
    return ''.join(BS + format(b, '03o') for b in bs)


def pretty(stem: str) -> str:
    """Make human-friendly title from filename stem."""
    return re.sub(r'[_]+', ' ', stem).strip()


def list_added_games(card_path: str, max_games: int = 240) -> tuple[list[tuple[str, str]], list[str]]:
    """List games that will be added to the menu in exact engine order.
    Returns:
      (list of (folder, file_name), warnings)
    """
    card_path = validate_card_path(card_path)
    rp = os.path.join(card_path, 'roms_pandory')
    xml_p = os.path.join(card_path, 'pandory', 'pandory.xml')
    with open(xml_p, 'r', encoding='utf-8', errors='replace') as f:
        xml = f.read()

    folders = sorted(set(re.findall(r'<emulator [^>]*folder="([^"]+)"', xml)))
    games = []
    for f in folders:
        d = os.path.join(rp, f)
        if not os.path.isdir(d):
            continue
        for name in sorted(os.listdir(d), key=lambda n: n.encode('utf-8')):
            p = os.path.join(d, name)
            if not os.path.isfile(p) or name.startswith('.') or name.lower().endswith('.txt'):
                continue
            games.append((f, name))

    warnings = []
    if len(games) > max_games:
        warnings.append(f'WARNING: {len(games)} games; only the first {max_games} get names')
        games = games[:max_games]

    return games, warnings


def load_names_map(card_path: str) -> dict[str, str]:
    """Read names_map.txt from card (read-only; never writes to card)."""
    card_path = validate_card_path(card_path)
    mp = os.path.join(card_path, 'pandory', 'names_map.txt')
    names = {}
    if os.path.exists(mp):
        with open(mp, 'r', encoding='utf-8') as f:
            for line in f:
                if '|' in line and not line.startswith('#'):
                    k, v = line.rstrip('\r\n').split('|', 1)
                    names[k.strip()] = v.strip()
    return names


def set_title(card_path: str, file_name: str, title: str) -> None:
    """Update or add a game title in names_map.txt.
    Sanitizes pipe ('|' -> '-') and newlines ('\\r\\n' -> ' ') before saving.
    """
    card_path = validate_card_path(card_path)
    sanitized = title.replace('|', '-').replace('\r', ' ').replace('\n', ' ').strip()
    if not sanitized or not sanitized.replace('-', '').strip():
        raise ValueError("Title cannot be empty after sanitization.")

    mp = os.path.join(card_path, 'pandory', 'names_map.txt')
    lines = []
    found = False
    if os.path.exists(mp):
        with open(mp, 'r', encoding='utf-8') as f:
            for line in f:
                stripped = line.rstrip('\r\n')
                if '|' in stripped and not stripped.startswith('#'):
                    k, v = stripped.split('|', 1)
                    if k.strip() == file_name:
                        lines.append(f"{file_name} | {sanitized}")
                        found = True
                        continue
                lines.append(stripped)
    else:
        lines.append('# file name | title shown in the menu (edit the title; keep it under about 24 characters)')

    if not found:
        lines.append(f"{file_name} | {sanitized}")

    write_with_backup(mp, '\n'.join(lines) + '\n')


def generate_patch(card_path: str, use_tags: bool = True, max_games: int = 240) -> PatchResult:
    """Generate patch.txt and update names_map.txt for the card.
    Returns PatchResult.
    """
    card_path = validate_card_path(card_path)
    games, warnings = list_added_games(card_path, max_games=max_games)

    mp = os.path.join(card_path, 'pandory', 'names_map.txt')
    names = load_names_map(card_path)

    added_to_map = []
    for f, name in games:
        if name not in names:
            names[name] = pretty(os.path.splitext(name)[0])
            added_to_map.append(name)

    # Save names_map.txt with write_with_backup
    map_lines = ['# file name | title shown in the menu (edit the title; keep it under about 24 characters)']
    for f, name in games:
        map_lines.append(f'{name} | {names[name]}')
    write_with_backup(mp, '\n'.join(map_lines) + '\n')

    lines = []
    rows = []
    for k, (f, name) in enumerate(games):
        title = names[name]
        tag = SYS_TAG.get(f, '') if use_tags else ''
        shown = (tag + ' ' + title).strip() if tag else title
        ko = shown.encode('utf-32le') + b'\0\0\0\0'
        en = shown.encode('ascii', 'replace') + b'\0'

        # D k slot-offset escapes: record index read live from menu's list
        lines.append('D %d %d %s' % (k, 0x340, octal(en)))
        lines.append('D %d %d %s' % (k, 0x380, octal(ko)))
        lines.append('D %d %d %s' % (k, 0x000, octal(ko)))
        lines.append('D %d %d %s' % (k, 0x0c0, octal(ko)))
        rows.append((9801 + k, f, shown, name))

    for a, e in CODE_PATCHES:
        lines.append('%d %s' % (a, BS + e))

    patch_path = os.path.join(card_path, 'pandory', 'patch.txt')
    patch_text = '\n'.join(lines) + '\n'
    write_with_backup(patch_path, patch_text, forbid_nul=True)

    return PatchResult(
        patch_path=patch_path,
        games_count=len(games),
        rows=rows,
        warnings=warnings,
        added_to_map=added_to_map,
    )

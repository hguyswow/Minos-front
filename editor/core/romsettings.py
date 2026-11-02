"""Module for managing per-game ROM and per-system emulator settings in pandory.xml.

Note on integerScale (investigated 2026-11-01, not implemented):
In pandory.orig, 'integerScale' maps to '-1' by default for RetroArch video_scale_integer.
Tristate (-1=unset/default, 0=false, 1=true) is an educated guess only.
"""
from dataclasses import dataclass
import os
from pathlib import Path
import re
from typing import Optional
import xml.etree.ElementTree as ET

from editor.core.backup import write_with_backup
from editor.core.card import validate_card_path

VALID_RATIO_STATES = ("default", "original", "full")
VALID_QUALITY_STATES = ("default", "sharp", "smooth")
VALID_STATES = VALID_RATIO_STATES  # backward compatibility
BANNED_CHARS = {'"', '<', '>', '&', '/', '\\'}


@dataclass
class RomEntry:
    name: str
    attrib: dict[str, str]
    raw_snippet: str
    broken: bool = False
    ratio: str = "default"    # "default" | "original" | "full"
    quality: str = "default"  # "default" | "sharp" | "smooth"


@dataclass
class EmulatorEntry:
    folder: str
    suffix: str
    attrib: dict[str, str]
    raw_snippet: str
    broken: bool = False
    ratio: str = "default"    # "default" | "original" | "full"
    quality: str = "default"  # "default" | "sharp" | "smooth"


def validate_file_name(file_name: str) -> None:
    if not file_name or not isinstance(file_name, str):
        raise ValueError("파일 이름이 비어 있거나 올바르지 않습니다.")
    for ch in file_name:
        if ch in BANNED_CHARS or ord(ch) < 32:
            raise ValueError(f"파일 이름에 사용할 수 없는 문자({repr(ch)})가 포함되어 있습니다.")


def validate_folder_name(folder: str) -> None:
    if not folder or not isinstance(folder, str):
        raise ValueError("기종 폴더 이름이 비어 있거나 올바르지 않습니다.")
    for ch in folder:
        if ch in BANNED_CHARS or ord(ch) < 32:
            raise ValueError(f"기종 폴더 이름에 사용할 수 없는 문자({repr(ch)})가 포함되어 있습니다.")


def mask_comments(text: str) -> str:
    """Mask comment contents with spaces while keeping total length and newlines identical."""
    def repl(m):
        full = m.group(0)
        return '<!--' + (' ' * (len(full) - 7)) + '-->'
    return re.sub(r'<!--[\s\S]*?-->', repl, text)


ROM_ELEM_PATTERN = re.compile(r'<rom\b(?:[^>"\'/]|/(?!>)|"[^"]*"|\'[^\']*\')*?(?:/>|>[\s\S]*?</rom>)')
EMULATOR_ELEM_PATTERN = re.compile(r'<emulator\b(?:[^>"\'/]|/(?!>)|"[^"]*"|\'[^\']*\')*?(?:/>|>[\s\S]*?</emulator>)')


def _parse_ratio_from_attrib(attrib: dict[str, str]) -> str:
    val = attrib.get("stretchDisplay")
    if val == "false":
        return "original"
    if val == "true":
        return "full"
    return "default"


def _parse_quality_from_attrib(attrib: dict[str, str]) -> str:
    val = attrib.get("smoothPixels")
    if val == "false":
        return "sharp"
    if val == "true":
        return "smooth"
    return "default"


def _get_pandory_xml_path(card_path: str | Path) -> Path:
    validate_card_path(card_path)
    return Path(card_path) / "pandory" / "pandory.xml"


def _update_snippet(raw: str, ratio: Optional[str] = None, quality: Optional[str] = None) -> str:
    """Update ratio (stretchDisplay) and quality (smoothPixels) in a snippet.
    Order rule: stretchDisplay comes BEFORE smoothPixels.
    """
    new_raw = raw

    # 1. Update/remove/add stretchDisplay
    if ratio is not None:
        target_val = "false" if ratio == "original" else "true" if ratio == "full" else None
        has_stretch = bool(re.search(r'stretchDisplay=(["\'])(.*?)\1', new_raw))

        if ratio == "default":
            new_raw = re.sub(r'\s+stretchDisplay=(["\'])(.*?)\1', '', new_raw)
        elif has_stretch:
            new_raw = re.sub(r'stretchDisplay=(["\'])(.*?)\1', f'stretchDisplay=\\g<1>{target_val}\\g<1>', new_raw)
        else:
            # If smoothPixels already exists, insert BEFORE smoothPixels
            m_smooth = re.search(r'\s+smoothPixels=(["\'])(.*?)\1', new_raw)
            if m_smooth:
                idx = m_smooth.start()
                new_raw = new_raw[:idx] + f' stretchDisplay="{target_val}"' + new_raw[idx:]
            else:
                m_ws = re.search(r'(?P<ws>\s*)/>$', new_raw)
                if m_ws:
                    ws = m_ws.group('ws')
                    new_raw = new_raw[:m_ws.start()] + f' stretchDisplay="{target_val}"' + ws + '/>'
                else:
                    m_gt = re.search(r'(?P<ws>\s*)>', new_raw)
                    if m_gt:
                        ws = m_gt.group('ws')
                        new_raw = new_raw[:m_gt.start()] + f' stretchDisplay="{target_val}"' + ws + new_raw[m_gt.start():]
                    else:
                        raise ValueError("설정 태그의 형식을 인식할 수 없습니다.")

    # 2. Update/remove/add smoothPixels
    if quality is not None:
        target_val = "false" if quality == "sharp" else "true" if quality == "smooth" else None
        has_smooth = bool(re.search(r'smoothPixels=(["\'])(.*?)\1', new_raw))

        if quality == "default":
            new_raw = re.sub(r'\s+smoothPixels=(["\'])(.*?)\1', '', new_raw)
        elif has_smooth:
            new_raw = re.sub(r'smoothPixels=(["\'])(.*?)\1', f'smoothPixels=\\g<1>{target_val}\\g<1>', new_raw)
        else:
            m_ws = re.search(r'(?P<ws>\s*)/>$', new_raw)
            if m_ws:
                ws = m_ws.group('ws')
                new_raw = new_raw[:m_ws.start()] + f' smoothPixels="{target_val}"' + ws + '/>'
            else:
                m_gt = re.search(r'(?P<ws>\s*)>', new_raw)
                if m_gt:
                    ws = m_gt.group('ws')
                    new_raw = new_raw[:m_gt.start()] + f' smoothPixels="{target_val}"' + ws + new_raw[m_gt.start():]
                else:
                    raise ValueError("설정 태그의 형식을 인식할 수 없습니다.")

    return new_raw


def read_rom_entries(card_path: str | Path) -> dict[str, RomEntry]:
    """Read all active <rom> elements from pandory.xml inside <roms> block."""
    xml_path = _get_pandory_xml_path(card_path)
    if not xml_path.exists():
        raise ValueError("pandory.xml 파일이 존재하지 않습니다.")

    text = xml_path.read_text(encoding="utf-8")
    masked = mask_comments(text)

    roms_open = list(re.finditer(r'<roms\b[^>]*>', masked))
    roms_close = list(re.finditer(r'</roms>', masked))
    if len(roms_open) != 1 or len(roms_close) != 1:
        raise ValueError("<roms> 구역이 올바르지 않거나 중복되어 있습니다.")

    chunk_start = roms_open[0].end()
    chunk_end = roms_close[0].start()
    chunk = masked[chunk_start:chunk_end]

    entries: dict[str, RomEntry] = {}
    for m in ROM_ELEM_PATTERN.finditer(chunk):
        raw = text[chunk_start + m.start(): chunk_start + m.end()]
        try:
            elem = ET.fromstring(raw)
            name = elem.get("name")
            if not name:
                entries[f"_broken_{m.start()}"] = RomEntry(
                    name="",
                    attrib={},
                    raw_snippet=raw,
                    broken=True,
                    ratio="default",
                    quality="default",
                )
            else:
                ratio = _parse_ratio_from_attrib(elem.attrib)
                quality = _parse_quality_from_attrib(elem.attrib)
                entries[name] = RomEntry(
                    name=name,
                    attrib=dict(elem.attrib),
                    raw_snippet=raw,
                    broken=False,
                    ratio=ratio,
                    quality=quality,
                )
        except Exception:
            m_name = re.search(r'\bname=(["\'])(.*?)\1', raw)
            name = m_name.group(2) if m_name else f"_broken_{m.start()}"
            entries[name] = RomEntry(
                name=name,
                attrib={},
                raw_snippet=raw,
                broken=True,
                ratio="default",
                quality="default",
            )

    return entries


def set_rom_ratio(card_path: str | Path, file_name: str, state: str) -> str | None:
    """Set or remove stretchDisplay for file_name in pandory.xml."""
    return set_rom_options_bulk(card_path, [file_name], ratio=state)


def set_rom_quality(card_path: str | Path, file_name: str, state: str) -> str | None:
    """Set or remove smoothPixels for file_name in pandory.xml."""
    return set_rom_options_bulk(card_path, [file_name], quality=state)


def set_rom_options_bulk(
    card_path: str | Path,
    file_names: list[str],
    ratio: Optional[str] = None,
    quality: Optional[str] = None,
) -> str | None:
    """Bulk update ratio and/or quality for multiple games in pandory.xml atomically."""
    if not file_names:
        raise ValueError("파일 목록이 비어 있습니다.")
    if ratio is None and quality is None:
        raise ValueError("변경할 화면 비율이나 화질 설정이 지정되지 않았습니다.")
    if ratio is not None and ratio not in VALID_RATIO_STATES:
        raise ValueError(f"화면 비율 설정값({ratio})이 올바르지 않습니다.")
    if quality is not None and quality not in VALID_QUALITY_STATES:
        raise ValueError(f"화질 설정값({quality})이 올바르지 않습니다.")

    # Deduplicate while preserving order
    seen = set()
    unique_names: list[str] = []
    for fn in file_names:
        if fn not in seen:
            seen.add(fn)
            unique_names.append(fn)

    for fn in unique_names:
        validate_file_name(fn)

    xml_path = _get_pandory_xml_path(card_path)
    if not xml_path.exists():
        raise ValueError("pandory.xml 파일이 존재하지 않습니다.")

    data = xml_path.read_bytes()
    text = data.decode("utf-8")
    nl = "\r\n" if "\r\n" in text else "\n"

    masked = mask_comments(text)

    roms_open = list(re.finditer(r'<roms\b[^>]*>', masked))
    roms_close = list(re.finditer(r'</roms>', masked))
    if len(roms_open) != 1 or len(roms_close) != 1:
        raise ValueError("<roms> 구역이 올바르지 않거나 중복되어 있습니다.")

    chunk_start = roms_open[0].end()
    chunk_end = roms_close[0].start()
    chunk = masked[chunk_start:chunk_end]

    # Map name -> list of matches
    all_active_matches = []
    matches_by_name: dict[str, list[tuple[Any, str, Optional[ET.Element], bool]]] = {}

    for m in ROM_ELEM_PATTERN.finditer(chunk):
        raw = text[chunk_start + m.start(): chunk_start + m.end()]
        all_active_matches.append((m, raw))

        entry_name = None
        is_broken = False
        elem = None
        try:
            elem = ET.fromstring(raw)
            entry_name = elem.get("name")
            if not entry_name:
                is_broken = True
        except Exception:
            is_broken = True
            m_name = re.search(r'\bname=(["\'])(.*?)\1', raw)
            if m_name:
                entry_name = m_name.group(2)

        if entry_name:
            matches_by_name.setdefault(entry_name, []).append((m, raw, elem, is_broken))

    # Phase 1: Pre-validation of all requested files (Zero-Write on error)
    for fn in unique_names:
        if fn in matches_by_name:
            items = matches_by_name[fn]
            if len(items) > 1:
                raise ValueError(f"'{fn}' 게임의 설정 줄이 여러 개 존재하여 안전을 위해 변경하지 않았습니다.")
            _, _, _, is_broken = items[0]
            if is_broken:
                raise ValueError(f"'{fn}' 게임의 설정 줄이 이미 손상되어 있어 안전을 위해 변경하지 않았습니다.")

    # Phase 2: Compute replacements and insertions
    replacements: list[tuple[int, int, str]] = []  # (start, end, new_snippet)
    new_names_to_insert: list[str] = []

    for fn in unique_names:
        if fn in matches_by_name:
            m, raw, elem, _ = matches_by_name[fn][0]
            new_snippet = _update_snippet(raw, ratio=ratio, quality=quality)
            if new_snippet != raw:
                try:
                    ET.fromstring(new_snippet)
                except Exception as ex:
                    raise ValueError(f"'{fn}' 게임의 생성된 설정 조각 형식이 올바르지 않습니다: {ex}")
                abs_start = chunk_start + m.start()
                abs_end = chunk_start + m.end()
                replacements.append((abs_start, abs_end, new_snippet))
        else:
            # Entry does not exist
            # Only insert if there's something to set (not default/None)
            target_stretch = "false" if ratio == "original" else "true" if ratio == "full" else None
            target_smooth = "false" if quality == "sharp" else "true" if quality == "smooth" else None

            attrs = []
            if target_stretch is not None:
                attrs.append(f'stretchDisplay="{target_stretch}"')
            if target_smooth is not None:
                attrs.append(f'smoothPixels="{target_smooth}"')

            if attrs:
                new_names_to_insert.append(fn)

    if not replacements and not new_names_to_insert:
        return None  # No changes needed

    # Apply existing replacements from end to start to keep offsets valid
    replacements.sort(key=lambda x: x[0], reverse=True)
    curr_text = text
    for start, end, new_snip in replacements:
        curr_text = curr_text[:start] + new_snip + curr_text[end:]

    # Apply insertions before </roms>
    if new_names_to_insert:
        # Determine indentation
        if all_active_matches:
            last_m, _ = all_active_matches[-1]
            last_abs_start = chunk_start + last_m.start()
            last_line_start = text.rfind(nl, 0, last_abs_start)
            if last_line_start == -1:
                last_line_start = 0
            else:
                last_line_start += len(nl)
            indent = text[last_line_start:last_abs_start]
        else:
            close_line_start = text.rfind(nl, 0, chunk_end)
            if close_line_start == -1:
                close_line_start = 0
            else:
                close_line_start += len(nl)
            indent = text[close_line_start:chunk_end] + "    "

        # Construct insertion lines
        insert_lines = []
        for fn in new_names_to_insert:
            target_stretch = "false" if ratio == "original" else "true" if ratio == "full" else None
            target_smooth = "false" if quality == "sharp" else "true" if quality == "smooth" else None
            attrs = [f'name="{fn}"']
            if target_stretch is not None:
                attrs.append(f'stretchDisplay="{target_stretch}"')
            if target_smooth is not None:
                attrs.append(f'smoothPixels="{target_smooth}"')
            attr_str = " ".join(attrs)
            snip = f'<rom {attr_str} />'
            try:
                ET.fromstring(snip)
            except Exception as ex:
                raise ValueError(f"'{fn}' 게임의 생성된 설정 조각 형식이 올바르지 않습니다: {ex}")
            insert_lines.append(f"{indent}{snip}{nl}")

        # Find close line start in updated text
        close_m = re.search(r'</roms>', curr_text)
        assert close_m is not None
        close_pos = close_m.start()
        close_line_start = curr_text.rfind(nl, 0, close_pos)
        if close_line_start == -1:
            close_line_start = 0
        else:
            close_line_start += len(nl)

        curr_text = curr_text[:close_line_start] + "".join(insert_lines) + curr_text[close_line_start:]

    if curr_text == text:
        return None

    return write_with_backup(str(xml_path), curr_text.encode("utf-8"))


def read_emulator_entries(card_path: str | Path) -> dict[str, list[EmulatorEntry]]:
    """Read all active <emulator> elements from pandory.xml inside <emulators> block."""
    xml_path = _get_pandory_xml_path(card_path)
    if not xml_path.exists():
        raise ValueError("pandory.xml 파일이 존재하지 않습니다.")

    text = xml_path.read_text(encoding="utf-8")
    masked = mask_comments(text)

    em_open = list(re.finditer(r'<emulators\b[^>]*>', masked))
    em_close = list(re.finditer(r'</emulators>', masked))
    if len(em_open) != 1 or len(em_close) != 1:
        raise ValueError("<emulators> 구역이 올바르지 않거나 중복되어 있습니다.")

    chunk_start = em_open[0].end()
    chunk_end = em_close[0].start()
    chunk = masked[chunk_start:chunk_end]

    entries: dict[str, list[EmulatorEntry]] = {}
    for m in EMULATOR_ELEM_PATTERN.finditer(chunk):
        raw = text[chunk_start + m.start(): chunk_start + m.end()]
        try:
            elem = ET.fromstring(raw)
            folder = elem.get("folder")
            suffix = elem.get("suffix", "")
            if not folder:
                key = f"_broken_{m.start()}"
                entries.setdefault(key, []).append(
                    EmulatorEntry(
                        folder="",
                        suffix=suffix,
                        attrib={},
                        raw_snippet=raw,
                        broken=True,
                        ratio="default",
                        quality="default",
                    )
                )
            else:
                ratio = _parse_ratio_from_attrib(elem.attrib)
                quality = _parse_quality_from_attrib(elem.attrib)
                entries.setdefault(folder, []).append(
                    EmulatorEntry(
                        folder=folder,
                        suffix=suffix,
                        attrib=dict(elem.attrib),
                        raw_snippet=raw,
                        broken=False,
                        ratio=ratio,
                        quality=quality,
                    )
                )
        except Exception:
            m_folder = re.search(r'\bfolder=(["\'])(.*?)\1', raw)
            folder = m_folder.group(2) if m_folder else f"_broken_{m.start()}"
            m_suffix = re.search(r'\bsuffix=(["\'])(.*?)\1', raw)
            suffix = m_suffix.group(2) if m_suffix else ""
            entries.setdefault(folder, []).append(
                EmulatorEntry(
                    folder=folder,
                    suffix=suffix,
                    attrib={},
                    raw_snippet=raw,
                    broken=True,
                    ratio="default",
                    quality="default",
                )
            )

    return entries


def set_emulator_options(
    card_path: str | Path,
    folder: str,
    ratio: Optional[str] = None,
    quality: Optional[str] = None,
) -> str | None:
    """Set ratio and/or quality for all <emulator> elements matching folder in pandory.xml."""
    validate_folder_name(folder)
    if ratio is None and quality is None:
        raise ValueError("변경할 화면 비율이나 화질 설정이 지정되지 않았습니다.")
    if ratio is not None and ratio not in VALID_RATIO_STATES:
        raise ValueError(f"화면 비율 설정값({ratio})이 올바르지 않습니다.")
    if quality is not None and quality not in VALID_QUALITY_STATES:
        raise ValueError(f"화질 설정값({quality})이 올바르지 않습니다.")

    xml_path = _get_pandory_xml_path(card_path)
    if not xml_path.exists():
        raise ValueError("pandory.xml 파일이 존재하지 않습니다.")

    data = xml_path.read_bytes()
    text = data.decode("utf-8")

    masked = mask_comments(text)
    em_open = list(re.finditer(r'<emulators\b[^>]*>', masked))
    em_close = list(re.finditer(r'</emulators>', masked))
    if len(em_open) != 1 or len(em_close) != 1:
        raise ValueError("<emulators> 구역이 올바르지 않거나 중복되어 있습니다.")

    chunk_start = em_open[0].end()
    chunk_end = em_close[0].start()
    chunk = masked[chunk_start:chunk_end]

    target_matches = []
    for m in EMULATOR_ELEM_PATTERN.finditer(chunk):
        raw = text[chunk_start + m.start(): chunk_start + m.end()]
        is_broken = False
        entry_folder = None
        try:
            elem = ET.fromstring(raw)
            entry_folder = elem.get("folder")
            if not entry_folder:
                is_broken = True
        except Exception:
            is_broken = True
            m_f = re.search(r'\bfolder=(["\'])(.*?)\1', raw)
            if m_f:
                entry_folder = m_f.group(2)

        if entry_folder == folder:
            if is_broken:
                raise ValueError(f"'{folder}' 기종의 설정 줄이 이미 손상되어 있어 안전을 위해 변경하지 않았습니다.")
            target_matches.append((m, raw))

    if not target_matches:
        raise ValueError(f"기종 '{folder}'을(를) pandory.xml 설정에서 찾을 수 없습니다.")

    # Compute replacements
    replacements: list[tuple[int, int, str]] = []
    for m, raw in target_matches:
        new_snip = _update_snippet(raw, ratio=ratio, quality=quality)
        if new_snip != raw:
            try:
                ET.fromstring(new_snip)
            except Exception as ex:
                raise ValueError(f"기종 '{folder}'의 생성된 설정 조각 형식이 올바르지 않습니다: {ex}")
            abs_start = chunk_start + m.start()
            abs_end = chunk_start + m.end()
            replacements.append((abs_start, abs_end, new_snip))

    if not replacements:
        return None

    # Apply from end to start
    replacements.sort(key=lambda x: x[0], reverse=True)
    curr_text = text
    for start, end, new_snip in replacements:
        curr_text = curr_text[:start] + new_snip + curr_text[end:]

    if curr_text == text:
        return None

    return write_with_backup(str(xml_path), curr_text.encode("utf-8"))

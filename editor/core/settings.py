"""Settings module for pandory/pandory.xml."""
import os
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Any, Optional

from editor.core.backup import write_with_backup
from editor.core.card import validate_card_path


@dataclass
class SettingSpec:
    name: str
    label: str
    type_str: str  # 'bool' | 'int' | 'float'
    min_val: Optional[float] = None
    max_val: Optional[float] = None
    description: str = ""


EDITABLE_SPECS: dict[str, SettingSpec] = {
    "stretchDisplay": SettingSpec(
        name="stretchDisplay",
        label="화면 가득 채우기",
        type_str="bool",
        min_val=None,
        max_val=None,
        description="게임 화면 비율 유지를 해제하고 모니터 전체에 가득 차도록 늘립니다.",
    ),
    "smoothPixels": SettingSpec(
        name="smoothPixels",
        label="픽셀 부드럽게 (스무딩)",
        type_str="bool",
        min_val=None,
        max_val=None,
        description="거친 픽셀을 부드럽게 뭉개주는 그래픽 보정 필터를 적용합니다.",
    ),
    "scanlineOpacity": SettingSpec(
        name="scanlineOpacity",
        label="브라운관 줄무늬 진하기",
        type_str="float",
        min_val=0.0,
        max_val=1.0,
        description="고전 브라운관 TV 느낌의 가로 줄무늬(스캔라인) 진하기를 0부터 1까지 조절합니다.",
    ),
    "useBetterScanlines": SettingSpec(
        name="useBetterScanlines",
        label="고급 줄무늬 효과",
        type_str="bool",
        min_val=None,
        max_val=None,
        description="더 정교하고 자연스러운 고품질 줄무늬 효과(jpinoRoyale)를 사용합니다.",
    ),
    "forceSmoothCGA": SettingSpec(
        name="forceSmoothCGA",
        label="구형 브라운관 화면 보정",
        type_str="bool",
        min_val=None,
        max_val=None,
        description="CGA 저해상도 화면 연결 시 픽셀을 강제로 부드럽게 보정합니다.",
    ),
    "menuMusic": SettingSpec(
        name="menuMusic",
        label="메뉴 배경 음악 켜기",
        type_str="bool",
        min_val=None,
        max_val=None,
        description="판도라 게임 선택 메뉴 화면에서 배경 음악을 재생합니다.",
    ),
    "musicVolume": SettingSpec(
        name="musicVolume",
        label="배경 음악 음량",
        type_str="int",
        min_val=0,
        max_val=100,
        description="메뉴 배경 음악의 소리 크기를 0부터 100까지 조절합니다.",
    ),
    "disableForcedQualityFilter": SettingSpec(
        name="disableForcedQualityFilter",
        label="기기 기본 화질 필터 끄기",
        type_str="bool",
        min_val=None,
        max_val=None,
        description="체크하면 기기에 원래 있는 화질 필터를 끈 상태로 유지하고, 해제하면 그 필터가 동작할 수 있습니다. 기기에서 확인이 필요합니다.",
    ),
}


def read_settings(card_path: str) -> dict[str, str]:
    """Read all active <setting name= value=> entries inside <system> (ignoring comments)."""
    card_path = validate_card_path(card_path)
    xml_path = os.path.join(card_path, "pandory", "pandory.xml")
    if not os.path.isfile(xml_path):
        raise ValueError(f"pandory.xml 파일을 찾을 수 없습니다: {xml_path}")

    with open(xml_path, "rb") as f:
        data = f.read()

    m = re.search(rb"<system\b[^>]*>(.*?)</system>", data, re.DOTALL)
    if not m:
        return {}

    sys_content = re.sub(rb"<!--.*?-->", rb"", m.group(1), flags=re.DOTALL)
    pairs = re.findall(
        rb'<setting\b[^>]*?\bname=["\']([^"\']+)["\'][^>]*?\bvalue=["\']([^"\']*)["\']',
        sys_content,
    )
    return {name.decode("utf-8"): value.decode("utf-8") for name, value in pairs}


def set_settings(card_path: str, changes: dict[str, Any]) -> Optional[str]:
    """Change settings via exact byte replacement inside <system> block.
    - Atomically validates all changes first.
    - If no change is made, returns None and leaves file untouched.
    - If valid and changed, verifies XML validity and writes via write_with_backup.
    Returns backup path on success, or None if unchanged.
    """
    card_path = validate_card_path(card_path)
    if not changes:
        return None

    # 1. Validation & normalization
    normalized: dict[str, str] = {}
    for k, v in changes.items():
        if k not in EDITABLE_SPECS:
            raise ValueError(f"'{k}'은(는) 변경할 수 없는 설정입니다.")
        spec = EDITABLE_SPECS[k]

        if spec.type_str == "bool":
            if isinstance(v, bool):
                normalized[k] = "true" if v else "false"
            elif isinstance(v, str) and v.lower() in ("true", "false"):
                normalized[k] = v.lower()
            else:
                raise ValueError(f"'{k}' 설정은 참/거짓(true/false) 값이어야 합니다.")

        elif spec.type_str == "float":
            if isinstance(v, bool):
                raise ValueError(f"'{k}' 설정은 소수여야 합니다.")
            try:
                fv = float(v)
            except (TypeError, ValueError):
                raise ValueError(f"'{k}' 설정은 올바른 소수여야 합니다.")
            if spec.min_val is not None and fv < spec.min_val:
                raise ValueError(f"'{k}' 설정값은 {spec.min_val} 이상이어야 합니다.")
            if spec.max_val is not None and fv > spec.max_val:
                raise ValueError(f"'{k}' 설정값은 {spec.max_val} 이하여야 합니다.")
            # Format float nicely (e.g. 0.35, 1.0 or 1)
            rounded = round(fv, 2)
            if rounded == int(rounded):
                normalized[k] = str(rounded)
            else:
                normalized[k] = str(rounded)

        elif spec.type_str == "int":
            if isinstance(v, bool) or isinstance(v, float):
                raise ValueError(f"'{k}' 설정은 정수여야 합니다.")
            if isinstance(v, str):
                if not re.match(r"^-?\d+$", v.strip()):
                    raise ValueError(f"'{k}' 설정은 올바른 정수여야 합니다.")
                iv = int(v.strip())
            elif isinstance(v, int):
                iv = v
            else:
                raise ValueError(f"'{k}' 설정은 올바른 정수여야 합니다.")
            if spec.min_val is not None and iv < spec.min_val:
                raise ValueError(f"'{k}' 설정값은 {spec.min_val} 이상이어야 합니다.")
            if spec.max_val is not None and iv > spec.max_val:
                raise ValueError(f"'{k}' 설정값은 {spec.max_val} 이하여야 합니다.")
            normalized[k] = str(iv)

    # 2. Read file bytes
    xml_path = os.path.join(card_path, "pandory", "pandory.xml")
    if not os.path.isfile(xml_path):
        raise ValueError(f"pandory.xml 파일을 찾을 수 없습니다: {xml_path}")

    with open(xml_path, "rb") as f:
        data = f.read()

    # 3. Locate <system> block
    sys_match = re.search(rb"(<system\b[^>]*>)(.*?)(</system>)", data, re.DOTALL)
    if not sys_match:
        raise ValueError("pandory.xml에서 <system> 설정을 찾을 수 없습니다.")

    prefix = data[: sys_match.start(2)]
    sys_block = sys_match.group(2)
    suffix = data[sys_match.end(2) :]

    # 4. Find active settings in sys_block (excluding comments)
    comment_spans = [m.span() for m in re.finditer(rb"<!--.*?-->", sys_block, re.DOTALL)]

    active_matches: dict[str, Any] = {}
    for name in normalized:
        pattern = re.compile(
            rb'(<setting\b[^>]*?\bname=["\']'
            + re.escape(name.encode("utf-8"))
            + rb'["\'][^>]*?\bvalue=["\'])([^"\']*?)(["\'])'
        )
        matches = []
        for m in pattern.finditer(sys_block):
            in_comment = any(cs <= m.start() and m.end() <= ce for cs, ce in comment_spans)
            if not in_comment:
                matches.append(m)

        if len(matches) == 0:
            raise ValueError(f"'{name}' 설정 줄을 pandory.xml의 <system>에서 찾을 수 없습니다.")
        if len(matches) > 1:
            raise ValueError(f"'{name}' 설정이 2개 이상 중복되어 있습니다.")
        active_matches[name] = matches[0]

    # 5. Check if anything actually changes
    has_change = False
    for name, new_val in normalized.items():
        m = active_matches[name]
        old_val = m.group(2).decode("utf-8", errors="replace")
        # Compare as floats if float
        spec = EDITABLE_SPECS[name]
        if spec.type_str == "float":
            try:
                if float(old_val) != float(new_val):
                    has_change = True
            except ValueError:
                has_change = True
        else:
            if old_val != new_val:
                has_change = True

    if not has_change:
        return None

    # 6. Perform byte replacements from bottom to top to preserve offsets
    replacements = [
        (active_matches[name], normalized[name].encode("utf-8")) for name in normalized
    ]
    replacements.sort(key=lambda x: x[0].start(2), reverse=True)

    new_sys_block = bytearray(sys_block)
    for m, new_bytes in replacements:
        s2 = m.start(2)
        e2 = m.end(2)
        new_sys_block[s2:e2] = new_bytes

    new_data = prefix + bytes(new_sys_block) + suffix

    # 7. Validate <system> block XML structure only
    full_system_chunk = sys_match.group(1) + bytes(new_sys_block) + sys_match.group(3)
    try:
        ET.fromstring(full_system_chunk)
    except Exception as ex:
        raise ValueError(f"화면 및 소리 설정 데이터 구조가 올바르지 않습니다: {ex}")

    # 8. Write via write_with_backup (binary mode)
    return write_with_backup(xml_path, new_data)


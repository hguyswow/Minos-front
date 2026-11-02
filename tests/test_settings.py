# Acceptance tests.
import os, re
import pytest
import xml.etree.ElementTree as ET
from editor.core import settings, card as ccard
from editor.app.controller import EditorController, SettingView

HANGUL = re.compile("[가-힣]")
EDIT7 = {"stretchDisplay", "smoothPixels", "scanlineOpacity", "useBetterScanlines",
         "forceSmoothCGA", "menuMusic", "musicVolume"}

XML = (
    '<?xml version="1.0" encoding="UTF-8"?>\r\n'
    "<pandory>\r\n"
    "    <!-- General settings -->\r\n"
    "    <system>\r\n"
    '        <setting name="debug" value="false"/>\r\n'
    '        <setting name="disableDipswitches" value="true"/>\r\n'
    "        <!-- old: <setting name=\"musicVolume\" value=\"99\"/> -->\r\n"
    '        <setting name="scanlineOpacity" value="0.2"/>\r\n'
    '        <setting name="useBetterScanlines" value="true"/>\r\n'
    '        <setting name="smoothPixels" value="false"/>\r\n'
    '        <setting name="forceSmoothCGA" value="true" />\r\n'
    '        <setting name="stretchDisplay" value="false" />\r\n'
    '        <setting name="menuMusic" value="true" />\r\n'
    '        <setting name="musicVolume" value="10" />\r\n'
    "    </system>\r\n"
    "    <emulators>\r\n"
    '        <emulator suffix="GBA" folder="gba" core="mgba" />\r\n'
    "    </emulators>\r\n"
    '    <setting name="smoothPixels" value="false"/>\r\n'
    "</pandory>\r\n"
).encode("utf-8")


@pytest.fixture
def fake(tmp_path):
    c = tmp_path / "card"
    (c / "pandory").mkdir(parents=True)
    (c / "roms").mkdir()
    (c / "roms_pandory").mkdir()
    (c / "pandory" / "pandory.xml").write_bytes(XML)
    return c


def xmlp(c):
    return c / "pandory" / "pandory.xml"


def baks(c):
    return sorted(p for p in (c / "pandory").iterdir() if ".bak" in p.name)


def test_editable_specs():
    assert set(settings.EDITABLE_SPECS) == EDIT7 | {"disableForcedQualityFilter"}
    for name, s in settings.EDITABLE_SPECS.items():
        assert s.name == name and s.type_str in ("bool", "int", "float") and HANGUL.search(s.label) and HANGUL.search(s.description)
    assert settings.EDITABLE_SPECS["scanlineOpacity"].min_val == 0 and settings.EDITABLE_SPECS["scanlineOpacity"].max_val == 1
    assert settings.EDITABLE_SPECS["musicVolume"].min_val == 0 and settings.EDITABLE_SPECS["musicVolume"].max_val == 100


def test_read_settings_ignores_comments_and_outside(fake):
    r = settings.read_settings(str(fake))
    assert r["musicVolume"] == "10" and r["debug"] == "false" and r["stretchDisplay"] == "false"
    assert len(r) == 9  # only active <setting> inside <system>


def test_set_bool_is_byte_exact(fake):
    before = xmlp(fake).read_bytes()
    bak = settings.set_settings(str(fake), {"stretchDisplay": True})
    after = xmlp(fake).read_bytes()
    expected = before.replace(b'name="stretchDisplay" value="false"', b'name="stretchDisplay" value="true"', 1)
    assert after == expected and b"\r\n" in after
    assert bak and os.path.isfile(bak) and open(bak, "rb").read() == before
    assert settings.read_settings(str(fake))["stretchDisplay"] == "true"


def test_string_bools_normalized(fake):
    settings.set_settings(str(fake), {"menuMusic": "False", "smoothPixels": "TRUE"})
    r = settings.read_settings(str(fake))
    assert r["menuMusic"] == "false" and r["smoothPixels"] == "true"
    # the decoy <setting> outside <system> is untouched
    assert xmlp(fake).read_bytes().count(b'name="smoothPixels" value="false"') == 1


def test_numbers(fake):
    settings.set_settings(str(fake), {"scanlineOpacity": 0.35, "musicVolume": 50})
    r = settings.read_settings(str(fake))
    assert float(r["scanlineOpacity"]) == pytest.approx(0.35) and r["musicVolume"] == "50"
    settings.set_settings(str(fake), {"scanlineOpacity": "1", "musicVolume": "0"})
    r = settings.read_settings(str(fake))
    assert float(r["scanlineOpacity"]) == 1.0 and r["musicVolume"] == "0"


def test_comment_decoy_not_touched(fake):
    settings.set_settings(str(fake), {"musicVolume": 77})
    data = xmlp(fake).read_bytes()
    assert b'<!-- old: <setting name="musicVolume" value="99"/> -->' in data
    assert settings.read_settings(str(fake))["musicVolume"] == "77"
    ET.fromstring(data)  # still valid XML


def test_multiple_changes_one_backup(fake):
    settings.set_settings(str(fake), {"stretchDisplay": True, "musicVolume": 20, "scanlineOpacity": 0.5})
    assert len(baks(fake)) == 1
    r = settings.read_settings(str(fake))
    assert r["stretchDisplay"] == "true" and r["musicVolume"] == "20"


@pytest.mark.parametrize("changes", [
    {"scanlineOpacity": 1.5}, {"scanlineOpacity": -0.1}, {"scanlineOpacity": "abc"},
    {"musicVolume": 101}, {"musicVolume": -1}, {"musicVolume": 10.5}, {"musicVolume": "x"},
    {"stretchDisplay": "yes"}, {"stretchDisplay": 1},
    {"debug": True}, {"disableDipswitches": False}, {"nope": "1"},
    {"stretchDisplay": True, "musicVolume": 999},  # valid + invalid -> nothing written
])
def test_invalid_changes_write_nothing(fake, changes):
    before = xmlp(fake).read_bytes()
    with pytest.raises(ValueError) as e:
        settings.set_settings(str(fake), changes)
    assert HANGUL.search(str(e.value))  # message is user-readable Korean
    assert xmlp(fake).read_bytes() == before and baks(fake) == []


def test_unchanged_value_writes_nothing(fake):
    before = xmlp(fake).read_bytes()
    assert settings.set_settings(str(fake), {"musicVolume": 10, "menuMusic": True}) is None
    assert xmlp(fake).read_bytes() == before and baks(fake) == []


def test_missing_or_duplicate_setting_rejected(fake):
    data = XML.replace(b'        <setting name="menuMusic" value="true" />\r\n', b"")
    xmlp(fake).write_bytes(data)
    with pytest.raises(ValueError):
        settings.set_settings(str(fake), {"menuMusic": False})
    dup = XML.replace(b'        <setting name="menuMusic" value="true" />\r\n',
                      b'        <setting name="menuMusic" value="true" />\r\n        <setting name="menuMusic" value="true" />\r\n')
    xmlp(fake).write_bytes(dup)
    with pytest.raises(ValueError):
        settings.set_settings(str(fake), {"menuMusic": False})
    assert xmlp(fake).read_bytes() == dup


def test_pre_existing_breakage_outside_system_does_not_block_edit(fake):
    # The real card's pandory.xml has a line like this (missing space between attributes; the device tolerates it).
    broken = XML.replace(b'<emulator suffix="GBA" folder="gba" core="mgba" />',
                         b'<rom name="xmen.zip" keymap="fbae-xmen"core="fba-external" />')
    assert broken != XML
    with pytest.raises(ET.ParseError):
        ET.fromstring(broken)  # whole file is not strict XML
    xmlp(fake).write_bytes(broken)
    settings.set_settings(str(fake), {"musicVolume": 33})
    after = xmlp(fake).read_bytes()
    assert after == broken.replace(b'name="musicVolume" value="10"', b'name="musicVolume" value="33"', 1)
    assert settings.read_settings(str(fake))["musicVolume"] == "33"  # the broken line is NOT "repaired"


def test_real_card_xml_copy_is_editable(tmp_path):
    ref = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "reference", "pandory.xml")
    c = tmp_path / "card"
    (c / "pandory").mkdir(parents=True)
    (c / "roms").mkdir()
    (c / "roms_pandory").mkdir()
    orig = open(ref, "rb").read()
    (c / "pandory" / "pandory.xml").write_bytes(orig)
    settings.set_settings(str(c), {"stretchDisplay": True, "musicVolume": 30, "scanlineOpacity": 0.35})
    new = (c / "pandory" / "pandory.xml").read_bytes()
    assert len(orig.splitlines()) == len(new.splitlines())
    diff = [(a, b) for a, b in zip(orig.splitlines(), new.splitlines()) if a != b]
    assert len(diff) == 3  # exactly the three edited lines changed
    assert open(str(c / "pandory" / "pandory.xml.bak"), "rb").read() == orig


def test_bad_card_rejected(tmp_path):
    with pytest.raises(ccard.CardValidationError):
        settings.read_settings(str(tmp_path))
    with pytest.raises(ccard.CardValidationError):
        settings.set_settings(str(tmp_path), {"musicVolume": 5})


# ---- controller ----
def test_controller_get_settings(fake):
    c = EditorController(str(fake))
    views = c.get_settings()
    assert all(isinstance(v, SettingView) for v in views)
    assert {v.name for v in views if v.editable} == EDIT7
    assert {v.name for v in views if not v.editable} == {"debug", "disableDipswitches"}
    first_locked = next(i for i, v in enumerate(views) if not v.editable)
    assert all(v.editable for v in views[:first_locked])  # editable first
    mv = next(v for v in views if v.name == "musicVolume")
    assert mv.type_str == "int" and mv.value == "10" and (mv.min_val, mv.max_val) == (0, 100) and HANGUL.search(mv.label)


def test_controller_save_settings(fake):
    c = EditorController(str(fake))
    msg = c.save_settings({"musicVolume": 40})
    assert HANGUL.search(msg) and "pandory.xml.bak" in msg
    msg2 = c.save_settings({"musicVolume": 40})
    assert HANGUL.search(msg2) and msg2 != msg and ".bak" not in msg2
    with pytest.raises(ValueError):
        c.save_settings({"musicVolume": 400})


def test_controller_needs_card():
    c = EditorController()
    with pytest.raises(ValueError):
        c.get_settings()
    with pytest.raises(ValueError):
        c.save_settings({"musicVolume": 1})

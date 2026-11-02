# Acceptance tests.
import ast, os, re
import pytest
from editor.core import romsettings, settings
from editor.app.controller import EditorController, GameRow, SystemRow

HANGUL = re.compile("[가-힣]")

TEMPLATE = (
    '<?xml version="1.0" encoding="UTF-8"?>\n'
    "<pandory>\n"
    "    <system>\n"
    '        <setting name="stretchDisplay" value="false" />\n'
    '        <setting name="disableForcedQualityFilter" value="true"/>\n'
    "    </system>\n"
    "    <emulators>\n"
    '        <emulator suffix="PICO" folder="genesis" core="picodrive" />\n'
    '        <emulator suffix="GENESIS" folder="genesis" core="picodrive"/>\n'
    '        <emulator suffix="GBLINK" folder="gblink" core="tgbdual" keymap="gameboy" stretchDisplay="true" />\n'
    '        <emulator suffix="GBA" folder="gba" core="mgba" keymap="gba" />\n'
    '        <emulator suffix="BAD" folder="badf" core="x"keymap="y" />\n'
    '        <!-- <emulator suffix="DECOY" folder="decoy" core="c" /> -->\n'
    "    </emulators>\n"
    "    <roms>\n"
    '        <rom name="QuakeSW.zip" core="tyrquake"/>\n'
    '        <rom name="sf2.zip" speed="100" />\n'
    '        <rom name="a.zip" stretchDisplay="false" speed="100" />\n'
    '        <rom name="xmen.zip" keymap="fbae-xmen"core="fba-external" />\n'
    '        <rom name="dup.zip" speed="1" />\n'
    '        <rom name="dup.zip" speed="2" />\n'
    "    </roms>\n"
    "</pandory>\n"
)


def make_card(tmp_path, nl="\n", xml=TEMPLATE):
    c = tmp_path / "card"
    for d in ("pandory", "roms", "roms_pandory/gba", "roms_pandory/genesis"):
        (c / d).mkdir(parents=True)
    data = xml.replace("\n", nl).encode("utf-8")
    (c / "pandory" / "pandory.xml").write_bytes(data)
    return c, data


def xmlp(c):
    return c / "pandory" / "pandory.xml"


def baks(c):
    return sorted(p.name for p in (c / "pandory").iterdir() if ".bak" in p.name)


@pytest.fixture(params=["\n", "\r\n"], ids=["LF", "CRLF"])
def card_nl(request, tmp_path):
    c, data = make_card(tmp_path, request.param)
    return c, data, request.param.encode()


# ---------------- <rom> quality ----------------
def test_quality_add_replace_remove(card_nl):
    c, before, nl = card_nl
    romsettings.set_rom_quality(str(c), "sf2.zip", "smooth")
    romsettings.set_rom_quality(str(c), "QuakeSW.zip", "sharp")
    exp = before.replace(b'<rom name="sf2.zip" speed="100" />', b'<rom name="sf2.zip" speed="100" smoothPixels="true" />', 1)
    exp = exp.replace(b'<rom name="QuakeSW.zip" core="tyrquake"/>', b'<rom name="QuakeSW.zip" core="tyrquake" smoothPixels="false"/>', 1)
    assert xmlp(c).read_bytes() == exp
    romsettings.set_rom_quality(str(c), "sf2.zip", "sharp")
    assert b'<rom name="sf2.zip" speed="100" smoothPixels="false" />' in xmlp(c).read_bytes()
    romsettings.set_rom_quality(str(c), "sf2.zip", "default")
    romsettings.set_rom_quality(str(c), "QuakeSW.zip", "default")
    assert xmlp(c).read_bytes() == before.replace(b'<rom name="QuakeSW.zip" core="tyrquake"/>', b'<rom name="QuakeSW.zip" core="tyrquake"/>', 1)
    e = romsettings.read_rom_entries(str(c))
    assert e["sf2.zip"].quality == "default" and e["sf2.zip"].ratio == "default"


def test_new_rom_element_for_quality(card_nl):
    c, before, nl = card_nl
    romsettings.set_rom_quality(str(c), "New.zip", "smooth")
    exp = before.replace(b"    </roms>", b'        <rom name="New.zip" smoothPixels="true" />' + nl + b"    </roms>", 1)
    assert xmlp(c).read_bytes() == exp
    assert romsettings.read_rom_entries(str(c))["New.zip"].quality == "smooth"


def test_ratio_and_quality_coexist_in_stable_order(card_nl):
    c, before, nl = card_nl
    romsettings.set_rom_ratio(str(c), "sf2.zip", "full")
    romsettings.set_rom_quality(str(c), "sf2.zip", "sharp")
    assert b'<rom name="sf2.zip" speed="100" stretchDisplay="true" smoothPixels="false" />' in xmlp(c).read_bytes()
    e = romsettings.read_rom_entries(str(c))["sf2.zip"]
    assert (e.ratio, e.quality, e.attrib["speed"]) == ("full", "sharp", "100")


# ---------------- bulk ----------------
def test_bulk_one_write_one_backup(card_nl):
    c, before, nl = card_nl
    bak = romsettings.set_rom_options_bulk(str(c), ["sf2.zip", "QuakeSW.zip", "New.zip"], ratio="full", quality="smooth")
    exp = before.replace(b'<rom name="sf2.zip" speed="100" />', b'<rom name="sf2.zip" speed="100" stretchDisplay="true" smoothPixels="true" />', 1)
    exp = exp.replace(b'<rom name="QuakeSW.zip" core="tyrquake"/>', b'<rom name="QuakeSW.zip" core="tyrquake" stretchDisplay="true" smoothPixels="true"/>', 1)
    exp = exp.replace(b"    </roms>", b'        <rom name="New.zip" stretchDisplay="true" smoothPixels="true" />' + nl + b"    </roms>", 1)
    assert xmlp(c).read_bytes() == exp
    assert bak and baks(c) == ["pandory.xml.bak"] and open(bak, "rb").read() == before


def test_bulk_only_the_requested_attribute(tmp_path):
    c, before = make_card(tmp_path)
    romsettings.set_rom_options_bulk(str(c), ["a.zip", "sf2.zip"], quality="smooth")
    e = romsettings.read_rom_entries(str(c))
    assert (e["a.zip"].ratio, e["a.zip"].quality) == ("original", "smooth")  # existing ratio untouched
    assert (e["sf2.zip"].ratio, e["sf2.zip"].quality) == ("default", "smooth")


def test_bulk_duplicates_in_list_are_fine_and_noop_writes_nothing(tmp_path):
    c, before = make_card(tmp_path)
    romsettings.set_rom_options_bulk(str(c), ["sf2.zip", "sf2.zip"], ratio="full")
    assert xmlp(c).read_bytes().count(b'name="sf2.zip"') == 1
    mid = xmlp(c).read_bytes()
    n = len(baks(c))
    assert romsettings.set_rom_options_bulk(str(c), ["sf2.zip"], ratio="full") is None
    assert xmlp(c).read_bytes() == mid and len(baks(c)) == n


@pytest.mark.parametrize("names,kw", [
    (["sf2.zip", "xmen.zip"], {"ratio": "full"}),  # broken line poisons the whole batch
    (["sf2.zip", "dup.zip"], {"ratio": "full"}),
    (["sf2.zip", "a/b.zip"], {"ratio": "full"}),
    (["sf2.zip", ""], {"quality": "smooth"}),
    ([], {"ratio": "full"}),
    (["sf2.zip"], {}),
    (["sf2.zip"], {"ratio": "bogus"}),
    (["sf2.zip"], {"quality": "bogus"}),
])
def test_bulk_refusals_are_all_or_nothing(tmp_path, names, kw):
    c, before = make_card(tmp_path)
    with pytest.raises(ValueError) as e:
        romsettings.set_rom_options_bulk(str(c), names, **kw)
    assert HANGUL.search(str(e.value))
    assert xmlp(c).read_bytes() == before and baks(c) == []


def test_bulk_message_names_the_offender(tmp_path):
    c, _ = make_card(tmp_path)
    with pytest.raises(ValueError) as e:
        romsettings.set_rom_options_bulk(str(c), ["sf2.zip", "xmen.zip"], ratio="full")
    assert "xmen.zip" in str(e.value)


# ---------------- <emulator> ----------------
def test_read_emulator_entries(tmp_path):
    c, _ = make_card(tmp_path)
    em = romsettings.read_emulator_entries(str(c))
    assert [x.suffix for x in em["genesis"]] == ["PICO", "GENESIS"]
    assert em["gblink"][0].ratio == "full" and em["gba"][0].ratio == "default"
    assert em["badf"][0].broken is True and "decoy" not in em
    assert all(not x.broken for k in ("genesis", "gblink", "gba") for x in em[k])


def test_emulator_edit_touches_every_element_of_the_folder(card_nl):
    c, before, nl = card_nl
    romsettings.set_emulator_options(str(c), "genesis", ratio="original", quality="smooth")
    exp = before.replace(b'<emulator suffix="PICO" folder="genesis" core="picodrive" />',
                         b'<emulator suffix="PICO" folder="genesis" core="picodrive" stretchDisplay="false" smoothPixels="true" />', 1)
    exp = exp.replace(b'<emulator suffix="GENESIS" folder="genesis" core="picodrive"/>',
                      b'<emulator suffix="GENESIS" folder="genesis" core="picodrive" stretchDisplay="false" smoothPixels="true"/>', 1)
    assert xmlp(c).read_bytes() == exp
    assert baks(c) == ["pandory.xml.bak"]


def test_emulator_replace_and_remove(card_nl):
    c, before, nl = card_nl
    romsettings.set_emulator_options(str(c), "gblink", ratio="default")
    assert xmlp(c).read_bytes() == before.replace(b' stretchDisplay="true" />', b' />', 1)
    # original file (with the attribute) comes back after setting it again
    romsettings.set_emulator_options(str(c), "gblink", ratio="full")
    assert b'<emulator suffix="GBLINK" folder="gblink" core="tgbdual" keymap="gameboy" stretchDisplay="true" />' in xmlp(c).read_bytes()


@pytest.mark.parametrize("folder", ["badf", "nope", "decoy", "", "a/b", "genesis\n"])
def test_emulator_refusals_change_nothing(tmp_path, folder):
    c, before = make_card(tmp_path)
    with pytest.raises(ValueError) as e:
        romsettings.set_emulator_options(str(c), folder, ratio="full")
    assert HANGUL.search(str(e.value))
    assert xmlp(c).read_bytes() == before and baks(c) == []


def test_emulator_no_change_writes_nothing(tmp_path):
    c, before = make_card(tmp_path)
    assert romsettings.set_emulator_options(str(c), "gblink", ratio="full") is None
    assert romsettings.set_emulator_options(str(c), "gba", ratio="default", quality="default") is None
    assert xmlp(c).read_bytes() == before and baks(c) == []


def test_real_card_xml_copy_genesis(tmp_path):
    ref = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "reference", "pandory.xml")
    orig = open(ref, "rb").read()
    c = tmp_path / "card"
    for d in ("pandory", "roms", "roms_pandory"):
        (c / d).mkdir(parents=True)
    xmlp(c).write_bytes(orig)
    em = romsettings.read_emulator_entries(str(c))
    assert sum(len(v) for v in em.values()) == 15 and not any(x.broken for v in em.values() for x in v)
    romsettings.set_emulator_options(str(c), "genesis", ratio="full", quality="sharp")
    new = xmlp(c).read_bytes()
    ol, nl_ = orig.split(b"\n"), new.split(b"\n")
    assert len(ol) == len(nl_)
    changed = [i for i, (a, b) in enumerate(zip(ol, nl_)) if a != b]
    assert len(changed) == 2 and all(b'folder="genesis"' in ol[i] for i in changed)
    assert b'keymap="fbae-xmen"core="fba-external"' in new  # the pre-existing broken <rom> line is untouched
    assert open(str(c / "pandory" / "pandory.xml.bak"), "rb").read() == orig


# ---------------- global setting: disableForcedQualityFilter ----------------
def test_forced_filter_setting_is_editable_and_neutral(tmp_path):
    assert "disableForcedQualityFilter" in settings.EDITABLE_SPECS
    s = settings.EDITABLE_SPECS["disableForcedQualityFilter"]
    assert s.type_str == "bool" and HANGUL.search(s.label) and HANGUL.search(s.description)
    assert "블러" not in s.label + s.description and "기기에서 확인" in s.description  # effect on the device is not verified
    c, before = make_card(tmp_path)
    settings.set_settings(str(c), {"disableForcedQualityFilter": False})
    assert settings.read_settings(str(c))["disableForcedQualityFilter"] == "false"
    assert xmlp(c).read_bytes() == before.replace(b'name="disableForcedQualityFilter" value="true"', b'name="disableForcedQualityFilter" value="false"', 1)


# ---------------- controller ----------------
def _put(c, folder, name):
    d = c / "roms_pandory" / folder
    d.mkdir(parents=True, exist_ok=True)
    (d / name).write_bytes(b"x")


def test_gamerow_quality_field():
    import dataclasses
    f = dataclasses.fields(GameRow)
    assert [x.name for x in f][-2:] == ["ratio", "quality"] and f[-1].default == "default"
    assert GameRow(9801, "gba", "t", "f", "r").quality == "default"


def test_controller_game_options(tmp_path):
    c, _ = make_card(tmp_path)
    _put(c, "gba", "Zelda.gba")
    _put(c, "gba", "a.zip")
    _put(c, "genesis", "sf2.zip")
    ctl = EditorController(str(c))
    msg = ctl.set_game_options(["Zelda.gba", "sf2.zip"], ratio="full", quality="smooth")
    assert HANGUL.search(msg) and "2" in msg
    rows = {r.file_name: r for r in ctl.get_games()}
    assert (rows["Zelda.gba"].ratio, rows["Zelda.gba"].quality) == ("full", "smooth")
    assert (rows["sf2.zip"].ratio, rows["sf2.zip"].quality) == ("full", "smooth")
    assert (rows["a.zip"].ratio, rows["a.zip"].quality) == ("original", "default")  # not selected -> untouched
    before = xmlp(c).read_bytes()
    with pytest.raises(ValueError):
        ctl.set_game_options(["Zelda.gba", "not-in-list.zip"], ratio="default")
    assert xmlp(c).read_bytes() == before
    with pytest.raises(ValueError):
        ctl.set_game_options([], ratio="full")


def test_controller_systems(tmp_path):
    c, _ = make_card(tmp_path)
    _put(c, "gba", "Zelda.gba")
    _put(c, "gba", "a.zip")
    _put(c, "genesis", "sf2.zip")
    ctl = EditorController(str(c))
    sysrows = {s.folder: s for s in ctl.get_systems()}
    assert all(isinstance(s, SystemRow) for s in sysrows.values())
    assert [s.folder for s in ctl.get_systems()] == sorted(sysrows)
    assert (sysrows["gba"].game_count, sysrows["genesis"].game_count, sysrows["badf"].game_count) == (2, 1, 0)
    assert sysrows["gblink"].ratio == "full" and sysrows["genesis"].ratio == "default" and sysrows["genesis"].quality == "default"
    msg = ctl.set_system_options("genesis", ratio="original", quality="sharp")
    assert HANGUL.search(msg)
    s2 = {s.folder: s for s in ctl.get_systems()}["genesis"]
    assert (s2.ratio, s2.quality) == ("original", "sharp")
    # make the two genesis elements disagree -> "mixed"
    p = xmlp(c)
    p.write_bytes(p.read_bytes().replace(b'folder="genesis" core="picodrive" stretchDisplay="false" smoothPixels="false" />',
                                         b'folder="genesis" core="picodrive" smoothPixels="false" />', 1))
    assert {s.folder: s for s in ctl.get_systems()}["genesis"].ratio == "mixed"
    with pytest.raises(ValueError):
        ctl.set_system_options("badf", ratio="full")
    with pytest.raises(ValueError):
        ctl.set_system_options("nope", ratio="full")


def test_controller_needs_card():
    ctl = EditorController()
    for call in (ctl.get_systems, lambda: ctl.set_game_options(["a.zip"], ratio="full"), lambda: ctl.set_system_options("gba", ratio="full")):
        with pytest.raises(ValueError):
            call()


def test_screen_text_hides_internal_names():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    banned = ("smoothPixels", "stretchDisplay", "disableForcedQualityFilter", "pandory.xml", "emulator", "integerScale")
    for f in ("editor/app/gui.py", "editor/app/guide.py"):
        tree = ast.parse(open(os.path.join(root, f), encoding="utf-8").read())
        bad = [n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str) and any(b in n.value for b in banned)]
        assert not bad, (f, bad)
    gui = open(os.path.join(root, "editor/app/gui.py"), encoding="utf-8").read()
    assert "화질" in gui and "기종별" in gui

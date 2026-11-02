# Acceptance tests.
import ast, dataclasses, os, re
import pytest
from editor.core import romsettings, card as ccard
from editor.app.controller import EditorController, GameRow

HANGUL = re.compile("[가-힣]")

TEMPLATE = (
    '<?xml version="1.0" encoding="UTF-8"?>\n'
    "<pandory>\n"
    "    <system>\n"
    '        <setting name="stretchDisplay" value="false" />\n'
    "    </system>\n"
    "    <emulators>\n"
    '        <emulator suffix="GBA" folder="gba" core="mgba" keymap="gba" />\n'
    "    </emulators>\n"
    '    <!-- Rom-specific: <rom name="decoy.zip" stretchDisplay="true" /> -->\n'
    "    <roms>\n"
    "        <!-- Custom cores for ports -->\n"
    '        <rom name="QuakeSW.zip" core="tyrquake"/>\n'
    '        <rom name="sf2.zip" speed="100" />\n'
    "        <rom name='single.zip' speed='50' />\n"
    '        <rom name="a.zip" stretchDisplay="false" speed="100" />\n'
    '        <rom name="b.zip" stretchDisplay="true"/>\n'
    '        <rom name="gt.zip" note="a>b" />\n'
    '        <rom name="xmen.zip" keymap="fbae-xmen"core="fba-external" />\n'
    '        <rom name="dup.zip" speed="1" />\n'
    '        <rom name="dup.zip" speed="2" />\n'
    "    </roms>\n"
    "</pandory>\n"
)


def make_card(tmp_path, nl="\n", xml=TEMPLATE):
    c = tmp_path / "card"
    for d in ("pandory", "roms", "roms_pandory/gba"):
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


# ---------- read ----------
def test_read_entries(tmp_path):
    c, _ = make_card(tmp_path)
    e = romsettings.read_rom_entries(str(c))
    assert "decoy.zip" not in e  # lives inside a comment
    assert e["xmen.zip"].broken is True
    assert {k for k, v in e.items() if v.broken} == {"xmen.zip"}
    assert e["single.zip"].attrib["speed"] == "50" and e["gt.zip"].attrib["note"] == "a>b"
    assert (e["sf2.zip"].ratio, e["a.zip"].ratio, e["b.zip"].ratio) == ("default", "original", "full")
    assert "dup.zip" in e


# ---------- edit: byte exact ----------
def test_add_attribute_keeps_everything_else(card_nl):
    c, before, nl = card_nl
    bak = romsettings.set_rom_ratio(str(c), "sf2.zip", "original")
    after = xmlp(c).read_bytes()
    assert after == before.replace(b'<rom name="sf2.zip" speed="100" />', b'<rom name="sf2.zip" speed="100" stretchDisplay="false" />', 1)
    assert bak and open(bak, "rb").read() == before


def test_add_attribute_on_selfclosing_without_space_and_single_quotes(card_nl):
    c, before, nl = card_nl
    romsettings.set_rom_ratio(str(c), "QuakeSW.zip", "full")
    romsettings.set_rom_ratio(str(c), "single.zip", "full")
    after = xmlp(c).read_bytes()
    exp = before.replace(b'<rom name="QuakeSW.zip" core="tyrquake"/>', b'<rom name="QuakeSW.zip" core="tyrquake" stretchDisplay="true"/>', 1)
    exp = exp.replace(b"<rom name='single.zip' speed='50' />", b"<rom name='single.zip' speed='50' stretchDisplay=\"true\" />", 1)
    assert after == exp


def test_element_with_gt_inside_attribute_value(card_nl):
    c, before, nl = card_nl
    romsettings.set_rom_ratio(str(c), "gt.zip", "original")
    assert xmlp(c).read_bytes() == before.replace(b'<rom name="gt.zip" note="a>b" />', b'<rom name="gt.zip" note="a>b" stretchDisplay="false" />', 1)


def test_replace_and_remove(card_nl):
    c, before, nl = card_nl
    romsettings.set_rom_ratio(str(c), "a.zip", "full")
    romsettings.set_rom_ratio(str(c), "b.zip", "original")
    exp = before.replace(b'<rom name="a.zip" stretchDisplay="false" speed="100" />', b'<rom name="a.zip" stretchDisplay="true" speed="100" />', 1)
    exp = exp.replace(b'<rom name="b.zip" stretchDisplay="true"/>', b'<rom name="b.zip" stretchDisplay="false"/>', 1)
    assert xmlp(c).read_bytes() == exp
    romsettings.set_rom_ratio(str(c), "a.zip", "default")
    romsettings.set_rom_ratio(str(c), "b.zip", "default")
    exp2 = before.replace(b'<rom name="a.zip" stretchDisplay="false" speed="100" />', b'<rom name="a.zip" speed="100" />', 1)
    exp2 = exp2.replace(b'<rom name="b.zip" stretchDisplay="true"/>', b'<rom name="b.zip"/>', 1)
    assert xmlp(c).read_bytes() == exp2  # the element itself is never deleted


def test_new_element_inserted_before_roms_close_with_file_newline(card_nl):
    c, before, nl = card_nl
    romsettings.set_rom_ratio(str(c), "New Game.zip", "full")
    exp = before.replace(b"    </roms>", b'        <rom name="New Game.zip" stretchDisplay="true" />' + nl + b"    </roms>", 1)
    assert xmlp(c).read_bytes() == exp
    e = romsettings.read_rom_entries(str(c))
    assert e["New Game.zip"].ratio == "full"


def test_name_only_in_comment_is_treated_as_new(card_nl):
    c, before, nl = card_nl
    romsettings.set_rom_ratio(str(c), "decoy.zip", "original")
    after = xmlp(c).read_bytes()
    assert b'<!-- Rom-specific: <rom name="decoy.zip" stretchDisplay="true" /> -->' in after  # comment untouched
    assert after.count(b'name="decoy.zip"') == 2 and romsettings.read_rom_entries(str(c))["decoy.zip"].ratio == "original"


def test_apostrophe_in_file_name_is_allowed(tmp_path):
    c, before = make_card(tmp_path)
    romsettings.set_rom_ratio(str(c), "Ghosts'n Goblins.zip", "original")
    assert b'<rom name="Ghosts\'n Goblins.zip" stretchDisplay="false" />' in xmlp(c).read_bytes()
    assert romsettings.read_rom_entries(str(c))["Ghosts'n Goblins.zip"].ratio == "original"


def test_other_entries_unchanged(tmp_path):
    c, _ = make_card(tmp_path)
    before = romsettings.read_rom_entries(str(c))
    romsettings.set_rom_ratio(str(c), "sf2.zip", "full")
    after = romsettings.read_rom_entries(str(c))
    for k, v in before.items():
        if k != "sf2.zip":
            assert after[k].attrib == v.attrib and after[k].broken == v.broken, k
    assert after["sf2.zip"].attrib["speed"] == "100" and after["sf2.zip"].ratio == "full"


# ---------- refusals: file stays byte-identical, no backup ----------
@pytest.mark.parametrize("name,state", [
    ("xmen.zip", "full"),  # already-broken line
    ("dup.zip", "full"),  # duplicated active entry
    ("", "full"), ("a/b.zip", "full"), ("a\\b.zip", "full"), ('a"b.zip', "full"), ("a<b.zip", "full"), ("a>b.zip", "full"),
    ("a&b.zip", "full"), ("a\nb.zip", "full"), ("a\x00b.zip", "full"),
    ("sf2.zip", "bogus"), ("sf2.zip", ""), ("sf2.zip", None),
])
def test_refusals_change_nothing(tmp_path, name, state):
    c, before = make_card(tmp_path)
    with pytest.raises(ValueError) as e:
        romsettings.set_rom_ratio(str(c), name, state)
    assert HANGUL.search(str(e.value))
    assert xmlp(c).read_bytes() == before and baks(c) == []


def test_no_change_writes_nothing(tmp_path):
    c, before = make_card(tmp_path)
    assert romsettings.set_rom_ratio(str(c), "a.zip", "original") is None  # already false
    assert romsettings.set_rom_ratio(str(c), "sf2.zip", "default") is None  # already default
    assert romsettings.set_rom_ratio(str(c), "not-there.zip", "default") is None  # nothing to remove
    assert xmlp(c).read_bytes() == before and baks(c) == []


def test_roms_block_must_be_exactly_one(tmp_path):
    for xml in (TEMPLATE.replace("    </roms>\n", ""), TEMPLATE.replace("<roms>", "<roms></roms>\n    <roms>", 1)):
        c, before = make_card(tmp_path / ("x%d" % hash(xml)), xml=xml)
        with pytest.raises(ValueError):
            romsettings.set_rom_ratio(str(c), "sf2.zip", "full")
        assert xmlp(c).read_bytes() == before


def test_bad_card(tmp_path):
    with pytest.raises(ccard.CardValidationError):
        romsettings.read_rom_entries(str(tmp_path))
    with pytest.raises(ccard.CardValidationError):
        romsettings.set_rom_ratio(str(tmp_path), "a.zip", "full")


# ---------- the real card file (copy of reference/pandory.xml) ----------
def test_real_card_xml_copy(tmp_path):
    ref = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "reference", "pandory.xml")
    orig = open(ref, "rb").read()
    c = tmp_path / "card"
    for d in ("pandory", "roms", "roms_pandory"):
        (c / d).mkdir(parents=True)
    xmlp(c).write_bytes(orig)
    e = romsettings.read_rom_entries(str(c))
    assert len(e) >= 900 and {k for k, v in e.items() if v.broken} == {"xmen.zip"}
    nl = b"\r\n" if b"\r\n" in orig else b"\n"
    romsettings.set_rom_ratio(str(c), "sf2.zip", "full")
    romsettings.set_rom_ratio(str(c), "A Brand New Game.zip", "original")
    new = xmlp(c).read_bytes()
    ol, nl_ = orig.split(nl), new.split(nl)
    assert len(nl_) == len(ol) + 1
    changed = [i for i, (a, b) in enumerate(zip(ol, nl_)) if a != b]
    assert any(b'name="sf2.zip"' in ol[i] for i in changed)
    assert b'keymap="fbae-xmen"core="fba-external"' in new  # broken line left exactly as it was
    with pytest.raises(ValueError):
        romsettings.set_rom_ratio(str(c), "xmen.zip", "full")
    assert open(str(c / "pandory" / "pandory.xml.bak"), "rb").read() == orig


# ---------- controller ----------
def test_gamerow_is_backward_compatible():
    fields = dataclasses.fields(GameRow)
    assert [f.name for f in fields][:5] == ["menu_no", "folder", "shown_title", "file_name", "raw_title"]
    assert fields[-1].name == "ratio" and fields[-1].default == "default"
    r = GameRow(9801, "gba", "[GBA] Z", "Zelda.gba", "Z")
    assert r.ratio == "default"


def test_controller_ratio_flow(tmp_path):
    c, _ = make_card(tmp_path)
    (c / "roms_pandory" / "gba" / "Zelda.gba").write_bytes(b"x")
    (c / "roms_pandory" / "gba" / "a.zip").write_bytes(b"x")
    ctl = EditorController(str(c))
    rows = {r.file_name: r for r in ctl.get_games()}
    assert rows["Zelda.gba"].ratio == "default" and rows["a.zip"].ratio == "original"
    msg = ctl.set_game_ratio("Zelda.gba", "full")
    assert HANGUL.search(msg) and "기기" in msg
    assert {r.file_name: r.ratio for r in ctl.get_games()}["Zelda.gba"] == "full"
    ctl.set_game_ratio("Zelda.gba", "default")
    assert {r.file_name: r.ratio for r in ctl.get_games()}["Zelda.gba"] == "default"
    with pytest.raises(ValueError):
        ctl.set_game_ratio("not-in-list.zip", "full")
    with pytest.raises(ValueError):
        ctl.set_game_ratio("Zelda.gba", "bogus")


def test_controller_needs_card():
    with pytest.raises(ValueError):
        EditorController().set_game_ratio("a.zip", "full")


def test_screen_text_has_no_internal_names():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for f in ("editor/app/gui.py", "editor/app/guide.py"):
        tree = ast.parse(open(os.path.join(root, f), encoding="utf-8").read())
        bad = [n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str)
               and ("stretchDisplay" in n.value or "pandory.xml" in n.value)]
        assert not bad, (f, bad)
    assert "화면 비율" in open(os.path.join(root, "editor/app/gui.py"), encoding="utf-8").read()

# Acceptance tests.
# Controller only; never opens a Tk window; never touches a real drive.
import os, re
import pytest
from editor.core import card as ccard
from editor.app.controller import EditorController, GameRow, ApplyResult, HookViewStatus

XML = """<?xml version="1.0"?>
<pandory><emulators>
    <emulator suffix="GBA" folder="gba" core="mgba" keymap="gba" />
    <emulator suffix="PICO" folder="genesis" core="picodrive" />
    <emulator suffix="X" folder="zzz" core="x" />
    <emulator suffix="Script" folder="scripts" core="shell"/>
</emulators></pandory>
"""
HANGUL = re.compile("[가-힣]")


@pytest.fixture
def fake(tmp_path):
    c = tmp_path / "card"
    (c / "pandory").mkdir(parents=True)
    (c / "roms").mkdir()
    (c / "roms_pandory").mkdir()
    (c / "pandory" / "pandory.xml").write_text(XML, encoding="utf-8")
    return c


def put(c, folder, name):
    d = c / "roms_pandory" / folder
    d.mkdir(parents=True, exist_ok=True)
    (d / name).write_bytes(b"x")


def mapfile(c):
    return (c / "pandory" / "names_map.txt").read_text(encoding="utf-8")


# ---- open / no card ----
def test_open_card_ok(fake):
    c = EditorController()
    assert not c.is_card_loaded()
    c.open_card(str(fake))
    assert c.is_card_loaded()
    c2 = EditorController(str(fake))
    assert c2.is_card_loaded()


def test_open_bad_card_keeps_previous(fake, tmp_path):
    c = EditorController(str(fake))
    with pytest.raises(ccard.CardValidationError):
        c.open_card(str(tmp_path))  # no card structure
    with pytest.raises(ccard.CardValidationError):
        c.open_card("C:\\")
    assert c.is_card_loaded()
    assert c.card_path == os.path.abspath(str(fake))


def test_no_card_raises_valueerror(tmp_path):
    c = EditorController()
    for call in (c.get_games, c.get_supported_folders, c.apply_patch, c.get_hook_status,
                 lambda: c.add_game("x.zip", "gba"), lambda: c.update_title("a.zip", "t")):
        with pytest.raises(ValueError):
            call()


# ---- list (read-only) ----
def test_get_games_readonly_and_tags(fake):
    put(fake, "genesis", "Sonic_1.zip")
    put(fake, "gba", "Zelda.gba")
    c = EditorController(str(fake))
    rows = c.get_games()
    assert [(r.menu_no, r.folder, r.file_name) for r in rows] == [(9801, "gba", "Zelda.gba"), (9802, "genesis", "Sonic_1.zip")]
    assert isinstance(rows[0], GameRow)
    assert rows[0].raw_title == "Zelda" and rows[0].shown_title == "[GBA] Zelda"
    assert rows[1].raw_title == "Sonic 1" and rows[1].shown_title == "[MD] Sonic 1"
    # reading must not write anything to the card
    assert not (fake / "pandory" / "names_map.txt").exists()
    assert not (fake / "pandory" / "patch.txt").exists()
    c.use_tags = False
    assert c.get_games()[0].shown_title == "Zelda"


def test_supported_folders(fake):
    assert EditorController(str(fake)).get_supported_folders() == ["gba", "genesis", "scripts", "zzz"]


def test_count_warning(fake):
    for i in range(240):
        put(fake, "genesis", "g%03d.zip" % i)
    c = EditorController(str(fake))
    assert c.get_game_count_warning() is None
    put(fake, "genesis", "g240.zip")
    w = c.get_game_count_warning()
    assert isinstance(w, str) and HANGUL.search(w)


# ---- add ----
def test_add_game(fake, tmp_path):
    put(fake, "gba", "Zelda.gba")
    src = tmp_path / "Sonic.zip"
    src.write_bytes(b"rom")
    c = EditorController(str(fake))
    row = c.add_game(str(src), "genesis", "소닉")
    assert isinstance(row, GameRow)
    assert (row.menu_no, row.folder, row.file_name, row.raw_title) == (9802, "genesis", "Sonic.zip", "소닉")
    assert (fake / "roms_pandory" / "genesis" / "Sonic.zip").exists() and src.exists()
    assert "Sonic.zip | 소닉" in mapfile(fake)
    with pytest.raises(FileExistsError):
        c.add_game(str(src), "genesis", "소닉2")


# ---- title edit ----
def test_update_title(fake):
    put(fake, "gba", "a.gba")
    put(fake, "gba", "b.gba")
    (fake / "pandory" / "names_map.txt").write_text("# my comment\na.gba | 에이\nb.gba | 비\n", encoding="utf-8", newline="\n")
    c = EditorController(str(fake))
    c.update_title("a.gba", "새 이름")
    m = mapfile(fake)
    assert m.splitlines()[0] == "# my comment" and "b.gba | 비" in m and "a.gba | 새 이름" in m
    assert [r.raw_title for r in c.get_games()] == ["새 이름", "비"]


def test_update_title_sanitizes_and_validates(fake):
    put(fake, "gba", "a.gba")
    c = EditorController(str(fake))
    c.update_title("a.gba", "A|B\nC\r")
    t = c.get_games()[0].raw_title
    assert "|" not in t and "\n" not in t and "\r" not in t
    assert len(mapfile(fake).strip().splitlines()) == 2  # header + one game; format intact
    for bad in ("", "   ", "|"):
        with pytest.raises(ValueError):
            c.update_title("a.gba", bad)
    with pytest.raises(ValueError):
        c.update_title("nope.gba", "x")


def test_title_warning(fake):
    c = EditorController(str(fake))
    c.use_tags = False
    assert c.title_warning("gba", "가" * 28) is None
    w = c.title_warning("gba", "가" * 29)
    assert isinstance(w, str) and HANGUL.search(w)
    c.use_tags = True  # "[GBA] " takes 6 characters
    assert c.title_warning("gba", "가" * 22) is None
    assert c.title_warning("gba", "가" * 23)


# ---- apply ----
def test_apply_patch(fake):
    put(fake, "gba", "a.gba")
    c = EditorController(str(fake))
    r = c.apply_patch(use_tags=False)
    assert isinstance(r, ApplyResult) and r.success and r.games_count == 1 and isinstance(r.warnings, list)
    assert c.use_tags is False  # the explicit choice sticks
    raw = (fake / "pandory" / "patch.txt").read_bytes()
    assert os.path.normcase(r.patch_path) == os.path.normcase(str(fake / "pandory" / "patch.txt"))
    assert raw and b"\x00" not in raw
    assert HANGUL.search(r.message)
    assert "[GBA]" not in c.get_games()[0].shown_title


# ---- hook ----
def test_hook_status(fake):
    c = EditorController(str(fake))
    s = c.get_hook_status()
    assert isinstance(s, HookViewStatus) and s.is_ok is False and s.status_label and HANGUL.search(s.details)
    buf = bytearray(b"\x00" * (0xE9C24 + 200))
    h = b"sh /mnt/sdcard/pandory/auto.sh >/dev/null 2>&1 &"
    buf[0xE9C24:0xE9C24 + len(h)] = h
    (fake / "pandory" / "pandory").write_bytes(bytes(buf))
    (fake / "pandory" / "auto.sh").write_text("#", encoding="utf-8")
    (fake / "pandory" / "patch.txt").write_text("x\n", encoding="utf-8")
    s2 = c.get_hook_status()
    assert s2.is_ok is True and s2.status_label != s.status_label


# ---- messages ----
def test_format_error_message():
    f = EditorController.format_error_message
    msgs = [f(ccard.CardValidationError("x")), f(FileExistsError("y")), f(ValueError("Extension '.exe' is forbidden.")), f(RuntimeError("boom"))]
    for m in msgs:
        assert isinstance(m, str) and HANGUL.search(m)
        assert "Traceback" not in m and "CardValidationError" not in m
    assert len(set(msgs[:3])) == 3  # the three known cases get distinct explanations
    assert f(ValueError("카드가 선택되지 않았습니다.")) and HANGUL.search(f(ValueError("카드가 선택되지 않았습니다.")))


# ---- gui import / entry points ----
def test_gui_import_has_no_side_effects():
    import tkinter
    import editor.app.gui as gui
    assert callable(gui.main)
    assert getattr(tkinter, "_default_root", None) is None  # no window created on import


def test_entry_files_exist():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    assert os.path.isfile(os.path.join(root, "run_editor.py"))
    assert os.path.isfile(os.path.join(root, "실행.bat"))

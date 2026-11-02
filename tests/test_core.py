# Acceptance tests.
# All tests use a fake card under tmp_path. Never touches a real drive.
import os, re
import pytest
from editor.core import card, backup, names, games, hook

XML = """<?xml version="1.0"?>
<pandory>
  <emulators>
    <emulator suffix="GBA" folder="gba" core="mgba" keymap="gba" />
    <emulator suffix="PICO" folder="genesis" core="picodrive" />
    <emulator suffix="X" folder="zzz" core="x" />
    <emulator suffix="Script" folder="scripts" core="shell"/>
  </emulators>
</pandory>
"""


@pytest.fixture
def fake(tmp_path):
    c = tmp_path / "card"
    (c / "pandory").mkdir(parents=True)
    (c / "roms").mkdir()
    (c / "roms_pandory").mkdir()
    (c / "pandory" / "pandory.xml").write_text(XML, encoding="utf-8")
    return c


def put(c, folder, name, data=b"x"):
    d = c / "roms_pandory" / folder
    d.mkdir(parents=True, exist_ok=True)
    (d / name).write_bytes(data)


def unoct(s):
    return bytes(int(x, 8) for x in re.findall(r"\\(\d{3})", s))


def mapfile(c):
    return (c / "pandory" / "names_map.txt").read_text(encoding="utf-8")


# ---------------- card ----------------
def test_card_ok(fake):
    got = card.validate_card_path(str(fake))
    assert os.path.normcase(got) == os.path.normcase(os.path.abspath(str(fake)))


def test_card_missing_structure(tmp_path):
    with pytest.raises(card.CardValidationError):
        card.validate_card_path(str(tmp_path))


def test_card_rejects_system_drive():
    with pytest.raises(card.CardValidationError):
        card.validate_card_path("C:\\")
    with pytest.raises(card.CardValidationError):
        card.validate_card_path("C:")


# ---------------- backup ----------------
def test_backup_chain(tmp_path):
    p = tmp_path / "f.txt"
    assert backup.write_with_backup(str(p), "one\n") is None
    b1 = backup.write_with_backup(str(p), "two\n")
    assert b1 and open(b1, encoding="utf-8").read() == "one\n"
    b2 = backup.write_with_backup(str(p), "three\n")
    assert b2 and b2 != b1 and open(b2, encoding="utf-8").read() == "two\n"
    assert open(b1, encoding="utf-8").read() == "one\n"  # old backup never destroyed
    assert p.read_text(encoding="utf-8") == "three\n"


def test_backup_identical_skips(tmp_path):
    p = tmp_path / "f.txt"
    backup.write_with_backup(str(p), "same\n")
    assert backup.write_with_backup(str(p), "same\n") is None
    assert sorted(x.name for x in tmp_path.iterdir()) == ["f.txt"]


def test_backup_forbid_nul(tmp_path):
    p = tmp_path / "f.txt"
    backup.write_with_backup(str(p), "ok\n")
    with pytest.raises(ValueError):
        backup.write_with_backup(str(p), b"bad\x00data", forbid_nul=True)
    assert p.read_text(encoding="utf-8") == "ok\n"
    backup.write_with_backup(str(tmp_path / "bin"), b"a\x00b")  # binary allowed by default
    assert (tmp_path / "bin").read_bytes() == b"a\x00b"


def test_backup_text_uses_lf(tmp_path):
    p = tmp_path / "f.txt"
    backup.write_with_backup(str(p), "a\nb\n")
    assert p.read_bytes() == b"a\nb\n"


# ---------------- names ----------------
def test_sort_order_and_skips(fake):
    # NTFS/FAT32 are case-insensitive: never put names differing only by case in one folder.
    # Byte order puts uppercase before lowercase ("B1" < "a1"), unlike case-insensitive order.
    for n in ("b2.zip", "B1.zip", "a1.zip", "notes.txt", ".hid"):
        put(fake, "genesis", n)
    put(fake, "gba", "z.gba")
    lst, warn = names.list_added_games(str(fake))
    assert lst == [("gba", "z.gba"), ("genesis", "B1.zip"), ("genesis", "a1.zip"), ("genesis", "b2.zip")]
    assert warn == []


def test_menu_numbers_tags_and_map(fake):
    put(fake, "gba", "My_Game.gba")
    put(fake, "genesis", "s.zip")
    put(fake, "zzz", "u.bin")
    r = names.generate_patch(str(fake))
    assert [x[0] for x in r.rows] == [9801, 9802, 9803]
    assert tuple(r.rows[0][1:]) == ("gba", "[GBA] My Game", "My_Game.gba")
    assert r.rows[1][2] == "[MD] s"
    assert r.rows[2][2] == "u"  # unknown folder -> no tag
    assert "My_Game.gba | My Game" in mapfile(fake)
    r2 = names.generate_patch(str(fake), use_tags=False)
    assert r2.rows[0][2] == "My Game"


def test_custom_title_preserved(fake):
    put(fake, "gba", "a.gba")
    (fake / "pandory" / "names_map.txt").write_text("a.gba | 내 게임\n", encoding="utf-8", newline="\n")
    r = names.generate_patch(str(fake))
    assert r.rows[0][2] == "[GBA] 내 게임"
    assert "a.gba | 내 게임" in mapfile(fake)


def test_patch_format_and_roundtrip(fake):
    put(fake, "gba", "a.gba")
    (fake / "pandory" / "names_map.txt").write_text("a.gba | 한글 Game\n", encoding="utf-8", newline="\n")
    names.generate_patch(str(fake), use_tags=False)
    raw = (fake / "pandory" / "patch.txt").read_bytes()
    assert b"\x00" not in raw and raw.endswith(b"\n") and b"\r" not in raw
    lines = raw.decode("ascii").splitlines()
    d = [l for l in lines if l.startswith("D 0 ")]
    assert [l.split(" ")[2] for l in d] == ["832", "896", "0", "192"]  # 0x340,0x380,0x000,0x0c0
    ko = unoct(d[1].split(" ", 3)[3])
    assert ko == "한글 Game".encode("utf-32le") + b"\0\0\0\0"
    en = unoct(d[0].split(" ", 3)[3])
    assert en == "한글 Game".encode("ascii", "replace") + b"\x00"
    static = [l for l in lines if not l.startswith("D ")]
    assert [int(l.split(" ")[0]) for l in static] == [0x2F618, 0x2F728, 0x2FA68, 0x31330]
    assert unoct(static[3].split(" ", 1)[1]) == b"\x00\x00\xa0\xe1"
    assert unoct(static[0].split(" ", 1)[1]) == b"\x00"


def test_over_240_warns_and_truncates(fake):
    for i in range(241):
        put(fake, "genesis", "g%03d.zip" % i)
    lst, warn = names.list_added_games(str(fake))
    assert len(lst) == 240 and warn
    r = names.generate_patch(str(fake))
    assert len(r.rows) == 240 and r.warnings


# ---------------- games ----------------
def test_add_game(fake, tmp_path):
    src = tmp_path / "Sonic.zip"
    src.write_bytes(b"rom")
    r = games.add_game(str(fake), str(src), "genesis", display_title="소닉")
    assert os.path.isfile(r.dest_path) and src.exists()
    assert r.folder == "genesis" and r.filename == "Sonic.zip" and r.title == "소닉"
    assert "Sonic.zip | 소닉" in mapfile(fake)


def test_add_game_refuses_overwrite(fake, tmp_path):
    put(fake, "genesis", "Sonic.zip", b"old")
    src = tmp_path / "Sonic.zip"
    src.write_bytes(b"new")
    with pytest.raises(FileExistsError):
        games.add_game(str(fake), str(src), "genesis")
    assert (fake / "roms_pandory" / "genesis" / "Sonic.zip").read_bytes() == b"old"


def test_add_game_bad_folder_and_ext(fake, tmp_path):
    ok = tmp_path / "a.zip"
    ok.write_bytes(b"1")
    with pytest.raises(ValueError):
        games.add_game(str(fake), str(ok), "not_in_xml")
    for bad in ("a.txt", "a.exe", "a.bat"):
        p = tmp_path / bad
        p.write_bytes(b"1")
        with pytest.raises(ValueError):
            games.add_game(str(fake), str(p), "genesis")
    gdir = fake / "roms_pandory" / "genesis"
    assert not gdir.exists() or not list(gdir.iterdir())


# ---------------- hook ----------------
HOOK = b"sh /mnt/sdcard/pandory/auto.sh >/dev/null 2>&1 &"
ORIG = b'find /tmp -name "*.zip.dat" -exec bash -c'


def make_bin(fake, text):
    buf = bytearray(b"\x00" * (0xE9C24 + 200))
    buf[0xE9C24:0xE9C24 + len(text)] = text
    (fake / "pandory" / "pandory").write_bytes(bytes(buf))


def test_hook_installed(fake):
    make_bin(fake, HOOK)
    (fake / "pandory" / "auto.sh").write_text("#", encoding="utf-8")
    before = (fake / "pandory" / "pandory").read_bytes()
    s = hook.check_hook(str(fake))
    assert s.pandory_bin_exists and s.hook_installed and s.auto_sh_exists and not s.patch_txt_exists
    assert (fake / "pandory" / "pandory").read_bytes() == before  # read-only


def test_hook_original_and_missing(fake):
    make_bin(fake, ORIG)
    assert hook.check_hook(str(fake)).hook_installed is False
    (fake / "pandory" / "pandory").unlink()
    s = hook.check_hook(str(fake))
    assert not s.pandory_bin_exists and not s.hook_installed

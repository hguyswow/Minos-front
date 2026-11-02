# Acceptance tests.
import datetime, hashlib, json, os, re, zipfile
import pytest
from editor.core import snapshot, card as ccard
from editor.app.controller import EditorController

HANGUL = re.compile("[가-힣]")
NAME_RE = re.compile(r"^판도라백업_\d{8}_\d{6}\.zip$")

# files on the fake card -> (included in snapshot?)
FILES = {
    "pandory/pandory.xml": (b"<pandory/>", True),
    "pandory/auto.sh": (b"#!/bin/sh\n", True),
    "pandory/patch.txt": (b"D 0 832 x\n", True),
    "pandory/names_map.txt": (b"a.gba | A\n", True),
    "pandory/collections/a.cfg": (b"cfg", True),
    "pandory/pandory": (b"BIN" * 300, True),
    "roms_pandory/scripts/00_Names.sh": (b"sh1", True),
    "roms_pandory/scripts/한글 스크립트.sh": (b"sh2", True),
    "roms_pandory/scripts_off/old.sh": (b"sh3", True),
    "user_bg.bmp": (b"BM" + b"\x00" * 50, True),
    "music/bg.mp3": (b"mp3", True),
    # excluded
    "pandory/cores/big.so": (b"so", False),
    "pandory/debug.log": (b"log", False),
    "pandory/x.lock": (b"lock", False),
    "pandory/pandory.xml.bak": (b"old", False),
    "pandory/pandory.xml.bak1": (b"old1", False),
    "roms_pandory/genesis/Sonic.zip": (b"rom", False),
    "roms/0000.zip": (b"rom", False),
    "demo.avi": (b"avi", False),
    "autorun.inf": (b"inf", False),
    "rb_arr.bin": (b"bin", False),
    "music/other.mp3": (b"m", False),
    "movies/x.avi": (b"mv", False),
    "pandory_backups/orig.zip": (b"z", False),
}
INCLUDED = {k for k, (_, inc) in FILES.items() if inc}


def sha(b):
    return hashlib.sha256(b).hexdigest()


@pytest.fixture
def fake(tmp_path):
    c = tmp_path / "card"
    for rel, (data, _) in FILES.items():
        p = c / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
    (c / "roms").mkdir(exist_ok=True)
    (c / "roms_pandory").mkdir(exist_ok=True)
    return c


@pytest.fixture
def clock(monkeypatch):
    state = {"t": datetime.datetime(2026, 11, 1, 12, 0, 0)}
    monkeypatch.setattr(snapshot, "_now", lambda: state["t"])
    return state


def tree(c):
    out = {}
    for dp, _, fs in os.walk(c):
        for f in fs:
            p = os.path.join(dp, f)
            out[os.path.relpath(p, c).replace("\\", "/")] = open(p, "rb").read()
    return out


def mk_zip(path, entries, manifest_paths=None, tamper=None):
    """Build a snapshot-like zip with a CORRECT manifest for the given entries (unless tamper is given)."""
    files = [{"path": k, "size": len(v), "sha256": sha(v)} for k, v in entries.items()]
    man = {"created_at": "2026-11-01T12:00:00", "card_path": "X", "app_version": "t", "files": files, "skipped": []}
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("manifest.json", json.dumps(man, ensure_ascii=False))
        for k, v in entries.items():
            z.writestr(k, (tamper or {}).get(k, v))
    return str(path)


# ---------- create ----------
def test_create_snapshot_contents(fake, tmp_path, clock):
    dest = tmp_path / "bk"
    z = snapshot.create_snapshot(str(fake), str(dest))
    assert os.path.dirname(os.path.abspath(z)) == os.path.abspath(str(dest))
    assert NAME_RE.match(os.path.basename(z)) and "20261101_120000" in z
    with zipfile.ZipFile(z) as zf:
        names = set(zf.namelist())
        assert names == INCLUDED | {"manifest.json"}
        man = json.loads(zf.read("manifest.json").decode("utf-8"))
        assert {f["path"] for f in man["files"]} == INCLUDED
        for f in man["files"]:
            assert f["sha256"] == sha(FILES[f["path"]][0]) and f["size"] == len(FILES[f["path"]][0])
        assert zf.read("roms_pandory/scripts/한글 스크립트.sh") == b"sh2"


def test_create_skips_over_50mb_and_records_it(fake, tmp_path, clock):
    with open(fake / "pandory" / "huge.bin", "wb") as f:
        f.truncate(51 * 1024 * 1024)
    z = snapshot.create_snapshot(str(fake), str(tmp_path / "bk"))
    with zipfile.ZipFile(z) as zf:
        assert "pandory/huge.bin" not in zf.namelist()
        man = json.loads(zf.read("manifest.json").decode("utf-8"))
    assert any("huge.bin" in str(s) for s in man["skipped"])


def test_same_name_refused(fake, tmp_path, clock):
    dest = tmp_path / "bk"
    z = snapshot.create_snapshot(str(fake), str(dest))
    before = open(z, "rb").read()
    with pytest.raises(ValueError) as e:
        snapshot.create_snapshot(str(fake), str(dest))
    assert HANGUL.search(str(e.value))
    assert open(z, "rb").read() == before


def test_create_does_not_modify_card(fake, tmp_path, clock):
    before = tree(fake)
    snapshot.create_snapshot(str(fake), str(tmp_path / "bk"))
    assert tree(fake) == before


def test_bad_card_rejected(tmp_path, clock):
    with pytest.raises(ccard.CardValidationError):
        snapshot.create_snapshot(str(tmp_path), str(tmp_path / "bk"))


# ---------- list ----------
def test_list_snapshots(fake, tmp_path, clock):
    dest = tmp_path / "bk"
    assert snapshot.list_snapshots(str(dest)) == []  # missing dir is fine
    z1 = snapshot.create_snapshot(str(fake), str(dest))
    clock["t"] += datetime.timedelta(minutes=5)
    z2 = snapshot.create_snapshot(str(fake), str(dest))
    (dest / "broken.zip").write_bytes(b"not a zip at all")
    (dest / "notes.txt").write_text("x")
    infos = snapshot.list_snapshots(str(dest))
    assert [os.path.basename(i.file_path) for i in infos[:2]] == [os.path.basename(z2), os.path.basename(z1)]  # newest first
    good = infos[0]
    assert good.is_valid and good.file_count == len(INCLUDED) and good.file_size > 0 and good.file_name == os.path.basename(z2)
    bad = [i for i in infos if i.file_name == "broken.zip"]
    assert len(bad) == 1 and bad[0].is_valid is False and bad[0].file_count == -1
    assert all(i.file_name != "notes.txt" for i in infos)


# ---------- preview ----------
def test_preview_classifies_and_writes_nothing(fake, tmp_path, clock):
    z = snapshot.create_snapshot(str(fake), str(tmp_path / "bk"))
    (fake / "pandory" / "names_map.txt").write_bytes(b"changed\n")  # overwrite
    os.remove(fake / "pandory" / "patch.txt")  # new
    before = tree(fake)
    plan = snapshot.preview_restore(str(fake), z)
    assert tree(fake) == before
    assert plan.new_files == ["pandory/patch.txt"]
    assert plan.overwrite_files == ["pandory/names_map.txt"]
    assert len(plan.identical_files) == len(INCLUDED) - 2
    assert plan.total_restore_count == 2 and plan.zip_path == z


# ---------- restore ----------
def test_restore_roundtrip_safety_snapshot_and_no_deletes(fake, tmp_path, clock):
    z = snapshot.create_snapshot(str(fake), str(tmp_path / "bk"))
    (fake / "pandory" / "names_map.txt").write_bytes(b"changed\n")
    os.remove(fake / "pandory" / "patch.txt")
    (fake / "roms_pandory" / "scripts" / "한글 스크립트.sh").write_bytes(b"EDITED")
    (fake / "pandory" / "extra.txt").write_bytes(b"not in backup")
    clock["t"] += datetime.timedelta(minutes=10)
    safety = tmp_path / "safe"
    r = snapshot.restore_snapshot(str(fake), z, str(safety))
    assert r.success and r.restored_count == 3 and HANGUL.search(r.message)
    for rel in INCLUDED:
        assert (fake / rel).read_bytes() == FILES[rel][0], rel
    assert (fake / "pandory" / "extra.txt").read_bytes() == b"not in backup"  # nothing deleted
    assert os.path.isfile(r.safety_backup_path) and os.path.dirname(os.path.abspath(r.safety_backup_path)) == os.path.abspath(str(safety))
    with zipfile.ZipFile(r.safety_backup_path) as zf:  # captured the state BEFORE restoring
        assert zf.read("pandory/names_map.txt") == b"changed\n"
        assert zf.read("roms_pandory/scripts/한글 스크립트.sh") == b"EDITED"
    leftovers = [p for p in tree(fake) if "tmp_restore" in p]
    assert leftovers == []
    # excluded stuff never touched
    assert (fake / "roms_pandory" / "genesis" / "Sonic.zip").read_bytes() == b"rom"


def test_restore_rejects_tampered_zip_without_any_write(fake, tmp_path, clock):
    entries = {"pandory/names_map.txt": b"good\n"}
    z = mk_zip(tmp_path / "t.zip", entries, tamper={"pandory/names_map.txt": b"EVIL\n"})
    before = tree(fake)
    safety = tmp_path / "safe"
    with pytest.raises(ValueError) as e:
        snapshot.restore_snapshot(str(fake), z, str(safety))
    assert HANGUL.search(str(e.value))
    assert tree(fake) == before and not safety.exists() or not list(safety.iterdir())
    with pytest.raises(ValueError):
        snapshot.preview_restore(str(fake), z)


@pytest.mark.parametrize("evil", [
    "../evil.txt", "pandory/../../evil.txt", "/evil.txt", "C:/evil.txt", "C:\\evil.txt",
    "roms/0000.zip", "roms_pandory/genesis/x.zip", "autorun.inf", "music/other.mp3", "demo.avi",
])
def test_restore_rejects_paths_outside_allowlist(fake, tmp_path, clock, evil):
    z = mk_zip(tmp_path / "e.zip", {"pandory/names_map.txt": b"ok\n", evil: b"x"})
    before = tree(fake)
    with pytest.raises(ValueError):
        snapshot.restore_snapshot(str(fake), z, str(tmp_path / "safe"))
    assert tree(fake) == before
    assert not (tmp_path / "evil.txt").exists() and not (fake.parent / "evil.txt").exists()


def mk_zip_manifest_only(path, entries, extra_manifest_paths):
    """Manifest lists extra paths that have NO matching zip entry."""
    files = [{"path": k, "size": len(v), "sha256": sha(v)} for k, v in entries.items()]
    files += [{"path": p, "size": 1, "sha256": sha(b"a")} for p in extra_manifest_paths]
    man = {"created_at": "2026-11-01T12:00:00", "card_path": "X", "app_version": "t", "files": files, "skipped": []}
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("manifest.json", json.dumps(man, ensure_ascii=False))
        for k, v in entries.items():
            z.writestr(k, v)
    return str(path)


@pytest.mark.parametrize("ghost", [
    "../OUTSIDE_DIR/evil.txt", "pandory/../../OUTSIDE_DIR/evil.txt", "/OUTSIDE_DIR/evil.txt", "C:/OUTSIDE_DIR/evil.txt",
    "roms/ghost.zip", "autorun.inf",
    "pandory/ghost.txt",  # allowed path, but the zip has no such entry -> manifest and zip must agree
])
def test_manifest_paths_are_validated_too(fake, tmp_path, clock, ghost):
    z = mk_zip_manifest_only(tmp_path / "m.zip", {"pandory/names_map.txt": b"ok\n"}, [ghost])
    before = tree(fake)
    top_before = sorted(os.listdir(tmp_path))
    with pytest.raises(ValueError) as e:
        snapshot.preview_restore(str(fake), z)
    assert HANGUL.search(str(e.value))
    with pytest.raises(ValueError):
        snapshot.restore_snapshot(str(fake), z, str(tmp_path / "safe"))
    assert tree(fake) == before
    assert not (tmp_path / "OUTSIDE_DIR").exists() and not (fake.parent / "OUTSIDE_DIR").exists()
    assert sorted(os.listdir(tmp_path)) == top_before  # no safety dir, no stray folders anywhere next to the card


def test_restore_not_a_zip_or_no_manifest(fake, tmp_path, clock):
    bad = tmp_path / "bad.zip"
    bad.write_bytes(b"garbage")
    with pytest.raises(ValueError):
        snapshot.restore_snapshot(str(fake), str(bad), str(tmp_path / "s"))
    nom = tmp_path / "nom.zip"
    with zipfile.ZipFile(nom, "w") as z:
        z.writestr("pandory/names_map.txt", b"x")
    with pytest.raises(ValueError):
        snapshot.restore_snapshot(str(fake), str(nom), str(tmp_path / "s"))


def test_restore_failure_rolls_back(fake, tmp_path, clock):
    z = snapshot.create_snapshot(str(fake), str(tmp_path / "bk"))
    # make several files differ so they would be overwritten ...
    (fake / "pandory" / "auto.sh").write_bytes(b"MOD1")
    (fake / "pandory" / "patch.txt").write_bytes(b"MOD2")
    (fake / "user_bg.bmp").write_bytes(b"MOD3")
    # ... and make one target impossible to write: a directory sits where a file must go
    os.remove(fake / "music" / "bg.mp3")
    os.makedirs(fake / "music" / "bg.mp3")
    (fake / "music" / "bg.mp3" / "inner.txt").write_bytes(b"i")
    before = tree(fake)
    clock["t"] += datetime.timedelta(minutes=1)
    with pytest.raises(Exception):
        snapshot.restore_snapshot(str(fake), z, str(tmp_path / "safe"))
    after = tree(fake)
    assert {k: v for k, v in after.items() if "tmp_restore" not in k} == before  # everything back to pre-restore state
    assert not [k for k in after if "tmp_restore" in k]


# ---------- controller ----------
def test_controller_backup_flow(fake, tmp_path, clock):
    c = EditorController(str(fake))
    d = str(tmp_path / "bk")
    z = c.make_backup(d)
    assert os.path.isfile(z)
    infos = c.get_backups(d)
    assert len(infos) == 1 and infos[0].is_valid
    (fake / "pandory" / "names_map.txt").write_bytes(b"changed\n")
    plan = c.plan_restore(z)
    assert plan.overwrite_files == ["pandory/names_map.txt"]
    clock["t"] += datetime.timedelta(minutes=1)
    r = c.restore_backup(z, safety_dir=str(tmp_path / "safe"))
    assert r.success and HANGUL.search(r.message)
    assert (fake / "pandory" / "names_map.txt").read_bytes() == FILES["pandory/names_map.txt"][0]


def test_controller_default_dir_and_needs_card(tmp_path):
    c = EditorController()
    assert c.get_default_backup_dir().replace("\\", "/").endswith("/판도라백업")
    for call in (lambda: c.make_backup(str(tmp_path / "x")), lambda: c.plan_restore("z.zip"),
                 lambda: c.restore_backup("z.zip", safety_dir=str(tmp_path))):
        with pytest.raises(ValueError):
            call()

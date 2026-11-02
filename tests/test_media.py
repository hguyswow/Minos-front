# Acceptance tests.
# Skipped automatically when ffmpeg is not installed. Never touches a real drive or the user's Documents folder.
import datetime, os, re, struct, subprocess
import pytest
from editor.core import media, card as ccard
from editor.app.controller import EditorController

FFMPEG = media.find_ffmpeg()
pytestmark = pytest.mark.skipif(FFMPEG is None, reason="ffmpeg not installed")
HANGUL = re.compile("[가-힣]")

DEMO = {  # card file -> (w, h) the device expects
    "demo.avi": (1280, 720), "demo_en.avi": (1280, 720),
    "demo_384x224.avi": (384, 224), "demo_en_384x224.avi": (384, 224),
    "demo_640x480.avi": (640, 480), "demo_en_640x480.avi": (640, 480),
    "demo_1024x600.avi": (1024, 768), "demo_en_1024x600.avi": (1024, 768),
}


def ff(*args):
    subprocess.run([FFMPEG, "-v", "error", "-y", *args], check=True)


@pytest.fixture(scope="module")
def src(tmp_path_factory):
    d = tmp_path_factory.mktemp("src")
    s = {}
    s["red_sq"] = str(d / "red_800x800.png")
    ff("-f", "lavfi", "-i", "color=c=red:s=800x800", "-frames:v", "1", s["red_sq"])
    s["photo"] = str(d / "photo 한글 1920x1080.jpg")  # korean + spaces in the path on purpose
    ff("-f", "lavfi", "-i", "testsrc2=s=1920x1080", "-frames:v", "1", "-q:v", "3", s["photo"])
    s["vid_audio"] = str(d / "v_audio.mp4")
    ff("-f", "lavfi", "-i", "testsrc2=s=640x360:r=25", "-f", "lavfi", "-i", "sine=f=440:sample_rate=44100",
       "-t", "2", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", s["vid_audio"])
    s["vid_silent"] = str(d / "v_silent.mp4")
    ff("-f", "lavfi", "-i", "testsrc2=s=320x240:r=25", "-t", "2", "-c:v", "libx264", "-pix_fmt", "yuv420p", s["vid_silent"])
    s["vid_long"] = str(d / "v_long.mp4")
    ff("-f", "lavfi", "-i", "testsrc2=s=160x90:r=5", "-t", "35", "-c:v", "libx264", "-pix_fmt", "yuv420p", s["vid_long"])
    s["wav_mono"] = str(d / "mono.wav")
    ff("-f", "lavfi", "-i", "sine=f=262:sample_rate=8000", "-t", "2", "-ac", "1", s["wav_mono"])
    s["garbage"] = str(d / "garbage.png")
    open(s["garbage"], "wb").write(b"this is not an image" * 50)
    return s


@pytest.fixture
def clock(monkeypatch):
    st = {"t": datetime.datetime(2026, 11, 1, 13, 0, 0)}
    monkeypatch.setattr(media, "_now", lambda: st["t"])
    return st


@pytest.fixture
def fake(tmp_path):
    c = tmp_path / "card"
    for d in ("pandory", "roms", "roms_pandory", "music"):
        (c / d).mkdir(parents=True)
    (c / "pandory" / "pandory.xml").write_text("<pandory/>", encoding="utf-8")
    (c / "user_bg.bmp").write_bytes(b"OLDBMP")
    (c / "music" / "bg.mp3").write_bytes(b"OLDMP3")
    for n in DEMO:
        (c / n).write_bytes(b"OLD:" + n.encode())
    return c


def tree(c):
    out = {}
    for dp, _, fs in os.walk(c):
        for f in fs:
            p = os.path.join(dp, f)
            out[os.path.relpath(p, c).replace("\\", "/")] = open(p, "rb").read()
    return out


def bmp_pixel(path, x, y):
    d = open(path, "rb").read()
    off, = struct.unpack("<I", d[10:14])
    w, h = struct.unpack("<ii", d[18:26])
    bpp, = struct.unpack("<H", d[28:30])
    assert bpp == 24 and w == 1280 and abs(h) == 720
    stride = ((w * 3 + 3) // 4) * 4
    row = (h - 1 - y) if h > 0 else y
    b, g, r = d[off + row * stride + x * 3: off + row * stride + x * 3 + 3]
    return r, g, b


# ---------- ffmpeg / probe ----------
def test_find_ffmpeg_and_probe(src):
    assert os.path.isfile(FFMPEG) and media.find_ffprobe() and os.path.isfile(media.find_ffprobe())
    i = media.probe(src["photo"])
    assert (i.kind, i.width, i.height) == ("image", 1920, 1080)
    v = media.probe(src["vid_audio"])
    assert v.kind == "video" and (v.width, v.height) == (640, 360) and v.duration == pytest.approx(2, abs=0.5)
    a = media.probe(src["wav_mono"])
    assert a.kind == "audio" and a.channels == 1 and a.sample_rate == 8000


# ---------- background ----------
@pytest.mark.parametrize("mode", ["fit", "fill", "stretch"])
def test_background_spec_and_modes(src, tmp_path, mode):
    out = str(tmp_path / "o.bmp")
    media.convert_background(src["red_sq"], out, mode)
    i = media.probe(out)
    assert (i.codec_name, i.pix_fmt, i.width, i.height) == ("bmp", "bgr24", 1280, 720)
    left = bmp_pixel(out, 10, 360)
    centre = bmp_pixel(out, 640, 360)
    corner = bmp_pixel(out, 10, 10)
    assert centre[0] > 200 and centre[1] < 40 and centre[2] < 40  # red in the middle in every mode
    if mode == "fit":  # 800x800 -> 720x720 centred, black bars left/right
        assert max(left) < 20 and max(corner) < 20
    else:  # fill / stretch cover the whole picture
        assert left[0] > 200 and corner[0] > 200


def test_background_from_korean_spaced_path(src, tmp_path):
    out = str(tmp_path / "한글 출력.bmp")
    media.convert_background(src["photo"], out, "fit")
    assert media.probe(out).width == 1280


# ---------- music ----------
def test_music_spec(src, tmp_path):
    out = str(tmp_path / "o.mp3")
    media.convert_music(src["wav_mono"], out)
    i = media.probe(out)
    assert (i.kind, i.codec_name, i.sample_rate, i.channels) == ("audio", "mp3", 44100, 2)


# ---------- demo video ----------
@pytest.mark.parametrize("w,h", [(384, 224), (640, 480), (1024, 768), (1280, 720)])
def test_demo_video_spec(src, tmp_path, w, h):
    out = str(tmp_path / "o.avi")
    media.convert_demo_video(src["vid_audio"], out, w, h, "fit")
    i = media.probe(out)
    assert (i.codec_name, i.pix_fmt, i.width, i.height) == ("mpeg4", "yuv420p", w, h)
    assert i.frame_rate == pytest.approx(24, abs=0.1)
    assert (i.audio_codec, i.sample_rate, i.channels) == ("mp3", 48000, 2)
    assert i.duration == pytest.approx(2, abs=0.5)


def test_demo_video_without_audio_gets_silent_track(src, tmp_path):
    out = str(tmp_path / "o.avi")
    media.convert_demo_video(src["vid_silent"], out, 640, 480, "fill")
    i = media.probe(out)
    assert (i.audio_codec, i.sample_rate, i.channels) == ("mp3", 48000, 2)


def test_demo_video_capped_at_30_seconds(src, tmp_path):
    out = str(tmp_path / "o.avi")
    media.convert_demo_video(src["vid_long"], out, 384, 224, "stretch")
    assert media.probe(out).duration <= 30.6


def test_bad_input_raises_korean_and_leaves_nothing(src, tmp_path):
    out = tmp_path / "o.bmp"
    with pytest.raises(ValueError) as e:
        media.convert_background(src["garbage"], str(out), "fit")
    assert HANGUL.search(str(e.value)) and not out.exists()
    outv = tmp_path / "o.avi"
    with pytest.raises(ValueError):
        media.convert_demo_video(src["garbage"], str(outv), 640, 480, "fit")
    assert not outv.exists()
    with pytest.raises(ValueError):
        media.convert_background(src["photo"], str(tmp_path / "x.bmp"), "bogus-mode")


# ---------- install onto the card ----------
def test_install_background_backs_up_on_pc_not_card(fake, src, tmp_path, clock):
    bk = tmp_path / "bk"
    folder = media.install_background(str(fake), src["photo"], "fit", backup_dir=str(bk))
    i = media.probe(str(fake / "user_bg.bmp"))
    assert (i.width, i.height, i.pix_fmt) == (1280, 720, "bgr24")
    assert os.path.isdir(folder) and os.path.dirname(os.path.abspath(folder)) == os.path.abspath(str(bk))
    assert os.path.basename(folder) == "미디어원본_20261101_130000"
    assert open(os.path.join(folder, "user_bg.bmp"), "rb").read() == b"OLDBMP"
    leftovers = [k for k in tree(fake) if ".bak" in k or "tmp_media" in k]
    assert leftovers == []  # nothing extra on the card


def test_install_music(fake, src, tmp_path, clock):
    folder = media.install_music(str(fake), src["wav_mono"], backup_dir=str(tmp_path / "bk"))
    i = media.probe(str(fake / "music" / "bg.mp3"))
    assert (i.codec_name, i.sample_rate, i.channels) == ("mp3", 44100, 2)
    assert open(os.path.join(folder, "music", "bg.mp3"), "rb").read() == b"OLDMP3"


def test_install_demo_subset_only_touches_chosen_files(fake, src, tmp_path, clock):
    before = tree(fake)
    chosen = ["demo_640x480.avi", "demo_en_640x480.avi"]
    folder = media.install_demo_videos(str(fake), src["vid_audio"], chosen, "fit", backup_dir=str(tmp_path / "bk"))
    after = tree(fake)
    for n in DEMO:
        if n in chosen:
            assert after[n] != before[n]
            i = media.probe(str(fake / n))
            assert (i.width, i.height, i.codec_name) == (640, 480, "mpeg4")
            assert open(os.path.join(folder, n), "rb").read() == before[n]
        else:
            assert after[n] == before[n]
    assert after["user_bg.bmp"] == before["user_bg.bmp"]


def test_1024x600_files_are_converted_to_1024x768_and_demo_to_1280x720(fake, src, tmp_path, clock):
    media.install_demo_videos(str(fake), src["vid_audio"], ["demo_1024x600.avi", "demo.avi"], "fill", backup_dir=str(tmp_path / "bk"))
    a = media.probe(str(fake / "demo_1024x600.avi"))
    b = media.probe(str(fake / "demo.avi"))
    assert (a.width, a.height) == (1024, 768) and (b.width, b.height) == (1280, 720)


@pytest.mark.parametrize("bad", [["../evil.avi"], ["demo_9.avi"], ["user_bg.bmp"], ["demo.avi", "pandory/pandory.xml"], []])
def test_install_demo_rejects_unknown_targets(fake, src, tmp_path, clock, bad):
    before = tree(fake)
    with pytest.raises(ValueError) as e:
        media.install_demo_videos(str(fake), src["vid_audio"], bad, "fit", backup_dir=str(tmp_path / "bk"))
    assert HANGUL.search(str(e.value))
    assert tree(fake) == before and not (tmp_path / "bk").exists()
    assert not (tmp_path.parent / "evil.avi").exists()


def test_failed_conversion_changes_nothing(fake, src, tmp_path, clock):
    before = tree(fake)
    with pytest.raises(ValueError):
        media.install_background(str(fake), src["garbage"], "fit", backup_dir=str(tmp_path / "bk"))
    with pytest.raises(ValueError):
        media.install_demo_videos(str(fake), src["garbage"], ["demo.avi"], "fit", backup_dir=str(tmp_path / "bk"))
    assert tree(fake) == before and not (tmp_path / "bk").exists()


def test_same_second_never_overwrites_a_saved_original(fake, src, tmp_path, clock):
    bk = str(tmp_path / "bk")
    f1 = media.install_background(str(fake), src["photo"], "fit", backup_dir=bk)
    try:
        f2 = media.install_background(str(fake), src["red_sq"], "fit", backup_dir=bk)
    except ValueError:
        f2 = None
    assert open(os.path.join(f1, "user_bg.bmp"), "rb").read() == b"OLDBMP"  # first original is intact
    assert f2 is None or os.path.abspath(f2) != os.path.abspath(f1)


def test_ffmpeg_missing_and_bad_card(fake, src, tmp_path, monkeypatch):
    with pytest.raises(ccard.CardValidationError):
        media.install_background(str(tmp_path), src["photo"], "fit", backup_dir=str(tmp_path / "bk"))
    monkeypatch.setattr(media, "find_ffmpeg", lambda: None)
    before = tree(fake)
    with pytest.raises(media.FfmpegNotFoundError) as e:
        media.install_background(str(fake), src["photo"], "fit", backup_dir=str(tmp_path / "bk"))
    assert isinstance(e.value, ValueError) and HANGUL.search(str(e.value)) and "ffmpeg" in str(e.value).lower()
    assert tree(fake) == before


def test_list_and_restore_originals(fake, src, tmp_path, clock):
    bk = str(tmp_path / "bk")
    media.install_background(str(fake), src["photo"], "fit", backup_dir=bk)
    items = media.list_media_originals(bk)
    assert len(items) == 1 and items[0].files == ["user_bg.bmp"] and items[0].folder_name == "미디어원본_20261101_130000"
    assert media.list_media_originals(str(tmp_path / "nonexistent")) == []
    clock["t"] += datetime.timedelta(minutes=5)
    new_bytes = (fake / "user_bg.bmp").read_bytes()
    media.restore_media_original(str(fake), items[0].folder_path, safety_backup_dir=bk)
    assert (fake / "user_bg.bmp").read_bytes() == b"OLDBMP"
    items2 = media.list_media_originals(bk)
    assert len(items2) == 2  # the replaced (new) file was kept too, so undo is itself undoable
    saved = [open(os.path.join(i.folder_path, "user_bg.bmp"), "rb").read() for i in items2]
    assert new_bytes in saved
    assert [k for k in tree(fake) if ".bak" in k or "tmp_media" in k] == []


# ---------- preview ----------
def test_preview_png(src, tmp_path):
    for kind, s in (("image", src["photo"]), ("video", src["vid_audio"])):
        out = str(tmp_path / ("p_%s.png" % kind))
        media.make_preview_image(s, out, kind, "fit")
        i = media.probe(out)
        assert (i.codec_name, i.width, i.height) == ("png", 640, 360)


# ---------- controller ----------
def test_controller_media_flow(fake, src, tmp_path, clock):
    c = EditorController(str(fake))
    c.media_backup_dir = str(tmp_path / "bk")
    st = c.get_media_status()
    assert st.has_ffmpeg and st.ffmpeg_path and "demo.avi" in st.demo_infos
    msg = c.apply_background(src["photo"], "fill")
    assert isinstance(msg, str) and HANGUL.search(msg)
    assert c.get_media_status().background_info.width == 1280
    assert isinstance(c.apply_music(src["wav_mono"]), str)
    clock["t"] += datetime.timedelta(minutes=1)
    msg = c.apply_demo_video(src["vid_audio"], ["demo_384x224.avi"], "fit")
    assert HANGUL.search(msg)
    prev = c.make_preview_png(src["photo"], "image", "fit")
    assert os.path.isfile(prev) and media.probe(prev).width == 640
    folder = media.list_media_originals(c.media_backup_dir)[-1].folder_path
    clock["t"] += datetime.timedelta(minutes=1)
    assert HANGUL.search(c.undo_media(folder))


def test_controller_defaults_and_needs_card(tmp_path):
    c = EditorController()
    assert c.get_default_media_backup_dir().replace("\\", "/").endswith("/판도라백업")
    for call in (c.get_media_status, lambda: c.apply_background("x.png", "fit"), lambda: c.apply_music("x.mp3"),
                 lambda: c.apply_demo_video("x.mp4", ["demo.avi"], "fit"), lambda: c.undo_media(str(tmp_path))):
        with pytest.raises(ValueError):
            call()

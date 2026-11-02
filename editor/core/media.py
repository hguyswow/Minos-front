"""Core module for Pandora Saga media customization (background, demo video, music)."""
import datetime
import glob
import json
import os
import re
import shutil
import subprocess
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

from editor.core.card import validate_card_path

DEMO_TARGETS: dict[str, tuple[int, int]] = {
    "demo.avi": (1280, 720),
    "demo_en.avi": (1280, 720),
    "demo_384x224.avi": (384, 224),
    "demo_en_384x224.avi": (384, 224),
    "demo_640x480.avi": (640, 480),
    "demo_en_640x480.avi": (640, 480),
    "demo_1024x600.avi": (1024, 768),
    "demo_en_1024x600.avi": (1024, 768),
}

MAX_MEDIA_SIZE = 100 * 1024 * 1024  # 100 MB


class FfmpegNotFoundError(ValueError):
    """Raised when ffmpeg is not found on the system."""

    pass


def _now() -> datetime.datetime:
    """Return current timestamp. Monkeypatched by tests."""
    return datetime.datetime.now()


def find_ffmpeg() -> Optional[str]:
    """Locate ffmpeg binary via env, PATH, or WinGet package directories."""
    env_p = os.environ.get("PANDORA_FFMPEG")
    if env_p and os.path.isfile(env_p):
        return env_p

    which_p = shutil.which("ffmpeg")
    if which_p and os.path.isfile(which_p):
        return which_p

    local_app_data = os.environ.get("LOCALAPPDATA", "")
    if local_app_data:
        pattern = os.path.join(
            local_app_data,
            "Microsoft",
            "WinGet",
            "Packages",
            "*FFmpeg*",
            "*",
            "bin",
            "ffmpeg.exe",
        )
        matches = glob.glob(pattern)
        if matches:
            return matches[0]

    return None


def find_ffprobe() -> Optional[str]:
    """Locate ffprobe binary via env, PATH, or WinGet package directories."""
    env_p = os.environ.get("PANDORA_FFPROBE")
    if env_p and os.path.isfile(env_p):
        return env_p

    ffmpeg_p = find_ffmpeg()
    if ffmpeg_p:
        probe_candidate = os.path.join(os.path.dirname(ffmpeg_p), "ffprobe.exe")
        if os.path.isfile(probe_candidate):
            return probe_candidate
        probe_cand2 = os.path.join(os.path.dirname(ffmpeg_p), "ffprobe")
        if os.path.isfile(probe_cand2):
            return probe_cand2

    which_p = shutil.which("ffprobe")
    if which_p and os.path.isfile(which_p):
        return which_p

    return None


def _require_ffmpeg() -> str:
    f = find_ffmpeg()
    if not f:
        raise FfmpegNotFoundError(
            "ffmpeg 변환 프로그램이 설치되어 있지 않습니다. winget install Gyan.FFmpeg 등을 통해 설치해 주세요."
        )
    return f


def _require_ffprobe() -> str:
    p = find_ffprobe()
    if not p:
        raise FfmpegNotFoundError(
            "ffprobe 분석 프로그램이 설치되어 있지 않습니다. ffmpeg와 함께 설치해 주세요."
        )
    return p


@dataclass
class MediaInfo:
    kind: str
    width: Optional[int] = None
    height: Optional[int] = None
    duration: Optional[float] = None
    codec_name: str = ""
    pix_fmt: str = ""
    frame_rate: Optional[float] = None
    audio_codec: str = ""
    sample_rate: Optional[int] = None
    channels: Optional[int] = None
    bit_rate: Optional[int] = None
    fourcc: str = ""


@dataclass
class MediaStatus:
    has_ffmpeg: bool
    ffmpeg_path: Optional[str]
    ffprobe_path: Optional[str]
    background_info: Optional[MediaInfo] = None
    music_info: Optional[MediaInfo] = None
    demo_infos: dict[str, Optional[MediaInfo]] = field(default_factory=dict)


@dataclass
class OriginalBackupItem:
    folder_name: str
    folder_path: str
    created_at: str
    files: list[str] = field(default_factory=list)


def probe(path: str) -> MediaInfo:
    """Analyze media file using ffprobe and return MediaInfo."""
    if not os.path.isfile(path):
        raise ValueError(f"파일을 찾을 수 없습니다: {path}")

    probe_exe = _require_ffprobe()

    cmd = [
        probe_exe,
        "-v",
        "error",
        "-print_format",
        "json",
        "-show_format",
        "-show_streams",
        path,
    ]

    try:
        res = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=True,
        )
        data = json.loads(res.stdout)
    except Exception as ex:
        raise ValueError(f"미디어 파일 정보를 읽을 수 없습니다: {ex}") from ex

    streams = data.get("streams", [])
    format_info = data.get("format", {})

    v_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
    a_stream = next((s for s in streams if s.get("codec_type") == "audio"), None)

    if not v_stream and not a_stream:
        raise ValueError(f"올바른 오디오나 비디오 스트림이 없습니다: {path}")

    # Determine kind
    kind = "unknown"
    duration = None
    if "duration" in format_info:
        try:
            duration = float(format_info["duration"])
        except (ValueError, TypeError):
            pass

    if v_stream:
        v_codec = v_stream.get("codec_name", "").lower()
        fmt_name = format_info.get("format_name", "").lower()
        nb_frames = v_stream.get("nb_frames")
        ext = os.path.splitext(path)[1].lower()
        is_img_codec = v_codec in (
            "bmp",
            "png",
            "jpeg",
            "jpg",
            "mjpeg",
            "webp",
            "gif",
            "tiff",
            "tga",
        )
        is_img_format = "pipe" in fmt_name or "image" in fmt_name or fmt_name in ("mjpeg", "png", "bmp")
        is_short_or_single = nb_frames == "1" or duration is None or duration <= 0.05
        is_img_ext = ext in (".bmp", ".png", ".jpg", ".jpeg", ".webp", ".gif", ".tiff")

        if is_img_codec and (is_img_format or is_short_or_single or is_img_ext):
            kind = "image"
        else:
            kind = "video"
    elif a_stream:
        kind = "audio"

    # Frame rate
    frame_rate = None
    if v_stream and "r_frame_rate" in v_stream:
        rf = v_stream["r_frame_rate"]
        if "/" in rf:
            num, den = rf.split("/", 1)
            try:
                den_f = float(den)
                if den_f > 0:
                    frame_rate = float(num) / den_f
            except (ValueError, ZeroDivisionError):
                pass
        else:
            try:
                frame_rate = float(rf)
            except ValueError:
                pass

    return MediaInfo(
        kind=kind,
        width=v_stream.get("width") if v_stream else None,
        height=v_stream.get("height") if v_stream else None,
        duration=duration,
        codec_name=v_stream.get("codec_name", "") if v_stream else (a_stream.get("codec_name", "") if a_stream else ""),
        pix_fmt=v_stream.get("pix_fmt", "") if v_stream else "",
        frame_rate=frame_rate,
        audio_codec=a_stream.get("codec_name", "") if a_stream else "",
        sample_rate=int(a_stream["sample_rate"]) if a_stream and "sample_rate" in a_stream else None,
        channels=int(a_stream["channels"]) if a_stream and "channels" in a_stream else None,
        bit_rate=int(format_info.get("bit_rate", 0)) if format_info.get("bit_rate") else None,
        fourcc=v_stream.get("codec_tag_string", "") if v_stream else "",
    )


def _build_filter(w: int, h: int, mode: str) -> str:
    """Build ffmpeg video filter string for fit/fill/stretch."""
    if mode == "stretch":
        return f"scale={w}:{h}"
    elif mode == "fit":
        return f"scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:black"
    elif mode == "fill":
        return f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h}"
    else:
        raise ValueError(f"지원하지 않는 화면 맞춤 방식입니다: {mode}")


def convert_background(src: str, out_bmp: str, mode: str = "fit") -> str:
    """Convert input image to 1280x720 24bit BMP."""
    if mode not in ("fit", "fill", "stretch"):
        raise ValueError(f"지원하지 않는 화면 맞춤 방식입니다: {mode}")

    ffmpeg = _require_ffmpeg()
    vf = _build_filter(1280, 720, mode)

    out_dir = os.path.dirname(out_bmp)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    cmd = [ffmpeg, "-v", "error", "-y", "-i", src, "-vf", vf, "-pix_fmt", "bgr24", out_bmp]

    try:
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        info = probe(out_bmp)
        if info.codec_name != "bmp" or info.pix_fmt != "bgr24" or info.width != 1280 or info.height != 720:
            raise ValueError("배경 이미지 변환 규격이 올바르지 않습니다.")
    except Exception as ex:
        if os.path.exists(out_bmp):
            try:
                os.remove(out_bmp)
            except Exception:
                pass
        raise ValueError(f"배경 이미지 변환에 실패했습니다: {ex}") from ex

    return out_bmp


def convert_music(src: str, out_mp3: str) -> str:
    """Convert audio to 44100Hz 2ch stereo MP3."""
    ffmpeg = _require_ffmpeg()

    out_dir = os.path.dirname(out_mp3)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    cmd = [
        ffmpeg,
        "-v",
        "error",
        "-y",
        "-i",
        src,
        "-vn",
        "-c:a",
        "libmp3lame",
        "-ar",
        "44100",
        "-ac",
        "2",
        "-b:a",
        "192k",
        out_mp3,
    ]

    try:
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        info = probe(out_mp3)
        if info.codec_name != "mp3" or info.sample_rate != 44100 or info.channels != 2:
            raise ValueError("음악 변환 규격이 올바르지 않습니다.")
    except Exception as ex:
        if os.path.exists(out_mp3):
            try:
                os.remove(out_mp3)
            except Exception:
                pass
        raise ValueError(f"음악 파일 변환에 실패했습니다: {ex}") from ex

    return out_mp3


def convert_demo_video(src: str, out_avi: str, width: int, height: int, mode: str = "fit") -> str:
    """Convert video to mpeg4 (XVID) yuv420p 24fps with mp3 48000Hz stereo audio."""
    if mode not in ("fit", "fill", "stretch"):
        raise ValueError(f"지원하지 않는 화면 맞춤 방식입니다: {mode}")

    ffmpeg = _require_ffmpeg()
    src_info = probe(src)

    vf = _build_filter(width, height, mode)

    out_dir = os.path.dirname(out_avi)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    has_audio = bool(src_info.audio_codec)

    if has_audio:
        cmd = [
            ffmpeg,
            "-v",
            "error",
            "-y",
            "-i",
            src,
            "-t",
            "30",
            "-vf",
            vf,
            "-r",
            "24",
            "-c:v",
            "mpeg4",
            "-vtag",
            "XVID",
            "-pix_fmt",
            "yuv420p",
            "-b:v",
            "1800k",
            "-c:a",
            "libmp3lame",
            "-ar",
            "48000",
            "-ac",
            "2",
            "-b:a",
            "96k",
            out_avi,
        ]
    else:
        # Generate silent stereo track
        cmd = [
            ffmpeg,
            "-v",
            "error",
            "-y",
            "-i",
            src,
            "-f",
            "lavfi",
            "-i",
            "anullsrc=channel_layout=stereo:sample_rate=48000",
            "-t",
            "30",
            "-shortest",
            "-vf",
            vf,
            "-r",
            "24",
            "-c:v",
            "mpeg4",
            "-vtag",
            "XVID",
            "-pix_fmt",
            "yuv420p",
            "-b:v",
            "1800k",
            "-c:a",
            "libmp3lame",
            "-ar",
            "48000",
            "-ac",
            "2",
            "-b:a",
            "96k",
            out_avi,
        ]

    try:
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        info = probe(out_avi)
        if (
            info.codec_name != "mpeg4"
            or info.pix_fmt != "yuv420p"
            or info.width != width
            or info.height != height
            or abs((info.frame_rate or 0) - 24.0) > 0.5
            or info.audio_codec != "mp3"
            or info.sample_rate != 48000
            or info.channels != 2
        ):
            raise ValueError("대기 영상 변환 규격이 올바르지 않습니다.")
    except Exception as ex:
        if os.path.exists(out_avi):
            try:
                os.remove(out_avi)
            except Exception:
                pass
        raise ValueError(f"대기 영상 변환에 실패했습니다: {ex}") from ex

    return out_avi


def _prepare_backup_folder(dest_parent: str) -> str:
    """Create a new unique backup directory under dest_parent."""
    os.makedirs(dest_parent, exist_ok=True)
    t = _now()
    base_name = f"미디어원본_{t.strftime('%Y%m%d_%H%M%S')}"
    target_dir = os.path.join(dest_parent, base_name)
    if os.path.exists(target_dir):
        idx = 1
        while os.path.exists(f"{target_dir}_{idx}"):
            idx += 1
        target_dir = f"{target_dir}_{idx}"
    os.makedirs(target_dir, exist_ok=True)
    return os.path.abspath(target_dir)


def install_background(
    card_path: str, src: str, mode: str = "fit", backup_dir: Optional[str] = None
) -> str:
    """Convert and install user_bg.bmp to card root, saving old file to backup_dir."""
    card_path = validate_card_path(card_path)
    _require_ffmpeg()

    if not backup_dir:
        backup_dir = os.path.join(os.path.expanduser("~"), "Documents", "판도라백업")

    # 1. Convert to temporary file
    tmp_out = os.path.join(card_path, f".tmp_media_{uuid.uuid4().hex}.bmp")
    try:
        convert_background(src, tmp_out, mode)

        # 2. Backup old file on PC if present
        card_dest = os.path.join(card_path, "user_bg.bmp")
        folder = _prepare_backup_folder(backup_dir)

        if os.path.isfile(card_dest):
            shutil.copy2(card_dest, os.path.join(folder, "user_bg.bmp"))

        # 3. Atomic replace on card
        os.replace(tmp_out, card_dest)
        return folder
    finally:
        if os.path.exists(tmp_out):
            try:
                os.remove(tmp_out)
            except Exception:
                pass


def install_music(
    card_path: str, src: str, backup_dir: Optional[str] = None
) -> str:
    """Convert and install music/bg.mp3 to card, saving old file to backup_dir."""
    card_path = validate_card_path(card_path)
    _require_ffmpeg()

    if not backup_dir:
        backup_dir = os.path.join(os.path.expanduser("~"), "Documents", "판도라백업")

    music_dir = os.path.join(card_path, "music")
    os.makedirs(music_dir, exist_ok=True)

    tmp_out = os.path.join(music_dir, f".tmp_media_{uuid.uuid4().hex}.mp3")
    try:
        convert_music(src, tmp_out)

        card_dest = os.path.join(music_dir, "bg.mp3")
        folder = _prepare_backup_folder(backup_dir)

        if os.path.isfile(card_dest):
            dest_backup_dir = os.path.join(folder, "music")
            os.makedirs(dest_backup_dir, exist_ok=True)
            shutil.copy2(card_dest, os.path.join(dest_backup_dir, "bg.mp3"))

        os.replace(tmp_out, card_dest)
        return folder
    finally:
        if os.path.exists(tmp_out):
            try:
                os.remove(tmp_out)
            except Exception:
                pass


def install_demo_videos(
    card_path: str,
    src: str,
    targets: list[str],
    mode: str = "fit",
    backup_dir: Optional[str] = None,
) -> str:
    """Convert and install selected demo AVI files onto card root."""
    card_path = validate_card_path(card_path)
    _require_ffmpeg()

    if not targets:
        raise ValueError("변경할 대기 영상 대상 목록이 비어 있습니다.")

    for t in targets:
        if t not in DEMO_TARGETS:
            raise ValueError(f"지원하지 않거나 올바르지 않은 대기 영상 대상입니다: {t}")

    if not backup_dir:
        backup_dir = os.path.join(os.path.expanduser("~"), "Documents", "판도라백업")

    # 1. Convert all targets to temp files first
    converted_temps: list[tuple[str, str]] = []  # (tmp_path, target_name)
    try:
        for t in targets:
            w, h = DEMO_TARGETS[t]
            tmp_out = os.path.join(card_path, f".tmp_media_{uuid.uuid4().hex}_{t}")
            convert_demo_video(src, tmp_out, w, h, mode)
            converted_temps.append((tmp_out, t))

        # 2. All conversions succeeded; create backup folder and copy old files
        folder = _prepare_backup_folder(backup_dir)
        for _, t in converted_temps:
            card_file = os.path.join(card_path, t)
            if os.path.isfile(card_file):
                shutil.copy2(card_file, os.path.join(folder, t))

        # 3. Replace files on card
        for tmp_out, t in converted_temps:
            card_file = os.path.join(card_path, t)
            os.replace(tmp_out, card_file)

        return folder
    finally:
        for tmp_out, _ in converted_temps:
            if os.path.exists(tmp_out):
                try:
                    os.remove(tmp_out)
                except Exception:
                    pass


def list_media_originals(backup_dir: str) -> list[OriginalBackupItem]:
    """List original media backup folders in backup_dir, sorted oldest first (alphabetical)."""
    if not os.path.isdir(backup_dir):
        return []

    items: list[OriginalBackupItem] = []
    for dname in sorted(os.listdir(backup_dir)):
        if not dname.startswith("미디어원본_"):
            continue
        dpath = os.path.join(backup_dir, dname)
        if not os.path.isdir(dpath):
            continue

        # Collect relative files inside
        files: list[str] = []
        for root, _, filenames in os.walk(dpath):
            for f in sorted(filenames):
                p = os.path.join(root, f)
                rel = os.path.relpath(p, dpath).replace("\\", "/")
                files.append(rel)

        items.append(
            OriginalBackupItem(
                folder_name=dname,
                folder_path=dpath,
                created_at=dname.replace("미디어원본_", ""),
                files=files,
            )
        )

    items.sort(key=lambda x: x.folder_name)
    return items


def restore_media_original(
    card_path: str, item_path: str, safety_backup_dir: Optional[str] = None
) -> str:
    """Restore previously backed up original media files back to the card."""
    card_path = validate_card_path(card_path)

    if not os.path.isdir(item_path):
        raise ValueError(f"보관 폴더를 찾을 수 없습니다: {item_path}")

    if not safety_backup_dir:
        safety_backup_dir = os.path.dirname(os.path.abspath(item_path))

    # Collect files to restore
    files_to_restore: list[tuple[str, str]] = []  # (abs_item_file, rel_path)
    for root, _, filenames in os.walk(item_path):
        for f in sorted(filenames):
            p = os.path.join(root, f)
            rel = os.path.relpath(p, item_path).replace("\\", "/")
            files_to_restore.append((p, rel))

    if not files_to_restore:
        raise ValueError("보관 폴더 안에 복원할 파일이 없습니다.")

    # 1. Capture current card state to a new safety folder
    safety_folder = _prepare_backup_folder(safety_backup_dir)
    for _, rel in files_to_restore:
        card_dest = os.path.join(card_path, rel)
        if os.path.isfile(card_dest):
            safe_dest = os.path.join(safety_folder, rel)
            os.makedirs(os.path.dirname(safe_dest), exist_ok=True)
            shutil.copy2(card_dest, safe_dest)

    # 2. Stage and replace onto card
    temp_files: list[tuple[str, str]] = []
    try:
        for src_file, rel in files_to_restore:
            card_dest = os.path.join(card_path, rel)
            os.makedirs(os.path.dirname(card_dest), exist_ok=True)
            tmp_dest = os.path.join(
                os.path.dirname(card_dest), f".tmp_media_{uuid.uuid4().hex}"
            )
            shutil.copy2(src_file, tmp_dest)
            temp_files.append((tmp_dest, card_dest))

        for tmp_dest, card_dest in temp_files:
            os.replace(tmp_dest, card_dest)
    finally:
        for tmp_dest, _ in temp_files:
            if os.path.exists(tmp_dest):
                try:
                    os.remove(tmp_dest)
                except Exception:
                    pass

    return safety_folder


def make_preview_image(src: str, out_png: str, kind: str, mode: str = "fit") -> str:
    """Generate 640x360 PNG preview for Tkinter display."""
    ffmpeg = _require_ffmpeg()
    vf = _build_filter(640, 360, mode)

    out_dir = os.path.dirname(out_png)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    cmd = [ffmpeg, "-v", "error", "-y", "-i", src, "-vf", vf, "-vframes", "1", out_png]

    try:
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except Exception as ex:
        if os.path.exists(out_png):
            try:
                os.remove(out_png)
            except Exception:
                pass
        raise ValueError(f"미리보기 생성에 실패했습니다: {ex}") from ex

    return out_png

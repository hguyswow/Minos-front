"""Core module for Pandora Saga card snapshot backup and restore."""
import datetime
import hashlib
import json
import os
import re
import uuid
import zipfile
from dataclasses import dataclass, field
from typing import Any, Optional

from editor.core.card import validate_card_path

APP_VERSION = "1.0.0"
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB


def _now() -> datetime.datetime:
    """Return current timestamp. Monkeypatched by tests."""
    return datetime.datetime.now()


def _sha256(data: bytes) -> str:
    """Return hex SHA-256 digest of data."""
    return hashlib.sha256(data).hexdigest()


def is_allowed_path(rel_path: str) -> bool:
    """Return whether the relative POSIX path is allowed for backup/restore.
    Rules:
    - user_bg.bmp (exact file in root)
    - music/bg.mp3 (exact file in music/)
    - roms_pandory/scripts/** (any file in scripts/)
    - roms_pandory/scripts_off/** (any file in scripts_off/)
    - pandory/** except:
        - pandory/cores/**
        - *.bak*
        - *.lock
        - *.log
    """
    rel = rel_path.replace("\\", "/")
    if rel == "user_bg.bmp":
        return True
    if rel == "music/bg.mp3":
        return True
    if rel.startswith("roms_pandory/scripts/"):
        return True
    if rel.startswith("roms_pandory/scripts_off/"):
        return True
    if rel.startswith("pandory/"):
        if rel.startswith("pandory/cores/"):
            return False
        base = os.path.basename(rel)
        if ".bak" in base:
            return False
        if base.endswith(".lock"):
            return False
        if base.endswith(".log"):
            return False
        return True
    return False


def validate_entry_path(path: str) -> str:
    """Validate relative path for ZipSlip, forbidden characters, and allowed whitelist.
    Returns normalized POSIX path, or raises ValueError.
    """
    posix_path = path.replace("\\", "/")
    parts = posix_path.split("/")
    if ".." in parts or posix_path.startswith("/") or ":" in posix_path:
        raise ValueError(f"위험하거나 올바르지 않은 경로가 포함되어 있습니다: {path}")

    if not is_allowed_path(posix_path):
        raise ValueError(f"허용되지 않은 파일 경로가 포함되어 있습니다: {path}")

    return posix_path


@dataclass
class SnapshotInfo:
    file_name: str
    file_path: str
    created_at: str
    file_size: int
    file_count: int
    is_valid: bool
    app_version: str = ""
    description: str = ""


@dataclass
class RestorePlan:
    zip_path: str
    new_files: list[str] = field(default_factory=list)
    overwrite_files: list[str] = field(default_factory=list)
    identical_files: list[str] = field(default_factory=list)
    total_restore_count: int = 0
    skipped_files: list[str] = field(default_factory=list)


@dataclass
class RestoreResult:
    success: bool
    restored_count: int
    safety_backup_path: str
    message: str


def create_snapshot(card_path: str, dest_dir: str, prefix: str = "판도라백업_") -> str:
    """Create a ZIP snapshot of allowed configuration and script files from the card.
    Saves to dest_dir with name f"{prefix}{YYYYMMDD_HHMMSS}.zip".
    If identical filename already exists, raises ValueError.
    Returns absolute path of the created ZIP.
    """
    card_path = validate_card_path(card_path)
    os.makedirs(dest_dir, exist_ok=True)

    t = _now()
    timestamp_str = t.strftime("%Y%m%d_%H%M%S")
    zip_name = f"{prefix}{timestamp_str}.zip"
    dest_path = os.path.join(dest_dir, zip_name)

    if os.path.exists(dest_path):
        raise ValueError(f"이미 동일한 이름의 백업 파일이 존재합니다: {zip_name}")

    # Gather files
    files_to_pack: list[tuple[str, str, int, bytes]] = []  # (abs_path, rel_path, size, data)
    skipped_list: list[dict[str, Any]] = []

    for root, _, filenames in os.walk(card_path):
        for f in sorted(filenames):
            abs_p = os.path.join(root, f)
            rel_p = os.path.relpath(abs_p, card_path).replace("\\", "/")
            if is_allowed_path(rel_p):
                size = os.path.getsize(abs_p)
                if size > MAX_FILE_SIZE:
                    skipped_list.append({"path": rel_p, "size": size, "reason": "50MB 초과"})
                else:
                    with open(abs_p, "rb") as fp:
                        data = fp.read()
                    files_to_pack.append((abs_p, rel_p, size, data))

    # Build manifest
    manifest_files = [
        {"path": rel, "size": size, "sha256": _sha256(data)}
        for _, rel, size, data in files_to_pack
    ]
    manifest = {
        "created_at": t.isoformat(),
        "card_path": os.path.abspath(card_path),
        "app_version": APP_VERSION,
        "files": manifest_files,
        "skipped": skipped_list,
    }

    manifest_bytes = json.dumps(manifest, ensure_ascii=False, indent=2).encode("utf-8")

    # Write ZIP atomically
    tmp_dest = os.path.join(dest_dir, f".tmp_create_{uuid.uuid4().hex}.zip")
    try:
        with zipfile.ZipFile(tmp_dest, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            # manifest.json
            zinfo_m = zipfile.ZipInfo("manifest.json", date_time=t.timetuple()[:6])
            zinfo_m.flag_bits |= 0x800
            zf.writestr(zinfo_m, manifest_bytes)

            for _, rel, _, data in files_to_pack:
                zinfo = zipfile.ZipInfo(rel, date_time=t.timetuple()[:6])
                zinfo.flag_bits |= 0x800
                zf.writestr(zinfo, data)

        os.replace(tmp_dest, dest_path)
    except Exception:
        if os.path.exists(tmp_dest):
            try:
                os.remove(tmp_dest)
            except Exception:
                pass
        raise

    return os.path.abspath(dest_path)


def list_snapshots(dest_dir: str) -> list[SnapshotInfo]:
    """List valid and invalid ZIP backups in dest_dir, ordered newest first."""
    if not os.path.isdir(dest_dir):
        return []

    results: list[SnapshotInfo] = []
    entries = sorted(os.listdir(dest_dir))

    for fname in entries:
        if not fname.lower().endswith(".zip"):
            continue
        full_p = os.path.join(dest_dir, fname)
        if not os.path.isfile(full_p):
            continue

        size = os.path.getsize(full_p)
        if not zipfile.is_zipfile(full_p):
            results.append(
                SnapshotInfo(
                    file_name=fname,
                    file_path=full_p,
                    created_at="",
                    file_size=size,
                    file_count=-1,
                    is_valid=False,
                    description="손상된 ZIP 파일",
                )
            )
            continue

        try:
            with zipfile.ZipFile(full_p, "r") as zf:
                if "manifest.json" not in zf.namelist():
                    results.append(
                        SnapshotInfo(
                            file_name=fname,
                            file_path=full_p,
                            created_at="",
                            file_size=size,
                            file_count=-1,
                            is_valid=False,
                            description="manifest.json 없음",
                        )
                    )
                    continue

                man_raw = zf.read("manifest.json").decode("utf-8", errors="replace")
                man = json.loads(man_raw)
                created = man.get("created_at", "")
                files = man.get("files", [])
                results.append(
                    SnapshotInfo(
                        file_name=fname,
                        file_path=full_p,
                        created_at=created,
                        file_size=size,
                        file_count=len(files),
                        is_valid=True,
                        app_version=man.get("app_version", ""),
                    )
                )
        except Exception:
            results.append(
                SnapshotInfo(
                    file_name=fname,
                    file_path=full_p,
                    created_at="",
                    file_size=size,
                    file_count=-1,
                    is_valid=False,
                    description="백업 정보 파싱 실패",
                )
            )

    # Sort newest first: using created_at / timestamp in filename, broken files last
    def _sort_key(s: SnapshotInfo):
        if s.created_at:
            return (1, s.created_at)
        m = re.search(r"\d{8}_\d{6}", s.file_name)
        if m:
            return (1, m.group(0))
        return (0, "")

    results.sort(key=_sort_key, reverse=True)
    return results


def preview_restore(card_path: str, zip_path: str) -> RestorePlan:
    """Validate ZIP integrity, check path safety, and calculate differences without writing."""
    card_path = validate_card_path(card_path)

    if not os.path.isfile(zip_path) or not zipfile.is_zipfile(zip_path):
        raise ValueError(f"올바른 백업 ZIP 파일이 아닙니다: {zip_path}")

    try:
        zf = zipfile.ZipFile(zip_path, "r")
    except Exception as ex:
        raise ValueError(f"백업 파일을 열 수 없습니다: {ex}")

    with zf:
        if "manifest.json" not in zf.namelist():
            raise ValueError("백업 파일에 안내 정보(manifest.json)가 누락되어 있습니다.")

        try:
            man_raw = zf.read("manifest.json").decode("utf-8")
            man = json.loads(man_raw)
        except Exception as ex:
            raise ValueError(f"백업 안내 정보를 읽을 수 없습니다: {ex}")

        # 1. Validate manifest files structure and paths
        manifest_files: dict[str, dict[str, Any]] = {}
        for item in man.get("files", []):
            p = item.get("path", "")
            norm_p = validate_entry_path(p)
            manifest_files[norm_p] = item

        # 2. Validate zip entries paths
        zip_entries = {
            name.replace("\\", "/")
            for name in zf.namelist()
            if name != "manifest.json"
        }
        for name in zip_entries:
            validate_entry_path(name)

        # 3. Manifest file set and ZIP entry set must match exactly
        if set(manifest_files.keys()) != zip_entries:
            raise ValueError("백업 파일 목록(manifest)과 압축 파일의 항목 목록이 일치하지 않습니다.")

        # 4. Check SHA-256 hash for each entry
        for name in sorted(zip_entries):
            expected_sha = manifest_files[name]["sha256"]
            data = zf.read(name)
            if _sha256(data) != expected_sha:
                raise ValueError(f"백업 파일의 내용이 변조되었습니다: {name}")

        new_files: list[str] = []
        overwrite_files: list[str] = []
        identical_files: list[str] = []

        for rel in sorted(manifest_files.keys()):
            card_file = os.path.join(card_path, rel)
            if not os.path.exists(card_file):
                new_files.append(rel)
            else:
                try:
                    with open(card_file, "rb") as fp:
                        card_data = fp.read()
                    if _sha256(card_data) == manifest_files[rel]["sha256"]:
                        identical_files.append(rel)
                    else:
                        overwrite_files.append(rel)
                except Exception:
                    overwrite_files.append(rel)

        skipped = [s["path"] if isinstance(s, dict) else str(s) for s in man.get("skipped", [])]

        return RestorePlan(
            zip_path=zip_path,
            new_files=new_files,
            overwrite_files=overwrite_files,
            identical_files=identical_files,
            total_restore_count=len(new_files) + len(overwrite_files),
            skipped_files=skipped,
        )


def restore_snapshot(card_path: str, zip_path: str, safety_dir: str) -> RestoreResult:
    """Restore card settings from a backup ZIP.
    1. Validates ZIP and manifest completely before any write.
    2. Creates a safety snapshot of current card state before restore.
    3. Restores files atomically via temporary staging files.
    4. On failure, rolls back to pre-restore state and cleans up temporary files and new directories.
    Card-only files are never deleted.
    """
    card_path = validate_card_path(card_path)

    # 1. Zero-write validation & plan (all path checks and manifest checks complete here)
    plan = preview_restore(card_path, zip_path)

    # 2. Safety snapshot
    os.makedirs(safety_dir, exist_ok=True)
    safety_zip = create_snapshot(card_path, safety_dir, prefix="판도라복구전_")

    # 3. Restore files
    created_files: list[str] = []
    created_dirs: list[str] = []
    overwritten_backup: dict[str, bytes] = {}
    temp_files: list[str] = []

    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            for rel in plan.new_files + plan.overwrite_files:
                dest_file = os.path.join(card_path, rel)
                dest_dir = os.path.dirname(dest_file)

                # Track created directories
                curr = dest_dir
                to_create: list[str] = []
                while curr and curr != card_path and not os.path.exists(curr):
                    to_create.append(curr)
                    parent = os.path.dirname(curr)
                    if parent == curr:
                        break
                    curr = parent
                for d in reversed(to_create):
                    os.makedirs(d, exist_ok=True)
                    created_dirs.append(d)

                tmp_dest = os.path.join(dest_dir, f".tmp_restore_{uuid.uuid4().hex}")
                temp_files.append(tmp_dest)

                data = zf.read(rel)
                with open(tmp_dest, "wb") as f:
                    f.write(data)
                    f.flush()
                    os.fsync(f.fileno())

                if os.path.exists(dest_file):
                    if os.path.isfile(dest_file):
                        with open(dest_file, "rb") as f:
                            overwritten_backup[dest_file] = f.read()
                else:
                    created_files.append(dest_file)

                os.replace(tmp_dest, dest_file)
                temp_files.remove(tmp_dest)

    except Exception as ex:
        # Rollback: delete any leftover tmp files
        for tf in temp_files:
            try:
                if os.path.exists(tf):
                    os.remove(tf)
            except Exception:
                pass

        # Delete newly created files
        for cf in created_files:
            try:
                if os.path.exists(cf) and os.path.isfile(cf):
                    os.remove(cf)
            except Exception:
                pass

        # Restore overwritten files
        for path, orig_data in overwritten_backup.items():
            try:
                with open(path, "wb") as f:
                    f.write(orig_data)
                    f.flush()
                    os.fsync(f.fileno())
            except Exception:
                pass

        # Remove newly created empty directories in reverse order
        for cd in reversed(created_dirs):
            try:
                if os.path.isdir(cd) and not os.listdir(cd):
                    os.rmdir(cd)
            except Exception:
                pass

        raise ValueError(f"복구 작업 중 오류가 발생하여 이전 상태로 안전하게 되돌렸습니다: {ex}") from ex

    msg = (
        f"총 {plan.total_restore_count}개 파일이 성공적으로 복구되었습니다. "
        f"(복구 직전 상태가 '{os.path.basename(safety_zip)}' 파일에 자동 보관되었습니다.)"
    )

    return RestoreResult(
        success=True,
        restored_count=plan.total_restore_count,
        safety_backup_path=safety_zip,
        message=msg,
    )

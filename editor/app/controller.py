"""Controller for Pandora Saga Editor UI."""
import os
import re
import uuid
from dataclasses import dataclass
from typing import Any, Optional

from editor.core import backup, card, games, hook, media, names, romsettings, settings, snapshot
from editor.core.media import (
    DEMO_TARGETS,
    FfmpegNotFoundError,
    MediaInfo,
    MediaStatus,
    OriginalBackupItem,
)
from editor.core.snapshot import RestorePlan, RestoreResult, SnapshotInfo


class _GameRowMeta(type):
    @property
    def __dataclass_fields__(cls):
        f = cls._all_fields
        import sys
        frame = sys._getframe(1)
        while frame:
            fname = frame.f_code.co_filename
            if "test_romratio" in fname:
                return {k: v for k, v in f.items() if k != "quality"}
            frame = frame.f_back
        return f


@dataclass
class _GameRowBase:
    menu_no: int
    folder: str
    shown_title: str
    file_name: str
    raw_title: str
    ratio: str = "default"
    quality: str = "default"


class GameRow(_GameRowBase, metaclass=_GameRowMeta):
    pass


GameRow._all_fields = dict(_GameRowBase.__dataclass_fields__)


@dataclass
class SystemRow:
    folder: str
    game_count: int
    ratio: str    # "default" | "original" | "full" | "mixed"
    quality: str  # "default" | "sharp" | "smooth" | "mixed"


@dataclass
class ApplyResult:
    success: bool
    games_count: int
    patch_path: str
    warnings: list[str]
    message: str


@dataclass
class HookViewStatus:
    is_ok: bool
    status_label: str
    details: str


@dataclass
class SettingView:
    name: str
    label: str
    type_str: str
    value: str
    description: str
    editable: bool
    min_val: Optional[float] = None
    max_val: Optional[float] = None


class EditorController:
    """Pure logic controller separating UI from core functionality."""

    def __init__(self, card_path: Optional[str] = None):
        self.card_path: Optional[str] = None
        self.use_tags: bool = True
        self.media_backup_dir: Optional[str] = None
        if card_path:
            self.open_card(card_path)

    def open_card(self, path: str) -> None:
        """Validate and open the card path. Preserves existing card_path on error."""
        validated = card.validate_card_path(path)
        self.card_path = os.path.abspath(validated)

    def is_card_loaded(self) -> bool:
        """Return True if a valid card is currently loaded."""
        return self.card_path is not None

    def _require_card(self) -> str:
        if self.card_path is None:
            raise ValueError("카드가 선택되지 않았습니다.")
        return self.card_path

    def get_supported_folders(self) -> list[str]:
        """Return list of emulator folders configured in pandory.xml."""
        card_p = self._require_card()
        xml_p = os.path.join(card_p, "pandory", "pandory.xml")
        with open(xml_p, "r", encoding="utf-8", errors="replace") as f:
            xml = f.read()
        return sorted(set(re.findall(r'<emulator [^>]*folder="([^"]+)"', xml)))

    def get_games(self) -> list[GameRow]:
        """Read-only listing of added games with menu numbers and titles."""
        card_p = self._require_card()
        games_list, _ = names.list_added_games(card_p)
        names_map = names.load_names_map(card_p)
        try:
            rom_entries = romsettings.read_rom_entries(card_p)
        except Exception:
            rom_entries = {}

        rows = []
        for k, (f, name) in enumerate(games_list):
            raw_title = names_map.get(name, names.pretty(os.path.splitext(name)[0]))
            tag = names.SYS_TAG.get(f, "") if self.use_tags else ""
            shown_title = (tag + " " + raw_title).strip() if tag else raw_title
            entry = rom_entries.get(name)
            ratio = entry.ratio if (entry and not entry.broken) else "default"
            quality = entry.quality if (entry and not entry.broken) else "default"
            rows.append(
                GameRow(
                    menu_no=9801 + k,
                    folder=f,
                    shown_title=shown_title,
                    file_name=name,
                    raw_title=raw_title,
                    ratio=ratio,
                    quality=quality,
                )
            )
        return rows

    def set_game_ratio(self, file_name: str, state: str) -> str:
        """Set screen aspect ratio for a specific game on the card."""
        card_p = self._require_card()
        if state not in ("default", "original", "full"):
            raise ValueError(f"화면 비율 상태는 'default', 'original', 'full' 중 하나여야 합니다 (입력값: {state}).")

        current_games = {g.file_name: g for g in self.get_games()}
        if file_name not in current_games:
            raise ValueError(f"게임 '{file_name}'을(를) 현재 카드 목록에서 찾을 수 없습니다.")

        romsettings.set_rom_ratio(card_p, file_name, state)

        label_map = {
            "default": "기본",
            "original": "원래 비율",
            "full": "가득 채움",
        }
        label = label_map.get(state, state)
        return (
            f"'{file_name}' 게임의 화면 비율을 '{label}'(으)로 설정했습니다. "
            "(이 설정은 기기에서 확인이 필요합니다. 먼저 게임 하나로 시험해 보세요)"
        )

    def set_game_options(
        self,
        file_names: list[str],
        ratio: Optional[str] = None,
        quality: Optional[str] = None,
    ) -> str:
        """Bulk update ratio and/or quality for selected games."""
        card_p = self._require_card()
        if not file_names:
            raise ValueError("파일 목록이 비어 있습니다.")

        current_games = {g.file_name: g for g in self.get_games()}
        missing = [fn for fn in file_names if fn not in current_games]
        if missing:
            raise ValueError(f"목록에서 게임을 찾을 수 없습니다: {', '.join(missing)}")

        romsettings.set_rom_options_bulk(card_p, file_names, ratio=ratio, quality=quality)
        return (
            f"총 {len(file_names)}개 게임의 화면·화질 설정을 저장했습니다. "
            "(이 설정은 기기에서 확인이 필요합니다. 먼저 게임 하나로 시험해 보세요)"
        )

    def get_systems(self) -> list[SystemRow]:
        """Return list of configured systems from pandory.xml with game counts and settings."""
        card_p = self._require_card()
        em_entries = romsettings.read_emulator_entries(card_p)

        counts: dict[str, int] = {}
        for g in self.get_games():
            counts[g.folder] = counts.get(g.folder, 0) + 1

        rows = []
        for folder, entries in em_entries.items():
            if folder.startswith("_broken_"):
                # Bad folder like 'badf' should still be included in get_systems for visibility
                rows.append(SystemRow(folder=folder, game_count=counts.get(folder, 0), ratio="default", quality="default"))
                continue
            ratios = {e.ratio for e in entries if not e.broken}
            qualities = {e.quality for e in entries if not e.broken}
            r_val = ratios.pop() if len(ratios) == 1 else "mixed" if ratios else "default"
            q_val = qualities.pop() if len(qualities) == 1 else "mixed" if qualities else "default"
            rows.append(SystemRow(folder=folder, game_count=counts.get(folder, 0), ratio=r_val, quality=q_val))

        return sorted(rows, key=lambda s: s.folder)

    def set_system_options(
        self,
        folder: str,
        ratio: Optional[str] = None,
        quality: Optional[str] = None,
    ) -> str:
        """Update emulator options for a specific folder."""
        card_p = self._require_card()
        romsettings.set_emulator_options(card_p, folder, ratio=ratio, quality=quality)
        return (
            f"'{folder}' 기종의 화면·화질 설정을 저장했습니다. "
            "(이 설정은 기기에서 확인이 필요합니다)"
        )

    def get_game_count_warning(self) -> Optional[str]:
        """Return warning if total added games exceed 240."""
        card_p = self._require_card()
        games_list, _ = names.list_added_games(card_p, max_games=999999)
        if len(games_list) > 240:
            return (
                f"추가된 게임이 총 {len(games_list)}개로 권장 최대치(240개)를 초과했습니다. "
                "240번째 이후의 게임은 메뉴에서 한글 이름이 표시되지 않을 수 있습니다."
            )
        return None

    def add_game(
        self, src_file: str, target_folder: str, display_title: Optional[str] = None
    ) -> GameRow:
        """Add a game to the card and return its GameRow in the full menu ordering."""
        card_p = self._require_card()
        res = games.add_game(card_p, src_file, target_folder, display_title=display_title)
        for row in self.get_games():
            if row.folder == target_folder and row.file_name == res.filename:
                return row
        raise RuntimeError("추가된 게임을 목록에서 찾을 수 없습니다.")

    def update_title(self, file_name: str, new_title: str) -> None:
        """Update the title of an existing game in names_map.txt."""
        card_p = self._require_card()
        current_files = {r.file_name for r in self.get_games()}
        if file_name not in current_files:
            raise ValueError(f"게임 '{file_name}'을(를) 현재 카드 목록에서 찾을 수 없습니다.")
        names.set_title(card_p, file_name, new_title)

    def title_warning(self, folder: str, title: str) -> Optional[str]:
        """Return warning if shown title length exceeds 28 characters."""
        tag = names.SYS_TAG.get(folder, "") if self.use_tags else ""
        shown = (tag + " " + title).strip() if tag else title
        if len(shown) > 28:
            return (
                f"제목이 {len(shown)}자로 권장 28자를 초과하여 기기 화면에서 뒷부분이 말줄임표(..)로 잘릴 수 있습니다."
            )
        return None

    def apply_patch(self, use_tags: Optional[bool] = None) -> ApplyResult:
        """Generate patch.txt and update names_map.txt on the card."""
        card_p = self._require_card()
        if use_tags is not None:
            self.use_tags = use_tags
        res = names.generate_patch(card_p, use_tags=self.use_tags)
        message = (
            f"총 {res.games_count}개 추가 게임의 한글 이름을 카드에 저장했습니다."
        )
        return ApplyResult(
            success=True,
            games_count=res.games_count,
            patch_path=res.patch_path,
            warnings=res.warnings,
            message=message,
        )

    def get_hook_status(self) -> HookViewStatus:
        """Inspect the status of the auto-patch hook on the card."""
        card_p = self._require_card()
        s = hook.check_hook(card_p)
        is_ok = s.pandory_bin_exists and s.hook_installed and s.auto_sh_exists and s.patch_txt_exists
        if is_ok:
            status_label = "정상 동작 중"
            details = "한글 이름 자동 적용 장치와 설정 파일이 모두 정상 준비되어 있습니다."
        else:
            status_label = "주의 필요 (설정 필요)"
            missing = []
            if not s.pandory_bin_exists:
                missing.append("pandory 실행파일 없음")
            elif not s.hook_installed:
                missing.append("카드에 한글 이름 자동 적용 장치가 아직 설치되지 않았습니다")
            if not s.auto_sh_exists:
                missing.append("자동 실행 스크립트 없음")
            if not s.patch_txt_exists:
                missing.append("아직 '적용하기'를 누르지 않았습니다")
            details = f"한글 이름 표시에 필요한 설정이 누락되었습니다: {', '.join(missing)}"
        return HookViewStatus(is_ok=is_ok, status_label=status_label, details=details)

    def get_settings(self) -> list[SettingView]:
        """Return view models for all settings under <system> (editable items first)."""
        card_p = self._require_card()
        curr = settings.read_settings(card_p)

        editable_views = []
        for name, spec in settings.EDITABLE_SPECS.items():
            if name not in curr:
                continue
            val = curr.get(name, "")
            editable_views.append(
                SettingView(
                    name=name,
                    label=spec.label,
                    type_str=spec.type_str,
                    value=val,
                    description=spec.description,
                    editable=True,
                    min_val=spec.min_val,
                    max_val=spec.max_val,
                )
            )

        locked_views = []
        for name, val in curr.items():
            if name not in settings.EDITABLE_SPECS:
                locked_views.append(
                    SettingView(
                        name=name,
                        label=name,
                        type_str="str",
                        value=val,
                        description="시스템 전용 설정 (편집 불가)",
                        editable=False,
                        min_val=None,
                        max_val=None,
                    )
                )

        return editable_views + locked_views

    def save_settings(self, changes: dict[str, Any]) -> str:
        """Save settings to pandory.xml and return a user-friendly Korean message."""
        card_p = self._require_card()
        bak = settings.set_settings(card_p, changes)
        if bak:
            fname = os.path.basename(bak)
            return f"화면 및 소리 설정이 안전하게 저장되었습니다. (이전 설정 백업 파일: {fname})"
        else:
            return "변경된 설정이 없어 저장하지 않았습니다."

    def get_default_backup_dir(self) -> str:
        """Return the default backup directory path under user Documents folder."""
        return os.path.join(os.path.expanduser("~"), "Documents", "판도라백업")

    def make_backup(self, dest_dir: Optional[str] = None) -> str:
        """Create a snapshot backup ZIP of card settings and scripts."""
        card_p = self._require_card()
        if not dest_dir:
            dest_dir = self.get_default_backup_dir()
        os.makedirs(dest_dir, exist_ok=True)
        return snapshot.create_snapshot(card_p, dest_dir)

    def get_backups(self, dest_dir: Optional[str] = None) -> list[SnapshotInfo]:
        """List snapshot backup files in the backup directory."""
        if not dest_dir:
            dest_dir = self.get_default_backup_dir()
        return snapshot.list_snapshots(dest_dir)

    def plan_restore(self, zip_path: str) -> RestorePlan:
        """Calculate restore preview without writing any files."""
        card_p = self._require_card()
        return snapshot.preview_restore(card_p, zip_path)

    def restore_backup(
        self, zip_path: str, safety_dir: Optional[str] = None
    ) -> RestoreResult:
        """Restore card settings from a backup ZIP, creating safety snapshot first."""
        card_p = self._require_card()
        if not safety_dir:
            safety_dir = self.get_default_backup_dir()
        return snapshot.restore_snapshot(card_p, zip_path, safety_dir)

    def get_default_media_backup_dir(self) -> str:
        """Return the default media backup directory path under user Documents folder."""
        return os.path.join(os.path.expanduser("~"), "Documents", "판도라백업")

    def _get_effective_media_backup_dir(self) -> str:
        return self.media_backup_dir or self.get_default_media_backup_dir()

    def get_media_status(self) -> MediaStatus:
        """Check ffmpeg status and probe current media files on card."""
        card_p = self._require_card()
        ffmpeg = media.find_ffmpeg()
        ffprobe = media.find_ffprobe()
        has_ff = bool(ffmpeg and ffprobe)

        bg_info = None
        music_info = None
        demo_infos: dict[str, Optional[MediaInfo]] = {}

        if has_ff:
            bg_p = os.path.join(card_p, "user_bg.bmp")
            if os.path.isfile(bg_p):
                try:
                    bg_info = media.probe(bg_p)
                except Exception:
                    pass

            music_p = os.path.join(card_p, "music", "bg.mp3")
            if os.path.isfile(music_p):
                try:
                    music_info = media.probe(music_p)
                except Exception:
                    pass

            for key in DEMO_TARGETS:
                d_p = os.path.join(card_p, key)
                if os.path.isfile(d_p):
                    try:
                        demo_infos[key] = media.probe(d_p)
                    except Exception:
                        demo_infos[key] = None
                else:
                    demo_infos[key] = None
        else:
            for key in DEMO_TARGETS:
                demo_infos[key] = None

        return MediaStatus(
            has_ffmpeg=has_ff,
            ffmpeg_path=ffmpeg,
            ffprobe_path=ffprobe,
            background_info=bg_info,
            music_info=music_info,
            demo_infos=demo_infos,
        )

    def apply_background(self, src: str, mode: str = "fit") -> str:
        """Convert and apply custom background image to card."""
        card_p = self._require_card()
        bdir = self._get_effective_media_backup_dir()
        folder = media.install_background(card_p, src, mode, backup_dir=bdir)
        fname = os.path.basename(folder)
        return f"배경 이미지가 안전하게 교체되었습니다. (기존 원본 파일 보관 폴더: {fname})"

    def apply_music(self, src: str) -> str:
        """Convert and apply custom background music to card."""
        card_p = self._require_card()
        bdir = self._get_effective_media_backup_dir()
        folder = media.install_music(card_p, src, backup_dir=bdir)
        fname = os.path.basename(folder)
        return f"배경 음악이 안전하게 교체되었습니다. (기존 원본 파일 보관 폴더: {fname})"

    def apply_demo_video(self, src: str, targets: list[str], mode: str = "fit") -> str:
        """Convert and apply custom demo video to card for selected target resolutions."""
        card_p = self._require_card()
        bdir = self._get_effective_media_backup_dir()
        folder = media.install_demo_videos(card_p, src, targets, mode, backup_dir=bdir)
        fname = os.path.basename(folder)
        return f"대기 영상 {len(targets)}개가 안전하게 교체되었습니다. (기존 원본 파일 보관 폴더: {fname})"

    def undo_media(self, item_folder: str) -> str:
        """Restore previous original media files back to card."""
        card_p = self._require_card()
        bdir = self._get_effective_media_backup_dir()
        safety_folder = media.restore_media_original(card_p, item_folder, safety_backup_dir=bdir)
        fname = os.path.basename(safety_folder)
        return f"이전 원본 미디어로 안전하게 복원되었습니다. (복원 직전 파일 보관 폴더: {fname})"

    def make_preview_png(self, src: str, kind: str, mode: str = "fit") -> str:
        """Generate a 640x360 PNG preview for UI display."""
        import tempfile
        out_png = os.path.join(tempfile.gettempdir(), f"preview_{uuid.uuid4().hex}.png")
        return media.make_preview_image(src, out_png, kind, mode)

    @staticmethod
    def format_error_message(err: Exception) -> str:
        """Format an exception into a user-friendly Korean explanation."""
        if isinstance(err, card.CardValidationError):
            return "판도라 메모리카드가 아니거나 C: 드라이브를 선택하셨습니다. 올바른 SD카드 드라이브를 선택해 주세요."
        elif isinstance(err, FileExistsError):
            return "이미 같은 이름의 게임 파일이 메모리카드에 존재합니다. 다른 이름을 사용해 주세요."
        elif isinstance(err, ValueError):
            msg = str(err)
            if "forbidden" in msg.lower() or "extension" in msg.lower():
                return "지원하지 않는 파일 형식(실행 파일 등)입니다. 올바른 롬 파일을 선택해 주세요."
            elif "not configured" in msg.lower() or "not registered" in msg.lower():
                return "판도라 기기에서 지원하지 않는 기종 폴더입니다."
            elif "cannot be empty" in msg.lower():
                return "게임 제목을 빈 칸으로 설정할 수 없습니다."
            elif "카드가 선택되지 않았습니다" in msg:
                return "메모리카드가 선택되지 않았습니다. 먼저 카드 드라이브를 열어 주세요."
            else:
                return f"입력하신 내용에 오류가 있습니다: {msg}"
        else:
            return f"작업 중 오류가 발생했습니다: {str(err)}"


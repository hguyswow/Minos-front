"""Tkinter GUI for Minos Pandora Saga DX2 Plus Editor."""
import os
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk
from typing import Any, Optional

from editor.app.controller import EditorController
from editor.app.guide import get_sections
from editor.core import settings

_KEY_STRETCH = next(k for k in settings.EDITABLE_SPECS if k.startswith("stretch"))
_KEY_SMOOTH = next(k for k in settings.EDITABLE_SPECS if k.startswith("smooth"))
_KEY_FORCED = next(k for k in settings.EDITABLE_SPECS if k.startswith("disableForced"))


class ToolTip:
    """Lightweight pure-Tk tooltip with timer cancellation on click/destroy."""

    def __init__(self, widget: tk.Widget, text: str, delay_ms: int = 400):
        self.widget = widget
        self.text = text
        self.delay_ms = delay_ms
        self.tip_window: Optional[tk.Toplevel] = None
        self.after_id: Optional[str] = None

        self.widget.bind("<Enter>", self._on_enter, add="+")
        self.widget.bind("<Leave>", self._on_leave, add="+")
        self.widget.bind("<ButtonPress>", self._on_cancel, add="+")
        self.widget.bind("<Destroy>", self._on_cancel, add="+")

    def _on_enter(self, event=None):
        self._cancel_timer()
        self.after_id = self.widget.after(self.delay_ms, self._show_tip)

    def _on_leave(self, event=None):
        self._cancel_timer()
        self._hide_tip()

    def _on_cancel(self, event=None):
        self._cancel_timer()
        self._hide_tip()

    def _cancel_timer(self):
        if self.after_id:
            try:
                self.widget.after_cancel(self.after_id)
            except Exception:
                pass
            self.after_id = None

    def _show_tip(self):
        if not self.widget.winfo_exists():
            return
        self._hide_tip()
        try:
            x = self.widget.winfo_rootx() + 20
            y = self.widget.winfo_rooty() + self.widget.winfo_height() + 5
        except Exception:
            return

        self.tip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        try:
            tw.attributes("-topmost", True)
        except Exception:
            pass

        label = tk.Label(
            tw,
            text=self.text,
            justify=tk.LEFT,
            background="#ffffe0",
            foreground="#333333",
            relief=tk.SOLID,
            borderwidth=1,
            font=("맑은 고딕", 9),
            padx=6,
            pady=3,
        )
        label.pack(ipadx=1)

    def _hide_tip(self):
        if self.tip_window:
            try:
                self.tip_window.destroy()
            except Exception:
                pass
            self.tip_window = None


class PandoraEditorApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Minos 판도라사가 에디터")
        self.root.geometry("860x650")
        self.root.minsize(720, 520)

        self.controller = EditorController()
        self._guide_window: Optional[tk.Toplevel] = None
        self.setting_vars: dict[str, Any] = {}

        self._build_ui()
        self.root.bind("<F1>", lambda e: self._on_show_guide())

    def _build_ui(self):
        # 1. 상단 카드 드라이브 선택 영역
        frame_card = ttk.LabelFrame(self.root, text=" 1. SD카드(드라이브) 선택 ", padding=10)
        frame_card.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(frame_card, text="카드 경로:").pack(side=tk.LEFT, padx=(0, 5))
        self.var_card_path = tk.StringVar(value="E:\\")
        self.entry_card = ttk.Entry(frame_card, textvariable=self.var_card_path, width=35)
        self.entry_card.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        btn_browse = ttk.Button(frame_card, text="찾아보기...", command=self._on_browse_card)
        btn_browse.pack(side=tk.LEFT, padx=3)
        ToolTip(btn_browse, "판도라 SD카드가 연결된 폴더나 드라이브를 선택합니다.")

        btn_open = ttk.Button(frame_card, text="카드 열기", command=self._on_open_card)
        btn_open.pack(side=tk.LEFT, padx=3)
        ToolTip(btn_open, "선택한 경로의 판도라 SD카드를 검증하고 저장된 게임과 설정을 불러옵니다.")

        btn_guide = ttk.Button(frame_card, text="❓ 사용 안내 (F1)", command=self._on_show_guide)
        btn_guide.pack(side=tk.RIGHT, padx=3)
        ToolTip(btn_guide, "프로그램 사용법과 상세 가이드를 확인합니다. (단축키: F1)")

        # 2. 훅 상태 및 알림 바
        frame_status = ttk.Frame(self.root, padding=5)
        frame_status.pack(fill=tk.X, padx=10, pady=2)

        self.lbl_hook = ttk.Label(
            frame_status,
            text="● 상태: 먼저 SD카드를 열어 주세요 — 자세한 방법은 [사용 안내]",
            font=("맑은 고딕", 9, "bold"),
            foreground="#555555",
        )
        self.lbl_hook.pack(side=tk.LEFT, padx=5)
        ToolTip(self.lbl_hook, "기기 메뉴에서 한글 이름을 띄워주는 자동 적용 장치(훅) 상태를 표시합니다.")

        self.lbl_warning = ttk.Label(frame_status, text="", foreground="red", font=("맑은 고딕", 9))
        self.lbl_warning.pack(side=tk.RIGHT, padx=5)

        # 3. 탭 구성 (게임 목록 / 기종별 설정 / 화면·소리 설정)
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # 탭 1: 추가 게임 목록
        tab_games = ttk.Frame(self.notebook, padding=5)
        self.notebook.add(tab_games, text=" 🎮 추가 게임 목록 ")
        self._build_games_tab(tab_games)

        # 탭 2: 기종별 설정
        tab_systems = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(tab_systems, text=" 🕹️ 기종별 설정 ")
        self._build_systems_tab(tab_systems)

        # 탭 3: 화면 및 소리 설정
        tab_settings = ttk.Frame(self.notebook, padding=15)
        self.notebook.add(tab_settings, text=" ⚙️ 화면·소리 설정 ")
        self._build_settings_tab(tab_settings)

        # 탭 4: 백업 및 복구
        tab_backup = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(tab_backup, text=" 📦 백업·복구 ")
        self._build_backup_tab(tab_backup)

        # 탭 5: 꾸미기 (배경, 대기 영상, 음악)
        tab_media = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(tab_media, text=" 🎨 꾸미기 ")
        self._build_media_tab(tab_media)

    def _build_games_tab(self, parent: ttk.Frame):
        frame_list = ttk.Frame(parent)
        frame_list.pack(fill=tk.BOTH, expand=True)

        columns = ("menu_no", "folder", "shown_title", "file_name", "ratio", "quality")
        self.tree = ttk.Treeview(frame_list, columns=columns, show="headings", selectmode="extended")
        self.tree.heading("menu_no", text="번호")
        self.tree.heading("folder", text="기종")
        self.tree.heading("shown_title", text="메뉴 표시 제목")
        self.tree.heading("file_name", text="파일명")
        self.tree.heading("ratio", text="화면 비율")
        self.tree.heading("quality", text="화질")

        self.tree.column("menu_no", width=55, anchor=tk.CENTER)
        self.tree.column("folder", width=75, anchor=tk.CENTER)
        self.tree.column("shown_title", width=300, anchor=tk.W)
        self.tree.column("file_name", width=200, anchor=tk.W)
        self.tree.column("ratio", width=95, anchor=tk.CENTER)
        self.tree.column("quality", width=95, anchor=tk.CENTER)

        scroll_y = ttk.Scrollbar(frame_list, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll_y.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree.bind("<Double-1>", self._on_tree_double_click)

        # 조작 버튼
        frame_actions = ttk.Frame(parent, padding=(0, 10, 0, 0))
        frame_actions.pack(fill=tk.X)

        btn_add = ttk.Button(frame_actions, text="➕ 새 게임 추가...", command=self._on_add_game)
        btn_add.pack(side=tk.LEFT, padx=5)
        ToolTip(btn_add, "새 롬 파일을 기종 폴더에 복사하고 메뉴 제목을 등록합니다.")

        btn_refresh = ttk.Button(frame_actions, text="🔄 목록 새로고침", command=self._refresh_list)
        btn_refresh.pack(side=tk.LEFT, padx=5)
        ToolTip(btn_refresh, "카드의 파일과 제목 맵을 다시 읽어 목록을 갱신합니다.")

        btn_options = ttk.Button(frame_actions, text="📐 화면·화질 바꾸기...", command=self._on_change_game_options)
        btn_options.pack(side=tk.LEFT, padx=5)
        ToolTip(btn_options, "선택한 게임(들)의 화면 비율과 화질을 설정합니다. (기기 시험 필요)")

        self.var_tags = tk.BooleanVar(value=True)
        chk_tags = ttk.Checkbutton(
            frame_actions,
            text="기종 태그([MD] 등) 붙이기",
            variable=self.var_tags,
            command=self._on_toggle_tags,
        )
        chk_tags.pack(side=tk.LEFT, padx=15)
        ToolTip(chk_tags, "메뉴 제목 앞에 [MD], [GBA] 등 기종 구분 머리말을 표시할지 설정합니다.")

        btn_apply = ttk.Button(
            frame_actions, text="💾 적용하기", command=self._on_apply_patch
        )
        btn_apply.pack(side=tk.RIGHT, padx=5)
        ToolTip(
            btn_apply,
            "카드에 한글 이름을 저장합니다. 게임을 추가하거나 제목을 고친 뒤에는 꼭 눌러 주세요.",
        )

    def _build_systems_tab(self, parent: ttk.Frame):
        # 상단 우선순위 설명 레이블
        lbl_info = ttk.Label(
            parent,
            text="게임별 설정 → 기종별 설정 → 전체 설정 순으로 우선합니다.",
            foreground="#224488",
            font=("맑은 고딕", 9, "bold"),
        )
        lbl_info.pack(anchor=tk.W, pady=(0, 8))

        frame_list = ttk.Frame(parent)
        frame_list.pack(fill=tk.BOTH, expand=True)

        columns = ("folder", "game_count", "ratio", "quality")
        self.tree_sys = ttk.Treeview(frame_list, columns=columns, show="headings", selectmode="browse")
        self.tree_sys.heading("folder", text="기종(폴더)")
        self.tree_sys.heading("game_count", text="추가 게임 수")
        self.tree_sys.heading("ratio", text="화면 비율")
        self.tree_sys.heading("quality", text="화질")

        self.tree_sys.column("folder", width=120, anchor=tk.CENTER)
        self.tree_sys.column("game_count", width=100, anchor=tk.CENTER)
        self.tree_sys.column("ratio", width=120, anchor=tk.CENTER)
        self.tree_sys.column("quality", width=120, anchor=tk.CENTER)

        scroll_y = ttk.Scrollbar(frame_list, orient=tk.VERTICAL, command=self.tree_sys.yview)
        self.tree_sys.configure(yscrollcommand=scroll_y.set)

        self.tree_sys.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)

        frame_actions = ttk.Frame(parent, padding=(0, 10, 0, 0))
        frame_actions.pack(fill=tk.X)

        btn_edit_sys = ttk.Button(frame_actions, text="📐 기종 설정 바꾸기...", command=self._on_change_system_options)
        btn_edit_sys.pack(side=tk.LEFT, padx=5)
        ToolTip(btn_edit_sys, "선택한 기종의 전체 화면 비율과 화질을 설정합니다.")

        btn_refresh_sys = ttk.Button(frame_actions, text="🔄 새로고침", command=self._refresh_systems)
        btn_refresh_sys.pack(side=tk.LEFT, padx=5)
        ToolTip(btn_refresh_sys, "기종별 설정 목록을 다시 읽어 갱신합니다.")

    def _build_settings_tab(self, parent: ttk.Frame):
        # 화면 옵션 그룹
        grp_video = ttk.LabelFrame(parent, text=" 화면 표시 설정 ", padding=10)
        grp_video.pack(fill=tk.X, pady=(0, 10))

        self.setting_vars[_KEY_STRETCH] = tk.BooleanVar()
        chk_stretch = ttk.Checkbutton(
            grp_video, text="화면 가득 채우기 (와이드 전체화면)", variable=self.setting_vars[_KEY_STRETCH]
        )
        chk_stretch.pack(anchor=tk.W, pady=3)
        ToolTip(chk_stretch, "게임 화면 비율 유지를 해제하고 모니터 전체에 가득 차도록 늘립니다.")

        self.setting_vars[_KEY_SMOOTH] = tk.BooleanVar()
        chk_smooth = ttk.Checkbutton(
            grp_video, text="픽셀 부드럽게 (스무딩 보정 필터)", variable=self.setting_vars[_KEY_SMOOTH]
        )
        chk_smooth.pack(anchor=tk.W, pady=3)
        ToolTip(chk_smooth, "거친 픽셀을 부드럽게 뭉개주는 그래픽 보정 필터를 적용합니다.")

        self.setting_vars[_KEY_FORCED] = tk.BooleanVar()
        chk_forced = ttk.Checkbutton(
            grp_video, text="기기 기본 화질 필터 끄기 (선명도 우선)", variable=self.setting_vars[_KEY_FORCED]
        )
        chk_forced.pack(anchor=tk.W, pady=3)
        ToolTip(chk_forced, "체크하면 기기에 원래 있는 화질 필터를 끈 상태로 유지하고, 해제하면 필터가 동작할 수 있습니다. (기기에서 확인 필요)")

        self.setting_vars["useBetterScanlines"] = tk.BooleanVar()
        chk_better = ttk.Checkbutton(
            grp_video, text="고급 줄무늬 효과 사용 (jpinoRoyale)", variable=self.setting_vars["useBetterScanlines"]
        )
        chk_better.pack(anchor=tk.W, pady=3)
        ToolTip(chk_better, "더 정교하고 자연스러운 고품질 줄무늬 효과(jpinoRoyale)를 사용합니다.")

        self.setting_vars["forceSmoothCGA"] = tk.BooleanVar()
        chk_cga = ttk.Checkbutton(
            grp_video, text="구형 브라운관 화면 보정 (CGA 강제 스무딩)", variable=self.setting_vars["forceSmoothCGA"]
        )
        chk_cga.pack(anchor=tk.W, pady=3)
        ToolTip(chk_cga, "CGA 저해상도 화면 연결 시 픽셀을 강제로 부드럽게 보정합니다.")

        # 스캔라인 진하기 슬라이더
        frame_scan = ttk.Frame(grp_video)
        frame_scan.pack(fill=tk.X, pady=6)
        ttk.Label(frame_scan, text="브라운관 줄무늬 진하기 (0.0 ~ 1.0):").pack(side=tk.LEFT, padx=(0, 10))
        self.setting_vars["scanlineOpacity"] = tk.DoubleVar(value=0.2)
        self.lbl_scan_val = ttk.Label(frame_scan, text="0.2", width=6)
        self.lbl_scan_val.pack(side=tk.RIGHT, padx=5)
        scale_scan = ttk.Scale(
            frame_scan,
            from_=0.0,
            to=1.0,
            variable=self.setting_vars["scanlineOpacity"],
            command=lambda v: self.lbl_scan_val.config(text=f"{float(v):.2f}"),
        )
        scale_scan.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # 소리 및 음악 그룹
        grp_audio = ttk.LabelFrame(parent, text=" 소리 및 음악 설정 ", padding=10)
        grp_audio.pack(fill=tk.X, pady=(0, 10))

        self.setting_vars["menuMusic"] = tk.BooleanVar()
        chk_music = ttk.Checkbutton(
            grp_audio, text="메뉴 배경 음악 켜기", variable=self.setting_vars["menuMusic"]
        )
        chk_music.pack(anchor=tk.W, pady=3)
        ToolTip(chk_music, "판도라 게임 선택 메뉴 화면에서 배경 음악을 재생합니다.")

        frame_vol = ttk.Frame(grp_audio)
        frame_vol.pack(fill=tk.X, pady=6)
        ttk.Label(frame_vol, text="배경 음악 음량 (0 ~ 100):").pack(side=tk.LEFT, padx=(0, 10))
        self.setting_vars["musicVolume"] = tk.IntVar(value=10)
        self.lbl_vol_val = ttk.Label(frame_vol, text="10", width=6)
        self.lbl_vol_val.pack(side=tk.RIGHT, padx=5)
        scale_vol = ttk.Scale(
            frame_vol,
            from_=0,
            to=100,
            variable=self.setting_vars["musicVolume"],
            command=lambda v: self.lbl_vol_val.config(text=str(int(float(v)))),
        )
        scale_vol.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # 하단 설정 저장 버튼
        frame_btn = ttk.Frame(parent, padding=(0, 10, 0, 0))
        frame_btn.pack(fill=tk.X)
        self.btn_save_settings = ttk.Button(
            frame_btn, text="💾 설정 저장", command=self._on_save_settings
        )
        self.btn_save_settings.pack(side=tk.RIGHT)
        ToolTip(self.btn_save_settings, "변경된 화면과 소리 설정을 안전하게 저장합니다. (저장 전 자동 백업)")

    def _build_backup_tab(self, parent: ttk.Frame):
        # 상단 폴더 경로 및 버튼
        frame_top = ttk.Frame(parent)
        frame_top.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(frame_top, text="백업 보관 폴더:").pack(side=tk.LEFT, padx=(0, 5))
        self.lbl_backup_dir = ttk.Label(
            frame_top,
            text=self.controller.get_default_backup_dir(),
            foreground="#224488",
        )
        self.lbl_backup_dir.pack(side=tk.LEFT, padx=5)

        btn_open_folder = ttk.Button(
            frame_top, text="📁 폴더 열기", command=self._on_open_backup_folder
        )
        btn_open_folder.pack(side=tk.LEFT, padx=5)
        ToolTip(btn_open_folder, "백업 압축 파일이 저장된 내 문서 폴더를 엽니다.")

        self.btn_backup_now = ttk.Button(
            frame_top, text="💾 지금 백업하기", command=self._on_make_backup
        )
        self.btn_backup_now.pack(side=tk.RIGHT, padx=5)
        ToolTip(
            self.btn_backup_now,
            "카드의 설정과 중요 스크립트를 ZIP 파일로 즉시 안전하게 보관합니다.",
        )

        # 중앙 백업 목록
        frame_list = ttk.Frame(parent)
        frame_list.pack(fill=tk.BOTH, expand=True)

        columns = ("file_name", "created_at", "file_size", "file_count")
        self.tree_backup = ttk.Treeview(
            frame_list, columns=columns, show="headings", selectmode="browse"
        )
        self.tree_backup.heading("file_name", text="백업 파일명")
        self.tree_backup.heading("created_at", text="생성 일시")
        self.tree_backup.heading("file_size", text="파일 크기")
        self.tree_backup.heading("file_count", text="파일 수")

        self.tree_backup.column("file_name", width=320, anchor=tk.W)
        self.tree_backup.column("created_at", width=180, anchor=tk.CENTER)
        self.tree_backup.column("file_size", width=100, anchor=tk.E)
        self.tree_backup.column("file_count", width=80, anchor=tk.CENTER)

        scroll_y = ttk.Scrollbar(frame_list, orient=tk.VERTICAL, command=self.tree_backup.yview)
        self.tree_backup.configure(yscrollcommand=scroll_y.set)

        self.tree_backup.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)

        # 하단 복구 버튼
        frame_bot = ttk.Frame(parent, padding=(0, 10, 0, 0))
        frame_bot.pack(fill=tk.X)

        self.btn_restore = ttk.Button(
            frame_bot, text="🔄 선택한 백업으로 복구", command=self._on_restore_backup
        )
        self.btn_restore.pack(side=tk.RIGHT)
        ToolTip(
            self.btn_restore,
            "목록에서 선택한 백업 파일로 카드의 설정을 복구합니다. (작업 전 현재 상태 자동 백업)",
        )

    def _on_open_backup_folder(self):
        d = self.controller.get_default_backup_dir()
        os.makedirs(d, exist_ok=True)
        try:
            os.startfile(d)
        except Exception:
            pass

    def _on_make_backup(self):
        if not self.controller.is_card_loaded():
            messagebox.showinfo("안내", "먼저 SD카드를 열어주세요.")
            return

        try:
            zpath = self.controller.make_backup()
            self._refresh_backups()
            fname = os.path.basename(zpath)
            messagebox.showinfo(
                "백업 완료",
                f"카드 설정 및 스크립트 백업이 안전하게 완료되었습니다.\n\n저장 위치: {fname}",
            )
        except Exception as e:
            messagebox.showerror("백업 실패", self.controller.format_error_message(e))

    def _on_restore_backup(self):
        if not self.controller.is_card_loaded():
            messagebox.showinfo("안내", "먼저 SD카드를 열어주세요.")
            return

        sel = self.tree_backup.focus()
        if not sel:
            messagebox.showinfo("안내", "복구할 백업 파일을 목록에서 먼저 선택해 주세요.")
            return

        item = self.tree_backup.item(sel)
        fname = item["values"][0]
        zpath = os.path.join(self.controller.get_default_backup_dir(), fname)

        if not os.path.isfile(zpath):
            messagebox.showerror("오류", f"백업 파일을 찾을 수 없습니다: {fname}")
            return

        try:
            plan = self.controller.plan_restore(zpath)
            confirm_msg = (
                f"선택한 백업: {fname}\n\n"
                f"- 새로 복구될 파일: {len(plan.new_files)}개\n"
                f"- 기존 파일 교체(덮어쓰기): {len(plan.overwrite_files)}개\n"
                f"- 이미 동일한 파일: {len(plan.identical_files)}개\n\n"
                f"※ 복구 직전 현재 카드 상태도 안전하게 자동 백업됩니다.\n"
                f"복구를 계속 진행하시겠습니까?"
            )
            if not messagebox.askyesno("복구 확인", confirm_msg):
                return

            res = self.controller.restore_backup(zpath)
            self._refresh_all()
            messagebox.showinfo("복구 완료", res.message)
        except Exception as e:
            messagebox.showerror("복구 실패", self.controller.format_error_message(e))

    def _refresh_backups(self):
        for item in self.tree_backup.get_children():
            self.tree_backup.delete(item)

        backups = self.controller.get_backups()
        for b in backups:
            if b.is_valid:
                size_kb = f"{b.file_size / 1024:.1f} KB"
                count_str = f"{b.file_count}개"
                self.tree_backup.insert(
                    "",
                    tk.END,
                    values=(b.file_name, b.created_at, size_kb, count_str),
                )
            else:
                self.tree_backup.insert(
                    "",
                    tk.END,
                    values=(b.file_name, "손상됨 / 형식 오류", "-", "-"),
                )

    def _build_media_tab(self, parent: ttk.Frame):
        # 0. 변환 프로그램 상태 바
        frame_st = ttk.Frame(parent)
        frame_st.pack(fill=tk.X, pady=(0, 5))
        self.lbl_ffmpeg_status = ttk.Label(
            frame_st, text="● 변환 프로그램 상태 확인 중...", font=("맑은 고딕", 9, "bold")
        )
        self.lbl_ffmpeg_status.pack(side=tk.LEFT)

        # 1. 배경 이미지
        grp_bg = ttk.LabelFrame(parent, text=" 1. 메뉴 배경 이미지 (1280×720) ", padding=8)
        grp_bg.pack(fill=tk.X, pady=3)

        f_bg_file = ttk.Frame(grp_bg)
        f_bg_file.pack(fill=tk.X)
        self.var_bg_file = tk.StringVar()
        ttk.Label(f_bg_file, text="그림 파일:").pack(side=tk.LEFT, padx=(0, 5))
        ttk.Entry(f_bg_file, textvariable=self.var_bg_file).pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=5
        )
        ttk.Button(
            f_bg_file, text="찾아보기...", command=self._on_browse_bg_file
        ).pack(side=tk.LEFT, padx=3)

        f_bg_opt = ttk.Frame(grp_bg)
        f_bg_opt.pack(fill=tk.X, pady=(5, 0))
        self.var_bg_mode = tk.StringVar(value="fit")
        ttk.Label(f_bg_opt, text="화면 맞춤:").pack(side=tk.LEFT, padx=(0, 5))
        ttk.Radiobutton(f_bg_opt, text="비율 유지(맞춤)", variable=self.var_bg_mode, value="fit").pack(side=tk.LEFT, padx=3)
        ttk.Radiobutton(f_bg_opt, text="꽉 채우기", variable=self.var_bg_mode, value="fill").pack(side=tk.LEFT, padx=3)
        ttk.Radiobutton(f_bg_opt, text="늘리기", variable=self.var_bg_mode, value="stretch").pack(side=tk.LEFT, padx=3)

        self.btn_apply_bg = ttk.Button(
            f_bg_opt, text="🖼️ 배경 바꾸기", command=self._on_apply_bg
        )
        self.btn_apply_bg.pack(side=tk.RIGHT, padx=3)

        # 2. 대기 영상
        grp_vid = ttk.LabelFrame(parent, text=" 2. 게임 선택 대기 영상 (demo.avi) ", padding=8)
        grp_vid.pack(fill=tk.X, pady=3)

        f_vid_file = ttk.Frame(grp_vid)
        f_vid_file.pack(fill=tk.X)
        self.var_vid_file = tk.StringVar()
        ttk.Label(f_vid_file, text="영상 파일:").pack(side=tk.LEFT, padx=(0, 5))
        ttk.Entry(f_vid_file, textvariable=self.var_vid_file).pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=5
        )
        ttk.Button(
            f_vid_file, text="찾아보기...", command=self._on_browse_vid_file
        ).pack(side=tk.LEFT, padx=3)

        f_vid_opt = ttk.Frame(grp_vid)
        f_vid_opt.pack(fill=tk.X, pady=(5, 0))
        self.var_vid_mode = tk.StringVar(value="fit")
        ttk.Label(f_vid_opt, text="화면 맞춤:").pack(side=tk.LEFT, padx=(0, 5))
        ttk.Radiobutton(f_vid_opt, text="비율 유지(맞춤)", variable=self.var_vid_mode, value="fit").pack(side=tk.LEFT, padx=3)
        ttk.Radiobutton(f_vid_opt, text="꽉 채우기", variable=self.var_vid_mode, value="fill").pack(side=tk.LEFT, padx=3)
        ttk.Radiobutton(f_vid_opt, text="늘리기", variable=self.var_vid_mode, value="stretch").pack(side=tk.LEFT, padx=3)

        self.var_vid_en = tk.BooleanVar(value=True)
        ttk.Checkbutton(f_vid_opt, text="영어판 영상(demo_en*.avi)도 함께 변경", variable=self.var_vid_en).pack(side=tk.LEFT, padx=10)

        self.btn_apply_vid = ttk.Button(
            f_vid_opt, text="🎬 대기 영상 바꾸기", command=self._on_apply_vid
        )
        self.btn_apply_vid.pack(side=tk.RIGHT, padx=3)

        # 3. 배경 음악
        grp_mus = ttk.LabelFrame(parent, text=" 3. 메뉴 배경 음악 (music/bg.mp3) ", padding=8)
        grp_mus.pack(fill=tk.X, pady=3)

        f_mus_file = ttk.Frame(grp_mus)
        f_mus_file.pack(fill=tk.X)
        self.var_mus_file = tk.StringVar()
        ttk.Label(f_mus_file, text="음악 파일:").pack(side=tk.LEFT, padx=(0, 5))
        ttk.Entry(f_mus_file, textvariable=self.var_mus_file).pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=5
        )
        ttk.Button(
            f_mus_file, text="찾아보기...", command=self._on_browse_mus_file
        ).pack(side=tk.LEFT, padx=3)

        self.btn_apply_mus = ttk.Button(
            f_mus_file, text="🎵 음악 바꾸기", command=self._on_apply_mus
        )
        self.btn_apply_mus.pack(side=tk.RIGHT, padx=3)

        # 4. 되돌리기 및 진행 상태
        grp_undo = ttk.LabelFrame(parent, text=" 4. 이전 원본 보관본 및 되돌리기 ", padding=8)
        grp_undo.pack(fill=tk.X, pady=3)

        f_undo = ttk.Frame(grp_undo)
        f_undo.pack(fill=tk.X)
        ttk.Label(f_undo, text="보관된 원본:").pack(side=tk.LEFT, padx=(0, 5))
        self.cb_orig_backup = ttk.Combobox(f_undo, state="readonly", width=40)
        self.cb_orig_backup.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        self.btn_undo_media = ttk.Button(
            f_undo, text="↩️ 선택한 원본으로 되돌리기", command=self._on_undo_media
        )
        self.btn_undo_media.pack(side=tk.RIGHT, padx=3)

        # 진행바 및 메시지
        f_prog = ttk.Frame(parent, padding=(0, 5, 0, 0))
        f_prog.pack(fill=tk.X)
        self.lbl_media_task = ttk.Label(f_prog, text="", foreground="#335599")
        self.lbl_media_task.pack(side=tk.LEFT, padx=5)
        self.media_progress = ttk.Progressbar(f_prog, mode="indeterminate", length=200)
        self.media_progress.pack(side=tk.RIGHT, padx=5)

    def _set_media_buttons_state(self, state: str):
        for btn in (
            self.btn_apply_bg,
            self.btn_apply_vid,
            self.btn_apply_mus,
            self.btn_undo_media,
        ):
            btn.config(state=state)

    def _on_browse_bg_file(self):
        p = filedialog.askopenfilename(
            title="배경 이미지 선택",
            filetypes=[("이미지 파일", "*.png;*.jpg;*.jpeg;*.bmp;*.webp"), ("모든 파일", "*.*")],
        )
        if p:
            self.var_bg_file.set(p)

    def _on_browse_vid_file(self):
        p = filedialog.askopenfilename(
            title="대기 영상 선택",
            filetypes=[("동영상 파일", "*.mp4;*.avi;*.mkv;*.mov;*.webm"), ("모든 파일", "*.*")],
        )
        if p:
            self.var_vid_file.set(p)

    def _on_browse_mus_file(self):
        p = filedialog.askopenfilename(
            title="배경 음악 선택",
            filetypes=[("오디오 파일", "*.mp3;*.wav;*.flac;*.ogg;*.m4a"), ("모든 파일", "*.*")],
        )
        if p:
            self.var_mus_file.set(p)

    def _run_media_task(self, target_fn, success_title: str = "완료"):
        self.media_progress.start(10)
        self.lbl_media_task.config(text="변환 및 카드 적용 중... 잠시만 기다려 주세요.")
        self._set_media_buttons_state("disabled")

        def _worker():
            err = None
            msg = ""
            try:
                msg = target_fn()
            except Exception as ex:
                err = ex

            def _on_done():
                self.media_progress.stop()
                self.lbl_media_task.config(text="")
                self._set_media_buttons_state("normal")
                self._refresh_media()
                if err:
                    messagebox.showerror("실패", self.controller.format_error_message(err))
                else:
                    messagebox.showinfo(success_title, msg)

            self.root.after(0, _on_done)

        threading.Thread(target=_worker, daemon=True).start()

    def _on_apply_bg(self):
        if not self.controller.is_card_loaded():
            messagebox.showinfo("안내", "먼저 SD카드를 열어주세요.")
            return
        src = self.var_bg_file.get().strip()
        if not src or not os.path.isfile(src):
            messagebox.showinfo("안내", "먼저 바꿀 배경 이미지 파일을 선택해 주세요.")
            return

        mode = self.var_bg_mode.get()
        if not messagebox.askyesno(
            "배경 이미지 변경 확인",
            f"선택한 이미지로 카드 배경을 변경하시겠습니까?\n(기존 원본 파일은 PC 백업 폴더에 자동으로 보관됩니다.)",
        ):
            return

        self._run_media_task(
            lambda: self.controller.apply_background(src, mode), "배경 변경 완료"
        )

    def _on_apply_vid(self):
        if not self.controller.is_card_loaded():
            messagebox.showinfo("안내", "먼저 SD카드를 열어주세요.")
            return
        src = self.var_vid_file.get().strip()
        if not src or not os.path.isfile(src):
            messagebox.showinfo("안내", "먼저 바꿀 동영상 파일을 선택해 주세요.")
            return

        targets = ["demo.avi", "demo_384x224.avi", "demo_640x480.avi", "demo_1024x600.avi"]
        if self.var_vid_en.get():
            targets += ["demo_en.avi", "demo_en_384x224.avi", "demo_en_640x480.avi", "demo_en_1024x600.avi"]

        mode = self.var_vid_mode.get()
        if not messagebox.askyesno(
            "대기 영상 변경 확인",
            f"총 {len(targets)}개의 대기 영상 파일을 새로 변환하여 변경하시겠습니까?\n(영상 길이는 앞 30초가 적용되며, 기존 원본 파일은 PC 백업 폴더에 안전하게 보관됩니다.)",
        ):
            return

        self._run_media_task(
            lambda: self.controller.apply_demo_video(src, targets, mode),
            "대기 영상 변경 완료",
        )

    def _on_apply_mus(self):
        if not self.controller.is_card_loaded():
            messagebox.showinfo("안내", "먼저 SD카드를 열어주세요.")
            return
        src = self.var_mus_file.get().strip()
        if not src or not os.path.isfile(src):
            messagebox.showinfo("안내", "먼저 바꿀 음악 파일을 선택해 주세요.")
            return

        if not messagebox.askyesno(
            "배경 음악 변경 확인",
            f"선택한 음악 파일로 메뉴 배경 음악을 변경하시겠습니까?\n(기존 원본 파일은 PC 백업 폴더에 자동으로 보관됩니다.)",
        ):
            return

        self._run_media_task(
            lambda: self.controller.apply_music(src), "배경 음악 변경 완료"
        )

    def _on_undo_media(self):
        if not self.controller.is_card_loaded():
            messagebox.showinfo("안내", "먼저 SD카드를 열어주세요.")
            return

        sel = self.cb_orig_backup.get().strip()
        if not sel:
            messagebox.showinfo("안내", "되돌릴 원본 보관본을 선택해 주세요.")
            return

        backup_dir = self.controller._get_effective_media_backup_dir()
        item_path = os.path.join(backup_dir, sel)
        if not os.path.isdir(item_path):
            messagebox.showerror("오류", f"보관 폴더를 찾을 수 없습니다: {sel}")
            return

        if not messagebox.askyesno(
            "원본 되돌리기 확인",
            f"'{sel}'에 보관된 파일들로 카드의 미디어를 되돌리시겠습니까?\n(현재 파일도 새로운 보관본으로 자동 보관됩니다.)",
        ):
            return

        self._run_media_task(
            lambda: self.controller.undo_media(item_path), "원본 되돌리기 완료"
        )

    def _refresh_media(self):
        if not hasattr(self, "lbl_ffmpeg_status"):
            return

        if not self.controller.is_card_loaded():
            self.lbl_ffmpeg_status.config(
                text="● 미디어 상태: 먼저 SD카드를 열어 주세요", foreground="#555555"
            )
            return

        try:
            st = self.controller.get_media_status()
            if st.has_ffmpeg:
                self.lbl_ffmpeg_status.config(
                    text="● 변환 프로그램(ffmpeg): 정상 동작 가능", foreground="green"
                )
            else:
                self.lbl_ffmpeg_status.config(
                    text="▲ 변환 프로그램(ffmpeg)을 찾을 수 없습니다 (변환 기능 비활성)",
                    foreground="orange",
                )
        except Exception:
            pass

        # Update backups combobox
        try:
            from editor.core import media as core_media
            backup_dir = self.controller._get_effective_media_backup_dir()
            items = core_media.list_media_originals(backup_dir)
            names = [it.folder_name for it in reversed(items)]
            self.cb_orig_backup["values"] = names
            if names:
                self.cb_orig_backup.current(0)
            else:
                self.cb_orig_backup.set("")
        except Exception:
            pass

    def _on_show_guide(self):
        """Display the user guide window (singleton)."""
        if self._guide_window and self._guide_window.winfo_exists():
            self._guide_window.deiconify()
            self._guide_window.lift()
            self._guide_window.focus_force()
            return

        self._guide_window = win = tk.Toplevel(self.root)
        win.title("Minos 판도라사가 에디터 - 사용 안내")
        win.geometry("660x460")
        win.minsize(580, 380)
        win.resizable(True, True)
        win.transient(self.root)

        def _on_close():
            self._guide_window = None
            win.destroy()

        win.protocol("WM_DELETE_WINDOW", _on_close)

        sections = get_sections()

        frame_left = ttk.Frame(win, padding=10)
        frame_left.pack(side=tk.LEFT, fill=tk.Y)

        ttk.Label(frame_left, text="안내 목차", font=("맑은 고딕", 10, "bold")).pack(
            anchor=tk.W, pady=(0, 5)
        )

        list_box = tk.Listbox(
            frame_left,
            width=20,
            font=("맑은 고딕", 9),
            selectmode=tk.SINGLE,
            exportselection=False,
        )
        list_box.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scroll_l = ttk.Scrollbar(frame_left, orient=tk.VERTICAL, command=list_box.yview)
        list_box.configure(yscrollcommand=scroll_l.set)
        scroll_l.pack(side=tk.RIGHT, fill=tk.Y)

        for s in sections:
            list_box.insert(tk.END, s.title)

        frame_right = ttk.Frame(win, padding=10)
        frame_right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        lbl_section_title = ttk.Label(frame_right, text="", font=("맑은 고딕", 11, "bold"))
        lbl_section_title.pack(anchor=tk.W, pady=(0, 5))

        frame_text = ttk.Frame(frame_right)
        frame_text.pack(fill=tk.BOTH, expand=True)

        text_body = tk.Text(
            frame_text,
            wrap=tk.WORD,
            font=("맑은 고딕", 10),
            padx=8,
            pady=8,
            relief=tk.SOLID,
            borderwidth=1,
        )
        text_body.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scroll_r = ttk.Scrollbar(frame_text, orient=tk.VERTICAL, command=text_body.yview)
        text_body.configure(yscrollcommand=scroll_r.set)
        scroll_r.pack(side=tk.RIGHT, fill=tk.Y)

        def _on_select(event=None):
            sel = list_box.curselection()
            if not sel:
                return
            idx = sel[0]
            sec = sections[idx]
            lbl_section_title.config(text=f"📌 {sec.title}")

            text_body.config(state=tk.NORMAL)
            text_body.delete("1.0", tk.END)
            text_body.insert("1.0", sec.body)
            text_body.config(state=tk.DISABLED)

        list_box.bind("<<ListboxSelect>>", _on_select)

        if sections:
            list_box.selection_set(0)
            list_box.activate(0)
            _on_select()

        frame_bottom = ttk.Frame(win, padding=8)
        frame_bottom.pack(side=tk.BOTTOM, fill=tk.X)
        ttk.Button(frame_bottom, text="닫기", command=_on_close).pack(side=tk.RIGHT, padx=5)

    def _on_browse_card(self):
        selected = filedialog.askdirectory(title="판도라 SD카드 폴더 선택")
        if selected:
            self.var_card_path.set(selected)
            self._on_open_card()

    def _on_open_card(self):
        path = self.var_card_path.get().strip()
        try:
            self.controller.open_card(path)
            self._refresh_all()
        except Exception as e:
            msg = self.controller.format_error_message(e)
            messagebox.showerror("카드 열기 실패", msg)

    def _refresh_all(self):
        self._refresh_hook()
        self._refresh_list()
        self._refresh_systems()
        self._refresh_settings()
        self._refresh_backups()
        self._refresh_media()

    def _refresh_hook(self):
        if not self.controller.is_card_loaded():
            self.lbl_hook.config(
                text="● 상태: 먼저 SD카드를 열어 주세요 — 자세한 방법은 [사용 안내]",
                foreground="#555555",
            )
            return
        s = self.controller.get_hook_status()
        if s.is_ok:
            self.lbl_hook.config(text=f"● 훅 상태: {s.status_label}", foreground="green")
        else:
            self.lbl_hook.config(
                text=f"▲ 훅 상태: {s.status_label} ({s.details})", foreground="orange"
            )

    def _refresh_list(self):
        if not self.controller.is_card_loaded():
            return
        for item in self.tree.get_children():
            self.tree.delete(item)

        ratio_map = {
            "default": "기본",
            "original": "원래 비율",
            "full": "가득 채움",
        }
        quality_map = {
            "default": "기본",
            "sharp": "선명하게",
            "smooth": "부드럽게",
        }

        rows = self.controller.get_games()
        for r in rows:
            r_label = ratio_map.get(getattr(r, "ratio", "default"), "기본")
            q_label = quality_map.get(getattr(r, "quality", "default"), "기본")
            self.tree.insert("", tk.END, values=(r.menu_no, r.folder, r.shown_title, r.file_name, r_label, q_label))

        warn = self.controller.get_game_count_warning()
        if warn:
            self.lbl_warning.config(text=warn)
        else:
            self.lbl_warning.config(text=f"총 {len(rows)}개 게임")

    def _on_change_ratio(self):
        self._on_change_game_options()

    def _on_change_game_options(self):
        if not self.controller.is_card_loaded():
            messagebox.showinfo("안내", "먼저 SD카드를 열어 주세요.")
            return
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("안내", "화면·화질 설정을 변경할 게임을 목록에서 먼저 선택해 주세요.")
            return

        file_names = []
        titles = []
        for it in selected:
            vals = self.tree.item(it, "values")
            if vals:
                file_names.append(vals[3])
                titles.append(vals[2])

        win = tk.Toplevel(self.root)
        win.title("게임 화면·화질 설정")
        win.geometry("420x420")
        win.transient(self.root)
        win.grab_set()

        f_content = ttk.Frame(win, padding=15)
        f_content.pack(fill=tk.BOTH, expand=True)

        if len(file_names) == 1:
            ttk.Label(f_content, text=f"게임: {titles[0]}", font=("맑은 고딕", 9, "bold")).pack(anchor=tk.W, pady=(0, 2))
            ttk.Label(f_content, text=f"파일: {file_names[0]}", foreground="#666666").pack(anchor=tk.W, pady=(0, 10))
        else:
            ttk.Label(f_content, text=f"선택된 게임: 총 {len(file_names)}개", font=("맑은 고딕", 10, "bold"), foreground="#224488").pack(anchor=tk.W, pady=(0, 10))

        grp_ratio = ttk.LabelFrame(f_content, text=" 화면 비율 ", padding=8)
        grp_ratio.pack(fill=tk.X, pady=(0, 8))
        var_ratio = tk.StringVar(value="keep")
        ttk.Radiobutton(grp_ratio, text="(변경 안 함)", variable=var_ratio, value="keep").pack(anchor=tk.W, pady=2)
        ttk.Radiobutton(grp_ratio, text="기본 (전체 설정 따름)", variable=var_ratio, value="default").pack(anchor=tk.W, pady=2)
        ttk.Radiobutton(grp_ratio, text="원래 비율 (화면 비율 유지)", variable=var_ratio, value="original").pack(anchor=tk.W, pady=2)
        ttk.Radiobutton(grp_ratio, text="가득 채움 (화면 가득 채우기)", variable=var_ratio, value="full").pack(anchor=tk.W, pady=2)

        grp_quality = ttk.LabelFrame(f_content, text=" 화질 ", padding=8)
        grp_quality.pack(fill=tk.X, pady=(0, 8))
        var_quality = tk.StringVar(value="keep")
        ttk.Radiobutton(grp_quality, text="(변경 안 함)", variable=var_quality, value="keep").pack(anchor=tk.W, pady=2)
        ttk.Radiobutton(grp_quality, text="기본 (전체 설정 따름)", variable=var_quality, value="default").pack(anchor=tk.W, pady=2)
        ttk.Radiobutton(grp_quality, text="선명하게 (픽셀 도트 유지)", variable=var_quality, value="sharp").pack(anchor=tk.W, pady=2)
        ttk.Radiobutton(grp_quality, text="부드럽게 (살짝 번짐)", variable=var_quality, value="smooth").pack(anchor=tk.W, pady=2)

        ttk.Label(
            f_content,
            text="※ 기기 환경에 따라 확인이 필요합니다.\n   먼저 게임 하나로 시험해 보세요.",
            foreground="#335599",
            font=("맑은 고딕", 8),
        ).pack(anchor=tk.W, pady=(4, 0))

        f_btn = ttk.Frame(f_content)
        f_btn.pack(side=tk.BOTTOM, fill=tk.X, pady=(10, 0))

        def _apply():
            r_val = None if var_ratio.get() == "keep" else var_ratio.get()
            q_val = None if var_quality.get() == "keep" else var_quality.get()
            if r_val is None and q_val is None:
                messagebox.showinfo("안내", "변경할 화면 비율이나 화질 설정을 선택해 주세요.")
                return
            try:
                msg = self.controller.set_game_options(file_names, ratio=r_val, quality=q_val)
                self._refresh_list()
                self._refresh_systems()
                win.destroy()
                messagebox.showinfo("화면·화질 설정 완료", msg)
            except Exception as ex:
                messagebox.showerror("오류", self.controller.format_error_message(ex))

        ttk.Button(f_btn, text="저장", command=_apply).pack(side=tk.RIGHT, padx=3)
        ttk.Button(f_btn, text="취소", command=win.destroy).pack(side=tk.RIGHT, padx=3)

    def _refresh_systems(self):
        if not self.controller.is_card_loaded():
            return
        if not hasattr(self, "tree_sys"):
            return
        for item in self.tree_sys.get_children():
            self.tree_sys.delete(item)

        ratio_map = {
            "default": "기본",
            "original": "원래 비율",
            "full": "가득 채움",
            "mixed": "섞여 있음",
        }
        quality_map = {
            "default": "기본",
            "sharp": "선명하게",
            "smooth": "부드럽게",
            "mixed": "섞여 있음",
        }

        try:
            sys_rows = self.controller.get_systems()
            for s in sys_rows:
                r_label = ratio_map.get(s.ratio, s.ratio)
                q_label = quality_map.get(s.quality, s.quality)
                self.tree_sys.insert("", tk.END, values=(s.folder, f"{s.game_count}개", r_label, q_label))
        except Exception:
            pass

    def _on_change_system_options(self):
        if not self.controller.is_card_loaded():
            messagebox.showinfo("안내", "먼저 SD카드를 열어 주세요.")
            return
        sel = self.tree_sys.focus()
        if not sel:
            messagebox.showinfo("안내", "설정을 변경할 기종을 목록에서 먼저 선택해 주세요.")
            return
        vals = self.tree_sys.item(sel, "values")
        if not vals:
            return
        folder = vals[0]

        win = tk.Toplevel(self.root)
        win.title("기종별 화면·화질 설정")
        win.geometry("400x400")
        win.transient(self.root)
        win.grab_set()

        f_content = ttk.Frame(win, padding=15)
        f_content.pack(fill=tk.BOTH, expand=True)

        ttk.Label(f_content, text=f"기종: {folder}", font=("맑은 고딕", 10, "bold"), foreground="#224488").pack(anchor=tk.W, pady=(0, 10))

        grp_ratio = ttk.LabelFrame(f_content, text=" 화면 비율 ", padding=8)
        grp_ratio.pack(fill=tk.X, pady=(0, 8))
        var_ratio = tk.StringVar(value="keep")
        ttk.Radiobutton(grp_ratio, text="(변경 안 함)", variable=var_ratio, value="keep").pack(anchor=tk.W, pady=2)
        ttk.Radiobutton(grp_ratio, text="기본 (전체 설정 따름)", variable=var_ratio, value="default").pack(anchor=tk.W, pady=2)
        ttk.Radiobutton(grp_ratio, text="원래 비율 (화면 비율 유지)", variable=var_ratio, value="original").pack(anchor=tk.W, pady=2)
        ttk.Radiobutton(grp_ratio, text="가득 채움 (화면 가득 채우기)", variable=var_ratio, value="full").pack(anchor=tk.W, pady=2)

        grp_quality = ttk.LabelFrame(f_content, text=" 화질 ", padding=8)
        grp_quality.pack(fill=tk.X, pady=(0, 8))
        var_quality = tk.StringVar(value="keep")
        ttk.Radiobutton(grp_quality, text="(변경 안 함)", variable=var_quality, value="keep").pack(anchor=tk.W, pady=2)
        ttk.Radiobutton(grp_quality, text="기본 (전체 설정 따름)", variable=var_quality, value="default").pack(anchor=tk.W, pady=2)
        ttk.Radiobutton(grp_quality, text="선명하게 (픽셀 도트 유지)", variable=var_quality, value="sharp").pack(anchor=tk.W, pady=2)
        ttk.Radiobutton(grp_quality, text="부드럽게 (살짝 번짐)", variable=var_quality, value="smooth").pack(anchor=tk.W, pady=2)

        ttk.Label(
            f_content,
            text="※ 이미 개별 설정된 기종의 경우 기존 값이 덮어써집니다.\n   기기 환경에 따라 확인이 필요합니다.",
            foreground="#335599",
            font=("맑은 고딕", 8),
        ).pack(anchor=tk.W, pady=(4, 0))

        f_btn = ttk.Frame(f_content)
        f_btn.pack(side=tk.BOTTOM, fill=tk.X, pady=(10, 0))

        def _apply():
            r_val = None if var_ratio.get() == "keep" else var_ratio.get()
            q_val = None if var_quality.get() == "keep" else var_quality.get()
            if r_val is None and q_val is None:
                messagebox.showinfo("안내", "변경할 설정을 선택해 주세요.")
                return
            try:
                msg = self.controller.set_system_options(folder, ratio=r_val, quality=q_val)
                self._refresh_systems()
                win.destroy()
                messagebox.showinfo("기종별 설정 완료", msg)
            except Exception as ex:
                messagebox.showerror("오류", self.controller.format_error_message(ex))

        ttk.Button(f_btn, text="저장", command=_apply).pack(side=tk.RIGHT, padx=3)
        ttk.Button(f_btn, text="취소", command=win.destroy).pack(side=tk.RIGHT, padx=3)

    def _refresh_settings(self):
        if not self.controller.is_card_loaded():
            return
        try:
            views = self.controller.get_settings()
            for v in views:
                if v.name in self.setting_vars:
                    var = self.setting_vars[v.name]
                    if v.type_str == "bool":
                        var.set(v.value.lower() == "true")
                    elif v.type_str == "float":
                        try:
                            val_f = float(v.value) if v.value else 0.2
                            if val_f < 0.0 or val_f > 1.0:
                                val_f = 0.2
                        except (ValueError, TypeError):
                            val_f = 0.2
                        var.set(val_f)
                        self.lbl_scan_val.config(text=f"{val_f:.2f}")
                    elif v.type_str == "int":
                        try:
                            val_i = int(v.value) if v.value else 10
                            if val_i < 0 or val_i > 100:
                                val_i = 10
                        except (ValueError, TypeError):
                            val_i = 10
                        var.set(val_i)
                        self.lbl_vol_val.config(text=str(val_i))
        except Exception:
            pass

    def _on_save_settings(self):
        if not self.controller.is_card_loaded():
            messagebox.showinfo("안내", "먼저 SD카드를 열어주세요.")
            return

        changes = {
            _KEY_STRETCH: self.setting_vars[_KEY_STRETCH].get(),
            _KEY_SMOOTH: self.setting_vars[_KEY_SMOOTH].get(),
            _KEY_FORCED: self.setting_vars[_KEY_FORCED].get(),
            "useBetterScanlines": self.setting_vars["useBetterScanlines"].get(),
            "forceSmoothCGA": self.setting_vars["forceSmoothCGA"].get(),
            "scanlineOpacity": round(self.setting_vars["scanlineOpacity"].get(), 2),
            "menuMusic": self.setting_vars["menuMusic"].get(),
            "musicVolume": int(self.setting_vars["musicVolume"].get()),
        }

        try:
            msg = self.controller.save_settings(changes)
            self._refresh_settings()
            messagebox.showinfo("설정 저장 완료", msg)
        except Exception as e:
            messagebox.showerror("설정 저장 실패", self.controller.format_error_message(e))

    def _on_toggle_tags(self):
        self.controller.use_tags = self.var_tags.get()
        self._refresh_list()

    def _on_tree_double_click(self, event):
        item = self.tree.focus()
        if not item:
            return
        values = self.tree.item(item, "values")
        if not values:
            return
        folder = values[1]
        file_name = values[3]

        current_title = ""
        for r in self.controller.get_games():
            if r.file_name == file_name:
                current_title = r.raw_title
                break

        new_title = simpledialog.askstring(
            "제목 수정",
            f"메뉴에 표시할 새 제목을 입력하세요:\n(기종: {folder}, 파일: {file_name})",
            initialvalue=current_title,
            parent=self.root,
        )
        if new_title is None:
            return

        warn = self.controller.title_warning(folder, new_title)
        if warn:
            messagebox.showwarning("제목 길이 안내", warn)

        try:
            self.controller.update_title(file_name, new_title)
            self._refresh_list()
        except Exception as e:
            messagebox.showerror("오류", self.controller.format_error_message(e))

    def _on_add_game(self):
        if not self.controller.is_card_loaded():
            messagebox.showinfo("안내", "먼저 SD카드를 열어주세요.")
            return

        src = filedialog.askopenfilename(
            title="추가할 롬 파일 선택",
            filetypes=[
                (
                    "ROM 파일",
                    "*.zip *.bin *.smd *.md *.sfc *.smc *.nes *.gba *.gb *.gbc *.pce",
                ),
                ("모든 파일", "*.*"),
            ],
        )
        if not src:
            return

        folders = self.controller.get_supported_folders()
        if not folders:
            messagebox.showerror("오류", "지원 기종 목록을 읽을 수 없습니다.")
            return

        dlg = tk.Toplevel(self.root)
        dlg.title("기종 및 제목 설정")
        dlg.geometry("380x220")
        dlg.transient(self.root)
        dlg.grab_set()

        ttk.Label(dlg, text="선택한 파일:").pack(anchor=tk.W, padx=15, pady=(10, 2))
        ttk.Label(dlg, text=os.path.basename(src), font=("맑은 고딕", 9, "bold")).pack(
            anchor=tk.W, padx=15
        )

        ttk.Label(dlg, text="기종 폴더:").pack(anchor=tk.W, padx=15, pady=(10, 2))
        cb_folder = ttk.Combobox(dlg, values=folders, state="readonly")
        cb_folder.pack(fill=tk.X, padx=15)
        ext = os.path.splitext(src)[1].lower()
        if ext in (".gba",):
            cb_folder.set("gba")
        elif ext in (".md", ".smd", ".gen"):
            cb_folder.set("genesis")
        else:
            cb_folder.current(0)

        ttk.Label(dlg, text="메뉴 표시 제목:").pack(anchor=tk.W, padx=15, pady=(10, 2))
        stem = os.path.splitext(os.path.basename(src))[0]
        var_title = tk.StringVar(value=stem.replace("_", " "))
        entry_title = ttk.Entry(dlg, textvariable=var_title)
        entry_title.pack(fill=tk.X, padx=15)

        def _do_add():
            folder = cb_folder.get()
            title = var_title.get().strip()
            warn = self.controller.title_warning(folder, title)
            if warn:
                messagebox.showwarning("제목 길이 안내", warn)
            try:
                self.controller.add_game(src, folder, display_title=title if title else None)
                dlg.destroy()
                self._refresh_list()
                messagebox.showinfo("성공", f"게임 '{os.path.basename(src)}'이(가) 추가되었습니다.")
            except Exception as e:
                messagebox.showerror("추가 실패", self.controller.format_error_message(e))

        btn_box = ttk.Frame(dlg)
        btn_box.pack(fill=tk.X, padx=15, pady=15)
        ttk.Button(btn_box, text="추가", command=_do_add).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_box, text="취소", command=dlg.destroy).pack(side=tk.RIGHT)

    def _on_apply_patch(self):
        if not self.controller.is_card_loaded():
            messagebox.showinfo("안내", "먼저 SD카드를 열어주세요.")
            return
        try:
            res = self.controller.apply_patch(use_tags=self.var_tags.get())
            self._refresh_all()
            messagebox.showinfo("적용 완료", res.message)
        except Exception as e:
            messagebox.showerror("적용 실패", self.controller.format_error_message(e))


def main():
    root = tk.Tk()
    app = PandoraEditorApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()

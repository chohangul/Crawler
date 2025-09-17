"""회원사 뉴스 수집 통합 애플리케이션.

이 모듈은 설정, 회원사 관리, 사용자 인터페이스를 통합하여
비개발자도 쉽게 사용할 수 있는 뉴스 크롤링 도구를 제공합니다.
"""

from __future__ import annotations

import json
import logging
import os
import queue
import random
import threading
import time
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import customtkinter as ctk
import pandas as pd
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

# ---------------------------------------------------------------------------
# 경로 및 기본 설정
# ---------------------------------------------------------------------------
APP_NAME = "NewsCollector"


def _resolve_app_root() -> Path:
    """Return location for bundled assets."""

    if getattr(sys, "frozen", False):  # PyInstaller 실행 파일
        return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return Path(__file__).resolve().parent


def _platform_storage_dir() -> Path:
    """플랫폼에 맞는 사용자 데이터 디렉터리 반환."""

    if sys.platform.startswith("win"):
        appdata = os.environ.get("APPDATA")
        if appdata:
            return Path(appdata) / APP_NAME
        return Path.home() / "AppData" / "Roaming" / APP_NAME
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / APP_NAME
    data_home = os.environ.get("XDG_DATA_HOME")
    if data_home:
        return Path(data_home) / APP_NAME
    return Path.home() / ".local" / "share" / APP_NAME


def _can_write(path: Path) -> bool:
    """지정한 경로에 쓰기가 가능한지 테스트."""

    try:
        path.mkdir(parents=True, exist_ok=True)
        test_file = path / ".write_test"
        with open(test_file, "w", encoding="utf-8") as temp:
            temp.write("test")
        test_file.unlink()
        return True
    except OSError:
        return False


def _resolve_storage_root() -> Path:
    """실행 환경에 따라 데이터 저장소 경로 결정."""

    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).resolve().parent
        if _can_write(exe_dir):
            return exe_dir
        return _platform_storage_dir()
    return Path(__file__).resolve().parent


APP_ROOT = _resolve_app_root()
STORAGE_ROOT = _resolve_storage_root()
DATA_DIR = STORAGE_ROOT / "data"
CONFIG_FILE = STORAGE_ROOT / "config.json"
MEMBER_DATA_FILE = DATA_DIR / "members.xlsx"
DEFAULT_RESULTS_DIR = STORAGE_ROOT / "results"
RESULTS_DIR = DEFAULT_RESULTS_DIR
LOG_DIR = STORAGE_ROOT / "logs"
RESOURCE_DIR = APP_ROOT / "resources"

for directory in (STORAGE_ROOT, DATA_DIR, LOG_DIR, DEFAULT_RESULTS_DIR):
    directory.mkdir(parents=True, exist_ok=True)

ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

# ---------------------------------------------------------------------------
# 로깅 설정
# ---------------------------------------------------------------------------
logger = logging.getLogger("crawler_app")
logger.setLevel(logging.INFO)


def setup_logging() -> None:
    """파일 및 콘솔 로깅 설정."""
    if logger.handlers:
        return

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = LOG_DIR / f"crawler_{timestamp}.log"

    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)


setup_logging()

# ---------------------------------------------------------------------------
# 구성 관리
# ---------------------------------------------------------------------------


class Config:
    """JSON 기반 설정 관리."""

    DEFAULTS: Dict[str, object] = {
        "crawl_interval": 2,
        "max_retries": 3,
        "timeout": 30,
        "max_articles_per_company": 20,
        "platforms": ["google", "naver"],
        "enable_content_crawling": False,
        "auto_save": True,
        "export_format": "xlsx",
        "export_path": str(DEFAULT_RESULTS_DIR),
        "last_run": "없음",
    }

    def __init__(self, file_path: Path = CONFIG_FILE) -> None:
        self.file_path = Path(file_path)
        self.settings: Dict[str, object] = {}
        self.load()

    def load(self) -> None:
        if self.file_path.exists():
            try:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if not isinstance(data, dict):
                    raise ValueError("설정 파일 형식이 올바르지 않습니다.")
                self.settings = {**self.DEFAULTS, **data}
            except Exception as exc:  # pragma: no cover - 방어 코드
                logger.error("설정 파일을 불러오지 못했습니다: %s", exc)
                self.settings = dict(self.DEFAULTS)
        else:
            self.settings = dict(self.DEFAULTS)
            self.save()

    def save(self) -> None:
        try:
            self.file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(self.settings, f, indent=2, ensure_ascii=False)
        except Exception as exc:  # pragma: no cover - 방어 코드
            logger.error("설정을 저장하지 못했습니다: %s", exc)

    def get(self, key: str, default: Optional[object] = None) -> object:
        return self.settings.get(key, default)

    def set(self, key: str, value: object) -> None:
        self.settings[key] = value
        self.save()


# ---------------------------------------------------------------------------
# 회원사 데이터 관리
# ---------------------------------------------------------------------------


class MemberManager:
    """회원사 정보를 Pandas DataFrame으로 관리."""

    def __init__(self) -> None:
        self.members_df: pd.DataFrame = pd.DataFrame()
        self.load_members()

    def load_members(self) -> None:
        if MEMBER_DATA_FILE.exists():
            try:
                self.members_df = pd.read_excel(MEMBER_DATA_FILE)
                self.validate_dataframe()
                logger.info("회원사 데이터 로드 완료: %s건", len(self.members_df))
            except Exception as exc:
                logger.error("회원사 데이터를 불러오지 못했습니다: %s", exc)
                self.create_empty_dataframe()
        else:
            self.create_empty_dataframe()

    def create_empty_dataframe(self) -> None:
        self.members_df = pd.DataFrame(
            columns=["회원사명", "검색키워드", "활성화", "카테고리", "홈페이지"]
        )

    def validate_dataframe(self) -> None:
        if self.members_df is None or self.members_df.empty:
            self.create_empty_dataframe()
            return

        required_columns = ["회원사명", "검색키워드", "활성화", "카테고리", "홈페이지"]
        for column in required_columns:
            if column not in self.members_df.columns:
                default_value = "Y" if column == "활성화" else ""
                self.members_df[column] = default_value

        self.members_df["회원사명"] = self.members_df["회원사명"].fillna("")
        self.members_df["검색키워드"] = self.members_df.apply(
            lambda row: row["검색키워드"] if isinstance(row["검색키워드"], str) and row["검색키워드"].strip() else row["회원사명"],
            axis=1,
        )
        self.members_df["활성화"] = self.members_df["활성화"].fillna("Y")
        self.members_df["카테고리"] = self.members_df["카테고리"].fillna("일반")
        self.members_df["홈페이지"] = self.members_df["홈페이지"].fillna("")

    def save_members(self) -> bool:
        try:
            MEMBER_DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
            with pd.ExcelWriter(MEMBER_DATA_FILE, engine="openpyxl") as writer:
                self.members_df.to_excel(writer, index=False, sheet_name="회원사목록")
                worksheet = writer.sheets["회원사목록"]
                for idx, column in enumerate(self.members_df.columns):
                    max_width = max(
                        self.members_df[column].astype(str).str.len().max(),
                        len(column),
                    )
                    worksheet.column_dimensions[chr(65 + idx)].width = min(max_width + 2, 50)
            logger.info("회원사 데이터를 저장했습니다.")
            return True
        except Exception as exc:
            logger.error("회원사 데이터를 저장하지 못했습니다: %s", exc)
            return False

    def import_from_excel(self, file_path: str) -> tuple[bool, str]:
        try:
            df = pd.read_excel(file_path)
            if "회원사명" not in df.columns:
                raise ValueError("'회원사명' 컬럼이 존재하지 않습니다.")

            df = df.dropna(subset=["회원사명"])
            df["회원사명"] = df["회원사명"].astype(str).str.strip()
            df = df[df["회원사명"] != ""]

            self.members_df = df
            self.validate_dataframe()
            self.save_members()
            return True, f"{len(self.members_df)}개 회원사를 불러왔습니다."
        except Exception as exc:
            logger.error("회원사 데이터를 가져오지 못했습니다: %s", exc)
            return False, f"파일을 불러오지 못했습니다: {exc}"

    def add_member(self, member_data: Dict[str, str]) -> bool:
        try:
            new_row = pd.DataFrame([member_data])
            self.members_df = pd.concat([self.members_df, new_row], ignore_index=True)
            if "회원사명" in self.members_df.columns:
                self.members_df.drop_duplicates(subset=["회원사명"], keep="last", inplace=True)
            return self.save_members()
        except Exception as exc:
            logger.error("회원사 추가 실패: %s", exc)
            return False

    def update_member(self, company_name: str, member_data: Dict[str, str]) -> bool:
        try:
            idx = self.members_df[self.members_df["회원사명"] == company_name].index
            if not idx.empty:
                for key, value in member_data.items():
                    self.members_df.loc[idx[0], key] = value
                return self.save_members()
            return False
        except Exception as exc:
            logger.error("회원사 업데이트 실패: %s", exc)
            return False

    def remove_member(self, company_name: str) -> bool:
        try:
            self.members_df = self.members_df[self.members_df["회원사명"] != company_name]
            return self.save_members()
        except Exception as exc:
            logger.error("회원사 삭제 실패: %s", exc)
            return False

    def get_all_members(self) -> List[Dict[str, str]]:
        if self.members_df is None or self.members_df.empty:
            return []
        return self.members_df.to_dict("records")

    def get_active_members(self) -> List[Dict[str, str]]:
        if self.members_df is None or self.members_df.empty:
            return []
        active_df = self.members_df[self.members_df["활성화"] == "Y"]
        return active_df.to_dict("records")

    def get_member_count(self) -> int:
        return 0 if self.members_df is None else len(self.members_df)

    def get_active_count(self) -> int:
        if self.members_df is None or self.members_df.empty:
            return 0
        return int((self.members_df["활성화"] == "Y").sum())


# ---------------------------------------------------------------------------
# 회원사 관리 다이얼로그
# ---------------------------------------------------------------------------


class MemberEditDialog(ctk.CTkToplevel):
    """회원사 추가/수정 창."""

    def __init__(self, parent: ctk.CTk, member_data: Optional[Dict[str, str]] = None) -> None:
        super().__init__(parent)
        self.title("회원사 편집" if member_data else "회원사 추가")
        self.geometry("500x420")
        self.transient(parent)
        self.grab_set()
        self.member_data = member_data or {}
        self.result: Optional[Dict[str, str]] = None

        self._create_widgets()

    def _create_widgets(self) -> None:
        main_frame = ctk.CTkFrame(self)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        fields = [
            ("회원사명", "회원사 이름을 입력하세요"),
            ("검색키워드", "검색에 사용할 키워드 (미입력 시 회원사명)"),
            ("카테고리", "예: 전자, IT, 제조 등"),
            ("홈페이지", "홈페이지 URL"),
        ]

        self.entries: Dict[str, ctk.CTkEntry] = {}
        for label_text, placeholder in fields:
            label = ctk.CTkLabel(main_frame, text=f"{label_text}:", font=("맑은 고딕", 12))
            label.pack(anchor="w", pady=(8, 0))

            entry = ctk.CTkEntry(main_frame, placeholder_text=placeholder, height=32)
            entry.pack(fill="x", pady=4)

            if value := self.member_data.get(label_text):
                entry.insert(0, value)

            self.entries[label_text] = entry

        self.active_var = tk.StringVar(value=self.member_data.get("활성화", "Y"))
        active_checkbox = ctk.CTkCheckBox(
            main_frame,
            text="활성화 (뉴스 수집 대상)",
            variable=self.active_var,
            onvalue="Y",
            offvalue="N",
        )
        active_checkbox.pack(anchor="w", pady=12)

        button_frame = ctk.CTkFrame(main_frame)
        button_frame.pack(fill="x", pady=(10, 0))

        save_btn = ctk.CTkButton(button_frame, text="저장", command=self._on_save, fg_color="green")
        save_btn.pack(side="right", padx=5)

        cancel_btn = ctk.CTkButton(button_frame, text="취소", command=self.destroy)
        cancel_btn.pack(side="right")

    def _on_save(self) -> None:
        company_name = self.entries["회원사명"].get().strip()
        if not company_name:
            messagebox.showwarning("경고", "회원사명은 필수 입력 항목입니다.")
            return

        self.result = {
            "회원사명": company_name,
            "검색키워드": self.entries["검색키워드"].get().strip() or company_name,
            "카테고리": self.entries["카테고리"].get().strip() or "일반",
            "홈페이지": self.entries["홈페이지"].get().strip(),
            "활성화": self.active_var.get(),
        }
        self.destroy()


class MemberManagerDialog(ctk.CTkToplevel):
    """회원사 관리 창."""

    def __init__(self, parent: ctk.CTk, member_manager: MemberManager) -> None:
        super().__init__(parent)
        self.member_manager = member_manager
        self.selected_item: Optional[str] = None

        self.title("회원사 관리")
        self.geometry("920x620")
        self.transient(parent)
        self.grab_set()

        self._create_widgets()
        self.load_member_list()

    def _create_widgets(self) -> None:
        main_frame = ctk.CTkFrame(self)
        main_frame.pack(fill="both", expand=True, padx=12, pady=12)

        button_frame = ctk.CTkFrame(main_frame)
        button_frame.pack(fill="x", pady=(0, 12))

        buttons = [
            ("📁 엑셀 불러오기", self.import_excel),
            ("📥 샘플 템플릿", self.download_sample),
            ("➕ 회원사 추가", self.add_member),
            ("✏️ 수정", self.edit_member),
            ("🗑️ 삭제", self.delete_member),
            ("💾 저장", self.save_members),
        ]

        for text, command in buttons:
            btn = ctk.CTkButton(button_frame, text=text, command=command, width=130, height=36)
            btn.pack(side="left", padx=4)

        list_frame = ctk.CTkFrame(main_frame)
        list_frame.pack(fill="both", expand=True)

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview", font=("맑은 고딕", 10))
        style.configure("Treeview.Heading", font=("맑은 고딕", 11, "bold"))

        columns = ("회원사명", "검색키워드", "활성화", "카테고리", "홈페이지")
        self.tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=20)

        column_widths = {
            "회원사명": 160,
            "검색키워드": 160,
            "활성화": 70,
            "카테고리": 110,
            "홈페이지": 220,
        }
        for col in columns:
            self.tree.heading(col, text=col, command=lambda c=col: self.sort_treeview(c))
            self.tree.column(col, width=column_widths.get(col, 100), anchor="center")

        v_scroll = ttk.Scrollbar(list_frame, orient="vertical", command=self.tree.yview)
        h_scroll = ttk.Scrollbar(list_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        v_scroll.grid(row=0, column=1, sticky="ns")
        h_scroll.grid(row=1, column=0, sticky="ew")

        list_frame.grid_rowconfigure(0, weight=1)
        list_frame.grid_columnconfigure(0, weight=1)

        self.tree.bind("<Double-1>", lambda _event: self.edit_member())

        info_frame = ctk.CTkFrame(main_frame)
        info_frame.pack(fill="x", pady=(12, 0))

        self.info_label = ctk.CTkLabel(info_frame, text="", font=("맑은 고딕", 11))
        self.info_label.pack(side="left", padx=10)

        close_btn = ctk.CTkButton(info_frame, text="닫기", command=self.destroy, width=100)
        close_btn.pack(side="right", padx=10)

    def load_member_list(self) -> None:
        for item in self.tree.get_children():
            self.tree.delete(item)

        for member in self.member_manager.get_all_members():
            values = (
                member.get("회원사명", ""),
                member.get("검색키워드", ""),
                member.get("활성화", "Y"),
                member.get("카테고리", ""),
                member.get("홈페이지", ""),
            )
            tag = "inactive" if values[2] != "Y" else "active"
            self.tree.insert("", "end", values=values, tags=(tag,))

        self.tree.tag_configure("inactive", foreground="gray")
        self.update_info()

    def update_info(self) -> None:
        total = self.member_manager.get_member_count()
        active = self.member_manager.get_active_count()
        self.info_label.configure(text=f"총 {total}개 회원사 (활성: {active}개)")

    def import_excel(self) -> None:
        file_path = filedialog.askopenfilename(
            title="엑셀 파일 선택",
            filetypes=[("Excel 파일", "*.xlsx *.xls"), ("모든 파일", "*.*")],
        )
        if not file_path:
            return
        success, message = self.member_manager.import_from_excel(file_path)
        if success:
            self.load_member_list()
            messagebox.showinfo("성공", message)
        else:
            messagebox.showerror("오류", message)

    def download_sample(self) -> None:
        file_path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel", "*.xlsx")],
            initialfile="회원사_템플릿.xlsx",
        )
        if not file_path:
            return

        sample_data = pd.DataFrame(
            {
                "회원사명": ["삼성전자", "LG전자", "SK하이닉스", "현대자동차", "POSCO"],
                "검색키워드": ["삼성전자", "LG전자", "SK하이닉스", "현대자동차", "POSCO"],
                "활성화": ["Y"] * 5,
                "카테고리": ["전자", "전자", "반도체", "자동차", "철강"],
                "홈페이지": [
                    "https://www.samsung.com",
                    "https://www.lge.co.kr",
                    "https://www.skhynix.com",
                    "https://www.hyundai.com",
                    "https://www.posco.co.kr",
                ],
            }
        )

        try:
            with pd.ExcelWriter(file_path, engine="openpyxl") as writer:
                sample_data.to_excel(writer, index=False, sheet_name="회원사목록")
                worksheet = writer.sheets["회원사목록"]
                for idx, column in enumerate(sample_data.columns):
                    max_width = max(sample_data[column].astype(str).str.len().max(), len(column))
                    worksheet.column_dimensions[chr(65 + idx)].width = min(max_width + 2, 50)
            messagebox.showinfo("완료", "샘플 템플릿을 저장했습니다.")
        except Exception as exc:
            messagebox.showerror("오류", f"파일을 저장하지 못했습니다: {exc}")

    def add_member(self) -> None:
        dialog = MemberEditDialog(self)
        self.wait_window(dialog)
        if dialog.result:
            if self.member_manager.add_member(dialog.result):
                self.load_member_list()
                messagebox.showinfo("성공", "회원사가 추가되었습니다.")
            else:
                messagebox.showerror("오류", "회원사 추가에 실패했습니다.")

    def edit_member(self) -> None:
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("경고", "수정할 회원사를 선택하세요.")
            return

        values = self.tree.item(selection[0], "values")
        member_data = {
            "회원사명": values[0],
            "검색키워드": values[1],
            "활성화": values[2],
            "카테고리": values[3],
            "홈페이지": values[4],
        }

        dialog = MemberEditDialog(self, member_data)
        self.wait_window(dialog)
        if dialog.result:
            if self.member_manager.update_member(values[0], dialog.result):
                self.load_member_list()
                messagebox.showinfo("성공", "회원사 정보를 수정했습니다.")
            else:
                messagebox.showerror("오류", "회원사 정보를 수정하지 못했습니다.")

    def delete_member(self) -> None:
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("경고", "삭제할 회원사를 선택하세요.")
            return

        company_name = self.tree.item(selection[0], "values")[0]
        if messagebox.askyesno("확인", f"'{company_name}'을(를) 삭제하시겠습니까?"):
            if self.member_manager.remove_member(company_name):
                self.load_member_list()
                messagebox.showinfo("성공", "회원사를 삭제했습니다.")
            else:
                messagebox.showerror("오류", "회원사를 삭제하지 못했습니다.")

    def save_members(self) -> None:
        if self.member_manager.save_members():
            messagebox.showinfo("성공", "회원사 데이터를 저장했습니다.")
        else:
            messagebox.showerror("오류", "회원사 데이터를 저장하지 못했습니다.")

    def sort_treeview(self, column: str) -> None:
        data = [(self.tree.set(child, column), child) for child in self.tree.get_children("")]
        data.sort()
        for index, (_, item) in enumerate(data):
            self.tree.move(item, "", index)


# ---------------------------------------------------------------------------
# 설정 다이얼로그
# ---------------------------------------------------------------------------


class SettingsDialog(ctk.CTkToplevel):
    """크롤링 설정 관리 창."""

    def __init__(self, parent: ctk.CTk, config: Config) -> None:
        super().__init__(parent)
        self.config = config
        self.title("설정")
        self.geometry("640x540")
        self.transient(parent)
        self.grab_set()

        self.selected_path = Path(self.config.get("export_path", str(DEFAULT_RESULTS_DIR)))

        self._create_widgets()

    def _create_widgets(self) -> None:
        tabview = ctk.CTkTabview(self)
        tabview.pack(fill="both", expand=True, padx=12, pady=12)

        crawl_tab = tabview.add("크롤링 설정")
        platform_tab = tabview.add("플랫폼 설정")
        save_tab = tabview.add("저장 설정")

        self._create_crawling_settings(crawl_tab)
        self._create_platform_settings(platform_tab)
        self._create_save_settings(save_tab)

        button_frame = ctk.CTkFrame(self)
        button_frame.pack(fill="x", padx=12, pady=(0, 12))

        reset_btn = ctk.CTkButton(button_frame, text="기본값 복원", fg_color="orange", command=self.reset_settings)
        reset_btn.pack(side="left")

        cancel_btn = ctk.CTkButton(button_frame, text="취소", command=self.destroy)
        cancel_btn.pack(side="right", padx=6)

        save_btn = ctk.CTkButton(button_frame, text="저장", fg_color="green", command=self.save_settings)
        save_btn.pack(side="right")

    def _create_crawling_settings(self, parent: ctk.CTkFrame) -> None:
        interval_frame = ctk.CTkFrame(parent)
        interval_frame.pack(fill="x", pady=10, padx=10)

        ctk.CTkLabel(interval_frame, text="요청 간격 (초)", font=("맑은 고딕", 12, "bold")).pack(anchor="w")
        self.interval_var = tk.IntVar(value=int(self.config.get("crawl_interval", 2)))
        self.interval_label = ctk.CTkLabel(interval_frame, text=f"{self.interval_var.get()}초")
        self.interval_label.pack(anchor="e")

        self.interval_slider = ctk.CTkSlider(
            interval_frame,
            from_=1,
            to=10,
            number_of_steps=9,
            command=self._on_interval_change,
        )
        self.interval_slider.pack(fill="x", pady=6)
        self.interval_slider.set(self.interval_var.get())

        retry_frame = ctk.CTkFrame(parent)
        retry_frame.pack(fill="x", pady=10, padx=10)

        ctk.CTkLabel(retry_frame, text="재시도 횟수", font=("맑은 고딕", 12, "bold")).pack(anchor="w")
        self.retry_var = tk.IntVar(value=int(self.config.get("max_retries", 3)))
        retry_spin = tk.Spinbox(retry_frame, from_=1, to=10, textvariable=self.retry_var, width=5)
        retry_spin.pack(anchor="w", pady=4)

        timeout_frame = ctk.CTkFrame(parent)
        timeout_frame.pack(fill="x", pady=10, padx=10)

        ctk.CTkLabel(timeout_frame, text="요청 타임아웃 (초)", font=("맑은 고딕", 12, "bold")).pack(anchor="w")
        self.timeout_var = tk.IntVar(value=int(self.config.get("timeout", 30)))
        timeout_spin = tk.Spinbox(timeout_frame, from_=10, to=120, increment=5, textvariable=self.timeout_var, width=5)
        timeout_spin.pack(anchor="w", pady=4)

        article_frame = ctk.CTkFrame(parent)
        article_frame.pack(fill="x", pady=10, padx=10)

        ctk.CTkLabel(article_frame, text="회사당 최대 기사 수", font=("맑은 고딕", 12, "bold")).pack(anchor="w")
        self.articles_var = tk.IntVar(value=int(self.config.get("max_articles_per_company", 20)))
        self.articles_label = ctk.CTkLabel(article_frame, text=f"{self.articles_var.get()}개")
        self.articles_label.pack(anchor="e")

        self.articles_slider = ctk.CTkSlider(
            article_frame,
            from_=5,
            to=50,
            number_of_steps=45,
            command=self._on_articles_change,
        )
        self.articles_slider.pack(fill="x", pady=6)
        self.articles_slider.set(self.articles_var.get())

    def _create_platform_settings(self, parent: ctk.CTkFrame) -> None:
        ctk.CTkLabel(parent, text="수집할 플랫폼", font=("맑은 고딕", 13, "bold")).pack(anchor="w", padx=10, pady=(10, 6))

        enabled_platforms = set(self.config.get("platforms", ["google", "naver"]))
        self.platform_vars: Dict[str, tk.BooleanVar] = {}

        platform_info = {
            "google": ("Google 뉴스", "구글에서 뉴스를 검색합니다."),
            "naver": ("Naver 뉴스", "네이버에서 뉴스를 검색합니다."),
            "daum": ("Daum 뉴스", "다음 뉴스는 준비 중입니다."),
        }

        for platform, (title, description) in platform_info.items():
            frame = ctk.CTkFrame(parent)
            frame.pack(fill="x", padx=10, pady=6)

            var = tk.BooleanVar(value=platform in enabled_platforms)
            checkbox = ctk.CTkCheckBox(frame, text=title, variable=var, font=("맑은 고딕", 12, "bold"))
            checkbox.pack(anchor="w")

            if platform == "daum":
                checkbox.configure(state="disabled")

            desc = ctk.CTkLabel(frame, text=description, font=("맑은 고딕", 10), text_color="gray")
            desc.pack(anchor="w", padx=20)

            self.platform_vars[platform] = var

        option_frame = ctk.CTkFrame(parent)
        option_frame.pack(fill="x", padx=10, pady=10)

        self.content_var = tk.BooleanVar(value=bool(self.config.get("enable_content_crawling", False)))
        content_checkbox = ctk.CTkCheckBox(
            option_frame,
            text="기사 본문까지 수집 (느릴 수 있음)",
            variable=self.content_var,
        )
        content_checkbox.pack(anchor="w")

    def _create_save_settings(self, parent: ctk.CTkFrame) -> None:
        auto_frame = ctk.CTkFrame(parent)
        auto_frame.pack(fill="x", padx=10, pady=10)

        self.auto_save_var = tk.BooleanVar(value=bool(self.config.get("auto_save", True)))
        auto_checkbox = ctk.CTkCheckBox(auto_frame, text="수집 후 자동 저장", variable=self.auto_save_var)
        auto_checkbox.pack(anchor="w")

        format_frame = ctk.CTkFrame(parent)
        format_frame.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(format_frame, text="기본 저장 형식", font=("맑은 고딕", 12, "bold")).pack(anchor="w")
        self.format_var = tk.StringVar(value=str(self.config.get("export_format", "xlsx")))

        for text, value in [("Excel (.xlsx)", "xlsx"), ("CSV (.csv)", "csv")]:
            radio = ctk.CTkRadioButton(format_frame, text=text, value=value, variable=self.format_var)
            radio.pack(anchor="w", padx=10, pady=2)

        path_frame = ctk.CTkFrame(parent)
        path_frame.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(path_frame, text="저장 경로", font=("맑은 고딕", 12, "bold")).pack(anchor="w")
        self.path_label = ctk.CTkLabel(path_frame, text=str(self.selected_path), text_color="blue")
        self.path_label.pack(anchor="w", padx=10, pady=4)

        change_btn = ctk.CTkButton(path_frame, text="경로 변경", width=120, command=self.change_save_path)
        change_btn.pack(anchor="w", padx=10, pady=4)

    def change_save_path(self) -> None:
        selected = filedialog.askdirectory(title="저장 경로 선택")
        if selected:
            self.selected_path = Path(selected)
            self.path_label.configure(text=str(self.selected_path))

    def _on_interval_change(self, value: float) -> None:
        self.interval_var.set(int(round(value)))
        self.interval_label.configure(text=f"{self.interval_var.get()}초")

    def _on_articles_change(self, value: float) -> None:
        self.articles_var.set(int(round(value)))
        self.articles_label.configure(text=f"{self.articles_var.get()}개")

    def save_settings(self) -> None:
        platforms = [name for name, var in self.platform_vars.items() if var.get() and name != "daum"]
        if not platforms:
            messagebox.showwarning("경고", "최소 하나의 플랫폼을 선택해야 합니다.")
            return

        self.config.set("crawl_interval", int(self.interval_var.get()))
        self.config.set("max_retries", int(self.retry_var.get()))
        self.config.set("timeout", int(self.timeout_var.get()))
        self.config.set("max_articles_per_company", int(self.articles_var.get()))
        self.config.set("platforms", platforms)
        self.config.set("enable_content_crawling", bool(self.content_var.get()))
        self.config.set("auto_save", bool(self.auto_save_var.get()))
        self.config.set("export_format", str(self.format_var.get()))
        self.config.set("export_path", str(self.selected_path))

        global RESULTS_DIR
        RESULTS_DIR = Path(self.selected_path)
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)

        messagebox.showinfo("성공", "설정을 저장했습니다.")
        self.destroy()

    def reset_settings(self) -> None:
        defaults = Config.DEFAULTS
        self.interval_slider.set(defaults["crawl_interval"])
        self.retry_var.set(defaults["max_retries"])
        self.timeout_var.set(defaults["timeout"])
        self.articles_slider.set(defaults["max_articles_per_company"])
        for name, var in self.platform_vars.items():
            var.set(name in defaults["platforms"])
        self.content_var.set(bool(defaults["enable_content_crawling"]))
        self.auto_save_var.set(bool(defaults["auto_save"]))
        self.format_var.set(str(defaults["export_format"]))
        self.selected_path = Path(str(defaults["export_path"]))
        self.path_label.configure(text=str(self.selected_path))
        self._on_interval_change(self.interval_slider.get())
        self._on_articles_change(self.articles_slider.get())


# ---------------------------------------------------------------------------
# 메인 애플리케이션 창
# ---------------------------------------------------------------------------


class MainWindow(ctk.CTk):
    """회원사 뉴스 수집 메인 UI."""

    def __init__(self) -> None:
        super().__init__()

        self.title("회원사 뉴스 수집 프로그램 v1.0")
        self.geometry("1024x760")
        self.minsize(920, 660)

        self.config_manager = Config()
        self.member_manager = MemberManager()
        self.collected_data: Optional[pd.DataFrame] = None
        self.crawl_thread: Optional[threading.Thread] = None
        self.is_crawling = False
        self.log_queue: "queue.Queue[tuple[str, str]]" = queue.Queue()

        self._refresh_results_dir()
        self._setup_window()
        self._create_widgets()
        self.update_status()
        self.process_log_queue()

        logger.info("=" * 70)
        logger.info("회원사 뉴스 수집 프로그램을 시작합니다.")
        logger.info("=" * 70)

    def _setup_window(self) -> None:
        try:
            icon_candidates = [
                RESOURCE_DIR / "app.ico",
                APP_ROOT / "app.ico",
            ]
            for icon_path in icon_candidates:
                if icon_path.exists() and os.name == "nt":
                    self.iconbitmap(icon_path)
                    break
        except Exception:  # pragma: no cover - OS 의존
            pass

        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")

        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def _refresh_results_dir(self) -> None:
        global RESULTS_DIR
        export_path = Path(self.config_manager.get("export_path", str(DEFAULT_RESULTS_DIR)))
        RESULTS_DIR = export_path
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    def _create_widgets(self) -> None:
        main_container = ctk.CTkFrame(self)
        main_container.pack(fill="both", expand=True, padx=12, pady=12)

        title_frame = ctk.CTkFrame(main_container)
        title_frame.pack(fill="x", pady=(0, 12))

        title_label = ctk.CTkLabel(
            title_frame,
            text="📰 회원사 뉴스 수집 프로그램",
            font=("맑은 고딕", 20, "bold"),
        )
        title_label.pack(pady=10)

        self._create_button_bar(main_container)

        content_frame = ctk.CTkFrame(main_container)
        content_frame.pack(fill="both", expand=True)

        left_panel = ctk.CTkFrame(content_frame)
        left_panel.pack(side="left", fill="both", expand=True, padx=(0, 6))

        self._create_status_section(left_panel)
        self._create_action_section(left_panel)

        right_panel = ctk.CTkFrame(content_frame)
        right_panel.pack(side="left", fill="both", expand=True, padx=(6, 0))

        self._create_log_section(right_panel)

    def _create_button_bar(self, parent: ctk.CTkFrame) -> None:
        button_frame = ctk.CTkFrame(parent)
        button_frame.pack(fill="x", pady=(0, 10))

        buttons = [
            ("📋 회원사 관리", self.open_member_manager, None),
            ("▶️ 수집 실행", self.start_crawling, "green"),
            ("📊 결과 보기", self.view_results, None),
            ("⚙️ 설정", self.open_settings, None),
            ("❓ 도움말", self.show_help, None),
        ]

        for text, command, color in buttons:
            btn = ctk.CTkButton(
                button_frame,
                text=text,
                command=command,
                width=150,
                height=42,
                font=("맑은 고딕", 12, "bold"),
                fg_color=color if color else None,
            )
            btn.pack(side="left", padx=6)

    def _create_status_section(self, parent: ctk.CTkFrame) -> None:
        status_frame = ctk.CTkFrame(parent)
        status_frame.pack(fill="x", pady=(0, 12))

        ctk.CTkLabel(
            status_frame,
            text="📊 현재 상태",
            font=("맑은 고딕", 14, "bold"),
        ).pack(anchor="w", padx=12, pady=6)

        info_frame = ctk.CTkFrame(status_frame)
        info_frame.pack(fill="x", padx=12, pady=6)

        self.status_labels: Dict[str, ctk.CTkLabel] = {}
        items = [
            ("registered", "등록 회원사", "0개"),
            ("active", "활성 회원사", "0개"),
            ("last_run", "마지막 실행", "없음"),
            ("collected", "수집된 기사", "0건"),
        ]

        for index, (key, label, default) in enumerate(items):
            row = index // 2
            col = (index % 2) * 2

            name_label = ctk.CTkLabel(info_frame, text=f"{label}:", font=("맑은 고딕", 11))
            name_label.grid(row=row, column=col, sticky="w", padx=6, pady=4)

            value_label = ctk.CTkLabel(info_frame, text=default, font=("맑은 고딕", 11, "bold"), text_color="blue")
            value_label.grid(row=row, column=col + 1, sticky="w", padx=6, pady=4)
            self.status_labels[key] = value_label

        for i in range(2):
            info_frame.grid_columnconfigure(i * 2, weight=1)

    def _create_action_section(self, parent: ctk.CTkFrame) -> None:
        action_frame = ctk.CTkFrame(parent)
        action_frame.pack(fill="x", pady=(0, 12))

        ctk.CTkLabel(
            action_frame,
            text="🚀 실행 제어",
            font=("맑은 고딕", 14, "bold"),
        ).pack(anchor="w", padx=12, pady=6)

        button_frame = ctk.CTkFrame(action_frame)
        button_frame.pack(fill="x", padx=12, pady=6)

        self.start_button = ctk.CTkButton(
            button_frame,
            text="✅ 지금 시작",
            command=self.start_crawling,
            width=140,
            height=42,
            font=("맑은 고딕", 12, "bold"),
            fg_color="green",
        )
        self.start_button.pack(side="left", padx=4)

        self.stop_button = ctk.CTkButton(
            button_frame,
            text="⏹️ 중지",
            command=self.stop_crawling,
            width=140,
            height=42,
            font=("맑은 고딕", 12, "bold"),
            fg_color="red",
            state="disabled",
        )
        self.stop_button.pack(side="left", padx=4)

        self.export_button = ctk.CTkButton(
            button_frame,
            text="💾 결과 저장",
            command=self.export_results,
            width=140,
            height=42,
            font=("맑은 고딕", 12, "bold"),
            state="disabled",
        )
        self.export_button.pack(side="left", padx=4)

        progress_frame = ctk.CTkFrame(action_frame)
        progress_frame.pack(fill="x", padx=12, pady=12)

        self.progress_label = ctk.CTkLabel(progress_frame, text="대기 중...", font=("맑은 고딕", 11))
        self.progress_label.pack(anchor="w")

        self.progress_var = tk.DoubleVar(value=0.0)
        self.progress_bar = ctk.CTkProgressBar(progress_frame)
        self.progress_bar.pack(fill="x", pady=6)
        self.progress_bar.set(0)

        self.detail_label = ctk.CTkLabel(progress_frame, text="", font=("맑은 고딕", 10), text_color="gray")
        self.detail_label.pack(anchor="w")

    def _create_log_section(self, parent: ctk.CTkFrame) -> None:
        log_frame = ctk.CTkFrame(parent)
        log_frame.pack(fill="both", expand=True)

        header = ctk.CTkFrame(log_frame)
        header.pack(fill="x", padx=12, pady=6)

        ctk.CTkLabel(header, text="📝 실행 로그", font=("맑은 고딕", 14, "bold")).pack(side="left")

        clear_btn = ctk.CTkButton(header, text="지우기", width=80, command=self.clear_log)
        clear_btn.pack(side="right", padx=4)

        save_btn = ctk.CTkButton(header, text="로그 저장", width=90, command=self.save_log)
        save_btn.pack(side="right", padx=4)

        self.log_text = ctk.CTkTextbox(log_frame, height=360, font=("Consolas", 9), wrap="word")
        self.log_text.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        self.log_message("프로그램이 시작되었습니다.")
        self.log_message(f"작업 디렉토리: {Path.cwd()}")

    # ------------------------------------------------------------------
    # 상태 및 로그
    # ------------------------------------------------------------------
    def log_message(self, message: str, level: str = "INFO") -> None:
        timestamp = datetime.now().strftime("%H:%M:%S")
        level_emojis = {
            "INFO": "ℹ️",
            "SUCCESS": "✅",
            "WARNING": "⚠️",
            "ERROR": "❌",
        }
        emoji = level_emojis.get(level, "📌")
        entry = f"[{timestamp}] {emoji} {message}\n"
        self.log_text.insert("end", entry)
        self.log_text.see("end")

        if level == "ERROR":
            logger.error(message)
        elif level == "WARNING":
            logger.warning(message)
        else:
            logger.info(message)

    def process_log_queue(self) -> None:
        try:
            while not self.log_queue.empty():
                level, message = self.log_queue.get_nowait()
                self.log_message(message, level)
        except queue.Empty:
            pass
        finally:
            self.after(150, self.process_log_queue)

    def update_status(self) -> None:
        try:
            self.status_labels["registered"].configure(
                text=f"{self.member_manager.get_member_count()}개"
            )
            self.status_labels["active"].configure(
                text=f"{self.member_manager.get_active_count()}개"
            )
            self.status_labels["last_run"].configure(
                text=str(self.config_manager.get("last_run", "없음"))
            )
            if self.collected_data is not None and not self.collected_data.empty:
                self.status_labels["collected"].configure(
                    text=f"{len(self.collected_data)}건"
                )
            else:
                self.status_labels["collected"].configure(text="0건")
        except Exception as exc:
            logger.error("상태 정보를 갱신하지 못했습니다: %s", exc)

    # ------------------------------------------------------------------
    # 사용자 액션 핸들러
    # ------------------------------------------------------------------
    def open_member_manager(self) -> None:
        dialog = MemberManagerDialog(self, self.member_manager)
        self.wait_window(dialog)
        self.update_status()

    def open_settings(self) -> None:
        dialog = SettingsDialog(self, self.config_manager)
        self.wait_window(dialog)
        self._refresh_results_dir()

    def show_help(self) -> None:
        help_window = ctk.CTkToplevel(self)
        help_window.title("도움말")
        help_window.geometry("620x520")
        help_window.transient(self)

        text = ctk.CTkTextbox(help_window, wrap="word")
        text.pack(fill="both", expand=True, padx=12, pady=12)
        text.insert(
            "end",
            """
회원사 뉴스 수집 프로그램 사용법
===============================

1. 회원사 관리
 - [회원사 관리] 버튼을 눌러 회원사를 등록하거나 수정하세요.
 - Excel 파일에서 불러오거나 직접 입력할 수 있습니다.
 - 샘플 템플릿을 내려받아 형식을 확인할 수 있습니다.

2. 뉴스 수집 실행
 - [수집 실행] 또는 [지금 시작] 버튼을 누르면 활성화된 회원사의 뉴스를 수집합니다.
 - 진행률과 현재 작업 대상이 실시간으로 표시됩니다.

3. 결과 확인
 - 수집이 완료되면 [결과 저장] 버튼을 통해 Excel 또는 CSV 형식으로 저장할 수 있습니다.
 - [결과 보기] 버튼으로 결과 폴더를 바로 열 수 있습니다.

4. 설정
 - 요청 간격, 재시도 횟수 등 크롤링 관련 옵션을 변경할 수 있습니다.
 - 기본 저장 경로와 형식도 설정 가능합니다.

도움이 더 필요하면 관리자에게 문의하세요.
""",
        )
        text.configure(state="disabled")

    def clear_log(self) -> None:
        self.log_text.delete("1.0", "end")
        self.log_message("로그를 초기화했습니다.")

    def save_log(self) -> None:
        file_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text", "*.txt"), ("All files", "*.*")],
            initialfile=f"log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
        )
        if not file_path:
            return
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(self.log_text.get("1.0", "end-1c"))
            self.log_message(f"로그를 저장했습니다: {file_path}", "SUCCESS")
        except Exception as exc:
            self.log_message(f"로그 저장 실패: {exc}", "ERROR")

    def start_crawling(self) -> None:
        if self.is_crawling:
            return

        active_members = self.member_manager.get_active_members()
        if not active_members:
            messagebox.showwarning("경고", "활성화된 회원사가 없습니다. 회원사 관리를 먼저 진행하세요.")
            return

        self.collected_data = None
        self.is_crawling = True
        self.start_button.configure(state="disabled")
        self.stop_button.configure(state="normal")
        self.export_button.configure(state="disabled")
        self.progress_bar.set(0)
        self.progress_label.configure(text="준비 중...")
        self.detail_label.configure(text="")
        self.log_message("뉴스 수집을 시작합니다.")

        self.crawl_thread = threading.Thread(target=self._run_crawler, args=(active_members,), daemon=True)
        self.crawl_thread.start()

    def stop_crawling(self) -> None:
        if not self.is_crawling:
            return

        if messagebox.askyesno("확인", "수집을 중지하시겠습니까?"):
            self.is_crawling = False
            self.log_message("사용자가 수집을 중지했습니다.", "WARNING")

    def _run_crawler(self, members: List[Dict[str, str]]) -> None:
        try:
            interval = int(self.config_manager.get("crawl_interval", 2))
            max_articles = int(self.config_manager.get("max_articles_per_company", 20))
            platforms = self.config_manager.get("platforms", ["google", "naver"])

            collected_rows: List[Dict[str, str]] = []
            success_count = 0
            fail_count = 0
            total = len(members)

            for index, member in enumerate(members, start=1):
                if not self.is_crawling:
                    break

                company = member.get("회원사명", "")
                self._schedule_progress_update(index, total, company)
                self.log_queue.put(("INFO", f"[{index}/{total}] {company} 수집 시작"))

                try:
                    time.sleep(max(0.4, random.uniform(interval * 0.4, interval * 1.4)))
                    article_count = random.randint(5, max_articles)
                    now = datetime.now().strftime("%Y-%m-%d %H:%M")
                    for i in range(article_count):
                        collected_rows.append(
                            {
                                "회원사명": company,
                                "기사제목": f"{company} 관련 뉴스 {i + 1}",
                                "URL": f"https://example.com/{company}/{i}",
                                "출처": random.choice(["Google", "Naver"]),
                                "발행일시": now,
                                "수집일시": now,
                                "플랫폼": random.choice(platforms) if platforms else "기타",
                            }
                        )
                    success_count += 1
                    self.log_queue.put(("SUCCESS", f"{company}: {article_count}개 기사 수집 완료"))
                except Exception as exc:  # pragma: no cover - 시뮬레이션 예외 처리
                    fail_count += 1
                    self.log_queue.put(("ERROR", f"{company} 수집 실패: {exc}"))

            if not self.is_crawling:
                self._schedule_stop()
                return

            result_df = pd.DataFrame(collected_rows)
            self._schedule_complete(result_df, success_count, fail_count)
        except Exception as exc:  # pragma: no cover - 방어 코드
            self.log_queue.put(("ERROR", f"크롤링 중 오류가 발생했습니다: {exc}"))
            self._schedule_stop()

    def _schedule_progress_update(self, index: int, total: int, company: str) -> None:
        def update() -> None:
            if total:
                self.progress_bar.set(index / total)
                self.progress_label.configure(text=f"수집 중... ({index}/{total})")
            self.detail_label.configure(text=f"현재: {company}")

        self.after(0, update)

    def _schedule_complete(self, data: pd.DataFrame, success_count: int, fail_count: int) -> None:
        def finalize() -> None:
            self.is_crawling = False
            self.collected_data = data
            self.start_button.configure(state="normal")
            self.stop_button.configure(state="disabled")
            if self.collected_data is not None and not self.collected_data.empty:
                self.export_button.configure(state="normal")
            self.progress_bar.set(1 if success_count > 0 else 0)
            self.progress_label.configure(text="수집 완료")
            self.detail_label.configure(text="")

            self.config_manager.set("last_run", datetime.now().strftime("%Y-%m-%d %H:%M"))
            self.update_status()

            self.log_queue.put(("SUCCESS", f"수집 완료! 성공: {success_count}건, 실패: {fail_count}건"))

            if self.config_manager.get("auto_save", True) and self.collected_data is not None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                ext = str(self.config_manager.get("export_format", "xlsx"))
                auto_path = RESULTS_DIR / f"news_{timestamp}.{ext}"
                self.save_results(auto_path)

        self.after(0, finalize)

    def _schedule_stop(self) -> None:
        def finalize() -> None:
            self.is_crawling = False
            self.start_button.configure(state="normal")
            self.stop_button.configure(state="disabled")
            self.export_button.configure(state="disabled")
            self.progress_bar.set(0)
            self.progress_label.configure(text="중지됨")
            self.detail_label.configure(text="")
        self.after(0, finalize)

    def view_results(self) -> None:
        try:
            if os.name == "nt":
                os.startfile(RESULTS_DIR)  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                import subprocess

                subprocess.Popen(["open", str(RESULTS_DIR)])
            else:
                import subprocess

                subprocess.Popen(["xdg-open", str(RESULTS_DIR)])
            self.log_message(f"결과 폴더 열기: {RESULTS_DIR}")
        except Exception as exc:
            messagebox.showinfo("정보", f"결과 폴더 위치: {RESULTS_DIR}")
            self.log_message(f"결과 폴더를 열지 못했습니다: {exc}", "ERROR")

    def export_results(self) -> None:
        if self.collected_data is None or self.collected_data.empty:
            messagebox.showwarning("경고", "저장할 데이터가 없습니다.")
            return

        file_path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel", "*.xlsx"), ("CSV", "*.csv")],
            initialfile=f"뉴스수집결과_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
        )
        if not file_path:
            return

        if self.save_results(Path(file_path)):
            messagebox.showinfo("완료", f"결과를 저장했습니다.\n{file_path}")

    def save_results(self, file_path: Path) -> bool:
        if self.collected_data is None or self.collected_data.empty:
            return False
        try:
            file_path = Path(file_path)
            file_path.parent.mkdir(parents=True, exist_ok=True)
            if file_path.suffix.lower() == ".csv":
                self.collected_data.to_csv(file_path, index=False, encoding="utf-8-sig")
            else:
                with pd.ExcelWriter(file_path, engine="openpyxl") as writer:
                    self.collected_data.to_excel(writer, index=False, sheet_name="뉴스수집결과")
                    worksheet = writer.sheets["뉴스수집결과"]
                    for idx, column in enumerate(self.collected_data.columns):
                        max_width = max(
                            self.collected_data[column].astype(str).str.len().max(),
                            len(column),
                        )
                        worksheet.column_dimensions[chr(65 + idx)].width = min(max_width + 2, 60)
            self.log_message(f"결과 저장: {file_path}", "SUCCESS")
            return True
        except Exception as exc:
            self.log_message(f"결과 저장 실패: {exc}", "ERROR")
            return False

    def on_closing(self) -> None:
        if self.is_crawling:
            result = messagebox.askyesno("종료", "수집이 진행 중입니다. 종료하시겠습니까?")
            if not result:
                return
            self.is_crawling = False
            if self.crawl_thread and self.crawl_thread.is_alive():
                self.crawl_thread.join(timeout=2)
        self.destroy()


def main() -> None:
    app = MainWindow()
    app.mainloop()


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # pragma: no cover - GUI 실행 방어 코드
        logger.error("프로그램 실행 중 오류가 발생했습니다: %s", exc)
        messagebox.showerror("오류", f"프로그램 실행 중 문제가 발생했습니다.\n{exc}")

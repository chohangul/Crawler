#!/usr/bin/env python3
"""NewsCollector Windows 패키지를 생성하는 유틸리티."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path
from typing import Optional

import pandas as pd

APP_NAME = "NewsCollector"
EXECUTABLE_NAME = f"{APP_NAME}.exe"
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
ENTRYPOINT = PROJECT_ROOT / "integrated_main.py"
DIST_DIR = PROJECT_ROOT / "dist"
PYINSTALLER_WORK_DIR = PROJECT_ROOT / "build" / "pyinstaller"
SPEC_DIR = Path(__file__).resolve().parent
PORTABLE_DIR = DIST_DIR / "NewsCollector_Portable"
DEFAULT_VERSION = "1.6.0"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="PyInstaller 실행 파일과 설치 프로그램을 생성합니다.",
    )
    parser.add_argument(
        "--version",
        default=DEFAULT_VERSION,
        help="배포에 사용할 버전 문자열 (기본: %(default)s)",
    )
    parser.add_argument(
        "--skip-installer",
        action="store_true",
        help="Inno Setup 설치 프로그램 생성 단계를 건너뜁니다.",
    )
    parser.add_argument(
        "--keep-build",
        action="store_true",
        help="PyInstaller 작업 디렉터리를 정리하지 않습니다.",
    )
    return parser.parse_args()


def find_icon() -> Optional[Path]:
    candidates = [
        PROJECT_ROOT / "resources" / "app.ico",
        PROJECT_ROOT / "app.ico",
    ]
    for icon in candidates:
        if icon.exists():
            return icon
    return None


def run_pyinstaller() -> Path:
    try:
        import PyInstaller.__main__  # type: ignore
    except ImportError as exc:  # pragma: no cover - 빌드 환경 전용
        raise SystemExit(
            "PyInstaller가 설치되어 있지 않습니다. 'pip install -r requirements-build.txt'를 실행하세요."
        ) from exc

    if not ENTRYPOINT.exists():
        raise SystemExit(f"엔트리 포인트를 찾을 수 없습니다: {ENTRYPOINT}")

    DIST_DIR.mkdir(parents=True, exist_ok=True)
    PYINSTALLER_WORK_DIR.mkdir(parents=True, exist_ok=True)

    existing_exe = DIST_DIR / EXECUTABLE_NAME
    if existing_exe.exists():
        existing_exe.unlink()

    command = [
        str(ENTRYPOINT),
        "--noconfirm",
        "--windowed",
        "--clean",
        f"--name={APP_NAME}",
        f"--distpath={DIST_DIR}",
        f"--workpath={PYINSTALLER_WORK_DIR}",
        f"--specpath={SPEC_DIR}",
        "--collect-all=customtkinter",
        "--hidden-import=customtkinter",
        "--hidden-import=tkinter",
        "--hidden-import=selenium",
        "--hidden-import=webdriver_manager",
        "--hidden-import=openpyxl",
        "--hidden-import=pandas",
        "--hidden-import=beautifulsoup4",
        "--hidden-import=PIL",
        "--hidden-import=lxml",
        "--hidden-import=requests",
    ]

    icon_path = find_icon()
    if icon_path:
        command.append(f"--icon={icon_path}")

    print("[1/4] PyInstaller로 실행 파일을 생성합니다...")
    PyInstaller.__main__.run(command)

    exe_path = DIST_DIR / EXECUTABLE_NAME
    if not exe_path.exists():
        raise SystemExit("PyInstaller 빌드 결과를 찾을 수 없습니다.")

    return exe_path


def create_member_template(target: Path) -> None:
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

    target.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(target, engine="openpyxl") as writer:
        sample_data.to_excel(writer, index=False, sheet_name="회원사목록")
        worksheet = writer.sheets["회원사목록"]
        for idx, column in enumerate(sample_data.columns):
            max_width = max(sample_data[column].astype(str).str.len().max(), len(column))
            worksheet.column_dimensions[chr(65 + idx)].width = min(max_width + 2, 50)


def write_portable_readme(portable_dir: Path, version: str) -> None:
    readme_path = portable_dir / "README.txt"
    readme_content = textwrap.dedent(
        f"""
        {APP_NAME} v{version}
        =====================

        1. 실행 방법
        ------------
        - NewsCollector.exe 파일을 더블 클릭하면 프로그램이 실행됩니다.
        - 처음 실행 시 data/logs/results 폴더가 자동으로 생성되며, 설정과 로그는 동일한 폴더에 저장됩니다.

        2. 회원사 템플릿
        ----------------
        - data/회원사_템플릿.xlsx 파일을 참고하여 회원사 정보를 입력할 수 있습니다.
        - 프로그램 내 [회원사 관리] > [엑셀 불러오기] 버튼으로 파일을 불러오세요.

        3. 설치형 패키지
        ----------------
        - dist/installer 폴더에 생성되는 NewsCollector_Setup.exe를 사용하면
          일반 Windows 프로그램처럼 설치/삭제가 가능합니다.
        - 설치 버전은 사용자 AppData 영역에 데이터를 저장하므로 관리자 권한이 필요하지 않습니다.

        4. 문의
        ------
        - 빌드 또는 배포 과정에 문제가 발생하면 개발팀에 문의하세요.
        """
    ).strip()

    readme_path.write_text(readme_content, encoding="utf-8")


def copy_resources(portable_dir: Path) -> None:
    resources_src = PROJECT_ROOT / "resources"
    resources_dst = portable_dir / "resources"
    if resources_dst.exists():
        shutil.rmtree(resources_dst)
    if resources_src.exists():
        shutil.copytree(resources_src, resources_dst)
    else:
        resources_dst.mkdir()


def create_portable_bundle(exe_path: Path, version: str) -> Path:
    if PORTABLE_DIR.exists():
        shutil.rmtree(PORTABLE_DIR)

    PORTABLE_DIR.mkdir(parents=True)
    shutil.copy2(exe_path, PORTABLE_DIR / EXECUTABLE_NAME)

    for folder in ("data", "logs", "results"):
        (PORTABLE_DIR / folder).mkdir()

    create_member_template(PORTABLE_DIR / "data" / "회원사_템플릿.xlsx")
    write_portable_readme(PORTABLE_DIR, version)
    copy_resources(PORTABLE_DIR)

    print(f"[2/4] 휴대용 패키지 생성 완료: {PORTABLE_DIR}")
    return PORTABLE_DIR


def create_zip_archive(portable_dir: Path, version: str) -> Path:
    archive_base = DIST_DIR / f"{APP_NAME}_Portable_v{version}"
    archive_file = archive_base.with_suffix(".zip")
    if archive_file.exists():
        archive_file.unlink()

    shutil.make_archive(str(archive_base), "zip", root_dir=portable_dir)
    print(f"[3/4] 휴대용 ZIP 패키지 생성: {archive_file}")
    return archive_file


def build_installer(portable_dir: Path, version: str) -> Optional[Path]:
    iscc_path = shutil.which("iscc") or shutil.which("ISCC.exe")
    if not iscc_path:
        print("[!] Inno Setup Compiler(ISCC)를 찾을 수 없습니다. 설치 프로그램 생성을 건너뜁니다.")
        return None

    installer_output = DIST_DIR / "installer"
    installer_output.mkdir(parents=True, exist_ok=True)

    script_path = SPEC_DIR / "installer.iss"
    if not script_path.exists():
        raise SystemExit(f"Inno Setup 스크립트를 찾을 수 없습니다: {script_path}")

    cmd = [
        iscc_path,
        str(script_path),
        f"/DAppVersion={version}",
        f"/DSourceDir={portable_dir}",
        f"/DOutputDir={installer_output}",
    ]

    print("[4/4] Inno Setup으로 설치 프로그램을 생성합니다...")
    subprocess.run(cmd, check=True)

    installer_path = installer_output / "NewsCollector_Setup.exe"
    if installer_path.exists():
        print(f"설치 프로그램 생성 완료: {installer_path}")
        return installer_path

    print("[!] 설치 프로그램 파일을 찾을 수 없습니다. Inno Setup 로그를 확인하세요.")
    return None


def cleanup_pyinstaller_artifacts() -> None:
    if PYINSTALLER_WORK_DIR.exists():
        shutil.rmtree(PYINSTALLER_WORK_DIR)


def main() -> None:
    args = parse_args()

    exe_path = run_pyinstaller()
    portable_dir = create_portable_bundle(exe_path, args.version)
    create_zip_archive(portable_dir, args.version)

    if not args.skip_installer:
        build_installer(portable_dir, args.version)

    if not args.keep_build:
        cleanup_pyinstaller_artifacts()

    print("\n모든 작업이 완료되었습니다.")
    print(f"- 실행 파일: {exe_path}")
    print(f"- 휴대용 패키지: {PORTABLE_DIR}")
    print(f"- ZIP 압축본: {DIST_DIR / f'{APP_NAME}_Portable_v{args.version}.zip'}")
    if not args.skip_installer:
        print("- 설치 프로그램: dist/installer/NewsCollector_Setup.exe (ISCC가 설치된 경우)")


if __name__ == "__main__":
    main()

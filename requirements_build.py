"""
requirements.txt - 필요한 패키지 목록
"""
# requirements.txt
customtkinter==5.2.0
pandas==2.0.3
openpyxl==3.1.2
requests==2.31.0
beautifulsoup4==4.12.2
selenium==4.15.0
webdriver-manager==4.0.1
Pillow==10.0.0
lxml==4.9.3

"""
build.py - PyInstaller 빌드 스크립트
"""
import PyInstaller.__main__
import os
import shutil
from pathlib import Path

def build_exe():
    """실행 파일 빌드"""
    
    # 빌드 디렉토리 생성
    build_dir = Path("build")
    dist_dir = Path("dist")
    
    # 리소스 디렉토리 확인
    resources_dir = Path("resources")
    if not resources_dir.exists():
        resources_dir.mkdir()
        print("resources 디렉토리 생성됨")
    
    # 데이터 디렉토리 생성
    data_dir = Path("data")
    if not data_dir.exists():
        data_dir.mkdir()
        print("data 디렉토리 생성됨")
    
    # 아이콘 파일 생성 (없는 경우 기본 아이콘 사용)
    icon_path = Path("app.ico")
    
    # PyInstaller 실행
    PyInstaller.__main__.run([
        'main.py',
        '--name=NewsCollector',
        '--onefile',
        '--windowed',
        '--add-data=resources;resources',
        '--add-data=data;data',
        '--hidden-import=customtkinter',
        '--hidden-import=selenium',
        '--hidden-import=webdriver_manager',
        '--hidden-import=openpyxl',
        '--hidden-import=pandas',
        '--hidden-import=beautifulsoup4',
        '--hidden-import=PIL',
        '--hidden-import=tkinter',
        '--collect-all=customtkinter',
        '--noconfirm',
        '--clean'
    ])
    
    print("\n빌드 완료!")
    print(f"실행 파일 위치: {dist_dir / 'NewsCollector.exe'}")
    
    # 배포 패키지 생성
    create_distribution_package()

def create_distribution_package():
    """배포 패키지 생성"""
    dist_dir = Path("dist")
    package_dir = dist_dir / "NewsCollector_Package"
    
    # 패키지 디렉토리 생성
    if package_dir.exists():
        shutil.rmtree(package_dir)
    package_dir.mkdir(parents=True)
    
    # 실행 파일 복사
    exe_file = dist_dir / "NewsCollector.exe"
    if exe_file.exists():
        shutil.copy2(exe_file, package_dir)
    
    # 필요한 디렉토리 생성
    (package_dir / "data").mkdir()
    (package_dir / "results").mkdir()
    (package_dir / "logs").mkdir()
    (package_dir / "resources").mkdir()
    
    # 샘플 회원사 템플릿 생성
    import pandas as pd
    sample_data.to_excel(package_dir / "회원사_템플릿.xlsx", index=False)
    
    # README 파일 생성
    readme_content = """
회원사 뉴스 수집 프로그램 v1.0
================================

1. 프로그램 소개
----------------
회원사의 뉴스를 자동으로 수집하는 Windows용 프로그램입니다.
Google과 Naver에서 뉴스를 검색하여 Excel 파일로 저장합니다.

2. 사용 방법
------------
1) NewsCollector.exe 실행
2) [회원사 관리] 버튼 클릭 → 회원사_템플릿.xlsx 파일 참고하여 회원사 등록
3) [수집 실행] 또는 [지금 시작] 버튼 클릭하여 뉴스 수집 시작
4) 수집 완료 후 [결과 내보내기] 버튼으로 Excel 파일 저장

3. 폴더 구조
------------
- data/      : 회원사 데이터 저장
- results/   : 수집 결과 저장
- logs/      : 프로그램 로그 파일
- resources/ : 프로그램 리소스

4. 시스템 요구사항
-----------------
- Windows 7 이상
- 인터넷 연결 필요
- 최소 RAM: 4GB
- 저장 공간: 500MB 이상

5. 문제 해결
------------
- 프로그램이 실행되지 않는 경우: 
  관리자 권한으로 실행하거나 백신 프로그램 예외 처리

- 수집이 되지 않는 경우:
  인터넷 연결 확인, 방화벽 설정 확인

6. 주의사항
-----------
- 과도한 수집은 대상 사이트에 부담을 줄 수 있으므로 적절한 간격으로 실행
- 수집된 뉴스의 저작권은 원 출처에 있음
- 내부 업무용으로만 사용

문의: your-email@company.com
"""
    
    with open(package_dir / "README.txt", "w", encoding="utf-8") as f:
        f.write(readme_content)
    
    print(f"\n배포 패키지 생성 완료: {package_dir}")
    print("포함된 파일:")
    print("- NewsCollector.exe (실행 파일)")
    print("- 회원사_템플릿.xlsx (샘플 데이터)")
    print("- README.txt (사용 설명서)")
    print("- 필요 폴더들 (data, results, logs, resources)")

if __name__ == "__main__":
    print("회원사 뉴스 수집 프로그램 빌드 시작...")
    build_exe() = pd.DataFrame({
        '회원사명': ['삼성전자', 'LG전자', 'SK하이닉스', '현대자동차', 'POSCO'],
        '검색키워드': ['삼성전자', 'LG전자', 'SK하이닉스', '현대자동차', 'POSCO'],
        '활성화': ['Y', 'Y', 'Y', 'Y', 'Y'],
        '카테고리': ['전자', '전자', '반도체', '자동차', '철강'],
        '홈페이지': ['samsung.com', 'lge.co.kr', 'skhynix.com', 'hyundai.com', 'posco.co.kr']
    })
    sample_data
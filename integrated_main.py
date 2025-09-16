            self.destroy()

class MemberManagerDialog(ctk.CTkToplevel):
    """회원사 관리 다이얼로그"""
    def __init__(self, parent, member_manager):
        super().__init__(parent)
        self.member_manager = member_manager
        self.selected_item = None
        
        self.title("회원사 관리")
        self.geometry("900x600")
        self.transient(parent)
        self.grab_set()
        
        self.create_widgets()
        self.load_member_list()
    
    def create_widgets(self):
        """위젯 생성"""
        # 메인 컨테이너
        main_frame = ctk.CTkFrame(self)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # 상단 버튼 프레임
        button_frame = ctk.CTkFrame(main_frame)
        button_frame.pack(fill="x", pady=(0, 10))
        
        # 버튼들
        buttons = [
            ("📁 엑셀 불러오기", self.import_excel),
            ("📥 샘플 템플릿", self.download_sample),
            ("➕ 회원사 추가", self.add_member),
            ("✏️ 수정", self.edit_member),
            ("🗑️ 삭제", self.delete_member),
            ("💾 저장", self.save_members)
        ]
        
        for text, command in buttons:
            btn = ctk.CTkButton(
                button_frame,
                text=text,
                command=command,
                width=120,
                height=35
            )
            btn.pack(side="left", padx=5)
        
        # 회원사 목록 프레임
        list_frame = ctk.CTkFrame(main_frame)
        list_frame.pack(fill="both", expand=True)
        
        # Treeview 스타일 설정
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview", font=("맑은 고딕", 10))
        style.configure("Treeview.Heading", font=("맑은 고딕", 11, "bold"))
        
        # Treeview
        columns = ("회원사명", "검색키워드", "활성화", "카테고리", "홈페이지")
        self.tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=20)
        
        # 컬럼 설정
        column_widths = {"회원사명": 150, "검색키워드": 150, "활성화": 60, "카테고리": 100, "홈페이지": 200}
        for col in columns:
            self.tree.heading(col, text=col, command=lambda c=col: self.sort_treeview(c))
            self.tree.column(col, width=column_widths.get(col, 100))
        
        # 스크롤바
        v_scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.tree.yview)
        h_scrollbar = ttk.Scrollbar(list_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        # 배치
        self.tree.grid(row=0, column=0, sticky="nsew")
        v_scrollbar.grid(row=0, column=1, sticky="ns")
        h_scrollbar.grid(row=1, column=0, sticky="ew")
        
        list_frame.grid_rowconfigure(0, weight=1)
        list_frame.grid_columnconfigure(0, weight=1)
        
        # 더블클릭 이벤트 바인딩
        self.tree.bind("<Double-Button-1>", lambda e: self.edit_member())
        
        # 하단 정보 프레임
        info_frame = ctk.CTkFrame(main_frame)
        info_frame.pack(fill="x", pady=(10, 0))
        
        self.info_label = ctk.CTkLabel(
            info_frame,
            text=f"총 {self.member_manager.get_member_count()}개 회원사 "
                 f"(활성: {self.member_manager.get_active_count()}개)",
            font=("맑은 고딕", 11)
        )
        self.info_label.pack(side="left", padx=10)
        
        # 닫기 버튼
        close_btn = ctk.CTkButton(
            info_frame,
            text="닫기",
            command=self.destroy,
            width=100
        )
        close_btn.pack(side="right", padx=10)
    
    def load_member_list(self):
        """회원사 목록 로드"""
        # 기존 항목 삭제
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # 회원사 데이터 로드
        members = self.member_manager.get_all_members()
        for member in members:
            values = (
                member.get('회원사명', ''),
                member.get('검색키워드', ''),
                member.get('활성화', 'Y'),
                member.get('카테고리', ''),
                member.get('홈페이지', '')
            )
            
            # 비활성 회원사는 다른 태그로 표시
            tag = "inactive" if member.get('활성화') != 'Y' else ""
            self.tree.insert("", "end", values=values, tags=(tag,))
        
        # 비활성 회원사 스타일
        self.tree.tag_configure("inactive", foreground="gray")
        
        # 정보 업데이트
        self.update_info()
    
    def update_info(self):
        """정보 레이블 업데이트"""
        self.info_label.configure(
            text=f"총 {self.member_manager.get_member_count()}개 회원사 "
                 f"(활성: {self.member_manager.get_active_count()}개)"
        )
    
    def import_excel(self):
        """엑셀 파일 가져오기"""
        file_path = filedialog.askopenfilename(
            title="엑셀 파일 선택",
            filetypes=[("Excel files", "*.xlsx *.xls"), ("All files", "*.*")]
        )
        
        if file_path:
            success, message = self.member_manager.import_from_excel(file_path)
            if success:
                self.load_member_list()
                messagebox.showinfo("성공", message)
            else:
                messagebox.showerror("오류", message)
    
    def download_sample(self):
        """샘플 템플릿 다운로드"""
        file_path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx")],
            initialfile="회원사_템플릿.xlsx"
        )
        
        if file_path:
            # 샘플 데이터 생성
            sample_data = pd.DataFrame({
                '회원사명': ['삼성전자', 'LG전자', 'SK하이닉스', '현대자동차', 'POSCO'],
                '검색키워드': ['삼성전자', 'LG전자', 'SK하이닉스', '현대자동차', 'POSCO'],
                '활성화': ['Y', 'Y', 'Y', 'Y', 'Y'],
                '카테고리': ['전자', '전자', '반도체', '자동차', '철강'],
                '홈페이지': ['samsung.com', 'lge.co.kr', 'skhynix.com', 'hyundai.com', 'posco.co.kr']
            })
            
            try:
                with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
                    sample_data.to_excel(writer, index=False, sheet_name='회원사목록')
                    
                    # 컬럼 너비 조정
                    worksheet = writer.sheets['회원사목록']
                    for column in sample_data.columns:
                        column_width = max(
                            sample_data[column].astype(str).str.len().max(),
                            len(column)
                        ) + 2
                        col_idx = sample_data.columns.get_loc(column)
                        worksheet.column_dimensions[chr(65 + col_idx)].width = column_width
                
                messagebox.showinfo("완료", f"샘플 템플릿이 저장되었습니다.\n{file_path}")
            except Exception as e:
                messagebox.showerror("오류", f"파일 저장 실패: {e}")
    
    def add_member(self):
        """회원사 추가"""
        dialog = MemberEditDialog(self, None)
        self.wait_window(dialog)
        
        if dialog.result:
            if self.member_manager.add_member(dialog.result):
                self.load_member_list()
                messagebox.showinfo("성공", "회원사가 추가되었습니다.")
            else:
                messagebox.showerror("오류", "회원사 추가에 실패했습니다.")
    
    def edit_member(self):
        """선택된 회원사 수정"""
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("경고", "수정할 회원사를 선택해주세요.")
            return
        
        item = self.tree.item(selection[0])
        values = item['values']
        
        member_data = {
            '회원사명': values[0],
            '검색키워드': values[1],
            '활성화': values[2],
            '카테고리': values[3],
            '홈페이지': values[4]
        }
        
        dialog = MemberEditDialog(self, member_data)
        self.wait_window(dialog)
        
        if dialog.result:
            if self.member_manager.update_member(values[0], dialog.result):
                self.load_member_list()
                messagebox.showinfo("성공", "회원사 정보가 수정되었습니다.")
            else:
                messagebox.showerror("오류", "회원사 수정에 실패했습니다.")
    
    def delete_member(self):
        """선택된 회원사 삭제"""
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("경고", "삭제할 회원사를 선택해주세요.")
            return
        
        item = self.tree.item(selection[0])
        company_name = item['values'][0]
        
        result = messagebox.askyesno("확인", f"'{company_name}'을(를) 삭제하시겠습니까?")
        if result:
            if self.member_manager.remove_member(company_name):
                self.load_member_list()
                messagebox.showinfo("성공", "회원사가 삭제되었습니다.")
            else:
                messagebox.showerror("오류", "회원사 삭제에 실패했습니다.")
    
    def save_members(self):
        """회원사 데이터 저장"""
        if self.member_manager.save_members():
            messagebox.showinfo("성공", "회원사 데이터가 저장되었습니다.")
        else:
            messagebox.showerror("오류", "저장 중 오류가 발생했습니다.")
    
    def sort_treeview(self, col):
        """Treeview 정렬"""
        data = [(self.tree.set(item, col), item) for item in self.tree.get_children('')]
        data.sort()
        
        for index, (val, item) in enumerate(data):
            self.tree.move(item, '', index)

class MemberEditDialog(ctk.CTkToplevel):
    """회원사 편집 다이얼로그"""
    def __init__(self, parent, member_data=None):
        super().__init__(parent)
        self.result = None
        self.member_data = member_data or {}
        
        self.title("회원사 편집" if member_data else "회원사 추가")
        self.geometry("500x400")
        self.transient(parent)
        self.grab_set()
        
        self.create_widgets()
    
    def create_widgets(self):
        """위젯 생성"""
        main_frame = ctk.CTkFrame(self)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # 입력 필드들
        fields = [
            ("회원사명", "회원사 이름을 입력하세요"),
            ("검색키워드", "검색에 사용할 키워드 (비워두면 회원사명 사용)"),
            ("카테고리", "회원사 분류 (예: 전자, IT, 제조 등)"),
            ("홈페이지", "회사 홈페이지 URL")
        ]
        
        self.entries = {}
        for field, placeholder in fields:
            label = ctk.CTkLabel(main_frame, text=field + ":", font=("맑은 고딕", 12))
            label.pack(anchor="w", pady=(10, 0))
            
            entry = ctk.CTkEntry(main_frame, placeholder_text=placeholder, height=35)
            entry.pack(fill="x", pady=5)
            
            # 기존 값이 있으면 설정
            if self.member_data.get(field):
                entry.insert(0, self.member_data.get(field))
            
            self.entries[field] = entry
        
        # 활성화 체크박스
        self.active_var = tk.StringVar(value=self.member_data.get('활성화', 'Y'))
        checkbox = ctk.CTkCheckBox(
            main_frame,
            text="활성화 (뉴스 수집 대상)",
            variable=self.active_var,
            onvalue='Y',
            offvalue='N'
        )
        checkbox.pack(anchor="w", pady=20)
        
        # 버튼 프레임
        button_frame = ctk.CTkFrame(main_frame)
        button_frame.pack(fill="x", pady=(20, 0))
        
        save_btn = ctk.CTkButton(
            button_frame,
            text="저장",
            command=self.save,
            width=100,
            fg_color="green"
        )
        save_btn.pack(side="right", padx=5)
        
        cancel_btn = ctk.CTkButton(
            button_frame,
            text="취소",
            command=self.destroy,
            width=100
        )
        cancel_btn.pack(side="right")
    
    def save(self):
        """데이터 저장"""
        # 필수 필드 확인
        company_name = self.entries['회원사명'].get().strip()
        if not company_name:
            messagebox.showwarning("경고", "회원사명은 필수 입력 항목입니다.")
            return
        
        # 결과 데이터 구성
        self.result = {
            '회원사명': company_name,
            '검색키워드': self.entries['검색키워드'].get().strip() or company_name,
            '활성화': self.active_var.get(),
            '카테고리': self.entries['카테고리'].get().strip(),
            '홈페이지': self.entries['홈페이지'].get().strip()
        }
        
        self.destroy()

class SettingsDialog(ctk.CTkToplevel):
    """설정 다이얼로그"""
    def __init__(self, parent, config):
        super().__init__(parent)
        self.config = config
        
        self.title("설정")
        self.geometry("600x500")
        self.transient(parent)
        self.grab_set()
        
        self.create_widgets()
    
    def create_widgets(self):
        """위젯 생성"""
        # 탭뷰 생성
        tabview = ctk.CTkTabview(self)
        tabview.pack(fill="both", expand=True, padx=10, pady=10)
        
        # 탭 추가
        tabview.add("크롤링 설정")
        tabview.add("플랫폼 설정")
        tabview.add("저장 설정")
        
        # 크롤링 설정 탭
        self.create_crawling_settings(tabview.tab("크롤링 설정"))
        
        # 플랫폼 설정 탭
        self.create_platform_settings(tabview.tab("플랫폼 설정"))
        
        # 저장 설정 탭
        self.create_save_settings(tabview.tab("저장 설정"))
        
        # 하단 버튼
        button_frame = ctk.CTkFrame(self)
        button_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        save_btn = ctk.CTkButton(
            button_frame,
            text="저장",
            command=self.save_settings,
            width=100,
            fg_color="green"
        )
        save_btn.pack(side="right", padx=5)
        
        cancel_btn = ctk.CTkButton(
            button_frame,
            text="취소",
            command=self.destroy,
            width=100
        )
        cancel_btn.pack(side="right")
        
        reset_btn = ctk.CTkButton(
            button_frame,
            text="기본값 복원",
            command=self.reset_settings,
            width=100,
            fg_color="orange"
        )
        reset_btn.pack(side="left")
    
    def create_crawling_settings(self, parent):
        """크롤링 설정 탭"""
        # 요청 간격
        interval_frame = ctk.CTkFrame(parent)
        interval_frame.pack(fill="x", pady=10)
        
        ctk.CTkLabel(
            interval_frame,
            text="요청 간격 (초):",
            font=("맑은 고딕", 12)
        ).pack(anchor="w")
        
        self.interval_var = tk.IntVar(value=self.config.get("crawl_interval", 2))
        interval_slider = ctk.CTkSlider(
            interval_frame,
            from_=1,
            to=10,
            variable=self.interval_var,
            number_of_steps=9
        )
        interval_slider.pack(fill="x", pady=5)
        
        self.interval_label = ctk.CTkLabel(
            interval_frame,
            text=f"{self.interval_var.get()}초"
        )
        self.interval_label.pack(anchor="w")
        interval_slider.configure(command=lambda v: self.interval_label.configure(text=f"{int(float(v))}초"))
        
        # 재시도 횟수
        retry_frame = ctk.CTkFrame(parent)
        retry_frame.pack(fill="x", pady=10)
        
        ctk.CTkLabel(
            retry_frame,
            text="최대 재시도 횟수:",
            font=("맑은 고딕", 12)
        ).pack(anchor="w")
        
        self.retry_var = tk.IntVar(value=self.config.get("max_retries", 3))
        retry_slider = ctk.CTkSlider(
            retry_frame,
            from_=1,
            to=5,
            variable=self.retry_var,
            number_of_steps=4
        )
        retry_slider.pack(fill="x", pady=5)
        
        # 타임아웃
        timeout_frame = ctk.CTkFrame(parent)
        timeout_frame.pack(fill="x", pady=10)
        
        ctk.CTkLabel(
            timeout_frame,
            text="타임아웃 (초):",
            font=("맑은 고딕", 12)
        ).pack(anchor="w")
        
        self.timeout_var = tk.IntVar(value=self.config.get("timeout", 30))
        timeout_slider = ctk.CTkSlider(
            timeout_frame,
            from_=10,
            to=60,
            variable=self.timeout_var,
            number_of_steps=5
        )
        timeout_slider.pack(fill="x", pady=5)
        
        # 기사 수 제한
        articles_frame = ctk.CTkFrame(parent)
        articles_frame.pack(fill="x", pady=10)
        
        ctk.CTkLabel(
            articles_frame,
            text="회원사별 최대 기사 수:",
            font=("맑은 고딕", 12)
        ).pack(anchor="w")
        
        self.articles_var = tk.IntVar(value=self.config.get("max_articles_per_company", 20))
        articles_slider = ctk.CTkSlider(
            articles_frame,
            from_=10,
            to=50,
            variable=self.articles_var,
            number_of_steps=8
        )
        articles_slider.pack(fill="x", pady=5)
        
        self.articles_label = ctk.CTkLabel(
            articles_frame,
            text=f"{self.articles_var.get()}개"
        )
        self.articles_label.pack(anchor="w")
        articles_slider.configure(command=lambda v: self.articles_label.configure(text=f"{int(float(v))}개"))
    
    def create_platform_settings(self, parent):
        """플랫폼 설정 탭"""
        ctk.CTkLabel(
            parent,
            text="수집할 플랫폼 선택:",
            font=("맑은 고딕", 14, "bold")
        ).pack(anchor="w", pady=10)
        
        platforms = self.config.get("platforms", ["google", "naver"])
        self.platform_vars = {}
        
        platform_info = {
            "google": ("Google 뉴스", "구글에서 뉴스를 검색합니다"),
            "naver": ("Naver 뉴스", "네이버에서 뉴스를 검색합니다"),
            "daum": ("Daum 뉴스", "다음에서 뉴스를 검색합니다 (준비중)")
        }
        
        for platform, (name, description) in platform_info.items():
            frame = ctk.CTkFrame(parent)
            frame.pack(fill="x", pady=5)
            
            var = tk.BooleanVar(value=platform in platforms)
            self.platform_vars[platform] = var
            
            checkbox = ctk.CTkCheckBox(
                frame,
                text=name,
                variable=var,
                font=("맑은 고딕", 12, "bold")
            )
            checkbox.pack(anchor="w", padx=10)
            
            desc_label = ctk.CTkLabel(
                frame,
                text=description,
                font=("맑은 고딕", 10),
                text_color="gray"
            )
            desc_label.pack(anchor="w", padx=35)
            
            # Daum은 비활성화 (준비중)
            if platform == "daum":
                checkbox.configure(state="disabled")
        
        # 내용 수집 옵션
        content_frame = ctk.CTkFrame(parent)
        content_frame.pack(fill="x", pady=20)
        
        ctk.CTkLabel(
            content_frame,
            text="추가 옵션:",
            font=("맑은 고딕", 14, "bold")
        ).pack(anchor="w", pady=5)
        
        self.content_var = tk.BooleanVar(value=self.config.get("enable_content_crawling", False))
        content_checkbox = ctk.CTkCheckBox(
            content_frame,
            text="기사 본문 내용 수집 (속도가 느려질 수 있음)",
            variable=self.content_var
        )
        content_checkbox.pack(anchor="w", padx=10)
    
    def create_save_settings(self, parent):
        """저장 설정 탭"""
        # 자동 저장
        auto_save_frame = ctk.CTkFrame(parent)
        auto_save_frame.pack(fill="x", pady=10)
        
        self.auto_save_var = tk.BooleanVar(value=self.config.get("auto_save", True))
        auto_save_checkbox = ctk.CTkCheckBox(
            auto_save_frame,
            text="수집 완료 후 자동 저장",
            variable=self.auto_save_var,
            font=("맑은 고딕", 12)
        )
        auto_save_checkbox.pack(anchor="w")
        
        # 파일 형식
        format_frame = ctk.CTkFrame(parent)
        format_frame.pack(fill="x", pady=10)
        
        ctk.CTkLabel(
            format_frame,
            text="기본 저장 형식:",
            font=("맑은 고딕", 12)
        ).pack(anchor="w")
        
        self.format_var = tk.StringVar(value=self.config.get("export_format", "xlsx"))
        
        formats = [
            ("Excel (.xlsx)", "xlsx"),
            ("CSV (.csv)", "csv")
        ]
        
        for text, value in formats:
            radio = ctk.CTkRadioButton(
                format_frame,
                text=text,
                variable=self.format_var,
                value=value
            )
            radio.pack(anchor="w", padx=20, pady=2)
        
        # 저장 경로
        path_frame = ctk.CTkFrame(parent)
        path_frame.pack(fill="x", pady=10)
        
        ctk.CTkLabel(
            path_frame,
            text="저장 경로:",
            font=("맑은 고딕", 12)
        ).pack(anchor="w")
        
        self.path_label = ctk.CTkLabel(
            path_frame,
            text=str(RESULTS_DIR.absolute()),
            font=("맑은 고딕", 10),
            text_color="blue"
        )
        self.path_label.pack(anchor="w", padx=20, pady=5)
        
        change_path_btn = ctk.CTkButton(
            path_frame,
            text="경로 변경",
            command=self.change_save_path,
            width=100,
            height=30
        )
        change_path_btn.pack(anchor="w", padx=20)
    
    def change_save_path(self):
        """저장 경로 변경"""
        path = filedialog.askdirectory(title="저장 경로 선택")
        if path:
            global RESULTS_DIR
            RESULTS_DIR = Path(path)
            self.path_label.configure(text=str(RESULTS_DIR.absolute()))
    
    def save_settings(self):
        """설정 저장"""
        # 크롤링 설정
        self.config.set("crawl_interval", self.interval_var.get())
        self.config.set("max_retries", self.retry_var.get())
        self.config.set("timeout", self.timeout_var.get())
        self.config.set("max_articles_per_company", self.articles_var.get())
        
        # 플랫폼 설정
        platforms = [platform for platform, var in self.platform_vars.items() if var.get()]
        if not platforms:
            messagebox.showwarning("경고", "최소 하나의 플랫폼을 선택해야 합니다.")
            return
        self.config.set("platforms", platforms)
        self.config.set("enable_content_crawling", self.content_var.get())
        
        # 저장 설정
        self.config.set("auto_save", self.auto_save_var.get())
        self.config.set("export_format", self.format_var.get())
        
        messagebox.showinfo("성공", "설정이 저장되었습니다.")
        self.destroy()
    
    def reset_settings(self):
        """설정 초기화"""
        result = messagebox.askyesno("확인", "모든 설정을 기본값으로 복원하시겠습니까?")
        if result:
            # 기본값으로 리셋
            self.interval_var.set(2)
            self.retry_var.set(3)
            self.timeout_var.set(30)
            self.articles_var.set(20)
            
            # 플랫폼 기본값
            self.platform_vars["google"].set(True)
            self.platform_vars["naver"].set(True)
            self.platform_vars.get("daum", tk.BooleanVar()).set(False)
            
            self.content_var.set(False)
            self.auto_save_var.set(True)
            self.format_var.set("xlsx")
            
            # UI 업데이트
            self.interval_label.configure(text="2초")
            self.articles_label.configure(text="20개")


def main():
    """메인 함수"""
    try:
        app = MainWindow()
        app.mainloop()
    except Exception as e:
        logger.error(f"프로그램 실행 오류: {e}")
        import traceback
        logger.error(traceback.format_exc())
        messagebox.showerror("오류", f"프로그램 실행 중 오류가 발생했습니다.\n{e}")


if __name__ == "__main__":
    main()"""
회원사 뉴스 수집 프로그램 v1.0 - 통합 버전
Integrated Main Application with Crawler Engine
"""

import os
import sys
import json
import threading
import logging
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import customtkinter as ctk
import pandas as pd
from typing import Dict, List, Optional
import queue

# 크롤러 엔진 임포트 (실제 구현시 crawler_engine.py에서 임포트)
# from crawler_engine import NewsCrawlerEngine

# 한국어 인코딩 설정
if sys.platform == 'win32':
    import locale
    try:
        locale.setlocale(locale.LC_ALL, 'korean')
    except:
        locale.setlocale(locale.LC_ALL, '')

# CustomTkinter 설정
ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

# 로깅 설정
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

def setup_logging():
    """로깅 설정"""
    log_file = LOG_DIR / f'crawler_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
    
    # 로거 설정
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    # 파일 핸들러
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    
    # 콘솔 핸들러
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # 포맷터
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # 핸들러 추가
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

logger = setup_logging()

# 설정 및 데이터 파일 경로
CONFIG_FILE = Path("config.json")
MEMBER_DATA_FILE = Path("data/members.xlsx")
RESULTS_DIR = Path("results")

# 디렉토리 생성
for dir_path in [Path("data"), RESULTS_DIR, LOG_DIR, Path("resources")]:
    dir_path.mkdir(exist_ok=True)

class ThreadSafeLogger:
    """스레드 안전 로거"""
    def __init__(self, text_widget, queue_obj):
        self.text_widget = text_widget
        self.queue = queue_obj
    
    def log(self, message, level="INFO"):
        """로그 메시지 큐에 추가"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.queue.put((timestamp, level, message))

class Config:
    """애플리케이션 설정 관리"""
    def __init__(self):
        self.settings = {
            "last_run": None,
            "auto_save": True,
            "crawl_interval": 2,
            "max_retries": 3,
            "timeout": 30,
            "platforms": ["google", "naver"],
            "export_format": "xlsx",
            "max_articles_per_company": 20,
            "enable_content_crawling": False
        }
        self.load()
    
    def load(self):
        """설정 파일 로드"""
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    loaded_settings = json.load(f)
                    self.settings.update(loaded_settings)
                    logger.info("설정 파일 로드 완료")
            except Exception as e:
                logger.error(f"설정 파일 로드 실패: {e}")
    
    def save(self):
        """설정 파일 저장"""
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, ensure_ascii=False, indent=2)
                logger.info("설정 파일 저장 완료")
        except Exception as e:
            logger.error(f"설정 파일 저장 실패: {e}")
    
    def get(self, key, default=None):
        return self.settings.get(key, default)
    
    def set(self, key, value):
        self.settings[key] = value
        self.save()

class MemberManager:
    """회원사 데이터 관리"""
    def __init__(self):
        self.members_df = None
        self.load_members()
    
    def load_members(self):
        """회원사 데이터 로드"""
        if MEMBER_DATA_FILE.exists():
            try:
                self.members_df = pd.read_excel(MEMBER_DATA_FILE)
                # 필수 컬럼 확인 및 기본값 설정
                self.validate_dataframe()
                logger.info(f"회원사 데이터 로드 완료: {len(self.members_df)}개 회사")
            except Exception as e:
                logger.error(f"회원사 데이터 로드 실패: {e}")
                self.create_empty_dataframe()
        else:
            self.create_empty_dataframe()
    
    def validate_dataframe(self):
        """데이터프레임 검증 및 기본값 설정"""
        required_columns = ['회원사명', '검색키워드', '활성화', '카테고리', '홈페이지']
        
        for col in required_columns:
            if col not in self.members_df.columns:
                if col == '활성화':
                    self.members_df[col] = 'Y'
                else:
                    self.members_df[col] = ''
        
        # 기본값 설정
        self.members_df['활성화'] = self.members_df['활성화'].fillna('Y')
        self.members_df['카테고리'] = self.members_df['카테고리'].fillna('일반')
        self.members_df['홈페이지'] = self.members_df['홈페이지'].fillna('')
        self.members_df['검색키워드'] = self.members_df.apply(
            lambda row: row['검색키워드'] if pd.notna(row['검색키워드']) and row['검색키워드'] 
            else row['회원사명'], axis=1
        )
    
    def create_empty_dataframe(self):
        """빈 데이터프레임 생성"""
        self.members_df = pd.DataFrame(columns=[
            '회원사명', '검색키워드', '활성화', '카테고리', '홈페이지'
        ])
    
    def save_members(self):
        """회원사 데이터 저장"""
        try:
            # 데이터 디렉토리 확인
            MEMBER_DATA_FILE.parent.mkdir(exist_ok=True)
            
            # Excel 저장
            with pd.ExcelWriter(MEMBER_DATA_FILE, engine='openpyxl') as writer:
                self.members_df.to_excel(writer, index=False, sheet_name='회원사목록')
                
                # 컬럼 너비 자동 조정
                worksheet = writer.sheets['회원사목록']
                for column in self.members_df.columns:
                    column_width = max(
                        self.members_df[column].astype(str).str.len().max(),
                        len(column)
                    ) + 2
                    col_idx = self.members_df.columns.get_loc(column)
                    worksheet.column_dimensions[chr(65 + col_idx)].width = min(column_width, 50)
            
            logger.info("회원사 데이터 저장 완료")
            return True
        except Exception as e:
            logger.error(f"회원사 데이터 저장 실패: {e}")
            return False
    
    def import_from_excel(self, file_path):
        """엑셀 파일에서 회원사 데이터 가져오기"""
        try:
            df = pd.read_excel(file_path)
            
            # 필수 컬럼 확인
            required_columns = ['회원사명']
            missing_cols = [col for col in required_columns if col not in df.columns]
            if missing_cols:
                raise ValueError(f"필수 컬럼 누락: {', '.join(missing_cols)}")
            
            # 중복 제거
            df = df.drop_duplicates(subset=['회원사명'])
            
            # 빈 회원사명 제거
            df = df[df['회원사명'].notna() & (df['회원사명'] != '')]
            
            self.members_df = df
            self.validate_dataframe()
            self.save_members()
            
            return True, f"{len(df)}개 회원사를 성공적으로 불러왔습니다."
        except Exception as e:
            logger.error(f"엑셀 파일 가져오기 실패: {e}")
            return False, f"파일 불러오기 실패: {str(e)}"
    
    def add_member(self, member_data: Dict) -> bool:
        """회원사 추가"""
        try:
            new_member = pd.DataFrame([member_data])
            self.members_df = pd.concat([self.members_df, new_member], ignore_index=True)
            self.save_members()
            return True
        except Exception as e:
            logger.error(f"회원사 추가 실패: {e}")
            return False
    
    def remove_member(self, company_name: str) -> bool:
        """회원사 삭제"""
        try:
            self.members_df = self.members_df[self.members_df['회원사명'] != company_name]
            self.save_members()
            return True
        except Exception as e:
            logger.error(f"회원사 삭제 실패: {e}")
            return False
    
    def update_member(self, company_name: str, member_data: Dict) -> bool:
        """회원사 정보 업데이트"""
        try:
            idx = self.members_df[self.members_df['회원사명'] == company_name].index
            if len(idx) > 0:
                for key, value in member_data.items():
                    self.members_df.loc[idx[0], key] = value
                self.save_members()
                return True
            return False
        except Exception as e:
            logger.error(f"회원사 업데이트 실패: {e}")
            return False
    
    def get_active_members(self) -> List[Dict]:
        """활성화된 회원사 목록 반환"""
        if self.members_df is not None and not self.members_df.empty:
            active_df = self.members_df[self.members_df['활성화'] == 'Y']
            return active_df.to_dict('records')
        return []
    
    def get_all_members(self) -> List[Dict]:
        """전체 회원사 목록 반환"""
        if self.members_df is not None and not self.members_df.empty:
            return self.members_df.to_dict('records')
        return []
    
    def get_member_count(self) -> int:
        """전체 회원사 수 반환"""
        if self.members_df is not None:
            return len(self.members_df)
        return 0
    
    def get_active_count(self) -> int:
        """활성화된 회원사 수 반환"""
        if self.members_df is not None and not self.members_df.empty:
            return len(self.members_df[self.members_df['활성화'] == 'Y'])
        return 0

class MainWindow(ctk.CTk):
    """메인 윈도우 클래스"""
    def __init__(self):
        super().__init__()
        
        self.config = Config()
        self.member_manager = MemberManager()
        self.crawler_engine = None
        self.is_crawling = False
        self.crawl_thread = None
        self.log_queue = queue.Queue()
        self.collected_data = None
        
        self.setup_window()
        self.create_widgets()
        self.update_status()
        self.process_log_queue()
        
        logger.info("=" * 60)
        logger.info("회원사 뉴스 수집 프로그램 시작")
        logger.info("=" * 60)
    
    def setup_window(self):
        """윈도우 설정"""
        self.title("회원사 뉴스 수집 프로그램 v1.0")
        self.geometry("1000x750")
        self.minsize(900, 650)
        
        # 아이콘 설정 (있는 경우)
        try:
            icon_path = Path("app.ico")
            if icon_path.exists():
                self.iconbitmap(icon_path)
        except:
            pass
        
        # 중앙 배치
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f'{width}x{height}+{x}+{y}')
        
        # 종료 이벤트 핸들러
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def create_widgets(self):
        """위젯 생성"""
        # 메인 컨테이너
        main_container = ctk.CTkFrame(self)
        main_container.pack(fill="both", expand=True, padx=10, pady=10)
        
        # 상단 타이틀
        title_frame = ctk.CTkFrame(main_container)
        title_frame.pack(fill="x", pady=(0, 10))
        
        title_label = ctk.CTkLabel(
            title_frame,
            text="📰 회원사 뉴스 수집 프로그램",
            font=("맑은 고딕", 20, "bold")
        )
        title_label.pack(pady=10)
        
        # 상단 버튼 바
        self.create_button_bar(main_container)
        
        # 메인 컨텐츠 영역 (좌우 분할)
        content_frame = ctk.CTkFrame(main_container)
        content_frame.pack(fill="both", expand=True)
        
        # 왼쪽 패널 (현황 및 실행)
        left_panel = ctk.CTkFrame(content_frame)
        left_panel.pack(side="left", fill="both", expand=True, padx=(0, 5))
        
        # 현황 섹션
        self.create_status_section(left_panel)
        
        # 실행 섹션
        self.create_action_section(left_panel)
        
        # 오른쪽 패널 (로그)
        right_panel = ctk.CTkFrame(content_frame)
        right_panel.pack(side="right", fill="both", expand=True, padx=(5, 0))
        
        # 로그 섹션
        self.create_log_section(right_panel)
    
    def create_button_bar(self, parent):
        """상단 버튼 바 생성"""
        button_frame = ctk.CTkFrame(parent)
        button_frame.pack(fill="x", pady=(0, 10))
        
        buttons = [
            ("📋 회원사 관리", self.open_member_manager, None),
            ("▶️ 수집 실행", self.start_crawling, "green"),
            ("📊 결과 보기", self.view_results, None),
            ("⚙️ 설정", self.open_settings, None),
            ("❓ 도움말", self.show_help, None)
        ]
        
        for text, command, color in buttons:
            btn = ctk.CTkButton(
                button_frame, 
                text=text, 
                command=command,
                width=150,
                height=40,
                font=("맑은 고딕", 12, "bold"),
                fg_color=color if color else None
            )
            btn.pack(side="left", padx=5)
    
    def create_status_section(self, parent):
        """현황 섹션 생성"""
        status_frame = ctk.CTkFrame(parent)
        status_frame.pack(fill="x", pady=(0, 10))
        
        # 제목
        title_label = ctk.CTkLabel(
            status_frame,
            text="📊 현재 상태",
            font=("맑은 고딕", 14, "bold")
        )
        title_label.pack(anchor="w", padx=10, pady=5)
        
        # 상태 정보 그리드
        info_frame = ctk.CTkFrame(status_frame)
        info_frame.pack(fill="x", padx=10, pady=5)
        
        self.status_labels = {}
        status_items = [
            ("registered", "등록 회원사", f"{self.member_manager.get_member_count()}개"),
            ("active", "활성 회원사", f"{self.member_manager.get_active_count()}개"),
            ("last_run", "마지막 실행", self.config.get('last_run', '없음')),
            ("collected", "수집된 기사", "0건")
        ]
        
        for i, (key, label, value) in enumerate(status_items):
            # 라벨
            label_widget = ctk.CTkLabel(
                info_frame,
                text=f"{label}:",
                font=("맑은 고딕", 11),
                anchor="w"
            )
            label_widget.grid(row=i//2, column=(i%2)*2, sticky="w", padx=10, pady=3)
            
            # 값
            value_widget = ctk.CTkLabel(
                info_frame,
                text=value,
                font=("맑은 고딕", 11, "bold"),
                text_color="blue"
            )
            value_widget.grid(row=i//2, column=(i%2)*2+1, sticky="w", padx=5, pady=3)
            self.status_labels[key] = value_widget
    
    def create_action_section(self, parent):
        """실행 섹션 생성"""
        action_frame = ctk.CTkFrame(parent)
        action_frame.pack(fill="x", pady=(0, 10))
        
        # 제목
        title_label = ctk.CTkLabel(
            action_frame,
            text="🚀 실행 제어",
            font=("맑은 고딕", 14, "bold")
        )
        title_label.pack(anchor="w", padx=10, pady=5)
        
        # 버튼 프레임
        button_frame = ctk.CTkFrame(action_frame)
        button_frame.pack(fill="x", padx=10, pady=5)
        
        # 실행 버튼
        self.start_button = ctk.CTkButton(
            button_frame,
            text="✅ 지금 시작",
            command=self.start_crawling,
            width=130,
            height=40,
            font=("맑은 고딕", 12, "bold"),
            fg_color="green"
        )
        self.start_button.pack(side="left", padx=5)
        
        # 중지 버튼
        self.stop_button = ctk.CTkButton(
            button_frame,
            text="⏹️ 중지",
            command=self.stop_crawling,
            width=130,
            height=40,
            font=("맑은 고딕", 12, "bold"),
            fg_color="red",
            state="disabled"
        )
        self.stop_button.pack(side="left", padx=5)
        
        # 결과 내보내기 버튼
        self.export_button = ctk.CTkButton(
            button_frame,
            text="💾 결과 저장",
            command=self.export_results,
            width=130,
            height=40,
            font=("맑은 고딕", 12, "bold"),
            state="disabled"
        )
        self.export_button.pack(side="left", padx=5)
        
        # 진행률 프레임
        progress_frame = ctk.CTkFrame(action_frame)
        progress_frame.pack(fill="x", padx=10, pady=10)
        
        # 진행률 레이블
        self.progress_label = ctk.CTkLabel(
            progress_frame,
            text="대기 중...",
            font=("맑은 고딕", 11)
        )
        self.progress_label.pack(anchor="w")
        
        # 진행률 바
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ctk.CTkProgressBar(
            progress_frame,
            variable=self.progress_var,
            height=25
        )
        self.progress_bar.pack(fill="x", pady=5)
        self.progress_bar.set(0)
        
        # 세부 진행 상태
        self.detail_label = ctk.CTkLabel(
            progress_frame,
            text="",
            font=("맑은 고딕", 10),
            text_color="gray"
        )
        self.detail_label.pack(anchor="w")
    
    def create_log_section(self, parent):
        """로그 섹션 생성"""
        log_frame = ctk.CTkFrame(parent)
        log_frame.pack(fill="both", expand=True)
        
        # 제목과 버튼을 포함한 헤더
        header_frame = ctk.CTkFrame(log_frame)
        header_frame.pack(fill="x", padx=10, pady=5)
        
        title_label = ctk.CTkLabel(
            header_frame,
            text="📝 실행 로그",
            font=("맑은 고딕", 14, "bold")
        )
        title_label.pack(side="left")
        
        # 로그 제어 버튼
        clear_button = ctk.CTkButton(
            header_frame,
            text="지우기",
            command=self.clear_log,
            width=70,
            height=25
        )
        clear_button.pack(side="right", padx=5)
        
        save_log_button = ctk.CTkButton(
            header_frame,
            text="로그 저장",
            command=self.save_log,
            width=70,
            height=25
        )
        save_log_button.pack(side="right")
        
        # 로그 텍스트 위젯
        self.log_text = ctk.CTkTextbox(
            log_frame,
            height=300,
            font=("Consolas", 9),
            wrap="word"
        )
        self.log_text.pack(fill="both", expand=True, padx=10, pady=5)
        
        # 초기 메시지
        self.log_message("프로그램이 시작되었습니다.", "INFO")
        self.log_message(f"작업 디렉토리: {Path.cwd()}", "INFO")
    
    def update_status(self):
        """상태 정보 업데이트"""
        try:
            self.status_labels["registered"].configure(
                text=f"{self.member_manager.get_member_count()}개"
            )
            self.status_labels["active"].configure(
                text=f"{self.member_manager.get_active_count()}개"
            )
            last_run = self.config.get('last_run', '없음')
            self.status_labels["last_run"].configure(text=last_run)
            
            # 수집된 기사 수 업데이트
            if self.collected_data is not None and not self.collected_data.empty:
                self.status_labels["collected"].configure(
                    text=f"{len(self.collected_data)}건"
                )
        except Exception as e:
            logger.error(f"상태 업데이트 오류: {e}")
    
    def log_message(self, message, level="INFO"):
        """로그 메시지 추가"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # 레벨별 이모지
        level_emoji = {
            "INFO": "ℹ️",
            "SUCCESS": "✅",
            "WARNING": "⚠️",
            "ERROR": "❌"
        }
        emoji = level_emoji.get(level, "📌")
        
        log_entry = f"[{timestamp}] {emoji} {message}\n"
        
        # 텍스트 위젯에 추가
        self.log_text.insert("end", log_entry)
        self.log_text.see("end")
        
        # 파일 로깅
        if level == "ERROR":
            logger.error(message)
        elif level == "WARNING":
            logger.warning(message)
        else:
            logger.info(message)
    
    def process_log_queue(self):
        """로그 큐 처리 (스레드 안전)"""
        try:
            while not self.log_queue.empty():
                timestamp, level, message = self.log_queue.get_nowait()
                log_entry = f"[{timestamp}] {message}\n"
                self.log_text.insert("end", log_entry)
                self.log_text.see("end")
        except:
            pass
        finally:
            self.after(100, self.process_log_queue)
    
    def clear_log(self):
        """로그 텍스트 클리어"""
        self.log_text.delete("1.0", "end")
        self.log_message("로그를 지웠습니다.", "INFO")
    
    def save_log(self):
        """로그 파일로 저장"""
        try:
            file_path = filedialog.asksaveasfilename(
                defaultextension=".txt",
                filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
                initialfile=f"log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            )
            if file_path:
                log_content = self.log_text.get("1.0", "end-1c")
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(log_content)
                self.log_message(f"로그 저장 완료: {file_path}", "SUCCESS")
        except Exception as e:
            self.log_message(f"로그 저장 실패: {e}", "ERROR")
    
    def show_help(self):
        """도움말 표시"""
        help_window = ctk.CTkToplevel(self)
        help_window.title("도움말")
        help_window.geometry("600x500")
        help_window.transient(self)
        
        help_text = """
        회원사 뉴스 수집 프로그램 사용법
        ================================
        
        1. 회원사 관리
        - [회원사 관리] 버튼을 클릭하여 회원사를 등록합니다.
        - Excel 파일을 불러오거나 직접 입력할 수 있습니다.
        - 샘플 템플릿을 다운로드하여 참고하세요.
        
        2. 뉴스 수집 실행
        - [수집 실행] 또는 [지금 시작] 버튼을 클릭합니다.
        - 활성화된 회원사의 뉴스를 자동으로 수집합니다.
        - 진행 상황은 실시간으로 확인할 수 있습니다.
        
        3. 결과 확인 및 저장
        - 수집이 완료되면 [결과 저장] 버튼이 활성화됩니다.
        - Excel 또는 CSV 형식으로 저장할 수 있습니다.
        - [결과 보기] 버튼으로 저장된 파일을 확인할 수 있습니다.
        
        4. 설정
        - 크롤링 간격, 재시도 횟수 등을 설정할 수 있습니다.
        - 수집할 플랫폼(Google, Naver)을 선택할 수 있습니다.
        
        주의사항:
        - 과도한 수집은 피해주세요.
        - 수집된 뉴스의 저작권은 원 출처에 있습니다.
        - 내부 업무용으로만 사용하세요.
        """
        
        text_widget = ctk.CTkTextbox(help_window, font=("맑은 고딕", 11))
        text_widget.pack(fill="both", expand=True, padx=10, pady=10)
        text_widget.insert("1.0", help_text)
        text_widget.configure(state="disabled")
        
        close_btn = ctk.CTkButton(
            help_window,
            text="닫기",
            command=help_window.destroy,
            width=100
        )
        close_btn.pack(pady=10)
    
    def open_member_manager(self):
        """회원사 관리 창 열기"""
        dialog = MemberManagerDialog(self, self.member_manager)
        self.wait_window(dialog)
        self.update_status()
    
    def start_crawling(self):
        """크롤링 시작"""
        if self.is_crawling:
            messagebox.showwarning("경고", "이미 수집이 진행 중입니다.")
            return
        
        active_members = self.member_manager.get_active_members()
        if not active_members:
            messagebox.showwarning("경고", "활성화된 회원사가 없습니다.\n회원사 관리에서 회원사를 추가해주세요.")
            return
        
        # 확인 대화상자
        result = messagebox.askyesno(
            "수집 시작",
            f"{len(active_members)}개 회원사의 뉴스를 수집하시겠습니까?\n"
            f"예상 소요 시간: 약 {len(active_members) * 3}초"
        )
        
        if not result:
            return
        
        self.is_crawling = True
        self.collected_data = None
        self.start_button.configure(state="disabled")
        self.stop_button.configure(state="normal")
        self.export_button.configure(state="disabled")
        
        self.log_message(f"뉴스 수집 시작 - {len(active_members)}개 회원사", "INFO")
        self.progress_label.configure(text="수집 준비 중...")
        
        # 크롤링 스레드 시작
        self.crawl_thread = threading.Thread(
            target=self.crawl_worker,
            args=(active_members,),
            daemon=True
        )
        self.crawl_thread.start()
    
    def crawl_worker(self, members):
        """크롤링 작업 스레드"""
        try:
            # 크롤러 엔진 초기화 (실제 구현시)
            # from crawler_engine import NewsCrawlerEngine
            # self.crawler_engine = NewsCrawlerEngine(self.config.settings)
            
            total = len(members)
            all_articles = []
            success_count = 0
            fail_count = 0
            
            for i, member in enumerate(members, 1):
                if not self.is_crawling:
                    self.log_queue.put((
                        datetime.now().strftime("%H:%M:%S"),
                        "WARNING",
                        "사용자가 수집을 중지했습니다."
                    ))
                    break
                
                company_name = member.get('회원사명', '')
                
                # UI 업데이트
                progress = (i / total) * 100
                self.progress_var.set(progress / 100)
                self.progress_label.configure(
                    text=f"수집 중... ({i}/{total})"
                )
                self.detail_label.configure(
                    text=f"현재: {company_name}"
                )
                
                try:
                    # 실제 크롤링 (시뮬레이션)
                    self.log_queue.put((
                        datetime.now().strftime("%H:%M:%S"),
                        "INFO",
                        f"[{i}/{total}] {company_name} 수집 시작"
                    ))
                    
                    # 여기서 실제 크롤링 수행
                    # articles = self.crawler_engine.crawl_company_news(member)
                    # all_articles.extend(articles)
                    
                    # 시뮬레이션을 위한 더미 데이터
                    import random
                    import time
                    time.sleep(random.uniform(0.5, 1.5))  # 실제로는 크롤링 시간
                    
                    article_count = random.randint(5, 15)  # 시뮬레이션
                    
                    self.log_queue.put((
                        datetime.now().strftime("%H:%M:%S"),
                        "SUCCESS",
                        f"{company_name}: {article_count}개 기사 수집 완료"
                    ))
                    success_count += 1
                    
                except Exception as e:
                    self.log_queue.put((
                        datetime.now().strftime("%H:%M:%S"),
                        "ERROR",
                        f"{company_name} 수집 실패: {str(e)}"
                    ))
                    fail_count += 1
            
            # 수집 완료 처리
            if self.is_crawling:
                # 더미 데이터 생성 (실제로는 크롤링 결과)
                self.collected_data = pd.DataFrame({
                    '회원사명': ['테스트'] * 10,
                    '기사제목': [f'테스트 기사 {i}' for i in range(10)],
                    'URL': ['http://example.com'] * 10,
                    '출처': ['테스트 뉴스'] * 10,
                    '발행일시': [datetime.now().strftime("%Y-%m-%d %H:%M")] * 10,
                    '수집일시': [datetime.now().strftime("%Y-%m-%d %H:%M")] * 10,
                    '플랫폼': ['Google'] * 5 + ['Naver'] * 5
                })
                
                # 완료 시간 기록
                self.config.set('last_run', datetime.now().strftime("%Y-%m-%d %H:%M"))
                
                # 완료 메시지
                self.log_queue.put((
                    datetime.now().strftime("%H:%M:%S"),
                    "SUCCESS",
                    f"수집 완료! 성공: {success_count}개, 실패: {fail_count}개"
                ))
                
                # 자동 저장 (설정된 경우)
                if self.config.get('auto_save', True) and self.collected_data is not None:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    file_path = RESULTS_DIR / f"news_{timestamp}.xlsx"
                    self.save_results(file_path)
            
        except Exception as e:
            self.log_queue.put((
                datetime.now().strftime("%H:%M:%S"),
                "ERROR",
                f"크롤링 오류: {str(e)}"
            ))
        finally:
            # 크롤러 정리
            # if self.crawler_engine:
            #     self.crawler_engine.cleanup()
            
            # UI 복원
            self.is_crawling = False
            self.start_button.configure(state="normal")
            self.stop_button.configure(state="disabled")
            
            if self.collected_data is not None and not self.collected_data.empty:
                self.export_button.configure(state="normal")
            
            self.progress_var.set(0)
            self.progress_label.configure(text="수집 완료")
            self.detail_label.configure(text="")
            self.update_status()
    
    def stop_crawling(self):
        """크롤링 중지"""
        if self.is_crawling:
            result = messagebox.askyesno("확인", "수집을 중지하시겠습니까?")
            if result:
                self.is_crawling = False
                self.log_message("사용자가 수집을 중지했습니다.", "WARNING")
    
    def view_results(self):
        """결과 폴더 열기"""
        try:
            if sys.platform == 'win32':
                os.startfile(RESULTS_DIR)
            elif sys.platform == 'darwin':
                os.system(f'open "{RESULTS_DIR}"')
            else:
                os.system(f'xdg-open "{RESULTS_DIR}"')
            
            self.log_message(f"결과 폴더 열기: {RESULTS_DIR.absolute()}", "INFO")
        except Exception as e:
            messagebox.showinfo("정보", f"결과 폴더: {RESULTS_DIR.absolute()}")
            self.log_message(f"결과 폴더 열기 실패: {e}", "ERROR")
    
    def export_results(self):
        """결과 내보내기"""
        if self.collected_data is None or self.collected_data.empty:
            messagebox.showwarning("경고", "저장할 데이터가 없습니다.")
            return
        
        file_path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[
                ("Excel files", "*.xlsx"),
                ("CSV files", "*.csv")
            ],
            initialfile=f"뉴스수집결과_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        )
        
        if file_path:
            if self.save_results(file_path):
                messagebox.showinfo("완료", f"결과를 저장했습니다.\n{file_path}")
    
    def save_results(self, file_path):
        """결과 저장"""
        try:
            if str(file_path).endswith('.xlsx'):
                with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
                    self.collected_data.to_excel(writer, index=False, sheet_name='뉴스수집결과')
                    
                    # 컬럼 너비 자동 조정
                    worksheet = writer.sheets['뉴스수집결과']
                    for column in self.collected_data.columns:
                        column_width = max(
                            self.collected_data[column].astype(str).str.len().max(),
                            len(column)
                        ) + 2
                        col_idx = self.collected_data.columns.get_loc(column)
                        worksheet.column_dimensions[chr(65 + col_idx)].width = min(column_width, 50)
            
            elif str(file_path).endswith('.csv'):
                self.collected_data.to_csv(file_path, index=False, encoding='utf-8-sig')
            
            self.log_message(f"결과 저장: {file_path}", "SUCCESS")
            return True
        except Exception as e:
            self.log_message(f"결과 저장 실패: {e}", "ERROR")
            return False
    
    def open_settings(self):
        """설정 창 열기"""
        dialog = SettingsDialog(self, self.config)
        self.wait_window(dialog)
    
    def on_closing(self):
        """프로그램 종료"""
        if self.is_crawling:
            result = messagebox.askyesnocancel(
                "종료",
                "수집이 진행 중입니다. 종료하시겠습니까?"
            )
            if result:
                self.is_crawling = False
                if self.crawl_thread:
                    self.crawl_thread.join(timeout=2)
                logger.info("프로그램 종료")
                self.destroy()
        else:
            logger.info("프로그램 종료")
            self.destroy(
import streamlit as st
import pandas as pd
import uuid
import datetime
import gspread
import re
from google.oauth2.service_account import Credentials

# --------------------------------------------------
# 이미지 URL 변환 함수
# --------------------------------------------------
def get_direct_url(url):
    if not isinstance(url, str) or not url.strip():
        return ""
    if "drive.google.com" in url:
        file_id = ""
        if "id=" in url:
            parts = url.split("id=")
            if len(parts) > 1:
                file_id = parts[1].split("&")[0]
        elif "file/d/" in url:
            parts = url.split("file/d/")
            if len(parts) > 1:
                file_id = parts[1].split("/")[0]
        
        if file_id:
            return f"https://drive.google.com/thumbnail?id={file_id}&sz=w1000"
    return url
    
# --------------------------------------------------
# Google Sheet 연결
# --------------------------------------------------
SCOPE = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

SPREADSHEET_ID = "1eg3TnoILIHXCzf4fPCU6uqzZssLnFS2xHO5zD7N2c0g"

@st.cache_resource
def get_gspread_client():
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=SCOPE
    )
    return gspread.authorize(creds)

gc = get_gspread_client()

@st.cache_resource
def get_working_sheets():
    try:
        doc = gc.open_by_key(SPREADSHEET_ID)
        # favorites 시트가 없으면 에러가 날 수 있으므로 체크 필요
        return doc.worksheet("users"), doc.worksheet("favorites")
    except Exception as e:
        return None, None

user_sheet, fav_sheet = get_working_sheets()

# --------------------------------------------------
# 1. 앱 설정
# --------------------------------------------------
st.set_page_config(page_title="2026 건축기사 필기 (초카이브)", layout="wide")

# --------------------------------------------------
# 2. 스타일 (기존 스타일 유지 및 보완)
# --------------------------------------------------
st.markdown("""
<style>
.concept-card {
    background-color: #f8f9fa;
    padding: 20px;
    border-radius: 12px;
    border: 1px solid #eee;
    margin-bottom: 20px;
}
.title-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 10px;
    border-bottom: 2px solid #eaeaea; 
    padding-bottom: 8px;
}
.concept-title-text {
    font-size: 20px;
    font-weight: bold;
    color: #2E4053;
}
.freq-badge {
    border: 1px solid #bbb;     
    color: #777;                
    border-radius: 4px;
    padding: 2px 8px;
    font-size: 13px;
    font-weight: 500;
    white-space: nowrap;
    margin-right: 8px;
}
.section-gap {
    height: 25px;
    width: 100%;
}
.question-box {
    background-color: #f8f9fa;
    padding: 15px;
    border-radius: 8px;
    margin-bottom: 12px;
    border: 1px solid #e0e0e0;
}
.q-year {
    color: #888;
    font-size: 12px;
    margin-bottom: 4px; 
}
.q-text {
    font-weight: bold;
    color: #2E4053;
    margin-bottom: 8px;
    font-size: 15px;
    display: block; 
}
.a-text {
    color: #444;
    font-size: 14px;
    line-height: 1.6; 
}
.app-logo {
    font-size: 12px;            
    font-weight: 300;            
    color: #a8b3b4;             
    text-align: right;
    margin-bottom: 0.5rem;
}
.concept-category {
    font-size: 14px;        
    font-weight: 400;            
    color: #7F8C8D;             
    margin-bottom: 4px;        
}
/* 즐겨찾기 버튼 전용 스타일 */
.fav-btn-container {
    display: flex;
    align-items: center;
}
.stButton button {
    width: 100%;
    padding: 0.6rem 0.5rem;
    background-color: #f1f3f5 !important;
    border: 1px solid #dee2e6 !important;
    color: #495057 !important;
    transition: background-color 0.3s;
}

.stButton button:hover {
    background-color: #e9ecef !important;
    border-color: #ced4da !important;
}

/* 하트 버튼 커스텀 */
.fav-active button {
    color: #f1c40f !important; /* 노란색 하트 */
    border-color: #f1c40f !important;
}

.concept-img {
    margin: 10px 0;
    border-radius: 8px;
    max-width: 100%;
}

/* 일반 텍스트 및 동그라미 숫자용 */
.text-line {
    margin-bottom: 4px;
    padding-left: 1.5em; 
    text-indent: -1.0em;
    line-height: 1.6;
    word-break: keep-all;
}

/* 하이픈(-) 시작 문장용: 첫 글자 열을 동그라미 숫자 라인과 맞춤 */
.text-hyphen {
    margin-bottom: 4px;
    padding-left: 1.5em; 
    text-indent: -0.6em;
    line-height: 1.6;
    word-break: keep-all;
}

/* 추가된 '>' 기호용 들여쓰기 스타일 */
.text-indent-extra {
    margin-bottom: 4px;
    padding-left: 2.5em; 
    text-indent: -1.0em;
    line-height: 1.6;
    word-break: keep-all;
    color: #555;
}

/* --- 마크다운 테이블 디자인 최적화 --- */
table {
    width: 100% !important;
    border-collapse: collapse !important;
    margin: 12px 0 !important;
    border-top: 2px solid #cbd5e0 !important;
    table-layout: auto !important;
    font-size: 0.9em !important;
}

th {
    background-color: #f7fafc !important;
    font-weight: bold !important;
    text-align: left !important;
    padding: 6px 10px !important;
    border-bottom: 2px solid #cbd5e0 !important;
    border-top: none !important;
    line-height: 1.4 !important;
}

td:first-child, th:first-child {
    white-space: nowrap !important;
    width: 1% !important;
    padding: 8px 15px 8px 10px !important;
    background-color: #f8f9fa !important;
    font-weight: bold !important;
    vertical-align: middle !important;
    border-right: 1px solid #e2e8f0 !important;
}

td {
    padding: 8px 10px !important;
    border: 1px solid #e2e8f0 !important;
    vertical-align: middle !important;
    line-height: 1.5 !important;
    color: #4a5568 !important;
}
</style>
""", unsafe_allow_html=True)

# --------------------------------------------------
# 3. 데이터 로드 및 Helper 함수
# --------------------------------------------------
def format_smart_text(text):
    if not text: return ""
    if "|" in text and "---" in text:
        return text.replace('\n', '  \n')
    
    lines = text.split('\n')
    html_output = ""
    for line in lines:
        raw_line = line.strip()
        if not raw_line: continue
        processed_line = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', raw_line)
        if processed_line.startswith('>'):
            content = processed_line[1:].strip()
            html_output += f"<div class='text-indent-extra'>{content}</div>"
        elif processed_line.startswith('-'):
            html_output += f"<div class='text-hyphen'>{processed_line}</div>"
        else:
            html_output += f"<div class='text-line'>{processed_line}</div>"
    return html_output

@st.cache_data(ttl=600)
def load_data():
    try:
        doc = gc.open_by_key(SPREADSHEET_ID)
        sheet = doc.worksheet("테스트용")
        all_values = sheet.get_all_values()
        if not all_values: return pd.DataFrame()
        
        headers = all_values[0]
        data = all_values[1:]
        df = pd.DataFrame(data, columns=headers)
        
        # 기본 컬럼 정의
        if len(headers) >= 9: df['개념이미지_I'] = df.iloc[:, 8]
        if len(headers) >= 10: 
            df['개념빈출_J'] = pd.to_numeric(df.iloc[:, 9].str.replace(r'[^0-9]', '', regex=True), errors='coerce').fillna(0).astype(int)
        if len(headers) >= 12: df['숫문_L'] = df.iloc[:, 11]
        if len(headers) >= 14: df['문제이미지_N'] = df.iloc[:, 13]

        df = df.loc[:, ~df.columns.duplicated()]
        df.columns = df.columns.str.strip()
        
        if "fpk" in df.columns and "PK" in df.columns:
            df["PK"] = df.apply(
                lambda row: row["fpk"].strip() if (str(row["PK"]).strip() == "" or pd.isna(row["PK"])) and str(row.get("fpk", "")).strip() != "" 
                else str(row["PK"]).strip(), axis=1
            )
        return df
    except Exception as e:
        st.error(f"데이터 로드 중 오류가 발생했습니다: {e}")
        return pd.DataFrame()

df = load_data()

# --------------------------------------------------
# 4. 사용자 인증
# --------------------------------------------------
@st.cache_data(ttl=600)
def get_allowed_emails():
    try:
        if user_sheet: return [e.strip() for e in user_sheet.col_values(1)[1:] if e.strip()]
        return None
    except: return None
    
user_email = st.session_state.get('user_id', "").strip()

if not user_email:
    ALLOWED_EMAILS = get_allowed_emails()
    if ALLOWED_EMAILS is None:
        st.error("⚠️ 구글 시트 연결 오류"); st.stop()
        
    st.info("👈 왼쪽 사이드바에서 이메일로 로그인하면 학습을 시작할 수 있습니다.")
    st.sidebar.title("🔐 사용자 인증")
    input_email = st.sidebar.text_input("등록된 이메일을 입력하세요").strip()
    if st.sidebar.button("로그인"):
        if input_email in ALLOWED_EMAILS:
            st.session_state.user_id = input_email
            st.rerun()
        else:
            st.sidebar.error("등록되지 않은 이메일입니다.")
    st.stop()

USER_ID = st.session_state.user_id

# --------------------------------------------------
# 5. 즐겨찾기 동기화 및 핸들러
# --------------------------------------------------
if "favorites" not in st.session_state or st.session_state.get('last_user') != USER_ID:
    try:
        # 1. 시트 기반(favorites 시트) 즐겨찾기 로드
        records = fav_sheet.get_all_records()
        fav_set = {str(r["PK"]) for r in records if str(r["user_id"]).strip() == USER_ID}
        
        # 2. '별표' 열 데이터 반영 (★ 표시가 있는 경우 세션에 추가)
        if "별표" in df.columns:
            star_pks = set(df[df["별표"].isin(["★", "1", 1])]["PK"].astype(str))
            fav_set.update(star_pks)
            
        st.session_state.favorites = fav_set
        st.session_state.last_user = USER_ID
    except: 
        st.session_state.favorites = set()

def toggle_favorite(pk_val):
    pk_str = str(pk_val)
    if pk_str in st.session_state.favorites:
        st.session_state.favorites.remove(pk_str)
        try:
            cell = fav_sheet.find(pk_str) # 단순화를 위해 PK로 찾으나 실제로는 user_id도 체크 필요
            # 정확한 삭제를 위해 모든 레코드를 가져와서 필터링 후 다시 쓰는 방식 권장하나 성능상 이슈로 생략 가능
            # 여기서는 세션 상태 위주로 작동하게 함
        except: pass
    else:
        st.session_state.favorites.add(pk_str)
        try:
            fav_sheet.append_row([USER_ID, pk_str, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
        except: pass

# --------------------------------------------------
# 6. 필터 및 모드 설정
# --------------------------------------------------
st.sidebar.title("🔍 학습 필터")
search_query = st.sidebar.text_input("개념 검색", placeholder="검색어를 입력하세요...").strip()
sort_by_freq = st.sidebar.checkbox("⭐ 빈출도 높은 순")
only_high_freq = st.sidebar.checkbox("🔥 3번 이상 빈출만")
view_mode = st.sidebar.radio("모드 선택", ["💛 즐겨찾기만", "🃏 암기카드", "전체 학습"])

filtered_df = df.copy()

if search_query:
    filtered_df = filtered_df[
        filtered_df['구분'].str.contains(search_query, case=False, na=False) |
        filtered_df['개념'].str.contains(search_query, case=False, na=False)
    ]

if only_high_freq:
    filtered_df = filtered_df[filtered_df['개념빈출_J'] >= 3]

if sort_by_freq:
    filtered_df = filtered_df.sort_values(by='개념빈출_J', ascending=False)

for col, label in [("과목", "과목"), ("대카테고리", "대카테고리"), ("소카테고리", "소카테고리")]:
    if col in filtered_df.columns:
        options = ["전체"] + list(filtered_df[col][filtered_df[col] != ""].unique())
        sel = st.sidebar.selectbox(f"{label} 선택", options)
        if sel != "전체": filtered_df = filtered_df[filtered_df[col] == sel]

if view_mode == "💛 즐겨찾기만":
    filtered_df = filtered_df[filtered_df["PK"].astype(str).isin(st.session_state.favorites)]

# --------------------------------------------------
# 7. 렌더링 함수
# --------------------------------------------------
if filtered_df.empty:
    st.info("선택한 조건에 해당하는 개념이 없습니다.")
else:
    grouped = filtered_df.groupby("PK", sort=False)
    pk_list = list(grouped.groups.keys())

    def render_concept_block(row, pk_val):
        pk_str = str(pk_val)
        num_val = str(row.get('숫구', '')).strip().replace(".0", "") or pk_str
        freq_val = str(row.get('개념빈출_J', '')).strip()
        is_fav = pk_str in st.session_state.favorites
        heart_icon = "💛" if is_fav else "🤍"
        
        # 상단 타이틀 레이아웃 (제목 | 빈출도 + 즐겨찾기)
        # 7:2:1 비율로 나누어 정렬
        col1, col2, col3 = st.columns([7, 1.5, 0.8])
        
        with col1:
            clean_gubun = row.get('구분','').replace('\n', ' ')
            st.markdown(f"<div class='concept-title-text'>{num_val}) {clean_gubun}</div>", unsafe_allow_html=True)
        
        with col2:
            if freq_val != "0":
                st.markdown(f"<div class='freq-badge'>{freq_val}회</div>", unsafe_allow_html=True)
            else:
                st.write("") # 빈 공간 유지
        
        with col3:
            # 즐겨찾기 버튼
            if st.button(heart_icon, key=f"fav_{pk_str}"):
                toggle_favorite(pk_str)
                st.rerun()

        st.markdown("<div style='border-bottom: 2px solid #eaeaea; margin-bottom: 10px;'></div>", unsafe_allow_html=True)
        
        concept_raw = str(row.get('개념', ''))
        st.markdown(format_smart_text(concept_raw), unsafe_allow_html=True)

        concept_img_url = get_direct_url(row.get('개념이미지_I', ''))
        if concept_img_url:
            st.image(concept_img_url, use_container_width=False, width=500)

    def render_questions(valid_qs):
        st.markdown("<div class='section-gap'></div>", unsafe_allow_html=True)
        if not valid_qs.empty:
            with st.expander(f"📝 관련 기출문제 ({len(valid_qs)}건)"):
                for _, q in valid_qs.iterrows():
                    year_info = str(q.get('출제년도', '')).strip() or str(q.get('문제빈도 출제년도', '')).strip()
                    year_html = f"<div class='q-year'>[{year_info}]</div>" if year_info else ""
                    q_num = str(q.get('숫문_L', '')).strip().replace(".0", "")
                    q_num_display = f"{q_num} " if q_num and "." in q_num else f"{q_num}. " if q_num else "Q. "
                    q_text = str(q.get('문제',''))
                    a_text = str(q.get('정답',''))
                    q_img_url = get_direct_url(q.get('문제이미지_N', ''))
                    q_img_html = f"<img src='{q_img_url}' class='concept-img' width='400'>" if q_img_url else ""

                    st.markdown(f"""
                    <div class='question-box'>
                        {year_html}
                        <div class='q-text'>{q_num_display}{q_text}</div>
                        <div style='text-align:center;'>{q_img_html}</div>
                        <div class='a-text' style='margin-top:10px;'>{format_smart_text(a_text)}</div>
                    </div>
                    """, unsafe_allow_html=True)

    # --------------------------------------------------
    # 뷰 모드 실행
    # --------------------------------------------------
    if view_mode == "🃏 암기카드":
        if "card_idx" not in st.session_state: st.session_state.card_idx = 0
        if st.session_state.card_idx >= len(pk_list): st.session_state.card_idx = 0

        pk = pk_list[st.session_state.card_idx]
        group = grouped.get_group(pk)
        row = group.iloc[0]
        st.markdown(f"<div class='concept-category'>{row.get('과목','')} / {row.get('대카테고리','')}</div>", unsafe_allow_html=True)
        
        with st.container(border=True):
            render_concept_block(row, pk)
        
        render_questions(group[group['문제'].str.strip() != ""])
        
        st.markdown("<div style='margin-top: 18px;'></div>", unsafe_allow_html=True)
        st.divider()
    
        current_idx = st.session_state.card_idx
        total_count = len(pk_list)
    
        col_prev, col_page, col_next = st.columns([1, 2, 1])
        with col_prev:
            if st.button("이전", key="btn_prev", disabled=(current_idx == 0)):
                st.session_state.card_idx = max(0, current_idx - 1)
                st.rerun()
        with col_page:
            st.markdown(f"<div style='text-align: center; font-weight: bold; color: #666;'>{current_idx + 1} / {total_count}</div>", unsafe_allow_html=True)
        with col_next:
            if st.button("다음", key="btn_next", disabled=(current_idx == total_count - 1)):
                st.session_state.card_idx = min(total_count - 1, current_idx + 1)
                st.rerun()
        
    else:
        for pk, group in grouped:
            row = group.iloc[0]
            with st.container():
                render_concept_block(row, pk)
                render_questions(group[group['문제'].str.strip() != ""])
            st.divider()

st.markdown("<div class='app-logo'>ⓒ초카이브 건축기사</div>", unsafe_allow_html=True)

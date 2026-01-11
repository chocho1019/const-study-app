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
        return doc.worksheet("users"), doc.worksheet("favorites")
    except Exception as e:
        return None, None

user_sheet, fav_sheet = get_working_sheets()

# --------------------------------------------------
# 1. 앱 설정
# --------------------------------------------------
st.set_page_config(page_title="2026 건축기사 필기 (초카이브)", layout="wide")

# --------------------------------------------------
# 2. 스타일 (즐겨찾기 버튼 및 레이아웃 유지)
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
    display: inline-block;
    vertical-align: middle;
}
/* 즐겨찾기 하트 버튼 전용 스타일 */
.stButton > button {
    border: none !important;
    background-color: transparent !important;
    padding: 0 !important;
    font-size: 22px !important;
    line-height: 1 !important;
    box-shadow: none !important;
    color: inherit !important;
}
.stButton > button:hover {
    background-color: transparent !important;
    color: #FFD700 !important; /* 호버 시 골드색 */
}
.section-gap { height: 25px; width: 100%; }
.question-box {
    background-color: #f8f9fa;
    padding: 15px;
    border-radius: 8px;
    margin-bottom: 12px;
    border: 1px solid #e0e0e0;
}
.q-year { color: #888; font-size: 12px; margin-bottom: 4px; }
.q-text { font-weight: bold; color: #2E4053; margin-bottom: 8px; font-size: 15px; display: block; }
.a-text { color: #444; font-size: 14px; line-height: 1.6; }
.app-logo { font-size: 12px; font-weight: 300; color: #a8b3b4; text-align: right; margin-bottom: 0.5rem; }
.concept-category { font-size: 14px; font-weight: 400; color: #7F8C8D; margin-bottom: 4px; }

/* 텍스트 정렬 스타일 */
.text-line { margin-bottom: 4px; padding-left: 1.5em; text-indent: -1.0em; line-height: 1.6; word-break: keep-all; }
.text-hyphen { margin-bottom: 4px; padding-left: 1.5em; text-indent: -0.6em; line-height: 1.6; word-break: keep-all; }
.text-indent-extra { margin-bottom: 4px; padding-left: 2.5em; text-indent: -1.0em; line-height: 1.6; word-break: keep-all; color: #555; }

/* 테이블 최적화 */
table { width: 100% !important; border-collapse: collapse !important; margin: 12px 0 !important; border-top: 2px solid #cbd5e0 !important; font-size: 0.9em !important; }
th { background-color: #f7fafc !important; font-weight: bold !important; text-align: left !important; padding: 6px 10px !important; border-bottom: 2px solid #cbd5e0 !important; }
td:first-child, th:first-child { white-space: nowrap !important; width: 1% !important; padding: 8px 15px 8px 10px !important; background-color: #f8f9fa !important; font-weight: bold !important; vertical-align: middle !important; border-right: 1px solid #e2e8f0 !important; }
td { padding: 8px 10px !important; border: 1px solid #e2e8f0 !important; vertical-align: middle !important; line-height: 1.5 !important; color: #4a5568 !important; }
</style>
""", unsafe_allow_html=True)

# --------------------------------------------------
# 3. 데이터 로드 및 Helper 함수
# --------------------------------------------------
def format_smart_text(text):
    if not text: return ""
    if "|" in text and "---" in text: return text.replace('\n', '  \n')
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
        if len(headers) >= 10: 
            df['개념빈출_J'] = pd.to_numeric(df.iloc[:, 9].str.replace(r'[^0-9]', '', regex=True), errors='coerce').fillna(0).astype(int)
        df = df.loc[:, ~df.columns.duplicated()]
        df.columns = df.columns.str.strip()
        return df
    except: return pd.DataFrame()

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
    if ALLOWED_EMAILS is None: st.error("⚠️ 연결 오류"); st.stop()
    st.sidebar.title("🔐 사용자 인증")
    input_email = st.sidebar.text_input("등록된 이메일을 입력하세요").strip()
    if st.sidebar.button("로그인"):
        if input_email in ALLOWED_EMAILS:
            st.session_state.user_id = input_email
            st.rerun()
    st.stop()

USER_ID = st.session_state.user_id

# --------------------------------------------------
# 5. 즐겨찾기 로직
# --------------------------------------------------
if "favorites" not in st.session_state or st.session_state.get('last_user') != USER_ID:
    try:
        records = fav_sheet.get_all_records()
        st.session_state.favorites = {str(r["PK"]) for r in records if str(r["user_id"]).strip() == USER_ID}
        st.session_state.last_user = USER_ID
    except: st.session_state.favorites = set()

def toggle_fav(pk):
    pk_str = str(pk)
    if pk_str in st.session_state.favorites:
        st.session_state.favorites.remove(pk_str)
        try:
            cells = fav_sheet.findall(USER_ID, in_column=1)
            for cell in cells:
                if str(fav_sheet.cell(cell.row, 2).value) == pk_str:
                    fav_sheet.delete_rows(cell.row)
                    break
        except: pass
    else:
        st.session_state.favorites.add(pk_str)
        try:
            fav_sheet.append_row([USER_ID, pk_str, datetime.datetime.now().strftime("%Y-%m-%d")])
        except: pass

# --------------------------------------------------
# 6. 필터 및 검색
# --------------------------------------------------
st.sidebar.title("🔍 학습 필터")
search_query = st.sidebar.text_input("개념 검색", placeholder="검색어를 입력하세요...").strip()
sort_by_freq = st.sidebar.checkbox("⭐ 빈출도 높은 순")
only_high_freq = st.sidebar.checkbox("🔥 3번 이상 빈출만")
view_mode = st.sidebar.radio("모드 선택", ["전체 학습", "🃏 암기카드", "💛 즐겨찾기만"])

filtered_df = df.copy()
if search_query:
    filtered_df = filtered_df[filtered_df['구분'].str.contains(search_query, case=False, na=False) | filtered_df['개념'].str.contains(search_query, case=False, na=False)]
if only_high_freq: filtered_df = filtered_df[filtered_df['개념빈출_J'] >= 3]
if sort_by_freq: filtered_df = filtered_df.sort_values(by='개념빈출_J', ascending=False)

if view_mode == "💛 즐겨찾기만":
    filtered_df = filtered_df[filtered_df["PK"].astype(str).isin(st.session_state.favorites)]

# --------------------------------------------------
# 7. 렌더링 함수
# --------------------------------------------------
if filtered_df.empty:
    st.info("조건에 맞는 개념이 없습니다.")
else:
    grouped = filtered_df.groupby("PK", sort=False)
    pk_list = list(grouped.groups.keys())

    def render_concept_block(row, pk_val):
        # 상단 헤더 레이아웃 (제목 영역 / 메타 정보 영역)
        col_title, col_meta = st.columns([0.75, 0.25])
        
        with col_title:
            num_val = str(row.get('숫구', '')).strip().replace(".0", "") or str(pk_val)
            clean_gubun = row.get('구분','').replace('\n', ' ')
            st.markdown(f"<div class='concept-title-text'>{num_val}) {clean_gubun}</div>", unsafe_allow_html=True)
            
        with col_meta:
            # 빈출 배지와 하트 버튼을 한 줄에 나란히 배치 (배지가 넓으므로 2:1 비율)
            meta_inner_1, meta_inner_2 = st.columns([2, 1])
            
            freq_val = str(row.get('개념빈출_J', '')).strip()
            with meta_inner_1:
                if freq_val != "0":
                    st.markdown(f"<div class='freq-badge'>{freq_val}회</div>", unsafe_allow_html=True)
                else:
                    st.write("") # 빈 공간 유지
            
            with meta_inner_2:
                is_fav = str(pk_val) in st.session_state.favorites
                heart_icon = "💛" if is_fav else "🤍"
                # 버튼 클릭 시 즉시 토글 후 리런
                if st.button(heart_icon, key=f"btn_fav_{pk_val}_{row.name}"):
                    toggle_fav(pk_val)
                    st.rerun()

        st.markdown("<div style='height:8px; border-bottom:2px solid #eaeaea; margin-bottom:12px;'></div>", unsafe_allow_html=True)
        st.markdown(format_smart_text(str(row.get('개념', ''))), unsafe_allow_html=True)
        img_url = get_direct_url(row.get('개념이미지_I', ''))
        if img_url: st.image(img_url, width=500)

    def render_questions(valid_qs):
        if not valid_qs.empty:
            with st.expander(f"📝 관련 기출문제 ({len(valid_qs)}건)"):
                for _, q in valid_qs.iterrows():
                    year = str(q.get('출제년도', '')).strip()
                    st.markdown(f"<div class='question-box'><div class='q-year'>[{year}]</div><div class='q-text'>{q.get('문제','')}</div><div class='a-text'>{format_smart_text(str(q.get('정답','')))}</div></div>", unsafe_allow_html=True)

    # 모드별 실행 로직
    if view_mode == "🃏 암기카드":
        if "card_idx" not in st.session_state: st.session_state.card_idx = 0
        idx = st.session_state.card_idx % len(pk_list)
        pk = pk_list[idx]
        group = grouped.get_group(pk)
        row = group.iloc[0]
        
        st.markdown(f"<div class='concept-category'>{row.get('과목','')} / {row.get('대카테고리','')}</div>", unsafe_allow_html=True)
        with st.container(border=True): 
            render_concept_block(row, pk)
        
        render_questions(group[group['문제'].str.strip() != ""])
        
        # 하단 네비게이션
        st.markdown("<div style='margin-top:20px;'></div>", unsafe_allow_html=True)
        nav1, nav2, nav3 = st.columns([1, 2, 1])
        if nav1.button("⬅️ 이전", key="prev_card", use_container_width=True): 
            st.session_state.card_idx -= 1
            st.rerun()
        nav2.markdown(f"<div style='text-align:center; font-size:18px; font-weight:bold; padding-top:5px;'>{idx+1} / {len(pk_list)}</div>", unsafe_allow_html=True)
        if nav3.button("다음 ➡️", key="next_card", use_container_width=True): 
            st.session_state.card_idx += 1
            st.rerun()
            
    else: # 전체 학습 및 즐겨찾기만 모드
        for pk, group in grouped:
            row = group.iloc[0]
            with st.container():
                render_concept_block(row, pk)
                render_questions(group[group['문제'].str.strip() != ""])
            st.divider()

st.markdown("<div class='app-logo'>ⓒ초카이브 건축기사</div>", unsafe_allow_html=True)

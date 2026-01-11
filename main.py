
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
# 2. 스타일 (기존 스타일 유지)
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
/* 기존 스타일에서 이 부분을 찾아 교체하거나 덮어쓰세요 */
.stButton button {
    width: 100%;
    padding: 0.6rem 0.5rem; /* 클릭하기 좋게 패딩을 살짝 늘렸습니다 */
    background-color: #f1f3f5 !important; /* 연한 회색 배경 */
    border: 1px solid #dee2e6 !important; /* 테두리도 연하게 설정 */
    color: #495057 !important; /* 글자색 */
    transition: background-color 0.3s;
}

.stButton button:hover {
    background-color: #e9ecef !important; /* 마우스 올렸을 때 약간 더 진한 회색 */
    border-color: #ced4da !important;
}

.concept-img {
    margin: 10px 0;
    border-radius: 8px;
    max-width: 100%;
}

.text-line {
   margin-bottom: 4px;
    /* 왼쪽 여백과 들여쓰기 값을 조절하여 동그라미 숫자와 글자 시작 열을 맞춤 */
    padding-left: 1.5em; 
    text-indent: -1.5em;
    line-height: 1.6;
    word-break: keep-all;

table {
    width: 100%;
    border-collapse: collapse;
    margin: 10px 0;
}
th, td {
    padding: 8px;
    border: 1px solid #ddd;
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
        if line.strip():
            html_output += f"<div class='text-line'>{line.strip()}</div>"
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
        
        # 열 매핑 (I:8, J:9, L:11, N:13)
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
# 5. 즐겨찾기 불러오기
# --------------------------------------------------
if "favorites" not in st.session_state or st.session_state.get('last_user') != USER_ID:
    try:
        records = fav_sheet.get_all_records()
        st.session_state.favorites = {str(r["PK"]) for r in records if str(r["user_id"]).strip() == USER_ID}
        st.session_state.last_user = USER_ID
    except: st.session_state.favorites = set()

# --------------------------------------------------
# 6. 필터 및 모드 설정
# --------------------------------------------------
st.sidebar.title("🔍 학습 필터")
# (수정됨) 라벨에서 (J열 기준) 텍스트 제거
sort_by_freq = st.sidebar.checkbox("⭐ 빈출도 높은 순")
only_high_freq = st.sidebar.checkbox("🔥 3번 이상 빈출만")
view_mode = st.sidebar.radio("모드 선택", ["💛 즐겨찾기만", "🃏 암기카드", "전체 학습"])

filtered_df = df.copy()

# 필터 적용 로직
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
    filtered_df = filtered_df[filtered_df["PK"].isin(st.session_state.favorites)]

# --------------------------------------------------
# 7. 렌더링 함수
# --------------------------------------------------
if filtered_df.empty:
    st.info("선택한 조건에 해당하는 개념이 없습니다.")
else:
    grouped = filtered_df.groupby("PK", sort=False)
    pk_list = list(grouped.groups.keys())

    def render_concept_block(row, pk_val):
        num_val = str(row.get('숫구', '')).strip().replace(".0", "") or pk_val
        freq_val = str(row.get('개념빈출_J', '')).strip()
        badge_html = f"<div class='freq-badge'>{freq_val}회</div>" if freq_val != "0" else ""

        st.markdown(f"""
        <div class='title-row'>
            <div class='concept-title-text'>{num_val}) {row.get('구분','')}</div>
            {badge_html}
        </div>
        """, unsafe_allow_html=True)
        
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
                    
                    # (수정됨) 마침표 중복 방지 로직
                    q_num = str(q.get('숫문_L', '')).strip().replace(".0", "")
                    if q_num:
                        # 시트 데이터에 이미 점이 있다면 그대로 쓰고, 없으면 하나만 붙여줌
                        q_num_display = f"{q_num} " if "." in q_num else f"{q_num}. "
                    else:
                        q_num_display = "Q. "
                    
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
    # 뷰 모드 실행 (수정된 버튼 배치 부분)
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
        
        # --------------------------------------------------
        # 3. 하단 네비게이션 (무조건 전체 너비 사용)
        # --------------------------------------------------
        st.markdown("<div style='margin-top: 30px;'></div>", unsafe_allow_html=True)
        st.divider()
    
        # 현재 인덱스 및 전체 개수 계산
        current_idx = st.session_state.card_idx
        total_count = len(pk_list)
    
        # 이전 버튼: use_container_width=True를 사용하여 강제로 가로 꽉 채움
        if st.button("이전", key="btn_prev", use_container_width=True, disabled=(current_idx == 0)):
            st.session_state.card_idx = max(0, current_idx - 1)
            st.rerun()
    
        # 페이지 표시: 중앙 정렬 및 여백 조절
        st.markdown(
            f"<div style='text-align: center; padding: 10px 0; font-size: 16px; font-weight: bold; color: #666;'>"
            f"{current_idx + 1} / {total_count}"
            f"</div>", 
            unsafe_allow_html=True
        )
    
        # 다음 버튼: use_container_width=True를 사용하여 강제로 가로 꽉 채움
        if st.button("다음", key="btn_next", use_container_width=True, disabled=(current_idx == total_count - 1)):
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

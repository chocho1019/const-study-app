import streamlit as st
import pandas as pd
import uuid
import datetime
import gspread
from google.oauth2.service_account import Credentials

# --------------------------------------------------
# 이미지 URL 변환 함수
# --------------------------------------------------
def get_direct_url(url):
    if not isinstance(url, str):
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
# 2. 스타일
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
.concept-title-card {
    font-size: 22px;
    font-weight: bold;
    color: #2E4053;
    margin-bottom: 15px;
}
.concept-content-card {
    font-size: 16px;
    color: #333;
    line-height: 1.6;
}
.concept-content-card table {
    width: 100%;
    border-collapse: collapse;
}
.concept-content-card th, .concept-content-card td {
    border: 1px solid #ddd;
    padding: 8px;
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
    margin-bottom: 8px;       
}
.concept-title {
    font-size: 24px;
    font-weight: bold;
    color: #2E4053;
    line-height: 1.2;
    margin-bottom: 15px;
}
.stButton button {
    width: 100%;
    padding: 0.25rem 0.5rem;
}
hr { margin: 1.5rem 0; }
</style>
""", unsafe_allow_html=True)

# --------------------------------------------------
# 3. 데이터 로드 및 FPK 처리 (수정됨)
# --------------------------------------------------
@st.cache_data(ttl=600)
def load_data():
    try:
        doc = gc.open_by_key(SPREADSHEET_ID)
        sheet = doc.worksheet("테스트용")
        all_values = sheet.get_all_values()
        
        if not all_values:
            return pd.DataFrame()

        headers = all_values[0]
        data = all_values[1:]
        df = pd.DataFrame(data, columns=headers)
        df = df.loc[:, ~df.columns.duplicated()]
        df.columns = df.columns.str.strip()
        
        # 1번 요청: FPK 처리 로직
        # 'fpk' 열이 있으면, 'PK'가 비어있는 행의 'PK'를 'fpk' 값으로 대체하여 연결
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
        if user_sheet:
            return [e.strip() for e in user_sheet.col_values(1)[1:] if e.strip()]
        return None
    except Exception as e:
        return None
    
user_email = st.session_state.get('user_id', "").strip()

if not user_email:
    ALLOWED_EMAILS = get_allowed_emails()
    if ALLOWED_EMAILS is None:
        st.error("⚠️ 구글 시트 연결 오류")
        st.stop()
        
    st.sidebar.title("🔐 사용자 인증")
    input_email = st.sidebar.text_input("등록된 이메일을 입력하세요").strip()
    if st.sidebar.button("로그인"):
        if input_email in ALLOWED_EMAILS:
            st.session_state.user_id = input_email
            st.rerun()
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
    except:
        st.session_state.favorites = set()

# --------------------------------------------------
# 6. 필터 및 모드 설정
# --------------------------------------------------
st.sidebar.title("🔍 학습 필터")
sort_by_freq = st.sidebar.checkbox("⭐ 빈출도 높은 순")
only_high_freq = st.sidebar.checkbox("🔥 3번 이상 빈출만")
view_mode = st.sidebar.radio("모드 선택", ["💛 즐겨찾기만", "🃏 암기카드", "전체 학습"])

filtered_df = df.copy()

for col, label in [("과목", "과목"), ("대카테고리", "대카테고리"), ("소카테고리", "소카테고리")]:
    if col in filtered_df.columns:
        options = ["전체"] + list(filtered_df[col][filtered_df[col] != ""].unique())
        sel = st.sidebar.selectbox(f"{label} 선택", options)
        if sel != "전체":
            filtered_df = filtered_df[filtered_df[col] == sel]

if view_mode == "💛 즐겨찾기만":
    filtered_df = filtered_df[filtered_df["PK"].isin(st.session_state.favorites)]

freq_col = "개념빈출" if "개념빈출" in filtered_df.columns else "빈출"
if only_high_freq and freq_col in filtered_df.columns:
    filtered_df["빈출_num"] = pd.to_numeric(filtered_df[freq_col], errors='coerce').fillna(0)
    filtered_df = filtered_df[filtered_df["빈출_num"] >= 3]

# --------------------------------------------------
# 7. 메인 화면 출력
# --------------------------------------------------
if filtered_df.empty:
    st.info("선택한 조건에 해당하는 개념이 없습니다.")
else:
    # PK를 기준으로 그룹화 (개념 1개에 여러 기출문제를 묶기 위함)
    grouped = filtered_df.groupby("PK", sort=False)
    pk_list = list(grouped.groups.keys())

    if view_mode == "🃏 암기카드":
        if "card_idx" not in st.session_state: st.session_state.card_idx = 0
        if st.session_state.card_idx >= len(pk_list): st.session_state.card_idx = 0
        
        pk = pk_list[st.session_state.card_idx]
        group = grouped.get_group(pk)
        row = group.iloc[0]
        
        # UI 레이아웃
        st.markdown(f"<div class='concept-category'>{row.get('과목','')} / {row.get('대카테고리','')}</div>", unsafe_allow_html=True)
        
        # 제목 및 내용 (2번 요청: <br> 허용 설정)
        num_str = str(row.get('숫구', '')).replace(".0", "")
        st.markdown(f"<div class='concept-title-card'>{num_str}. {row.get('구분','')}</div>", unsafe_allow_html=True)
        
        with st.container(border=True):
            # 2번 요청사항: unsafe_allow_html=True로 <br> 태그 반영
            st.markdown(str(row.get('개념', '')), unsafe_allow_html=True)
        
        # 기출문제 표시 (3번 요청사항 적용)
        valid_qs = group[group['문제'].str.strip() != ""]
        if not valid_qs.empty:
            with st.expander(f"📝 관련 기출문제 ({len(valid_qs)}건)"):
                for _, q in valid_qs.iterrows():
                    # 3번 요청: 정답 텍스트 깔끔하게 변경
                    st.markdown(f"""
                    <div style="background-color: #f1f8ff; padding: 15px; border-radius: 10px; margin-bottom: 10px; border: 1px solid #cce5ff;">
                        <span style='color: #888; font-size: 0.8em;'>[{q.get('문제빈도 출제년도','')}]</span>
                        <div style='font-weight: bold; color: #004085; margin: 5px 0;'>Q. {q.get('문제','')}</div>
                        <div style='color: #333;'>{q.get('정답','')}</div>
                    </div>
                    """, unsafe_allow_html=True)

        # 네비게이션
        c1, c2, c3 = st.columns([1,2,1])
        if c1.button(" 이전 "): st.session_state.card_idx = max(0, st.session_state.card_idx-1); st.rerun()
        c2.markdown(f"<p style='text-align:center;'>{st.session_state.card_idx+1} / {len(pk_list)}</p>", unsafe_allow_html=True)
        if c3.button(" 다음 "): st.session_state.card_idx = min(len(pk_list)-1, st.session_state.card_idx+1); st.rerun()

    else:
        # 전체 학습 모드
        for pk, group in grouped:
            row = group.iloc[0]
            st.markdown(f"<div class='concept-title'>{pk}. {row.get('구분','')}</div>", unsafe_allow_html=True)
            
            # 2번 요청: <br> 반영
            st.markdown(str(row.get('개념', '')), unsafe_allow_html=True)
            
            valid_qs = group[group['문제'].str.strip() != ""]
            if not valid_qs.empty:
                with st.expander(f"📝 관련 기출문제 ({len(valid_qs)}건)"):
                    for _, q in valid_qs.iterrows():
                        # 3번 요청: 깔끔한 정답 데이터 출력
                        st.markdown(f"""
                        <div style="background-color: #f8f9fa; padding: 12px; border-radius: 8px; margin-bottom: 10px; border: 1px solid #ddd;">
                            <div style='font-weight: bold; margin-bottom: 5px;'>Q. {q.get('문제','')}</div>
                            <div style='color: #333;'>{q.get('정답','')}</div>
                        </div>
                        """, unsafe_allow_html=True)
            st.divider()

st.markdown("<div class='app-logo'>ⓒ초카이브 건축기사</div>", unsafe_allow_html=True)

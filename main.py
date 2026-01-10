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
# 2. 스타일 (간격 및 빈출 뱃지 추가)
# --------------------------------------------------
st.markdown("""
<style>
/* 타이틀과 빈출 표시를 한 줄에 배치 */
.title-wrapper {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 10px;
}
.freq-badge {
    padding: 2px 8px;
    border: 1px solid #d1d1d1;
    border-radius: 4px;
    color: #a0a0a0;
    font-size: 14px;
    font-weight: 400;
}
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
}
.concept-content-card {
    font-size: 16px;
    color: #333;
    line-height: 1.4; /* 줄간격 조정 */
}
.app-logo {
    font-size: 12px;           
    color: #a8b3b4;            
    text-align: right;
}
.concept-category {
    font-size: 14px;        
    color: #7F8C8D;            
    margin-bottom: 8px;       
}
.concept-title {
    font-size: 20px; /* 사진2의 느낌으로 소폭 조정 */
    font-weight: bold;
    color: #2E4053;
    line-height: 1.2;
}
/* 기출문제 내부 텍스트 간격 조정 */
.question-box {
    background-color: #f8f9fa;
    padding: 15px;
    border-radius: 10px;
    margin-bottom: 10px;
    border: 1px solid #eee;
    line-height: 1.4;
}
.stButton button {
    width: 100%;
    padding: 0.25rem 0.5rem;
}
hr { margin: 1.5rem 0; }
</style>
""", unsafe_allow_html=True)

# --------------------------------------------------
# 3. 데이터 로드 및 FPK 처리
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
# 4. 사용자 인증 로직 (기존 유지)
# --------------------------------------------------
user_email = st.session_state.get('user_id', "").strip()
if not user_email:
    st.sidebar.title("🔐 사용자 인증")
    input_email = st.sidebar.text_input("등록된 이메일을 입력하세요").strip()
    if st.sidebar.button("로그인"):
        st.session_state.user_id = input_email
        st.rerun()
    st.stop()
USER_ID = st.session_state.user_id

# --------------------------------------------------
# 5. 즐겨찾기 (기존 유지)
# --------------------------------------------------
if "favorites" not in st.session_state:
    st.session_state.favorites = set()

# --------------------------------------------------
# 6. 필터 및 화면 출력
# --------------------------------------------------
st.sidebar.title("🔍 학습 필터")
view_mode = st.sidebar.radio("모드 선택", ["🃏 암기카드", "전체 학습", "💛 즐겨찾기만"])

filtered_df = df.copy()
# (기존 필터 로직 동일하게 적용 가능)

if filtered_df.empty:
    st.info("데이터가 없습니다.")
else:
    grouped = filtered_df.groupby("PK", sort=False)
    pk_list = list(grouped.groups.keys())

    # --- 출력 로직 시작 ---
    for pk in pk_list:
        group = grouped.get_group(pk)
        row = group.iloc[0]
        
        # 1. 타이틀 구성 (숫구 + 구분) & 5. 빈출 표시
        num_val = str(row.get('숫구', '')).replace(".0", "")
        title_text = f"{num_val}) {row.get('구분', '')}"
        freq_val = str(row.get('개념빈출', '')).replace(".0", "")
        
        st.markdown(f"""
        <div class="title-wrapper">
            <div class="concept-title">{title_text}</div>
            <div class="freq-badge">{freq_val}회</div>
        </div>
        """, unsafe_allow_html=True)
        
        # 4. 개념 내용 (간격 조정 적용)
        concept_content = str(row.get('개념', ''))
        st.markdown(f"<div class='concept-content-card'>{concept_content}</div>", unsafe_allow_html=True)
        
        # --- 관련 기출문제 영역 ---
        valid_qs = group[group['문제'].str.strip() != ""]
        if not valid_qs.empty:
            with st.expander(f"📝 관련 기출문제 ({len(valid_qs)}건)"):
                for _, q in valid_qs.iterrows():
                    # 2. 자연스러운 간격 & 3. 출제년도 표시
                    years = q.get('문제빈도 출제년도', '')
                    st.markdown(f"""
                    <div class="question-box">
                        <div style='color: #888; font-size: 0.75em; margin-bottom: 3px;'>[{years}]</div>
                        <div style='font-weight: bold; color: #2E4053; margin-bottom: 5px;'>Q. {q.get('문제','')}</div>
                        <div style='color: #333;'>{q.get('정답','')}</div>
                    </div>
                    """, unsafe_allow_html=True)
        
        st.divider()

st.markdown("<div class='app-logo'>ⓒ초카이브 건축기사</div>", unsafe_allow_html=True)

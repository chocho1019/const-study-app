import streamlit as st
import pandas as pd
import uuid
import datetime
import gspread
from google.oauth2.service_account import Credentials

# --------------------------------------------------
# 이미지 URL 변환 함수 (Google Drive 썸네일 지원)
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
# Google Sheet 연결 및 데이터 로드
# --------------------------------------------------
SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
SPREADSHEET_ID = "1eg3TnoILIHXCzf4fPCU6uqzZssLnFS2xHO5zD7N2c0g"

@st.cache_resource
def get_gspread_client():
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=SCOPE)
    return gspread.authorize(creds)

gc = get_gspread_client()

@st.cache_resource
def get_working_sheets():
    try:
        doc = gc.open_by_key(SPREADSHEET_ID)
        return doc.worksheet("users"), doc.worksheet("favorites")
    except:
        return None, None

user_sheet, fav_sheet = get_working_sheets()

# --------------------------------------------------
# 1. 앱 설정 및 스타일 (간격 최적화)
# --------------------------------------------------
st.set_page_config(page_title="2026 건축기사 필기 (초카이브)", layout="wide")

st.markdown("""
<style>
/* 개념 텍스트 간격 제거 */
.concept-text-container p {
    margin-bottom: 0px !important;
    padding-bottom: 0px !important;
    line-height: 1.5;
}

/* 기출문제 박스 내부 간격 최적화 */
.question-box {
    background-color: #f8f9fa;
    padding: 12px;
    border-radius: 8px;
    margin-bottom: 10px;
    border: 1px solid #e0e0e0;
}
.q-year { color: #888; font-size: 12px; margin-bottom: 2px; }
.q-text { font-weight: bold; color: #2E4053; margin-bottom: 4px; font-size: 15px; }
.a-text { color: #444; font-size: 14px; line-height: 1.4; }

/* 타이틀 및 빈출 배지 */
.title-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 8px;
}
.concept-title-text { font-size: 19px; font-weight: bold; color: #2E4053; }
.freq-badge {
    border: 1px solid #d1d1d1;
    color: #999;
    border-radius: 4px;
    padding: 1px 6px;
    font-size: 12px;
}

.app-logo { font-size: 12px; color: #a8b3b4; text-align: right; }
hr { margin: 1rem 0; }
</style>
""", unsafe_allow_html=True)

# --------------------------------------------------
# 2. 데이터 처리 로직
# --------------------------------------------------
@st.cache_data(ttl=600)
def load_data():
    try:
        doc = gc.open_by_key(SPREADSHEET_ID)
        sheet = doc.worksheet("테스트용")
        df = pd.DataFrame(sheet.get_all_records())
        df.columns = df.columns.str.strip()
        
        if "fpk" in df.columns and "PK" in df.columns:
            df["PK"] = df.apply(
                lambda row: str(row["fpk"]).strip() if not str(row["PK"]).strip() and str(row.get("fpk", "")).strip() else str(row["PK"]).strip(), axis=1
            )
        return df
    except Exception as e:
        st.error(f"데이터 로드 오류: {e}")
        return pd.DataFrame()

df = load_data()

# [사용자 인증 및 즐겨찾기 로직 - 기존과 동일하게 유지]
user_email = st.session_state.get('user_id', "").strip()
if not user_email:
    st.sidebar.title("🔐 로그인")
    input_email = st.sidebar.text_input("이메일 입력").strip()
    if st.sidebar.button("접속"):
        st.session_state.user_id = input_email
        st.rerun()
    st.stop()

# --------------------------------------------------
# 3. 렌더링 함수 (요청사항 핵심 반영)
# --------------------------------------------------
def render_concept_section(row, pk_val):
    # 타이틀 (숫구 우선 사용)
    num_val = str(row.get('숫구', '')).strip().replace(".0", "")
    if not num_val: num_val = pk_val
    
    freq_val = str(row.get('개념빈출', '')).strip().replace(".0", "")
    badge_html = f"<div class='freq-badge'>{freq_val}회</div>" if freq_val else ""

    st.markdown(f"""
    <div class='title-row'>
        <div class='concept-title-text'>{num_val}) {row.get('구분','')}</div>
        {badge_html}
    </div>
    """, unsafe_allow_html=True)
    
    # 개념 텍스트 (마크다운 + <br> 지원을 위한 처리)
    concept_raw = str(row.get('개념', ''))
    # 한 줄 띄어쓰기 없이 붙이기 위해 연속된 줄바꿈 제거 후 마크다운 줄바꿈(\n)으로 통일
    concept_processed = concept_raw.replace('\n\n', '\n').replace('\n', '  \n')
    
    st.markdown(f"<div class='concept-text-container'>", unsafe_allow_html=True)
    st.markdown(concept_processed, unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)
    
    # 개념 이미지 출력
    img_url = get_direct_url(row.get('개념이미지', ''))
    if img_url:
        st.image(img_url, use_container_width=True)

def render_question_section(valid_qs):
    if not valid_qs.empty:
        with st.expander(f"📝 관련 기출문제 ({len(valid_qs)}건)"):
            for _, q in valid_qs.iterrows():
                year_info = str(q.get('문제빈도 출제년도', '')).strip()
                # 정답 텍스트 줄바꿈 처리 및 띄어쓰기 제거
                answer_processed = str(q.get('정답', '')).replace('\n\n', '\n').replace('\n', '<br>')
                
                st.markdown(f"""
                <div class='question-box'>
                    <div class='q-year'>[{year_info}]</div>
                    <div class='q-text'>Q. {q.get('문제','')}</div>
                    <div class='a-text'>{answer_processed}</div>
                </div>
                """, unsafe_allow_html=True)
                
                # 문제 이미지(해설 이미지 등) 출력
                q_img_url = get_direct_url(q.get('문제이미지', ''))
                if q_img_url:
                    st.image(q_img_url, width=400)

# --------------------------------------------------
# 4. 메인 화면 출력
# --------------------------------------------------
view_mode = st.sidebar.radio("모드 선택", ["전체 학습", "🃏 암기카드", "💛 즐겨찾기만"])
filtered_df = df.copy() # (필터 로직 생략 - 기존 유지)

if not filtered_df.empty:
    grouped = filtered_df.groupby("PK", sort=False)
    
    if view_mode == "전체 학습":
        for pk, group in grouped:
            row = group.iloc[0]
            render_concept_section(row, pk)
            render_question_section(group[group['문제'].str.strip() != ""])
            st.divider()
    # (암기카드 로직도 render 함수를 호출하도록 구현)
else:
    st.info("해당하는 데이터가 없습니다.")

st.markdown("<div class='app-logo'>ⓒ초카이브 건축기사</div>", unsafe_allow_html=True)

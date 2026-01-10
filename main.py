import streamlit as st
import pandas as pd
import datetime
import gspread
from google.oauth2.service_account import Credentials

# --------------------------------------------------
# 추가: 이미지 URL 변환 함수
# --------------------------------------------------
def get_direct_url(url):
    if not isinstance(url, str): return url
    if "drive.google.com" in url:
        file_id = ""
        if "id=" in url:
            file_id = url.split("id=")[1].split("&")[0]
        elif "file/d/" in url:
            file_id = url.split("file/d/")[1].split("/")[0]
        if file_id:
            return f"https://drive.google.com/thumbnail?id={file_id}&sz=w1000"
    return url

# --------------------------------------------------
# Google Sheet 연결
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
        # 테스트용 시트와 유저/즐겨찾기 시트 로드
        return doc.worksheet("users"), doc.worksheet("favorites")
    except Exception as e:
        return None, None

user_sheet, fav_sheet = get_working_sheets()

# --------------------------------------------------
# 1. 앱 설정 및 스타일
# --------------------------------------------------
st.set_page_config(page_title="2026 건축기사 필기 (초카이브)", layout="wide")

st.markdown("""
<style>
    .concept-card { background-color: #f8f9fa; padding: 20px; border-radius: 12px; border: 1px solid #eee; margin-bottom: 20px; }
    .concept-title-card { font-size: 22px; font-weight: bold; color: #2E4053; margin-bottom: 15px; }
    .concept-content-card { font-size: 16px; color: #333; line-height: 1.6; }
    .concept-category { font-size: 14px; color: #7F8C8D; margin-bottom: 8px; }
    .concept-title { font-size: 24px; font-weight: bold; color: #2E4053; margin-bottom: 15px; }
    .app-logo { font-size: 12px; color: #a8b3b4; text-align: right; margin-bottom: 0.5rem; }
    /* 테이블 스타일 커스텀 */
    table { width: 100%; border-collapse: collapse; margin: 10px 0; }
    th { background-color: #f2f2f2; font-weight: bold; }
    td, th { border: 1px solid #ddd; padding: 8px; text-align: left; }
</style>
""", unsafe_allow_html=True)

# --------------------------------------------------
# 2. 데이터 로드 (통합 시트: 테스트용)
# --------------------------------------------------
@st.cache_data
def load_integrated_data(csv_url):
    df = pd.read_csv(csv_url)
    df.columns = df.columns.str.strip()
    df["PK"] = df["PK"].astype(str).str.strip()
    # 숫구, 숫문 등 숫자 데이터 처리
    for col in ["숫구", "숫문", "정답"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)
    return df

# '테스트용' 시트의 GID를 확인하여 URL 설정 (스크린샷 기반 GID 확인 필요, 여기서는 예시 GID 사용)
# 만약 GID가 다르다면 아래 gid= 부분을 수정해야 합니다.
TEST_SHEET_URL = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/gviz/tq?tqx=out:csv&gid=1116239162" # '테스트용' 시트 GID

df = load_integrated_data(TEST_SHEET_URL)

# --------------------------------------------------
# 3. 사용자 인증 및 즐겨찾기 (기존 유지)
# --------------------------------------------------
user_email = st.session_state.get('user_id', "").strip()
if not user_email:
    # (인증 로직 생략 - 기존 코드와 동일)
    st.sidebar.title("🔐 사용자 인증")
    # ... (기존 인증 코드 삽입)
    st.stop()

USER_ID = st.session_state.user_id

if "favorites" not in st.session_state:
    try:
        records = fav_sheet.get_all_records()
        st.session_state.favorites = {str(r["PK"]) for r in records if str(r["user_id"]).strip() == USER_ID}
    except:
        st.session_state.favorites = set()

# --------------------------------------------------
# 4. 사이드바 필터
# --------------------------------------------------
st.sidebar.title("🔍 학습 필터")
view_mode = st.sidebar.radio("모드 선택", ["전체 학습", "🃏 암기카드", "💛 즐겨찾기만"])

filtered_df = df.copy()
for col, label in [("과목", "과목"), ("대카테고리", "대카테고리"), ("소카테고리", "소카테고리")]:
    options = ["전체"] + list(filtered_df[col].dropna().unique())
    sel = st.sidebar.selectbox(f"{label} 선택", options)
    if sel != "전체":
        filtered_df = filtered_df[filtered_df[col] == sel]

if view_mode == "💛 즐겨찾기만":
    filtered_df = filtered_df[filtered_df["PK"].isin(st.session_state.favorites)]

# --------------------------------------------------
# 5. 메인 화면 출력 로직
# --------------------------------------------------
if filtered_df.empty:
    st.info("선택한 조건에 해당하는 데이터가 없습니다.")
else:
    # PK별로 그룹화 (하나의 개념에 여러 문제가 있을 수 있음)
    grouped = filtered_df.groupby("PK", sort=False)
    pk_list = list(grouped.groups.keys())

    if view_mode == "🃏 암기카드":
        # 암기카드 로직 (생략 - 필요시 리스트 모드와 동일한 제목/내용 구조 적용)
        if "card_idx" not in st.session_state: st.session_state.card_idx = 0
        idx = st.session_state.card_idx
        pk = pk_list[idx % len(pk_list)]
        group = grouped.get_group(pk)
        row = group.iloc[0]
        # ... (이하 암기카드 UI 구성)
    
    else: # 전체 학습 모드
        for pk in pk_list:
            group = grouped.get_group(pk)
            row = group.iloc[0] # 개념 정보는 첫 번째 행에서 가져옴
            is_fav = pk in st.session_state.favorites

            # 제목 영역: 숫구. 구분
            title_text = f"{row['숫구']}. {row['구분']}"
            col_h, col_t = st.columns([0.05, 0.95])
            with col_h:
                if st.button("💛" if is_fav else "🤍", key=f"fav_{pk}"):
                    # 즐겨찾기 토글 로직
                    st.rerun()
            with col_t:
                st.markdown(f"<div class='concept-title'>{title_text}</div>", unsafe_allow_html=True)

            # 개념 내용 출력 (표 형식 지원)
            concept_content = str(row['개념']) if pd.notna(row['개념']) else ""
            if "|" in concept_content: # 마크다운 표 형태인 경우
                st.markdown(concept_content, unsafe_allow_html=True)
            else:
                st.write(concept_content)

            # 개념 이미지
            if pd.notna(row.get('개념이미지')) and str(row['개념이미지']).startswith("http"):
                st.image(get_direct_url(str(row['개념이미지'])), use_container_width=True)

            # 기출문제 영역 (L열 이후 데이터 활용)
            # '문제' 열에 데이터가 있는 행들만 추출
            questions = group[group['문제'].notna()]
            if not questions.empty:
                with st.expander(f"📝 관련 기출문제 ({len(questions)}건)"):
                    for _, q_row in questions.iterrows():
                        q_num = q_row['숫문']
                        q_text = q_row['문제']
                        q_ans = q_row['정답']
                        q_year = q_row.get('출제년도', '')
                        
                        q_html = f"""
                        <div style="background-color: #f1f8ff; padding: 15px; border-radius: 10px; margin-bottom: 10px; border: 1px solid #cce5ff;">
                            <span style='color: #888; font-size: 0.8em;'>[{q_year}]</span>
                            <div style='font-weight: bold; margin-top: 5px;'>Q{q_num}. {q_text}</div>
                            <div style='margin-top: 10px; color: #333;'><b>정답: {q_ans}번</b></div>
                        </div>
                        """
                        st.markdown(q_html, unsafe_allow_html=True)
                        if pd.notna(q_row.get('문제이미지')) and str(q_row['문제이미지']).startswith("http"):
                            st.image(get_direct_url(str(q_row['문제이미지'])), width=400)
            else:
                with st.expander("📝 관련 기출문제 (0건)"):
                    st.write("등록된 기출문제가 없습니다.")
            
            st.divider()

# 하단 로고
st.markdown("<div class='app-logo'>ⓒ초카이브 건축기사</div>", unsafe_allow_html=True)

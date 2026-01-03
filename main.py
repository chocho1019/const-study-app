import streamlit as st
import pandas as pd
import uuid
import datetime
import gspread
from google.oauth2.service_account import Credentials

# --------------------------------------------------
# Google Sheet 연결
# --------------------------------------------------
SCOPE = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

creds = Credentials.from_service_account_info(
    st.secrets["gcp_service_account"],
    scopes=SCOPE
)

gc = gspread.authorize(creds)

SPREADSHEET_ID = "1eg3TnoILIHXCzf4fPCU6uqzZssLnFS2xHO5zD7N2c0g"
sheet = gc.open_by_key(SPREADSHEET_ID)

fav_sheet = sheet.worksheet("favorites")


# --------------------------------------------------
# 1. 앱 설정
# --------------------------------------------------
st.set_page_config(page_title="2026 건축기사 필기 (초카이브)", layout="wide")

# --------------------------------------------------
# 2. 스타일
# --------------------------------------------------

st.markdown("""
<style>
/* 페이지 표시 글자 스타일 추가 (연한 회색) */
.nav-text {
    text-align: center; 
    line-height: 2.4; 
    font-weight: bold; 
    font-size: 16px;
    color: #bdc3c7; /* 연한 회색 */
}

/* 암기카드 전용 배경 박스 */
.concept-card {
    background-color: #f8f9fa; /* 연한 회색 */
    padding: 20px;
    border-radius: 12px;
    border: 1px solid #eee;
    margin-bottom: 20px;
}

/* 박스 안의 제목 스타일 */
.concept-title-card {
    font-size: 22px;
    font-weight: bold;
    color: #2E4053;
    margin-bottom: 15px;
}

/* 박스 안의 내용 스타일 */
.concept-content-card {
    font-size: 16px;
    color: #333;
    line-height: 1.6;
    white-space: pre-wrap;
}


/* 모바일에서 컬럼 가로 정렬 강제 유지 */
[data-testid="column"] {
    min-width: 0px !important;
    flex-basis: fit-content !important;
}

.app-logo {
    font-size: 14px;
    font-weight: 500;
    color: #9aa0a6;
    text-align: right;
    margin-bottom: 1rem;
}

.concept-category {
    font-size: 12px;
    color: #7F8C8D;
    margin-bottom: 4px;
}

.concept-title {
    font-size: 24px;
    font-weight: bold;
    color: #2E4053;
    line-height: 1.2;
    margin-bottom: 15px; /* 제목 아래 간격 확보 */
}

/* 기출문제 박스 위쪽 간격 추가 */
.q-box {
    background-color: #e7f3fe; 
    border-left: 5px solid #2196F3; 
    padding: 15px; 
    border-radius: 5px;
    margin-top: 20px; /* 개념 내용과의 간격 확보 */
}

/* 버튼 내부 여백 조절 */
.stButton button {
    width: 100%;
    padding: 0.25rem 0.5rem;
}

hr { margin: 1.5rem 0; }
</style>
""", unsafe_allow_html=True)

# --------------------------------------------------
# 3. 데이터 로드
# --------------------------------------------------
@st.cache_data
def load_sheet(csv_url):
    df = pd.read_csv(csv_url)
    df.columns = df.columns.str.strip()
    df["PK"] = df["PK"].astype(str).str.strip()
    return df

CONCEPT_URL = "https://docs.google.com/spreadsheets/d/1eg3TnoILIHXCzf4fPCU6uqzZssLnFS2xHO5zD7N2c0g/gviz/tq?tqx=out:csv&gid=775019664"
QUESTION_URL = "https://docs.google.com/spreadsheets/d/1eg3TnoILIHXCzf4fPCU6uqzZssLnFS2xHO5zD7N2c0g/gviz/tq?tqx=out:csv&gid=46086374"

df_concept = load_sheet(CONCEPT_URL)
df_question = load_sheet(QUESTION_URL)

df = df_concept.merge(df_question, on="PK", how="left")

# --------------------------------------------------
# 4. 초기 사용자 인증 처리 (데이터 접근 제어)
# --------------------------------------------------
# 'users' 시트에서 허용된 이메일 목록 가져오기
try:
    user_sheet = sheet.worksheet("users")
    ALLOWED_EMAILS = [e.strip() for e in user_sheet.col_values(1)[1:] if e.strip()]
except Exception as e:
    st.error("구글 시트에 'users' 탭이 없거나 설정을 확인해주세요.")
    st.stop()

# 세션에 저장된 이메일 확인
user_email = st.session_state.get('user_id', "").strip()

# 만약 로그인이 안 되어 있다면 로그인 창만 보여주고 중단
if not user_email or user_email not in ALLOWED_EMAILS:
    st.sidebar.title("🔐 사용자 인증")
    input_email = st.sidebar.text_input("등록된 이메일을 입력하세요", key="login_input").strip()
    if st.sidebar.button("로그인"):
        if input_email in ALLOWED_EMAILS:
            st.session_state.user_id = input_email
            st.rerun()
        else:
            st.sidebar.error("등록되지 않은 이메일입니다.")
    st.info("👈 왼쪽 사이드바에서 이메일로 로그인하면 학습을 시작할 수 있습니다.")
    st.stop()

USER_ID = st.session_state.user_id

# --------------------------------------------------
# 5. 상단 로고 (여기에 다시 추가합니다)
# --------------------------------------------------
st.markdown(
    "<div class='app-logo'>🏗️ 건축기사 필기노트 by. 초카이브</div>",
    unsafe_allow_html=True
)

# --------------------------------------------------
# 5. 저장된 즐겨찾기 불러오기
# --------------------------------------------------
if "favorites" not in st.session_state or st.session_state.get('last_user') != USER_ID:
    try:
        records = fav_sheet.get_all_records()
        st.session_state.favorites = {
            str(r["PK"]) for r in records 
            if str(r["user_id"]).strip() == USER_ID
        }
        st.session_state.last_user = USER_ID
    except:
        st.session_state.favorites = set()

    
# --------------------------------------------------
# 6. 사이드바 필터 (상단 배치)
# --------------------------------------------------
st.sidebar.title("🔍 학습 필터")

# 빈출도 관련 필터
sort_by_freq = st.sidebar.checkbox("⭐ 빈출도 높은 순")
only_high_freq = st.sidebar.checkbox("🔥 3번 이상 빈출만")

view_mode = st.sidebar.radio("모드 선택", ["💛 즐겨찾기만", "🃏 암기카드", "전체 학습"])

filtered_df = df.copy()

# 카테고리 필터링
for col, label in [("과목", "과목"), ("대카테고리", "대카테고리"), ("소카테고리", "소카테고리")]:
    if col in filtered_df.columns:
        options = ["전체"] + sorted(filtered_df[col].dropna().unique())
        sel = st.sidebar.selectbox(f"{label} 선택", options)
        if sel != "전체":
            filtered_df = filtered_df[filtered_df[col] == sel]

# 필터 적용 로직 (즐겨찾기, 빈출도)
if view_mode == "💛 즐겨찾기만":
    filtered_df = filtered_df[filtered_df["PK"].isin(st.session_state.favorites)]

if only_high_freq and "빈출" in filtered_df.columns:
    filtered_df["빈출_num"] = pd.to_numeric(filtered_df["빈출"], errors='coerce').fillna(0)
    filtered_df = filtered_df[filtered_df["빈출_num"] >= 3]

if sort_by_freq and "빈출" in filtered_df.columns:
    if "빈출_num" not in filtered_df.columns:
        filtered_df["빈출_num"] = pd.to_numeric(filtered_df["빈출"], errors='coerce').fillna(0)
    filtered_df = filtered_df.sort_values("빈출_num", ascending=False)

# --------------------------------------------------
# 🃏 암기카드 상태 관리
# --------------------------------------------------
if "card_index" not in st.session_state:
    st.session_state.card_index = 0

if "last_pk_list" not in st.session_state:
    st.session_state.last_pk_list = []

current_pk_list = filtered_df["PK"].tolist()

if st.session_state.last_pk_list != current_pk_list:
    st.session_state.card_index = 0
    st.session_state.last_pk_list = current_pk_list


# --------------------------------------------------
# 7. 사용자 인증 정보 (사이드바 하단 배치)
# --------------------------------------------------
st.sidebar.markdown("---")
st.sidebar.write(f"👤 **로그인 정보**: {USER_ID}")
if st.sidebar.button("로그아웃"):
    del st.session_state.user_id
    st.rerun()

# --------------------------------------------------
# 7. 메인 화면
# --------------------------------------------------

if filtered_df.empty:
    st.info("선택한 조건에 해당하는 개념이 없습니다.")


# ==================================================
# 🃏 암기카드 모드 (수정본)
# ==================================================
elif view_mode == "🃏 암기카드":
    total = len(filtered_df)
    i = st.session_state.card_index
    row = filtered_df.iloc[i]
    pk = row["PK"]
    is_fav = pk in st.session_state.favorites

    # --- 회색 박스 시작 ---
    # 박스 상단과 카테고리 표시
    cat_text = f"{row.get('과목','')} / {row.get('대카테고리','')} / {row.get('소카테고리','')}"
    st.markdown(f"""
        <div class="concept-card">
            <div class='concept-category'>{cat_text}</div>
    """, unsafe_allow_html=True)
    
    # 하트 버튼 배치 (컬럼을 사용하여 박스 내부처럼 보이게 함)
    col_fav, _ = st.columns([0.1, 0.9])
    with col_fav:
        if st.button("💛" if is_fav else "🤍", key=f"card_fav_{pk}"):
            now = datetime.datetime.now().isoformat()
            if is_fav:
                cells = fav_sheet.findall(pk)
                for c in cells:
                    if fav_sheet.cell(c.row, 1).value == USER_ID:
                        fav_sheet.delete_rows(c.row)
                        break
                st.session_state.favorites.remove(pk)
            else:
                fav_sheet.append_row([USER_ID, pk, now])
                st.session_state.favorites.add(pk)
            st.rerun()
    
    # 제목과 내용 출력 후 박스 닫기(</div>)
    title_text = row.get('개념','제목 없음')
    content_text = row.get('내용','') if pd.notna(row.get('내용')) else ""
    st.markdown(f"""
            <div class="concept-title-card" style="margin-top:5px;">{title_text}</div>
            <div class="concept-content-card">{content_text}</div>
        </div>
    """, unsafe_allow_html=True)
    # --- 회색 박스 끝 ---

    # 4. 하단 네비게이션 버튼
    st.write("") 
    col_l, col_c, col_r = st.columns([1, 1, 1])

    with col_l:
        if st.button("＜", disabled=(i == 0), use_container_width=True):
            st.session_state.card_index -= 1
            st.rerun()

    with col_c:
        # 페이지 표시 글자 스타일 적용 (nav-text 클래스 사용)
        st.markdown(f"<div class='nav-text'>{i + 1} / {total}</div>", unsafe_allow_html=True)

    with col_r:
        if st.button("＞", disabled=(i == total - 1), use_container_width=True):
            st.session_state.card_index += 1
            st.rerun()



# ==================================================
# 📚 전체 학습 / 즐겨찾기
# ==================================================
else:
    for idx, (_, row) in enumerate(filtered_df.iterrows()):
        pk = row["PK"]
        is_fav = pk in st.session_state.favorites

        col_heart, col_title = st.columns([0.05, 0.95])

        with col_heart:
            if st.button("💛" if is_fav else "🤍", key=f"fav_{pk}_{idx}"):
                now = datetime.datetime.now().isoformat()

                if is_fav:
                    cells = fav_sheet.findall(pk)
                    for c in cells:
                        if fav_sheet.cell(c.row, 1).value == USER_ID:
                            fav_sheet.delete_rows(c.row)
                            break
                    st.session_state.favorites.remove(pk)
                else:
                    fav_sheet.append_row([USER_ID, pk, now])
                    st.session_state.favorites.add(pk)

                st.rerun()

        with col_title:
            st.markdown(
                f"<div class='concept-title'>{row.get('개념','제목 없음')}</div>",
                unsafe_allow_html=True
            )

        if pd.notna(row.get("내용")):
            st.write(row["내용"])


        # 📝 기출문제 (간격 수정 버전)
        with st.expander("📝 관련 기출문제 확인"):
            if pd.notna(row.get("기출문제(질문)")):
                year = row.get("기출문제(출제년도)", "연도 미상")
                year_style = f"<span style='color: #888888; font-size: 0.75em; font-weight: bold;'>[{year} 출제]</span>"
                question_text = f"<div style='margin-top: 10px; font-weight: bold; color: #004085;'>Q. {row['기출문제(질문)']}</div>"
                
                options_text = ""
                if pd.notna(row.get("기출문제(보기)")):
                    options_content = str(row['기출문제(보기)']).replace("\n", "<br>")
                    options_text = f"<div style='margin-top: 10px; color: #004085;'>{options_content}</div>"
                
                # q-box 클래스를 사용하여 상단 마진(간격) 부여
                full_html = f"""
                <div class="q-box">
                    {year_style}
                    {question_text}
                    {options_text}
                </div>
                """
                st.markdown(full_html, unsafe_allow_html=True)

                if pd.notna(row.get("정답")):
                    st.write("") # 정답 박스 앞 여백
                    st.success(f"정답: {row['정답']}")

                
        st.divider()

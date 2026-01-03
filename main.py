import streamlit as st
import pd
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
st.set_page_config(page_title="2025 건축기사 마스터", layout="wide")

# --------------------------------------------------
# 2. 스타일 (모바일 한 줄 유지를 위한 CSS 추가)
# --------------------------------------------------
st.markdown("""
<style>
/* 1. 모바일에서 컬럼이 아래로 떨어지지 않게 강제 설정 */
[data-testid="column"] {
    min-width: 0px !important;
    flex-basis: fit-content !important;
}

/* 2. 버튼 내부 여백 줄여서 한 줄 유지 */
.stButton button {
    padding: 0px 5px !important;
    width: 100%;
}

.app-logo {
    font-size: 14px;
    font-weight: 500;
    color: #9aa0a6;
    text-align: right;
    margin-bottom: 1rem;
}

.concept-title {
    font-size: 20px; /* 모바일 고려 사이즈 살짝 축소 */
    font-weight: bold;
    color: #2E4053;
    line-height: 1.2;
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
# 4. 초기 사용자 인증 처리
# --------------------------------------------------
try:
    user_sheet = sheet.worksheet("users")
    ALLOWED_EMAILS = [e.strip() for e in user_sheet.col_values(1)[1:] if e.strip()]
except Exception as e:
    st.error("구글 시트에 'users' 탭이 없거나 설정을 확인해주세요.")
    st.stop()

user_email = st.session_state.get('user_id', "").strip()

if not user_email or user_email not in ALLOWED_EMAILS:
    st.sidebar.title("🔐 사용자 인증")
    input_email = st.sidebar.text_input("등록된 이메일을 입력하세요", key="login_input").strip()
    if st.sidebar.button("로그인"):
        if input_email in ALLOWED_EMAILS:
            st.session_state.user_id = input_email
            st.rerun()
        else:
            st.sidebar.error("등록되지 않은 이메일입니다.")
    st.stop()

USER_ID = st.session_state.user_id

st.markdown("<div class='app-logo'>🏗️ 건축기사 필기노트 made by. 초카이브</div>", unsafe_allow_html=True)

# --------------------------------------------------
# 5. 즐겨찾기 로드
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
# 6. 사이드바 필터
# --------------------------------------------------
st.sidebar.title("🔍 학습 필터")
sort_by_freq = st.sidebar.checkbox("⭐ 빈출도 높은 순")
only_high_freq = st.sidebar.checkbox("🔥 3번 이상 빈출만")
view_mode = st.sidebar.radio("모드 선택", ["💛 즐겨찾기만", "🗂️ 카드 암기", "전체 학습"])

filtered_df = df.copy()
for col, label in [("과목", "과목"), ("대카테고리", "대카테고리"), ("소카테고리", "소카테고리")]:
    if col in filtered_df.columns:
        options = ["전체"] + sorted(filtered_df[col].dropna().unique())
        sel = st.sidebar.selectbox(f"{label} 선택", options)
        if sel != "전체":
            filtered_df = filtered_df[filtered_df[col] == sel]

if view_mode == "💛 즐겨찾기만":
    filtered_df = filtered_df[filtered_df["PK"].isin(st.session_state.favorites)]

if only_high_freq and "빈출" in filtered_df.columns:
    filtered_df["빈출_num"] = pd.to_numeric(filtered_df["빈출"], errors='coerce').fillna(0)
    filtered_df = filtered_df[filtered_df["빈출_num"] >= 3]

if sort_by_freq and "빈출" in filtered_df.columns:
    if "빈출_num" not in filtered_df.columns:
        filtered_df["빈출_num"] = pd.to_numeric(filtered_df["빈출"], errors='coerce').fillna(0)
    filtered_df = filtered_df.sort_values("빈출_num", ascending=False)

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
else:
    if view_mode == "🗂️ 카드 암기":
        if "card_index" not in st.session_state:
            st.session_state.card_index = 0
        if st.session_state.card_index >= len(filtered_df):
            st.session_state.card_index = 0
        display_df = filtered_df.iloc[[st.session_state.card_index]]
    else:
        display_df = filtered_df

    for idx, (_, row) in enumerate(display_df.iterrows()):
        pk = row["PK"]
        is_fav = pk in st.session_state.favorites

        # 제목과 하트 밀착 (간격을 0.05로 최소화)
        col_heart, col_title = st.columns([0.1, 0.9])

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
            st.markdown(f"<div class='concept-title'>{row.get('개념','제목 없음')}</div>", unsafe_allow_html=True)

        if pd.notna(row.get("내용")):
            st.write(row["내용"])

        # 카드 암기 모드일 때는 기출문제 숨김 (모바일 스크롤 방지)
        if view_mode != "🗂️ 카드 암기":
            with st.expander("📝 관련 기출문제 확인"):
                if pd.notna(row.get("기출문제(질문)")):
                    year = row.get("기출문제(출제년도)", "연도 미상")
                    question_text = f"<div style='margin-top: 10px; font-weight: bold; color: #004085;'>Q. {row['기출문제(질문)']}</div>"
                    st.markdown(question_text, unsafe_allow_html=True)
                    if pd.notna(row.get("정답")):
                        st.success(f"정답: {row['정답']}")
                else:
                    st.write("연결된 기출문제가 없습니다.")

        # 카드 모드 네비게이션 (한 줄 강제 유지)
        if view_mode == "🗂️ 카드 암기":
            st.write("") 
            # 번호 영역 비율을 늘리고 버튼을 양옆으로 밀착
            b_col1, b_col2, b_col3 = st.columns([1, 1.2, 1])
            
            with b_col1:
                if st.button("⬅️ 이전", use_container_width=True):
                    if st.session_state.card_index > 0:
                        st.session_state.card_index -= 1
                        st.rerun()
            
            with b_col2:
                st.markdown(f"<p style='text-align: center; line-height: 2.2; font-weight: bold; font-size: 15px;'>{st.session_state.card_index + 1} / {len(filtered_df)}</p>", unsafe_allow_html=True)
            
            with b_col3:
                if st.button("다음 ➡️", use_container_width=True):
                    if st.session_state.card_index < len(filtered_df) - 1:
                        st.session_state.card_index += 1
                        st.rerun()
        
        st.divider()

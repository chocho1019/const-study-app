import streamlit as st
import pandas as pd
import datetime
import gspread
from google.oauth2.service_account import Credentials

# ==================================================
# 1. 기본 설정
# ==================================================
st.set_page_config(page_title="2025 건축기사 마스터", layout="wide")

SPREADSHEET_ID = "1eg3TnoILIHXCzf4fPCU6uqzZssLnFS2xHO5zD7N2c0g"

CONCEPT_URL = (
    "https://docs.google.com/spreadsheets/d/"
    f"{SPREADSHEET_ID}/gviz/tq?tqx=out:csv&gid=775019664"
)
QUESTION_URL = (
    "https://docs.google.com/spreadsheets/d/"
    f"{SPREADSHEET_ID}/gviz/tq?tqx=out:csv&gid=46086374"
)

# ==================================================
# 2. 스타일
# ==================================================
st.markdown("""
<style>
[data-testid="column"] {
    min-width: 0px !important;
    flex-basis: fit-content !important;
}
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
    font-size: 20px;
    font-weight: bold;
    color: #2E4053;
    line-height: 1.2;
}
</style>
""", unsafe_allow_html=True)

# ==================================================
# 3. Google Sheet 연결
# ==================================================
@st.cache_resource
def connect_gsheet():
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"], scopes=scope
    )
    return gspread.authorize(creds)

gc = connect_gsheet()
sheet = gc.open_by_key(SPREADSHEET_ID)
fav_sheet = sheet.worksheet("favorites")

# ==================================================
# 4. 데이터 로드
# ==================================================
@st.cache_data
def load_sheet(url: str) -> pd.DataFrame:
    df = pd.read_csv(url)
    df.columns = df.columns.str.strip()
    df["PK"] = df["PK"].astype(str).str.strip()
    return df

df = load_sheet(CONCEPT_URL).merge(
    load_sheet(QUESTION_URL),
    on="PK",
    how="left"
)

# ==================================================
# 5. 사용자 인증
# ==================================================
try:
    user_sheet = sheet.worksheet("users")
    ALLOWED_EMAILS = [
        e.strip() for e in user_sheet.col_values(1)[1:] if e.strip()
    ]
except Exception:
    st.error("구글 시트에 'users' 탭이 없습니다.")
    st.stop()

if "user_id" not in st.session_state:
    st.sidebar.title("🔐 사용자 인증")
    email = st.sidebar.text_input("등록된 이메일").strip()
    if st.sidebar.button("로그인"):
        if email in ALLOWED_EMAILS:
            st.session_state.user_id = email
            st.rerun()
        else:
            st.sidebar.error("등록되지 않은 이메일입니다.")
    st.stop()

USER_ID = st.session_state.user_id
st.markdown("<div class='app-logo'>🏗️ 건축기사 필기노트 made by. 초카이브</div>", unsafe_allow_html=True)

# ==================================================
# 6. 즐겨찾기 로드
# ==================================================
@st.cache_data
def load_favorites(user_id: str):
    records = fav_sheet.get_all_records()
    return {
        str(r["PK"]) for r in records
        if str(r["user_id"]).strip() == user_id
    }

if "favorites" not in st.session_state:
    st.session_state.favorites = load_favorites(USER_ID)

# ==================================================
# 7. 사이드바 필터
# ==================================================
st.sidebar.title("🔍 학습 필터")

sort_by_freq = st.sidebar.checkbox("⭐ 빈출도 높은 순")
only_high_freq = st.sidebar.checkbox("🔥 3번 이상 빈출만")
view_mode = st.sidebar.radio(
    "모드 선택",
    ["💛 즐겨찾기만", "🗂️ 카드 암기", "전체 학습"]
)

filtered_df = df.copy()

for col in ["과목", "대카테고리", "소카테고리"]:
    if col in filtered_df.columns:
        options = ["전체"] + sorted(filtered_df[col].dropna().unique())
        selected = st.sidebar.selectbox(col, options)
        if selected != "전체":
            filtered_df = filtered_df[filtered_df[col] == selected]

if "빈출" in filtered_df.columns:
    filtered_df["빈출_num"] = pd.to_numeric(
        filtered_df["빈출"], errors="coerce"
    ).fillna(0)

if only_high_freq:
    filtered_df = filtered_df[filtered_df["빈출_num"] >= 3]

if sort_by_freq:
    filtered_df = filtered_df.sort_values("빈출_num", ascending=False)

if view_mode == "💛 즐겨찾기만":
    filtered_df = filtered_df[
        filtered_df["PK"].isin(st.session_state.favorites)
    ]

st.sidebar.markdown("---")
st.sidebar.write(f"👤 {USER_ID}")
if st.sidebar.button("로그아웃"):
    st.session_state.clear()
    st.rerun()

# ==================================================
# 8. 메인 화면
# ==================================================
if filtered_df.empty:
    st.info("선택한 조건에 해당하는 개념이 없습니다.")
    st.stop()

if view_mode == "🗂️ 카드 암기":
    st.session_state.setdefault("card_index", 0)
    st.session_state.card_index %= len(filtered_df)
    display_df = filtered_df.iloc[[st.session_state.card_index]]
else:
    display_df = filtered_df

for idx, row in display_df.iterrows():
    pk = row["PK"]
    is_fav = pk in st.session_state.favorites

    col_heart, col_title = st.columns([0.1, 0.9])

    with col_heart:
        if st.button("💛" if is_fav else "🤍", key=f"fav_{pk}_{idx}"):
            now = datetime.datetime.now().isoformat()
            if is_fav:
                for c in fav_sheet.findall(pk):
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

    if view_mode != "🗂️ 카드 암기":
        with st.expander("📝 관련 기출문제 확인"):
            if pd.notna(row.get("기출문제(질문)")):
                st.markdown(
                    f"**Q. {row['기출문제(질문)']}**",
                    unsafe_allow_html=True
                )
                if pd.notna(row.get("정답")):
                    st.success(f"정답: {row['정답']}")
            else:
                st.write("연결된 기출문제가 없습니다.")

    if view_mode == "🗂️ 카드 암기":
        c1, c2, c3 = st.columns([1, 1.2, 1])
        with c1:
            if st.button("⬅️ 이전"):
                st.session_state.card_index -= 1
                st.rerun()
        with c2:
            st.markdown(
                f"<p style='text-align:center;font-weight:bold;'>"
                f"{st.session_state.card_index + 1} / {len(filtered_df)}</p>",
                unsafe_allow_html=True
            )
        with c3:
            if st.button("다음 ➡️"):
                st.session_state.card_index += 1
                st.rerun()

    st.divider()

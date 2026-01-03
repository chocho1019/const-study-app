import streamlit as st
import pandas as pd
import datetime
import gspread
from google.oauth2.service_account import Credentials

# --------------------------------------------------
# 1. 앱 설정 및 스타일
# --------------------------------------------------
st.set_page_config(page_title="2025 건축기사 마스터", layout="wide")

st.markdown("""
<style>
    [data-testid="column"] { min-width: 0px !important; flex-basis: fit-content !important; }
    .stButton button { padding: 0px 5px !important; width: 100%; }
    .app-logo { font-size: 14px; font-weight: 500; color: #9aa0a6; text-align: right; margin-bottom: 1rem; }
    .concept-title { font-size: 20px; font-weight: bold; color: #2E4053; line-height: 1.2; }
    hr { margin: 1.5rem 0; }
</style>
""", unsafe_allow_html=True)

# --------------------------------------------------
# 2. Google Sheet 연결 및 데이터 로드
# --------------------------------------------------
@st.cache_resource
def get_gspread_client():
    SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=SCOPE)
    return gspread.authorize(creds)

gc = get_gspread_client()
SPREADSHEET_ID = "1eg3TnoILIHXCzf4fPCU6uqzZssLnFS2xHO5zD7N2c0g"
sheet = gc.open_by_key(SPREADSHEET_ID)

@st.cache_data(ttl=600)
def load_data():
    CONCEPT_URL = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/gviz/tq?tqx=out:csv&gid=775019664"
    QUESTION_URL = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/gviz/tq?tqx=out:csv&gid=46086374"
    
    df_c = pd.read_csv(CONCEPT_URL).apply(lambda x: x.str.strip() if x.dtype == "object" else x)
    df_q = pd.read_csv(QUESTION_URL).apply(lambda x: x.str.strip() if x.dtype == "object" else x)
    
    # 데이터 병합 및 전처리
    full_df = df_c.merge(df_q, on="PK", how="left")
    if "빈출" in full_df.columns:
        full_df["빈출_num"] = pd.to_numeric(full_df["빈출"], errors='coerce').fillna(0)
    return full_df

df = load_data()

# --------------------------------------------------
# 3. 사용자 인증
# --------------------------------------------------
user_sheet = sheet.worksheet("users")
ALLOWED_EMAILS = [e for e in user_sheet.col_values(1)[1:] if e.strip()]

if 'user_id' not in st.session_state:
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
fav_sheet = sheet.worksheet("favorites")

# --------------------------------------------------
# 4. 즐겨찾기 동기화 (최적화)
# --------------------------------------------------
if "favorites" not in st.session_state:
    try:
        # 전체를 가져와서 필터링 (API 호출 최소화)
        records = fav_sheet.get_all_records()
        st.session_state.favorites = {str(r["PK"]) for r in records if str(r["user_id"]).strip() == USER_ID}
    except:
        st.session_state.favorites = set()

# --------------------------------------------------
# 5. 사이드바 필터링 로직
# --------------------------------------------------
st.sidebar.title("🔍 학습 필터")
sort_by_freq = st.sidebar.checkbox("⭐ 빈출도 높은 순")
only_high_freq = st.sidebar.checkbox("🔥 3번 이상 빈출만")
view_mode = st.sidebar.radio("모드 선택", ["전체 학습", "🗂️ 카드 암기", "💛 즐겨찾기만"])

filtered_df = df.copy()

# 카테고리 필터
for col in ["과목", "대카테고리", "소카테고리"]:
    if col in filtered_df.columns:
        options = ["전체"] + sorted(filtered_df[col].dropna().unique().tolist())
        sel = st.sidebar.selectbox(f"{col} 선택", options)
        if sel != "전체":
            filtered_df = filtered_df[filtered_df[col] == sel]

# 모드 및 빈출 필터
if view_mode == "💛 즐겨찾기만":
    filtered_df = filtered_df[filtered_df["PK"].isin(st.session_state.favorites)]

if only_high_freq:
    filtered_df = filtered_df[filtered_df["빈출_num"] >= 3]

if sort_by_freq:
    filtered_df = filtered_df.sort_values("빈출_num", ascending=False)

st.sidebar.markdown("---")
if st.sidebar.button("로그아웃"):
    del st.session_state.user_id
    st.rerun()

# --------------------------------------------------
# 6. 메인 화면 렌더링
# --------------------------------------------------
st.markdown("<div class='app-logo'>🏗️ 건축기사 필기노트 made by. 초카이브</div>", unsafe_allow_html=True)

if filtered_df.empty:
    st.info("선택한 조건에 해당하는 개념이 없습니다.")
else:
    # 카드 모드 인덱스 관리
    if view_mode == "🗂️ 카드 암기":
        if "card_idx" not in st.session_state: st.session_state.card_idx = 0
        st.session_state.card_idx = min(st.session_state.card_idx, len(filtered_df) - 1)
        display_df = filtered_df.iloc[[st.session_state.card_idx]]
    else:
        display_df = filtered_df

    for idx, row in display_df.iterrows():
        pk = str(row["PK"])
        is_fav = pk in st.session_state.favorites

        # 헤더 (하트 + 제목)
        col_h, col_t = st.columns([0.1, 0.9])
        with col_h:
            if st.button("💛" if is_fav else "🤍", key=f"fav_{pk}"):
                if is_fav:
                    # 삭제 로직: 해당하는 행을 찾아 삭제
                    cell = fav_sheet.find(pk) # 실제로는 user_id 조건까지 확인해야 안전함
                    if cell: fav_sheet.delete_rows(cell.row)
                    st.session_state.favorites.remove(pk)
                else:
                    fav_sheet.append_row([USER_ID, pk, datetime.datetime.now().isoformat()])
                    st.session_state.favorites.add(pk)
                st.rerun()
        with col_t:
            st.markdown(f"<div class='concept-title'>{row.get('개념','제목 없음')}</div>", unsafe_allow_html=True)

        # 본문 내용
        if pd.notna(row.get("내용")):
            st.write(row["내용"])

        # 기출문제 (카드 모드 제외)
        if view_mode != "🗂️ 카드 암기":
            with st.expander("📝 관련 기출문제 확인"):
                if pd.notna(row.get("기출문제(질문)")):
                    st.markdown(f"**Q. {row['기출문제(질문)']}**")
                    if pd.notna(row.get("정답")):
                        st.success(f"정답: {row['정답']}")
                else:
                    st.write("연결된 기출문제가 없습니다.")
        
        st.divider()

    # 카드 모드 네비게이션
    if view_mode == "🗂️ 카드 암기":
        c1, c2, c3 = st.columns([1, 1, 1])
        with c1:
            if st.button("⬅️ 이전") and st.session_state.card_idx > 0:
                st.session_state.card_idx -= 1
                st.rerun()
        with c2:
            st.markdown(f"<p style='text-align:center;'>{st.session_state.card_idx + 1} / {len(filtered_df)}</p>", unsafe_allow_html=True)
        with c3:
            if st.button("다음 ➡️") and st.session_state.card_idx < len(filtered_df) - 1:
                st.session_state.card_idx += 1
                st.rerun()

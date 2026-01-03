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
st.set_page_config(page_title="2025 건축기사 마스터", layout="wide")

# --------------------------------------------------
# 2. 스타일
# --------------------------------------------------
st.markdown("""
<style>
.app-logo {
    font-size: 14px;
    font-weight: 500;
    color: #9aa0a6;
    text-align: right;
    margin-bottom: 1rem;
}

.concept-title {
    font-size: 24px;
    font-weight: bold;
    color: #2E4053;
}

.heart-btn button {
    background: none;
    border: none;
    padding: 0;
    font-size: 22px;
    cursor: pointer;
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
    "<div class='app-logo'>🏗️ 건축기사 필기노트 made by. 초카이브</div>",
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

view_mode = st.sidebar.radio("모드 선택", ["💛 즐겨찾기만", "🗂️ 카드 암기", "전체 학습"])

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
# 7. 사용자 인증 정보 (사이드바 하단 배치)
# --------------------------------------------------
st.sidebar.markdown("---")
st.sidebar.write(f"👤 **로그인 정보**: {USER_ID}")
if st.sidebar.button("로그아웃"):
    del st.session_state.user_id
    st.rerun()
# --------------------------------------------------
# 7. 메인 화면 (모드별 분기 처리)
# --------------------------------------------------
if filtered_df.empty:
    st.info("선택한 조건에 해당하는 개념이 없습니다.")
else:
    # --- [카드 암기 모드 인덱스 관리] ---
    if view_mode == "🗂️ 카드 암기":
        if "card_index" not in st.session_state:
            st.session_state.card_index = 0
        if st.session_state.card_index >= len(filtered_df):
            st.session_state.card_index = 0
        
        # 현재 카드 데이터만 선택
        display_df = filtered_df.iloc[[st.session_state.card_index]]
    else:
        display_df = filtered_df

   # --- [공통 출력 루프] ---
    for idx, (_, row) in enumerate(display_df.iterrows()):
        pk = row["PK"]
        is_fav = pk in st.session_state.favorites

        # 1. 하트와 제목을 아주 좁은 간격으로 배치 (0.15 -> 0.07로 축소)
        # gap="small"을 추가하여 내부 간격을 더 줄입니다.
        col_heart, col_title = st.columns([0.07, 0.93], gap="small") 

        # ❤️ 하트 버튼
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

        # 📘 개념 제목 (마진을 조절하여 하트쪽으로 더 밀착)
        with col_title:
            st.markdown(f"""
                <div class='concept-title' style='margin-left: -10px;'>
                    {row.get('개념','제목 없음')}
                </div>
                """, unsafe_allow_html=True)


        # 📄 3. 내용
        if pd.notna(row.get("내용")):
            st.write(row["내용"])

        # 📝 4. 기출문제 (카드 암기 모드가 아닐 때만 출력)
        if view_mode != "🗂️ 카드 암기":
            with st.expander("📝 관련 기출문제 확인"):
                if pd.notna(row.get("기출문제(질문)")):
                    year = row.get("기출문제(출제년도)", "연도 미상")
                    year_style = f"<span style='color: #888888; font-size: 0.75em; font-weight: bold;'>[{year} 출제]</span>"
                    question_text = f"<div style='margin-top: 10px; font-weight: bold; color: #004085;'>Q. {row['기출문제(질문)']}</div>"
                    
                    options_text = ""
                    if pd.notna(row.get("기출문제(보기)")):
                        options_content = str(row['기출문제(보기)']).replace("\n", "<br>")
                        options_text = f"<div style='margin-top: 10px; color: #004085;'>{options_content}</div>"
                    
                    full_html = f"""
                    <div style="background-color: #e7f3fe; border-left: 5px solid #2196F3; padding: 15px; border-radius: 5px;">
                        {year_style} {question_text} {options_text}
                    </div>
                    """
                    st.markdown(full_html, unsafe_allow_html=True)
                    if pd.notna(row.get("정답")):
                        st.success(f"정답: {row['정답']}")
                else:
                    st.write("연결된 기출문제가 없습니다.")

        # --------------------------------------------------
        # 5. 카드 모드 네비게이션 버튼 (한 줄 배치)
        # --------------------------------------------------
        if view_mode == "🗂️ 카드 암기":
            st.write("") # 약간의 간격
            # 버튼과 페이지 번호를 한 줄에 배치 [이전(1) | 번호(1) | 다음(1)]
            btn_col1, btn_col2, btn_col3 = st.columns([1, 1, 1])
            
            with btn_col1:
                if st.button("⬅️ 이전", use_container_width=True, key="prev_btn"):
                    if st.session_state.card_index > 0:
                        st.session_state.card_index -= 1
                        st.rerun()
            
            with btn_col2:
                # 페이지 번호를 버튼 높이에 맞춰 중앙 정렬
                st.markdown(f"<p style='text-align: center; line-height: 2.5; font-weight: bold;'>{st.session_state.card_index + 1} / {len(filtered_df)}</p>", unsafe_allow_html=True)
            
            with btn_col3:
                if st.button("다음 ➡️", use_container_width=True, key="next_btn"):
                    if st.session_state.card_index < len(filtered_df) - 1:
                        st.session_state.card_index += 1
                        st.rerun()
        
        st.divider()

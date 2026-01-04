
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

/* 상단 로고 스타일 수정 */
.app-logo {
    font-size: 12px;         
    font-weight: 300;         
    color: #a8b3b4;          
    text-align: right;
    margin-bottom: 0.5rem;
}

/* 카테고리 경로 스타일 수정 */
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
# 🃏 암기카드 모드 (카테고리 표시 + 클릭 필터 추가)
# ==================================================
elif view_mode == "🃏 암기카드":
    total = len(filtered_df)
    i = st.session_state.card_index
    row = filtered_df.iloc[i]
    pk = row["PK"]
    is_fav = pk in st.session_state.favorites

    # 1. 최상단: 카테고리 정보 표시
    cat_text = f"{row.get('과목','')} / {row.get('대카테고리','')} / {row.get('소카테고리','')}"
    st.markdown(f"<div class='concept-category'>{cat_text}</div>", unsafe_allow_html=True)

    # 2. 즐겨찾기 버튼
    col_h, _ = st.columns([0.1, 0.9])
    with col_h:
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

    # 3. 개념 박스 (글머리 기호 및 줄 간격 수정 적용)
    title_text = row.get('개념','제목 없음')
    content_raw = row.get('내용','') if pd.notna(row.get('내용')) else ""
    
    content_html = ""
    if content_raw:
        lines = str(content_raw).split('\n')
        content_html = "<ul style='padding-left: 20px; margin-top: 0; color: #333;'>"
        for line in lines:
            if line.strip():
                # 수정된 부분: f 다음에 따옴표 추가
                content_html += f"<li style='margin-bottom: 2px; line-height: 1.4;'>{line.strip()}</li>"
        content_html += "</ul>"

    card_html = f"""
    <div class="concept-card">
        <div class="concept-title-card">{title_text}</div>
        <div class="concept-content-card">{content_html}</div>
    </div>
    """
    st.markdown(card_html, unsafe_allow_html=True)
    
    # 4. 하단 네비게이션 버튼
    st.write("") 
    col_l, col_c, col_r = st.columns([1, 1, 1])
    with col_l:
        if st.button("＜", disabled=(i == 0), use_container_width=True):
            st.session_state.card_index -= 1
            st.rerun()
    with col_c:
        st.markdown(f"<p style='text-align: center; line-height: 2.4; font-weight: bold; font-size: 16px; color: #D3D3D3;'>{i + 1} / {total}</p>", unsafe_allow_html=True)
    with col_r:
        if st.button("＞", disabled=(i == total - 1), use_container_width=True):
            st.session_state.card_index += 1
            st.rerun()

# ==================================================
# 📚 전체 학습 / 즐겨찾기
# ==================================================
else:
    grouped_df = filtered_df.groupby("PK", sort=False)

    for pk, group in grouped_df:
        row = group.iloc[0]
        is_fav = pk in st.session_state.favorites

        col_heart, col_title = st.columns([0.05, 0.95])
        with col_heart:
            if st.button("💛" if is_fav else "🤍", key=f"fav_list_{pk}"):
                now = datetime.datetime.now().isoformat()
                if is_fav:
                    cells = fav_sheet.findall(str(pk))
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

        
        # --- 개념 내용 출력 (글머리 기호 및 줄 간격 수정) ---
        if pd.notna(row.get("내용")):
            content_raw = str(row["내용"])
            lines = content_raw.split('\n')
            
            html_content = "<ul style='padding-left: 20px; margin-bottom: 0; color: #333;'>"
            for line in lines:
                if line.strip():
                    # 수정된 부분: f 다음에 따옴표 추가
                    html_content += f"<li style='margin-bottom: 2px; line-height: 1.4;'>{line.strip()}</li>"
            html_content += "</ul>"
            st.markdown(html_content, unsafe_allow_html=True)

        
        # --- 개념 내용 출력 아래에 추가 ---
        if pd.notna(row.get("이미지URL")) and str(row["이미지URL"]).strip():
            # URL이 "http"로 시작하는지 확인 후 이미지 출력
            image_url = str(row["이미지URL"]).strip()
            if image_url.startswith("http"):
                st.image(image_url, use_container_width=True)


        # --- 📝 기출문제 영역 --- 
        has_question = group['기출문제(질문)'].notna().any()
        if has_question:
            # 이 줄을 추가하여 개념 내용과 기출문제 토글 사이 간격을 띄웁니다.
            st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
            with st.expander(f"📝 관련 기출문제 ({len(group)}건)"):
                for _, q_row in group.iterrows():
                    if pd.notna(q_row.get("기출문제(질문)")):
                        year = q_row.get("기출문제(출제년도)", "연도 미상")
                        year_style = f"<span style='color: #888888; font-size: 0.75em; font-weight: bold;'>[{year} 출제]</span>"
                        question_text = f"<div style='margin-top: 5px; font-weight: bold; color: #004085;'>Q. {q_row['기출문제(질문)']}</div>"
                        
                        options_text = ""
                        if pd.notna(q_row.get("기출문제(보기)")):
                            options_content = str(q_row['기출문제(보기)']).replace("\n", "<br>")
                            options_text = f"<div style='margin-top: 5px; color: #333; font-size: 0.95em;'>{options_content}</div>"
                        
                        answer_html = ""
                        if pd.notna(q_row.get("정답")):
                            answer_html = f"<div style='margin-top: 8px; color: #155724; background-color: #d4edda; padding: 5px 10px; border-radius: 4px; font-size: 0.9em;'>✅ 정답: {q_row['정답']}</div>"

                        full_html = f"""
                        <div style="background-color: #f1f8ff; padding: 15px; border-radius: 8px; margin-bottom: 10px; border: 1px solid #cce5ff;">
                            {year_style}
                            {question_text}
                            {options_text}
                            {answer_html}
                        </div>
                        """
                        st.markdown(full_html, unsafe_allow_html=True)
        st.divider()

# --------------------------------------------------
# 8. 하단 로고
# --------------------------------------------------
st.write("") 
st.markdown("<div class='app-logo'>ⓒ초카이브 건축기사</div>", unsafe_allow_html=True)

import streamlit as st
import pandas as pd
import uuid
import datetime
import gspread
import re
from google.oauth2.service_account import Credentials

# --------------------------------------------------
# 1. 앱 설정 및 스타일 (사용자 지정 스타일 유지)
# --------------------------------------------------
st.set_page_config(page_title="2026 건축기사 필기 (초카이브)", layout="wide")

st.markdown("""
<style>
.concept-card { background-color: #f8f9fa; padding: 20px; border-radius: 12px; border: 1px solid #eee; margin-bottom: 20px; }
.title-row { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; border-bottom: 2px solid #eaeaea; padding-bottom: 8px; }
.concept-title-text { font-size: 20px; font-weight: bold; color: #2E4053; }
.freq-badge { border: 1px solid #bbb; color: #777; border-radius: 4px; padding: 2px 8px; font-size: 13px; font-weight: 500; white-space: nowrap; }
/* 하트 버튼 스타일 */
.stButton > button { background-color: transparent !important; border: none !important; padding: 0 !important; font-size: 22px !important; line-height: 1 !important; box-shadow: none !important; }
.q-box { background-color: #f1f8ff; padding: 15px; border-radius: 8px; margin-bottom: 10px; border: 1px solid #cce5ff; }
.app-logo { font-size: 12px; font-weight: 300; color: #a8b3b4; text-align: right; }
</style>
""", unsafe_allow_html=True)

# --------------------------------------------------
# 2. Google Sheet 연결 및 데이터 로드
# --------------------------------------------------
SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
SPREADSHEET_ID = "1eg3TnoILIHXCzf4fPCU6uqzZssLnFS2xHO5zD7N2c0g"

@st.cache_resource
def get_gspread_client():
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=SCOPE)
    return gspread.authorize(creds)

gc = get_gspread_client()
doc = gc.open_by_key(SPREADSHEET_ID)
fav_sheet = doc.worksheet("favorites")
user_sheet = doc.worksheet("users")

@st.cache_data
def load_data():
    # 개념 데이터와 문제 데이터 시트 gid를 이용해 직접 로드 (기존 URL 방식 유지)
    CONCEPT_URL = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/gviz/tq?tqx=out:csv&gid=775019664"
    QUESTION_URL = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/gviz/tq?tqx=out:csv&gid=46086374"
    
    df_c = pd.read_csv(CONCEPT_URL).apply(lambda x: x.str.strip() if x.dtype == "object" else x)
    df_q = pd.read_csv(QUESTION_URL).apply(lambda x: x.str.strip() if x.dtype == "object" else x)
    
    # 열 이름 공백 제거
    df_c.columns = df_c.columns.str.strip()
    df_q.columns = df_q.columns.str.strip()
    
    # PK 기준 병합
    return df_c.merge(df_q, on="PK", how="left")

df = load_data()

# --------------------------------------------------
# 3. 사용자 인증 및 즐겨찾기 세션 관리
# --------------------------------------------------
ALLOWED_EMAILS = [e.strip() for e in user_sheet.col_values(1)[1:] if e.strip()]
user_email = st.session_state.get('user_id', "").strip()

if not user_email or user_email not in ALLOWED_EMAILS:
    st.sidebar.title("🔐 로그인")
    input_email = st.sidebar.text_input("이메일 입력").strip()
    if st.sidebar.button("로그인"):
        if input_email in ALLOWED_EMAILS:
            st.session_state.user_id = input_email
            st.rerun()
    st.stop()

USER_ID = st.session_state.user_id

if "favorites" not in st.session_state or st.session_state.get('last_user') != USER_ID:
    try:
        records = fav_sheet.get_all_records()
        st.session_state.favorites = {str(r["PK"]) for r in records if str(r["user_id"]).strip() == USER_ID}
        st.session_state.last_user = USER_ID
    except: st.session_state.favorites = set()

def toggle_fav(pk):
    pk_str = str(pk)
    if pk_str in st.session_state.favorites:
        st.session_state.favorites.remove(pk_str)
        try:
            cells = fav_sheet.findall(pk_str, in_column=2)
            for c in cells:
                if str(fav_sheet.cell(c.row, 1).value) == USER_ID:
                    fav_sheet.delete_rows(c.row)
                    break
        except: pass
    else:
        st.session_state.favorites.add(pk_str)
        fav_sheet.append_row([USER_ID, pk_str, datetime.datetime.now().isoformat()])

# --------------------------------------------------
# 4. 필터 및 렌더링 함수 (핵심 수정 부분)
# --------------------------------------------------
st.sidebar.title("🔍 필터")
view_mode = st.sidebar.radio("모드 선택", ["전체 학습", "🃏 암기카드", "💛 즐겨찾기만"])
filtered_df = df.copy()

if view_mode == "💛 즐겨찾기만":
    filtered_df = filtered_df[filtered_df["PK"].astype(str).isin(st.session_state.favorites)]

# 렌더링 함수
def render_unit(row, pk_val, group):
    # 상단 헤더 (제목 + 빈출배지 + 하트)
    col1, col2 = st.columns([0.8, 0.2])
    with col1:
        st.markdown(f"<div class='concept-title-text'>{row.get('개념','제목 없음')}</div>", unsafe_allow_html=True)
    with col2:
        m1, m2 = st.columns([1, 1])
        freq = str(row.get('빈출', '0'))
        with m1:
            if freq != '0': st.markdown(f"<div class='freq-badge'>{freq}회</div>", unsafe_allow_html=True)
        with m2:
            is_fav = str(pk_val) in st.session_state.favorites
            if st.button("💛" if is_fav else "🤍", key=f"fav_{pk_val}_{row.name}"):
                toggle_fav(pk_val)
                st.rerun()
    
    # 내용 출력
    content = str(row.get('내용', ''))
    if content:
        st.markdown(f"<div style='margin-top:10px; line-height:1.6;'>{content}</div>", unsafe_allow_html=True)

    # 기출문제 출력 (KeyError 방지 로직)
    # 시트의 실제 열 이름이 '기출문제(질문)' 인지 확인 후 처리
    q_col = '기출문제(질문)' 
    if q_col in group.columns and group[q_col].notna().any():
        with st.expander(f"📝 관련 기출문제 ({len(group[group[q_col].notna()])}건)"):
            for _, q in group.iterrows():
                if pd.notna(q.get(q_col)):
                    st.markdown(f"""
                    <div class="q-box">
                        <small style='color:#888;'>[{q.get('기출문제(출제년도)','연도미상')}]</small><br>
                        <b>Q. {q[q_col]}</b><br>
                        <div style='margin-top:5px;'>{str(q.get('기출문제(보기)','')).replace('\\n','<br>')}</div>
                        <div style='margin-top:8px; color:green;'>✅ 정답: {q.get('정답','')}</div>
                    </div>
                    """, unsafe_allow_html=True)

# --------------------------------------------------
# 5. 모드별 실행
# --------------------------------------------------
if filtered_df.empty:
    st.info("데이터가 없습니다.")
elif view_mode == "🃏 암기카드":
    if "c_idx" not in st.session_state: st.session_state.c_idx = 0
    pk_list = filtered_df["PK"].unique().tolist()
    idx = st.session_state.c_idx % len(pk_list)
    pk = pk_list[idx]
    group = filtered_df[filtered_df["PK"] == pk]
    render_unit(group.iloc[0], pk, group)
    
    # 네비게이션
    c1, c2, c3 = st.columns([1,2,1])
    if c1.button("⬅️ 이전"): st.session_state.c_idx -= 1; st.rerun()
    c2.write(f"**{idx+1} / {len(pk_list)}**")
    if c3.button("다음 ➡️"): st.session_state.c_idx += 1; st.rerun()
else:
    for pk, group in filtered_df.groupby("PK", sort=False):
        render_unit(group.iloc[0], pk, group)
        st.divider()

st.markdown("<div class='app-logo'>ⓒ초카이브 건축기사</div>", unsafe_allow_html=True)

import streamlit as st
import pandas as pd
import uuid
import datetime
import gspread
import re
from google.oauth2.service_account import Credentials

# --------------------------------------------------
# 이미지 URL 변환 함수
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
# 2. 스타일 (기존 스타일 유지 및 보완)
# --------------------------------------------------
st.markdown("""
# [수정] 2. 스타일 부분에 아래 내용 추가/교체
st.markdown("""
<style>
/* 기존 스타일 유지 */
.concept-card { background-color: #f8f9fa; padding: 20px; border-radius: 12px; border: 1px solid #eee; margin-bottom: 20px; }
.title-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 10px;
    border-bottom: 2px solid #eaeaea; 
    padding-bottom: 8px;
    gap: 10px; /* 배지와 버튼 사이 간격 */
}
.concept-title-text {
    font-size: 20px;
    font-weight: bold;
    color: #2E4053;
    flex-grow: 1; /* 제목이 공간을 채우도록 */
}
.right-meta {
    display: flex;
    align-items: center;
    gap: 8px;
}
.freq-badge {
    border: 1px solid #bbb;     
    color: #777;                
    border-radius: 4px;
    padding: 2px 8px;
    font-size: 13px;
    font-weight: 500;
    white-space: nowrap;        
}
/* 즐겨찾기 버튼 전용 스타일 */
.stButton > button[kind="secondary"] {
    padding: 2px 10px !important;
    height: auto !important;
    width: auto !important;
    font-size: 18px !important;
    background-color: transparent !important;
    border: none !important;
    box-shadow: none !important;
}
/* 나머지 기존 스타일... (생략 방지를 위해 핵심만 표기) */
.text-line { margin-bottom: 4px; padding-left: 1.5em; text-indent: -1.0em; line-height: 1.6; word-break: keep-all; }
/* ... (이하 동일) ... */
</style>
""", unsafe_allow_html=True)

# --------------------------------------------------
# [신규 추가] 즐겨찾기 토글 함수
# --------------------------------------------------
def toggle_favorite(pk_val):
    pk_val = str(pk_val)
    if pk_val in st.session_state.favorites:
        # 삭제
        st.session_state.favorites.remove(pk_val)
        try:
            cell = fav_sheet.find(pk_val, in_column=2) # PK가 2번째 열이라고 가정
            if cell:
                # 해당 유저의 데이터인지 확인 후 삭제 로직 필요 (단순화를 위해 전체 행 삭제 예시)
                records = fav_sheet.get_all_records()
                for idx, r in enumerate(records):
                    if str(r["PK"]) == pk_val and str(r["user_id"]) == USER_ID:
                        fav_sheet.delete_rows(idx + 2)
                        break
        except: pass
    else:
        # 추가
        st.session_state.favorites.add(pk_val)
        try:
            fav_sheet.append_row([USER_ID, pk_val, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
        except: pass

# --------------------------------------------------
# 7. 렌더링 함수 (수정본)
# --------------------------------------------------
if filtered_df.empty:
    st.info("선택한 조건에 해당하는 개념이 없습니다.")
else:
    grouped = filtered_df.groupby("PK", sort=False)
    pk_list = list(grouped.groups.keys())

    def render_concept_block(row, pk_val):
        pk_val = str(pk_val)
        num_val = str(row.get('숫구', '')).strip().replace(".0", "") or pk_val
        freq_val = str(row.get('개념빈출_J', '')).strip()
        
        # 제목 행 레이아웃 (제목 | 배지 + 하트버튼)
        col1, col2 = st.columns([0.85, 0.15])
        
        with col1:
            clean_gubun = row.get('구분','').replace('\n', ' ')
            st.markdown(f"<div class='concept-title-text'>{num_val}) {clean_gubun}</div>", unsafe_allow_html=True)
        
        with col2:
            # 배지와 버튼을 한 줄에 배치하기 위해 컨테이너 사용
            is_fav = pk_val in st.session_state.favorites
            heart_icon = "💛" if is_fav else "🤍"
            
            # CSS로 정렬하기 힘든 streamlit 버튼 특성상 columns를 한 번 더 쪼개거나 
            # 아래와 같이 배치
            m_col1, m_col2 = st.columns([1, 1])
            with m_col1:
                if freq_val != "0":
                    st.markdown(f"<div class='freq-badge'>{freq_val}회</div>", unsafe_allow_html=True)
            with m_col2:
                if st.button(heart_icon, key=f"fav_{pk_val}_{row.name}"):
                    toggle_favorite(pk_val)
                    st.rerun()

        st.markdown("<div style='border-bottom: 2px solid #eaeaea; margin-bottom: 10px;'></div>", unsafe_allow_html=True)
        
        concept_raw = str(row.get('개념', ''))
        st.markdown(format_smart_text(concept_raw), unsafe_allow_html=True)

        concept_img_url = get_direct_url(row.get('개념이미지_I', ''))
        if concept_img_url:
            st.image(concept_img_url, use_container_width=False, width=500)

    # ... (render_questions 함수는 기존과 동일) ...

    # --------------------------------------------------
    # 뷰 모드 실행
    # --------------------------------------------------
    if view_mode == "🃏 암기카드":
        # ... (기존 암기카드 로직 동일, render_concept_block 내부에서 버튼이 생김) ...
        if "card_idx" not in st.session_state: st.session_state.card_idx = 0
        if st.session_state.card_idx >= len(pk_list): st.session_state.card_idx = 0

        pk = pk_list[st.session_state.card_idx]
        group = grouped.get_group(pk)
        row = group.iloc[0]
        st.markdown(f"<div class='concept-category'>{row.get('과목','')} / {row.get('대카테고리','')}</div>", unsafe_allow_html=True)
        
        with st.container(border=True):
            render_concept_block(row, pk)
        
        render_questions(group[group['문제'].str.strip() != ""])
        # ... (이하 이전/다음 버튼 로직 동일) ...
        
    else: # 전체 학습 및 즐겨찾기 모드
        for pk, group in grouped:
            row = group.iloc[0]
            with st.container():
                render_concept_block(row, pk)
                render_questions(group[group['문제'].str.strip() != ""])
            st.divider()

st.markdown("<div class='app-logo'>ⓒ초카이브 건축기사</div>", unsafe_allow_html=True)

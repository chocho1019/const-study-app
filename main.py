import streamlit as st
import pandas as pd

# 1. 앱 설정
st.set_page_config(page_title="2025 건축기사 마스터", layout="wide")

# 2. 스타일 설정
st.markdown("""
    <style>
    .concept-title { font-size: 24px; font-weight: bold; color: #2E4053; }
    hr { margin: 1.5rem 0; }
    .stExpander { border: 1px solid #f0f2f6; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

# 3. 데이터 로드 함수 (기존 구조 유지)
@st.cache_data
def load_full_data():
    base_url = "https://docs.google.com/spreadsheets/d/1eg3TnoILIHXCzf4fPCU6uqzZssLnFS2xHO5zD7N2c0g/export?format=csv"
    
    # 개념 시트와 기출문제 시트 개별 로드
    concept_df = pd.read_csv(f"{base_url}&gid=0") 
    quiz_df = pd.read_csv(f"{base_url}&gid=46086374")
    
    # 공백 제거
    concept_df.columns = [c.strip() for c in concept_df.columns]
    quiz_df.columns = [c.strip() for c in quiz_df.columns]
    
    return concept_df, quiz_df

concept_df, quiz_df = load_full_data()

if concept_df is not None:
    if 'favorites' not in st.session_state:
        st.session_state.favorites = set()

    # --- 사이드바 필터 ---
    st.sidebar.title("🔍 필터")
    view_mode = st.sidebar.radio("모드", ["전체 학습", "💛 즐겨찾기"])
    
    f_df = concept_df.copy()
    
    # 위계별 필터링
    subjects = ["전체"] + sorted(f_df['과목'].dropna().unique().tolist())
    sel_sub = st.sidebar.selectbox("과목", subjects)
    if sel_sub != "전체": f_df = f_df[f_df['과목'] == sel_sub]
    
    majors = ["전체"] + sorted(f_df['대카테고리'].dropna().unique().tolist())
    sel_major = st.sidebar.selectbox("대카테고리", majors)
    if sel_major != "전체": f_df = f_df[f_df['대카테고리'] == sel_major]
    
    minors = ["전체"] + sorted(f_df['소카테고리'].dropna().unique().tolist())
    sel_minor = st.sidebar.selectbox("소카테고리", minors)
    if sel_minor != "전체": f_df = f_df[f_df['소카테고리'] == sel_minor]

    if view_mode == "💛 즐겨찾기":
        f_df = f_df[f_df['PK'].astype(str).isin(st.session_state.favorites)]

    # --- 메인 화면 ---
    st.title("🏗️ 건축기사 필기 요약노트")
    
    for _, row in f_df.iterrows():
        # PK-FK 매칭을 위해 문자열로 변환 (오류 방지 핵심)
        pk_val = str(row['PK'])
        
        # 제목 및 즐겨찾기
        c1, c2 = st.columns([0.9, 0.1])
        with c1:
            st.markdown(f"<div class='concept-title'>{row['개념']}</div>", unsafe_allow_html=True)
        with c2:
            is_fav = pk_val in st.session_state.favorites
            if st.button("💛" if is_fav else "🤍", key=f"f_{pk_val}"):
                if is_fav: st.session_state.favorites.remove(pk_val)
                else: st.session_state.favorites.add(pk_val)
                st.rerun()
        
        # 내용
        st.write(row['내용'])
        
        # 이미지 (URL이 있는 경우만)
        if '이미지' in row and pd.notna(row['이미지']):
            st.image(row['이미지'], use_container_width=True)
            
        # 🌟 기출문제 연동 (요청하신 3가지 항목만 표시)
        with st.expander("📝 해당 기출문제 확인"):
            # 매칭을 위해 quiz_df의 FK도 문자열로 변환하여 비교
            matched_quiz = quiz_df[quiz_df['FK'].astype(str) == pk_val]
            
            if not matched_quiz.empty:
                for i, q_row in matched_quiz.iterrows():
                    # 1. 기출문제(출제년도)
                    st.markdown(f"**📅 출제년도: {q_row.get('기출문제(출제년도)', '정보없음')}**")
                    # 2. 기출문제(질문)
                    st.info(f"❓ {q_row.get('기출문제(질문)', '질문이 없습니다.')}")
                    # 3. 기출문제(보기)
                    st.write(f"📋 {q_row.get('기출문제(보기)', '보기가 없습니다.')}")
                    
                    # 문제 사이 구분선
                    if i < matched_quiz.index[-1]:
                        st.markdown("---")
            else:
                st.write("✅ 연결된 기출문제가 없습니다.")
        
        st.divider()

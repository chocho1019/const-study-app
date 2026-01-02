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

# 3. 데이터 로드 함수 (가장 안정적인 주소 방식 사용)
@st.cache_data
def load_full_data():
    SHEET_ID = "1eg3TnoILIHXCzf4fPCU6uqzZssLnFS2xHO5zD7N2c0g"
    # export?format=csv&gid=... 형식이 가장 에러가 적습니다.
    concept_url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid=0"
    quiz_url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid=46086374"
    
    concept_df = pd.read_csv(concept_url)
    quiz_df = pd.read_csv(quiz_url)
    
    # 공백 제거 및 PK/FK 타입 통일
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
    
    # 과목/대/소 카테고리 필터링
    for col in ['과목', '대카테고리', '소카테고리']:
        if col in f_df.columns:
            options = ["전체"] + sorted(f_df[col].dropna().unique().tolist())
            sel = st.sidebar.selectbox(f"{col} 선택", options)
            if sel != "전체":
                f_df = f_df[f_df[col] == sel]

    if view_mode == "💛 즐겨찾기":
        f_df = f_df[f_df['PK'].astype(str).isin(st.session_state.favorites)]

    # --- 메인 화면 ---
    st.title("🏗️ 건축기사 필기 요약노트")
    
    for _, row in f_df.iterrows():
        pk_val = str(row['PK']) # 매칭을 위해 문자열로 변환
        
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
        
        # 내용 및 이미지
        st.write(row['내용'])
        if '이미지' in row and pd.notna(row['이미지']) and str(row['이미지']).startswith('http'):
            st.image(row['이미지'], use_container_width=True)
            
        # 🌟 기출문제 연동 (요청하신 3가지 항목만 표시)
        with st.expander("📝 해당 기출문제 확인"):
            # quiz_df의 FK와 concept_df의 PK를 비교
            matched_quiz = quiz_df[quiz_df['FK'].astype(str) == pk_val]
            
            if not matched_quiz.empty:
                for q_idx, q_row in matched_quiz.iterrows():
                    # 1. 출제년도
                    st.markdown(f"**📅 출제년도: {q_row.get('기출문제(출제년도)', '정보없음')}**")
                    # 2. 질문
                    st.info(f"❓ {q_row.get('기출문제(질문)', '질문 정보가 없습니다.')}")
                    # 3. 보기
                    st.write(f"📋 {q_row.get('기출문제(보기)', '보기가 없습니다.')}")
                    
                    # 문제 사이 구분선
                    if q_idx < matched_quiz.index[-1]:
                        st.markdown("---")
            else:
                st.write("✅ 연결된 기출문제가 없습니다.")
        
        st.divider()

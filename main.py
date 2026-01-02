import streamlit as st
import pandas as pd

# 1. 앱 페이지 설정
st.set_page_config(page_title="2025 건축기사 마스터", layout="wide")

# 2. CSS 스타일 적용 (가독성 향상)
st.markdown("""
    <style>
    .concept-title { font-size: 26px; font-weight: bold; color: #1E3A5F; margin-bottom: 5px; }
    .stExpander { border: 1px solid #D1D5DB; border-radius: 8px; background-color: #F9FAFB; }
    hr { margin: 2rem 0; }
    </style>
    """, unsafe_allow_html=True)

# 3. 데이터 로드 함수 (가장 안정적인 GID 개별 호출 방식)
@st.cache_data
def load_all_data():
    SHEET_ID = "1eg3TnoILIHXCzf4fPCU6uqzZssLnFS2xHO5zD7N2c0g"
    # 개념 시트 (gid=0) 및 기출문제 시트 (gid=46086374) 주소
    concept_url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid=0"
    quiz_url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid=46086374"
    
    try:
        c_df = pd.read_csv(concept_url)
        q_df = pd.read_csv(quiz_url)
        
        # 모든 컬럼명의 앞뒤 공백을 제거하여 키 에러 방지
        c_df.columns = [col.strip() for col in c_df.columns]
        q_df.columns = [col.strip() for col in q_df.columns]
        
        return c_df, q_df
    except Exception as e:
        st.error(f"데이터를 불러오는 중 오류가 발생했습니다: {e}")
        return None, None

concept_df, quiz_df = load_all_data()

# 4. 앱 로직 시작
if concept_df is not None and quiz_df is not None:
    # 즐겨찾기 세션 상태 초기화
    if 'favorites' not in st.session_state:
        st.session_state.favorites = set()

    # --- 사이드바 필터 구성 ---
    st.sidebar.title("🛠️ 필터 설정")
    view_mode = st.sidebar.radio("모드 선택", ["📖 전체 학습", "💛 즐겨찾기"])
    
    # 위계별 필터링 (과목 -> 대카테고리 -> 소카테고리)
    f_df = concept_df.copy()
    
    # 과목 필터
    if '과목' in f_df.columns:
        subjects = ["전체"] + sorted(f_df['과목'].dropna().unique().tolist())
        sel_sub = st.sidebar.selectbox("1. 과목", subjects)
        if sel_sub != "전체":
            f_df = f_df[f_df['과목'] == sel_sub]

    # 대카테고리 필터
    if '대카테고리' in f_df.columns:
        majors = ["전체"] + sorted(f_df['대카테고리'].dropna().unique().tolist())
        sel_major = st.sidebar.selectbox("2. 대카테고리", majors)
        if sel_major != "전체":
            f_df = f_df[f_df['대카테고리'] == sel_major]

    # 소카테고리 필터
    if '소카테고리' in f_df.columns:
        minors = ["전체"] + sorted(f_df['소카테고리'].dropna().unique().tolist())
        sel_minor = st.sidebar.selectbox("3. 소카테고리", minors)
        if sel_minor != "전체":
            f_df = f_df[f_df['소카테고리'] == sel_minor]

    # 즐겨찾기 모드 필터링
    if view_mode == "💛 즐겨찾기":
        f_df = f_df[f_df['PK'].astype(str).isin(st.session_state.favorites)]

    # --- 메인 화면 출력 ---
    st.title("🏗️ 건축기사 필기 요약노트")
    st.caption("과목별 핵심 개념과 기출문제를 한눈에 정리합니다.")
    
    if f_df.empty:
        st.warning("표시할 데이터가 없습니다. 필터를 조정해 주세요.")
    else:
        for _, row in f_df.iterrows():
            # PK 값을 문자열로 통일 (매칭 정확도 확보)
            current_pk = str(row['PK'])
            
            # 개념 상단 (제목 + 즐겨찾기 버튼)
            t_col, f_col = st.columns([0.85, 0.15])
            with t_col:
                st.markdown(f"<div class='concept-title'>{row['개념']}</div>", unsafe_allow_html=True)
            with f_col:
                is_fav = current_pk in st.session_state.favorites
                if st.button("💛" if is_fav else "🤍", key=f"fav_{current_pk}"):
                    if is_fav: st.session_state.favorites.remove(current_pk)
                    else: st.session_state.favorites.add(current_pk)
                    st.rerun()
            
            # 개념 내용
            st.write(row['내용'])
            
            # 이미지 (데이터가 있고 http로 시작하는 경우만)
            if '이미지' in row and pd.notna(row['이미지']) and str(row['이미지']).startswith('http'):
                st.image(row['이미지'], use_container_width=True)
            
            # 🌟 기출문제 연동 토글 (년도, 질문, 보기)
            with st.expander("📝 해당 기출문제 확인"):
                # quiz_df의 FK 열과 현재 개념의 PK 열을 매칭
                matched_quiz = quiz_df[quiz_df['FK'].astype(str) == current_pk]
                
                if not matched_quiz.empty:
                    for i, q_row in matched_quiz.iterrows():
                        # 1. 출제년도
                        st.markdown(f"**📅 출제년도: {q_row.get('기출문제(출제년도)', 'N/A')}**")
                        # 2. 질문
                        st.info(f"❓ {q_row.get('기출문제(질문)', '질문이 없습니다.')}")
                        # 3. 보기
                        st.write(f"📋 {q_row.get('기출문제(보기)', '보기가 없습니다.')}")
                        
                        # 문제 간 구분선
                        if i < matched_quiz.index[-1]:
                            st.markdown("---")
                else:
                    st.write("✅ 연결된 기출문제가 없습니다.")
            
            st.divider()

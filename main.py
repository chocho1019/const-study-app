import streamlit as st
import pandas as pd

# 1. 페이지 설정
st.set_page_config(page_title="건축기사 2025 스마트 노트", layout="wide")

# 2. 데이터 로드 함수
@st.cache_data
def load_data():
    sheet_id = '1v3BcFDsWe6SioGRy_FfWKbh0bQqXHueGEHPZpwVRPxE'
    
    # [개념] 시트 로드
    concept_url = f'https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet=개념'
    df_concept = pd.read_csv(concept_url).fillna("")
    
    # [기출문제] 시트 로드
    quiz_url = f'https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet=기출문제'
    df_quiz = pd.read_csv(quiz_url).fillna("")
    
    return df_concept, df_quiz

try:
    df_concept, df_quiz = load_data()

    # --- 사이드바 필터 ---
    st.sidebar.title("🔍 학습 필터")
    
    # 과목 필터
    if '과목' in df_concept.columns:
        subjects = ["전체"] + sorted(list(df_concept['과목'].unique()))
        sel_subject = st.sidebar.selectbox("과목 선택", subjects)
    
    # 빈출도 필터
    df_concept['빈출'] = pd.to_numeric(df_concept['빈출'], errors='coerce').fillna(0)
    min_score = st.sidebar.slider("최소 빈출 합산 점수", 0, int(df_concept['빈출'].max()) if not df_concept.empty else 10, 0)

    # 필터 적용
    view_df = df_concept.copy()
    if sel_subject != "전체":
        view_df = view_df[view_df['과목'] == sel_subject]
    view_df = view_df[view_df['빈출'] >= min_score]

    # --- 메인 화면 ---
    if view_df.empty:
        st.warning("조건에 맞는 데이터가 없습니다.")
    else:
        if 'idx' not in st.session_state: st.session_state.idx = 0
        st.session_state.idx = st.session_state.idx % len(view_df)
        row = view_df.iloc[st.session_state.idx]
        
        st.caption(f"{row['과목']} > {row['대카테고리']}")
        st.title(f"{row['개념']} (빈출: {int(row['빈출'])})")
        
        col1, col2 = st.columns([3, 2])
        with col1:
            st.info(str(row['내용']).replace("\\n", "\n"))
        
        with col2:
            if row['이미지URL'] and row['이미지URL'] != "-":
                st.image(row['이미지URL'], use_container_width=True)

        st.divider()

        # --- 기출문제 매칭 (사용자님 시트 컬럼명 기준) ---
        current_pk = str(row['PK']).strip()
        # 시트 내 '기출문제 (질문)' 컬럼 확인
        related_quizzes = df_quiz[df_quiz['PK'].astype(str).str.contains(current_pk, na=False)]

        if not related_quizzes.empty:
            with st.expander(f"📝 관련 기출문제 ({len(related_quizzes)}개) 보기", expanded=True):
                for _, q_row in related_quizzes.iterrows():
                    # 질문 컬럼명이 '기출문제 (질문)' 인지 '기출문제(질문)' 인지 유연하게 대응
                    q_text = q_row.get('기출문제 (질문)', q_row.get('기출문제(질문)', '질문 정보 없음'))
                    q_year = q_row.get('기출문제(출제년도)', '연도 미상')
                    st.markdown(f"**[{q_year}]** {q_text}")
                    st.divider()

        # 네비게이션
        c1, c2, c3 = st.columns([1, 2, 1])
        with c1:
            if st.button("⬅️ 이전"): st.session_state.idx -= 1; st.rerun()
        with c2:
            st.markdown(f"<center>{st.session_state.idx + 1} / {len(view_df)}</center>", unsafe_allow_html=True)
        with c3:
            if st.button("다음 ➡️"): st.session_state.idx += 1; st.rerun()

except Exception as e:
    st.error(f"데이터 로딩 중 오류 발생: {e}")
    st.info("시트의 열 이름이 'PK', '과목', '내용' 등으로 정확한지 확인해 주세요.")

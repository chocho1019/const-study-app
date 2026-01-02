import streamlit as st
import pandas as pd

# 1. 페이지 기본 설정
st.set_page_config(page_title="건축기사 2025 스마트 노트", layout="wide")

# 2. 데이터 로드 함수 (사용자님의 시트 ID 고정)
@st.cache_data
def load_data():
    sheet_id = '1v3BcFDsWe6SioGRy_FfWKbh0bQqXHueGEHPZpwVRPxE'
    
    # [개념] 시트 읽기
    concept_url = f'https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet=개념'
    df_concept = pd.read_csv(concept_url).fillna("")
    
    # [기출문제] 시트 읽기
    quiz_url = f'https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet=기출문제'
    df_quiz = pd.read_csv(quiz_url).fillna("")
    
    return df_concept, df_quiz

# 데이터 불러오기 실행
try:
    df_concept, df_quiz = load_data()

    # --- 사이드바: 필터 설정 ---
    st.sidebar.title("🔍 학습 필터")
    
    # 과목 선택
    subjects = ["전체"] + sorted(list(df_concept['과목'].unique()))
    sel_subject = st.sidebar.selectbox("과목을 선택하세요", subjects)
    
    # 빈출도 필터 (시트의 '빈출' 컬럼 기준)
    # 빈출 컬럼이 숫자가 아닐 경우를 대비해 처리
    df_concept['빈출'] = pd.to_numeric(df_concept['빈출'], errors='coerce').fillna(0)
    max_binchul = int(df_concept['빈출'].max())
    min_score = st.sidebar.slider("최소 빈출 합산 점수", 0, max_binchul, 0)
    
    # 별표 필터
    only_star = st.sidebar.checkbox("⭐ 별표(중요) 개념만")

    # 데이터 필터링 적용
    view_df = df_concept.copy()
    if sel_subject != "전체":
        view_df = view_df[view_df['과목'] == sel_subject]
    
    view_df = view_df[view_df['빈출'] >= min_score]
    
    if only_star:
        # 별표 컬럼에 값이 있는 것만 필터링 (보통 1 또는 별 모양)
        view_df = view_df[view_df['별표'] != ""]

    # --- 메인 화면: 개념 카드 ---
    if view_df.empty:
        st.warning("조건에 맞는 데이터가 없습니다. 필터를 조정해 주세요.")
    else:
        # 세션 상태로 현재 보고 있는 카드 번호 관리
        if 'idx' not in st.session_state:
            st.session_state.idx = 0
            
        # 인덱스 범위 초과 방지
        st.session_state.idx = st.session_state.idx % len(view_df)
        row = view_df.iloc[st.session_state.idx]
        
        # 상단 정보 표시
        st.caption(f"{row['과목']} > {row['대카테고리']} > {row['소카테고리']}")
        st.title(f"{row['개념']} (빈출: {int(row['빈출'])})")
        
        # 본문 영역
        col1, col2 = st.columns([3, 2])
        with col1:
            st.markdown("### 💡 핵심 요약")
            # 시트의 줄바꿈(\\n)을 실제 줄바꿈으로 변환
            content = str(row['내용']).replace("\\n", "\n")
            st.info(content)
        
        with col2:
            if row['이미지URL'] and row['이미지URL'] != "-":
                st.image(row['이미지URL'], caption=row['개념'], use_container_width=True)
            else:
                st.write("🖼️ 등록된 이미지가 없습니다.")

        st.divider()

        # --- 기출문제 자동 매칭 (FK/PK 기반) ---
        current_pk = str(row['PK']).strip()
        # 기출문제 시트의 PK 컬럼에 현재 개념의 PK가 포함되어 있는지 확인
        related_quizzes = df_quiz[df_quiz['PK'].astype(str).str.contains(current_pk, na=False)]

        if not related_quizzes.empty:
            with st.expander(f"📝 관련 기출문제 ({len(related_quizzes)}개) 펼쳐보기", expanded=True):
                for _, q_row in related_quizzes.iterrows():
                    st.markdown(f"**[{q_row['기출문제(출제년도)']}] {q_row['기출문제 (질문)'] or q_row['기출문제(질문)'] if '기출문제(질문)' in q_row else '질문 없음'}**")
                    st.write(f"> {q_row['기출문제 (보기)'] or q_row['기출문제(보기)']}")
                    st.divider()
        else:
            st.info("이 개념과 직접 연결된 기출문제가 기출문제 탭에 없습니다.")

        # --- 하단 이동 버튼 ---
        st.write("")
        c1, c2, c3 = st.columns([1, 2, 1])
        with c1:
            if st.button("⬅️ 이전"):
                st.session_state.idx -= 1
                st.rerun()
        with c2:
            st.markdown(f"<h3 style='text-align: center;'>{st.session_state.idx + 1} / {len(view_df)}</h3>", unsafe_allow_html=True)
        with c3:
            if st.button("다음 ➡️"):
                st.session_state.idx += 1
                st.rerun()

except Exception as e:
    st.error("데이터 로딩 오류!")
    st.write(f"오류 내용: {e}")
    st.info("구글 시트에서 [공유] -> [링크가 있는 모든 사용자] -> [뷰어]로 설정되어 있는지 확인해 주세요.")

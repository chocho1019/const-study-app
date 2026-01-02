import streamlit as st
import pandas as pd

# 1. 페이지 설정
st.set_page_config(page_title="건축기사 2025 스마트 노트", layout="wide")

# 2. 데이터 로드 함수 (사용자님의 시트 ID 적용)
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

try:
    df_concept, df_quiz = load_data()

    # --- 사이드바 필터 ---
    st.sidebar.title("🔍 학습 필터")
    
    # 과목 필터
    if '과목' in df_concept.columns:
        subjects = ["전체"] + sorted(list(df_concept['과목'].unique()))
        sel_subject = st.sidebar.selectbox("과목 선택", subjects)
    else:
        sel_subject = "전체"
    
    # 빈출도 숫자 변환 및 필터
    if '빈출' in df_concept.columns:
        df_concept['빈출'] = pd.to_numeric(df_concept['빈출'], errors='coerce').fillna(0)
        max_val = int(df_concept['빈출'].max()) if len(df_concept) > 0 else 10
        min_score = st.sidebar.slider("최소 빈출 합산 점수", 0, max_val, 0)
    else:
        min_score = 0

    # 필터링 적용
    view_df = df_concept.copy()
    if sel_subject != "전체":
        view_df = view_df[view_df['과목'] == sel_subject]
    if '빈출' in view_df.columns:
        view_df = view_df[view_df['빈출'] >= min_score]

    # --- 메인 화면 ---
    if view_df.empty:
        st.warning("조건에 맞는 데이터가 없습니다. 시트의 내용을 확인하거나 필터를 조정해 주세요.")
    else:
        if 'idx' not in st.session_state: st.session_state.idx = 0
        st.session_state.idx = st.session_state.idx % len(view_df)
        row = view_df.iloc[st.session_state.idx]
        
        # 상단 헤더
        st.caption(f"{row.get('과목','')} > {row.get('대카테고리','')}")
        st.title(f"{row.get('개념','제목 없음')} (빈출 합계: {int(row.get('빈출',0))})")
        
        # 내용 및 이미지
        col1, col2 = st.columns([3, 2])
        with col1:
            st.markdown("### 💡 핵심 요약")
            content = str(row.get('내용','내용이 없습니다.')).replace("\\n", "\n")
            st.info(content)
        
        with col2:
            img_url = row.get('이미지URL', "")
            if img_url and img_url != "-":
                st.image(img_url, use_container_width=True)
            else:
                st.write("🖼️ 등록된 이미지가 없습니다.")

        st.divider()

        # --- 기출문제 매칭 (시트 컬럼명 정밀 대응) ---
        current_pk = str(row.get('PK', '')).strip()
        
        # 기출문제 시트에서 현재 PK가 포함된 행 찾기
        if not df_quiz.empty and 'PK' in df_quiz.columns:
            related_quizzes = df_quiz[df_quiz['PK'].astype(str).str.contains(current_pk, na=False)]
            
            if not related_quizzes.empty:
                with st.expander(f"📝 관련 기출문제 ({len(related_quizzes)}개) 펼쳐보기", expanded=True):
                    for _, q_row in related_quizzes.iterrows():
                        # 시트의 다양한 컬럼명 표기에 대응
                        q_year = q_row.get('기출문제(출제년도)', '연도미상')
                        q_text = q_row.get('기출문제 (질문)', q_row.get('기출문제(질문)', '질문 정보 없음'))
                        q_choice = q_row.get('기출문제 (보기)', q_row.get('기출문제(보기)', '보기 정보 없음'))
                        
                        st.markdown(f"**[{q_year}]** {q_text}")
                        if q_choice != '보기 정보 없음':
                            st.write(f"보기: {q_choice}")
                        st.divider()
            else:
                st.info("이 개념과 연결된 기출문제가 없습니다.")

        # 하단 버튼
        st.write("")
        c1, c2, c3 = st.columns([1, 2, 1])
        with c1:
            if st.button("⬅️ 이전"): st.session_state.idx -= 1; st.rerun()
        with c2:
            st.markdown(f"<h3 style='text-align: center;'>{st.session_state.idx + 1} / {len(view_df)}</h3>", unsafe_allow_html=True)
        with c3:
            if st.button("다음 ➡️"): st.session_state.idx += 1; st.rerun()

except Exception as e:
    st.error(f"데이터 로딩 중 오류가 발생했습니다.")
    st.write(f"상세 오류: {e}")
    st.info("구글 시트 탭 이름이 '개념'과 '기출문제'가 맞는지, 그리고 링크 공유가 '뷰어'로 되어있는지 다시 확인해 주세요.")

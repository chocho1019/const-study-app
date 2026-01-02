import streamlit as st
import pandas as pd

# 1. 페이지 설정
st.set_page_config(page_title="건축기사 2025 스마트 노트", layout="wide")

@st.cache_data
def load_data():
    sheet_id = '1v3BcFDsWe6SioGRy_FfWKbh0bQqXHueGEHPZpwVRPxE'
    
    # [개념] 시트 로드
    concept_url = f'https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet=개념'
    df_c = pd.read_csv(concept_url)
    df_c.columns = df_c.columns.str.strip() # 열 이름 공백 제거
    
    # [기출문제] 시트 로드
    quiz_url = f'https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet=기출문제'
    df_q = pd.read_csv(quiz_url)
    df_q.columns = df_q.columns.str.strip() # 열 이름 공백 제거
    
    return df_c.fillna(""), df_q.fillna("")

try:
    df_concept, df_quiz = load_data()

    # 사이드바 설정
    st.sidebar.title("🔍 학습 필터")
    
    # 열 이름이 시트마다 다를 수 있어 안전하게 추출
    col_subject = '과목' if '과목' in df_concept.columns else df_concept.columns[1]
    col_pk = 'PK' if 'PK' in df_concept.columns else df_concept.columns[0]
    col_binchul = '빈출' if '빈출' in df_concept.columns else df_concept.columns[7]

    subjects = ["전체"] + sorted(list(df_concept[col_subject].unique()))
    sel_subject = st.sidebar.selectbox("과목 선택", subjects)
    
    # 필터링
    view_df = df_concept.copy()
    if sel_subject != "전체":
        view_df = view_df[view_df[col_subject] == sel_subject]

    if view_df.empty:
        st.warning("데이터가 없습니다.")
    else:
        if 'idx' not in st.session_state: st.session_state.idx = 0
        st.session_state.idx = st.session_state.idx % len(view_df)
        row = view_df.iloc[st.session_state.idx]
        
        # 메인 화면 출력
        st.caption(f"{row[col_subject]}")
        st.title(f"{row.get('개념', '제목없음')}")
        
        c1, c2 = st.columns([3, 2])
        with c1:
            st.info(str(row.get('내용', '내용없음')).replace("\\n", "\n"))
        with c2:
            img = row.get('이미지URL', "")
            if img and img != "-": st.image(img, use_container_width=True)

        st.divider()

        # --- 기출문제 매칭 로직 (가장 안전한 방식) ---
        target_id = str(row[col_pk]).strip()
        
        # 기출문제 시트에서 PK 혹은 FK 열을 찾아 매칭
        # 사용자님 시트의 기출문제 탭 2번째 열(B열)이 연결 ID인 것을 반영
        quiz_pk_col = df_quiz.columns[1] 
        related_quizzes = df_quiz[df_quiz[quiz_pk_col].astype(str).str.contains(target_id, na=False)]

        if not related_quizzes.empty:
            with st.expander(f"📝 관련 기출문제 ({len(related_quizzes)}개)", expanded=True):
                for _, q in related_quizzes.iterrows():
                    # 열 순서로 데이터 추출 (이름이 달라도 작동하게)
                    year = q.iloc[5] if len(q) > 5 else "연도미상"
                    question = q.iloc[2] if len(q) > 2 else "질문 없음"
                    choices = q.iloc[3] if len(q) > 3 else ""
                    
                    st.markdown(f"**[{year}]** {question}")
                    if choices: st.write(f"보기: {choices}")
                    st.divider()

        # 네비게이션
        bn1, bn2, bn3 = st.columns([1, 2, 1])
        with bn1:
            if st.button("⬅️ 이전"): st.session_state.idx -= 1; st.rerun()
        with bn2:
            st.markdown(f"<h3 style='text-align: center;'>{st.session_state.idx + 1} / {len(view_df)}</h3>", unsafe_allow_html=True)
        with bn3:
            if st.button("다음 ➡️"): st.session_state.idx += 1; st.rerun()

except Exception as e:
    st.error(f"데이터 로딩 오류: {e}")
    st.write("시트의 열 순서나 이름을 확인해주세요.")

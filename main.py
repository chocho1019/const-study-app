import streamlit as st
import pandas as pd

# 1. 페이지 설정
st.set_page_config(page_title="건축기사 2025 스마트 노트", layout="wide")

@st.cache_data
def load_data():
    # 사용자님의 시트 ID
    sheet_id = '1v3BcFDsWe6SioGRy_FfWKbh0bQqXHueGEHPZpwVRPxE'
    
    # [개념] 시트의 고유 GID (시트 하단 '개념' 탭을 누를 때 주소창 끝에 있는 숫자)
    # 확인된 사용자님의 '개념' 탭 GID는 0입니다.
    concept_gid = '0'
    # [기출문제] 시트의 고유 GID
    quiz_gid = '1799292523' 

    concept_url = f'https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={concept_gid}'
    quiz_url = f'https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={quiz_gid}'
    
    df_c = pd.read_csv(concept_url).fillna("")
    df_q = pd.read_csv(quiz_url).fillna("")
    
    # 열 이름의 앞뒤 공백 제거 (매칭 오류 방지)
    df_c.columns = df_c.columns.str.strip()
    df_q.columns = df_q.columns.str.strip()
    
    return df_c, df_q

try:
    df_concept, df_quiz = load_data()

    # 탭 메뉴 구성
    st.sidebar.title("📚 메뉴")
    menu = st.sidebar.radio("이동", ["개념 학습", "기출문제 목록"])

    if menu == "개념 학습":
        # 과목 필터
        subjects = ["전체"] + sorted(list(df_concept['과목'].unique()))
        sel_subject = st.sidebar.selectbox("과목 선택", subjects)
        
        view_df = df_concept.copy()
        if sel_subject != "전체":
            view_df = view_df[view_df['과목'] == sel_subject]

        if view_df.empty:
            st.warning("데이터가 없습니다.")
        else:
            if 'idx' not in st.session_state: st.session_state.idx = 0
            st.session_state.idx = st.session_state.idx % len(view_df)
            row = view_df.iloc[st.session_state.idx]
            
            st.caption(f"{row['과목']} > {row['대카테고리']}")
            st.title(f"{row['개념']}")
            
            c1, c2 = st.columns([3, 2])
            with c1:
                st.info(str(row['내용']).replace("\\n", "\n"))
            with c2:
                if row['이미지URL'] and row['이미지URL'] != "-":
                    st.image(row['이미지URL'], use_container_width=True)

            st.divider()

            # --- 관련 기출문제 자동 매칭 ---
            current_pk = str(row['PK']).strip()
            # 기출문제 탭의 PK 열과 매칭 (사용자 시트 컬럼명 기준)
            related_quizzes = df_quiz[df_quiz['PK'].astype(str).str.contains(current_pk, na=False)]

            if not related_quizzes.empty:
                with st.expander(f"📝 관련 기출문제 ({len(related_quizzes)}개)", expanded=True):
                    for _, q in related_quizzes.iterrows():
                        year = q.get('기출문제(출제년도)', '연도미상')
                        question = q.get('기출문제 (질문)', q.get('기출문제(질문)', '질문 없음'))
                        st.markdown(f"**[{year}]** {question}")
                        st.divider()

            # 하단 네비게이션
            bn1, bn2, bn3 = st.columns([1, 2, 1])
            with bn1:
                if st.button("⬅️ 이전"): st.session_state.idx -= 1; st.rerun()
            with b2:
                st.markdown(f"<h3 style='text-align: center;'>{st.session_state.idx + 1} / {len(view_df)}</h3>", unsafe_allow_html=True)
            with b3:
                if st.button("다음 ➡️"): st.session_state.idx += 1; st.rerun()

    else:
        st.title("📝 전체 기출문제 목록")
        st.dataframe(df_quiz)

except Exception as e:
    st.error(f"데이터를 불러올 수 없습니다.")
    st.write(f"오류 원인: {e}")
    st.info("구글 시트의 [개념] 탭 GID가 0이 맞는지 확인해 주세요.")

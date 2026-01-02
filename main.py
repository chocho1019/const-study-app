import streamlit as st

# 모바일 화면 설정
st.set_page_config(page_title="건축기사 요약", layout="centered")

# 비밀번호 체크 함수
def check_password():
    if "password_correct" not in st.session_state:
        st.markdown("### 🔐 건축기사 한입 공부")
        password = st.text_input("비밀번호를 입력하세요", type="password")
        if st.button("입장하기"):
            if password == "1234":
                st.session_state["password_correct"] = True
                st.rerun()
            else:
                st.error("비밀번호가 틀렸습니다.")
        return False
    return True

if check_password():
    # 학습 데이터 (주신 사진 내용 반영)
    study_data = [
        {"concept": "(1) 기준점 (벤치마크)", "desc": "① 이동/소멸 우려 없는 곳에 설치\n② 공사 완료 시까지 존치\n③ 2개소 이상 설치\n④ 침하, 경사 확인 등에 사용"},
        {"concept": "(5) 시멘트 창고 설계", "desc": "① 바닥구조는 마루널깔기\n② 크기는 100포당 2~3m2 권장\n③ 환기창 설치 금지\n④ 바닥은 지반에서 30cm 이상 높게"},
        {"concept": "(6) 비계면적 공식", "desc": "① 외줄비계 : H(L+8x0.45)\n② 쌍줄비계 : H(L+8x0.9)\n③ 강관비계 : H(L+8x1)"},
        {"concept": "주상도 주요 정보", "desc": "① N치\n② 토층별 두께\n③ 토층의 구성\n* 오답: 투수계수"}
    ]

    st.title("🏗️ 건축기사 모바일 요약집")

    if 'idx' not in st.session_state:
        st.session_state.idx = 0

    # 카드 UI
    with st.container(border=True):
        st.subheader(study_data[st.session_state.idx]['concept'])
        st.markdown(study_data[st.session_state.idx]['desc'].replace("\n", "\n\n"))

    # 버튼
    col1, col2 = st.columns(2)
    with col1:
        if st.button("⬅️ 이전", use_container_width=True):
            st.session_state.idx = max(0, st.session_state.idx - 1)
    with col2:
        if st.button("다음 ➡️", use_container_width=True):
            st.session_state.idx = min(len(study_data) - 1, st.session_state.idx + 1)
    
    st.progress((st.session_state.idx + 1) / len(study_data))

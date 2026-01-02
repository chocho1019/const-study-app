import streamlit as st
import pandas as pd

# ---------------------------------------------------------
# [설정 영역] 실제 구글 시트의 열 이름과 일치하게 수정해주세요!
# ---------------------------------------------------------

# 1. 구글 시트 공유 링크 (CSV 내보내기용으로 변환됨)
# 현재 주신 시트 ID를 기반으로 설정했습니다.
SHEET_ID = '1eg3TnoILIHXCzf4fPCU6uqzZssLnFS2xHO5zD7N2c0g'

# 시트별 GID (주소창의 gid= 숫자)
# 예: 개념 시트가 gid=0, 기출 시트가 gid=12345 라면 아래 숫자를 바꿔주세요.
# 주신 링크의 gid=46086374를 '개념 시트'라고 가정했습니다. 기출문제 시트의 gid도 확인해서 넣어주세요.
CONCEPT_GID = '46086374' 
QUESTION_GID = '0' # <--- [중요] 기출문제 시트의 GID로 꼭 변경해주세요!

# 2. 열 이름 매핑 (시트의 1행 헤더와 똑같아야 함)
COL_CONFIG = {
    # [개념 시트 컬럼]
    'subject': '과목',            # 과목 열 이름
    'main_cat': '대카테고리',      # 대분류 열 이름
    'sub_cat': '소카테고리',       # 소분류 열 이름
    'concept': '개념',            # 개념 제목 열 이름
    'content': '내용',            # 상세 내용 열 이름
    'image': '이미지URL',         # 이미지 링크가 있는 열 이름
    'frequency': '빈출',          # 빈출도(숫자나 등급) 열 이름
    'pk': 'ID',                  # 개념의 고유 ID (PK)

    # [기출문제 시트 컬럼]
    'q_content': '문제',          # 문제 내용
    'q_answer': '정답',           # 정답
    'fk': '개념ID'                # 개념과 연결되는 ID (FK)
}

# ---------------------------------------------------------
# [앱 로직 시작]
# ---------------------------------------------------------

st.set_page_config(layout="wide", page_title="학습 도우미 앱")

# CSS로 스타일 다듬기 (제목 옆 별표 배치 등을 위해)
st.markdown("""
<style>
    .stButton>button {
        border: none;
        background: transparent;
        font-size: 20px;
    }
    .concept-title {
        font-size: 24px;
        font-weight: bold;
        color: #333;
        display: inline-block;
    }
    .divider {
        margin-top: 10px;
        margin-bottom: 20px;
        border-bottom: 1px solid #ddd;
    }
</style>
""", unsafe_allow_html=True)

# 데이터 로드 함수 (캐싱 적용)
@st.cache_data(ttl=600)
def load_data(sheet_id, gid):
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
    try:
        df = pd.read_csv(url)
        # 결측치 처리 (빈 문자열로)
        df = df.fillna("") 
        return df
    except Exception as e:
        st.error(f"데이터를 불러오는데 실패했습니다. GID나 권한을 확인해주세요. 에러: {e}")
        return pd.DataFrame()

# 데이터 불러오기
df_concepts = load_data(SHEET_ID, CONCEPT_GID)
df_questions = load_data(SHEET_ID, QUESTION_GID)

# 세션 상태 초기화 (즐겨찾기 저장용)
if 'favorites' not in st.session_state:
    st.session_state.favorites = []

def toggle_favorite(concept_id):
    if concept_id in st.session_state.favorites:
        st.session_state.favorites.remove(concept_id)
    else:
        st.session_state.favorites.append(concept_id)

# ---------------------------------------------------------
# [사이드바 & 상단] 필터링 영역
# ---------------------------------------------------------

st.title("📚 나만의 학습 앱")

# 보기 모드 선택
view_mode = st.radio("보기 모드", ["전체 학습", "⭐ 즐겨찾기만 보기"], horizontal=True)

if not df_concepts.empty:
    
    # 1. 필터링 로직 (위계 구조 적용)
    
    # (1) 과목 선택
    subjects = df_concepts[COL_CONFIG['subject']].unique().tolist()
    selected_subject = st.selectbox("과목 선택", ["전체"] + subjects)
    
    filtered_df = df_concepts.copy()
    if selected_subject != "전체":
        filtered_df = filtered_df[filtered_df[COL_CONFIG['subject']] == selected_subject]

    # (2) 대카테고리 선택 (과목 선택에 따라 변동)
    main_cats = filtered_df[COL_CONFIG['main_cat']].unique().tolist()
    selected_main = st.selectbox("대분류 선택", ["전체"] + main_cats)
    
    if selected_main != "전체":
        filtered_df = filtered_df[filtered_df[COL_CONFIG['main_cat']] == selected_main]

    # (3) 소카테고리 선택
    sub_cats = filtered_df[COL_CONFIG['sub_cat']].unique().tolist()
    selected_sub = st.selectbox("소분류 선택", ["전체"] + sub_cats)
    
    if selected_sub != "전체":
        filtered_df = filtered_df[filtered_df[COL_CONFIG['sub_cat']] == selected_sub]

    # (4) 빈출순 정렬 옵션
    sort_by_freq = st.checkbox("빈출순으로 보기")
    if sort_by_freq:
        # 빈출 컬럼이 숫자가 아닐 경우를 대비해 문자열로 처리하거나 형변환 필요할 수 있음
        # 여기서는 내림차순(높은게 위로)으로 가정
        try:
            filtered_df = filtered_df.sort_values(by=COL_CONFIG['frequency'], ascending=False)
        except:
            st.warning("빈출 데이터 형식을 숫자로 정렬할 수 없습니다.")

    # (5) 즐겨찾기 모드일 경우 필터링
    if view_mode == "⭐ 즐겨찾기만 보기":
        filtered_df = filtered_df[filtered_df[COL_CONFIG['pk']].isin(st.session_state.favorites)]
        if filtered_df.empty:
            st.info("아직 즐겨찾기한 개념이 없습니다.")


    st.markdown("---") # 구분선

    # ---------------------------------------------------------
    # [메인 콘텐츠] 개념 리스트 출력
    # ---------------------------------------------------------
    
    if filtered_df.empty and view_mode == "전체 학습":
        st.warning("해당 조건의 개념이 없습니다.")

    for index, row in filtered_df.iterrows():
        c_pk = row[COL_CONFIG['pk']]
        c_title = row[COL_CONFIG['concept']]
        c_content = row[COL_CONFIG['content']]
        c_image = row[COL_CONFIG['image']]
        
        # --- 카드 UI 시작 ---
        col1, col2 = st.columns([0.9, 0.1])
        
        with col1:
            # 개념 제목
            st.markdown(f"### {c_title}")
        
        with col2:
            # 별표 버튼
            is_fav = c_pk in st.session_state.favorites
            btn_label = "★" if is_fav else "☆"
            if st.button(btn_label, key=f"fav_{c_pk}"):
                toggle_favorite(c_pk)
                st.rerun() # 상태 업데이트 후 리로드

        # 내용
        st.write(c_content)
        
        # 이미지 (URL이 있을 때만 표시)
        if c_image and str(c_image).strip() != "":
            try:
                st.image(c_image, use_column_width=True)
            except:
                st.caption("이미지를 불러올 수 없습니다.")

        # 기출문제 토글
        with st.expander("해당 기출문제 보기"):
            # FK와 PK 매칭
            if not df_questions.empty:
                # 데이터 타입 매칭 (문자열로 변환하여 비교)
                related_qs = df_questions[df_questions[COL_CONFIG['fk']].astype(str) == str(c_pk)]
                
                if not related_qs.empty:
                    for q_idx, q_row in related_qs.iterrows():
                        st.markdown(f"**Q:** {q_row[COL_CONFIG['q_content']]}")
                        st.info(f"**A:** {q_row[COL_CONFIG['q_answer']]}")
                        st.divider()
                else:
                    st.text("등록된 기출문제가 없습니다.")
            else:
                st.text("기출문제 데이터를 불러오지 못했습니다.")

        st.markdown("<div class='divider'></div>", unsafe_allow_html=True)

else:
    st.write("데이터를 로딩 중이거나 불러올 수 없습니다.")

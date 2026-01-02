import streamlit as st
import pandas as pd

# ==============================================================================
# [1] 설정 영역 - 보내주신 시트의 실제 열 이름(PK, FK 등)을 반영했습니다.
# ==============================================================================

SHEET_ID = '1eg3TnoILIHXCzf4fPCU6uqzZssLnFS2xHO5zD7N2c0g'
CONCEPT_GID = '46086374'   # 개념 시트
QUESTION_GID = '775019664' # 기출문제 시트

# 두 번째 스크린샷에 나온 실제 열 이름 리스트를 바탕으로 수정했습니다.
COL_CONFIG = {
    # [개념 시트]
    'subject': '과목',            
    'main_cat': '대카테고리',      
    'sub_cat': '소카테고리',       
    'concept': '개념',            
    'content': '내용',            
    'image': '이미지URL',         
    'frequency': '빈출',          
    'pk': 'PK',                  # 'ID'에서 'PK'로 수정 완료!

    # [기출문제 시트]
    'q_content': '문제',          
    'q_answer': '정답',           
    'fk': 'FK'                   # '개념ID'에서 'FK'로 수정 완료!
}

# ==============================================================================
# [2] 앱 로직
# ==============================================================================

st.set_page_config(layout="wide", page_title="나만의 학습 앱")

# 스타일 설정
st.markdown("""
<style>
    .stButton>button {border: none; background: transparent; font-size: 20px;}
    .divider {margin-top: 10px; margin-bottom: 20px; border-bottom: 1px solid #ddd;}
</style>
""", unsafe_allow_html=True)

@st.cache_data(ttl=600)
def load_data(sheet_id, gid):
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
    try:
        df = pd.read_csv(url)
        df.columns = df.columns.str.strip() # 공백 제거
        df = df.fillna("")
        return df
    except:
        return pd.DataFrame()

# 데이터 로드
df_concepts = load_data(SHEET_ID, CONCEPT_GID)
df_questions = load_data(SHEET_ID, QUESTION_GID)

# 세션 상태 (즐겨찾기)
if 'favorites' not in st.session_state:
    st.session_state.favorites = []

def toggle_favorite(concept_id):
    if concept_id in st.session_state.favorites:
        st.session_state.favorites.remove(concept_id)
    else:
        st.session_state.favorites.append(concept_id)

# --- UI 시작 ---
st.title("📚 나만의 학습 앱")

view_mode = st.radio("보기 모드", ["전체 학습", "⭐ 즐겨찾기만 보기"], horizontal=True)

if not df_concepts.empty:
    # 필터 위계 구조
    subjects = sorted(list(set(df_concepts[COL_CONFIG['subject']].unique())))
    selected_subject = st.selectbox("과목 선택", ["전체"] + subjects)
    
    filtered_df = df_concepts.copy()
    if selected_subject != "전체":
        filtered_df = filtered_df[filtered_df[COL_CONFIG['subject']] == selected_subject]

    main_cats = sorted(list(set(filtered_df[COL_CONFIG['main_cat']].unique())))
    selected_main = st.selectbox("대분류 선택", ["전체"] + main_cats)
    
    if selected_main != "전체":
        filtered_df = filtered_df[filtered_df[COL_CONFIG['main_cat']] == selected_main]

    sub_cats = sorted(list(set(filtered_df[COL_CONFIG['sub_cat']].unique())))
    selected_sub = st.selectbox("소분류 선택", ["전체"] + sub_cats)
    
    if selected_sub != "전체":
        filtered_df = filtered_df[filtered_df[COL_CONFIG['sub_cat']] == selected_sub]

    sort_by_freq = st.checkbox("빈출순으로 보기")
    if sort_by_freq:
        filtered_df = filtered_df.sort_values(by=COL_CONFIG['frequency'], ascending=False)

    if view_mode == "⭐ 즐겨찾기만 보기":
        filtered_df = filtered_df[filtered_df[COL_CONFIG['pk']].isin(st.session_state.favorites)]

    st.markdown("---")

    # 리스트 출력
    for index, row in filtered_df.iterrows():
        c_pk = row[COL_CONFIG['pk']]
        
        col1, col2 = st.columns([0.9, 0.1])
        with col1:
            st.markdown(f"### {row[COL_CONFIG['concept']]}")
        with col2:
            is_fav = c_pk in st.session_state.favorites
            if st.button("★" if is_fav else "☆", key=f"fav_{c_pk}"):
                toggle_favorite(c_pk)
                st.rerun()

        st.write(row[COL_CONFIG['content']])
        
        if row[COL_CONFIG['image']] and str(row[COL_CONFIG['image']]).startswith('http'):
            st.image(row[COL_CONFIG['image']], use_container_width=True)

        with st.expander("해당 기출문제 보기"):
            if not df_questions.empty:
                related_qs = df_questions[df_questions[COL_CONFIG['fk']].astype(str) == str(c_pk)]
                if not related_qs.empty:
                    for _, q_row in related_qs.iterrows():
                        st.markdown(f"**Q:** {q_row[COL_CONFIG['q_content']]}")
                        st.info(f"**A:** {q_row[COL_CONFIG['q_answer']]}")
                        st.divider()
                else:
                    st.write("연결된 기출문제가 없습니다.")
        
        st.markdown("<div class='divider'></div>", unsafe_allow_html=True)
else:
    st.error("시트에서 데이터를 가져올 수 없습니다. 링크와 열 이름을 확인해 주세요.")

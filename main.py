import streamlit as st
import pandas as pd

# ==============================================================================
# [1] 기본 설정 (여기만 확인하시면 됩니다)
# ==============================================================================

# 구글 시트 ID
SHEET_ID = '1eg3TnoILIHXCzf4fPCU6uqzZssLnFS2xHO5zD7N2c0g'

# 시트별 GID (주소창의 gid= 숫자)
CONCEPT_GID = '46086374'   # 개념 시트
QUESTION_GID = '775019664' # 기출문제 시트 (업데이트됨)

# 열 이름 설정 (구글 시트의 1행과 똑같아야 함)
# 혹시 에러가 나면 앱 화면에 실제 열 이름이 표시되니 그걸 보고 여기를 수정하면 됩니다.
COL_CONFIG = {
    # [개념 시트]
    'subject': '과목',            
    'main_cat': '대카테고리',      
    'sub_cat': '소카테고리',       
    'concept': '개념',            
    'content': '내용',            
    'image': '이미지URL',         # 이미지 주소가 들어있는 열 이름 (없으면 비워두거나 무시됨)
    'frequency': '빈출',          
    'pk': 'ID',                  # 개념 고유 ID (예: 1, 2, 3...)

    # [기출문제 시트]
    'q_content': '문제',          
    'q_answer': '정답',           
    'fk': '개념ID'                # 개념과 연결되는 ID
}

# ==============================================================================
# [2] 앱 로직 (건드리지 않으셔도 됩니다)
# ==============================================================================

st.set_page_config(layout="wide", page_title="나만의 학습 앱")

# 스타일 설정
st.markdown("""
<style>
    .stButton>button {border: none; background: transparent; font-size: 20px;}
    .concept-title {font-size: 24px; font-weight: bold; color: #333;}
    .divider {margin-top: 10px; margin-bottom: 20px; border-bottom: 1px solid #ddd;}
</style>
""", unsafe_allow_html=True)

@st.cache_data(ttl=600)
def load_data(sheet_id, gid):
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
    try:
        df = pd.read_csv(url)
        # 중요: 열 이름의 앞뒤 공백 제거 (에러 방지용)
        df.columns = df.columns.str.strip()
        df = df.fillna("")
        return df
    except Exception as e:
        return pd.DataFrame()

# 데이터 로드
df_concepts = load_data(SHEET_ID, CONCEPT_GID)
df_questions = load_data(SHEET_ID, QUESTION_GID)

# ------------------------------------------------------------------------------
# [안전장치] 열 이름 체크 (에러 발생 시 화면에 표시)
# ------------------------------------------------------------------------------
if not df_concepts.empty:
    required_cols = [COL_CONFIG['subject'], COL_CONFIG['main_cat'], COL_CONFIG['concept'], COL_CONFIG['pk']]
    missing_cols = [col for col in required_cols if col not in df_concepts.columns]
    
    if missing_cols:
        st.error("🚨 **[긴급 점검] 구글 시트의 열 이름을 찾을 수 없습니다!**")
        st.write(f"코드에서 찾는 이름: {missing_cols}")
        st.write("---")
        st.warning(f"👇 **실제 시트에 있는 열 이름 목록** (아래 이름을 보고 코드의 `COL_CONFIG`를 수정하세요)")
        st.code(list(df_concepts.columns))
        st.stop() # 더 이상 실행하지 않고 멈춤

# 세션 상태 (즐겨찾기)
if 'favorites' not in st.session_state:
    st.session_state.favorites = []

def toggle_favorite(concept_id):
    if concept_id in st.session_state.favorites:
        st.session_state.favorites.remove(concept_id)
    else:
        st.session_state.favorites.append(concept_id)

# ------------------------------------------------------------------------------
# [UI] 화면 구성
# ------------------------------------------------------------------------------

st.title("📚 나만의 학습 앱")

# 보기 모드
view_mode = st.radio("보기 모드", ["전체 학습", "⭐ 즐겨찾기만 보기"], horizontal=True)

if not df_concepts.empty:
    # --- 필터링 로직 ---
    
    # 1. 과목
    subjects = sorted(list(set(df_concepts[COL_CONFIG['subject']].tolist())))
    if "전체" not in subjects: subjects.insert(0, "전체")
    selected_subject = st.selectbox("과목 선택", subjects)
    
    filtered_df = df_concepts.copy()
    if selected_subject != "전체":
        filtered_df = filtered_df[filtered_df[COL_CONFIG['subject']] == selected_subject]

    # 2. 대분류
    main_cats = sorted(list(set(filtered_df[COL_CONFIG['main_cat']].tolist())))
    if "전체" not in main_cats: main_cats.insert(0, "전체")
    selected_main = st.selectbox("대분류 선택", main_cats)
    
    if selected_main != "전체":
        filtered_df = filtered_df[filtered_df[COL_CONFIG['main_cat']] == selected_main]

    # 3. 소분류
    sub_cats = sorted(list(set(filtered_df[COL_CONFIG['sub_cat']].tolist())))
    if "전체" not in sub_cats: sub_cats.insert(0, "전체")
    selected_sub = st.selectbox("소분류 선택", sub_cats)
    
    if selected_sub != "전체":
        filtered_df = filtered_df[filtered_df[COL_CONFIG['sub_cat']] == selected_sub]

    # 4. 빈출 정렬
    sort_by_freq = st.checkbox("빈출순으로 보기")
    if sort_by_freq:
        try:
            filtered_df = filtered_df.sort_values(by=COL_CONFIG['frequency'], ascending=False)
        except:
            pass

    # 5. 즐겨찾기 필터
    if view_mode == "⭐ 즐겨찾기만 보기":
        filtered_df = filtered_df[filtered_df[COL_CONFIG['pk']].isin(st.session_state.favorites)]
        if filtered_df.empty:
            st.info("즐겨찾기한 내용이 없습니다.")

    st.markdown("---")

    # --- 메인 리스트 출력 ---
    for index, row in filtered_df.iterrows():
        # 데이터 안전하게 가져오기
        c_pk = row[COL_CONFIG['pk']]
        c_title = row.get(COL_CONFIG['concept'], "제목 없음")
        c_content = row.get(COL_CONFIG['content'], "")
        c_image = row.get(COL_CONFIG['image'], "")
        
        # 카드 헤더
        col1, col2 = st.columns([0.9, 0.1])
        with col1:
            st.markdown(f"### {c_title}")
        with col2:
            is_fav = c_pk in st.session_state.favorites
            btn_label = "★" if is_fav else "☆"
            if st.button(btn_label, key=f"fav_{c_pk}_{index}"): # key 중복 방지
                toggle_favorite(c_pk)
                st.rerun()

        # 내용
        st.write(c_content)
        
        # 이미지
        if c_image and str(c_image).strip() != "" and str(c_image) != "nan":
            st.image(str(c_image), use_column_width=True)

        # 기출문제 토글
        with st.expander("해당 기출문제 보기"):
            if not df_questions.empty:
                # FK 비교 (문자열로 변환하여 비교)
                fk_col = COL_CONFIG['fk']
                if fk_col in df_questions.columns:
                    related_qs = df_questions[df_questions[fk_col].astype(str) == str(c_pk)]
                    
                    if not related_qs.empty:
                        for idx, q_row in related_qs.iterrows():
                            q_txt = q_row.get(COL_CONFIG['q_content'], "문제 내용 없음")
                            a_txt = q_row.get(COL_CONFIG['q_answer'], "정답 없음")
                            st.markdown(f"**Q:** {q_txt}")
                            st.info(f"**A:** {a_txt}")
                            st.divider()
                    else:
                        st.caption("연결된 기출문제가 없습니다.")
                else:
                    st.warning(f"기출문제 시트에서 '{fk_col}' 열을 찾을 수 없습니다.")
            else:
                st.caption("기출문제 데이터를 불러오지 못했습니다.")

        st.markdown("<div class='divider'></div>", unsafe_allow_html=True)

else:
    st.info("데이터를 불러오는 중이거나 데이터가 비어있습니다.")

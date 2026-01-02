import streamlit as st
import pandas as pd

# ---------------------------------------------------------
# [설정] 구글 시트 정보 및 컬럼 매핑 (이 부분을 실제 시트에 맞춰 수정하세요!)
# ---------------------------------------------------------

# 구글 시트 ID (URL 중간의 긴 문자열)
SHEET_ID = '1eg3TnoILIHXCzf4fPCU6uqzZssLnFS2xHO5zD7N2c0g'

# 시트별 GID (URL 끝의 gid= 숫자)
# 예: 개념 시트가 첫 번째라면 보통 0, 기출문제 시트가 두 번째라면 해당 gid
GID_CONCEPTS = '0'        # <--- 개념 시트의 gid로 변경하세요
GID_QUESTIONS = '46086374' # <--- 기출문제 시트의 gid로 변경하세요 (링크주신 gid 참고함)

# CSV 변환 URL 생성 함수
def get_sheet_url(doc_id, gid):
    return f'https://docs.google.com/spreadsheets/d/{doc_id}/export?format=csv&gid={gid}'

# 컬럼 이름 매핑 (시트의 실제 헤더 이름으로 수정 필요)
cols = {
    # 개념 시트 컬럼
    "pk": "id",              # 고유번호
    "subject": "과목",        # 예: 건축계획
    "cat_main": "대분류",     # 예: 한국건축사
    "cat_sub": "소분류",      # 예: 한국전통건축 특징
    "title": "개념명",        # 예: 한식주택 개구부
    "content": "내용",        # 상세 설명
    "image": "이미지URL",     # 이미지 링크 (없으면 빈칸)
    "freq": "빈출",           # 빈출 여부 (예: O, X 또는 숫자)
    
    # 기출문제 시트 컬럼
    "fk": "concept_id",      # 개념 시트의 pk와 연결되는 키
    "exam_name": "기출회차",  # 예: 22-02
    "q_text": "문제",         # 문제 지문
    "options": "보기"         # 보기 내용
}

# ---------------------------------------------------------
# 1. 데이터 로드 및 전처리
# ---------------------------------------------------------
@st.cache_data(ttl=600) # 10분마다 갱신
def load_data():
    try:
        # 개념 데이터 로드
        df_c = pd.read_csv(get_sheet_url(SHEET_ID, GID_CONCEPTS))
        # 기출 데이터 로드
        df_q = pd.read_csv(get_sheet_url(SHEET_ID, GID_QUESTIONS))
        
        # 데이터 타입 정리 (PK, FK는 문자열로 통일하여 매칭 오류 방지)
        df_c[cols['pk']] = df_c[cols['pk']].astype(str)
        df_q[cols['fk']] = df_q[cols['fk']].astype(str)
        
        return df_c, df_q
    except Exception as e:
        st.error(f"데이터를 불러오는데 실패했습니다. 구글 시트 권한이나 컬럼명을 확인해주세요. 에러: {e}")
        return pd.DataFrame(), pd.DataFrame()

df_concepts, df_questions = load_data()

# ---------------------------------------------------------
# 2. 세션 상태 관리 (즐겨찾기 기능)
# ---------------------------------------------------------
if 'favorites' not in st.session_state:
    st.session_state['favorites'] = [] # 즐겨찾기된 PK 리스트

def toggle_favorite(pk):
    if pk in st.session_state['favorites']:
        st.session_state['favorites'].remove(pk)
    else:
        st.session_state['favorites'].append(pk)

# ---------------------------------------------------------
# 3. 사이드바 (네비게이션 & 필터)
# ---------------------------------------------------------
st.sidebar.title("📚 건축기사 쓱싹")

# 모드 선택
view_mode = st.sidebar.radio("학습 모드", ["전체 학습하기", "⭐ 즐겨찾기만 보기"])

# 필터링 로직
filtered_df = df_concepts.copy()

if view_mode == "⭐ 즐겨찾기만 보기":
    if not st.session_state['favorites']:
        st.warning("아직 즐겨찾기한 내용이 없습니다.")
    filtered_df = filtered_df[filtered_df[cols['pk']].isin(st.session_state['favorites'])]
else:
    # 1단계: 과목 선택
    subjects = filtered_df[cols['subject']].unique()
    selected_subject = st.sidebar.selectbox("1. 과목 선택", subjects)
    filtered_df = filtered_df[filtered_df[cols['subject']] == selected_subject]

    # 2단계: 대분류 선택
    if not filtered_df.empty:
        cat_mains = filtered_df[cols['cat_main']].unique()
        selected_main = st.sidebar.selectbox("2. 대분류", cat_mains)
        filtered_df = filtered_df[filtered_df[cols['cat_main']] == selected_main]

    # 3단계: 소분류 선택
    if not filtered_df.empty:
        cat_subs = filtered_df[cols['cat_sub']].unique()
        selected_sub = st.sidebar.selectbox("3. 소분류", cat_subs)
        filtered_df = filtered_df[filtered_df[cols['cat_sub']] == selected_sub]

    # (옵션) 빈출순 정렬/필터
    only_freq = st.sidebar.checkbox("🔥 빈출 개념만 보기")
    if only_freq:
        # 빈출 컬럼에 값이 있거나 특정 마킹이 있는 경우 필터링 (데이터에 따라 수정 필요)
        filtered_df = filtered_df[filtered_df[cols['freq']].notnull()]

# ---------------------------------------------------------
# 4. 메인 화면 구성
# ---------------------------------------------------------

# 상단 위계 표시 (Breadcrumbs)
if not filtered_df.empty:
    row = filtered_df.iloc[0]
    st.markdown(
        f"""
        <div style="text-align: right; color: #ccc; font-size: 0.8rem; margin-bottom: 20px;">
        {row[cols['subject']]} > {row[cols['cat_main']]} > {row[cols['cat_sub']]}
        </div>
        """, unsafe_allow_html=True
    )

# 카드 반복 출력
if filtered_df.empty:
    st.info("해당하는 개념이 없습니다.")
else:
    for index, row in filtered_df.iterrows():
        concept_pk = row[cols['pk']]
        is_fav = concept_pk in st.session_state['favorites']
        
        # --- 카드 디자인 시작 ---
        with st.container():
            # [제목 영역] : 개념명 + 즐겨찾기 별표
            c1, c2 = st.columns([0.85, 0.15])
            with c1:
                st.markdown(f"## {row[cols['title']]}")
            with c2:
                # 별표 버튼 (클릭 시 rerun되어 상태 반영)
                btn_label = "★" if is_fav else "☆"
                if st.button(btn_label, key=f"fav_{concept_pk}"):
                    toggle_favorite(concept_pk)
                    st.rerun()

            # [스타일링] 카드 구분선 (왼쪽의 노란색 바 느낌을 위해 markdown 사용 가능하지만 여기선 심플하게)
            st.markdown("---")

            # [본문 영역]
            # 1. 이미지 (있으면 표시)
            img_url = row.get(cols['image']) # 컬럼이 없거나 값이 비어있을 수 있음
            if pd.notna(img_url) and str(img_url).strip() != "":
                st.image(img_url, use_column_width=True)
            
            # 2. 텍스트 내용
            st.markdown(f"""
            <div style="background-color: rgba(255,255,255,0.1); padding: 15px; border-radius: 5px; border-left: 5px solid #F4D03F;">
                <span style="font-size: 1.1rem;">{row[cols['content']]}</span>
            </div>
            """, unsafe_allow_html=True)

            st.write("") # 여백

            # [기출문제 토글 영역]
            # 해당 개념(PK)에 매칭되는 기출문제(FK) 찾기
            related_qs = df_questions[df_questions[cols['fk']] == concept_pk]
            
            with st.expander(f"▼ 해당 기출문제 ({len(related_qs)}문제)"):
                if related_qs.empty:
                    st.write("등록된 기출문제가 없습니다.")
                else:
                    for idx, q_row in related_qs.iterrows():
                        st.markdown(f"**[{q_row[cols['exam_name']]}]**")
                        st.write(f"Q. {q_row[cols['q_text']]}")
                        if pd.notna(q_row[cols['options']]):
                            st.caption(f"{q_row[cols['options']]}")
                        st.divider()
            
            # 카드 간 간격
            st.write("---") 
            st.write("") 
            st.write("")

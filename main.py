import streamlit as st
import pandas as pd

# 1. 앱 설정
st.set_page_config(page_title="2026 초카이브 건축기사 필기", layout="wide")

# 2. 스타일 설정
st.markdown("""
    <style>
    .concept-title { font-size: 28px; font-weight: bold; color: #2E4053; margin-bottom: 10px; }
    .stButton button { width: 100%; }
    .question-card { 
        background-color: #f8f9fa; 
        padding: 15px; 
        border-radius: 8px; 
        border-left: 5px solid #4A90E2;
        margin-bottom: 10px;
    }
    hr { margin: 2rem 0; }
    </style>
    """, unsafe_allow_html=True)

# 3. 데이터 로드 및 타입 일치 병합 함수
@st.cache_data(ttl=300)
def load_combined_data():
    try:
        base_url = "https://docs.google.com/spreadsheets/d/1eg3TnoILIHXCzf4fPCU6uqzZssLnFS2xHO5zD7N2c0g/gviz/tq?tqx=out:csv"
        
        # 각 시트 로드 (gid=0: 개념, gid=775019664: 기출문제)
        concept_df = pd.read_csv(f"{base_url}&gid=0")
        exam_df = pd.read_csv(f"{base_url}&gid=775019664")
        
        # 열 이름 공백 제거
        concept_df.columns = [col.strip() for col in concept_df.columns]
        exam_df.columns = [col.strip() for col in exam_df.columns]
        
        # [핵심] 데이터 타입 불일치 해결: PK와 FK를 모두 문자열로 변환
        concept_df['PK'] = concept_df['PK'].astype(str).str.strip()
        exam_df['FK'] = exam_df['FK'].astype(str).str.strip()
        
        # 데이터 병합 (개념 기준 Left Join)
        merged_df = pd.merge(concept_df, exam_df, left_on='PK', right_on='FK', how='left')
        
        return merged_df
    except Exception as e:
        st.error(f"데이터 병합 실패: {e}")
        return None

df = load_combined_data()

if df is not None:
    # 세션 상태 초기화
    if 'favorites' not in st.session_state:
        st.session_state.favorites = set()

    # --- 사이드바 ---
    st.sidebar.title("🔍 학습 필터")
    sort_by_freq = st.sidebar.checkbox("⭐ 빈출도 높은 순으로 정렬")
    view_mode = st.sidebar.radio("모드 선택", ["전체 학습", "💛 즐겨찾기만"])
    
    filtered_df = df.copy()

    # 카테고리 필터링
    for col in ['과목', '대카테고리', '소카테고리']:
        if col in filtered_df.columns:
            options = ["전체"] + sorted(filtered_df[col].dropna().unique().tolist())
            sel = st.sidebar.selectbox(f"{col} 선택", options)
            if sel != "전체":
                filtered_df = filtered_df[filtered_df[col] == sel]

    # 즐겨찾기 필터
    if view_mode == "💛 즐겨찾기만":
        filtered_df = filtered_df[filtered_df['PK'].astype(str).isin(st.session_state.favorites)]

    # 빈도순 정렬 (기출 시트의 '빈도' 열 기준)
    if sort_by_freq and '빈도' in filtered_df.columns:
        # '1번', '2번' 등 텍스트인 경우 숫자로 변환하여 정렬
        filtered_df['빈도_num'] = filtered_df['빈도'].astype(str).str.extract('(\d+)').fillna(0).astype(int)
        filtered_df = filtered_df.sort_values(by='빈도_num', ascending=False)

    # --- 메인 화면 ---
    st.title("🏗️ 2026 초카이브 건축기사")
    
    # 중복 제거된 개념 리스트 생성
    unique_pks = filtered_df['PK'].unique()

    for pk_val in unique_pks:
        # 해당 PK에 해당하는 모든 행(개념 정보 + 기출문제들)
        concept_group = filtered_df[filtered_df['PK'] == pk_val]
        first_row = concept_group.iloc[0]
        pk_str = str(pk_val)

        # 개념 헤더
        col_title, col_fav = st.columns([0.85, 0.15])
        with col_title:
            st.markdown(f"<div class='concept-title'>{first_row['개념']}</div>", unsafe_allow_html=True)
        with col_fav:
            is_fav = pk_str in st.session_state.favorites
            if st.button("💛" if is_fav else "🤍", key=f"fav_{pk_str}"):
                if is_fav: st.session_state.favorites.remove(pk_str)
                else: st.session_state.favorites.add(pk_str)
                st.rerun()

        # 개념 내용 및 이미지
        if pd.notna(first_row['내용']):
            st.write(first_row['내용'])
        
        if '이미지' in first_row and pd.notna(first_row['이미지']):
            st.image(first_row['이미지'], use_container_width=True)

        # 기출문제 영역 (그룹화된 데이터 출력)
        with st.expander("📝 관련 기출문제 확인"):
            # 문제 내용이 실제 존재하는 행들만 필터링
            questions = concept_group[concept_group['문제'].notna()]
            
            if not questions.empty:
                for _, q_row in questions.iterrows():
                    year = q_row['년도'] if pd.notna(q_row['년도']) else "연도미상"
                    freq = q_row['빈도'] if pd.notna(q_row['빈도']) else "1"
                    
                    st.markdown(f"""
                    <div class="question-card">
                        <strong>[{year} 출제 / 빈도: {freq}]</strong><br><br>
                        {q_row['문제']}
                    </div>
                    """, unsafe_allow_html=True)
                    
                    if pd.notna(q_row['보기']):
                        st.markdown("**[보기]**")
                        st.write(q_row['보기'])
                    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
            else:
                st.info("연결된 기출문제가 없습니다.")
        
        st.divider()

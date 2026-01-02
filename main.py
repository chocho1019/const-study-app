import streamlit as st
import pandas as pd

# 1. 앱 설정
st.set_page_config(page_title="2026 초카이브 건축기사 필기", layout="wide")

# 2. 스타일 설정
st.markdown("""
    <style>
    .concept-title { font-size: 30px; font-weight: bold; color: #2E4053; }
    .stButton button { width: 100%; }
    hr { margin: 1.5rem 0; }
    </style>
    """, unsafe_allow_html=True)

# 3. 데이터 로드 및 병합 함수
@st.cache_data(ttl=300)
def load_combined_data():
    try:
        base_url = "https://docs.google.com/spreadsheets/d/1eg3TnoILIHXCzf4fPCU6uqzZssLnFS2xHO5zD7N2c0g/gviz/tq?tqx=out:csv"
        
        # [중요] 각 시트의 gid를 명시하여 데이터 로드
        # gid=0 : '개념' 시트 (일반적으로 첫 번째 탭)
        # gid=775019664 : '기출문제' 시트
        concept_df = pd.read_csv(f"{base_url}&gid=0")
        exam_df = pd.read_csv(f"{base_url}&gid=775019664")
        
        # 열 이름 공백 제거
        concept_df.columns = [col.strip() for col in concept_df.columns]
        exam_df.columns = [col.strip() for col in exam_df.columns]
        
        # '개념' 시트의 PK와 '기출문제' 시트의 FK를 기준으로 병합 (Left Join)
        # 개념은 하나인데 기출은 여러 개일 수 있으므로 merge 사용
        merged_df = pd.merge(concept_df, exam_df, left_on='PK', right_on='FK', how='left', suffixes=('', '_exam'))
        
        return merged_df
    except Exception as e:
        st.error(f"데이터 병합 실패: {e}")
        return None

df = load_combined_data()

if df is not None:
    # 세션 상태 초기화
    if 'favorites' not in st.session_state:
        st.session_state.favorites = set()

    # --- 사이드바 및 필터 (생략된 기존 로직과 동일하게 작동) ---
    st.sidebar.title("🔍 학습 필터")
    sort_by_freq = st.sidebar.checkbox("⭐ 빈출도 높은 순으로 정렬")
    view_mode = st.sidebar.radio("모드 선택", ["전체 학습", "💛 즐겨찾기만"])
    
    filtered_df = df.copy()

    # 즐겨찾기 필터 (중복 제거를 위해 PK 기준 처리)
    if view_mode == "💛 즐겨찾기만":
        filtered_df = filtered_df[filtered_df['PK'].astype(str).isin(st.session_state.favorites)]

    # 빈도순 정렬 (기출문제 시트의 '빈도' 기준)
    if sort_by_freq and '빈도' in filtered_df.columns:
        filtered_df = filtered_df.sort_values(by='빈도', ascending=False)

    # --- 메인 화면 ---
    st.title("🏗️ 초카이브 건축기사 필기")
    
    # 동일한 개념(PK)을 가진 행들을 그룹화하여 출력 (한 개념에 기출문제가 여러 개일 수 있음)
    unique_concepts = filtered_df['PK'].unique()

    for pk_val in unique_concepts:
        concept_rows = filtered_df[filtered_df['PK'] == pk_val]
        first_row = concept_rows.iloc[0]
        pk_str = str(pk_val)

        # 1. 개념 출력
        col_title, col_fav = st.columns([0.85, 0.15])
        with col_title:
            st.markdown(f"<div class='concept-title'>{first_row['개념']}</div>", unsafe_allow_html=True)
        with col_fav:
            is_fav = pk_str in st.session_state.favorites
            if st.button("💛" if is_fav else "🤍", key=f"fav_{pk_str}"):
                if is_fav: st.session_state.favorites.remove(pk_str)
                else: st.session_state.favorites.add(pk_str)
                st.rerun()

        st.write(first_row['내용'])
        
        if '이미지' in first_row and pd.notna(first_row['이미지']):
            st.image(first_row['이미지'], use_container_width=True)

        # 2. 연결된 기출문제 출력 (PK와 FK가 매칭된 모든 문제)
        with st.expander("📝 관련 기출문제 확인"):
            # 문제 내용이 있는 행만 필터링
            questions = concept_rows[concept_rows['문제'].notna()]
            
            if not questions.empty:
                for _, q_row in questions.iterrows():
                    year = q_row['년도'] if pd.notna(q_row['년도']) else "미상"
                    freq = q_row['빈도'] if pd.notna(q_row['빈도']) else "1"
                    
                    st.info(f"**[{year} 출제 / 빈도: {freq}]**\n\n{q_row['문제']}")
                    if pd.notna(q_row['보기']):
                        st.write(f"**보기:**\n{q_row['보기']}")
                    st.markdown("---")
            else:
                st.write("해당 개념과 연결된 기출문제가 없습니다.")
        
        st.divider()

import streamlit as st
import pandas as pd

# 1. 앱 설정
st.set_page_config(page_title="2025 건축기사 마스터", layout="wide")

# 2. 스타일 설정
st.markdown("""
    <style>
    .concept-title { font-size: 24px; font-weight: bold; color: #2E4053; }
    .stExpander { border: 1px solid #f0f2f6; border-radius: 10px; }
    hr { margin: 1rem 0; }
    </style>
    """, unsafe_allow_html=True)

# 3. 데이터 로드 함수 (URL을 분리하여 안정성 확보)
@st.cache_data
def load_data():
    # 시트 고유 ID
    SHEET_ID = "1eg3TnoILIHXCzf4fPCU6uqzZssLnFS2xHO5zD7N2c0g"
    
    # 개념 시트 로드 (첫번째 탭 - 보통 gid=0)
    concept_url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid=0"
    # 기출문제 시트 로드 (gid=46086374)
    quiz_url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid=46086374"
    
    try:
        c_df = pd.read_csv(concept_url)
        q_df = pd.read_csv(quiz_url)
        
        # 컬럼명 앞뒤 공백 제거
        c_df.columns = [col.strip() for col in c_df.columns]
        q_df.columns = [col.strip() for col in q_df.columns]
        
        return c_df, q_df
    except Exception as e:
        st.error(f"데이터 로드 에러 발생: {e}")
        return None, None

concept_df, quiz_df = load_data()

if concept_df is not None and quiz_df is not None:
    # 세션 상태 초기화
    if 'favorites' not in st.session_state:
        st.session_state.favorites = set()

    # --- 사이드바 필터 ---
    st.sidebar.title("🔍 학습 필터")
    view_mode = st.sidebar.radio("모드 선택", ["전체 학습", "💛 즐겨찾기만"])
    
    # 필터링용 데이터 복사
    f_df = concept_df.copy()
    
    # 위계별 필터 (열 이름이 시트와 정확히 맞아야 함)
    for col_name in ['과목', '대카테고리', '소카테고리']:
        if col_name in f_df.columns:
            options = ["전체"] + sorted(f_df[col_name].dropna().unique().tolist())
            selected = st.sidebar.selectbox(f"{col_name} 선택", options)
            if selected != "전체":
                f_df = f_df[f_df[col_name] == selected]

    if view_mode == "💛 즐겨찾기만":
        f_df = f_df[f_df['PK'].astype(str).isin(st.session_state.favorites)]

    # --- 메인 화면 ---
    st.title("🏗️ 건축기사 필기 요약노트")
    
    if f_df.empty:
        st.info("조건에 맞는 데이터가 없습니다.")
    else:
        for _, row in f_df.iterrows():
            pk = str(row['PK'])
            
            # 개념 헤더
            col_t, col_f = st.columns([0.85, 0.15])
            with col_t:
                st.markdown(f"<div class='concept-title'>{row['개념']}</div>", unsafe_allow_html=True)
            with col_f:
                is_fav = pk in st.session_state.favorites
                if st.button("💛" if is_fav else "🤍", key=f"btn_{pk}"):
                    if is_fav: st.session_state.favorites.remove(pk)
                    else: st.session_state.favorites.add(pk)
                    st.rerun()
            
            # 내용
            st.write(row['내용'])
            
            # 이미지
            if '이미지' in row and pd.notna(row['이미지']) and str(row['이미지']).startswith('http'):
                st.image(row['이미지'], use_container_width=True)
            
            # 기출문제 매핑 (PK-FK 연동)
            with st.expander("📝 해당 기출문제 확인"):
                # 기출문제 시트의 'FK' 열과 개념 시트의 'PK' 열을 대조
                matched = quiz_df[quiz_df['FK'].astype(str) == pk]
                
                if not matched.empty:
                    for _, q_row in matched.iterrows():
                        st.info(f"**[{q_row['기출문제(출제년도)']}]**\n\n{q_row['기출문제(질문)']}")
                        st.write(f"보기: {q_row['기출문제(보기)']}")
                        st.success(f"정답: {q_row['정답']}")
                        st.markdown("---")
                else:
                    st.write("연결된 기출문제가 없습니다.")
            st.divider()

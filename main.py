import streamlit as st
import pandas as pd

# 1. 앱 설정
st.set_page_config(page_title="2025 건축기사 마스터", layout="wide")

# 2. 스타일 설정 (매개변수 오타 수정: unsafe_allow_html=True)
st.markdown("""
    <style>
    .concept-title { font-size: 24px; font-weight: bold; color: #2E4053; }
    hr { margin-top: 1rem; margin-bottom: 1rem; }
    </style>
    """, unsafe_allow_html=True)

# 3. 데이터 로드 함수
@st.cache_data
def load_data(url):
    try:
        df = pd.read_csv(url)
        df.columns = [col.strip() for col in df.columns]  # 컬럼명 공백 제거
        return df
    except Exception as e:
        st.error(f"데이터 로드 실패: {e}")
        return None

# 구글 시트 CSV 링크
SHEET_URL = "https://docs.google.com/spreadsheets/d/1eg3TnoILIHXCzf4fPCU6uqzZssLnFS2xHO5zD7N2c0g/gviz/tq?tqx=out:csv"
df = load_data(SHEET_URL)

if df is not None:
    # 세션 상태 초기화
    if 'favorites' not in st.session_state:
        st.session_state.favorites = set()

    # --- 사이드바: 필터 설정 ---
    st.sidebar.title("🔍 학습 필터")
    view_mode = st.sidebar.radio("모드 선택", ["전체 학습", "⭐ 즐겨찾기만"])
    
    # 과목 선택
    sub_list = ["전체"] + sorted(df['과목'].dropna().unique().tolist())
    sel_sub = st.sidebar.selectbox("과목", sub_list)
    
    filtered_df = df.copy()
    if sel_sub != "전체":
        filtered_df = filtered_df[filtered_df['과목'] == sel_sub]

    # 대카테고리 선택
    major_list = ["전체"] + sorted(filtered_df['대카테고리'].dropna().unique().tolist())
    sel_major = st.sidebar.selectbox("대카테고리", major_list)
    if sel_major != "전체":
        filtered_df = filtered_df[filtered_df['대카테고리'] == sel_major]

    # 소카테고리 선택
    minor_list = ["전체"] + sorted(filtered_df['소카테고리'].dropna().unique().tolist())
    sel_minor = st.sidebar.selectbox("소카테고리", minor_list)
    if sel_minor != "전체":
        filtered_df = filtered_df[filtered_df['소카테고리'] == sel_minor]

    # 즐겨찾기 필터 적용
    if view_mode == "⭐ 즐겨찾기만":
        filtered_df = filtered_df[filtered_df['PK'].astype(str).isin(st.session_state.favorites)]

    # --- 메인 화면 ---
    st.title("🏗️ 건축기사 필기 요약노트")
    
    if filtered_df.empty:
        st.info("해당하는 데이터가 없습니다.")
    else:
        for _, row in filtered_df.iterrows():
            pk = str(row['PK'])
            
            # 제목과 즐겨찾기 버튼
            col_t, col_f = st.columns([0.8, 0.2])
            with col_t:
                st.markdown(f"<div class='concept-title'>{row['개념']}</div>", unsafe_allow_html=True)
            with col_f:
                is_fav = pk in st.session_state.favorites
                if st.button("★" if is_fav else "☆", key=f"btn_{pk}"):
                    if is_fav: st.session_state.favorites.remove(pk)
                    else: st.session_state.favorites.add(pk)
                    st.rerun()
            
            # 상세 내용
            st.write(row['내용'])
            
            # 이미지 출력 (URL 형식일 때만)
            if '이미지' in row and pd.notna(row['이미지']) and str(row['이미지']).startswith('http'):
                st.image(row['이미지'], use_container_width=True)
            
            # 기출문제 토글
            with st.expander("📝 해당 기출문제 확인"):
                if pd.notna(row['기출문제(질문)']):
                    st.info(f"**{row['기출문제(출제년도)']} 출제**\n\n{row['기출문제(질문)']}")
                    st.write(f"보기: {row['기출문제(보기)']}")
                    st.success(f"정답: {row['정답']}")
                else:
                    st.write("연결된 기출문제가 없습니다.")
            st.divider()

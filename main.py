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
    .question-box { background-color: #f0f2f6; padding: 15px; border-radius: 10px; border-left: 5px solid #2E4053; }
    </style>
    """, unsafe_allow_html=True)

# 3. 데이터 로드 함수
@st.cache_data(ttl=300) # 5분마다 업데이트
def load_data(url):
    try:
        # 데이터 로드 및 열 이름 공백 제거
        df = pd.read_csv(url)
        df.columns = [col.strip() for col in df.columns]
        return df
    except Exception as e:
        st.error(f"데이터 로드 실패: {e}")
        return None

# 구글 시트 CSV 링크 (시트 탭 gid 확인 필요)
# 기출문제 탭의 gid가 포함된 링크여야 정확한 열을 불러옵니다.
SHEET_URL = "https://docs.google.com/spreadsheets/d/1eg3TnoILIHXCzf4fPCU6uqzZssLnFS2xHO5zD7N2c0g/gviz/tq?tqx=out:csv"
df = load_data(SHEET_URL)

if df is not None:
    # 세션 상태 초기화
    if 'favorites' not in st.session_state:
        st.session_state.favorites = set()

    # --- 사이드바: 필터 설정 ---
    st.sidebar.title("🔍 학습 필터")
    
    # 빈출도순 정렬 (시트의 '빈도' 열 기준)
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

    # 빈도순 정렬 실행 (스크린샷의 '빈도' 열 반영)
    if sort_by_freq and '빈도' in filtered_df.columns:
        filtered_df = filtered_df.sort_values(by='빈도', ascending=False)

    # --- 메인 화면 ---
    st.title("🏗️ 초카이브 건축기사 필기")
    
    if filtered_df.empty:
        st.info("조건에 맞는 데이터가 없습니다. 필터를 조정해 보세요.")
    else:
        for idx, row in filtered_df.iterrows():
            pk = str(row['PK']) if 'PK' in row else str(idx)
            
            # 개념 헤더
            col_title, col_fav = st.columns([0.85, 0.15])
            with col_title:
                concept_name = row['개념'] if '개념' in row else "제목 없음"
                st.markdown(f"<div class='concept-title'>{concept_name}</div>", unsafe_allow_html=True)
            with col_fav:
                is_fav = pk in st.session_state.favorites
                if st.button("💛" if is_fav else "🤍", key=f"fav_{pk}"):
                    if is_fav: st.session_state.favorites.remove(pk)
                    else: st.session_state.favorites.add(pk)
                    st.rerun()
            
            # 내용 및 이미지
            if '내용' in row and pd.notna(row['내용']):
                st.write(row['내용'])
            
            if '이미지' in row and pd.notna(row['이미지']):
                img_url = str(row['이미지']).strip()
                if img_url.startswith('http'):
                    st.image(img_url, use_container_width=True)
            
            # --- [수정 포인트] 기출문제 연동 (스크린샷 기준) ---
            with st.expander("📝 관련 기출문제 확인"):
                # 스크린샷에 명시된 '문제' 열 확인
                if '문제' in row and pd.notna(row['문제']):
                    # '년도' 및 '빈도' 정보 추출
                    year_info = f" ({row['년도']})" if '년도' in row and pd.notna(row['년도']) else ""
                    freq_info = f" [출제: {row['빈도']}]" if '빈도' in row and pd.notna(row['빈도']) else ""
                    
                    st.markdown(f"**질문{year_info}{freq_info}**")
                    st.info(row['문제'])
                    
                    # '보기' 열 출력
                    if '보기' in row and pd.notna(row['보기']):
                        st.markdown("**[보기]**")
                        # 보기 내용에 줄바꿈이 있다면 반영하여 출력
                        st.write(row['보기'])
                else:
                    st.write("해당 개념과 연결된 기출문제가 없습니다.")
            
            st.divider()

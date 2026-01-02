import streamlit as st
import pandas as pd

# 1. 앱 설정
st.set_page_config(page_title="2025 건축기사 마스터", layout="wide")

# 2. 스타일 설정
st.markdown("""
    <style>
    .concept-title { font-size: 24px; font-weight: bold; color: #2E4053; }
    .stButton button { width: 100%; }
    hr { margin: 1.5rem 0; }
    </style>
    """, unsafe_allow_html=True)



# 3. 데이터 로드 함수 (개선됨)
@st.cache_data(ttl=600)  # 10분마다 캐시 갱신
def load_data(url):
    try:
        # csv 변환 주소 확인
        csv_url = url.replace('/edit?gid=', '/export?format=csv&gid=')
        df = pd.read_csv(csv_url)
        
        # 모든 컬럼명의 앞뒤 공백 제거 및 문자열화
        df.columns = [str(col).strip() for col in df.columns]
        
        # 데이터프레임 전체의 문자열 앞뒤 공백 제거
        df = df.applymap(lambda x: x.strip() if isinstance(x, str) else x)
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
    
    # 빈출도순 정렬 (최상단에 배치)
    sort_by_freq = st.sidebar.checkbox("⭐ 빈출도 높은 순으로 정렬")
    
    view_mode = st.sidebar.radio("모드 선택", ["전체 학습", "💛 즐겨찾기만"])
    
    # 위계적 필터링
    filtered_df = df.copy()

    # 1. 과목
    if '과목' in filtered_df.columns:
        sub_list = ["전체"] + sorted(filtered_df['과목'].dropna().unique().tolist())
        sel_sub = st.sidebar.selectbox("과목 선택", sub_list)
        if sel_sub != "전체":
            filtered_df = filtered_df[filtered_df['과목'] == sel_sub]

    # 2. 대카테고리
    if '대카테고리' in filtered_df.columns:
        major_list = ["전체"] + sorted(filtered_df['대카테고리'].dropna().unique().tolist())
        sel_major = st.sidebar.selectbox("대카테고리 선택", major_list)
        if sel_major != "전체":
            filtered_df = filtered_df[filtered_df['대카테고리'] == sel_major]

    # 3. 소카테고리
    if '소카테고리' in filtered_df.columns:
        minor_list = ["전체"] + sorted(filtered_df['소카테고리'].dropna().unique().tolist())
        sel_minor = st.sidebar.selectbox("소카테고리 선택", minor_list)
        if sel_minor != "전체":
            filtered_df = filtered_df[filtered_df['소카테고리'] == sel_minor]

    # 즐겨찾기 필터 적용
    if view_mode == "💛 즐겨찾기만":
        filtered_df = filtered_df[filtered_df['PK'].astype(str).isin(st.session_state.favorites)]

    # 빈출도 정렬 실행
    if sort_by_freq and '빈출' in filtered_df.columns:
        filtered_df = filtered_df.sort_values(by='빈출', ascending=False)

    # --- 메인 화면 ---
    st.title("🏗️ 건축기사 필기 요약노트")
    
    if filtered_df.empty:
        st.info("조건에 맞는 데이터가 없습니다. 필터를 조정해 보세요.")
    else:
        for _, row in filtered_df.iterrows():
            # PK가 없을 경우 인덱스를 대신 사용
            pk = str(row['PK']) if 'PK' in row else str(_)
            
            # 개념 헤더 영역
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
            
            # 본문 내용
            if '내용' in row:
                st.write(row['내용'])
            
            # 이미지 출력
            if '이미지' in row and pd.notna(row['이미지']):
                img_url = str(row['이미지']).strip()
                if img_url.startswith('http'):
                    st.image(img_url, use_container_width=True)
            
            # --- 기출문제 영역 (수정 포인트) ---
            with st.expander("📝 관련 기출문제 확인하기"):
                # 실제 시트의 컬럼명과 정확히 일치해야 함
                q_text = row.get('기출문제(질문)', None)
                
                # 데이터가 존재하고, 문자열로 변환했을 때 길이가 0보다 큰지 확인
                if pd.notna(q_text) and str(q_text).strip() != "":
                    year = row.get('기출문제(출제년도)', '연도 미상')
                    st.markdown(f"**[{year} 출제]**")
                    st.info(q_text)
                    
                    if '기출문제(보기)' in row and pd.notna(row['기출문제(보기)']):
                        st.markdown("**[보기]**")
                        st.write(row['기출문제(보기)'])
                    
                    if '정답' in row and pd.notna(row['정답']):
                        st.success(f"✅ 정답: {row['정답']}")
                else:
                    st.write("⚠️ 이 개념은 아직 등록된 기출문제가 없습니다.")
            
            st.divider()

import streamlit as st
import pandas as pd
import random

# -----------------------------------------------------------------------------
# 1. 앱 설정 및 상수 정의
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="2025 건축기사 마스터",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 구글 시트 ID와 GID (제공해주신 URL 분석 결과)
SHEET_ID = "1eg3TnoILIHXCzf4fPCU6uqzZssLnFS2xHO5zD7N2c0g"
GID = "46086374"  # 특정 시트 탭 ID
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID}"

# -----------------------------------------------------------------------------
# 2. 스타일 설정 (CSS)
# -----------------------------------------------------------------------------
st.markdown("""
    <style>
    /* 전체 폰트 및 배경 설정 */
    .main { background-color: #F8F9FA; }
    
    /* 개념 카드 스타일 */
    .concept-card {
        background-color: white;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin-bottom: 20px;
        border-left: 5px solid #4A90E2;
    }
    .concept-title { 
        font-size: 22px; 
        font-weight: 700; 
        color: #2E4053; 
        margin-bottom: 10px;
    }
    .badge {
        display: inline-block;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 12px;
        font-weight: bold;
        color: white;
        margin-right: 5px;
    }
    .badge-subject { background-color: #6C757D; }
    .badge-important { background-color: #DC3545; }
    
    /* 기출문제 박스 */
    .quiz-box {
        background-color: #E9F7EF;
        padding: 15px;
        border-radius: 8px;
        margin-top: 15px;
        border: 1px solid #D4EFDF;
    }
    </style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 3. 데이터 로드 및 전처리 함수
# -----------------------------------------------------------------------------
@st.cache_data(ttl=600)  # 10분마다 캐시 갱신
def load_data(url):
    try:
        df = pd.read_csv(url)
        # 컬럼명 앞뒤 공백 제거
        df.columns = [col.strip() for col in df.columns]
        
        # 필수 컬럼 존재 여부 확인 및 데이터 타입 정리
        if 'PK' not in df.columns:
            df['PK'] = df.index  # PK가 없으면 인덱스 사용
        
        df['PK'] = df['PK'].astype(str) # PK는 문자열로 통일
        
        # 빈출 컬럼이 있다면 숫자로 변환 (오류 방지)
        if '빈출' in df.columns:
            df['빈출'] = pd.to_numeric(df['빈출'], errors='coerce').fillna(0)
            
        return df
    except Exception as e:
        st.error(f"❌ 데이터 로드 중 오류가 발생했습니다: {e}")
        return pd.DataFrame()

# -----------------------------------------------------------------------------
# 4. 메인 로직
# -----------------------------------------------------------------------------
def main():
    # 데이터 로드
    df = load_data(CSV_URL)
    
    if df.empty:
        st.warning("데이터를 불러오지 못했습니다. 인터넷 연결이나 구글 시트 공유 설정을 확인해주세요.")
        return

    # 세션 상태 초기화 (즐겨찾기)
    if 'favorites' not in st.session_state:
        st.session_state.favorites = set()

    # --- 사이드바: 필터 및 제어 ---
    with st.sidebar:
        st.title("🔍 학습 필터")
        
        # 1. 검색 기능 (신규)
        search_query = st.text_input("검색 (키워드 입력)", placeholder="예: 콘크리트, 강도...")

        # 2. 필터링 (위계 구조)
        filtered_df = df.copy()
        
        # 검색어 필터링
        if search_query:
            mask = filtered_df.astype(str).apply(lambda x: x.str.contains(search_query, case=False, na=False)).any(axis=1)
            filtered_df = filtered_df[mask]

        # 과목 필터
        if '과목' in df.columns:
            subjects = ["전체"] + sorted(df['과목'].dropna().unique().tolist())
            selected_subject = st.selectbox("과목", subjects)
            if selected_subject != "전체":
                filtered_df = filtered_df[filtered_df['과목'] == selected_subject]

        # 카테고리 필터 (동적 로딩)
        if '대카테고리' in df.columns:
            # 선택된 과목에 해당하는 대카테고리만 표시
            available_majors = filtered_df['대카테고리'].dropna().unique().tolist()
            majors = ["전체"] + sorted(available_majors)
            selected_major = st.selectbox("대카테고리", majors)
            if selected_major != "전체":
                filtered_df = filtered_df[filtered_df['대카테고리'] == selected_major]

        st.divider()

        # 3. 보기 모드 및 정렬
        view_mode = st.radio("보기 모드", ["전체 학습", "💛 즐겨찾기만", "🎲 랜덤 1문제"], index=0)
        
        sort_by_freq = False
        if view_mode != "🎲 랜덤 1문제":
            sort_by_freq = st.checkbox("⭐ 빈출도 높은 순 정렬")

        st.info(f"총 **{len(df)}**개 중 **{len(filtered_df)}**개 학습 가능")

    # --- 데이터 필터링 로직 적용 ---
    
    # 즐겨찾기 모드
    if view_mode == "💛 즐겨찾기만":
        filtered_df = filtered_df[filtered_df['PK'].isin(st.session_state.favorites)]
    
    # 랜덤 모드
    elif view_mode == "🎲 랜덤 1문제":
        if not filtered_df.empty:
            filtered_df = filtered_df.sample(1)
        else:
            st.warning("조건에 맞는 데이터가 없어 랜덤 선택을 할 수 없습니다.")

    # 정렬
    if sort_by_freq and '빈출' in filtered_df.columns:
        filtered_df = filtered_df.sort_values(by='빈출', ascending=False)

    # --- 메인 콘텐츠 영역 ---
    st.title("🏗️ 2025 건축기사 필기 마스터")
    st.caption("건축기사 합격을 위한 요약노트 및 기출문제 뷰어입니다.")
    st.divider()

    if filtered_df.empty:
        st.info("조건에 맞는 학습 카드가 없습니다. 필터를 변경해보세요.")
    else:
        # 카드 렌더링
        for idx, row in filtered_df.iterrows():
            pk = row['PK']
            is_fav = pk in st.session_state.favorites
            
            # HTML/CSS 컨테이너 시작
            st.markdown(f"""
            <div class="concept-card">
                <div>
                    <span class="badge badge-subject">{row['과목'] if '과목' in row else '공통'}</span>
                    {'<span class="badge badge-important">⭐ 빈출</span>' if '빈출' in row and row['빈출'] >= 3 else ''}
                </div>
            """, unsafe_allow_html=True)
            
            # 제목 및 즐겨찾기 버튼 (컬럼 분할)
            col1, col2 = st.columns([0.9, 0.1])
            with col1:
                concept_title = row['개념'] if pd.notna(row.get('개념')) else "제목 없음"
                st.markdown(f"<div class='concept-title'>{concept_title}</div>", unsafe_allow_html=True)
            with col2:
                # 버튼 클릭 시 리렌더링 발생
                if st.button("💛" if is_fav else "🤍", key=f"btn_{pk}", help="즐겨찾기 추가/해제"):
                    if is_fav:
                        st.session_state.favorites.remove(pk)
                    else:
                        st.session_state.favorites.add(pk)
                    st.rerun()

            # 본문 내용
            if '내용' in row and pd.notna(row['내용']):
                st.markdown(row['내용'])

            # 이미지
            if '이미지' in row and pd.notna(row['이미지']):
                img_url = str(row['이미지']).strip()
                if img_url.startswith('http'):
                    st.image(img_url, use_container_width=True)

            # 기출문제 영역 (Expander로 숨김 처리하여 학습 효과 증대)
            q_col = '기출문제(질문)' # 컬럼명 매칭
            if q_col in row and pd.notna(row[q_col]):
                with st.expander("📝 실전 기출문제 풀어보기"):
                    st.markdown('<div class="quiz-box">', unsafe_allow_html=True)
                    
                    # 문제 정보
                    q_year = row.get('기출문제(출제년도)', '')
                    st.caption(f"📅 {q_year} 기출" if pd.notna(q_year) else "📅 기출 연도 미상")
                    
                    # 질문
                    st.markdown(f"**Q. {row[q_col]}**")
                    
                    # 보기
                    if '기출문제(보기)' in row and pd.notna(row['기출문제(보기)']):
                        st.code(row['기출문제(보기)'], language="text")
                    
                    st.markdown("---")
                    
                    # 정답 확인 버튼 (토글 대신 세션 스테이트 사용 안 함 -> 즉시 확인용)
                    # 팁: expander 안에 또다른 expander는 안되지만, 간단히 정답을 숨기는 UI
                    if '정답' in row and pd.notna(row['정답']):
                        if st.checkbox("정답 확인하기", key=f"chk_{pk}"):
                             st.success(f"✅ 정답: {row['정답']}")
                             if '해설' in row and pd.notna(row['해설']):
                                 st.info(f"💡 해설: {row['해설']}")
                    
                    st.markdown('</div>', unsafe_allow_html=True)

            st.markdown("</div>", unsafe_allow_html=True) # 카드 닫기

if __name__ == "__main__":
    main()

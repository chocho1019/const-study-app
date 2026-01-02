import streamlit as st
import pandas as pd

# 1. 앱 설정 및 스타일링
st.set_page_config(page_title="건축기사 마스터", layout="wide")
st.markdown("""
    <style>
    .concept-title { font-size: 24px; font-weight: bold; color: #2E4053; }
    .favorite-btn { float: right; }
    </style>
    """, unsafe_allow_stdio=True)

# 2. 데이터 로드 (캐싱)
@st.cache_data
def load_data():
    # 실제 구글 시트 CSV 내보내기 링크
    url = "https://docs.google.com/spreadsheets/d/1eg3TnoILIHXCzf4fPCU6uqzZssLnFS2xHO5zD7N2c0g/gviz/tq?tqx=out:csv"
    df = pd.read_csv(url)
    return df

df = load_data()

# 3. 세션 상태 초기화 (즐겨찾기 저장용)
if 'favorites' not in st.session_state:
    st.session_state.favorites = set()

# --- 사이드바 및 필터부 ---
st.sidebar.title("📚 학습 메뉴")
view_mode = st.sidebar.radio("보기 모드", ["전체 학습", "⭐ 즐겨찾기만 보기"])
sort_by_freq = st.sidebar.checkbox("빈출도 높은 순으로 정렬")

# 필터링용 데이터 준비
if view_mode == "⭐ 즐겨찾기만 보기":
    display_df = df[df['PK'].astype(str).isin(st.session_state.favorites)]
else:
    display_df = df.copy()

# 과목-대-소 카테고리 선택 (상단 배치)
col1, col2, col3 = st.columns(3)
with col1:
    subjects = ["전체"] + sorted(display_df['과목'].unique().tolist())
    sel_subject = st.selectbox("과목 선택", subjects)

# 위계에 따른 필터링
if sel_subject != "전체":
    display_df = display_df[display_df['과목'] == sel_subject]

with col2:
    major_cats = ["전체"] + sorted(display_df['대카테고리'].unique().tolist())
    sel_major = st.selectbox("대카테고리 선택", major_cats)

if sel_major != "전체":
    display_df = display_df[display_df['대카테고리'] == sel_major]

with col3:
    minor_cats = ["전체"] + sorted(display_df['소카테고리'].unique().tolist())
    sel_minor = st.selectbox("소카테고리 선택", minor_cats)

if sel_minor != "전체":
    display_df = display_df[display_df['소카테고리'] == sel_minor]

# 빈출도 정렬 적용
if sort_by_freq:
    display_df = display_df.sort_values(by='빈출', ascending=False)

st.divider()

# --- 메인 콘텐츠 영역 ---
if display_df.empty:
    st.info("조건에 맞는 내용이 없습니다.")
else:
    for _, row in display_df.iterrows():
        pk_val = str(row['PK'])
        
        # 개념 제목 및 즐겨찾기 행
        header_col, fav_col = st.columns([0.85, 0.15])
        with header_col:
            st.markdown(f"<div class='concept-title'>{row['개념']}</div>", unsafe_allow_stdio=True)
        with fav_col:
            # 별표 버튼 상태 제어
            is_fav = pk_val in st.session_state.favorites
            btn_label = "★" if is_fav else "☆"
            if st.button(btn_label, key=f"fav_{pk_val}"):
                if is_fav:
                    st.session_state.favorites.remove(pk_val)
                else:
                    st.session_state.favorites.add(pk_val)
                st.rerun()

        # 개념 내용 및 이미지
        st.write(row['내용'])
        
        # 이미지 컬럼이 있고 데이터가 있는 경우만 출력
        if '이미지' in row and pd.notna(row['이미지']):
            st.image(row['이미지'], caption=f"{row['개념']} 관련 이미지")
        
        # 기출문제 토글 (PK-FK 연동)
        # 구글 시트 내에서 같은 시트 혹은 다른 시트의 데이터를 FK로 조회
        # 여기서는 동일 시트 내에 기출 정보가 있다고 가정
        with st.expander("📝 해당 기출문제 확인하기"):
            if pd.notna(row['기출문제 (질문)']):
                st.write(f"**[{row['기출문제(출제년도)']}]**")
                st.write(row['기출문제 (질문)'])
                st.caption(row['기출문제 (보기)'])
                st.success(f"정답: {row['정답']}")
            else:
                st.write("연결된 기출문제가 없습니다.")
        
        st.divider()

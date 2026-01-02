import streamlit as st
import pandas as pd

# --------------------------------------------------
# 1. 앱 설정
# --------------------------------------------------
st.set_page_config(page_title="2025 건축기사 마스터", layout="wide")

# --------------------------------------------------
# 2. 스타일
# --------------------------------------------------
st.markdown("""
<style>
.app-logo {
    font-size: 14px;
    font-weight: 500;
    color: #9aa0a6;
    text-align: right;
    margin-bottom: 1rem;
}

.concept-title {
    font-size: 24px;
    font-weight: bold;
    color: #2E4053;
}

.heart-btn button {
    background: none;
    border: none;
    padding: 0;
    font-size: 22px;
    cursor: pointer;
}

hr { margin: 1.5rem 0; }
</style>
""", unsafe_allow_html=True)

# --------------------------------------------------
# 3. 데이터 로드
# --------------------------------------------------
@st.cache_data
def load_sheet(csv_url):
    df = pd.read_csv(csv_url)
    df.columns = df.columns.str.strip()
    df["PK"] = df["PK"].astype(str).str.strip()
    return df

CONCEPT_URL = "https://docs.google.com/spreadsheets/d/1eg3TnoILIHXCzf4fPCU6uqzZssLnFS2xHO5zD7N2c0g/gviz/tq?tqx=out:csv&gid=775019664"
QUESTION_URL = "https://docs.google.com/spreadsheets/d/1eg3TnoILIHXCzf4fPCU6uqzZssLnFS2xHO5zD7N2c0g/gviz/tq?tqx=out:csv&gid=46086374"

df_concept = load_sheet(CONCEPT_URL)
df_question = load_sheet(QUESTION_URL)

df = df_concept.merge(df_question, on="PK", how="left")

# --------------------------------------------------
# 4. 세션 상태
# --------------------------------------------------
if "favorites" not in st.session_state:
    st.session_state.favorites = set()

# --------------------------------------------------
# 5. 상단 로고
# --------------------------------------------------
st.markdown(
    "<div class='app-logo'>🏗️ 건축기사 필기 요약노트</div>",
    unsafe_allow_html=True
)

# --------------------------------------------------
# 6. 사이드바 필터
# --------------------------------------------------
st.sidebar.title("🔍 학습 필터")

sort_by_freq = st.sidebar.checkbox("⭐ 빈출도 높은 순")
view_mode = st.sidebar.radio("모드 선택", ["전체 학습", "💛 즐겨찾기만"])

filtered_df = df.copy()

for col, label in [
    ("과목", "과목"),
    ("대카테고리", "대카테고리"),
    ("소카테고리", "소카테고리"),
]:
    if col in filtered_df.columns:
        options = ["전체"] + sorted(filtered_df[col].dropna().unique())
        sel = st.sidebar.selectbox(f"{label} 선택", options)
        if sel != "전체":
            filtered_df = filtered_df[filtered_df[col] == sel]

if view_mode == "💛 즐겨찾기만":
    filtered_df = filtered_df[filtered_df["PK"].isin(st.session_state.favorites)]

if sort_by_freq and "빈출" in filtered_df.columns:
    filtered_df = filtered_df.sort_values("빈출", ascending=False)

# --------------------------------------------------
# 7. 메인 화면 (⚠️ filtered_df 사용)
# --------------------------------------------------
if filtered_df.empty:
    st.info("선택한 조건에 해당하는 개념이 없습니다.")
else:
    for idx, (_, row) in enumerate(filtered_df.iterrows()):
        pk = row["PK"]
        is_fav = pk in st.session_state.favorites

        col_heart, col_title = st.columns([0.05, 0.95])

        with col_heart:
            if st.button(
                "💛" if is_fav else "🤍",
                key=f"fav_{pk}_{idx}",
                help="즐겨찾기",
            ):
                if is_fav:
                    st.session_state.favorites.remove(pk)
                else:
                    st.session_state.favorites.add(pk)
                st.rerun()

        with col_title:
            st.markdown(
                f"<div class='concept-title'>{row.get('개념','제목 없음')}</div>",
                unsafe_allow_html=True
            )

        if pd.notna(row.get("내용")):
            st.write(row["내용"])

        with st.expander("📝 관련 기출문제 확인"):
            if pd.notna(row.get("기출문제(질문)")):
                year = row.get("기출문제(출제년도)", "연도 미상")

                question_block = f"""
**[{year} 출제]**  
**Q.{row['기출문제(질문)']}**
"""

                if pd.notna(row.get("기출문제(보기)")):
                    question_block += f"""
  
{row['기출문제(보기)']}
"""

                st.info(question_block)

                if pd.notna(row.get("정답")):
                    st.success(f"정답: {row['정답']}")
            else:
                st.write("연결된 기출문제가 없습니다.")

        st.divider()


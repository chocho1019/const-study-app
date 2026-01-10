import streamlit as st
import pandas as pd
import uuid
import datetime
import gspread
from google.oauth2.service_account import Credentials

# --------------------------------------------------
# 이미지 URL 변환 함수
# --------------------------------------------------
def get_direct_url(url):
    if not isinstance(url, str):
        return ""
    if "drive.google.com" in url:
        file_id = ""
        if "id=" in url:
            parts = url.split("id=")
            if len(parts) > 1:
                file_id = parts[1].split("&")[0]
        elif "file/d/" in url:
            parts = url.split("file/d/")
            if len(parts) > 1:
                file_id = parts[1].split("/")[0]

        if file_id:
            return f"https://drive.google.com/thumbnail?id={file_id}&sz=w1000"
    return url

# --------------------------------------------------
# Google Sheet 연결
# --------------------------------------------------
SCOPE = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

SPREADSHEET_ID = "1eg3TnoILIHXCzf4fPCU6uqzZssLnFS2xHO5zD7N2c0g"

@st.cache_resource
def get_gspread_client():
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=SCOPE
    )
    return gspread.authorize(creds)

gc = get_gspread_client()

@st.cache_resource
def get_working_sheets():
    try:
        doc = gc.open_by_key(SPREADSHEET_ID)
        return doc.worksheet("users"), doc.worksheet("favorites")
    except:
        return None, None

user_sheet, fav_sheet = get_working_sheets()

# --------------------------------------------------
# 앱 설정
# --------------------------------------------------
st.set_page_config(page_title="2026 건축기사 필기 (초카이브)", layout="wide")

# --------------------------------------------------
# 스타일 (❌ 변경 없음)
# --------------------------------------------------
st.markdown("""
<style>
.concept-card {
    background-color: #f8f9fa;
    padding: 20px;
    border-radius: 12px;
    border: 1px solid #eee;
    margin-bottom: 20px;
}
.title-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 10px;
    border-bottom: 2px solid #eaeaea;
    padding-bottom: 8px;
}
.concept-title-text {
    font-size: 20px;
    font-weight: bold;
    color: #2E4053;
}
.freq-badge {
    border: 1px solid #bbb;
    color: #777;
    border-radius: 4px;
    padding: 2px 8px;
    font-size: 13px;
}
.section-gap { height: 30px; }
.question-box {
    background-color: #f8f9fa;
    padding: 15px;
    border-radius: 8px;
    margin-bottom: 12px;
    border: 1px solid #e0e0e0;
}
.q-year { color: #888; font-size: 12px; }
.q-text { font-weight: bold; color: #2E4053; }
.a-text { color: #444; font-size: 14px; line-height: 1.5; }
.app-logo {
    font-size: 12px;
    color: #a8b3b4;
    text-align: right;
}
</style>
""", unsafe_allow_html=True)

# --------------------------------------------------
# 데이터 로드
# --------------------------------------------------
@st.cache_data(ttl=600)
def load_data():
    doc = gc.open_by_key(SPREADSHEET_ID)
    sheet = doc.worksheet("테스트용")
    values = sheet.get_all_values()
    df = pd.DataFrame(values[1:], columns=values[0])
    df.columns = df.columns.str.strip()
    return df

df = load_data()

# --------------------------------------------------
# 메인 렌더링
# --------------------------------------------------
grouped = df.groupby("PK", sort=False)

def render_concept_block(row, pk):
    num_val = str(row.get("숫구", pk)).replace(".0", "")
    freq = str(row.get("개념빈출", "")).strip()
    badge = f"<div class='freq-badge'>{freq}회</div>" if freq else ""

    st.markdown(f"""
    <div class='title-row'>
        <div class='concept-title-text'>{num_val}) {row.get('구분','')}</div>
        {badge}
    </div>
    """, unsafe_allow_html=True)

    # ✅ 개념 (마크다운 + <br> 그대로)
    concept_html = str(row.get("개념", "")).replace("\n", "<br>")
    st.markdown(f"<div>{concept_html}</div>", unsafe_allow_html=True)

    # ✅ 개념 이미지 (개념 바로 아래)
    img_url = get_direct_url(row.get("개념이미지URL", ""))
    if img_url:
        st.markdown(f"""
        <div style="margin-top:4px;">
            <img src="{img_url}" style="max-width:100%; border-radius:8px;">
        </div>
        """, unsafe_allow_html=True)

def render_questions(qs):
    st.markdown("<div class='section-gap'></div>", unsafe_allow_html=True)
    with st.expander(f"📝 관련 기출문제 ({len(qs)}건)"):
        for _, q in qs.iterrows():
            year = q.get("출제년도", "")
            answer_html = str(q.get("정답", "")).replace("\n", "<br>")
            problem_url = q.get("문제URL", "")

            st.markdown(f"""
            <div class='question-box'>
                <div class='q-year'>[{year}]</div>
                <div class='q-text'>Q. {q.get("문제","")}</div>
                <div class='a-text'>
                    {answer_html}
                    {"<br><a href='"+problem_url+"' target='_blank'>🔗 문제 원문</a>" if problem_url else ""}
                </div>
            </div>
            """, unsafe_allow_html=True)

for pk, group in grouped:
    row = group.iloc[0]
    render_concept_block(row, pk)
    qs = group[group["문제"].str.strip() != ""]
    render_questions(qs)
    st.divider()

st.markdown("<div class='app-logo'>ⓒ초카이브 건축기사</div>", unsafe_allow_html=True)

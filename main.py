import streamlit as st
import pandas as pd
import uuid
import datetime
import gspread
from google.oauth2.service_account import Credentials

# --------------------------------------------------
# 추가: 이미지 URL 변환 함수
# --------------------------------------------------
def get_direct_url(url):
    if not isinstance(url, str):
        return ""
    if "drive.google.com" in url:
        file_id = ""
        # URL에서 ID 추출 (다양한 형식 대응)
        if "id=" in url:
            parts = url.split("id=")
            if len(parts) > 1:
                file_id = parts[1].split("&")[0]
        elif "file/d/" in url:
            parts = url.split("file/d/")
            if len(parts) > 1:
                file_id = parts[1].split("/")[0]
        
        if file_id:
            # uc 방식 대신 더 안정적인 thumbnail 방식으로 변환
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

# 전역 변수로 설정
gc = get_gspread_client()

@st.cache_resource
def get_working_sheets():
    try:
        doc = gc.open_by_key(SPREADSHEET_ID)
        # users, favorites 시트는 그대로 유지
        return doc.worksheet("users"), doc.worksheet("favorites")
    except Exception as e:
        return None, None

user_sheet, fav_sheet = get_working_sheets()


# --------------------------------------------------
# 1. 앱 설정
# --------------------------------------------------
st.set_page_config(page_title="2026 건축기사 필기 (초카이브)", layout="wide")

# --------------------------------------------------
# 2. 스타일
# --------------------------------------------------

st.markdown("""
<style>
/* 암기카드 전용 배경 박스 */
.concept-card {
    background-color: #f8f9fa;
    padding: 20px;
    border-radius: 12px;
    border: 1px solid #eee;
    margin-bottom: 20px;
}

/* 박스 안의 제목 스타일 */
.concept-title-card {
    font-size: 22px;
    font-weight: bold;
    color: #2E4053;
    margin-bottom: 15px;
}

/* 박스 안의 내용 스타일 */
.concept-content-card {
    font-size: 16px;
    color: #333;
    line-height: 1.6;
}
/* 마크다운 테이블 스타일 보정 */
.concept-content-card table {
    width: 100%;
    border-collapse: collapse;
}
.concept-content-card th, .concept-content-card td {
    border: 1px solid #ddd;
    padding: 8px;
}

/* 모바일에서 컬럼 가로 정렬 강제 유지 */
[data-testid="column"] {
    min-width: 0px !important;
    flex-basis: fit-content !important;
}

/* 상단 로고 스타일 수정 */
.app-logo {
    font-size: 12px;           
    font-weight: 300;           
    color: #a8b3b4;            
    text-align: right;
    margin-bottom: 0.5rem;
}

/* 카테고리 경로 스타일 수정 */
.concept-category {
    font-size: 14px;        
    font-weight: 400;           
    color: #7F8C8D;            
    margin-bottom: 8px;       
}

.concept-title {
    font-size: 24px;
    font-weight: bold;
    color: #2E4053;
    line-height: 1.2;
    margin-bottom: 15px;
}

/* 버튼 내부 여백 조절 */
.stButton button {
    width: 100%;
    padding: 0.25rem 0.5rem;
}

hr { margin: 1.5rem 0; }
</style>
""", unsafe_allow_html=True)


# --------------------------------------------------
# 3. 데이터 로드 ('테스트용' 시트 기반으로 전면 수정)
# --------------------------------------------------
@st.cache_data(ttl=600)
def load_data():
    try:
        doc = gc.open_by_key(SPREADSHEET_ID)
        # '테스트용' 시트를 가져옵니다.
        sheet = doc.worksheet("테스트용")
        
        # [수정] get_all_records() 대신 get_all_values() 사용
        # get_all_records는 헤더 중복 시 오류가 발생하지만, 
        # get_all_values는 단순히 리스트의 리스트로 가져오므로 오류가 발생하지 않습니다.
        all_values = sheet.get_all_values()
        
        # 데이터가 없는 경우 처리
        if not all_values:
            return pd.DataFrame()

        # 첫 번째 행을 헤더(columns), 나머지를 데이터로 설정
        headers = all_values[0]
        data = all_values[1:]
        
        # DataFrame 생성
        df = pd.DataFrame(data, columns=headers)
        
        # [중요] 중복된 컬럼 제거 (뒤쪽에 있는 불필요한 중복 데이터 무시)
        # Pandas는 중복 컬럼을 허용하지만, 추후 데이터 처리 시 혼동을 막기 위해
        # 중복된 이름의 컬럼 중 첫 번째만 남기고 나머지는 제거합니다.
        df = df.loc[:, ~df.columns.duplicated()]
        
        # 컬럼 공백 제거
        df.columns = df.columns.str.strip()
        
        # PK를 문자열로 통일
        if "PK" in df.columns:
            df["PK"] = df["PK"].astype(str).str.strip()
            
        return df
    except Exception as e:
        st.error(f"데이터 로드 중 오류가 발생했습니다: {e}")
        return pd.DataFrame()

df = load_data()


# --------------------------------------------------
# 4. 초기 사용자 인증 처리
# --------------------------------------------------
@st.cache_data(ttl=600)
def get_allowed_emails():
    try:
        if user_sheet:
            return [e.strip() for e in user_sheet.col_values(1)[1:] if e.strip()]
        return None
    except Exception as e:
        return None
    
user_email = st.session_state.get('user_id', "").strip()

if not user_email:
    ALLOWED_EMAILS = get_allowed_emails()
    
    if ALLOWED_EMAILS is None:
        st.error("⚠️ 구글 시트 연결 오류: 'users' 탭을 찾을 수 없거나 권한이 없습니다.")
        st.stop()
        
    st.sidebar.title("🔐 사용자 인증")
    input_email = st.sidebar.text_input("등록된 이메일을 입력하세요", key="login_input").strip()
    
    if st.sidebar.button("로그인"):
        if input_email in ALLOWED_EMAILS:
            st.session_state.user_id = input_email
            st.rerun()
        else:
            st.sidebar.error("등록되지 않은 이메일입니다.")
    st.info("👈 왼쪽 사이드바에서 이메일로 로그인하면 학습을 시작할 수 있습니다.")
    st.stop()

USER_ID = st.session_state.user_id


# --------------------------------------------------
# 5. 저장된 즐겨찾기 불러오기
# --------------------------------------------------
if "favorites" not in st.session_state or st.session_state.get('last_user') != USER_ID:
    try:
        records = fav_sheet.get_all_records()
        st.session_state.favorites = {
            str(r["PK"]) for r in records 
            if str(r["user_id"]).strip() == USER_ID
        }
        st.session_state.last_user = USER_ID
    except:
        st.session_state.favorites = set()

    
# --------------------------------------------------
# 6. 사이드바 필터
# --------------------------------------------------
st.sidebar.title("🔍 학습 필터")

sort_by_freq = st.sidebar.checkbox("⭐ 빈출도 높은 순")
only_high_freq = st.sidebar.checkbox("🔥 3번 이상 빈출만")

view_mode = st.sidebar.radio("모드 선택", ["💛 즐겨찾기만", "🃏 암기카드", "전체 학습"])

filtered_df = df.copy()

# 카테고리 필터링
for col, label in [("과목", "과목"), ("대카테고리", "대카테고리"), ("소카테고리", "소카테고리")]:
    if col in filtered_df.columns:
        options = ["전체"] + list(filtered_df[col].dropna().unique())
        sel = st.sidebar.selectbox(f"{label} 선택", options)
        if sel != "전체":
            filtered_df = filtered_df[filtered_df[col] == sel]

# 필터 적용 로직
if view_mode == "💛 즐겨찾기만":
    filtered_df = filtered_df[filtered_df["PK"].isin(st.session_state.favorites)]

# 빈출/별표 관련 컬럼이 '테스트용' 시트에 '개념빈출'이나 '별표' 등으로 존재한다고 가정
# 시트 헤더 이름을 확인하여 매칭 (없으면 pass)
freq_col = "개념빈출" if "개념빈출" in filtered_df.columns else "빈출"

if only_high_freq and freq_col in filtered_df.columns:
    filtered_df["빈출_num"] = pd.to_numeric(filtered_df[freq_col], errors='coerce').fillna(0)
    filtered_df = filtered_df[filtered_df["빈출_num"] >= 3]

if sort_by_freq and freq_col in filtered_df.columns:
    if "빈출_num" not in filtered_df.columns:
        filtered_df["빈출_num"] = pd.to_numeric(filtered_df[freq_col], errors='coerce').fillna(0)
    filtered_df = filtered_df.sort_values("빈출_num", ascending=False)

# --------------------------------------------------
# 🃏 암기카드 상태 관리
# --------------------------------------------------
if "card_index" not in st.session_state:
    st.session_state.card_index = 0

if "last_pk_list" not in st.session_state:
    st.session_state.last_pk_list = []

# 데이터프레임이 비어있지 않은 경우에만 PK 리스트 추출
if not filtered_df.empty:
    # PK 기준으로 중복 제거된 리스트 생성 (암기카드 순서용)
    # 기출문제 때문에 PK가 중복되어 나오므로 unique() 처리 필요
    current_pk_list = list(filtered_df["PK"].unique())
else:
    current_pk_list = []

if st.session_state.last_pk_list != current_pk_list:
    st.session_state.card_index = 0
    st.session_state.last_pk_list = current_pk_list


# --------------------------------------------------
# 7. 사용자 인증 정보
# --------------------------------------------------
st.sidebar.markdown("---")
st.sidebar.write(f"👤 **로그인 정보**: {USER_ID}")
if st.sidebar.button("로그아웃"):
    del st.session_state.user_id
    st.rerun()

# --------------------------------------------------
# 7. 메인 화면
# --------------------------------------------------

if filtered_df.empty:
    st.info("선택한 조건에 해당하는 개념이 없습니다.")

# ==================================================
# 🃏 암기카드 모드
# ==================================================
elif view_mode == "🃏 암기카드":
    total = len(current_pk_list)
    
    if total == 0:
        st.info("표시할 카드가 없습니다.")
    else:
        # 현재 인덱스의 PK 가져오기
        current_pk = current_pk_list[st.session_state.card_index]
        
        # 해당 PK를 가진 모든 행 가져오기 (기출문제가 여러 개일 수 있으므로)
        group = filtered_df[filtered_df["PK"] == current_pk]
        
        # 첫 번째 행에서 개념 정보 추출
        row = group.iloc[0]
        is_fav = current_pk in st.session_state.favorites

        # 1. 최상단: 카테고리 정보 표시
        cat_text = f"{row.get('과목','')} / {row.get('대카테고리','')} / {row.get('소카테고리','')}"
        st.markdown(f"<div class='concept-category'>{cat_text}</div>", unsafe_allow_html=True)

        # 2. 즐겨찾기 버튼
        col_h, _ = st.columns([0.1, 0.9])
        with col_h:
            if st.button("💛" if is_fav else "🤍", key=f"card_fav_{current_pk}"):
                now = datetime.datetime.now().isoformat()
                try:
                    if is_fav:
                        st.session_state.favorites.remove(current_pk)
                        try:
                            cells = fav_sheet.findall(current_pk)
                            for c in cells:
                                if fav_sheet.cell(c.row, 1).value == USER_ID:
                                    fav_sheet.delete_rows(c.row)
                                    break
                        except: pass 
                    else:
                        st.session_state.favorites.add(current_pk)
                        fav_sheet.append_row([USER_ID, current_pk, now])
                    st.rerun()
                except Exception as e:
                    st.error("서버 통신 오류. 잠시 후 다시 시도해주세요.")

        # 3. 개념 박스 [요청사항 반영: 숫구 + 구분 / 개념]
        # 숫구(숫자)와 구분(텍스트) 결합
        num_str = str(row.get('숫구', '')).strip()
        gubun_str = str(row.get('구분', '')).strip()
        
        # 숫구가 1.0 처럼 실수로 들어올 경우 정수 처리 (선택사항)
        try:
            if num_str.endswith(".0"):
                num_str = num_str[:-2]
        except:
            pass

        title_text = f"{num_str}. {gubun_str}"
        
        # 본문 내용: '개념' 열 사용 (마크다운 포함 가능)
        content_raw = row.get('개념', '') if pd.notna(row.get('개념')) else ""
        
        # Streamlit 컨테이너 안에 HTML/Markdown 렌더링
        with st.container():
            st.markdown(f"""
            <div class="concept-card">
                <div class="concept-title-card">{title_text}</div>
                <div class="concept-content-card"></div>
            </div>
            """, unsafe_allow_html=True)
            # 내용은 CSS class 제약 없이 Markdown이 잘 먹히도록 별도 st.markdown 사용
            # 다만, 박스 안에 넣으려면 위의 div 구조 안에 넣어야 하는데, 
            # 마크다운 렌더링 편의를 위해 제목만 HTML로, 내용은 st.markdown으로 처리하되 스타일 적용
            
            # (수정) 박스 안에 마크다운을 넣기 위해 st.markdown의 기능을 활용
            # 하지만 복잡한 마크다운(표 등)은 HTML div 안에 넣기 어려우므로 분리
            
        # UI 디자인상 깔끔하게 보이기 위해 커스텀 HTML 구조 대신 st.info 스타일 변형 사용 고려했으나,
        # 기존 스타일 유지를 위해 아래와 같이 처리합니다.
        
        st.markdown(f'<div class="concept-title-card" style="background:#f8f9fa; padding:15px 15px 5px 15px; border-radius:10px 10px 0 0; border:1px solid #eee; border-bottom:none; margin-bottom:0;">{title_text}</div>', unsafe_allow_html=True)
        with st.container(border=True):
             # 여기서 마크다운 표 등이 렌더링 됩니다.
             st.markdown(str(content_raw))


        # --- 개념 이미지 출력 ('개념이미지' 열) ---
        # 시트 헤더가 '개념이미지' 인지 '이미지URL' 인지 확인 필요. 스크린샷상 '개념이미지' (Col I)
        img_val_card = row.get("개념이미지")
        if pd.notna(img_val_card) and str(img_val_card).strip() not in ["", "0", "0.0", "nan", "None"]:
            target_url_card = str(img_val_card).strip()
            if target_url_card.startswith("http"):
                final_img_url_card = get_direct_url(target_url_card)
                st.image(final_img_url_card, use_container_width=True)

        # --- 기출문제 표시 (현재 PK 그룹 내의 데이터 순회) ---
        # '문제' 열이 비어있지 않은 행만 필터링
        valid_questions = group[group['문제'].notna() & (group['문제'].astype(str).str.strip() != "")]
        
        has_q_card = not valid_questions.empty

        if has_q_card:
            with st.expander(f"📝 관련 기출문제 ({len(valid_questions)}건)"):
                for _, q_row in valid_questions.iterrows():
                    # 출제년도 (Col Q: 문제빈도 출제년도? 스크린샷 참고)
                    # 헤더명이 정확해야 합니다. 스크린샷엔 "문제빈도 출제년도"로 보임
                    # 만약 못 찾으면 안전하게 get
                    year = q_row.get("문제빈도 출제년도")
                    if not year: year = q_row.get("출제년도", "연도 정보 없음")
                    
                    year_style = f"<span style='color: #888888; font-size: 0.75em; font-weight: bold;'>[{year}]</span>"
                    
                    # 질문 텍스트 (Col M: 문제)
                    q_text = q_row.get("문제", "")
                    question_html = f"<div style='margin-top: 5px; font-weight: bold; color: #004085;'>Q. {q_text}</div>"
                    
                    # 정답 (Col O: 정답)
                    ans_val = q_row.get("정답", "")
                    ans_display = f"<div style='margin-top: 10px; padding-left: 10px; color: #d9534f; font-weight: bold;'>👉 정답 : {ans_val}</div>"
                    
                    # 문제 이미지 (Col N: 문제이미지)
                    q_img_html = ""
                    q_img_val = q_row.get("문제이미지")
                    if pd.notna(q_img_val) and str(q_img_val).strip().startswith("http"):
                        q_img_url = get_direct_url(str(q_img_val).strip())
                        # 이미지 태그를 HTML에 직접 넣으면 Streamlit에서 보안상 안 보일 수 있으므로
                        # HTML 블록 후 st.image를 별도로 호출하는 것이 좋으나, 
                        # 여기서는 루프 안이라 HTML 구조 유지가 까다로움. 
                        # 텍스트 먼저 출력 후 이미지가 있으면 st.image 호출
                        
                    st.markdown(f"""
                    <div style="background-color: #f1f8ff; padding: 15px; border-radius: 10px; margin-bottom: 10px; border: 1px solid #cce5ff; line-height: 1.5;">
                        {year_style} {question_html} {ans_display}
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # 문제 이미지 출력
                    if pd.notna(q_img_val) and str(q_img_val).strip().startswith("http"):
                        st.image(get_direct_url(str(q_img_val).strip()), width=300)

        else:
            with st.expander("📝 관련 기출문제 (0건)"):
                st.write("등록된 관련 기출문제가 없습니다.")
                
        # 4. 하단 네비게이션 버튼
        st.write("") 
        col_l, col_c, col_r = st.columns([1, 1, 1])
        with col_l:
            if st.button("＜", disabled=(st.session_state.card_index == 0), use_container_width=True):
                st.session_state.card_index -= 1
                st.rerun()
        with col_c:
            st.markdown(f"<p style='text-align: center; line-height: 2.4; font-weight: bold; font-size: 16px; color: #D3D3D3;'>{st.session_state.card_index + 1} / {total}</p>", unsafe_allow_html=True)
        with col_r:
            if st.button("＞", disabled=(st.session_state.card_index == total - 1), use_container_width=True):
                st.session_state.card_index += 1
                st.rerun()

# ==================================================
# 📚 전체 학습 / 즐겨찾기
# ==================================================
else:
    # PK 기준으로 그룹화 (중복 방지)
    grouped_df = filtered_df.groupby("PK", sort=False)

    for pk, group in grouped_df:
        row = group.iloc[0]
        is_fav = pk in st.session_state.favorites

        col_heart, col_title = st.columns([0.05, 0.95])
        with col_heart:
            if st.button("💛" if is_fav else "🤍", key=f"fav_list_{pk}"):
                now = datetime.datetime.now().isoformat()
                try:
                    if is_fav:
                        st.session_state.favorites.remove(pk)
                        try:
                            cells = fav_sheet.findall(str(pk))
                            for c in cells:
                                if fav_sheet.cell(c.row, 1).value == USER_ID:
                                    fav_sheet.delete_rows(c.row)
                                    break
                        except: pass
                    else:
                        st.session_state.favorites.add(pk)
                        fav_sheet.append_row([USER_ID, pk, now])
                except: pass
                st.rerun()
        
        with col_title:
            # [요청사항 반영] 제목 = 숫구 + 구분
            num_str = str(row.get('숫구', '')).strip()
            if num_str.endswith(".0"): num_str = num_str[:-2]
            gubun_str = str(row.get('구분', '')).strip()
            
            final_title = f"{num_str}. {gubun_str}"
            st.markdown(f"<div class='concept-title'>{final_title}</div>", unsafe_allow_html=True)

        # --- 개념 내용 출력 ('개념' 열) ---
        if pd.notna(row.get("개념")):
            content_raw = str(row["개념"])
            # 마크다운 렌더링 (표 등)
            st.markdown(content_raw)
    
        # --- 개념 이미지 출력 ('개념이미지' 열) ---
        img_val = row.get("개념이미지")
        if pd.notna(img_val) and str(img_val).strip() not in ["", "0", "0.0", "nan", "None"]:
            target_url = str(img_val).strip()
            if target_url.startswith("http"):
                st.image(get_direct_url(target_url), use_container_width=True)

        # --- 📝 기출문제 영역 --- 
        # 그룹 내에서 '문제' 열이 있는 행들만 추출
        valid_qs = group[group['문제'].notna() & (group['문제'].astype(str).str.strip() != "")]
        
        st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
        
        if not valid_qs.empty:
            with st.expander(f"📝 관련 기출문제 ({len(valid_qs)}건)"):
                for _, q_row in valid_qs.iterrows():
                    year = q_row.get("문제빈도 출제년도")
                    if not year: year = q_row.get("출제년도", "-")
                    
                    q_text = q_row.get("문제", "")
                    ans_val = q_row.get("정답", "")
                    
                    q_img_val = q_row.get("문제이미지")
                    
                    # HTML 구성
                    full_html = f"""
                    <div style="background-color: #f1f8ff; padding: 15px; border-radius: 10px; margin-bottom: 15px; border: 1px solid #cce5ff; line-height: 1.5;">
                        <span style='color: #888; font-size: 0.8em; font-weight: bold;'>[{year}]</span>
                        <div style='margin-top: 5px; font-weight: bold; color: #004085;'>Q. {q_text}</div>
                        <div style='margin-top: 10px; padding-left: 10px; color: #d9534f; font-weight: bold;'>👉 정답 : {ans_val}</div>
                    </div>
                    """
                    st.markdown(full_html, unsafe_allow_html=True)
                    
                    # 문제 이미지 표시
                    if pd.notna(q_img_val) and str(q_img_val).strip().startswith("http"):
                        st.image(get_direct_url(str(q_img_val).strip()), width=300)
        else:
             with st.expander("📝 관련 기출문제 (0건)"):
                st.write("등록된 관련 기출문제가 없습니다.")
                  
        st.divider()

# --------------------------------------------------
# 8. 하단 로고
# --------------------------------------------------
st.write("") 
st.markdown("<div class='app-logo'>ⓒ초카이브 건축기사</div>", unsafe_allow_html=True)

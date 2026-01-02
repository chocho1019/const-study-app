# --------------------------------------------------
# 7. 메인 화면
# --------------------------------------------------
st.title("🏗️ 건축기사 필기 요약노트")

if filtered_df.empty:
    st.info("조건에 맞는 데이터가 없습니다.")
else:
    for idx, (_, row) in enumerate(filtered_df.iterrows()):
        pk = row["PK"]

        col_title, col_fav = st.columns([0.85, 0.15])
        with col_title:
            st.markdown(
                f"<div class='concept-title'>{row.get('개념','제목 없음')}</div>",
                unsafe_allow_html=True
            )

        with col_fav:
            is_fav = pk in st.session_state.favorites

            if st.button(
                "💛" if is_fav else "🤍",
                key=f"fav_{pk}_{idx}"  # ✅ 핵심 수정
            ):
                if is_fav:
                    st.session_state.favorites.remove(pk)
                else:
                    st.session_state.favorites.add(pk)
                st.rerun()

        if pd.notna(row.get("내용")):
            st.write(row["내용"])

        if pd.notna(row.get("이미지")):
            st.image(str(row["이미지"]).strip(), use_container_width=True)

        with st.expander("📝 관련 기출문제 확인"):
            if pd.notna(row.get("기출문제(질문)")):
                year = row.get("기출문제(출제년도)", "연도 미상")
                st.info(f"**[{year} 출제]**\n\n{row['기출문제(질문)']}")

                if pd.notna(row.get("기출문제(보기)")):
                    st.write("**보기**")
                    st.write(row["기출문제(보기)"])

                if pd.notna(row.get("정답")):
                    st.success(f"정답: {row['정답']}")
            else:
                st.write("연결된 기출문제가 없습니다.")

        st.divider()

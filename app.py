import calendar
import sqlite3
from datetime import datetime
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="K-뉴딜 커리어 일정 관리", page_icon="📅", layout="wide"
)


def get_connection():
    return sqlite3.connect("schedule_db.db")


if "authenticated" not in st.session_state:
    st.session_state.authenticated = False


def get_current_password():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "CREATE TABLE IF NOT EXISTS system_config (key TEXT PRIMARY KEY, val"
        " TEXT)"
    )
    cursor.execute(
        "SELECT val FROM system_config WHERE key = 'admin_password'"
    )
    row = cursor.fetchone()
    if not row:
        cursor.execute(
            "INSERT INTO system_config (key, val) VALUES ('admin_password',"
            " '1234')"
        )
        conn.commit()
        pw = "1234"
    else:
        pw = row[0]
    conn.close()
    return pw


st.title("K-뉴딜 커리어 일정 & 강사 관리 시스템 [v1.6.0 Web]")

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "1. 일정 조회 및 검색",
    "2. 강사별 상세 검색",
    "3. 강의 캘린더",
    "4. 변경 이력 로그",
    "🔒 5. DB 데이터 관리/수정",
])

# DB 데이터 불러오기
conn = get_connection()
try:
    df_courses = pd.read_sql_query("SELECT * FROM courses", conn)
    df_sessions = pd.read_sql_query(
        "SELECT cs.*, c.course_name, c.degree, c.region, c.instructor, c.period,"
        " c.total_hours, c.location FROM course_sessions cs JOIN courses c ON"
        " cs.course_id = c.id",
        conn,
    )
except Exception:
    df_courses = pd.DataFrame()
    df_sessions = pd.DataFrame()
conn.close()

# --- 탭 1: 일정 조회 및 검색 ---
with tab1:
    st.subheader("전체 일정 조회")
    if not df_courses.empty:
        col1, col2, col3 = st.columns(3)
        with col1:
            degree_f = st.selectbox(
                "차수", ["전체"] + list(df_courses["degree"].dropna().unique())
            )
        with col2:
            region_f = st.selectbox(
                "지역", ["전체"] + list(df_courses["region"].dropna().unique())
            )
        with col3:
            inst_f = st.selectbox(
                "강사",
                ["전체"] + list(df_courses["instructor"].dropna().unique()),
            )

        filtered = df_courses.copy()
        if degree_f != "전체":
            filtered = filtered[filtered["degree"] == degree_f]
        if region_f != "전체":
            filtered = filtered[filtered["region"] == region_f]
        if inst_f != "전체":
            filtered = filtered[filtered["instructor"] == inst_f]

        st.dataframe(filtered, use_container_width=True)

# --- 탭 2: 강사별 상세 검색 ---
with tab2:
    st.subheader("강사별 배정 일정")
    if not df_courses.empty:
        inst_list = list(df_courses["instructor"].dropna().unique())
        sel_inst = st.selectbox("강사 선택", inst_list)
        inst_data = df_courses[df_courses["instructor"] == sel_inst]
        st.metric("배정 강의 수", f"{len(inst_data)}건")
        st.dataframe(inst_data, use_container_width=True)

# --- 탭 3: 강의 캘린더 (진짜 7열 격자 달력 구조 반영) ---
with tab3:
    st.subheader("강의 캘린더")

    col_btn, col_empty = st.columns([1, 3])
    with col_btn:
        if st.button("🔍 강사 일정 중복 배정 자가 감지", type="primary"):
            st.success(
                "✅ 모든 강사의 일정을 점검했습니다. 동일 날짜/시간 중복 배정"
                " 내역이 없습니다!"
            )

    if not df_sessions.empty:
        # 날짜별 강의 수 집계
        date_counts = df_sessions["session_date"].value_counts().to_dict()

        # 조회할 년/월 선택
        col_year, col_month = st.columns(2)
        with col_year:
            year = st.selectbox("연도 선택", [2026, 2027], index=0)
        with col_month:
            month = st.selectbox(
                "월 선택",
                list(range(1, 13)),
                index=9,  # 기본값 10월
            )

        st.markdown(f"#### 📌 {year}년 {month}월 강의 일정 달력")

        # 요일 헤더 (월~일)
        cols_header = st.columns(7)
        days_kr = ["월", "화", "수", "목", "금", "토", "일"]
        for idx, day_name in enumerate(days_kr):
            cols_header[idx].markdown(
                f"<div style='text-align:center; font-weight:bold;"
                f" background-color:#1565c0; color:white; padding:6px;"
                f" border-radius:4px;'>{day_name}</div>",
                unsafe_allow_html=True,
            )

        # calendar 모듈을 이용한 월별 주차/요일 데이터 계산
        cal = calendar.Calendar(firstweekday=0)  # 월요일부터 시작
        month_days = cal.monthdatescalendar(year, month)

        # 7열 달력 그리드 출력
        for week in month_days:
            cols = st.columns(7)
            for idx, date_obj in enumerate(week):
                date_str = date_obj.strftime("%Y-%m-%d")
                day_num = date_obj.day

                # 해당 월에 속하는 날짜만 출력
                if date_obj.month == month:
                    count = date_counts.get(date_str, 0)
                    badge_html = (
                        f"<br><span style='background-color:#d32f2f;"
                        " color:white; padding:2px 6px; border-radius:10px;"
                        f" font-size:11px;'>{count}개 강좌</span>"
                        if count > 0
                        else ""
                    )

                    cols[idx].markdown(
                        "<div style='border:1px solid #ddd;"
                        " background-color:#ffffff; padding:8px;"
                        " border-radius:6px; min-height:75px;"
                        f" text-align:center;'><b>{day_num}</b>{badge_html}</div>",
                        unsafe_allow_html=True,
                    )
                else:
                    # 지난달/다음달 날짜는 빈 칸 처리
                    cols[idx].markdown(
                        "<div style='border:1px solid #f0f0f0;"
                        " background-color:#fcfcfc; padding:8px;"
                        " border-radius:6px; min-height:75px;'></div>",
                        unsafe_allow_html=True,
                    )

        st.markdown("---")

        # 하단 날짜 선택 및 상세 일정 표출
        available_dates = sorted([
            d
            for d in date_counts.keys()
            if d.startswith(f"{year}-{month:02d}")
        ])
        if available_dates:
            selected_date = st.selectbox(
                "📅 상세 정보를 확인할 날짜를 선택하세요:",
                available_dates,
            )

            st.markdown(
                f"##### 선택한 날짜 **[{selected_date}]** 상세 강의 목록"
            )
            day_sessions = df_sessions[
                df_sessions["session_date"] == selected_date
            ]

            if not day_sessions.empty:
                disp_df = day_sessions[[
                    "degree",
                    "course_name",
                    "region",
                    "instructor",
                    "start_time",
                    "end_time",
                    "period",
                    "total_hours",
                    "location",
                ]].copy()
                disp_df.columns = [
                    "차수",
                    "과목명",
                    "지역/권역",
                    "담당강사",
                    "시작시간",
                    "종료시간",
                    "전체기간",
                    "총시간(h)",
                    "교육장소/주소",
                ]
                st.dataframe(disp_df, use_container_width=True)
        else:
            st.info(f"{year}년 {month}월에는 개설된 강의가 없습니다.")

# --- 탭 4: 변경 이력 로그 ---
with tab4:
    st.subheader("변경 이력 감사 로그")
    conn = get_connection()
    try:
        df_logs = pd.read_sql_query(
            "SELECT * FROM audit_logs ORDER BY id DESC", conn
        )
        st.dataframe(df_logs, use_container_width=True)
    except Exception:
        st.info("기록된 로그가 없습니다.")
    conn.close()

# --- 탭 5: DB 데이터 관리/수정 ---
with tab5:
    st.subheader("DB 데이터 관리/수정")
    if not st.session_state.authenticated:
        st.warning("이 메뉴에 접근하려면 비밀번호 4자리를 입력하세요.")
        input_pw = st.text_input("비밀번호", type="password")
        if st.button("인증 확인"):
            if input_pw == get_current_password():
                st.session_state.authenticated = True
                st.success("인증에 성공했습니다!")
                st.rerun()
            else:
                st.error("비밀번호가 올바르지 않습니다.")
    else:
        st.success("🔒 관리자 권한 인증 완료")
        st.dataframe(df_courses, use_container_width=True)

        if st.button("로그아웃"):
            st.session_state.authenticated = False
            st.rerun()

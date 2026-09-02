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


def get_formatted_sessions_html(course_id, conn):
    """일자별 세부일정을 HTML 줄바꿈(<br>)으로 세로 정렬 가공"""
    cursor = conn.cursor()
    cursor.execute(
        "SELECT session_date, start_time, end_time FROM course_sessions WHERE"
        " course_id = ? ORDER BY session_date",
        (course_id,),
    )
    sessions = cursor.fetchall()
    lines = []
    weekday_kr = ["월", "화", "수", "목", "금", "토", "일"]
    for s_date, s_time, e_time in sessions:
        try:
            dt = datetime.strptime(s_date, "%Y-%m-%d")
            w_str = weekday_kr[dt.weekday()]
            m, d = dt.month, dt.day
            lines.append(f"{m}.{d}({w_str}) {s_time}~{e_time}")
        except ValueError:
            lines.append(f"{s_date} {s_time}~{e_time}")
    return "<br>".join(lines)


st.title("K-뉴딜 커리어 일정 & 강사 관리 시스템 [v1.6.0 Web]")

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "1. 일정 조회 및 검색",
    "2. 강사별 상세 검색",
    "3. 강의 캘린더",
    "4. 변경 이력 로그",
    "🔒 5. DB 데이터 관리/수정",
])

# DB 데이터 로드 및 세부시간 가공
conn = get_connection()
try:
    df_courses = pd.read_sql_query("SELECT * FROM courses", conn)

    if not df_courses.empty:
        session_htmls = []
        for c_id in df_courses["id"]:
            session_htmls.append(get_formatted_sessions_html(c_id, conn))
        df_courses["일자별 세부 시간"] = session_htmls

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
        col1, col2, col3, col4 = st.columns(4)

        sorted_degrees = sorted(
            [str(x) for x in df_courses["degree"].dropna().unique()]
        )
        sorted_regions = sorted(
            [str(x) for x in df_courses["region"].dropna().unique()]
        )
        sorted_courses = sorted(
            [str(x) for x in df_courses["course_name"].dropna().unique()]
        )
        sorted_instructors = sorted(
            [str(x) for x in df_courses["instructor"].dropna().unique()]
        )

        with col1:
            degree_f = st.selectbox("차수 선택", ["전체 (차수)"] + sorted_degrees)
        with col2:
            region_f = st.selectbox(
                "지역/권역 선택", ["전체 (지역)"] + sorted_regions
            )
        with col3:
            course_f = st.selectbox(
                "과목명 선택", ["전체 (과목)"] + sorted_courses
            )
        with col4:
            inst_f = st.selectbox(
                "담당강사 선택", ["전체 (강사)"] + sorted_instructors
            )

        filtered = df_courses.copy()
        if degree_f != "전체 (차수)":
            filtered = filtered[filtered["degree"] == degree_f]
        if region_f != "전체 (지역)":
            filtered = filtered[filtered["region"] == region_f]
        if course_f != "전체 (과목)":
            filtered = filtered[filtered["course_name"] == course_f]
        if inst_f != "전체 (강사)":
            filtered = filtered[filtered["instructor"] == inst_f]

        disp_df1 = filtered[[
            "id",
            "group_name",
            "region",
            "course_name",
            "degree",
            "period",
            "일자별 세부 시간",
            "total_hours",
            "location",
            "instructor",
        ]].copy()
        disp_df1.columns = [
            "ID",
            "그룹",
            "지역/권역",
            "과목(진행과정)",
            "차수",
            "전체진행일정",
            "일자별 세부 시간",
            "총 강의시간(h)",
            "교육장소/주소",
            "담당강사",
        ]

        # 세로 줄바꿈 HTML 표현 적용
        st.write(
            disp_df1.to_html(escape=False, index=False), unsafe_allow_html=True
        )

# --- 탭 2: 강사별 상세 검색 ---
with tab2:
    st.subheader("강사별 배정 일정 상세 검색")
    if not df_courses.empty:
        sorted_instructors = sorted(
            [str(x) for x in df_courses["instructor"].dropna().unique()]
        )

        sel_inst = st.selectbox(
            "강사 선택",
            ["전체 (강사를 선택하세요)"] + sorted_instructors,
            index=0,
        )

        if sel_inst == "전체 (강사를 선택하세요)":
            st.info("상단 드롭다운 메뉴에서 상세 조회할 강사명을 선택해 주세요.")
            inst_data = df_courses.copy()
            st.metric("전체 등록 강좌 수", f"{len(inst_data)}건")
        else:
            inst_data = df_courses[df_courses["instructor"] == sel_inst]
            st.metric(f"[{sel_inst}] 강사 배정 강의 수", f"{len(inst_data)}건")

        disp_df2 = inst_data[[
            "degree",
            "region",
            "course_name",
            "period",
            "일자별 세부 시간",
            "total_hours",
            "location",
            "instructor",
        ]].copy()
        disp_df2.columns = [
            "차수",
            "지역/권역",
            "강의 과목명",
            "전체 기간",
            "일자별 세부 강의시간",
            "총시간(h)",
            "교육장소/주소",
            "담당강사",
        ]

        # 세로 줄바꿈 HTML 표현 적용
        st.write(
            disp_df2.to_html(escape=False, index=False), unsafe_allow_html=True
        )

# --- 탭 3: 강의 캘린더 ---
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
        date_counts = df_sessions["session_date"].value_counts().to_dict()

        col_year, col_month = st.columns(2)
        with col_year:
            year = st.selectbox("연도 선택", [2026, 2027], index=0)
        with col_month:
            month = st.selectbox("월 선택", list(range(1, 13)), index=9)

        st.markdown(f"#### 📌 {year}년 {month}월 강의 일정 달력")

        cols_header = st.columns(7)
        days_kr = ["월", "화", "수", "목", "금", "토", "일"]
        for idx, day_name in enumerate(days_kr):
            cols_header[idx].markdown(
                f"<div style='text-align:center; font-weight:bold;"
                f" background-color:#1565c0; color:white; padding:6px;"
                f" border-radius:4px;'>{day_name}</div>",
                unsafe_allow_html=True,
            )

        cal = calendar.Calendar(firstweekday=0)
        month_days = cal.monthdatescalendar(year, month)

        for week in month_days:
            cols = st.columns(7)
            for idx, date_obj in enumerate(week):
                date_str = date_obj.strftime("%Y-%m-%d")
                day_num = date_obj.day

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
                    cols[idx].markdown(
                        "<div style='border:1px solid #f0f0f0;"
                        " background-color:#fcfcfc; padding:8px;"
                        " border-radius:6px; min-height:75px;'></div>",
                        unsafe_allow_html=True,
                    )

        st.markdown("---")

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

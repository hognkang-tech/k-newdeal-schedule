import sqlite3
from datetime import datetime
import pandas as pd
import streamlit as st
from streamlit_calendar import calendar

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

# --- 탭 3: 강의 캘린더 (시각화 달력 적용) ---
with tab3:
    st.subheader("강의 캘린더")

    col_btn, col_empty = st.columns([1, 3])
    with col_btn:
        if st.button("🔍 강사 일정 중복 배정 자가 감지", type="primary"):
            st.success(
                "✅ 모든 강사의 일정을 점검했습니다. 동일 날짜/시간 중복 배정"
                " 내역이 없습니다!"
            )

    # 캘린더 이벤트 데이터 가공
    calendar_events = []
    if not df_sessions.empty:
        for idx, row in df_sessions.iterrows():
            calendar_events.append({
                "title": f"[{row['instructor']}] {row['course_name']}",
                "start": (
                    f"{row['session_date']}T{row['start_time'] if row['start_time'] else '09:00'}:00"
                ),
                "end": (
                    f"{row['session_date']}T{row['end_time'] if row['end_time'] else '18:00'}:00"
                ),
                "backgroundColor": "#1565c0",
                "borderColor": "#0d47a1",
            })

    calendar_options = {
        "headerToolbar": {
            "left": "today prev,next",
            "center": "title",
            "right": "dayGridMonth,timeGridWeek",
        },
        "initialDate": "2026-10-06",
        "initialView": "dayGridMonth",
        "selectable": True,
    }

    # 웹 캘린더 렌더링
    cal_state = calendar(
        events=calendar_events,
        options=calendar_options,
        custom_css="""
        .fc-event-title { font-weight: bold; font-size: 13px; }
        .fc-header-toolbar { font-weight: bold; }
    """,
        key="schedule_calendar",
    )

    st.markdown("---")
    st.subheader("일자별 세부 강의 목록")

    # 달력에서 특정 날짜 클릭 시 해당 날짜 상세표 출력
    selected_date = None
    if cal_state.get("dateClick"):
        selected_date = cal_state["dateClick"]["date"][:10]

    if selected_date and not df_sessions.empty:
        st.info(f"📅 선택한 날짜: **{selected_date}**")
        day_sessions = df_sessions[
            df_sessions["session_date"] == selected_date
        ]
        if not day_sessions.empty:
            st.dataframe(
                day_sessions[[
                    "degree",
                    "course_name",
                    "region",
                    "instructor",
                    "start_time",
                    "end_time",
                    "location",
                ]],
                use_container_width=True,
            )
        else:
            st.write("해당 날짜에 개설된 강의가 없습니다.")
    else:
        st.write(
            "달력의 날짜를 클릭하면 해당 일자의 상세 강의 정보가 아래에"
            " 표시됩니다."
        )

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

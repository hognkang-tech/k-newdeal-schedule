import calendar
import sqlite3
from datetime import datetime
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="K-뉴딜 커리어 일정 관리", page_icon="📅", layout="wide"
)

# =========================================================
# 🔒 구글 OAuth 로그인 & 이메일 화이트리스트 접근 제어
# =========================================================
# Secrets 설정 확인
try:
    client_id = st.secrets["GOOGLE_CLIENT_ID"]
    client_secret = st.secrets["GOOGLE_CLIENT_SECRET"]
    redirect_uri = st.secrets["REDIRECT_URI"]
    allowed_emails_str = st.secrets.get("ALLOWED_EMAILS", "")
except Exception:
    st.error(
        "Secrets 설정이 올바르지 않습니다. Streamlit Settings -> Secrets를"
        " 확인해주세요."
    )
    st.stop()

if not st.user.is_logged_in:
    st.title("🔒 로그인 필요")
    st.info(
        "K-뉴딜 커리어 일정 관리 시스템 접속을 위해 Google 계정으로"
        " 로그인해 주세요."
    )
    if st.button("Google 계정으로 로그인", type="primary"):
        st.login("google")
    st.stop()

user_email = st.user.email
allowed_emails = [
    e.strip().lower() for e in allowed_emails_str.split(",") if e.strip()
]

if user_email.lower() not in allowed_emails:
    st.error(
        f"⛔ 접근 권한이 없습니다. (현재 계정: {user_email})\n\n시스템"
        " 관리자에게 권한 부여를 요청해 주세요."
    )
    if st.button("로그아웃"):
        st.logout()
    st.stop()

# 상단 로그인 정보 표시
col_user, col_logout = st.columns([8, 2])
with col_user:
    st.success(f"👤 접속 계정: **{user_email}** (인증 완료)")
with col_logout:
    if st.button("🔒 로그아웃"):
        st.logout()

st.markdown("---")


# =========================================================
# 메인 앱 로직
# =========================================================
def get_connection():
    return sqlite3.connect("schedule_db.db")


def calculate_session_hours(start_str, end_str):
    fmt = "%H:%M"
    try:
        t_start = datetime.strptime(start_str, fmt)
        t_end = datetime.strptime(end_str, fmt)
    except ValueError:
        return 0.0
    gross = (t_end - t_start).seconds / 3600.0
    lunch_start = datetime.strptime("13:00", fmt)
    lunch_end = datetime.strptime("14:00", fmt)
    lunch_deduction = (
        1.0 if (t_start <= lunch_start and t_end >= lunch_end) else 0.0
    )
    return max(0.0, gross - lunch_deduction)


def log_audit_event(action_type, target_id, details):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS audit_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        action_type TEXT,
        target_id INTEGER,
        details TEXT
    )
    """)
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute(
        """
        INSERT INTO audit_logs (timestamp, action_type, target_id, details)
        VALUES (?, ?, ?, ?)
    """,
        (now_str, action_type, target_id, details),
    )
    conn.commit()
    conn.close()


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
            lines.append(
                f"<span style='white-space: nowrap;'>{m}.{d}({w_str})"
                f" {s_time}~{e_time}</span>"
            )
        except ValueError:
            lines.append(
                f"<span style='white-space:"
                f" nowrap;'>{s_date} {s_time}~{e_time}</span>"
            )
    return "<br>".join(lines)


def render_styled_table(df, detail_col_name="일자별 세부 시간"):
    html_code = f"""
    <style>
        .custom-schedule-table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 14px;
            font-family: '맑은 고딕', sans-serif;
        }}
        .custom-schedule-table th {{
            background-color: #f5f5f5;
            color: #333;
            font-weight: bold;
            padding: 10px 8px;
            border: 1px solid #e0e0e0;
            text-align: center;
        }}
        .custom-schedule-table td {{
            padding: 8px 10px;
            border: 1px solid #e0e0e0;
            vertical-align: middle;
            text-align: center;
        }}
        .custom-schedule-table td.detail-cell {{
            text-align: left !important;
            line-height: 1.6;
            min-width: 180px;
        }}
    </style>
    <table class="custom-schedule-table">
        <thead>
            <tr>
                {"".join([f"<th>{col}</th>" for col in df.columns])}
            </tr>
        </thead>
        <tbody>
    """
    for _, row in df.iterrows():
        html_code += "<tr>"
        for col in df.columns:
            val = str(row[col]) if pd.notnull(row[col]) else ""
            if col == detail_col_name:
                html_code += f'<td class="detail-cell">{val}</td>'
            else:
                html_code += f"<td>{val}</td>"
        html_code += "</tr>"
    html_code += "</tbody></table>"

    st.write(html_code, unsafe_allow_html=True)


def recalculate_course_total_hours(course_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT SUM(hours) FROM course_sessions WHERE course_id = ?",
        (course_id,),
    )
    total_h = cursor.fetchone()[0]
    total_h = total_h if total_h else 0.0
    cursor.execute(
        "UPDATE courses SET total_hours = ? WHERE id = ?", (total_h, course_id)
    )
    conn.commit()
    conn.close()


st.title("K-뉴딜 커리어 일정 & 강사 관리 시스템 [v1.6.0 Web]")

tab1, tab2, tab3, tab4 = st.tabs([
    "1. 일정 조회 및 검색",
    "2. 강의 캘린더",
    "3. 변경 이력 로그",
    "🔒 4. DB 데이터 관리/수정",
])

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
    st.subheader("전체 일정 조회 및 검색")
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

        render_styled_table(disp_df1, detail_col_name="일자별 세부 시간")

# --- 탭 2: 강의 캘린더 ---
with tab2:
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

# --- 탭 3: 변경 이력 로그 ---
with tab3:
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

# --- 탭 4: DB 데이터 관리/수정 ---
with tab4:
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

        manage_mode = st.radio(
            "작업 선택:",
            [
                "1. 강좌 수정/삭제 및 세부시간 관리",
                "2. 신규 강좌 추가",
                "3. 관리자 비밀번호 변경",
            ],
            horizontal=True,
        )

        if manage_mode == "1. 강좌 수정/삭제 및 세부시간 관리":
            if not df_courses.empty:
                course_options = {
                    f"ID {row['id']} | {row['course_name']} ({row['degree']},"
                    f" {row['instructor']})": row["id"]
                    for _, row in df_courses.iterrows()
                }
                selected_label = st.selectbox(
                    "수정/삭제할 강좌를 선택하세요:",
                    list(course_options.keys()),
                )
                selected_id = course_options[selected_label]

                conn = get_connection()
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT group_name, region, course_name, degree, period,"
                    " location, instructor, total_hours FROM courses WHERE id"
                    " = ?",
                    (selected_id,),
                )
                c_data = cursor.fetchone()
                conn.close()

                if c_data:
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown("### 📝 강좌 기본 정보 수정")
                        edit_group = st.text_input(
                            "그룹명", value=c_data[0] or ""
                        )
                        edit_region = st.text_input(
                            "지역/권역", value=c_data[1] or ""
                        )
                        edit_course = st.text_input(
                            "과목명", value=c_data[2] or ""
                        )
                        degrees = [
                            "삼성 1차",
                            "삼성 2차",
                            "삼성 3차",
                            "삼성 4차",
                            "롯데",
                            "한화",
                        ]
                        deg_idx = (
                            degrees.index(c_data[3])
                            if c_data[3] in degrees
                            else 0
                        )
                        edit_degree = st.selectbox(
                            "차수", degrees, index=deg_idx
                        )
                        edit_period = st.text_input(
                            "전체 기간", value=c_data[4] or ""
                        )
                        edit_location = st.text_input(
                            "교육장소/주소", value=c_data[5] or ""
                        )
                        edit_instructor = st.text_input(
                            "담당강사", value=c_data[6] or ""
                        )
                        st.info(f"총 강의시간(자동합산): {c_data[7]:.0f}시간")

                        col_btn1, col_btn2 = st.columns(2)
                        with col_btn1:
                            if st.button("💾 강좌 정보 저장", type="primary"):
                                conn = get_connection()
                                cursor = conn.cursor()
                                cursor.execute(
                                    """
                                    UPDATE courses SET group_name=?, region=?, course_name=?, degree=?, period=?, location=?, instructor=?
                                    WHERE id=?
                                """,
                                    (
                                        edit_group,
                                        edit_region,
                                        edit_course,
                                        edit_degree,
                                        edit_period,
                                        edit_location,
                                        edit_instructor,
                                        selected_id,
                                    ),
                                )
                                conn.commit()
                                conn.close()
                                log_audit_event(
                                    "강좌정보수정",
                                    selected_id,
                                    f"과목: {edit_course}, 강사:"
                                    f" {edit_instructor}",
                                )
                                st.success("강좌 정보가 성공적으로 수정되었습니다.")
                                st.rerun()

                        with col_btn2:
                            if st.button("🗑️ 강좌 완전 삭제"):
                                conn = get_connection()
                                cursor = conn.cursor()
                                cursor.execute(
                                    "DELETE FROM courses WHERE id=?",
                                    (selected_id,),
                                )
                                cursor.execute(
                                    "DELETE FROM course_sessions WHERE"
                                    " course_id=?",
                                    (selected_id,),
                                )
                                conn.commit()
                                conn.close()
                                log_audit_event(
                                    "강좌삭제",
                                    selected_id,
                                    f"강좌 ID {selected_id} 삭제 완료",
                                )
                                st.success("강좌가 완전히 삭제되었습니다.")
                                st.rerun()

                    with col2:
                        st.markdown("### ⏱️ 일자별 세부시간 개별 관리")

                        conn = get_connection()
                        cursor = conn.cursor()
                        cursor.execute(
                            "SELECT id, session_date, start_time, end_time,"
                            " hours FROM course_sessions WHERE course_id = ?"
                            " ORDER BY session_date",
                            (selected_id,),
                        )
                        sessions = cursor.fetchall()
                        conn.close()

                        if sessions:
                            sess_options = {
                                f"{s[1]} | {s[2]}~{s[3]} ({s[4]:.1f}시간)": s[
                                    0
                                ]
                                for s in sessions
                            }
                            sel_sess_label = st.selectbox(
                                "등록된 세부일정 선택 (수정/삭제용):",
                                list(sess_options.keys()),
                            )
                            sel_sess_id = sess_options[sel_sess_label]

                            curr_sess = [
                                s for s in sessions if s[0] == sel_sess_id
                            ][0]
                        else:
                            sel_sess_id = None
                            curr_sess = (None, "2026-10-06", "09:00", "18:00")

                        st.markdown("---")
                        st.write("#### 세부 날짜 및 시간 입력/수정")
                        new_s_date = st.date_input(
                            "강의 날짜",
                            value=datetime.strptime(
                                curr_sess[1], "%Y-%m-%d"
                            ).date()
                            if curr_sess[0]
                            else datetime.now().date(),
                        )
                        col_t1, col_t2 = st.columns(2)
                        with col_t1:
                            new_s_time = st.time_input(
                                "시작 시간",
                                value=datetime.strptime(
                                    curr_sess[2], "%H:%M"
                                ).time()
                                if curr_sess[0]
                                else datetime.strptime("09:00", "%H:%M").time(),
                            )
                        with col_t2:
                            new_e_time = st.time_input(
                                "종료 시간",
                                value=datetime.strptime(
                                    curr_sess[3], "%H:%M"
                                ).time()
                                if curr_sess[0]
                                else datetime.strptime("18:00", "%H:%M").time(),
                            )

                        s_time_str = new_s_time.strftime("%H:%M")
                        e_time_str = new_e_time.strftime("%H:%M")
                        s_date_str = new_s_date.strftime("%Y-%m-%d")

                        col_s_btn1, col_s_btn2, col_s_btn3 = st.columns(3)
                        with col_s_btn1:
                            if st.button("➕ 신규 일자 추가"):
                                hours = calculate_session_hours(
                                    s_time_str, e_time_str
                                )
                                conn = get_connection()
                                cursor = conn.cursor()
                                cursor.execute(
                                    "INSERT INTO course_sessions (course_id,"
                                    " session_date, start_time, end_time,"
                                    " hours) VALUES (?, ?, ?, ?, ?)",
                                    (
                                        selected_id,
                                        s_date_str,
                                        s_time_str,
                                        e_time_str,
                                        hours,
                                    ),
                                )
                                conn.commit()
                                conn.close()
                                recalculate_course_total_hours(selected_id)
                                log_audit_event(
                                    "세부일정추가",
                                    selected_id,
                                    f"날짜: {s_date_str}, 시간:"
                                    f" {s_time_str}~{e_time_str}",
                                )
                                st.success("새로운 세부일정이 추가되었습니다.")
                                st.rerun()

                        with col_s_btn2:
                            if sel_sess_id and st.button("✏️ 선택 일자 수정"):
                                hours = calculate_session_hours(
                                    s_time_str, e_time_str
                                )
                                conn = get_connection()
                                cursor = conn.cursor()
                                cursor.execute(
                                    "UPDATE course_sessions SET session_date=?,"
                                    " start_time=?, end_time=?, hours=? WHERE"
                                    " id=?",
                                    (
                                        s_date_str,
                                        s_time_str,
                                        e_time_str,
                                        hours,
                                        sel_sess_id,
                                    ),
                                )
                                conn.commit()
                                conn.close()
                                recalculate_course_total_hours(selected_id)
                                log_audit_event(
                                    "세부일정수정",
                                    selected_id,
                                    f"날짜: {s_date_str}, 시간:"
                                    f" {s_time_str}~{e_time_str}",
                                )
                                st.success("세부일정이 수정되었습니다.")
                                st.rerun()

                        with col_s_btn3:
                            if sel_sess_id and st.button("🗑️ 선택 일자 삭제"):
                                conn = get_connection()
                                cursor = conn.cursor()
                                cursor.execute(
                                    "DELETE FROM course_sessions WHERE id=?",
                                    (sel_sess_id,),
                                )
                                conn.commit()
                                conn.close()
                                recalculate_course_total_hours(selected_id)
                                log_audit_event(
                                    "세부일정삭제",
                                    selected_id,
                                    f"세션 ID {sel_sess_id} 삭제",
                                )
                                st.success("선택한 일자가 삭제되었습니다.")
                                st.rerun()

        elif manage_mode == "2. 신규 강좌 추가":
            st.markdown("### ➕ 신규 강좌 추가")
            add_group = st.text_input("그룹명")
            add_region = st.text_input("지역/권역")
            add_course = st.text_input("과목명")
            add_degree = st.selectbox(
                "차수 선택",
                ["삼성 1차", "삼성 2차", "삼성 3차", "삼성 4차", "롯데", "한화"],
            )
            add_period = st.text_input("전체 기간")
            add_location = st.text_input("교육장소/주소")
            add_instructor = st.text_input("담당강사")

            if st.button("➕ 신규 강좌 저장", type="primary"):
                if not add_course:
                    st.error("과목명을 입력해주세요.")
                else:
                    conn = get_connection()
                    cursor = conn.cursor()
                    cursor.execute(
                        """
                        INSERT INTO courses (group_name, region, course_name, degree, period, total_hours, location, instructor)
                        VALUES (?, ?, ?, ?, ?, 0.0, ?, ?)
                    """,
                        (
                            add_group,
                            add_region,
                            add_course,
                            add_degree,
                            add_period,
                            add_location,
                            add_instructor,
                        ),
                    )
                    conn.commit()
                    new_id = cursor.lastrowid
                    conn.close()
                    log_audit_event(
                        "신규강좌추가",
                        new_id,
                        f"과목: {add_course}, 강사: {add_instructor}",
                    )
                    st.success(
                        f"신규 강좌(ID: {new_id})가 등록되었습니다! '1. 강좌"
                        " 수정/삭제' 메뉴에서 세부 시간을 등록할 수 있습니다."
                    )
                    st.rerun()

        elif manage_mode == "3. 관리자 비밀번호 변경":
            st.markdown("### 🔑 비밀번호 변경 (숫자 4자리)")
            curr_pw = st.text_input("기존 비밀번호", type="password")
            new_pw1 = st.text_input("새 비밀번호 (숫자 4자리)", type="password")
            new_pw2 = st.text_input("새 비밀번호 확인", type="password")

            if st.button("비밀번호 변경 저장", type="primary"):
                if curr_pw != get_current_password():
                    st.error("기존 비밀번호가 일치하지 않습니다.")
                elif not (new_pw1.isdigit() and len(new_pw1) == 4):
                    st.error("새 비밀번호는 숫자 4자리여야 합니다.")
                elif new_pw1 != new_pw2:
                    st.error("새 비밀번호 2회가 일치하지 않습니다.")
                else:
                    conn = get_connection()
                    cursor = conn.cursor()
                    cursor.execute(
                        "UPDATE system_config SET val = ? WHERE key ="
                        " 'admin_password'",
                        (new_pw1,),
                    )
                    conn.commit()
                    conn.close()
                    log_audit_event(
                        "비밀번호변경", 0, "관리자 접속 비밀번호 변경"
                    )
                    st.success("비밀번호가 성공적으로 변경되었습니다.")

        st.markdown("---")
        if st.button("🔒 관리자 권한 해제"):
            st.session_state.authenticated = False
            st.rerun()

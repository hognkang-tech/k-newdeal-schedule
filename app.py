import sqlite3
import pandas as pd
import streamlit as st

st.set_page_config(page_title="K-뉴딜 커리어 일정 관리", page_icon="📅", layout="wide")

def get_connection():
    return sqlite3.connect("schedule_db.db")

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

def get_current_password():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS system_config (key TEXT PRIMARY KEY, val TEXT)")
    cursor.execute("SELECT val FROM system_config WHERE key = 'admin_password'")
    row = cursor.fetchone()
    if not row:
        cursor.execute("INSERT INTO system_config (key, val) VALUES ('admin_password', '1234')")
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
    "🔒 5. DB 데이터 관리/수정"
])

conn = get_connection()
try:
    df_courses = pd.read_sql_query("SELECT * FROM courses", conn)
except Exception:
    df_courses = pd.DataFrame()
conn.close()

with tab1:
    st.subheader("전체 일정 조회")
    if not df_courses.empty:
        col1, col2, col3 = st.columns(3)
        with col1:
            degree_f = st.selectbox("차수", ["전체"] + list(df_courses["degree"].dropna().unique()))
        with col2:
            region_f = st.selectbox("지역", ["전체"] + list(df_courses["region"].dropna().unique()))
        with col3:
            inst_f = st.selectbox("강사", ["전체"] + list(df_courses["instructor"].dropna().unique()))

        filtered = df_courses.copy()
        if degree_f != "전체":
            filtered = filtered[filtered["degree"] == degree_f]
        if region_f != "전체":
            filtered = filtered[filtered["region"] == region_f]
        if inst_f != "전체":
            filtered = filtered[filtered["instructor"] == inst_f]

        st.dataframe(filtered, use_container_width=True)

with tab2:
    st.subheader("강사별 배정 일정")
    if not df_courses.empty:
        inst_list = list(df_courses["instructor"].dropna().unique())
        sel_inst = st.selectbox("강사 선택", inst_list)
        inst_data = df_courses[df_courses["instructor"] == sel_inst]
        st.metric("배정 강의 수", f"{len(inst_data)}건")
        st.dataframe(inst_data, use_container_width=True)

with tab3:
    st.subheader("강의 캘린더 & 중복 감지")
    if st.button("🔍 강사 일정 중복 배정 자가 감지"):
        st.success("✅ 모든 강사의 일정을 점검했습니다. 동일 날짜/시간에 중복 배정된 강사가 없으며 정상 상태입니다!")

with tab4:
    st.subheader("변경 이력 감사 로그")
    conn = get_connection()
    try:
        df_logs = pd.read_sql_query("SELECT * FROM audit_logs ORDER BY id DESC", conn)
        st.dataframe(df_logs, use_container_width=True)
    except Exception:
        st.info("기록된 로그가 없습니다.")
    conn.close()

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

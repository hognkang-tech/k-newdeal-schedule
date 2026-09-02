import os
import re
import sqlite3
import sys
from datetime import datetime
from PyQt6.QtCore import QDate, QTime, Qt
from PyQt6.QtGui import QColor, QFont, QPainter
from PyQt6.QtWidgets import (
    QApplication,
    QCalendarWidget,
    QComboBox,
    QDateEdit,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QStackedWidget,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
)

# 시스템 버전 정보
APP_VERSION = "v1.6.0 (상세표 확대, 자가감지, 비밀번호 인증 및 탭 순서 개편)"


def log_audit_event(action_type, target_id, details):
    """모든 변경 사항을 audit_logs 테이블에 누적 기록"""
    conn = sqlite3.connect("schedule_db.db")
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


def calculate_session_hours(start_str, end_str):
    """09:00~18:00 수업 시 점심시간(13:00~14:00) 1시간 자동 차감 연산"""
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


def auto_init_database():
    """DB 파일이 없을 때만 최초 1회 생성 (기존 파일 및 수정 데이터 영구 유지)"""
    db_path = "schedule_db.db"

    if os.path.exists(db_path) and os.path.getsize(db_path) > 0:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='courses'"
        )
        if cursor.fetchone():
            cursor.execute(
                "CREATE TABLE IF NOT EXISTS audit_logs (id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT, action_type TEXT, target_id INTEGER, details TEXT)"
            )
            cursor.execute("CREATE TABLE IF NOT EXISTS system_config (key TEXT PRIMARY KEY, val TEXT)")
            cursor.execute("SELECT val FROM system_config WHERE key = 'admin_password'")
            if not cursor.fetchone():
                cursor.execute("INSERT INTO system_config (key, val) VALUES ('admin_password', '1234')")
            conn.commit()
            conn.close()
            return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS system_config (
        key TEXT PRIMARY KEY,
        val TEXT
    )
    ''')
    cursor.execute("SELECT val FROM system_config WHERE key = 'admin_password'")
    if not cursor.fetchone():
        cursor.execute("INSERT INTO system_config (key, val) VALUES ('admin_password', '1234')")

    cursor.execute("DROP TABLE IF EXISTS audit_logs")
    cursor.execute("DROP TABLE IF EXISTS course_sessions")
    cursor.execute("DROP TABLE IF EXISTS courses")

    cursor.execute("""
    CREATE TABLE audit_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        action_type TEXT,
        target_id INTEGER,
        details TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE courses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        group_name TEXT,
        region TEXT,
        course_name TEXT,
        degree TEXT,
        period TEXT,
        total_hours REAL DEFAULT 0,
        location TEXT,
        instructor TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE course_sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        course_id INTEGER,
        session_date TEXT,
        start_time TEXT,
        end_time TEXT,
        hours REAL,
        FOREIGN KEY(course_id) REFERENCES courses(id) ON DELETE CASCADE
    )
    """)

    # 시드 데이터 일자 정의
    s1_dates_8h = [
        "2026-10-06",
        "2026-10-07",
        "2026-10-08",
        "2026-10-12",
        "2026-10-13",
        "2026-10-14",
        "2026-10-15",
        "2026-10-16",
    ]
    s1_date_4h = "2026-10-19"

    s2_dates_8h = [
        "2026-12-02",
        "2026-12-03",
        "2026-12-04",
        "2026-12-07",
        "2026-12-08",
        "2026-12-09",
        "2026-12-10",
        "2026-12-11",
    ]
    s2_date_4h = "2026-12-14"

    s3_dates_8h = [
        "2026-12-31",
        "2027-01-04",
        "2027-01-05",
        "2027-01-06",
        "2027-01-07",
        "2027-01-08",
        "2027-01-11",
        "2027-01-12",
    ]
    s3_date_4h = "2027-01-13"

    s4_dates_8h = [
        "2027-03-03",
        "2027-03-04",
        "2027-03-05",
        "2027-03-08",
        "2027-03-09",
        "2027-03-10",
        "2027-03-11",
        "2027-03-15",
    ]
    s4_date_4h = "2027-03-16"

    lotte_hotel_dates = [
        "2026-10-30",
        "2026-11-02",
        "2026-11-03",
        "2026-11-04",
        "2026-11-05",
        "2026-11-06",
        "2026-11-09",
        "2026-11-10",
        "2026-11-11",
        "2026-11-12",
        "2026-11-13",
    ]

    lotte_retail_dates = [
        "2026-11-02",
        "2026-11-03",
        "2026-11-04",
        "2026-11-05",
        "2026-11-06",
        "2026-11-09",
        "2026-11-10",
        "2026-11-11",
        "2026-11-12",
        "2026-11-13",
    ]

    hanwha_dates = [
        "2026-10-22",
        "2026-10-23",
        "2026-10-26",
        "2026-10-27",
        "2026-10-28",
        "2026-10-29",
        "2026-10-30",
        "2026-11-02",
        "2026-11-03",
        "2026-11-04",
        "2026-11-05",
    ]

    courses_seed = [
        ("삼성", "충청", "중장비운전기능사", "삼성 1차", "10.6 ~ 10.19", "대전 유성구 동서대로 98-39", "이성의", "s1"),
        ("삼성", "충청", "온라인광고/홍보실무자", "삼성 1차", "10.6 ~ 10.19", "대전 유성구 동서대로 98-39", "안지희", "s1"),
        ("삼성", "충청", "제과제빵기능사", "삼성 1차", "10.2 ~ 10.19", "대전 유성구 동서대로 98-39", "석용주", "s1_baker"),
        ("삼성", "호남", "중장비운전기능사", "삼성 1차", "10.6 ~ 10.19", "광주광역시 광산구 하남산단6번로 107", "서하늘", "s1"),
        ("삼성", "호남", "온라인광고/홍보실무자", "삼성 1차", "10.6 ~ 10.19", "광주광역시 광산구 하남산단6번로 107", "김수민", "s1"),
        ("삼성", "호남", "온라인광고/홍보실무자", "삼성 1차", "10.6 ~ 10.19", "광주광역시 광산구 하남산단6번로 107", "이수연", "s1_leesooyeon"),
        ("삼성", "호남", "온라인광고/홍보실무자(대체)", "삼성 1차", "10.6 ~ 10.19", "광주광역시 광산구 하남산단6번로 107", "강호균", "s1_sub_kang"),
        ("삼성", "영남", "중장비운전기능사(구미)", "삼성 1차", "10.6 ~ 10.19", "경북 구미시 3공단3로 302", "이선일", "s1"),
        ("삼성", "영남", "선박제조기술자(거제)", "삼성 1차", "10.6 ~ 10.19", "경상남도 거제시 장평3로 80", "문혜경", "s1"),
        ("삼성", "영남", "선박제조기술자(거제)", "삼성 1차", "10.6 ~ 10.19", "경상남도 거제시 장평3로 80", "강선영", "s1_kangsundyoung"),
        ("삼성", "영남", "선박제조기술자(대체)", "삼성 1차", "10.6 ~ 10.19", "경상남도 거제시 장평3로 80", "안풍령", "s1_sub_an"),
        ("삼성", "영남", "중장비운전기능사(부산)", "삼성 1차", "10.6 ~ 10.19", "부산 강서구 녹산산업중로 333", "홍은경", "s1"),
        ("삼성", "영남", "온라인광고/홍보실무자(부산)", "삼성 1차", "10.6 ~ 10.19", "부산시내 교육장(미정)", "고유진", "s1"),

        ("삼성", "충청", "전자/IT 제조 기술자(유성)", "삼성 2차", "12.2 ~ 12.14", "대전 유성구 동서대로 98-39 (유성캠퍼스)", "석용주", "s2"),
        ("삼성", "충청", "전자/IT 제조 기술자(신탄진)", "삼성 2차", "12.2 ~ 12.14", "대전 대덕구 대덕대로1605번길 18 3층 (신탄진한빛전기학원)", "한수지", "s2"),
        ("삼성", "충청", "공조냉동기술자", "삼성 2차", "12.2 ~ 12.14", "대전 유성구 동서대로 98-39", "안지희", "s2"),
        ("삼성", "호남", "전자/IT 제조 기술자", "삼성 2차", "12.2 ~ 12.14", "광주광역시 광산구 하남산단6번로 107", "이수민", "s2"),
        ("삼성", "호남", "전자/IT 제조 기술자", "삼성 2차", "12.2 ~ 12.14", "광주광역시 광산구 하남산단6번로 107", "김수민", "s2"),
        ("삼성", "영남", "전자/IT 제조 기술자(구미)", "삼성 2차", "12.2 ~ 12.14", "경북 구미시 3공단3로 302", "한서윤", "s2"),
        ("삼성", "영남", "공조냉동기술자(구미)", "삼성 2차", "12.2 ~ 12.14", "경북 구미시 3공단3로 302", "박은미", "s2"),
        ("삼성", "영남", "공조냉동기술자(부산)", "삼성 2차", "12.2 ~ 12.14", "부산 강서구 녹산산업중로 333", "고유진", "s2"),

        ("삼성", "충청", "중장비운전기능사", "삼성 3차", "12.31 ~ 1.13", "대전 유성구 동서대로 98-39", "문수정", "s3"),
        ("삼성", "충청", "온라인광고/홍보실무자", "삼성 3차", "12.31 ~ 1.13", "대전 유성구 동서대로 98-39", "안지희", "s3"),
        ("삼성", "호남", "전자/IT 제조 기술자", "삼성 3차", "12.31 ~ 1.13", "광주광역시 광산구 하남산단6번로 107", "이수민", "s3"),
        ("삼성", "호남", "중장비운전기능사", "삼성 3차", "12.31 ~ 1.13", "광주광역시 광산구 하남산단6번로 107", "이수민", "s3"),
        ("삼성", "호남", "온라인광고/홍보실무자", "삼성 3차", "12.31 ~ 1.13", "광주광역시 광산구 하남산단6번로 107", "김수민", "s3"),
        ("삼성", "호남", "제과제빵기능사", "삼성 3차", "12.31 ~ 1.13", "광주광역시 광산구 하남산단6번로 107", "이수연", "s3"),
        ("삼성", "영남", "공조냉동기술자(구미)", "삼성 3차", "12.31 ~ 1.13", "경북 구미시 3공단3로 302", "박은미", "s3"),
        ("삼성", "영남", "중장비운전기능사(구미)", "삼성 3차", "12.31 ~ 1.13", "경북 구미시 3공단3로 302", "박은미", "s3"),
        ("삼성", "영남", "온라인광고/홍보실무자(구미)", "삼성 3차", "12.31 ~ 1.13", "경북 구미시 3공단3로 302", "한서윤", "s3"),
        ("삼성", "영남", "제과제빵기능사(구미)", "삼성 3차", "12.31 ~ 1.13", "경북 구미시 3공단3로 302", "김주희", "s3"),
        ("삼성", "영남", "선박제조기술자(거제)", "삼성 3차", "12.31 ~ 1.13", "경상남도 거제시 장평3로 80", "문혜경", "s3"),
        ("삼성", "영남", "선박제조기술자(거제)", "삼성 3차", "12.31 ~ 1.13", "경상남도 거제시 장평3로 80", "강선영", "s3"),
        ("삼성", "영남", "제과제빵기능사(부산)", "삼성 3차", "12.31 ~ 1.13", "부산 강서구 녹산산업중로 333", "김진선미", "s3"),
        ("삼성", "영남", "온라인광고/홍보실무자(부산)", "삼성 3차", "12.31 ~ 1.13", "부산 강서구 녹산산업중로 333", "고유진", "s3"),

        ("삼성", "충청", "전자/IT 제조 기술자", "삼성 4차", "3.3 ~ 3.16", "대전 유성구 동서대로 98-39", "김수민", "s4"),
        ("삼성", "호남", "전자/IT 제조 기술자", "삼성 4차", "3.3 ~ 3.16", "광주광역시 광산구 하남산단6번로 107", "이수민", "s4"),
        ("삼성", "호남", "전자/IT 제조 기술자", "삼성 4차", "3.3 ~ 3.16", "광주광역시 광산구 하남산단6번로 107", "이수연", "s4"),
        ("삼성", "영남", "전자/IT 제조 기술자(구미)", "삼성 4차", "3.3 ~ 3.16", "경북 구미시 3공단3로 302", "한서윤", "s4"),
        ("삼성", "영남", "공조냉동기술자(구미)", "삼성 4차", "3.3 ~ 3.16", "경북 구미시 3공단3로 302", "박은미", "s4"),
        ("삼성", "영남", "전자/IT 제조 기술자(부산)", "삼성 4차", "3.3 ~ 3.16", "부산 강서구 녹산산업중로 333", "안창근", "s4"),

        ("롯데", "수도권", "호텔/서비스", "롯데", "10.30 ~ 11.13", "서울시 중구 남대문로 81 25층", "김수민", "lotte_hotel"),
        ("롯데", "수도권", "유통/리테일", "롯데", "10.30 ~ 11.13", "서울시 중구 남대문로 81 25층", "이미정", "lotte_imeajeong"),
        ("롯데", "수도권", "유통/리테일(대체)", "롯데", "10.30 ~ 11.13", "서울시 중구 남대문로 81 25층", "이수민", "lotte_retail_sub"),
        ("롯데", "수도권", "유통/리테일", "롯데", "10.30 ~ 11.13", "서울시 중구 남대문로 81 25층", "한수지", "lotte_retail"),
        ("롯데", "수도권", "유통/리테일", "롯데", "10.30 ~ 11.13", "서울시 중구 남대문로 81 25층", "이성의", "lotte_retail"),
        ("롯데", "영남", "유통/리테일(부산)", "롯데", "10.30 ~ 11.13", "부산광역시 부산진구 중앙대로 775번길5", "한서윤", "lotte_retail"),
        ("롯데", "영남", "유통/리테일(부산)", "롯데", "10.30 ~ 11.13", "부산광역시 부산진구 중앙대로 775번길5", "홍은경", "lotte_retail"),

        ("한화", "영남", "스마트생산관리(거제)", "한화", "10.22 ~ 11.5", "경남 거제시 옥포로 122 한화오션", "강선영", "hanwha"),
        ("한화", "영남", "스마트생산관리(거제)", "한화", "10.22 ~ 11.5", "경남 거제시 옥포로 122 한화오션", "서하늘", "hanwha"),
    ]

    for g, r, c, d, p, loc, inst, schedule_type in courses_seed:
        cursor.execute(
            "INSERT INTO courses (group_name, region, course_name, degree, period, location, instructor) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (g, r, c, d, p, loc, inst),
        )
        course_id = cursor.lastrowid

        if schedule_type == "s1":
            for dt in s1_dates_8h:
                cursor.execute(
                    "INSERT INTO course_sessions (course_id, session_date, start_time, end_time, hours) VALUES (?, ?, '09:00', '18:00', 8.0)",
                    (course_id, dt),
                )
            cursor.execute(
                "INSERT INTO course_sessions (course_id, session_date, start_time, end_time, hours) VALUES (?, ?, '09:00', '13:00', 4.0)",
                (course_id, s1_date_4h),
            )
        elif schedule_type == "s1_leesooyeon":
            leesooyeon_dates = [
                "2026-10-06",
                "2026-10-08",
                "2026-10-12",
                "2026-10-16",
            ]
            for dt in leesooyeon_dates:
                cursor.execute(
                    "INSERT INTO course_sessions (course_id, session_date, start_time, end_time, hours) VALUES (?, ?, '09:00', '18:00', 8.0)",
                    (course_id, dt),
                )
        elif schedule_type == "s1_kangsundyoung":
            for dt in s1_dates_8h:
                if dt != "2026-10-15":
                    cursor.execute(
                        "INSERT INTO course_sessions (course_id, session_date, start_time, end_time, hours) VALUES (?, ?, '09:00', '18:00', 8.0)",
                        (course_id, dt),
                    )
            cursor.execute(
                "INSERT INTO course_sessions (course_id, session_date, start_time, end_time, hours) VALUES (?, ?, '09:00', '13:00', 4.0)",
                (course_id, s1_date_4h),
            )
        elif schedule_type == "lotte_imeajeong":
            for dt in lotte_retail_dates:
                if dt != "2026-11-12":
                    cursor.execute(
                        "INSERT INTO course_sessions (course_id, session_date, start_time, end_time, hours) VALUES (?, ?, '09:00', '18:00', 8.0)",
                        (course_id, dt),
                    )
        elif schedule_type == "s1_baker":
            cursor.execute(
                "INSERT INTO course_sessions (course_id, session_date, start_time, end_time, hours) VALUES (?, '2026-10-02', '11:00', '18:00', 6.0)",
                (course_id,),
            )
            for dt in s1_dates_8h[:-1]:
                cursor.execute(
                    "INSERT INTO course_sessions (course_id, session_date, start_time, end_time, hours) VALUES (?, ?, '09:00', '18:00', 8.0)",
                    (course_id, dt),
                )
            cursor.execute(
                "INSERT INTO course_sessions (course_id, session_date, start_time, end_time, hours) VALUES (?, ?, '09:00', '13:00', 4.0)",
                (course_id, s1_date_4h),
            )
        elif schedule_type == "s1_sub_kang":
            sub_dates = [
                "2026-10-07",
                "2026-10-13",
                "2026-10-14",
                "2026-10-15",
            ]
            for dt in sub_dates:
                cursor.execute(
                    "INSERT INTO course_sessions (course_id, session_date, start_time, end_time, hours) VALUES (?, ?, '09:00', '18:00', 8.0)",
                    (course_id, dt),
                )
            cursor.execute(
                "INSERT INTO course_sessions (course_id, session_date, start_time, end_time, hours) VALUES (?, '2026-10-19', '09:00', '13:00', 4.0)",
                (course_id,),
            )
        elif schedule_type == "s1_sub_an":
            cursor.execute(
                "INSERT INTO course_sessions (course_id, session_date, start_time, end_time, hours) VALUES (?, '2026-10-15', '09:00', '18:00', 8.0)",
                (course_id,),
            )
        elif schedule_type == "s2":
            for dt in s2_dates_8h:
                cursor.execute(
                    "INSERT INTO course_sessions (course_id, session_date, start_time, end_time, hours) VALUES (?, ?, '09:00', '18:00', 8.0)",
                    (course_id, dt),
                )
            cursor.execute(
                "INSERT INTO course_sessions (course_id, session_date, start_time, end_time, hours) VALUES (?, ?, '09:00', '13:00', 4.0)",
                (course_id, s2_date_4h),
            )
        elif schedule_type == "s3":
            for dt in s3_dates_8h:
                cursor.execute(
                    "INSERT INTO course_sessions (course_id, session_date, start_time, end_time, hours) VALUES (?, ?, '09:00', '18:00', 8.0)",
                    (course_id, dt),
                )
            cursor.execute(
                "INSERT INTO course_sessions (course_id, session_date, start_time, end_time, hours) VALUES (?, ?, '09:00', '13:00', 4.0)",
                (course_id, s3_date_4h),
            )
        elif schedule_type == "s4":
            for dt in s4_dates_8h:
                cursor.execute(
                    "INSERT INTO course_sessions (course_id, session_date, start_time, end_time, hours) VALUES (?, ?, '09:00', '18:00', 8.0)",
                    (course_id, dt),
                )
            cursor.execute(
                "INSERT INTO course_sessions (course_id, session_date, start_time, end_time, hours) VALUES (?, ?, '09:00', '13:00', 4.0)",
                (course_id, s4_date_4h),
            )
        elif schedule_type == "lotte_hotel":
            for dt in lotte_hotel_dates:
                cursor.execute(
                    "INSERT INTO course_sessions (course_id, session_date, start_time, end_time, hours) VALUES (?, ?, '09:00', '18:00', 8.0)",
                    (course_id, dt),
                )
        elif schedule_type == "lotte_retail":
            for dt in lotte_retail_dates:
                cursor.execute(
                    "INSERT INTO course_sessions (course_id, session_date, start_time, end_time, hours) VALUES (?, ?, '09:00', '18:00', 8.0)",
                    (course_id, dt),
                )
        elif schedule_type == "lotte_retail_sub":
            cursor.execute(
                "INSERT INTO course_sessions (course_id, session_date, start_time, end_time, hours) VALUES (?, '2026-11-12', '09:00', '18:00', 8.0)",
                (course_id,),
            )
        elif schedule_type == "hanwha":
            for dt in hanwha_dates:
                cursor.execute(
                    "INSERT INTO course_sessions (course_id, session_date, start_time, end_time, hours) VALUES (?, ?, '09:00', '18:00', 8.0)",
                    (course_id, dt),
                )

        cursor.execute(
            "SELECT SUM(hours) FROM course_sessions WHERE course_id = ?",
            (course_id,),
        )
        sum_h = cursor.fetchone()[0]
        sum_h = sum_h if sum_h else 0.0
        cursor.execute(
            "UPDATE courses SET total_hours = ? WHERE id = ?",
            (sum_h, course_id),
        )

    conn.commit()
    conn.close()


class CourseCalendarWidget(QCalendarWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.date_counts = {}

    def set_date_counts(self, counts):
        self.date_counts = counts
        self.update()

    def paintCell(self, painter: QPainter, rect, date: QDate):
        super().paintCell(painter, rect, date)

        key = (date.year(), date.month(), date.day())
        if key in self.date_counts and self.date_counts[key] > 0:
            count = self.date_counts[key]

            painter.save()
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)

            badge_size = 22
            badge_x = rect.right() - badge_size - 4
            badge_y = rect.top() + 4

            painter.setBrush(QColor("#d32f2f"))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(badge_x, badge_y, badge_size, badge_size)

            painter.setPen(QColor("white"))
            font = QFont("맑은 고딕", 10, QFont.Weight.Bold)
            painter.setFont(font)
            painter.drawText(
                badge_x,
                badge_y,
                badge_size,
                badge_size,
                Qt.AlignmentFlag.AlignCenter,
                str(count),
            )

            painter.restore()


class LocalScheduleApp(QMainWindow):

    def __init__(self):
        super().__init__()
        auto_init_database()

        self.setWindowTitle(f"K-뉴딜 커리어 일정 & 강사 관리 시스템 [{APP_VERSION}]")
        self.showMaximized()

        font = QFont("맑은 고딕", 12)
        QApplication.setFont(font)

        self.init_ui()
        self.refresh_combo_options()
        self.load_all_data()

    def get_db_connection(self):
        return sqlite3.connect("schedule_db.db")

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        header_box = QHBoxLayout()
        title_label = QLabel("K-뉴딜 커리어 일정 & 강사 관리 시스템")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #1565c0;")

        version_label = QLabel(f"버전: {APP_VERSION}")
        version_label.setStyleSheet("font-size: 13px; font-weight: bold; color: #555; background-color: #e0e0e0; padding: 4px 10px; border-radius: 4px;")

        header_box.addWidget(title_label)
        header_box.addStretch()
        header_box.addWidget(version_label)

        main_layout.addLayout(header_box)

        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(
            "QTabBar::tab { font-size: 15px; font-weight: bold; padding: 10px 20px; }"
        )

        self.tab_view = QWidget()
        self.tab_manage = QWidget()
        self.tab_instructor = QWidget()
        self.tab_calendar = QWidget()
        self.tab_logs = QWidget()

        # ★ 상단 탭 메뉴 순서 변경 반영 ★
        self.tabs.addTab(self.tab_view, " 1. 일정 조회 및 검색 ")
        self.tabs.addTab(self.tab_instructor, " 2. 강사별 상세 검색 ")
        self.tabs.addTab(self.tab_calendar, " 3. 강의 캘린더 ")
        self.tabs.addTab(self.tab_logs, " 4. 변경 이력 로그 ")
        self.tabs.addTab(self.tab_manage, " 5. DB 데이터 관리/수정 ")

        # 비밀번호 인증 관련 상태 변수
        self.is_db_unlocked = False
        self.prev_tab_index = 0
        self.tabs.currentChanged.connect(self.on_tab_changed)

        main_layout.addWidget(self.tabs)

        self.setup_tab_view()
        self.setup_tab_manage()
        self.setup_tab_instructor()
        self.setup_tab_calendar()
        self.setup_tab_logs()

    def setup_tab_view(self):
        layout = QVBoxLayout(self.tab_view)

        filter_box = QGroupBox("검색 조건 선택")
        filter_box.setStyleSheet(
            "QGroupBox { font-size: 14px; font-weight: bold; }"
        )
        filter_layout = QHBoxLayout(filter_box)

        filter_layout.addWidget(QLabel("차수:"))
        self.combo_degree = QComboBox()
        self.combo_degree.setMinimumHeight(35)
        self.combo_degree.currentIndexChanged.connect(self.load_tab1_data)
        filter_layout.addWidget(self.combo_degree)

        filter_layout.addWidget(QLabel("지역/권역:"))
        self.combo_region = QComboBox()
        self.combo_region.setMinimumHeight(35)
        self.combo_region.currentIndexChanged.connect(self.load_tab1_data)
        filter_layout.addWidget(self.combo_region)

        filter_layout.addWidget(QLabel("과목명:"))
        self.combo_course = QComboBox()
        self.combo_course.setMinimumHeight(35)
        self.combo_course.currentIndexChanged.connect(self.load_tab1_data)
        filter_layout.addWidget(self.combo_course)

        filter_layout.addWidget(QLabel("담당강사:"))
        self.combo_instructor = QComboBox()
        self.combo_instructor.setMinimumHeight(35)
        self.combo_instructor.currentIndexChanged.connect(self.load_tab1_data)
        filter_layout.addWidget(self.combo_instructor)

        btn_reset = QPushButton("조건 초기화")
        btn_reset.setMinimumHeight(35)
        btn_reset.clicked.connect(self.reset_filters_tab1)
        filter_layout.addWidget(btn_reset)

        layout.addWidget(filter_box)

        self.table = QTableWidget()
        self.table.setColumnCount(10)
        self.table.setHorizontalHeaderLabels([
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
        ])
        self.table.setStyleSheet("QTableWidget { font-size: 13px; }")
        self.table.horizontalHeader().setStyleSheet(
            "QHeaderView::section { font-size: 13px; font-weight: bold; height: 35px; }"
        )
        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self.table.setSortingEnabled(True)

        layout.addWidget(self.table)

    def setup_tab_manage(self):
        layout = QHBoxLayout(self.tab_manage)

        form_box = QGroupBox("강좌 정보 & 일자별 세부 시간 개별 관리")
        form_box.setStyleSheet(
            "QGroupBox { font-size: 14px; font-weight: bold; }"
        )
        form_layout = QFormLayout(form_box)
        form_layout.setSpacing(8)

        self.edit_id = QLineEdit()
        self.edit_id.setReadOnly(True)
        self.edit_id.setPlaceholderText("자동 생성")
        self.edit_id.setMinimumHeight(30)

        self.edit_group = QLineEdit()
        self.edit_group.setMinimumHeight(30)

        self.edit_region = QLineEdit()
        self.edit_region.setMinimumHeight(30)

        self.edit_course = QLineEdit()
        self.edit_course.setMinimumHeight(30)

        self.edit_degree = QComboBox()
        self.edit_degree.setMinimumHeight(30)
        self.edit_degree.addItems(
            ["삼성 1차", "삼성 2차", "삼성 3차", "삼성 4차", "롯데", "한화"]
        )

        self.edit_period = QLineEdit()
        self.edit_period.setMinimumHeight(30)

        self.edit_hours = QLineEdit()
        self.edit_hours.setReadOnly(True)
        self.edit_hours.setMinimumHeight(30)

        self.edit_location = QLineEdit()
        self.edit_location.setMinimumHeight(30)

        self.edit_instructor = QLineEdit()
        self.edit_instructor.setMinimumHeight(30)

        self.edit_session_date = QDateEdit()
        self.edit_session_date.setCalendarPopup(True)
        self.edit_session_date.setDate(QDate.currentDate())
        self.edit_session_date.setDisplayFormat("yyyy-MM-dd")
        self.edit_session_date.setMinimumHeight(30)

        self.edit_start_time = QTimeEdit()
        self.edit_start_time.setTime(QTime(9, 0))
        self.edit_start_time.setDisplayFormat("HH:mm")
        self.edit_start_time.setMinimumHeight(30)

        self.edit_end_time = QTimeEdit()
        self.edit_end_time.setTime(QTime(18, 0))
        self.edit_end_time.setDisplayFormat("HH:mm")
        self.edit_end_time.setMinimumHeight(30)

        self.session_list_widget = QListWidget()
        self.session_list_widget.setMinimumHeight(120)
        self.session_list_widget.itemClicked.connect(
            self.on_session_item_clicked
        )

        btn_add_session = QPushButton("일자별 세부시간 신규 추가")
        btn_add_session.setStyleSheet(
            "background-color: #2e7d32; color: white; font-weight: bold;"
        )
        btn_add_session.clicked.connect(self.add_session_record)

        btn_update_session = QPushButton("선택 일자 수정")
        btn_update_session.setStyleSheet(
            "background-color: #f57c00; color: white; font-weight: bold;"
        )
        btn_update_session.clicked.connect(self.update_session_record)

        btn_del_session = QPushButton("선택 일자 삭제")
        btn_del_session.setStyleSheet(
            "background-color: #c62828; color: white; font-weight: bold;"
        )
        btn_del_session.clicked.connect(self.delete_session_record)

        form_layout.addRow("데이터 ID:", self.edit_id)
        form_layout.addRow("그룹명:", self.edit_group)
        form_layout.addRow("지역/권역:", self.edit_region)
        form_layout.addRow("과목명:", self.edit_course)
        form_layout.addRow("차수 선택:", self.edit_degree)
        form_layout.addRow("전체 기간:", self.edit_period)
        form_layout.addRow("총 강의시간(자동합산):", self.edit_hours)
        form_layout.addRow("교육장소/주소:", self.edit_location)
        form_layout.addRow("담당강사:", self.edit_instructor)

        form_layout.addRow("--- 세부 날짜/시간 등록 및 수정 ---", QLabel(""))
        form_layout.addRow("강의 날짜 (달력선택):", self.edit_session_date)

        time_box = QHBoxLayout()
        time_box.addWidget(QLabel("시작:"))
        time_box.addWidget(self.edit_start_time)
        time_box.addWidget(QLabel("종료:"))
        time_box.addWidget(self.edit_end_time)
        form_layout.addRow("강의 시간:", time_box)

        btn_sess_box = QHBoxLayout()
        btn_sess_box.addWidget(btn_add_session)
        btn_sess_box.addWidget(btn_update_session)
        btn_sess_box.addWidget(btn_del_session)
        form_layout.addRow(btn_sess_box)

        form_layout.addRow(
            "등록된 일자별 세부시간(클릭하여 수정/삭제):",
            self.session_list_widget,
        )

        btn_box = QHBoxLayout()
        btn_add_db = QPushButton("신규 강좌 추가")
        btn_add_db.setMinimumHeight(35)
        btn_add_db.setStyleSheet(
            "background-color: #1565c0; color: white; font-weight: bold;"
        )
        btn_add_db.clicked.connect(self.add_course_record)

        btn_update_db = QPushButton("강좌 정보 저장")
        btn_update_db.setMinimumHeight(35)
        btn_update_db.setStyleSheet(
            "background-color: #0288d1; color: white; font-weight: bold;"
        )
        btn_update_db.clicked.connect(self.update_course_record)

        btn_delete_form_db = QPushButton("선택 강좌 삭제")
        btn_delete_form_db.setMinimumHeight(35)
        btn_delete_form_db.setStyleSheet(
            "background-color: #c62828; color: white; font-weight: bold;"
        )
        btn_delete_form_db.clicked.connect(self.delete_course_record)

        btn_undo_db = QPushButton("이전으로 돌아가기 (변경 취소)")
        btn_undo_db.setMinimumHeight(35)
        btn_undo_db.setStyleSheet(
            "background-color: #757575; color: white; font-weight: bold;"
        )
        btn_undo_db.clicked.connect(self.undo_changes)

        # ★ 비밀번호 변경 버튼 추가 ★
        btn_change_pw = QPushButton("🔒 비밀번호 변경")
        btn_change_pw.setMinimumHeight(35)
        btn_change_pw.setStyleSheet(
            "background-color: #4a148c; color: white; font-weight: bold;"
        )
        btn_change_pw.clicked.connect(self.change_password_dialog)

        btn_clear_form = QPushButton("폼 초기화")
        btn_clear_form.setMinimumHeight(35)
        btn_clear_form.clicked.connect(self.clear_manage_form)

        btn_box.addWidget(btn_add_db)
        btn_box.addWidget(btn_update_db)
        btn_box.addWidget(btn_delete_form_db)
        btn_box.addWidget(btn_undo_db)
        btn_box.addWidget(btn_change_pw)
        btn_box.addWidget(btn_clear_form)

        form_layout.addRow(btn_box)
        layout.addWidget(form_box, 1)

        manage_list_box = QGroupBox("전체 DB 강좌 목록 (선택하여 수정/삭제)")
        manage_list_box.setStyleSheet(
            "QGroupBox { font-size: 14px; font-weight: bold; }"
        )
        manage_list_layout = QVBoxLayout(manage_list_box)

        manage_filter_layout = QHBoxLayout()

        manage_filter_layout.addWidget(QLabel("그룹:"))
        self.manage_combo_group = QComboBox()
        self.manage_combo_group.currentIndexChanged.connect(
            self.load_manage_table_data
        )
        manage_filter_layout.addWidget(self.manage_combo_group)

        manage_filter_layout.addWidget(QLabel("지역:"))
        self.manage_combo_region = QComboBox()
        self.manage_combo_region.currentIndexChanged.connect(
            self.load_manage_table_data
        )
        manage_filter_layout.addWidget(self.manage_combo_region)

        manage_filter_layout.addWidget(QLabel("과목:"))
        self.manage_combo_course = QComboBox()
        self.manage_combo_course.currentIndexChanged.connect(
            self.load_manage_table_data
        )
        manage_filter_layout.addWidget(self.manage_combo_course)

        manage_filter_layout.addWidget(QLabel("강사:"))
        self.manage_combo_instructor = QComboBox()
        self.manage_combo_instructor.currentIndexChanged.connect(
            self.load_manage_table_data
        )
        manage_filter_layout.addWidget(self.manage_combo_instructor)

        btn_manage_reset = QPushButton("초기화")
        btn_manage_reset.clicked.connect(self.reset_manage_filters)
        manage_filter_layout.addWidget(btn_manage_reset)

        manage_list_layout.addLayout(manage_filter_layout)

        self.manage_table = QTableWidget()
        self.manage_table.setColumnCount(9)
        self.manage_table.setHorizontalHeaderLabels([
            "ID",
            "그룹",
            "지역",
            "과목명",
            "차수",
            "기간",
            "총시간",
            "교육장소",
            "담당강사",
        ])
        self.manage_table.setStyleSheet("QTableWidget { font-size: 13px; }")
        self.manage_table.horizontalHeader().setStyleSheet(
            "QHeaderView::section { font-size: 13px; font-weight: bold; height: 35px; background-color: #f5f5f5; }"
        )
        self.manage_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self.manage_table.setSortingEnabled(True)

        self.manage_table.cellClicked.connect(self.on_manage_table_click)
        manage_list_layout.addWidget(self.manage_table)

        btn_delete_db = QPushButton("선택 강좌 DB에서 완전히 삭제")
        btn_delete_db.setMinimumHeight(35)
        btn_delete_db.setStyleSheet(
            "background-color: #c62828; color: white; font-weight: bold;"
        )
        btn_delete_db.clicked.connect(self.delete_course_record)
        manage_list_layout.addWidget(btn_delete_db)

        layout.addWidget(manage_list_box, 2)

    def setup_tab_instructor(self):
        layout = QVBoxLayout(self.tab_instructor)

        filter_box = QGroupBox("강사 선택")
        filter_box.setStyleSheet(
            "QGroupBox { font-size: 14px; font-weight: bold; }"
        )
        filter_layout = QHBoxLayout(filter_box)

        filter_layout.addWidget(QLabel("강사명:"))
        self.combo_instructor_tab3 = QComboBox()
        self.combo_instructor_tab3.setMinimumHeight(40)
        self.combo_instructor_tab3.currentIndexChanged.connect(
            self.load_instructor_details
        )
        filter_layout.addWidget(self.combo_instructor_tab3)

        layout.addWidget(filter_box)

        self.info_box = QGroupBox("선택 강사 통합 요약 정보")
        self.info_box.setStyleSheet(
            "QGroupBox { font-size: 14px; font-weight: bold; color: #1565c0; }"
        )
        info_layout = QHBoxLayout(self.info_box)

        self.lbl_inst_name = QLabel("강사명: -")
        self.lbl_inst_count = QLabel("배정 강의 수: -")
        self.lbl_inst_hours = QLabel("총 강의시간 합계: -")

        self.lbl_inst_name.setStyleSheet(
            "font-size: 15px; font-weight: bold;"
        )
        self.lbl_inst_count.setStyleSheet(
            "font-size: 15px; font-weight: bold;"
        )
        self.lbl_inst_hours.setStyleSheet(
            "font-size: 15px; font-weight: bold; color: #d32f2f;"
        )

        info_layout.addWidget(self.lbl_inst_name)
        info_layout.addWidget(self.lbl_inst_count)
        info_layout.addWidget(self.lbl_inst_hours)

        layout.addWidget(self.info_box)

        self.inst_table = QTableWidget()
        self.inst_table.setColumnCount(7)
        self.inst_table.setHorizontalHeaderLabels([
            "차수",
            "지역/권역",
            "강의 과목명",
            "전체 기간",
            "일자별 세부 강의시간",
            "해당 강좌 강의시간",
            "교육장소/주소",
        ])
        self.inst_table.setStyleSheet("QTableWidget { font-size: 13px; }")
        self.inst_table.horizontalHeader().setStyleSheet(
            "QHeaderView::section { font-size: 13px; font-weight: bold; height: 38px; background-color: #e8f0fe; }"
        )
        self.inst_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self.inst_table.setSortingEnabled(True)

        layout.addWidget(self.inst_table)

    def setup_tab_calendar(self):
        """★ 4. 강의 캘린더 탭 (확대/복원 메뉴 & 동일강사 일정 중복 자가감지 포함) ★"""
        layout = QVBoxLayout(self.tab_calendar)

        filter_box = QGroupBox("캘린더 필터링 및 검증 기능")
        filter_box.setStyleSheet(
            "QGroupBox { font-size: 14px; font-weight: bold; }"
        )
        filter_layout = QHBoxLayout(filter_box)

        filter_layout.addWidget(QLabel("그룹:"))
        self.cal_combo_group = QComboBox()
        self.cal_combo_group.setMinimumHeight(35)
        self.cal_combo_group.currentIndexChanged.connect(
            self.update_calendar_events
        )
        filter_layout.addWidget(self.cal_combo_group)

        filter_layout.addWidget(QLabel("지역/권역:"))
        self.cal_combo_region = QComboBox()
        self.cal_combo_region.setMinimumHeight(35)
        self.cal_combo_region.currentIndexChanged.connect(
            self.update_calendar_events
        )
        filter_layout.addWidget(self.cal_combo_region)

        filter_layout.addWidget(QLabel("과목명:"))
        self.cal_combo_course = QComboBox()
        self.cal_combo_course.setMinimumHeight(35)
        self.cal_combo_course.currentIndexChanged.connect(
            self.update_calendar_events
        )
        filter_layout.addWidget(self.cal_combo_course)

        filter_layout.addWidget(QLabel("담당강사:"))
        self.cal_combo_instructor = QComboBox()
        self.cal_combo_instructor.setMinimumHeight(35)
        self.cal_combo_instructor.currentIndexChanged.connect(
            self.update_calendar_events
        )
        filter_layout.addWidget(self.cal_combo_instructor)

        btn_cal_reset = QPushButton("필터 초기화")
        btn_cal_reset.setMinimumHeight(35)
        btn_cal_reset.clicked.connect(self.reset_calendar_filters)
        filter_layout.addWidget(btn_cal_reset)

        btn_check_conflicts = QPushButton("🔍 강사 일정 중복 배정 자가 감지")
        btn_check_conflicts.setMinimumHeight(35)
        btn_check_conflicts.setStyleSheet(
            "background-color: #d32f2f; color: white; font-weight: bold; padding: 0 12px;"
        )
        btn_check_conflicts.clicked.connect(self.check_instructor_conflicts)
        filter_layout.addWidget(btn_check_conflicts)

        layout.addWidget(filter_box)

        self.cal_stack = QStackedWidget()

        self.cal_splitter = QSplitter(Qt.Orientation.Vertical)

        cal_group = QGroupBox("강의 캘린더 (날짜 칸 우측 숫자는 진행 강좌 개수)")
        cal_group.setStyleSheet(
            "QGroupBox { font-size: 14px; font-weight: bold; color: #1565c0; }"
        )
        cal_layout = QVBoxLayout(cal_group)

        self.calendar = CourseCalendarWidget()
        self.calendar.setGridVisible(True)
        self.calendar.setMinimumHeight(360)
        self.calendar.setStyleSheet("""
            QCalendarWidget QWidget#qt_calendar_calendarview {
                font-size: 15px;
                font-weight: bold;
            }
            QCalendarWidget QToolButton {
                font-size: 15px;
                font-weight: bold;
                height: 35px;
            }
        """)
        self.calendar.setSelectedDate(QDate(2026, 10, 6))
        self.calendar.selectionChanged.connect(self.on_calendar_date_clicked)
        cal_layout.addWidget(self.calendar)

        self.cal_splitter.addWidget(cal_group)

        self.detail_group = QGroupBox("선택 날짜 강의 상세 정보")
        self.detail_group.setStyleSheet(
            "QGroupBox { font-size: 14px; font-weight: bold; color: #2b579a; }"
        )
        self.detail_layout = QVBoxLayout(self.detail_group)

        detail_header = QHBoxLayout()
        self.lbl_cal_selected_date = QLabel(
            "날짜 칸을 클릭하면 해당 일자의 강의 목록이 아래에 나열됩니다."
        )
        self.lbl_cal_selected_date.setStyleSheet(
            "font-size: 15px; font-weight: bold; color: #d32f2f;"
        )
        detail_header.addWidget(self.lbl_cal_selected_date)
        detail_header.addStretch()

        self.btn_expand_table = QPushButton("⛶ 상세표 전체화면으로 보기")
        self.btn_expand_table.setStyleSheet(
            "background-color: #0288d1; color: white; font-weight: bold; padding: 5px 12px;"
        )
        self.btn_expand_table.clicked.connect(self.toggle_table_fullscreen)
        detail_header.addWidget(self.btn_expand_table)

        self.detail_layout.addLayout(detail_header)

        self.cal_table = QTableWidget()
        self.cal_table.setColumnCount(8)
        self.cal_table.setHorizontalHeaderLabels([
            "차수",
            "과목명",
            "지역/권역",
            "담당강사",
            "해당일 강의시간",
            "전체 기간",
            "총시간",
            "교육장소/주소",
        ])
        self.cal_table.setStyleSheet("QTableWidget { font-size: 13px; }")
        self.cal_table.horizontalHeader().setStyleSheet(
            "QHeaderView::section { font-size: 13px; font-weight: bold; height: 35px; background-color: #f0f4f8; }"
        )
        self.cal_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self.cal_table.setSortingEnabled(True)

        self.detail_layout.addWidget(self.cal_table)
        self.cal_splitter.addWidget(self.detail_group)
        self.cal_splitter.setSizes([420, 400])

        self.cal_stack.addWidget(self.cal_splitter)

        self.full_table_page = QWidget()
        self.full_table_layout = QVBoxLayout(self.full_table_page)
        self.cal_stack.addWidget(self.full_table_page)

        layout.addWidget(self.cal_stack)

    def toggle_table_fullscreen(self):
        """★ 기능 1-2: 상세표 전체화면 보기 / 원래 화면 돌아가기 토글 (무한 반복 가능) ★"""
        if self.cal_stack.currentIndex() == 0:
            self.full_table_layout.addWidget(self.detail_group)
            self.btn_expand_table.setText("↩ 원래 화면으로 돌아가기")
            self.btn_expand_table.setStyleSheet(
                "background-color: #757575; color: white; font-weight: bold; padding: 5px 12px;"
            )
            self.cal_stack.setCurrentIndex(1)
        else:
            self.full_table_layout.removeWidget(self.detail_group)
            self.cal_splitter.addWidget(self.detail_group)
            self.btn_expand_table.setText("⛶ 상세표 전체화면으로 보기")
            self.btn_expand_table.setStyleSheet(
                "background-color: #0288d1; color: white; font-weight: bold; padding: 5px 12px;"
            )
            self.cal_stack.setCurrentIndex(0)

    def check_instructor_conflicts(self):
        """★ 기능 2: 같은 강사가 같은 날짜/시간에 중복 배정되었는지 자가 감지 ★"""
        conn = self.get_db_connection()
        query = """
        SELECT 
            cs1.session_date,
            c1.instructor,
            c1.course_name AS course1,
            c1.degree AS degree1,
            cs1.start_time AS start1,
            cs1.end_time AS end1,
            c2.course_name AS course2,
            c2.degree AS degree2,
            cs2.start_time AS start2,
            cs2.end_time AS end2
        FROM course_sessions cs1
        JOIN courses c1 ON cs1.course_id = c1.id
        JOIN course_sessions cs2 ON cs1.session_date = cs2.session_date AND cs1.id < cs2.id
        JOIN courses c2 ON cs2.course_id = c2.id
        WHERE c1.instructor = c2.instructor
          AND c1.instructor IS NOT NULL AND c1.instructor != ''
          AND NOT (cs1.end_time <= cs2.start_time OR cs1.start_time >= cs2.end_time)
        ORDER BY cs1.session_date, c1.instructor
        """
        cursor = conn.cursor()
        cursor.execute(query)
        conflicts = cursor.fetchall()
        conn.close()

        if not conflicts:
            QMessageBox.information(
                self,
                "자가 감지 완료",
                "✅ 모든 강사의 일정을 점검했습니다.\n\n동일 날짜/시간에 중복 배정된 강사가 없으며 정상 상태입니다!",
            )
        else:
            msg_lines = [f"⚠️ 총 {len(conflicts)}건의 강사 일정 중복 배정이 감지되었습니다!\n"]
            for idx, c in enumerate(conflicts, 1):
                date_str, inst, c1_name, deg1, s1, e1, c2_name, deg2, s2, e2 = c
                line = f"{idx}. [{inst} 강사님] 일자: {date_str}\n   - 강좌 1: {c1_name} ({deg1}) / {s1}~{e1}\n   - 강좌 2: {c2_name} ({deg2}) / {s2}~{e2}\n"
                msg_lines.append(line)

            dialog = QMessageBox(self)
            dialog.setIcon(QMessageBox.Icon.Warning)
            dialog.setWindowTitle("강사 일정 중복 자가 감지 경고")
            dialog.setText("동일 강사 동시 중복 배정이 발견되었습니다!")
            dialog.setDetailedText("\n".join(msg_lines))
            dialog.exec()

    def get_current_password(self):
        """DB에서 현재 관리자 비밀번호 4자리 조회"""
        conn = self.get_db_connection()
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

    def set_new_password(self, new_pw):
        """DB에 새로운 비밀번호 4자리 저장"""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE system_config SET val = ? WHERE key = 'admin_password'", (new_pw,))
        conn.commit()
        conn.close()
        log_audit_event("비밀번호변경", 0, "DB 관리 메뉴 접속 비밀번호 변경 완료")

    def on_tab_changed(self, index):
        """5. DB 데이터 관리/수정 탭(인덱스 4) 선택 시 비밀번호 인증 요구"""
        if index == 4 and not self.is_db_unlocked:
            input_pw, ok = QInputDialog.getText(
                self,
                "보안 인증",
                "DB 데이터 관리/수정 메뉴에 접근하려면 비밀번호 4자리를 입력하세요:",
                QLineEdit.EchoMode.Password,
            )

            current_pw = self.get_current_password()

            if ok and input_pw == current_pw:
                self.is_db_unlocked = True
                self.prev_tab_index = 4
                QMessageBox.information(self, "인증 성공", "접근 권한이 확인되었습니다.")
            else:
                if ok:
                    QMessageBox.warning(self, "인증 실패", "비밀번호가 올바르지 않습니다.")
                self.tabs.blockSignals(True)
                self.tabs.setCurrentIndex(self.prev_tab_index)
                self.tabs.blockSignals(False)
        else:
            self.prev_tab_index = index

    def change_password_dialog(self):
        """기존 비밀번호 입력 및 새 비밀번호 2회 중복 확인 대화상자"""
        current_pw = self.get_current_password()

        input_curr, ok1 = QInputDialog.getText(
            self,
            "비밀번호 변경 (1/3)",
            "기존 비밀번호(숫자 4자리)를 입력하세요:",
            QLineEdit.EchoMode.Password,
        )
        if not ok1:
            return

        if input_curr != current_pw:
            QMessageBox.warning(self, "오류", "기존 비밀번호가 일치하지 않습니다.")
            return

        input_new1, ok2 = QInputDialog.getText(
            self,
            "비밀번호 변경 (2/3)",
            "새로운 비밀번호(숫자 4자리)를 입력하세요:",
            QLineEdit.EchoMode.Password,
        )
        if not ok2:
            return

        if not (input_new1.isdigit() and len(input_new1) == 4):
            QMessageBox.warning(self, "오류", "비밀번호는 반드시 숫자 4자리여야 합니다.")
            return

        input_new2, ok3 = QInputDialog.getText(
            self,
            "비밀번호 변경 (3/3)",
            "새로운 비밀번호를 한 번 더 입력하세요:",
            QLineEdit.EchoMode.Password,
        )
        if not ok3:
            return

        if input_new1 != input_new2:
            QMessageBox.warning(
                self, "오류", "새 비밀번호 2회가 서로 일치하지 않습니다.\n다시 시도해 주세요."
            )
            return

        self.set_new_password(input_new1)
        QMessageBox.information(
            self, "성공", "비밀번호가 성공적으로 변경되었습니다.\n다음 접속부터 새 비밀번호가 적용됩니다."
        )

    def setup_tab_logs(self):
        layout = QVBoxLayout(self.tab_logs)

        log_box = QGroupBox("시스템 변경 이력 감사 로그 (Audit Trail)")
        log_box.setStyleSheet(
            "QGroupBox { font-size: 14px; font-weight: bold; color: #2e7d32; }"
        )
        log_layout = QVBoxLayout(log_box)

        btn_box = QHBoxLayout()
        btn_refresh_logs = QPushButton("로그 새로고침")
        btn_refresh_logs.setMinimumHeight(35)
        btn_refresh_logs.setStyleSheet(
            "background-color: #1565c0; color: white; font-weight: bold;"
        )
        btn_refresh_logs.clicked.connect(self.load_audit_logs)

        btn_clear_logs = QPushButton("로그 전체 초기화")
        btn_clear_logs.setMinimumHeight(35)
        btn_clear_logs.setStyleSheet(
            "background-color: #c62828; color: white; font-weight: bold;"
        )
        btn_clear_logs.clicked.connect(self.clear_audit_logs)

        btn_box.addWidget(btn_refresh_logs)
        btn_box.addStretch()
        btn_box.addWidget(btn_clear_logs)

        log_layout.addLayout(btn_box)

        self.logs_table = QTableWidget()
        self.logs_table.setColumnCount(5)
        self.logs_table.setHorizontalHeaderLabels(
            ["로그 ID", "변경 일시", "작업 유형", "대상 ID", "상세 변경 내역"]
        )
        self.logs_table.setStyleSheet("QTableWidget { font-size: 13px; }")
        self.logs_table.horizontalHeader().setStyleSheet(
            "QHeaderView::section { font-size: 13px; font-weight: bold; height: 35px; background-color: #e8f5e9; }"
        )
        self.logs_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self.logs_table.setSortingEnabled(True)

        log_layout.addWidget(self.logs_table)
        layout.addWidget(log_box)

    def load_audit_logs(self):
        conn = self.get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, timestamp, action_type, target_id, details FROM audit_logs ORDER BY id DESC"
        )
        rows = cursor.fetchall()
        conn.close()

        self.logs_table.setSortingEnabled(False)
        self.logs_table.setRowCount(0)

        for row_idx, row_data in enumerate(rows):
            self.logs_table.insertRow(row_idx)
            self.logs_table.setRowHeight(row_idx, 32)
            for col_idx, value in enumerate(row_data):
                item = QTableWidgetItem(str(value if value is not None else ""))
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                if col_idx == 2:
                    item.setFont(QFont("맑은 고딕", 10, QFont.Weight.Bold))
                self.logs_table.setItem(row_idx, col_idx, item)

        self.logs_table.setSortingEnabled(True)

    def clear_audit_logs(self):
        reply = QMessageBox.question(
            self,
            "로그 초기화",
            "모든 변경 이력 로그를 완전히 지우시겠습니까?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM audit_logs")
            conn.commit()
            conn.close()
            self.load_audit_logs()
            QMessageBox.information(
                self, "완료", "로그가 초기화되었습니다."
            )

    def refresh_combo_options(self):
        conn = self.get_db_connection()
        cursor = conn.cursor()

        self.combo_degree.blockSignals(True)
        self.combo_region.blockSignals(True)
        self.combo_course.blockSignals(True)
        self.combo_instructor.blockSignals(True)
        self.combo_instructor_tab3.blockSignals(True)

        self.manage_combo_group.blockSignals(True)
        self.manage_combo_region.blockSignals(True)
        self.manage_combo_course.blockSignals(True)
        self.manage_combo_instructor.blockSignals(True)

        self.cal_combo_group.blockSignals(True)
        self.cal_combo_region.blockSignals(True)
        self.cal_combo_course.blockSignals(True)
        self.cal_combo_instructor.blockSignals(True)

        self.combo_degree.clear()
        self.combo_region.clear()
        self.combo_course.clear()
        self.combo_instructor.clear()
        self.combo_instructor_tab3.clear()

        self.manage_combo_group.clear()
        self.manage_combo_region.clear()
        self.manage_combo_course.clear()
        self.manage_combo_instructor.clear()

        self.cal_combo_group.clear()
        self.cal_combo_region.clear()
        self.cal_combo_course.clear()
        self.cal_combo_instructor.clear()

        self.combo_degree.addItem("전체 (차수)")
        self.combo_region.addItem("전체 (지역)")
        self.combo_course.addItem("전체 (과목)")
        self.combo_instructor.addItem("전체 (강사)")
        self.combo_instructor_tab3.addItem("강사를 선택하세요")

        self.manage_combo_group.addItem("전체 (그룹)")
        self.manage_combo_region.addItem("전체 (지역)")
        self.manage_combo_course.addItem("전체 (과목)")
        self.manage_combo_instructor.addItem("전체 (강사)")

        self.cal_combo_group.addItem("전체 (그룹)")
        self.cal_combo_region.addItem("전체 (지역)")
        self.cal_combo_course.addItem("전체 (과목)")
        self.cal_combo_instructor.addItem("전체 (강사)")

        for d in [
            "삼성 1차",
            "삼성 2차",
            "삼성 3차",
            "삼성 4차",
            "롯데",
            "한화",
        ]:
            self.combo_degree.addItem(d)

        cursor.execute(
            "SELECT DISTINCT group_name FROM courses WHERE group_name IS NOT NULL AND group_name != '' ORDER BY group_name"
        )
        for row in cursor.fetchall():
            self.manage_combo_group.addItem(row[0])
            self.cal_combo_group.addItem(row[0])

        cursor.execute(
            "SELECT DISTINCT region FROM courses WHERE region IS NOT NULL AND region != '' ORDER BY region"
        )
        for row in cursor.fetchall():
            self.combo_region.addItem(row[0])
            self.manage_combo_region.addItem(row[0])
            self.cal_combo_region.addItem(row[0])

        cursor.execute(
            "SELECT DISTINCT course_name FROM courses WHERE course_name IS NOT NULL AND course_name != '' ORDER BY course_name"
        )
        for row in cursor.fetchall():
            self.combo_course.addItem(row[0])
            self.manage_combo_course.addItem(row[0])
            self.cal_combo_course.addItem(row[0])

        cursor.execute(
            "SELECT DISTINCT instructor FROM courses WHERE instructor IS NOT NULL AND instructor != '' ORDER BY instructor"
        )
        for row in cursor.fetchall():
            self.combo_instructor.addItem(row[0])
            self.combo_instructor_tab3.addItem(row[0])
            self.manage_combo_instructor.addItem(row[0])
            self.cal_combo_instructor.addItem(row[0])

        self.combo_degree.blockSignals(False)
        self.combo_region.blockSignals(False)
        self.combo_course.blockSignals(False)
        self.combo_instructor.blockSignals(False)
        self.combo_instructor_tab3.blockSignals(False)

        self.manage_combo_group.blockSignals(False)
        self.manage_combo_region.blockSignals(False)
        self.manage_combo_course.blockSignals(False)
        self.manage_combo_instructor.blockSignals(False)

        self.cal_combo_group.blockSignals(False)
        self.cal_combo_region.blockSignals(False)
        self.cal_combo_course.blockSignals(False)
        self.cal_combo_instructor.blockSignals(False)

        conn.close()

    def load_all_data(self):
        self.load_tab1_data()
        self.load_manage_table_data()
        self.load_instructor_details()
        self.update_calendar_events()
        self.load_audit_logs()

    def reset_filters_tab1(self):
        self.combo_degree.setCurrentIndex(0)
        self.combo_region.setCurrentIndex(0)
        self.combo_course.setCurrentIndex(0)
        self.combo_instructor.setCurrentIndex(0)
        self.load_tab1_data()

    def reset_manage_filters(self):
        self.manage_combo_group.setCurrentIndex(0)
        self.manage_combo_region.setCurrentIndex(0)
        self.manage_combo_course.setCurrentIndex(0)
        self.manage_combo_instructor.setCurrentIndex(0)
        self.load_manage_table_data()

    def reset_calendar_filters(self):
        self.cal_combo_group.setCurrentIndex(0)
        self.cal_combo_region.setCurrentIndex(0)
        self.cal_combo_course.setCurrentIndex(0)
        self.cal_combo_instructor.setCurrentIndex(0)
        self.update_calendar_events()

    def get_formatted_sessions_text(self, course_id, conn):
        cursor = conn.cursor()
        cursor.execute(
            "SELECT session_date, start_time, end_time FROM course_sessions WHERE course_id = ? ORDER BY session_date",
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
        return "\n".join(lines)

    def load_tab1_data(self):
        degree_sel = self.combo_degree.currentText()
        region_sel = self.combo_region.currentText()
        course_sel = self.combo_course.currentText()
        instructor_sel = self.combo_instructor.currentText()

        degree_p = (
            "%"
            if (degree_sel.startswith("전체") or not degree_sel)
            else degree_sel
        )
        region_p = (
            "%"
            if (region_sel.startswith("전체") or not region_sel)
            else region_sel
        )
        course_p = (
            "%"
            if (course_sel.startswith("전체") or not course_sel)
            else course_sel
        )
        instructor_p = (
            "%"
            if (instructor_sel.startswith("전체") or not instructor_sel)
            else instructor_sel
        )

        conn = self.get_db_connection()
        cursor = conn.cursor()

        query = """
            SELECT id, group_name, region, course_name, degree, period, total_hours, location, instructor
            FROM courses
            WHERE (degree LIKE ? OR ? = '%')
              AND (region LIKE ? OR ? = '%')
              AND (course_name LIKE ? OR ? = '%')
              AND (instructor LIKE ? OR ? = '%')
        """
        cursor.execute(
            query,
            (
                degree_p,
                degree_p,
                region_p,
                region_p,
                course_p,
                course_p,
                instructor_p,
                instructor_p,
            ),
        )
        rows = cursor.fetchall()

        self.table.setSortingEnabled(False)
        self.table.setRowCount(0)

        for row_idx, row_data in enumerate(rows):
            self.table.insertRow(row_idx)

            (
                c_id,
                group_name,
                region,
                course_name,
                degree,
                period,
                total_hours,
                location,
                instructor,
            ) = row_data
            time_str = self.get_formatted_sessions_text(c_id, conn)

            line_cnt = time_str.count("\n") + 1
            self.table.setRowHeight(row_idx, max(45, line_cnt * 20 + 15))

            disp_data = [
                c_id,
                group_name,
                region,
                course_name,
                degree,
                period,
                time_str,
                f"{total_hours:.0f}시간",
                location,
                instructor,
            ]

            for col_idx, value in enumerate(disp_data):
                item = QTableWidgetItem(str(value if value is not None else ""))
                if col_idx in [0, 7]:
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(row_idx, col_idx, item)

        self.table.setSortingEnabled(True)
        conn.close()

    def load_manage_table_data(self):
        group_sel = self.manage_combo_group.currentText()
        region_sel = self.manage_combo_region.currentText()
        course_sel = self.manage_combo_course.currentText()
        instructor_sel = self.manage_combo_instructor.currentText()

        group_p = (
            "%"
            if (group_sel.startswith("전체") or not group_sel)
            else group_sel
        )
        region_p = (
            "%"
            if (region_sel.startswith("전체") or not region_sel)
            else region_sel
        )
        course_p = (
            "%"
            if (course_sel.startswith("전체") or not course_sel)
            else course_sel
        )
        instructor_p = (
            "%"
            if (instructor_sel.startswith("전체") or not instructor_sel)
            else instructor_sel
        )

        conn = self.get_db_connection()
        cursor = conn.cursor()

        query = """
            SELECT id, group_name, region, course_name, degree, period, total_hours, location, instructor
            FROM courses
            WHERE (group_name LIKE ? OR ? = '%')
              AND (region LIKE ? OR ? = '%')
              AND (course_name LIKE ? OR ? = '%')
              AND (instructor LIKE ? OR ? = '%')
        """
        cursor.execute(
            query,
            (
                group_p,
                group_p,
                region_p,
                region_p,
                course_p,
                course_p,
                instructor_p,
                instructor_p,
            ),
        )
        all_rows = cursor.fetchall()
        conn.close()

        self.manage_table.setSortingEnabled(False)
        self.manage_table.setRowCount(0)
        for row_idx, row_data in enumerate(all_rows):
            self.manage_table.insertRow(row_idx)
            self.manage_table.setRowHeight(row_idx, 35)
            c_id, g, r, c, d, p, th, loc, inst = row_data
            disp_vals = [c_id, g, r, c, d, p, f"{th:.0f}시간", loc, inst]
            for col_idx, value in enumerate(disp_vals):
                item = QTableWidgetItem(str(value if value is not None else ""))
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.manage_table.setItem(row_idx, col_idx, item)

        self.manage_table.setSortingEnabled(True)

    def load_instructor_details(self):
        selected_inst = self.combo_instructor_tab3.currentText()
        if (
            not selected_inst
            or selected_inst == "강사를 선택하세요"
            or selected_inst.startswith("전체")
        ):
            self.inst_table.setRowCount(0)
            self.lbl_inst_name.setText("강사명: -")
            self.lbl_inst_count.setText("배정 강의 수: -")
            self.lbl_inst_hours.setText("총 강의시간 합계: -")
            return

        conn = self.get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT id, degree, region, course_name, period, total_hours, location
            FROM courses
            WHERE instructor = ?
        """,
            (selected_inst,),
        )
        rows = cursor.fetchall()

        self.inst_table.setSortingEnabled(False)
        self.inst_table.setRowCount(0)
        total_sum_hours = 0.0

        for row_idx, row_data in enumerate(rows):
            self.inst_table.insertRow(row_idx)
            c_id, degree, region, course, period, hours, location = row_data
            hours_val = float(hours) if hours else 0.0
            total_sum_hours += hours_val

            time_str = self.get_formatted_sessions_text(c_id, conn)

            data_list = [
                degree,
                region,
                course,
                period,
                time_str,
                f"{hours_val:.0f}시간",
                location,
            ]

            line_count = time_str.count("\n") + 1
            self.inst_table.setRowHeight(
                row_idx, max(50, line_count * 20 + 15)
            )

            for col_idx, value in enumerate(data_list):
                item = QTableWidgetItem(str(value if value is not None else ""))
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                if col_idx == 5:
                    item.setFont(QFont("맑은 고딕", 12, QFont.Weight.Bold))
                self.inst_table.setItem(row_idx, col_idx, item)

        self.inst_table.setSortingEnabled(True)
        conn.close()

        self.lbl_inst_name.setText(f"강사명: {selected_inst}")
        self.lbl_inst_count.setText(f"배정 강의 수: {len(rows)}건")
        self.lbl_inst_hours.setText(
            f"총 강의시간 합계: {total_sum_hours:.0f}시간"
        )

    def update_calendar_events(self):
        group_sel = self.cal_combo_group.currentText()
        region_sel = self.cal_combo_region.currentText()
        course_sel = self.cal_combo_course.currentText()
        instructor_sel = self.cal_combo_instructor.currentText()

        group_p = (
            "%"
            if (group_sel.startswith("전체") or not group_sel)
            else group_sel
        )
        region_p = (
            "%"
            if (region_sel.startswith("전체") or not region_sel)
            else region_sel
        )
        course_p = (
            "%"
            if (course_sel.startswith("전체") or not course_sel)
            else course_sel
        )
        instructor_p = (
            "%"
            if (instructor_sel.startswith("전체") or not instructor_sel)
            else instructor_sel
        )

        conn = self.get_db_connection()
        cursor = conn.cursor()

        query = """
            SELECT cs.session_date
            FROM course_sessions cs
            JOIN courses c ON cs.course_id = c.id
            WHERE (c.group_name LIKE ? OR ? = '%')
              AND (c.region LIKE ? OR ? = '%')
              AND (c.course_name LIKE ? OR ? = '%')
              AND (c.instructor LIKE ? OR ? = '%')
        """
        cursor.execute(
            query,
            (
                group_p,
                group_p,
                region_p,
                region_p,
                course_p,
                course_p,
                instructor_p,
                instructor_p,
            ),
        )
        rows = cursor.fetchall()
        conn.close()

        date_counts = {}
        for row in rows:
            s_date = row[0]
            try:
                dt = datetime.strptime(s_date, "%Y-%m-%d")
                key = (dt.year, dt.month, dt.day)
                date_counts[key] = date_counts.get(key, 0) + 1
            except ValueError:
                continue

        self.calendar.set_date_counts(date_counts)
        self.on_calendar_date_clicked()

    def on_calendar_date_clicked(self):
        selected_qdate = self.calendar.selectedDate()
        y, m, d = (
            selected_qdate.year(),
            selected_qdate.month(),
            selected_qdate.day(),
        )
        target_date_str = f"{y:04d}-{m:02d}-{d:02d}"

        key = (y, m, d)
        count = self.calendar.date_counts.get(key, 0)

        self.lbl_cal_selected_date.setText(
            f"선택한 날짜: {selected_qdate.toString('yyyy년 M월 d일 (ddd)')}  |  개설된 강좌 수: {count}개"
        )

        group_sel = self.cal_combo_group.currentText()
        region_sel = self.cal_combo_region.currentText()
        course_sel = self.cal_combo_course.currentText()
        instructor_sel = self.cal_combo_instructor.currentText()

        group_p = (
            "%"
            if (group_sel.startswith("전체") or not group_sel)
            else group_sel
        )
        region_p = (
            "%"
            if (region_sel.startswith("전체") or not region_sel)
            else region_sel
        )
        course_p = (
            "%"
            if (course_sel.startswith("전체") or not course_sel)
            else course_sel
        )
        instructor_p = (
            "%"
            if (instructor_sel.startswith("전체") or not instructor_sel)
            else instructor_sel
        )

        conn = self.get_db_connection()
        cursor = conn.cursor()

        query = """
            SELECT c.degree, c.course_name, c.region, c.instructor, cs.start_time, cs.end_time, c.period, c.total_hours, c.location
            FROM course_sessions cs
            JOIN courses c ON cs.course_id = c.id
            WHERE cs.session_date = ?
              AND (c.group_name LIKE ? OR ? = '%')
              AND (c.region LIKE ? OR ? = '%')
              AND (c.course_name LIKE ? OR ? = '%')
              AND (c.instructor LIKE ? OR ? = '%')
        """
        cursor.execute(
            query,
            (
                target_date_str,
                group_p,
                group_p,
                region_p,
                region_p,
                course_p,
                course_p,
                instructor_p,
                instructor_p,
            ),
        )
        rows = cursor.fetchall()
        conn.close()

        self.cal_table.setSortingEnabled(False)
        self.cal_table.setRowCount(0)

        weekday_kr = ["월", "화", "수", "목", "금", "토", "일"]
        dt = datetime(y, m, d)
        w_str = weekday_kr[dt.weekday()]

        for row_idx, row_data in enumerate(rows):
            (
                degree,
                course,
                region,
                instructor,
                start_t,
                end_t,
                period,
                hours,
                location,
            ) = row_data
            self.cal_table.insertRow(row_idx)
            self.cal_table.setRowHeight(row_idx, 38)

            disp_time = f"{m}.{d}({w_str}) {start_t}~{end_t}"

            data_list = [
                degree,
                course,
                region,
                instructor,
                disp_time,
                period,
                f"{hours:.0f}시간",
                location,
            ]

            for col_idx, value in enumerate(data_list):
                item = QTableWidgetItem(str(value if value is not None else ""))
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                if col_idx == 4:
                    item.setFont(
                        QFont("맑은 고딕", 11, QFont.Weight.Bold)
                    )
                self.cal_table.setItem(row_idx, col_idx, item)

        self.cal_table.setSortingEnabled(True)

    # --- 탭 2: 강좌 및 일자별 세부 시간 DB 수정 관리 메서드 ---

    def on_manage_table_click(self, row, col):
        course_id = self.manage_table.item(row, 0).text()
        self.edit_id.setText(course_id)
        self.edit_group.setText(self.manage_table.item(row, 1).text())
        self.edit_region.setText(self.manage_table.item(row, 2).text())
        self.edit_course.setText(self.manage_table.item(row, 3).text())

        degree_val = self.manage_table.item(row, 4).text()
        idx = self.edit_degree.findText(degree_val)
        if idx >= 0:
            self.edit_degree.setCurrentIndex(idx)
        else:
            self.edit_degree.setCurrentText(degree_val)

        self.edit_period.setText(self.manage_table.item(row, 5).text())
        self.edit_hours.setText(self.manage_table.item(row, 6).text())
        self.edit_location.setText(self.manage_table.item(row, 7).text())
        self.edit_instructor.setText(self.manage_table.item(row, 8).text())

        self.load_session_list(course_id)

    def load_session_list(self, course_id):
        self.session_list_widget.clear()
        conn = self.get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, session_date, start_time, end_time, hours FROM course_sessions WHERE course_id = ? ORDER BY session_date",
            (course_id,),
        )
        sessions = cursor.fetchall()
        conn.close()

        weekday_kr = ["월", "화", "수", "목", "금", "토", "일"]

        for s_id, s_date, s_time, e_time, h in sessions:
            try:
                dt = datetime.strptime(s_date, "%Y-%m-%d")
                w_str = weekday_kr[dt.weekday()]
                disp_date = f"{s_date}({w_str})"
            except ValueError:
                disp_date = s_date

            item = QListWidgetItem(
                f"{disp_date}    {s_time} ~ {e_time}    ({h:.1f}시간)"
            )

            item.setData(Qt.ItemDataRole.UserRole, s_id)
            item.setData(Qt.ItemDataRole.UserRole + 1, s_date)
            item.setData(Qt.ItemDataRole.UserRole + 2, s_time)
            item.setData(Qt.ItemDataRole.UserRole + 3, e_time)
            self.session_list_widget.addItem(item)

    def on_session_item_clicked(self, item):
        s_date_str = item.data(Qt.ItemDataRole.UserRole + 1)
        s_time_str = item.data(Qt.ItemDataRole.UserRole + 2)
        e_time_str = item.data(Qt.ItemDataRole.UserRole + 3)

        if s_date_str:
            q_date = QDate.fromString(s_date_str, "yyyy-MM-dd")
            self.edit_session_date.setDate(q_date)

        if s_time_str:
            q_time_start = QTime.fromString(s_time_str, "HH:mm")
            self.edit_start_time.setTime(q_time_start)

        if e_time_str:
            q_time_end = QTime.fromString(e_time_str, "HH:mm")
            self.edit_end_time.setTime(q_time_end)

    def add_session_record(self):
        course_id = self.edit_id.text()
        if not course_id:
            QMessageBox.warning(
                self, "경고", "오른쪽 목록에서 먼저 강좌를 선택해 주세요."
            )
            return

        q_date = self.edit_session_date.date()
        date_str = q_date.toString("yyyy-MM-dd")

        s_time = self.edit_start_time.time().toString("HH:mm")
        e_time = self.edit_end_time.time().toString("HH:mm")

        hours = calculate_session_hours(s_time, e_time)

        conn = self.get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT id FROM course_sessions WHERE course_id = ? AND session_date = ?",
            (course_id, date_str),
        )
        exists = cursor.fetchone()

        if exists:
            cursor.execute(
                "UPDATE course_sessions SET start_time = ?, end_time = ?, hours = ? WHERE id = ?",
                (s_time, e_time, hours, exists[0]),
            )
            log_audit_event(
                "세부일정수정",
                course_id,
                f"날짜: {date_str}, 시간: {s_time}~{e_time} ({hours}시간)",
            )
        else:
            cursor.execute(
                "INSERT INTO course_sessions (course_id, session_date, start_time, end_time, hours) VALUES (?, ?, ?, ?, ?)",
                (course_id, date_str, s_time, e_time, hours),
            )
            log_audit_event(
                "세부일정추가",
                course_id,
                f"날짜: {date_str}, 시간: {s_time}~{e_time} ({hours}시간)",
            )

        conn.commit()
        conn.close()

        self.recalculate_course_total_hours(course_id)
        self.load_session_list(course_id)
        self.reload_all_system_views()

    def update_session_record(self):
        course_id = self.edit_id.text()
        current_item = self.session_list_widget.currentItem()
        if not current_item:
            QMessageBox.warning(
                self, "경고", "수정할 세부일정을 리스트에서 먼저 선택해 주세요."
            )
            return

        session_id = current_item.data(Qt.ItemDataRole.UserRole)

        q_date = self.edit_session_date.date()
        date_str = q_date.toString("yyyy-MM-dd")

        s_time = self.edit_start_time.time().toString("HH:mm")
        e_time = self.edit_end_time.time().toString("HH:mm")

        reply = QMessageBox.question(
            self,
            "수정 확인",
            f"선택한 일자의 강의 정보를 아래 내용으로 수정하시겠습니까?\n\n- 일자: {date_str}\n- 시간: {s_time} ~ {e_time}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        hours = calculate_session_hours(s_time, e_time)

        conn = self.get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE course_sessions SET session_date = ?, start_time = ?, end_time = ?, hours = ? WHERE id = ?",
            (date_str, s_time, e_time, hours, session_id),
        )
        conn.commit()
        conn.close()

        log_audit_event(
            "세부일정수정",
            course_id,
            f"세션ID: {session_id}, 날짜: {date_str}, 시간: {s_time}~{e_time} ({hours}시간)",
        )

        self.recalculate_course_total_hours(course_id)
        self.load_session_list(course_id)
        self.reload_all_system_views()
        QMessageBox.information(
            self, "성공", "선택한 일자의 강의 시간이 수정되었습니다!"
        )

    def delete_session_record(self):
        course_id = self.edit_id.text()
        current_item = self.session_list_widget.currentItem()
        if not current_item:
            QMessageBox.warning(
                self, "경고", "삭제할 세부일정을 리스트에서 선택해 주세요."
            )
            return

        session_id = current_item.data(Qt.ItemDataRole.UserRole)
        s_date_str = current_item.data(Qt.ItemDataRole.UserRole + 1)

        reply = QMessageBox.question(
            self,
            "삭제 확인",
            f"선택한 일자 [{s_date_str}] 수업을 완전히 삭제하시겠습니까?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        conn = self.get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM course_sessions WHERE id = ?", (session_id,)
        )
        conn.commit()
        conn.close()

        log_audit_event(
            "세부일정삭제",
            course_id,
            f"세션ID: {session_id}, 삭제일자: {s_date_str}",
        )

        self.recalculate_course_total_hours(course_id)
        self.load_session_list(course_id)
        self.reload_all_system_views()

    def recalculate_course_total_hours(self, course_id):
        conn = self.get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT SUM(hours) FROM course_sessions WHERE course_id = ?",
            (course_id,),
        )
        total_h = cursor.fetchone()[0]
        total_h = total_h if total_h else 0.0

        cursor.execute(
            "UPDATE courses SET total_hours = ? WHERE id = ?",
            (total_h, course_id),
        )
        conn.commit()
        conn.close()

        self.edit_hours.setText(f"{total_h:.0f}시간")

    def reload_all_system_views(self):
        self.refresh_combo_options()
        self.load_tab1_data()
        self.load_manage_table_data()
        self.load_instructor_details()
        self.update_calendar_events()
        self.load_audit_logs()

    def clear_manage_form(self):
        self.edit_id.clear()
        self.edit_group.clear()
        self.edit_region.clear()
        self.edit_course.clear()
        self.edit_degree.setCurrentIndex(0)
        self.edit_period.clear()
        self.edit_hours.clear()
        self.edit_location.clear()
        self.edit_instructor.clear()
        self.session_list_widget.clear()

    def undo_changes(self):
        course_id = self.edit_id.text()
        if not course_id:
            self.reload_all_system_views()
            QMessageBox.information(
                self, "복원 완료", "화면이 이전 상태로 초기화되었습니다."
            )
            return

        conn = self.get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT group_name, region, course_name, degree, period, location, instructor, total_hours FROM courses WHERE id=?",
            (course_id,),
        )
        c_row = cursor.fetchone()
        conn.close()

        if c_row:
            self.edit_group.setText(c_row[0])
            self.edit_region.setText(c_row[1])
            self.edit_course.setText(c_row[2])
            idx = self.edit_degree.findText(c_row[3])
            if idx >= 0:
                self.edit_degree.setCurrentIndex(idx)
            self.edit_period.setText(c_row[4])
            self.edit_location.setText(c_row[5])
            self.edit_instructor.setText(c_row[6])
            self.edit_hours.setText(f"{c_row[7]:.0f}시간")
            self.load_session_list(course_id)

        self.reload_all_system_views()
        QMessageBox.information(
            self,
            "취소 및 복원 완료",
            "최근 저장 상태로 이전 데이터가 복원되었습니다.",
        )

    def add_course_record(self):
        conn = self.get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO courses (group_name, region, course_name, degree, period, total_hours, location, instructor)
            VALUES (?, ?, ?, ?, ?, 0.0, ?, ?)
        """,
            (
                self.edit_group.text(),
                self.edit_region.text(),
                self.edit_course.text(),
                self.edit_degree.currentText(),
                self.edit_period.text(),
                self.edit_location.text(),
                self.edit_instructor.text(),
            ),
        )
        conn.commit()
        new_id = cursor.lastrowid
        conn.close()

        log_audit_event(
            "신규강좌추가",
            new_id,
            f"과목: {self.edit_course.text()}, 강사: {self.edit_instructor.text()}",
        )

        QMessageBox.information(
            self,
            "성공",
            f"신규 강좌(ID: {new_id})가 등록되었습니다.\n아래에서 강의 날짜와 시간을 추가해 주세요.",
        )
        self.edit_id.setText(str(new_id))
        self.reload_all_system_views()

    def update_course_record(self):
        course_id = self.edit_id.text()
        if not course_id:
            QMessageBox.warning(
                self, "경고", "수정할 강좌를 오른쪽 목록에서 선택해 주세요."
            )
            return

        reply = QMessageBox.question(
            self,
            "수정 확인",
            f"강좌 ID [{course_id}]의 정보를 변경 내용으로 수정하시겠습니까?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        conn = self.get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE courses
            SET group_name=?, region=?, course_name=?, degree=?, period=?, location=?, instructor=?
            WHERE id=?
        """,
            (
                self.edit_group.text(),
                self.edit_region.text(),
                self.edit_course.text(),
                self.edit_degree.currentText(),
                self.edit_period.text(),
                self.edit_location.text(),
                self.edit_instructor.text(),
                course_id,
            ),
        )
        conn.commit()
        conn.close()

        log_audit_event(
            "강좌정보수정",
            course_id,
            f"과목: {self.edit_course.text()}, 강사: {self.edit_instructor.text()}, 장소: {self.edit_location.text()}",
        )

        self.recalculate_course_total_hours(course_id)
        self.reload_all_system_views()
        QMessageBox.information(
            self,
            "성공",
            "강좌 정보가 최종 수정되어 전체 시스템에 반영되었습니다!",
        )

    def delete_course_record(self):
        current_row = self.manage_table.currentRow()
        if current_row < 0:
            QMessageBox.warning(
                self, "경고", "삭제할 강좌를 목록에서 선택해 주세요."
            )
            return

        course_id = self.manage_table.item(current_row, 0).text()
        reply = QMessageBox.question(
            self,
            "삭제 확인",
            f"ID [{course_id}] 강좌와 관련 일자별 세부일정을 완전히 삭제하시겠습니까?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM courses WHERE id=?", (course_id,))
            cursor.execute(
                "DELETE FROM course_sessions WHERE course_id=?", (course_id,)
            )
            conn.commit()
            conn.close()

            log_audit_event("강좌삭제", course_id, f"강좌ID {course_id} 완전 삭제")

            QMessageBox.information(self, "성공", "삭제되었습니다.")
            self.clear_manage_form()
            self.reload_all_system_views()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = LocalScheduleApp()
    window.show()
    sys.exit(app.exec())
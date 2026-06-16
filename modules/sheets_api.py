from datetime import date

import gspread
import streamlit as st
from google.oauth2.service_account import Credentials

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
]

HEADERS = [
    "분석일", "회사명", "포지션", "매칭 스코어",
    "마감일", "강점", "총평", "JD URL", "지원 여부",
]


def _sheet():
    creds = Credentials.from_service_account_info(
        dict(st.secrets["gcp_service_account"]), scopes=SCOPES
    )
    client = gspread.authorize(creds)
    spreadsheet = client.open_by_key(st.secrets["SPREADSHEET_ID"])
    try:
        ws = spreadsheet.worksheet("공고목록")
    except gspread.WorksheetNotFound:
        ws = spreadsheet.add_worksheet(title="공고목록", rows=500, cols=len(HEADERS))
        ws.append_row(HEADERS)
    return ws


def save_result(result: dict, jd_url: str = "") -> None:
    ws = _sheet()
    preferred = result.get("preferred_matches", [])
    strengths_text = "\n".join(p.get("requirement", "") for p in preferred)
    row = [
        date.today().isoformat(),
        result.get("company", "미확인"),
        result.get("position", ""),
        result.get("score", 0),
        result.get("deadline") or "",
        strengths_text,
        result.get("summary", ""),
        jd_url,
        "N",
    ]
    ws.append_row(row, value_input_option="USER_ENTERED")


def delete_job(row: int) -> None:
    ws = _sheet()
    ws.delete_rows(row)


def update_applied(row: int, applied: bool) -> None:
    ws = _sheet()
    col = HEADERS.index("지원 여부") + 1
    ws.update_cell(row, col, "Y" if applied else "N")


def fetch_jobs() -> list[dict]:
    ws = _sheet()
    all_values = ws.get_all_values()
    if not all_values:
        return []

    # 첫 행이 헤더인지 확인 (없으면 데이터가 1행부터 시작)
    has_header = all_values[0][0] == "분석일"
    data_rows = all_values[1:] if has_header else all_values
    sheet_start = 2 if has_header else 1

    def val(row_vals, idx, default=""):
        return row_vals[idx] if idx < len(row_vals) else default

    jobs = []
    for i, row_vals in enumerate(data_rows, start=sheet_start):
        jobs.append({
            "row": i,
            "company": val(row_vals, 1),
            "position": val(row_vals, 2),
            "score": int(float(val(row_vals, 3) or 0)),
            "deadline": val(row_vals, 4) or None,
            "applied": str(val(row_vals, 8)).upper() == "Y",
            "summary": val(row_vals, 6),
            "url": val(row_vals, 7),
        })
    return jobs

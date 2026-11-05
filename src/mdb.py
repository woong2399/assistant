"""MotherDuck(DB: assistant) 읽기·쓰기. 토큰은 환경변수/.env/Streamlit secrets 의 MOTHERDUCK_TOKEN 에서만 읽는다."""
import json
import os
from pathlib import Path

import duckdb

DB = "assistant"
ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


def token():
    t = os.environ.get("MOTHERDUCK_TOKEN")
    if t:
        return t
    try:  # Streamlit 클라우드 secrets
        import streamlit as st
        if "MOTHERDUCK_TOKEN" in st.secrets:
            return st.secrets["MOTHERDUCK_TOKEN"]
    except Exception:
        pass
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            if line.startswith("MOTHERDUCK_TOKEN="):
                return line.split("=", 1)[1].strip().strip('"')
    return None


def available():
    return token() is not None


def connect():
    t = token()
    if not t:
        raise RuntimeError("MOTHERDUCK_TOKEN 이 없습니다")
    return duckdb.connect(f"md:{DB}?motherduck_token={t}")


def push_report(doc):
    """날짜별 보고서 한 건을 통째로 저장(같은 날짜는 교체)."""
    con = connect()
    con.execute("CREATE TABLE IF NOT EXISTS report_doc (report_date DATE, doc VARCHAR)")
    con.execute("DELETE FROM report_doc WHERE report_date = ?", [doc["report_date"]])
    con.execute("INSERT INTO report_doc VALUES (?, ?)", [doc["report_date"], json.dumps(doc, ensure_ascii=False)])
    con.close()


def list_dates():
    con = connect()
    rows = con.execute("SELECT strftime(report_date, '%Y-%m-%d') FROM report_doc ORDER BY 1 DESC LIMIT 60").fetchall()
    con.close()
    return [r[0] for r in rows]


def load(date_str):
    con = connect()
    r = con.execute("SELECT doc FROM report_doc WHERE report_date = ?", [date_str]).fetchone()
    con.close()
    return json.loads(r[0])


def daily_dates():
    con = connect()
    rows = con.execute("SELECT DISTINCT strftime(pick_date, '%Y-%m-%d') FROM daily_pick ORDER BY 1 DESC").fetchall()
    con.close()
    return [r[0] for r in rows]


def daily_rows(date_str):
    con = connect()
    rows = con.execute(
        "SELECT code, name, pct, theme, telegram FROM daily_pick WHERE pick_date = ? ORDER BY pct DESC NULLS LAST, name",
        [date_str],
    ).fetchall()
    con.close()
    return [dict(code=r[0], name=r[1], pct=r[2], theme=r[3], telegram=r[4]) for r in rows]

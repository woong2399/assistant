"""daily_data\\data\\날짜.json (급등주 일지)을 MotherDuck assistant.daily_pick 에 올린다.

py src/load_daily.py              전체 날짜
py src/load_daily.py --since 2026-11-05
날짜별로 지우고 다시 넣는다(같은 날짜 덮어쓰기). 읽기만 하는 곳: daily_data\\data. 토큰은 .env 의 MOTHERDUCK_TOKEN.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import mdb  # noqa: E402

SRC = Path(r"C:\Users\Jinwo\Documents\daily_data\data")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", default="0000-00-00")
    a = ap.parse_args()
    files = sorted(p for p in SRC.glob("????-??-??.json") if p.stem >= a.since)
    if not files:
        print("올릴 파일이 없습니다")
        return
    con = mdb.connect()
    con.execute(
        "CREATE TABLE IF NOT EXISTS daily_pick (pick_date DATE, code VARCHAR, name VARCHAR, pct DOUBLE, "
        "amount_est DOUBLE, source VARCHAR, theme VARCHAR, issue VARCHAR, news VARCHAR)"
    )
    # 옛 표(시트에서 손으로 올린 것)에는 새 열이 없으므로 없으면 추가
    cols = {r[0] for r in con.execute("SELECT column_name FROM information_schema.columns WHERE table_name='daily_pick'").fetchall()}
    for name, typ in [("amount_est", "DOUBLE"), ("source", "VARCHAR"), ("issue", "VARCHAR"), ("news", "VARCHAR")]:
        if name not in cols:
            con.execute(f"ALTER TABLE daily_pick ADD COLUMN {name} {typ}")
    total = 0
    for p in files:
        d = json.loads(p.read_text(encoding="utf-8"))
        con.execute("DELETE FROM daily_pick WHERE pick_date = ?", [d["date"]])
        rows = [
            (d["date"], s["code"], s["name"], s.get("pct"), s.get("amount_est"), s.get("source"),
             ", ".join(s.get("theme") or []) or None, s.get("issue") or None,
             json.dumps(s.get("news") or [], ensure_ascii=False))
            for s in d["stocks"]
        ]
        con.executemany(
            "INSERT INTO daily_pick (pick_date, code, name, pct, amount_est, source, theme, issue, news) VALUES (?,?,?,?,?,?,?,?,?)",
            rows,
        )
        total += len(rows)
        print(d["date"], len(rows))
    con.close()
    print("합계", total)


if __name__ == "__main__":
    main()

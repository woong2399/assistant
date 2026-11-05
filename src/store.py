"""보고서를 날짜별 JSON 파일로 저장한다: data/reports/YYYY-MM-DD.json
같은 날짜는 덮어쓴다(임시 파일에 쓴 뒤 바꿔 치기해서 반쯤 쓰인 파일이 남지 않게 함)."""
import datetime as dt
import json
import os
from pathlib import Path

REPORT_DIR = Path(__file__).resolve().parent.parent / "data" / "reports"


def save(report_date, market, failed, extra=None):
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    ok = sum(1 for r in market if r["value"] is not None)
    doc = {
        "report_date": report_date.isoformat(),
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "ok_count": ok,
        "fail_count": len(market) - ok,
        "failures": failed,
        "market": [{**r, "as_of": r["as_of"].isoformat() if r["as_of"] else None} for r in market],
        # 아래 항목은 아직 채우는 코드가 없다(준비 중)
        "disclosures": [],
        "events": [],
        "themes": [],
    }
    if extra:
        doc.update(extra)
    path = REPORT_DIR / f"{report_date.isoformat()}.json"
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, path)
    try:  # MotherDuck 에도 올린다. 실패해도 로컬 파일은 남는다.
        import mdb
        if mdb.available():
            mdb.push_report(doc)
    except Exception as e:  # noqa: BLE001
        print(f"MotherDuck 업로드 실패: {e}")
    return path


def list_dates():
    return sorted((p.stem for p in REPORT_DIR.glob("????-??-??.json")), reverse=True)


def load(date_str):
    return json.loads((REPORT_DIR / f"{date_str}.json").read_text(encoding="utf-8"))

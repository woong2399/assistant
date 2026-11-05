"""장전 보고서 만들기. 사용: python src/run_report.py [--dry-run]"""
import datetime as dt
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).parent))

import config  # noqa: E402
import dart  # noqa: E402
import schedule  # noqa: E402
import sources  # noqa: E402
import store  # noqa: E402

def collect_market():
    rows, failed = [], []
    for grp, no, sym, label, fb in config.MARKET:
        try:
            val, chg, as_of, src = sources.fetch(sym, fb)
            note = "선물 근월물·진행 중 값 포함 가능" if grp in config.LIVE_GROUPS else ""
            rows.append(dict(grp=grp, sort_no=no, symbol=sym, label=label,
                             value=val, change_pct=chg, as_of=as_of, source=src, note=note))
        except Exception as e:  # noqa: BLE001 - 한 칸이 실패해도 나머지는 계속
            failed.append(f"{label}({sym}): {e}")
            rows.append(dict(grp=grp, sort_no=no, symbol=sym, label=label,
                             value=None, change_pct=None, as_of=None,
                             source="", note=f"자료 없음: {str(e)[:150]}"))
    return rows, failed


def main():
    dry = "--dry-run" in sys.argv
    report_date = dt.date.today()
    rows, failed = collect_market()
    ok = sum(1 for r in rows if r["value"] is not None)
    print(f"보고서 날짜 {report_date}  성공 {ok} / 실패 {len(failed)}")
    for r in rows:
        v = "자료 없음" if r["value"] is None else f"{r['value']:,.2f} ({r['change_pct']:+.2f}%) {r['as_of']} [{r['source']}]"
        print(f"  {r['grp']:<8} {r['label']:<14} {v}")
    for f in failed:
        print("  실패:", f)
    if dry:
        print("(--dry-run: 파일에 저장하지 않음)")
        return
    events = schedule.all_events(report_date, report_date + dt.timedelta(days=7))
    try:
        discl = dart.collect(report_date)
        print(f"  공시 키워드 해당 {len(discl)}건")
    except Exception as e:  # noqa: BLE001 - 공시가 실패해도 보고서는 만든다
        discl = []
        failed.append(f"전자공시: {e}")
        print("  공시 실패:", e)
    path = store.save(report_date, rows, failed, {"events": events, "disclosures": discl})
    print("저장함:", path)


if __name__ == "__main__":
    main()

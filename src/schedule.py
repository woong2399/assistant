"""예정 행사. 고정 일정표(공식 사이트에서 확인한 날짜, 연 1~2회 갱신)와 규칙으로 계산하는 날짜.
출처·기준일은 볼트 Projects/Assistant/docs/일정표-2026.md (2026-11-05 수집)."""
import datetime as dt
from zoneinfo import ZoneInfo

NY, KST = ZoneInfo("America/New_York"), ZoneInfo("Asia/Seoul")

# 미국 발표: (현지 날짜, 현지 시각). 시각은 미국 동부시간.
FOMC_DECISION = ["2026-12-09"]  # 결정 발표일(2일차) 14:00 ET. 2027 일정은 연준 발표 후 추가(미확인)
CPI = ["2026-11-10", "2026-12-10", "2027-01-13", "2027-02-11", "2027-03-10"]  # 08:30 ET
JOBS = ["2026-11-06", "2026-12-04", "2027-01-08", "2027-02-05", "2027-03-05"]  # 08:30 ET
BOK = ["2026-11-26"]  # 한국은행 금통위 (한국 날짜)
US_HOLIDAY = {  # 미국 증시 휴장 (NYSE)
    "2026-11-26": "추수감사절", "2026-12-25": "성탄절",
    "2027-01-01": "새해", "2027-01-18": "킹 목사 기념일", "2027-02-15": "대통령의 날",
    "2027-03-26": "성금요일",
}


def _us(day, hh, mm):
    d = dt.date.fromisoformat(day)
    local = dt.datetime(d.year, d.month, d.day, hh, mm, tzinfo=NY)
    return local.astimezone(KST)


def _nth_weekday(year, month, weekday, n):
    d = dt.date(year, month, 1)
    d += dt.timedelta(days=(weekday - d.weekday()) % 7)
    return d + dt.timedelta(weeks=n - 1)


def all_events(start, end):
    """start~end(한국 날짜, 양 끝 포함) 사이 행사 목록. 날짜 순."""
    ev = []

    def add(kst_day, time_s, category, title, detail=""):
        if start <= kst_day <= end:
            ev.append({"date": kst_day.isoformat(), "time": time_s, "category": category,
                       "title": title, "detail": detail})

    for ds, hh, mm, cat, name in (
        [(d, 14, 0, "미국 통화", "FOMC 금리 결정 발표") for d in FOMC_DECISION]
        + [(d, 8, 30, "미국 지표", "미국 소비자물가(CPI) 발표") for d in CPI]
        + [(d, 8, 30, "미국 지표", "미국 고용지표 발표") for d in JOBS]
    ):
        k = _us(ds, hh, mm)
        add(k.date(), k.strftime("%H:%M"), cat, name, f"미국 현지 {ds[5:].replace('-', '/')} {hh:02d}:{mm:02d} (동부)")
    for ds in BOK:
        add(dt.date.fromisoformat(ds), "", "한국 통화", "한국은행 금통위 기준금리 결정")
    for ds, why in US_HOLIDAY.items():
        add(dt.date.fromisoformat(ds), "", "휴장", f"미국 증시 휴장 ({why})", "한국 시각 다음 날 아침 미국 지수 변동 없음")

    # 규칙으로 계산: 달마다 (범위를 한 달 넉넉히)
    y, m = start.year, start.month
    for _ in range(3):
        quad = m in (3, 6, 9, 12)
        kr = _nth_weekday(y, m, 3, 2)  # 둘째 목요일
        add(kr, "", "한국 만기", "네 마녀의 날 (지수·개별주식 선물·옵션 동시 만기)" if quad else "코스피200 옵션 만기",
            "휴장일과 겹치면 앞당겨짐(미반영)")
        us = _nth_weekday(y, m, 4, 3)  # 셋째 금요일
        add(us, "", "미국 만기", "미국 마녀의 날 (선물·옵션 동시 만기)" if quad else "미국 옵션 만기",
            "한국 시각 토요일 새벽 미국장 마감")
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)

    return sorted(ev, key=lambda e: (e["date"], e["time"] or "99:99", e["category"]))

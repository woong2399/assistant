"""DART 공시에서 키워드(dart_keywords.txt)에 걸린 것만 뽑는다.
이 파일은 독립적이라 나중에 News 프로젝트로 옮겨도 된다. 키: DART_API_KEY (assistant\.env, 없으면 ..\news\.env)"""
import datetime as dt
import json
import os
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MARKET = {"Y": "코스피", "K": "코스닥"}  # 코넥스·비상장은 뺀다
CAT_ORDER = ["계약", "주주환원", "리스크"]


def _key():
    if os.environ.get("DART_API_KEY"):
        return os.environ["DART_API_KEY"]
    for p in (ROOT / ".env", ROOT.parent / "news" / ".env"):
        if p.exists():
            for line in p.read_text(encoding="utf-8").splitlines():
                if line.startswith("DART_API_KEY="):
                    return line.split("=", 1)[1].strip()
    raise RuntimeError("DART_API_KEY 가 .env 에 없다")


def load_keywords(path=ROOT / "dart_keywords.txt"):
    kws = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and line.count("|") == 2:
            cat, kw, tone = (x.strip() for x in line.split("|"))
            kws.append((cat, kw, tone))  # cat 이 "제외" 이면 kw=분류, tone=뺄 말
    return kws


def _day_rows(key, day):
    rows, pg = [], 1
    while True:
        q = dict(crtfc_key=key, bgn_de=day, end_de=day, page_no=pg, page_count=100)
        d = json.loads(urllib.request.urlopen(
            "https://opendart.fss.or.kr/api/list.json?" + urllib.parse.urlencode(q), timeout=30).read())
        if d.get("status") == "013":  # 조회된 데이터가 없다
            break
        if d.get("status") != "000":
            raise RuntimeError(f"DART {d.get('status')} {d.get('message')}")
        rows += d["list"]
        if pg >= int(d.get("total_page") or 1):
            break
        pg += 1
        time.sleep(0.2)
    return rows


def prev_business_day(d):
    d -= dt.timedelta(days=1)
    while d.weekday() >= 5:
        d -= dt.timedelta(days=1)
    return d


def collect(report_date):
    """report_date 직전 영업일 ~ report_date 공시 중 키워드에 걸린 것. 정정 공시는 원본과 합친다."""
    key, kws = _key(), load_keywords()
    start = prev_business_day(report_date)
    days = [start + dt.timedelta(days=i) for i in range((report_date - start).days + 1)]
    out, seen = [], set()
    for day in days:
        for r in _day_rows(key, day.strftime("%Y%m%d")):
            if r["corp_cls"] not in MARKET:
                continue
            title = re.sub(r"\s+", " ", r["report_nm"]).strip()
            clean = re.sub(r"^\[[^\]]*정정\]\s*", "", title)
            ex = [(k, t) for c, k, t in kws if c == "제외"]
            hit = next(((c, t) for c, k, t in kws
                        if c != "제외" and k in clean
                        and not any(ec == c and et in clean for ec, et in ex)), None)
            if not hit:
                continue
            ident = (r["corp_code"], clean)
            if ident in seen:  # 같은 건의 정정 공시
                continue
            seen.add(ident)
            if hit[0] == "주주환원" and "해지" in clean:  # 신탁계약 해지 등은 호재가 아니다
                hit = (hit[0], "중립")
            out.append({
                "category": hit[0], "tone": hit[1], "corp": r["corp_name"], "code": r["stock_code"],
                "market": MARKET[r["corp_cls"]], "title": clean, "date": r["rcept_dt"],
                "url": "https://dart.fss.or.kr/dsaf001/main.do?rcpNo=" + r["rcept_no"],
            })
    out.sort(key=lambda x: (CAT_ORDER.index(x["category"]) if x["category"] in CAT_ORDER else 9, x["corp"]))
    return out

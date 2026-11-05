"""시세 가져오기. 야후 기본, 실패하면 예비(FRED, frankfurter). 모두 실패하면 예외."""
import csv
import datetime as dt
import io
import json
import urllib.parse
import urllib.request

UA = {"User-Agent": "Mozilla/5.0 (personal stock assistant)"}


def _get(url, timeout=20):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")


def yahoo(symbol):
    """(마지막 종가, 전일 대비 %, 기준 날짜)"""
    url = ("https://query1.finance.yahoo.com/v8/finance/chart/"
           + urllib.parse.quote(symbol) + "?range=10d&interval=1d")
    d = json.loads(_get(url))
    res = d["chart"]["result"][0]
    off = res["meta"].get("gmtoffset", 0)
    rows = [
        (dt.datetime.fromtimestamp(t + off, dt.timezone.utc).date(), c)
        for t, c in zip(res["timestamp"], res["indicators"]["quote"][0]["close"])
        if c is not None
    ]
    if len(rows) < 2:
        raise ValueError("야후 값이 2개 미만")
    (d0, v0), (d1, v1) = rows[-2], rows[-1]
    return v1, (v1 / v0 - 1) * 100, d1


def fred(series):
    text = _get(f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series}")
    rows = [r for r in csv.reader(io.StringIO(text))][1:]
    rows = [(r[0], float(r[1])) for r in rows if len(r) == 2 and r[1] not in ("", ".")]
    if len(rows) < 2:
        raise ValueError("FRED 값이 2개 미만")
    (d0, v0), (d1, v1) = rows[-2], rows[-1]
    return v1, (v1 / v0 - 1) * 100, dt.date.fromisoformat(d1)


def frankfurter(cur):
    d1 = json.loads(_get(f"https://api.frankfurter.app/latest?from=USD&to={cur}"))
    day = d1["date"]
    prev = (dt.date.fromisoformat(day) - dt.timedelta(days=4)).isoformat()
    h = json.loads(_get(f"https://api.frankfurter.app/{prev}..{day}?from=USD&to={cur}"))
    days = sorted(h["rates"])
    if len(days) < 2:
        raise ValueError("frankfurter 값이 2개 미만")
    v0, v1 = h["rates"][days[-2]][cur], h["rates"][days[-1]][cur]
    return v1, (v1 / v0 - 1) * 100, dt.date.fromisoformat(days[-1])


def fetch(symbol, fallback):
    """(값, 등락%, 기준일, 출처) 를 돌려준다. 실패하면 마지막 오류를 올린다."""
    errors = []
    try:
        return (*yahoo(symbol), "Yahoo")
    except Exception as e:  # noqa: BLE001 - 어떤 실패든 예비로 넘어간다
        errors.append(f"Yahoo: {e}")
    if fallback:
        kind, key = fallback
        try:
            fn = fred if kind == "fred" else frankfurter
            return (*fn(key), "FRED" if kind == "fred" else "frankfurter")
        except Exception as e:  # noqa: BLE001
            errors.append(f"{kind}: {e}")
    raise RuntimeError(" / ".join(errors))

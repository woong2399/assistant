"""장전 보고서 화면 (Streamlit). 실행: run_app.bat"""
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent / "src"))
import store  # noqa: E402

UP, DOWN, MUTED = "#d6372b", "#1f6fd0", "#6a6a6a"  # 한국식: 상승 빨강, 하락 파랑

st.set_page_config(page_title="장전 보고서", layout="centered")
st.markdown(
    """<style>
    .block-container{padding:1rem 1rem 3rem;max-width:520px}
    .grid{display:grid;grid-template-columns:repeat(3,1fr);gap:6px;margin-bottom:6px}
    .card{background:#fff;border:1px solid #eee;border-radius:8px;padding:6px 8px}
    .lab{font-size:11px;color:#6a6a6a}.val{font-size:15px;font-weight:700;line-height:1.3}
    .chg{font-size:12px}.src{font-size:9px;color:#6a6a6a}
    h1{font-size:22px!important}.it{margin:8px 0 2px}.it b{font-size:14px}.it small{color:#6a6a6a;font-size:11px}.sub{margin:1px 0 0 14px;font-size:13px;line-height:1.5}.sub a{text-decoration:none}.sub .d{color:#6a6a6a;font-size:12px}.ev{margin:6px 0 0 4px;font-size:14px}h2{font-size:15px!important;margin-top:1rem!important}
    </style>""",
    unsafe_allow_html=True,
)


def card(r):
    if r["value"] is None:
        return f'<div class="card"><div class="lab">{r["label"]}</div><div class="chg" style="color:{MUTED}">자료 없음</div></div>'
    v = r["value"]
    val = f"{v:,.0f}" if v >= 1000 else f"{v:,.2f}"
    c = r["change_pct"]
    if c is None:
        chg = ""
    else:
        chg = f'<div class="chg" style="color:{UP if c >= 0 else DOWN}">{"▲" if c >= 0 else "▼"} {abs(c):.2f}%</div>'
    asof = (r["as_of"] or "")[5:].replace("-", "/")
    return (f'<div class="card"><div class="lab">{r["label"]}</div><div class="val">{val}</div>{chg}'
            f'<div class="src">{asof} · {r["source"]}</div></div>')


def grid(rows):
    st.markdown('<div class="grid">' + "".join(card(r) for r in rows) + "</div>", unsafe_allow_html=True)


import mdb  # noqa: E402

USE_MD = mdb.available()  # 토큰이 있으면 MotherDuck, 없으면 이 PC 의 JSON
src = mdb if USE_MD else store


@st.cache_data(ttl=300)
def _dates():
    return src.list_dates()


@st.cache_data(ttl=300)
def _doc(d):
    return src.load(d)


dates = _dates()
st.title("장전 보고서")
if not dates:
    st.info("아직 보고서가 없습니다. run_report.bat 을 먼저 실행하세요.")
    st.stop()

date = st.selectbox("날짜", dates, label_visibility="collapsed")
doc = _doc(date)
st.caption(f"{doc['report_date']} · 생성 {doc['generated_at'][5:16].replace('T', ' ')} · "
           f"성공 {doc['ok_count']} / 실패 {doc['fail_count']}")

by = lambda *g: [r for r in doc["market"] if r["grp"] in g]  # noqa: E731

st.subheader("1. 주요 지수")
st.caption("종가 기준 전일 대비. 상승 빨강, 하락 파랑")
grid(by("지수-국내", "지수-미국", "환율"))

st.subheader("2. 미국 지표")
st.caption("VIX·금리는 미국 종가. 선물류는 진행 중 값이 섞일 수 있음")
grid(by("미국지표", "원자재"))

st.subheader("3. 전자공시 주목")
st.caption("직전 영업일~오늘 공시 중 키워드(계약·주주환원·리스크). 호재/악재 표시는 제목만 본 참고용")
if doc["disclosures"]:
    tone = {"호재쪽": "🔺", "악재쪽": "🔻", "중립": "▫️"}
    cats = []
    for x in doc["disclosures"]:
        if x["category"] not in cats:
            cats.append(x["category"])
    for c in cats:
        items = [x for x in doc["disclosures"] if x["category"] == c]
        corps = []
        for x in items:
            if x["corp"] not in corps:
                corps.append(x["corp"])
        with st.expander(f"{c} {len(corps)}종목", expanded=False):
            html = ""
            for name in corps:
                mine = [x for x in items if x["corp"] == name]
                html += f'<div class="it"><b>{name}</b> <small>{mine[0]["market"]}</small></div>'
                for x in mine:
                    html += (f'<div class="sub">{tone.get(x["tone"], "")} <a href="{x["url"]}" target="_blank">{x["title"]}</a>'
                             f' <span class="d">{x["date"][4:6]}/{x["date"][6:]}</span></div>')
            st.markdown(html, unsafe_allow_html=True)
else:
    st.caption("해당 공시 없음")

st.subheader("4. 예정 행사")
st.caption("오늘부터 7일 이내. 미국 행사는 한국 시각으로 표시")
if doc["events"]:
    import datetime as _dt
    base = _dt.date.fromisoformat(doc["report_date"])
    last = None
    for e in doc["events"]:
        if e["date"] != last:
            last = e["date"]
            n = (_dt.date.fromisoformat(e["date"]) - base).days
            tag = "오늘" if n == 0 else f"D-{n}"
            st.markdown(f"**{e['date'][5:].replace('-', '/')}** ({tag})")
        t = f"{e['time']} " if e.get("time") else ""
        sub = f'<div class="sub"><span class="d">{e["detail"]}</span></div>' if e.get("detail") else ""
        st.markdown(f'<div class="ev">{t}<b>[{e["category"]}]</b> {e["title"]}</div>{sub}', unsafe_allow_html=True)
else:
    st.caption("7일 이내 등록된 행사 없음")

st.subheader("5. 수급 들어온 테마")
st.caption("준비 중 (종목→테마 표 필요)")

if USE_MD:
    st.subheader("6. Daily 급등 종목")
    st.caption("등락률 높은 순. 아래 줄은 텔레그램에서 뽑은 이슈")
    try:
        ddates = st.cache_data(ttl=300)(mdb.daily_dates)()
        if ddates:
            dd = st.selectbox("Daily 날짜", ddates, label_visibility="collapsed")
            html = ""
            for r in st.cache_data(ttl=300)(mdb.daily_rows)(dd):
                p = r["pct"]
                pc = "" if p is None else f'<span style="color:{UP if p >= 0 else DOWN}">{"+" if p >= 0 else ""}{p:.2f}%</span>'
                th = f' <small>{r["theme"]}</small>' if r["theme"] else ""
                html += f'<div class="it"><b>{r["name"]}</b> <small>{r["code"]}</small> {pc}{th}</div>'
                if r["telegram"]:
                    html += f'<div class="sub">{r["telegram"]}</div>'
            st.markdown(html, unsafe_allow_html=True)
        else:
            st.caption("Daily 자료 없음")
    except Exception as e:  # noqa: BLE001
        st.caption(f"Daily 불러오기 실패: {e}")

if doc["failures"]:
    st.warning("자료 없음: " + ", ".join(f.split("(")[0] for f in doc["failures"]))

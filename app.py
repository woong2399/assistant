"""급등주 일지 화면. 데이터: MotherDuck assistant.daily_pick (읽기 전용 화면)"""
import html
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
import mdb  # noqa: E402

UP, DOWN, MUTED = "#d6372b", "#1f6fd0", "#6a6a6a"  # 한국식: 상승 빨강, 하락 파랑
LABEL = {"surge": "10%↑", "telegram": "텔레그램만", "both": ""}

st.set_page_config(page_title="급등주 일지", layout="centered")
st.markdown(
    """<style>
    .block-container{padding:1rem 1rem 3rem;max-width:520px}
    h1{font-size:22px!important}h2{font-size:15px!important;margin-top:1rem!important}
    .it{margin:10px 0 2px;font-size:15px}.it small{color:#6a6a6a;font-size:11px}
    .tag{font-size:10px;border:1px solid #ccc;border-radius:4px;padding:0 4px;color:#6a6a6a;margin-left:4px}
    .sub{margin:1px 0 0 14px;font-size:13px;line-height:1.5}.sub a{text-decoration:none}
    .th{margin:1px 0 0 14px;font-size:11px;color:#6a6a6a}
    </style>""",
    unsafe_allow_html=True,
)
st.title("급등주 일지")

if not mdb.available():
    st.info("이 화면은 MotherDuck 토큰이 있어야 보입니다.")
    st.stop()


@st.cache_data(ttl=300)
def _dates():
    return mdb.daily_dates()


@st.cache_data(ttl=300)
def _rows(d):
    return mdb.daily_rows(d)


try:
    dates = _dates()
    if not dates:
        st.caption("아직 일지 자료가 없습니다.")
        st.stop()
    day = st.selectbox("날짜", dates, label_visibility="collapsed")
    rows = _rows(day)
except Exception as e:  # noqa: BLE001
    st.warning(f"불러오기 실패: {e}")
    st.stop()

kind = st.radio("보기", ["전체", "10%↑만", "텔레그램에만"], horizontal=True, label_visibility="collapsed")
if kind == "10%↑만":
    rows = [r for r in rows if r["source"] in ("surge", "both")]
elif kind == "텔레그램에만":
    rows = [r for r in rows if r["source"] == "telegram"]

n_issue = sum(1 for r in rows if r["issue"])
st.caption(f"{day} · {len(rows)}종목 · 이슈 있음 {n_issue}")

# 테마별 종목 수 (테마가 입력된 날만)
themes = {}
for r in rows:
    for t in (r["theme"] or "").split(", "):
        if t:
            themes.setdefault(t, []).append(r["name"])
if themes:
    st.subheader("테마")
    parts = [f'<div class="it"><b>{html.escape(t)}</b> <small>{len(v)}종목 · {html.escape(", ".join(v[:6]))}'
             f'{" …" if len(v) > 6 else ""}</small></div>'
             for t, v in sorted(themes.items(), key=lambda x: -len(x[1]))]
    st.markdown("".join(parts), unsafe_allow_html=True)

st.subheader("종목")
out = ""
for r in rows:
    p = r["pct"]
    pc = "" if p is None else f'<span style="color:{UP if p >= 0 else DOWN}">{"+" if p >= 0 else ""}{p:.2f}%</span>'
    tag = LABEL.get(r["source"] or "", "")
    tag = f'<span class="tag">{tag}</span>' if tag else ""
    amt = f' · 거래대금 {r["amount"]:,.0f}백만' if r["amount"] else ""
    out += (f'<div class="it"><b>{html.escape(r["name"])}</b> <small>{r["code"]}{amt}</small> {pc}{tag}</div>')
    if r["theme"]:
        out += f'<div class="th">{html.escape(r["theme"])}</div>'
    if r["issue"]:
        out += f'<div class="sub">{html.escape(r["issue"])}</div>'
    for n in r["news"]:
        u = n.get("url", "")
        h = html.escape(n.get("headline", ""))
        out += f'<div class="sub">📰 <a href="{html.escape(u)}" target="_blank">{h}</a></div>' if u else f'<div class="sub">📰 {h}</div>'
st.markdown(out or "<div class='sub'>해당 종목 없음</div>", unsafe_allow_html=True)

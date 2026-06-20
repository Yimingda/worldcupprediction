#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""今日 / 指定日期的比赛预测列表。"""

import streamlit as st

from core import loader, view

st.set_page_config(page_title="今日预测", page_icon="🔥", layout="wide")
view.inject_css()

recs = loader.records()
all_dates = loader.dates()

st.title("🔥 比赛预测")
if not all_dates:
    st.info("暂无任何比赛日数据。")
    st.stop()

date = st.selectbox("选择比赛日", options=list(reversed(all_dates)), index=0)
day_recs = [r for r in recs if r["date"] == date]
st.caption(f"{date} · 共 {len(day_recs)} 场")

cols = st.columns(2)
for i, r in enumerate(day_recs):
    p = r["p"]
    with cols[i % 2].container(border=True):
        st.markdown(f"### {p.get('home_flag','')} {p.get('home_name','')} "
                    f"vs {p.get('away_flag','')} {p.get('away_name','')}")
        st.markdown(f"<span style='color:#888;font-size:12px'>{view.esc(p.get('match_group',''))} · "
                    f"{view.esc(p.get('match_date',''))} · {view.esc(p.get('match_venue',''))}</span>",
                    unsafe_allow_html=True)
        hp, dp = int(p.get("home_prob", 0)), int(p.get("draw_prob", 0))
        ap = int(p.get("away_prob", 100 - hp - dp))
        view.md(view.prob_split(hp, dp, ap)
                + f"<div style='font-size:12px;color:#666'>{p.get('home_name','')} {hp}% · "
                  f"平 {dp}% · {p.get('away_name','')} {ap}%</div>")
        actual = f" ｜ 实际 **{r['actual'][0]}-{r['actual'][1]}**" if r["actual"] else " ｜ 待赛"
        st.markdown(f"**推荐：{p.get('verdict_rec','—')}** ｜ 预测 **{p.get('verdict_score','-')}** "
                    f"｜ 把握 {view.stars(p.get('verdict_stars',0))}{actual}")
        if r["scored"]:
            view.md(view.result_badges(r["scored"]))
        if st.button("查看完整分析 →", key=f"d_{r['match_id']}", use_container_width=True):
            loader.open_detail(r["match_id"])

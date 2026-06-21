#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""今日 / 指定日期的比赛预测列表（暖色卡片观感，与模板统一）。"""

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
    hp, dp = int(p.get("home_prob", 0)), int(p.get("draw_prob", 0))
    ap = int(p.get("away_prob", 100 - hp - dp))
    actual = ('<span style="color:#0F6E56;font-weight:700">实际 %d-%d</span>' % (r["actual"][0], r["actual"][1])
              if r["actual"] else '<span style="color:#999">待赛</span>')
    badges = view.result_badges(r["scored"]) if r["scored"] else ""

    rec_box = (
        '<div style="display:flex;justify-content:space-between;align-items:center;gap:10px;'
        'background:#e8f8f2;border:1px solid rgba(29,158,117,.3);border-radius:8px;padding:8px 12px;margin-bottom:8px">'
        '<div style="font-size:13px;font-weight:700;color:#0F6E56">' + view.esc(p.get("verdict_rec", "—")) + '</div>'
        '<div style="text-align:right;font-size:12px;color:#0F6E56">预测 <b>' + view.esc(p.get("verdict_score", "-"))
        + '</b> · ' + view.stars(p.get("verdict_stars", 0)) + '</div></div>')

    card = (
        '<div class="wc-card">'
        '<div style="font-size:16px;font-weight:700;margin-bottom:2px">'
        + p.get("home_flag", "") + ' ' + view.esc(p.get("home_name", ""))
        + ' <span style="color:#aaa">vs</span> '
        + p.get("away_flag", "") + ' ' + view.esc(p.get("away_name", "")) + '</div>'
        '<div style="font-size:11px;color:#888;margin-bottom:10px">'
        + view.esc(p.get("match_group", "")) + ' · ' + view.esc(p.get("match_date", "")) + ' · '
        + view.esc(p.get("match_venue", "")) + '</div>'
        + view.prob_split(hp, dp, ap)
        + '<div style="font-size:12px;color:#666;margin-bottom:8px">'
        + p.get("home_flag", "") + ' ' + str(hp) + '% &nbsp;·&nbsp; 平 ' + str(dp) + '% &nbsp;·&nbsp; '
        + p.get("away_flag", "") + ' ' + str(ap) + '%</div>'
        + rec_box
        + '<div style="font-size:12px;margin-bottom:2px">' + actual + ' &nbsp; ' + badges + '</div>'
        + '</div>')

    with cols[i % 2]:
        view.md(card)
        if st.button("查看完整分析 →", key="d_%s" % r["match_id"], use_container_width=True):
            loader.open_detail(r["match_id"])

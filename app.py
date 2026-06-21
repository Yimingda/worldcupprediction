#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""世界杯预测中心 · 总览（Streamlit 多页应用入口）。"""

import streamlit as st

from core import loader, view

st.set_page_config(page_title="世界杯预测中心", page_icon="⚽", layout="wide")
view.inject_css()

recs = loader.records()
agg = loader.aggregate()
all_dates = loader.dates()
today = all_dates[-1] if all_dates else None

st.title("⚽ 世界杯预测中心 · 总览")
st.caption(f"累计 {agg['days']} 个比赛日 / {agg['total']} 场预测 · 已评分 {agg['graded']} 场")

if st.button("🔄 刷新最新数据", help="清缓存重新读取；注意：仅当已 push 到 GitHub，云端数据才会变"):
    loader.clear_cache()
    st.rerun()

# ── 战绩看板 ──
st.subheader("📊 累计战绩看板")
c = st.columns(4)
c[0].metric("已评分 / 总场次", f"{agg['graded']}/{agg['total']}")
c[1].metric("1X2 命中率", view.pct(agg["1x2"]))
c[2].metric("大小球命中", view.pct(agg["over25"]))
c[3].metric("让球命中", view.pct(agg["handicap"]))
c = st.columns(4)
c[0].metric("推荐兑现", view.pct(agg["verdict"]))
c[1].metric("精确比分", view.pct(agg["exact"]))
c[2].metric("平均 Brier", "—" if agg["brier"] is None else f"{agg['brier']:.3f}",
            help="三分类 Brier 分，越低越准（0~2）")
c[3].metric("大球偏差", "—" if agg["over_bias"] is None else f"{agg['over_bias']:+.2f}",
            help=">0 表示系统性高估进球数")

st.divider()

# ── 今日比赛预测 ──
st.subheader(f"🔥 今日比赛预测 · {today or '—'}")
todays = [r for r in recs if r["date"] == today]
if not todays:
    st.info("今日暂无世界杯比赛预测。")
else:
    cols = st.columns(2)
    for i, r in enumerate(todays):
        p = r["p"]
        with cols[i % 2].container(border=True):
            st.markdown(f"**{p.get('home_flag','')} {p.get('home_name','')} "
                        f"vs {p.get('away_flag','')} {p.get('away_name','')}**  ·  "
                        f"<span style='color:#888;font-size:12px'>{view.esc(p.get('match_group',''))} · "
                        f"{view.esc(p.get('match_date',''))}</span>", unsafe_allow_html=True)
            actual = f" ｜ 实际 **{r['actual'][0]}-{r['actual'][1]}**" if r["actual"] else " ｜ 待赛"
            st.markdown(f"推荐：{p.get('verdict_rec','—')} ｜ 预测 **{p.get('verdict_score','-')}** "
                        f"｜ 把握 {view.stars(p.get('verdict_stars',0))}{actual}")
            if r["scored"]:
                view.md(view.result_badges(r["scored"]))
            if st.button("查看完整分析 →", key=f"home_{r['match_id']}", use_container_width=True):
                loader.open_detail(r["match_id"])

st.divider()

# ── 历史时间线（最近 12 场） ──
st.subheader("🗂 历史归档 · 时间线")
ordered = sorted(recs, key=lambda x: (x["date"], -x["idx"]), reverse=True)
for r in ordered[:50]:
    p, sc = r["p"], r["scored"]
    left, mid, right = st.columns([1.2, 3, 1.2])
    left.markdown(f"<span style='font-size:12px;color:#888'>{r['date']}</span>", unsafe_allow_html=True)
    teams = (f"{p.get('home_flag','')} {p.get('home_name','')} vs "
             f"{p.get('away_flag','')} {p.get('away_name','')}")
    badges = view.result_badges(sc)
    mid.markdown(f"{teams}<br>{badges}", unsafe_allow_html=True)
    actual = f"{r['actual'][0]}-{r['actual'][1]}" if r["actual"] else "—"
    right.markdown(f"<div style='text-align:right'>预测 <b>{p.get('verdict_score','-')}</b><br>"
                   f"实际 <b>{actual}</b></div>", unsafe_allow_html=True)
if len(ordered) > 50:
    st.caption(f"仅显示最近 50 场，完整列表见「历史回测」页。")

st.caption("⚠ 全部分析由模型基于公开数据自动生成，仅供参考。请理性博彩，量力而行。")

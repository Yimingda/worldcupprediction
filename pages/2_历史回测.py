#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""历史回测：累计指标 + 趋势图 + 校准追踪 + 全量明细表。"""

import pandas as pd
import streamlit as st

from core import loader, view, calibration

st.set_page_config(page_title="历史回测", page_icon="📈", layout="wide")
view.inject_css()

recs = loader.records()
agg = loader.aggregate()
daily = loader.daily()

st.title("📈 历史回测")
st.caption(f"已评分 {agg['graded']} / 总 {agg['total']} 场 · {agg['days']} 个比赛日")

c = st.columns(4)
c[0].metric("1X2 命中率", view.pct(agg["1x2"]))
c[1].metric("大小球命中", view.pct(agg["over25"]))
c[2].metric("推荐兑现", view.pct(agg["verdict"]))
c[3].metric("平均 Brier", "—" if agg["brier"] is None else f"{agg['brier']:.3f}")

# ── 趋势图 ──
if daily:
    st.subheader("逐日趋势")
    df = pd.DataFrame(daily).set_index("date")
    t1, t2 = st.tabs(["命中率", "Brier"])
    with t1:
        st.line_chart(df[["hit_1x2", "hit_over25"]].rename(
            columns={"hit_1x2": "1X2命中", "hit_over25": "大小球命中"}))
    with t2:
        st.line_chart(df[["brier"]].rename(columns={"brier": "Brier"}))

# ── 校准追踪 ──
st.subheader("校准追踪")
cal = calibration.summary(recs)
cc = st.columns(2)
cc[0].metric("对数损失 log-loss", "—" if cal["log_loss"] is None else f"{cal['log_loss']:.3f}",
             help="衡量概率本身的准度（不只看命中），越低越好")
cc[1].metric("校准误差 ECE", "—" if cal["ece"] is None else f"{cal['ece']:.0f}%",
             help="平均 |置信度 - 实际命中率|，越低越校准")
if cal["buckets"]:
    st.caption("置信度分桶：校准良好时「平均置信度」应≈「实际命中率」")
    st.dataframe(pd.DataFrame(cal["buckets"]), use_container_width=True, hide_index=True)
else:
    st.caption("样本不足，暂无法分桶。")

# ── 明细表 ──
st.subheader("全量明细")
rows = []
for r in sorted(recs, key=lambda x: (x["date"], x["idx"]), reverse=True):
    p, sc = r["p"], r["scored"]
    rows.append({
        "日期": r["date"],
        "对阵": f"{p.get('home_name','')} vs {p.get('away_name','')}",
        "预测": p.get("verdict_score", "-"),
        "实际": f"{r['actual'][0]}-{r['actual'][1]}" if r["actual"] else "待赛",
        "1X2": ("✅" if sc["hit_1x2"] else "❌") if sc else "—",
        "大小球": ("✅" if sc["over25_hit"] else "❌") if sc else "—",
        "让球": ("✅" if sc["handicap_hit"] else "❌") if sc and sc["handicap_hit"] is not None else "—",
        "推荐": ("✅" if sc["verdict_hit"] else "❌") if sc and sc["verdict_hit"] is not None else "—",
        "比分": ("✅" if sc["exact_hit"] else "❌") if sc else "—",
        "Brier": sc["brier"] if sc else None,
    })
st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

st.subheader("打开单场详情")
labels = {f"{r['date']} · {r['p'].get('home_name','')} vs {r['p'].get('away_name','')}": r["match_id"]
          for r in sorted(recs, key=lambda x: (x["date"], x["idx"]), reverse=True)}
if labels:
    pick = st.selectbox("选择比赛", options=list(labels.keys()))
    if st.button("查看完整分析 →"):
        loader.open_detail(labels[pick])

st.caption("⚠ 样本量较小时指标仅作方向参考；数据按日累积，长期更可靠。")

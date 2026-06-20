#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""夺冠专题：四强 & 冠军预测。"""

import pandas as pd
import streamlit as st

from core import champion, view

st.set_page_config(page_title="夺冠专题", page_icon="🏆", layout="wide")
view.inject_css()

data = champion.load_champion()
if not data:
    st.info("暂无冠军预测数据（streamlit_app/data/champion_prediction.json 不存在）。")
    st.stop()

champs = data.get("champions", [])

st.title("🏆 " + data.get("title", "四强 & 冠军预测"))
st.caption(f"基准日 {data.get('as_of','')} · {data.get('stage','')} · {data.get('final_info','')}")

# ── 最终结论 ──
v = data.get("verdict", {})
if v:
    logic = "<br>".join("· " + view.esc(x) for x in v.get("logic", []))
    view.md(
        '<div class="wc-card wc-teal"><div style="display:flex;justify-content:space-between;gap:16px;flex-wrap:wrap">'
        f'<div><div class="wc-label" style="color:#0F6E56">本届结论</div>'
        f'<div style="font-size:15px;color:#0F6E56;line-height:1.9">'
        f'🏆 冠军 <b>{view.esc(v.get("champion","-"))}</b> &nbsp;|&nbsp; 🥈 亚军 <b>{view.esc(v.get("runner_up","-"))}</b>'
        f' &nbsp;|&nbsp; 🐎 黑马 <b>{view.esc(v.get("dark_horse","-"))}</b></div>'
        f'<div style="font-size:12px;color:#0F6E56;margin-top:6px;line-height:1.7">{logic}</div></div>'
        f'<div style="text-align:right"><div class="wc-label" style="color:#0F6E56">预测决赛比分</div>'
        f'<div style="font-size:30px;font-weight:700;color:#0F6E56">{view.esc(v.get("final_pick","-"))}</div>'
        f'<div style="font-size:12px;color:#0F6E56">把握度 {view.stars(v.get("stars",0))}</div></div></div></div>')

# ── 夺冠概率排行 ──
st.subheader("夺冠概率排行")
if champs:
    df = pd.DataFrame([{"队伍": f"{c.get('flag','')} {c['team']}", "夺冠概率(%)": c["champ_prob"]} for c in champs])
    st.bar_chart(df.set_index("队伍"), horizontal=True, color="#1D9E75")

# ── 四强预测 ──
st.subheader("🎯 四强预测")
ff = data.get("final_four", [])
cols = st.columns(len(ff) if ff else 1)
for i, t in enumerate(ff):
    with cols[i].container(border=True):
        st.markdown(f"### {t.get('flag','')} {t.get('team','')}")
        st.markdown(f"进四强概率 **{t.get('sf_prob',0)}%**")
        view.md(view.bar("", t.get("sf_prob", 0), 100, "#1D9E75", "%"))
        st.caption(t.get("why", ""))

# ── 夺冠梯队总表 ──
st.subheader("夺冠梯队（三档概率）")
if champs:
    table = pd.DataFrame([{
        "#": c["rank"], "队伍": f"{c.get('flag','')} {c['team']}", "档位": c.get("tier", ""),
        "夺冠%": c["champ_prob"], "进决赛%": c["final_prob"], "进四强%": c["sf_prob"],
        "参考赔率": c.get("odds", "-"),
    } for c in champs])
    st.dataframe(table, use_container_width=True, hide_index=True)

# ── 候选详情 ──
st.subheader("候选详情")
for c in champs:
    with st.expander(f"{c.get('flag','')} {c['team']} — {c.get('tier','')}（夺冠 {c['champ_prob']}%）"):
        r = c.get("rating", {})
        if r:
            labels = {"attack": "进攻", "defense": "防守", "squad_depth": "深度",
                      "form": "状态", "path_ease": "签运", "experience": "经验"}
            bars = "".join(view.bar(labels.get(k, k), r[k], 10, "#1D9E75") for k in labels if k in r)
            view.md(bars)
        if c.get("key_players"):
            view.md("关键球员：" + " ".join(view.badge(p, "blue") for p in c["key_players"]))
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**优势**")
            for s in c.get("strengths", []):
                st.markdown(f"- {s}")
        with col2:
            st.markdown("**风险**")
            for s in c.get("risks", []):
                st.markdown(f"- {s}")
        if c.get("rationale"):
            st.caption("综合理由：" + c["rationale"])

# ── 方法权重 ──
mw = data.get("method_weights", {})
if mw:
    st.subheader("预测方法权重")
    st.markdown(" ｜ ".join(f"{k} **{v}%**" for k, v in mw.items()))

st.caption("⚠ " + data.get("disclaimer", "仅供参考，请理性博彩。"))

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""球队本届战绩：选一支球队，查看其全部世界杯比赛与聚合数据。
可由「单场详情」页的链接带入（session_state/query_params 中的 team）。"""

import streamlit as st

from core import team_history as TH, standings, view

st.set_page_config(page_title="球队战绩", page_icon="📋", layout="wide")
view.inject_css()

teams = TH.all_teams()
if not teams:
    st.info("暂无球队数据（streamlit_app/data 下无 predictions.json）。")
    st.stop()

st.title("📋 球队本届战绩")

pre = st.session_state.get("team_pick") or st.query_params.get("team")
pre = standings.canon(pre) if pre else None
idx = teams.index(pre) if pre in teams else 0
team = st.selectbox("选择球队", teams, index=idx)
st.session_state["team_pick"] = team
st.query_params["team"] = team

flags = standings.discover_flags()
fl = flags.get(team, "")
s = TH.team_summary(team)

st.subheader(f"{fl} {team}" + (f" · {s['group']}组" if s["group"] else ""))
c = st.columns(5)
c[0].metric("已赛", s["played"])
c[1].metric("胜 / 平 / 负", f'{s["w"]} / {s["d"]} / {s["l"]}')
c[2].metric("进 / 失", f'{s["gf"]} / {s["ga"]}')
c[3].metric("积分", s["pts"])
c[4].metric("预测精确命中", f'{s["pred_exact_hit"]} / {s["played"]}')

st.markdown("#### 本届全部比赛")
rows = TH.team_matches(team)
if not rows:
    st.caption("暂无比赛记录。")
for r in rows:
    oc = r["outcome"]
    clr = {"胜": "#1D9E75", "平": "#888", "负": "#c0392b"}.get(oc, "#bbb")
    badge = f'<span style="color:{clr};font-weight:700">{oc or "待赛"}</span>'
    ha = "主" if r["is_home"] else "客"
    actual = r["actual"] or "—"
    view.md(
        '<div class="wc-card" style="padding:8px 14px;display:flex;justify-content:space-between;'
        'align-items:center;gap:10px">'
        f'<div style="font-size:11px;color:#888;width:96px;flex-shrink:0">{r["date"]}'
        f'<br><span style="font-size:10px">{ha}场 · {view.esc(r["group"])}</span></div>'
        f'<div style="flex:1;font-size:14px;font-weight:600">{fl}{view.esc(team)} '
        f'<span style="color:#ccc">vs</span> {r["opp_flag"]}{view.esc(r["opponent"])}</div>'
        f'<div style="text-align:right;font-size:12px;flex-shrink:0">预测 {view.esc(r["pred"])}'
        f'<br>实际 <b>{view.esc(actual)}</b> &nbsp;{badge}</div></div>')

st.caption("⚠ 仅覆盖本系统已生成预测的比赛日；更早轮次若无数据则不显示。分析仅供参考。")

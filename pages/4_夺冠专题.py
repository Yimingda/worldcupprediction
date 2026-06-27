#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""夺冠专题：四强 & 冠军预测。"""

import pandas as pd
import streamlit as st

from core import champion, view, standings

st.set_page_config(page_title="夺冠专题", page_icon="🏆", layout="wide")
view.inject_css()

data = champion.load_champion()
if not data:
    st.info("暂无冠军预测数据（streamlit_app/data/champion_prediction.json 不存在）。")
    st.stop()

champs = data.get("champions", [])

st.title("🏆 " + data.get("title", "四强 & 冠军预测"))
st.caption(f"基准日 {data.get('as_of','')} · {data.get('stage','')} · {data.get('final_info','')}")
st.caption("📌 概率基于公开赔率与实力推断，非自建模型；签表未定，不确定性高。")

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

# ── 分组积分榜（12组）──
st.divider()
st.subheader("📊 分组积分榜")
st.caption("按当前已赛累计；前两名（绿底）直接出线。小组赛进行中，最终以官方为准。")
try:
    _cur = standings.current_standings()
    _flags = standings.discover_flags()
    _gcols = st.columns(3)
    for _gi, _g in enumerate(sorted(standings.GROUPS)):
        _rows = _cur.get(_g, [])
        with _gcols[_gi % 3]:
            _h = [f'<div class="wc-card" style="padding:10px 12px;margin-bottom:10px">'
                  f'<div style="font-weight:700;margin-bottom:6px">{_g} 组</div>'
                  '<table style="width:100%;border-collapse:collapse;font-size:12px">'
                  '<tr style="color:#999;font-size:10px"><th style="text-align:left">#&nbsp;队</th>'
                  '<th>赛</th><th>积</th><th>净</th></tr>']
            for _i, _r in enumerate(_rows, 1):
                _bg = "background:#eaf3de;" if _i <= 2 else ""
                _fl = _flags.get(_r["team"], "")
                _gd = _r["gd"]
                _h.append(f'<tr style="{_bg}"><td style="text-align:left">{_i}&nbsp;{_fl}{view.esc(_r["team"])}</td>'
                          f'<td style="text-align:center">{_r["p"]}</td>'
                          f'<td style="text-align:center;font-weight:700">{_r["pts"]}</td>'
                          f'<td style="text-align:center">{"+" if _gd > 0 else ""}{_gd}</td></tr>')
            _h.append('</table></div>')
            view.md("".join(_h))
except Exception as _e:
    st.caption(f"积分榜暂不可用：{_e}")

# ── 32强对阵图（淘汰赛签表）──
st.divider()
st.subheader("🗺️ 32强对阵（淘汰赛签表）")
st.caption("已确定的填队名；未定的显示占位（「C组第1」「最佳第三」）。各组踢满3轮并回填赛果后自动补齐。")
try:
    _br = standings.bracket(standings.current_standings())
    _bf = standings.discover_flags()

    def _disp(_name, _settled):
        _flag = _bf.get(_name, "") if _settled else ""
        _clr = "#1c1c1a;font-weight:700" if _settled else "#999"
        return f'<span style="color:{_clr}">{_flag}{view.esc(_name)}</span>'

    _bcols = st.columns(2)
    for _i, _m in enumerate(_br):
        with _bcols[_i % 2]:
            view.md(
                '<div class="wc-card" style="padding:8px 12px;margin-bottom:8px;display:flex;'
                'justify-content:space-between;align-items:center;gap:10px">'
                f'<div style="font-size:10px;color:#bbb;flex-shrink:0">R32-{_i + 1}</div>'
                f'<div style="font-size:13px;text-align:right;flex:1">'
                f'{_disp(_m["a"], _m["a_settled"])} <span style="color:#ccc">vs</span> '
                f'{_disp(_m["b"], _m["b_settled"])}</div></div>')
except Exception as _e:
    st.caption(f"对阵图暂不可用：{_e}")

# ── 夺冠梯队总表 ──
st.divider()
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

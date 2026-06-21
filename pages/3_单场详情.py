#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""单场完整赛前分析详情。原样嵌入与静态模板一致的 HTML（render_match）。
通过 ?match=日期|序号 或下拉选择进入。"""

import streamlit as st
import streamlit.components.v1 as components

from core import data, loader, match_html, view

st.set_page_config(page_title="单场详情", page_icon="🔎", layout="wide")
view.inject_css()

recs = loader.records()
if not recs:
    st.info("暂无任何比赛数据。")
    st.stop()

match_id = st.query_params.get("match")
labels = {f"{r['date']} · {r['p'].get('home_name','')} vs {r['p'].get('away_name','')}": r["match_id"]
          for r in sorted(recs, key=lambda x: (x["date"], x["idx"]), reverse=True)}
ids = list(labels.values())
default_idx = ids.index(match_id) if match_id in ids else 0

pick_label = st.selectbox("选择比赛", options=list(labels.keys()), index=default_idx)
chosen_id = labels[pick_label]
st.query_params["match"] = chosen_id

rec = data.find_record(recs, chosen_id)
if not rec:
    st.error("未找到该比赛。")
    st.stop()

if rec["actual"]:
    view.md(f'<div class="wc-card wc-teal" style="margin-bottom:6px"><b>实际比分 '
            f'{rec["actual"][0]}-{rec["actual"][1]}</b> &nbsp; {view.result_badges(rec["scored"])}</div>')


def estimate_height(p):
    """按内容估算 iframe 高度，尽量少留白、不截断。"""
    h = 3700
    if p.get("group_standings"):
        h += 300
    if p.get("home_scorers") or p.get("away_scorers"):
        h += 130
    mext = max(len(p.get("home_mentality", [])), len(p.get("away_mentality", [])))
    if mext > 2:
        h += (mext - 2) * 80
    rext = max(len(p.get("home_risks", [])), len(p.get("away_risks", [])))
    if rext > 3:
        h += (rext - 3) * 30
    return h


html = match_html.render_match(rec["p"])
html = html.replace(
    '<div style="margin-bottom:10px"><a href="../index.html" '
    'style="font-size:12px;color:#888;text-decoration:none">← 返回总览</a></div>', "")

components.html(html, height=estimate_height(rec["p"]), scrolling=True)

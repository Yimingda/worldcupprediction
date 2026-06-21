#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""单场完整赛前分析详情。复用 view.render_detail 渲染（与静态模板视觉一致）。
通过 ?match=日期|序号 或下拉选择进入。"""

import streamlit as st

from core import data, loader, view

st.set_page_config(page_title="单场详情", page_icon="🔎", layout="wide")
view.inject_css()

recs = loader.records()
if not recs:
    st.info("暂无任何比赛数据。")
    st.stop()

# 优先用 session_state（switch_page 可靠保留）；回退到 URL 查询参数（可分享链接）
match_id = st.session_state.get("detail_match_id") or st.query_params.get("match")
labels = {f"{r['date']} · {r['p'].get('home_name','')} vs {r['p'].get('away_name','')}": r["match_id"]
          for r in sorted(recs, key=lambda x: (x["date"], x["idx"]), reverse=True)}
ids = list(labels.values())
default_idx = ids.index(match_id) if match_id in ids else 0

pick_label = st.selectbox("选择比赛", options=list(labels.keys()), index=default_idx)
chosen_id = labels[pick_label]
st.session_state["detail_match_id"] = chosen_id
st.query_params["match"] = chosen_id

rec = data.find_record(recs, chosen_id)
if not rec:
    st.error("未找到该比赛。")
    st.stop()

view.render_detail(rec["p"], rec["actual"], rec["scored"])

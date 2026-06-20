#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Streamlit 渲染组件：复用静态版的视觉语言（卡片/徽章/进度条）。"""

import html as _html
import streamlit as st

H, A = "#1D9E75", "#BA7517"

CSS = """
<style>
.block-container{padding:1.2rem 2rem 3rem;max-width:1100px}
.wc-card{background:#fff;border:1px solid #e2e0d8;border-radius:12px;padding:14px 18px;margin-bottom:12px}
.wc-teal{background:#e8f8f2;border:1px solid rgba(29,158,117,.3)}
.wc-amber{background:#fdf6e8;border:1px solid rgba(186,117,23,.25)}
.wc-label{font-size:10px;font-weight:700;color:#999;text-transform:uppercase;letter-spacing:.07em;margin-bottom:6px}
.wc-badge{display:inline-block;font-size:11px;font-weight:600;padding:2px 10px;border-radius:20px;margin:2px}
.b-green{background:#eaf3de;color:#3b6d11}.b-amber{background:#faeeda;color:#854f0b}
.b-red{background:#fdeaea;color:#a32d2d}.b-blue{background:#e6f1fb;color:#185fa5}.b-gray{background:#f0efe8;color:#555}
.wc-quote{background:#f5f4f0;border-left:3px solid #d0cec8;padding:5px 10px;border-radius:0 6px 6px 0;font-style:italic;color:#666;font-size:12px;margin-top:6px}
</style>
"""

_BADGE_CLS = {"green": "b-green", "amber": "b-amber", "red": "b-red", "blue": "b-blue", "gray": "b-gray"}


def inject_css():
    st.markdown(CSS, unsafe_allow_html=True)


def esc(x):
    return _html.escape(str(x), quote=True)


def pct(x):
    return "—" if x is None else f"{x * 100:.0f}%"


def stars(n):
    try:
        return "⭐" * int(n)
    except Exception:
        return ""


def badge(text, style="gray"):
    return f'<span class="wc-badge {_BADGE_CLS.get(style, "b-gray")}">{esc(text)}</span>'


def md(html):
    st.markdown(html, unsafe_allow_html=True)


def bar(label, val, max_val, color=H, suffix=""):
    try:
        num = float(str(val).replace("%", "") or 0)
    except ValueError:
        num = 0
    w = min(num / max_val * 100, 100) if max_val else 0
    return (f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:5px">'
            f'<div style="font-size:11px;color:#888;width:84px;flex-shrink:0">{esc(label)}</div>'
            f'<div style="flex:1;height:5px;background:#eeede8;border-radius:3px;overflow:hidden">'
            f'<div style="width:{w:.0f}%;height:100%;background:{color};border-radius:3px"></div></div>'
            f'<div style="font-size:11px;font-weight:600;width:46px;text-align:right;color:{color}">{esc(val)}{esc(suffix)}</div></div>')


def prob_split(hp, dp, ap):
    ap = max(int(ap), 0)
    return (f'<div style="display:flex;height:10px;border-radius:5px;overflow:hidden;gap:2px;margin:8px 0">'
            f'<div style="flex:{hp};background:#1D9E75;border-radius:3px 0 0 3px"></div>'
            f'<div style="flex:{dp};background:#ccc"></div>'
            f'<div style="flex:{ap};background:#BA7517;border-radius:0 3px 3px 0"></div></div>')


def result_badges(scored):
    if not scored:
        return badge("待赛", "gray")
    b = badge("胜平负 ✓" if scored["hit_1x2"] else "胜平负 ✗", "green" if scored["hit_1x2"] else "red")
    b += badge("大小球 ✓" if scored["over25_hit"] else "大小球 ✗", "green" if scored["over25_hit"] else "red")
    if scored["handicap_hit"] is not None:
        b += badge("让球 ✓" if scored["handicap_hit"] else "让球 ✗", "green" if scored["handicap_hit"] else "red")
    return b


# ───────────── 单场完整详情 ─────────────
def render_detail(p, actual, scored):
    g = p.get
    md(f'<h2>⚽ {g("home_flag","")} {esc(g("home_name",""))} '
       f'<span style="color:#aaa">vs</span> {g("away_flag","")} {esc(g("away_name",""))}</h2>'
       f'<div style="color:#888;font-size:13px;margin-bottom:6px">{esc(g("match_group",""))} · '
       f'{esc(g("match_date",""))} · {esc(g("match_venue",""))}</div>')

    if actual:
        md(f'<div class="wc-card wc-teal"><b>实际比分 {actual[0]}-{actual[1]}</b> &nbsp; {result_badges(scored)}</div>')
    else:
        md(f'<div class="wc-card">{badge("尚未开赛 / 等待赛果", "gray")}</div>')

    # 胜负概率
    hp, dp = int(g("home_prob", 0)), int(g("draw_prob", 0))
    ap = int(g("away_prob", 100 - hp - dp))
    st.subheader("② 胜负概率 & 赔率")
    c1, c2, c3 = st.columns(3)
    for col, prob, lab, odds, clr in [
        (c1, hp, f'{g("home_flag","")} {g("home_name","")}赢', g("home_odds", "-"), H),
        (c2, dp, "平局", g("draw_odds", "-"), "#888"),
        (c3, ap, f'{g("away_flag","")} {g("away_name","")}赢', g("away_odds", "-"), A)]:
        col.markdown(f'<div class="wc-card" style="text-align:center"><div style="font-size:30px;font-weight:700;color:{clr}">{prob}%</div>'
                     f'<div style="font-size:11px;color:#888">{esc(lab)}</div>'
                     f'<div style="font-size:12px;font-weight:600;margin-top:4px">赔率 {esc(odds)}</div></div>',
                     unsafe_allow_html=True)
    md(prob_split(hp, dp, ap))

    # 上轮数据
    st.subheader("① 上轮表现")
    lc, rc = st.columns(2)
    _last_round(lc, g("home_flag", ""), g("home_name", ""), g("home_prev", ""),
                g("h_poss", 50), g("h_shots", 0), g("h_sot", 0), g("h_bc", 0),
                g("h_xg", 0), g("h_goals", 0), g("h_xga", 0), g("h_oshots", 0), g("h_osot", 0), H)
    _last_round(rc, g("away_flag", ""), g("away_name", ""), g("away_prev", ""),
                g("a_poss", 50), g("a_shots", 0), g("a_sot", 0), g("a_bc", 0),
                g("a_xg", 0), g("a_goals", 0), g("a_xga", 0), g("a_oshots", 0), g("a_osot", 0), A)

    # 战术
    st.subheader("④ 阵型 & 战术")
    lc, rc = st.columns(2)
    _tactics(lc, p, "home", H)
    _tactics(rc, p, "away", A)

    # 心态
    st.subheader("⑤ 球员心态")
    lc, rc = st.columns(2)
    _mentality(lc, g("home_flag", ""), g("home_name", ""), g("home_mentality", []))
    _mentality(rc, g("away_flag", ""), g("away_name", ""), g("away_mentality", []))

    # 心态指标雷达
    labels = g("metric_labels", ["当前信心", "求胜紧迫", "进攻实力", "防守组织", "战术执行", "无压力感"])
    hm, am = g("home_metrics", []), g("away_metrics", [])
    if hm and am:
        st.subheader("⑦ 心态指标对比（满分10）")
        rows = "".join(
            f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:6px">'
            f'<div style="font-size:11px;color:#888;width:70px;text-align:right">{esc(labels[i])}</div>'
            f'<div style="flex:1">{bar(g("home_name",""), hm[i], 10, H)}{bar(g("away_name",""), am[i], 10, A)}</div></div>'
            for i in range(min(len(labels), len(hm), len(am))))
        md(f'<div class="wc-card">{rows}</div>')

    # 进球数量 + 比分
    st.subheader("⑧ 进球数量 & 最可能比分")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("过 2.5 球", f'{g("over25", 0)}%')
    c2.metric("过 3.5 球", f'{g("over35", 0)}%')
    c3.metric(f'{g("away_name","")}进球', f'{g("away_score_prob", 0)}%')
    c4.metric(esc(g("handicap_label", "让球")), f'{g("handicap", 0)}%')
    scores = g("likely_scores", [])
    if scores:
        chips = "".join(
            f'<span class="wc-badge {"b-green" if i == 0 else "b-gray"}" style="font-size:14px;font-weight:700">{esc(s)}'
            f'<span style="font-size:9px;font-weight:400"> {"最高" if i == 0 else "次选"}</span></span>' for i, s in enumerate(scores))
        md(f'<div style="margin-top:6px">{chips}</div>')

    # 风险点
    st.subheader("⑨ 风险点")
    lc, rc = st.columns(2)
    _risks(lc, "⚠ " + g("home_name", ""), g("home_risks", []))
    _risks(rc, "⚠ " + g("away_name", ""), g("away_risks", []))

    # 综合推荐
    st.subheader("⑩ 综合推荐")
    logic = "<br>".join("· " + esc(x) for x in g("verdict_logic", []))
    md(f'<div class="wc-card wc-teal"><div style="display:flex;justify-content:space-between;gap:16px;flex-wrap:wrap">'
       f'<div><div class="wc-label" style="color:#0F6E56">综合推荐</div>'
       f'<div style="font-size:17px;font-weight:700;color:#0F6E56">{esc(g("verdict_rec",""))}</div>'
       f'<div style="font-size:12px;color:#0F6E56;margin-top:6px;line-height:1.7">{logic}</div></div>'
       f'<div style="text-align:right"><div class="wc-label" style="color:#0F6E56">最可能比分</div>'
       f'<div style="font-size:34px;font-weight:700;color:#0F6E56">{esc(g("verdict_score","-"))}</div>'
       f'<div style="font-size:12px;color:#0F6E56">把握度 {stars(g("verdict_stars",0))}</div></div></div></div>')

    st.caption("⚠ 分析由模型基于公开数据自动生成，仅供参考。体育赛事充满不确定性，请理性博彩，量力而行。")


def _last_round(col, flag, name, prev, poss, shots, sot, bc, xg, goals, xga, oshots, osot, color):
    body = (f'<div class="wc-label">{flag} {esc(name)} — 上轮 {esc(prev)}</div>'
            + bar("控球率", poss, 100, color, "%") + bar("总射门", shots, 30, color)
            + bar("射正", sot, 15, color) + bar("大机会", bc, 8, color)
            + f'<div style="font-size:10px;color:#999;margin:6px 0 2px">xG {esc(xg)} → 实际 {esc(goals)} 球</div>'
            + '<div class="wc-label" style="margin-top:8px">防守（对手）</div>'
            + bar("对手射门", oshots, 30, "#378ADD") + bar("对手射正", osot, 15, "#378ADD")
            + bar("对手xG", xga, 3.0, "#c0392b" if float(xga or 0) > 1.2 else "#378ADD"))
    col.markdown(f'<div class="wc-card">{body}</div>', unsafe_allow_html=True)


def _tactics(col, p, side, color):
    g = p.get
    name = g(f"{side}_name", "")
    flag = g(f"{side}_flag", "")
    form = g(f"{side}_form", "")
    tactics = g(f"{side}_tactics", [])
    strat = g(f"{side}_strategy", "")
    bstyle = "green" if side == "home" else "amber"
    tg = "".join(badge(t, bstyle) for t in tactics)
    col.markdown(f'<div class="wc-card"><div style="font-weight:700;margin-bottom:6px">{flag} {esc(name)}</div>'
                 f'<div class="wc-badge b-gray" style="font-weight:700">{esc(form)}</div>'
                 f'<div style="margin:8px 0">{tg}</div>'
                 f'<div style="font-size:11px;font-weight:700;color:{color}">今日策略：{esc(strat)}</div></div>',
                 unsafe_allow_html=True)


def _mentality(col, flag, name, factors):
    if not factors:
        col.markdown('<div class="wc-card"><span style="color:#aaa;font-size:12px">（暂无心态数据）</span></div>',
                     unsafe_allow_html=True)
        return
    items = ""
    for f in factors:
        q = f'<div class="wc-quote">{esc(f.get("quote",""))}</div>' if f.get("quote") else ""
        items += (f'<div style="border-left:2px solid #e2e0d8;padding-left:8px;margin-bottom:8px">'
                  f'<div style="font-size:9px;font-weight:700;color:#999">{esc(f.get("title",""))}</div>'
                  f'<div style="font-size:11px;color:#444;margin-top:2px;line-height:1.5">{esc(f.get("desc",""))}</div>{q}</div>')
    col.markdown(f'<div class="wc-card"><div class="wc-label">{flag} {esc(name)} 赛前心态</div>{items}</div>',
                 unsafe_allow_html=True)


def _risks(col, title, risks):
    if not risks:
        col.markdown('<div class="wc-card"><span style="color:#aaa;font-size:12px">（暂无风险点）</span></div>',
                     unsafe_allow_html=True)
        return
    items = "".join(f'<div style="font-size:11px;margin-bottom:5px">• {esc(r)}</div>' for r in risks)
    col.markdown(f'<div class="wc-card"><div class="wc-label">{esc(title)}</div>{items}</div>', unsafe_allow_html=True)

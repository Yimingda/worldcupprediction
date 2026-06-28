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
    """单场完整详情：正文复用渲染库 detail_render.render_body（与原静态页同源 = 单一真相源），
    再叠加 Streamlit 专属的实际比分横幅与「球队战绩」跳转按钮。"""
    g = p.get
    import re as _re
    from core import detail_render as _dr

    # 实际比分横幅（Streamlit 专属）
    if actual:
        md(f'<div class="wc-card wc-teal"><b>实际比分 {actual[0]}-{actual[1]}</b> &nbsp; {result_badges(scored)}</div>')
    else:
        md(f'<div class="wc-card">{badge("尚未开赛 / 等待赛果", "gray")}</div>')

    # 完整正文（① 前两轮 / ②-⑩ / ⑪ 全部板块，含 ⑧ 字典修复、一致性保护等，只此一份实现）
    _body = _re.sub(r'<div[^>]*><a href="\.\./index\.html".*?</a></div>', "", _dr.render_body(p), count=1)
    _override = ("body{background:transparent!important;padding:0!important}"
                 ".wrap{max-width:100%!important;margin:0!important}")
    md("<style>" + _dr.CSS + _override + "</style><div class=\"wrap\">" + _body + "</div>")

    # 交互：跳转到完整「球队战绩」页（正文 ⑪ 已含两队全部比赛列表）
    try:
        _cc = st.columns(2)
        for _col, _side in ((_cc[0], "home"), (_cc[1], "away")):
            _nm = g(f"{_side}_name", "")
            if _col.button(f"📋 {g(f'{_side}_flag', '')} {esc(_nm)} 全部比赛 →",
                           key=f"th_{_side}", use_container_width=True):
                st.session_state["team_pick"] = _nm
                st.query_params["team"] = _nm
                st.switch_page("pages/5_球队战绩.py")
    except Exception:
        pass


def _grade_boxes(xg, xga):
    """进攻/防守评分（与静态渲染器 match_html.last_match_panel 保持一致）。"""
    xv, xav = float(xg or 0), float(xga or 0)
    atk = "A" if xv > 1.5 else ("B" if xv > 1.0 else ("C" if xv > 0.5 else "D"))
    dfd = "A" if xav < 0.5 else ("B" if xav < 1.0 else ("C" if xav < 1.5 else "D"))
    atk_clr = "#1D9E75" if atk in ("A", "B") else "#BA7517"
    dfd_clr = "#1D9E75" if dfd in ("A", "B") else ("#BA7517" if dfd == "C" else "#c0392b")
    atk_note = f"xG {esc(xg)}，{'机会质量高' if xv > 1.2 else '有待提升'}"
    dfd_note = f"对手xG {esc(xga)}，{'防守稳健' if xav < 1.0 else '承压较大'}"

    def box(lbl, grade, note, clr):
        return (f'<div style="background:#f5f4f0;border-radius:8px;padding:8px 10px">'
                f'<div style="font-size:9px;color:#888;margin-bottom:2px">{lbl}</div>'
                f'<div style="font-size:18px;font-weight:700;color:{clr}">{grade}</div>'
                f'<div style="font-size:9px;color:#888;margin-top:2px;line-height:1.3">{note}</div></div>')

    return ('<div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:8px">'
            + box("进攻评分", atk, atk_note, atk_clr)
            + box("防守评分", dfd, dfd_note, dfd_clr) + '</div>')


def _last_round(col, flag, name, prev, poss, shots, sot, bc, xg, goals, xga, oshots, osot, color):
    body = (f'<div class="wc-label">{flag} {esc(name)} — 上轮 {esc(prev)}</div>'
            + bar("控球率", poss, 100, color, "%") + bar("总射门", shots, 30, color)
            + bar("射正", sot, 15, color) + bar("大机会", bc, 8, color)
            + f'<div style="font-size:10px;color:#999;margin:6px 0 2px">xG {esc(xg)} → 实际 {esc(goals)} 球</div>'
            + '<div class="wc-label" style="margin-top:8px">防守（对手）</div>'
            + bar("对手射门", oshots, 30, "#378ADD") + bar("对手射正", osot, 15, "#378ADD")
            + bar("对手xG", xga, 3.0, "#c0392b" if float(xga or 0) > 1.2 else "#378ADD")
            + _grade_boxes(xg, xga))
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
        q = f'<div class="wc-quote">{esc(f.get("quote", ""))}</div>' if f.get("quote") else ""
        items += (f'<div style="border-left:2px solid #e2e0d8;padding-left:8px;margin-bottom:8px">'
                  f'<div style="font-size:9px;font-weight:700;color:#999">{esc(f.get("title", ""))}</div>'
                  f'<div style="font-size:11px;color:#444;margin-top:2px;line-height:1.5">{esc(f.get("desc", ""))}</div>{q}</div>')
    col.markdown(f'<div class="wc-card"><div class="wc-label">{flag} {esc(name)} 赛前心态</div>{items}</div>',
                 unsafe_allow_html=True)


def _risks(col, title, risks):
    if not risks:
        col.markdown('<div class="wc-card"><span style="color:#aaa;font-size:12px">（暂无风险点）</span></div>',
                     unsafe_allow_html=True)
        return
    items = "".join(f'<div style="font-size:11px;margin-bottom:5px">• {esc(r)}</div>' for r in risks)
    col.markdown(f'<div class="wc-card"><div class="wc-label">{esc(title)}</div>{items}</div>',
                 unsafe_allow_html=True)

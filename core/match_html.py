#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
2026 世界杯赛前分析 —— 无界面静态 HTML 生成器  (v2 优化版)
============================================================
用途：把一个比赛数据 JSON 渲染成独立的 HTML 文件（无需 Streamlit / 浏览器服务）。
    python render_predictions.py matches.json --outdir "D:/AI工作台/世界杯自动预测"

v2 五项优化（基于复盘）：
  1. 落后逆转能力维度  —— 新增逆境/落后翻盘评分与历史表现说明。
  2. 进球组合          —— 不押单一球员，列出 2-3 名最可能破门球员及概率。
  3. 大球阈值自动上调  —— 依据实力差距自动判断推荐「过2.5 / 过3.5」。
  4. 积分局势表标配化  —— 每场自动渲染组内 4 队积分表 + 出线场景推演。
  5. xG 实力/运气标签  —— 依据「实际进球 vs xG 比值」自动标注真实实力 / 运气成分。

所有字段可选，缺失项使用合理默认值或自动计算。运行 `--sample` 查看完整示例。
"""

import argparse
import datetime as _dt
import html as _html
import json
import os
import re


# ───────────────────────── 默认值 ─────────────────────────
def _d(match: dict) -> dict:
    g = match.get
    m = {
        "home_flag": g("home_flag", "🏠"), "home_name": g("home_name", "主队"),
        "home_prev": g("home_prev", ""), "home_pts": g("home_pts", 0),
        "away_flag": g("away_flag", "✈️"), "away_name": g("away_name", "客队"),
        "away_prev": g("away_prev", ""), "away_pts": g("away_pts", 0),
        "match_group": g("match_group", ""), "match_date": g("match_date", ""),
        "match_venue": g("match_venue", ""),
        "h_poss": g("h_poss", 50), "h_shots": g("h_shots", 0), "h_sot": g("h_sot", 0),
        "h_bc": g("h_bc", 0), "h_xg": g("h_xg", 0.0), "h_goals": g("h_goals", 0),
        "h_xga": g("h_xga", 0.0), "h_oshots": g("h_oshots", 0), "h_osot": g("h_osot", 0),
        "a_poss": g("a_poss", 50), "a_shots": g("a_shots", 0), "a_sot": g("a_sot", 0),
        "a_bc": g("a_bc", 0), "a_xg": g("a_xg", 0.0), "a_goals": g("a_goals", 0),
        "a_xga": g("a_xga", 0.0), "a_oshots": g("a_oshots", 0), "a_osot": g("a_osot", 0),
        "home_prob": g("home_prob", 40), "draw_prob": g("draw_prob", 30),
        "home_odds": g("home_odds", "-"), "draw_odds": g("draw_odds", "-"),
        "away_odds": g("away_odds", "-"),
        "home_form": g("home_form", "4-3-3"), "away_form": g("away_form", "4-4-2"),
        "home_strategy": g("home_strategy", "积极进攻，争取早进球建立优势"),
        "away_strategy": g("away_strategy", "战略性防守，伺机反击"),
        "home_tactics": g("home_tactics", ["积极进攻", "控球主导", "两翼突破"]),
        "away_tactics": g("away_tactics", ["低位防守", "快速反击", "密集中路"]),
        "home_tactic_notes": g("home_tactic_notes",
                               ["通过两翼高速突破制造机会", "中路组织接应，定位球是额外威胁", "主动压制节奏"]),
        "away_tactic_notes": g("away_tactic_notes",
                               ["深度防守压缩空间", "断球后快速出球寻求反击", "专注防守纪律，不轻易前压"]),
        "home_mentality": g("home_mentality", []),
        "away_mentality": g("away_mentality", []),
        "metric_labels": g("metric_labels",
                           ["当前信心", "求胜紧迫", "进攻实力", "防守组织", "战术执行", "无压力感"]),
        "home_metrics": g("home_metrics", [7, 7, 7, 7, 7, 5]),
        "away_metrics": g("away_metrics", [6, 6, 6, 6, 6, 6]),
        # ── ① 落后逆转能力 ──
        "home_comeback": g("home_comeback", 5), "away_comeback": g("away_comeback", 5),
        "home_comeback_note": g("home_comeback_note", "暂无历史逆境数据"),
        "away_comeback_note": g("away_comeback_note", "暂无历史逆境数据"),
        # ── ② 进球组合 ──  [{name, prob}]
        "home_scorers": g("home_scorers", []),
        "away_scorers": g("away_scorers", []),
        # ── ④ 积分局势 ──  group_standings: [{team, flag, p, w, d, l, gf, ga, gd, pts}]
        "group_standings": g("group_standings", []),
        # 进球概率
        "over25": g("over25", 50), "over35": g("over35", 30),
        "away_score_prob": g("away_score_prob", 40), "handicap": g("handicap", 50),
        "handicap_label": g("handicap_label", "主队让球 -1.5 胜"),
        "likely_scores": g("likely_scores", []),
        # 可选手动覆盖大球阈值建议
        "over_threshold_label": g("over_threshold_label", None),
        "over_threshold_note": g("over_threshold_note", None),
        "home_risks": g("home_risks", []), "away_risks": g("away_risks", []),
        "verdict_rec": g("verdict_rec", ""), "verdict_score": g("verdict_score", "-"),
        "verdict_stars": g("verdict_stars", 3), "verdict_logic": g("verdict_logic", []),
    }
    m["away_prob"] = 100 - int(m["home_prob"]) - int(m["draw_prob"])
    return m


# ───────────────────────── HTML 小工具 ─────────────────────────
def esc(x) -> str:
    return _html.escape(str(x), quote=True)


def _f(x, default=0.0):
    try:
        return float(re.sub(r"[^0-9.\-]", "", str(x)) or default)
    except ValueError:
        return default


def badge(text, style="gray"):
    styles = {
        "green": "background:#eaf3de;color:#3b6d11", "amber": "background:#faeeda;color:#854f0b",
        "red": "background:#fdeaea;color:#a32d2d", "blue": "background:#e6f1fb;color:#185fa5",
        "purple": "background:#eeedfe;color:#3c3489", "gray": "background:#f0efe8;color:#555",
    }
    css = styles.get(style, styles["gray"])
    return (f'<span style="display:inline-block;font-size:11px;font-weight:600;'
            f'padding:2px 9px;border-radius:20px;margin:2px;{css}">{esc(text)}</span>')


def stat_bar(label, val, max_val, color="#1D9E75", suffix=""):
    num = _f(val)
    pct = min(num / max_val * 100, 100) if max_val else 0
    return (f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:5px">'
            f'<div style="font-size:11px;color:#888;width:88px;flex-shrink:0">{esc(label)}</div>'
            f'<div style="flex:1;height:5px;background:#eeede8;border-radius:3px;overflow:hidden">'
            f'<div style="width:{pct:.0f}%;height:100%;background:{color};border-radius:3px"></div></div>'
            f'<div style="font-size:11px;font-weight:600;width:40px;text-align:right;color:{color}">'
            f'{esc(val)}{esc(suffix)}</div></div>')


def xg_bar(xg_val, actual, xg_color, act_color, max_xg=3.0):
    xg_pct = min(_f(xg_val) / max_xg * 100, 100) if max_xg else 0
    act_pct = min(_f(actual) / max_xg * 100 * 0.5, 95)
    return (
        '<div style="margin-bottom:6px">'
        '<div style="font-size:9px;color:#999;margin-bottom:3px">xG 期望 vs 实际</div>'
        '<div style="display:flex;align-items:center;gap:6px;margin-bottom:3px">'
        '<div style="font-size:10px;color:#888;width:52px">期望 xG</div>'
        '<div style="flex:1;height:16px;background:#eeede8;border-radius:3px;overflow:hidden">'
        f'<div style="width:{xg_pct:.0f}%;height:100%;background:{xg_color};display:flex;'
        f'align-items:center;padding-left:6px"><span style="font-size:9px;font-weight:700;'
        f'color:#fff">xG {esc(xg_val)}</span></div></div></div>'
        '<div style="display:flex;align-items:center;gap:6px">'
        '<div style="font-size:10px;color:#888;width:52px">实际进球</div>'
        '<div style="flex:1;height:16px;background:#eeede8;border-radius:3px;overflow:hidden">'
        f'<div style="width:{max(act_pct,10):.0f}%;height:100%;background:{act_color};display:flex;'
        f'align-items:center;padding-left:6px"><span style="font-size:9px;font-weight:700;'
        f'color:#fff">{esc(actual)} 球</span></div></div></div></div>')


def grade_box(label, grade, note, color="#BA7517"):
    return (f'<div style="background:#f5f4f0;border-radius:8px;padding:8px 10px">'
            f'<div style="font-size:9px;color:#888;margin-bottom:2px">{esc(label)}</div>'
            f'<div style="font-size:18px;font-weight:700;color:{color}">{esc(grade)}</div>'
            f'<div style="font-size:9px;color:#888;margin-top:2px;line-height:1.3">{esc(note)}</div></div>')


def radar_row(label, hs, as_, home_color, away_color, home_flag, away_flag):
    hp, ap = hs * 10, as_ * 10
    return (
        '<div style="display:flex;align-items:center;gap:8px;margin-bottom:5px">'
        f'<div style="font-size:10px;color:#888;width:64px;text-align:right;flex-shrink:0">{esc(label)}</div>'
        '<div style="flex:1">'
        '<div style="display:flex;align-items:center;gap:4px;margin-bottom:2px">'
        f'<span style="font-size:11px;width:20px">{home_flag}</span>'
        '<div style="flex:1;height:4px;background:#eeede8;border-radius:2px">'
        f'<div style="width:{hp}%;height:100%;background:{home_color};border-radius:2px"></div></div>'
        f'<span style="font-size:10px;font-weight:600;color:{home_color};width:14px">{hs}</span></div>'
        '<div style="display:flex;align-items:center;gap:4px">'
        f'<span style="font-size:11px;width:20px">{away_flag}</span>'
        '<div style="flex:1;height:4px;background:#eeede8;border-radius:2px">'
        f'<div style="width:{ap}%;height:100%;background:{away_color};border-radius:2px"></div></div>'
        f'<span style="font-size:10px;font-weight:600;color:{away_color};width:14px">{as_}</span></div>'
        '</div></div>')


def score_chip(score, note, is_top=False):
    bg = "#eaf3de" if is_top else "#f5f4f0"
    border = "#1D9E75" if is_top else "#e2e0d8"
    color = "#3b6d11" if is_top else "#1c1c1a"
    return (f'<div style="background:{bg};border:1px solid {border};border-radius:8px;'
            f'padding:5px 10px;text-align:center;min-width:62px;display:inline-block;margin:3px">'
            f'<div style="font-size:13px;font-weight:700;color:{color}">{esc(score)}</div>'
            f'<div style="font-size:9px;color:#888;margin-top:1px">{esc(note)}</div></div>')


# ───────────── 优化 5：xG 实力/运气 自动标签 ─────────────
def xg_luck_label(goals, xg):
    """根据 实际进球 / xG 比值，自动判定真实实力 vs 运气成分。"""
    g, x = _f(goals), _f(xg)
    if x <= 0.05:
        return ("数据不足", "gray", "—")
    r = g / x
    if r >= 1.8:
        return (f"⚡ 运气成分高（{g:.0f}球 / xG{x:.2f}，效率超常，难持续）", "red", "运气")
    if r >= 1.25:
        return (f"↑ 略超预期（进球略多于机会质量）", "amber", "略超")
    if r >= 0.8:
        return (f"✓ 真实实力（进球与 xG 基本吻合，发挥稳定）", "green", "实力")
    if r >= 0.4:
        return (f"↓ 效率偏低（机会未充分兑现）", "amber", "低效")
    return (f"⚠ 严重低效（{g:.0f}球 / xG{x:.2f}，锋无力或运气差）", "red", "低效")


def last_match_panel(name, flag, result, poss, shots, sot, bc,
                     xg, goals, xga, oshots, osot, primary="#1D9E75"):
    out = [f'<div class="sec-label">{flag} {esc(name)} — 上轮 {esc(result)}</div>']
    out.append('<div class="sec-label" style="margin-top:8px">进攻数据</div>')
    out.append(stat_bar("控球率", f"{poss}", 100, primary, "%"))
    out.append(stat_bar("总射门", shots, 30, primary))
    out.append(stat_bar("射正", sot, 15, primary))
    out.append(stat_bar("大机会", bc, 8, primary))
    out.append(xg_bar(xg, goals, primary, "#3B6D11" if primary == "#1D9E75" else "#BA7517"))
    # 优化 5：实力/运气标签
    label, style, _tag = xg_luck_label(goals, xg)
    out.append(badge(label, style))

    out.append('<div class="sec-label" style="margin-top:10px">防守数据（对手）</div>')
    out.append(stat_bar("对手射门", oshots, 30, "#378ADD"))
    out.append(stat_bar("对手射正", osot, 15, "#378ADD"))
    out.append(stat_bar("对手xG", xga, 3.0, "#c0392b" if _f(xga) > 1.2 else "#378ADD"))

    xv, xav = _f(xg), _f(xga)
    atk = "A" if xv > 1.5 else ("B" if xv > 1.0 else ("C" if xv > 0.5 else "D"))
    dfd = "A" if xav < 0.5 else ("B" if xav < 1.0 else ("C" if xav < 1.5 else "D"))
    out.append('<div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:8px">')
    out.append(grade_box("进攻评分", atk, f"xG {xg}，{'机会质量高' if xv>1.2 else '有待提升'}",
                         "#1D9E75" if atk in "AB" else "#BA7517"))
    out.append(grade_box("防守评分", dfd, f"对手xG {xga}，{'防守稳健' if xav<1.0 else '承压较大'}",
                         "#1D9E75" if dfd in "AB" else ("#BA7517" if dfd == "C" else "#c0392b")))
    out.append('</div>')
    return "".join(out)


# ───────────── 优化 4：积分局势表 + 出线推演 ─────────────
def standings_table(rows, home_name, away_name):
    if not rows:
        return '<div style="font-size:11px;color:#aaa">（暂无积分表数据）</div>'
    def _key(r):
        return (int(r.get("pts", 0)), int(r.get("gd", 0)), int(r.get("gf", 0)))
    rows = sorted(rows, key=_key, reverse=True)
    head = ("<tr><th>#</th><th style='text-align:left'>球队</th><th>赛</th><th>胜</th>"
            "<th>平</th><th>负</th><th>进</th><th>失</th><th>净</th><th>积分</th></tr>")
    body = []
    for i, r in enumerate(rows, 1):
        team = r.get("team", "")
        hl = team in (home_name, away_name)
        bg = "background:#eaf3de;" if hl else ("background:#fafaf7;" if i <= 2 else "")
        nm = f'{r.get("flag","")} {esc(team)}'
        if hl:
            nm = f'<strong>{nm}</strong>'
        rk = ("#1D9E75" if i <= 2 else "#bbb")
        gd = int(r.get("gd", 0))
        body.append(
            f'<tr style="{bg}"><td style="color:{rk};font-weight:700">{i}</td>'
            f'<td style="text-align:left">{nm}</td>'
            f'<td>{r.get("p",0)}</td><td>{r.get("w",0)}</td><td>{r.get("d",0)}</td>'
            f'<td>{r.get("l",0)}</td><td>{r.get("gf",0)}</td><td>{r.get("ga",0)}</td>'
            f'<td>{"+" if gd>0 else ""}{gd}</td>'
            f'<td style="font-weight:700">{r.get("pts",0)}</td></tr>')
    return (f'<table class="standing">{head}{"".join(body)}</table>'
            f'<div style="font-size:9px;color:#aaa;margin-top:4px">绿色=本场对阵两队 · 前两名直接出线（深色行）</div>')


def scenario_card(flag, name, pts, klass, color):
    pts = int(pts)
    return (f'<div class="card {klass}"><div style="font-size:11px;font-weight:700;color:{color};'
            f'margin-bottom:8px">{flag} {esc(name)}（当前{pts}分）</div>'
            f'<div style="font-size:11px;line-height:1.8">'
            f'🟢 赢 → <strong>{pts+3}分</strong>：抢占出线主动<br>'
            f'🟡 平 → <strong>{pts+1}分</strong>：末轮仍需努力<br>'
            f'🔴 输 → <strong>{pts}分</strong>：出线压力骤增</div></div>')


# ───────────── 优化 3：大球阈值自动判断 ─────────────
# 调参记录（2026-06-20 回测）：
#   原逻辑只有 gap<=12 才提示谨慎，其余中等差距一律默认「过 2.5」。
#   实测 突尼斯 vs 日本（胜率 25/30/45，fav=45、gap=20）默认推过 2.5，
#   实际仅 1-1（2 球，走小），属误判；而 荷兰 5-1 瑞典（fav=50、gap=28）走大命中。
#   结论：当「没有明显强队」(fav<52) 且差距中等 (gap<=26) 时，进球数方差大、
#   常陷入低进球缠斗，应转为谨慎/偏小，而非默认偏大。新增该判断带（见下）。
def over_recommendation(hp, ap, manual_label=None, manual_note=None):
    hp, ap = int(hp), int(ap)
    fav, gap = max(hp, ap), abs(hp - ap)
    if manual_label:
        return (manual_label, manual_note or "", "#1D9E75", "green")
    if fav >= 62 and gap >= 42:
        return ("建议主推「过 3.5 球」", "实力悬殊，强队多点开花概率高，保守过 2.5 价值偏低", "#1D9E75", "green")
    if fav >= 55 and gap >= 28:
        return ("建议「过 2.5 球」（可博过 3.5）", "存在明显实力差，偏向大球", "#1D9E75", "green")
    if gap <= 12:
        return ("大球需谨慎（≤2.5 偏稳）", "两队实力接近，易陷入低进球缠斗", "#BA7517", "amber")
    if fav < 52 and gap <= 26:
        return ("大球需谨慎（倾向小球 ≤2.5）", "无明显强队、差距中等，进球数方差大、易走小（2026-06-20 回测加入）", "#BA7517", "amber")
    return ("建议「过 2.5 球」", "中等实力差，正常大球预期", "#1D9E75", "green")


# ───────────── 优化 2：进球组合 ─────────────
def scorer_block(scorers, color):
    if not scorers:
        return '<div style="font-size:11px;color:#aaa">（暂无进球组合数据）</div>'
    out = []
    for s in scorers:
        name = esc(s.get("name", ""))
        prob = int(s.get("prob", 0))
        out.append(
            f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:6px">'
            f'<div style="font-size:11px;width:96px;flex-shrink:0">{name}</div>'
            f'<div style="flex:1;height:6px;background:#eeede8;border-radius:3px;overflow:hidden">'
            f'<div style="width:{min(prob,100)}%;height:100%;background:{color};border-radius:3px"></div></div>'
            f'<div style="font-size:11px;font-weight:700;color:{color};width:34px;text-align:right">{prob}%</div></div>')
    return "".join(out)


def mentality_block(factors):
    if not factors:
        return '<div style="font-size:11px;color:#aaa">（暂无心态数据）</div>'
    out = []
    for f in factors:
        title, desc, quote = esc(f.get("title", "")), esc(f.get("desc", "")), f.get("quote", "")
        q = "" if not quote else f'<div class="quote">{esc(quote)}</div>'
        out.append(f'<div style="border-left:2px solid #e2e0d8;padding-left:8px;margin-bottom:8px">'
                   f'<div style="font-size:9px;font-weight:700;color:#999">{title}</div>'
                   f'<div style="font-size:11px;color:#444;margin-top:2px;line-height:1.5">{desc}</div>{q}</div>')
    return "".join(out)


def comeback_card(flag, name, score, note, color):
    score = int(score)
    pct = min(score * 10, 100)
    if score >= 8:
        tag, tg = "逆境钢铁意志", "green"
    elif score >= 6:
        tag, tg = "尚可一搏", "amber"
    elif score >= 4:
        tag, tg = "落后易崩", "amber"
    else:
        tag, tg = "落后基本无力", "red"
    return (f'<div class="card"><div style="font-size:12px;font-weight:700;margin-bottom:8px">{flag} {esc(name)}</div>'
            f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:6px">'
            f'<div style="font-size:10px;color:#888;width:72px;flex-shrink:0">落后逆转力</div>'
            f'<div style="flex:1;height:8px;background:#eeede8;border-radius:4px;overflow:hidden">'
            f'<div style="width:{pct}%;height:100%;background:{color};border-radius:4px"></div></div>'
            f'<div style="font-size:13px;font-weight:700;color:{color};width:38px;text-align:right">{score}/10</div></div>'
            f'<div style="margin-bottom:6px">{badge(tag, tg)}</div>'
            f'<div style="font-size:11px;color:#555;line-height:1.6">{esc(note)}</div></div>')


def risk_list(risks):
    if not risks:
        return '<div style="font-size:11px;color:#aaa">（暂无风险点数据）</div>'
    out = []
    for r in risks:
        out.append('<div style="display:flex;gap:6px;margin-bottom:5px;font-size:11px">'
                   '<div style="width:5px;height:5px;border-radius:50%;background:#bbb;'
                   'margin-top:6px;flex-shrink:0"></div>'
                   f'<div>{esc(r)}</div></div>')
    return "".join(out)


# ───────────────────────── 样式 ─────────────────────────
CSS = """
*{box-sizing:border-box}
body{background:#f4f3ef;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif;color:#1c1c1a;margin:0;padding:24px}
.wrap{max-width:1080px;margin:0 auto}
h1.title{font-size:26px;margin:0 0 4px}
.sub{font-size:13px;color:#888;margin-bottom:16px}
h3.sec{font-size:15px;margin:22px 0 12px;border-top:1px solid #e2e0d8;padding-top:18px}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:14px}
.grid3{display:grid;grid-template-columns:1fr 1fr 1fr;gap:14px}
.grid4{display:grid;grid-template-columns:repeat(4,1fr);gap:14px}
.card{background:#fff;border:1px solid #e2e0d8;border-radius:12px;padding:16px 18px;margin-bottom:4px}
.card-amber{background:#fdf6e8;border:1px solid rgba(186,117,23,.25)}
.card-teal{background:#e8f8f2;border:1px solid rgba(29,158,117,.3)}
.sec-label{font-size:10px;font-weight:700;color:#999;text-transform:uppercase;letter-spacing:.07em;margin-bottom:6px}
.quote{background:#f5f4f0;border-left:3px solid #d0cec8;padding:5px 10px;border-radius:0 6px 6px 0;font-style:italic;color:#666;font-size:12px;margin-top:6px;line-height:1.5}
.foot{font-size:11px;color:#999;margin-top:24px;border-top:1px solid #e2e0d8;padding-top:12px}
table.standing{width:100%;border-collapse:collapse;font-size:12px;text-align:center}
table.standing th{font-size:10px;color:#999;font-weight:600;padding:5px 6px;border-bottom:1px solid #e0dfd8}
table.standing td{padding:7px 6px;border-bottom:1px solid #f0efe8}
.note{background:#fff;border:1px solid #e2e0d8;border-radius:10px;padding:10px 14px;display:flex;align-items:center;gap:12px;margin-bottom:4px}
@media(max-width:720px){.grid2,.grid3,.grid4{grid-template-columns:1fr}}
"""


def render_match(match: dict) -> str:
    m = _d(match)
    H, A = "#1D9E75", "#BA7517"
    P = []
    P.append('<div style="margin-bottom:10px"><a href="../index.html" style="font-size:12px;color:#888;text-decoration:none">← 返回总览</a></div>')
    P.append(f'<h1 class="title">⚽ {m["home_flag"]}{esc(m["home_name"])} vs {m["away_flag"]}{esc(m["away_name"])}</h1>')
    P.append(f'<div class="sub">{esc(m["match_group"])} · {esc(m["match_date"])} · {esc(m["match_venue"])}</div>')

    # 头部
    P.append('<div class="grid3">')
    P.append(f'<div class="card" style="text-align:center"><div style="font-size:40px">{m["home_flag"]}</div>'
             f'<div style="font-size:18px;font-weight:700;margin-top:6px">{esc(m["home_name"])}</div>'
             f'<div style="font-size:11px;color:#888;margin-top:4px">{esc(m["home_prev"])} · <strong>{esc(m["home_pts"])}分</strong></div></div>')
    P.append('<div style="text-align:center;padding-top:24px"><div style="font-size:24px;color:#aaa;font-weight:500">VS</div>'
             f'<div style="font-size:10px;color:#888;margin-top:8px;line-height:1.6">{esc(m["match_group"])}<br>{esc(m["match_date"])}<br>{esc(m["match_venue"])}</div></div>')
    P.append(f'<div class="card" style="text-align:center"><div style="font-size:40px">{m["away_flag"]}</div>'
             f'<div style="font-size:18px;font-weight:700;margin-top:6px">{esc(m["away_name"])}</div>'
             f'<div style="font-size:11px;color:#888;margin-top:4px">{esc(m["away_prev"])} · <strong>{esc(m["away_pts"])}分</strong></div></div>')
    P.append('</div>')

    # ① 上轮表现（含 xG 实力/运气标签）
    P.append('<h3 class="sec">① 上轮表现深度分析 — 进攻 / 防守 / xG 实力·运气判定</h3>')
    P.append('<div class="grid2"><div class="card">')
    P.append(last_match_panel(m["home_name"], m["home_flag"], m["home_prev"],
                              m["h_poss"], m["h_shots"], m["h_sot"], m["h_bc"],
                              m["h_xg"], m["h_goals"], m["h_xga"], m["h_oshots"], m["h_osot"], H))
    P.append('</div><div class="card">')
    P.append(last_match_panel(m["away_name"], m["away_flag"], m["away_prev"],
                              m["a_poss"], m["a_shots"], m["a_sot"], m["a_bc"],
                              m["a_xg"], m["a_goals"], m["a_xga"], m["a_oshots"], m["a_osot"], A))
    P.append('</div></div>')

    # ② 胜负概率
    P.append('<h3 class="sec">② 胜负概率 &amp; 参考赔率</h3>')
    P.append('<div class="grid3">')
    for prob, lbl, odds, clr in [
        (m["home_prob"], f'{m["home_flag"]} {esc(m["home_name"])}赢', m["home_odds"], H),
        (m["draw_prob"], "平局", m["draw_odds"], "#888"),
        (m["away_prob"], f'{m["away_flag"]} {esc(m["away_name"])}赢', m["away_odds"], A)]:
        P.append(f'<div class="card" style="text-align:center"><div style="font-size:32px;font-weight:700;color:{clr}">{prob}%</div>'
                 f'<div style="font-size:11px;color:#888;margin-top:4px">{lbl}</div>'
                 f'<div style="font-size:12px;font-weight:600;margin-top:4px">赔率 {esc(odds)}</div></div>')
    P.append('</div>')
    P.append(f'<div style="display:flex;height:8px;border-radius:4px;overflow:hidden;gap:2px;margin-top:10px">'
             f'<div style="flex:{m["home_prob"]};background:#1D9E75;border-radius:3px 0 0 3px"></div>'
             f'<div style="flex:{m["draw_prob"]};background:#ccc"></div>'
             f'<div style="flex:{max(m["away_prob"],0)};background:#BA7517;border-radius:0 3px 3px 0"></div></div>')

    # ③ 积分局势表（标配）+ 出线推演
    P.append('<h3 class="sec">③ 组内积分局势 &amp; 出线场景推演</h3>')
    P.append(f'<div class="card">{standings_table(m["group_standings"], m["home_name"], m["away_name"])}</div>')
    P.append('<div class="grid2" style="margin-top:10px">')
    P.append(scenario_card(m["home_flag"], m["home_name"], m["home_pts"], "card-teal", "#0F6E56"))
    P.append(scenario_card(m["away_flag"], m["away_name"], m["away_pts"], "card-amber", "#854F0B"))
    P.append('</div>')

    # ④ 阵型战术
    P.append('<h3 class="sec">④ 阵型 &amp; 战术策略</h3><div class="grid2">')
    for name, flag, form, tactics, notes, strat, clr, bg, fg in [
        (m["home_name"], m["home_flag"], m["home_form"], m["home_tactics"], m["home_tactic_notes"],
         m["home_strategy"], "#3b6d11", "#eaf3de", "#3b6d11"),
        (m["away_name"], m["away_flag"], m["away_form"], m["away_tactics"], m["away_tactic_notes"],
         m["away_strategy"], "#854f0b", "#faeeda", "#854f0b")]:
        tg = "".join(badge(t, "green" if clr == "#3b6d11" else "amber") for t in tactics)
        nt = "<br>".join("› " + esc(n) for n in notes)
        P.append(f'<div class="card"><div style="font-size:12px;font-weight:700;margin-bottom:6px">{flag} {esc(name)}</div>'
                 f'<div style="display:inline-block;background:{bg};color:{fg};font-size:12px;font-weight:700;'
                 f'padding:2px 10px;border-radius:8px;margin-bottom:8px">{esc(form)}</div>'
                 f'<div style="margin-bottom:8px">{tg}</div>'
                 f'<p style="font-size:11px;color:#555;line-height:1.7">{nt}</p>'
                 f'<div style="margin-top:8px;font-size:11px;font-weight:700;color:{clr}">今日策略：{esc(strat)}</div></div>')
    P.append('</div>')

    # ⑤ 心态
    P.append('<h3 class="sec">⑤ 球员心态 &amp; 决心</h3><div class="grid2">')
    P.append(f'<div class="card"><div class="sec-label">{m["home_flag"]} {esc(m["home_name"])} — 赛前心态</div>{mentality_block(m["home_mentality"])}</div>')
    P.append(f'<div class="card"><div class="sec-label">{m["away_flag"]} {esc(m["away_name"])} — 赛前心态</div>{mentality_block(m["away_mentality"])}</div>')
    P.append('</div>')

    # ⑥ 落后逆转能力（新维度）
    P.append('<h3 class="sec">⑥ 落后逆转能力 — 逆境/落后翻盘评估</h3><div class="grid2">')
    P.append(comeback_card(m["home_flag"], m["home_name"], m["home_comeback"], m["home_comeback_note"], H))
    P.append(comeback_card(m["away_flag"], m["away_name"], m["away_comeback"], m["away_comeback_note"], A))
    P.append('</div>')

    # ⑦ 心态指标
    P.append('<h3 class="sec">⑦ 心态指标对比（满分10）</h3><div class="card">')
    labels, hm, am = m["metric_labels"], m["home_metrics"], m["away_metrics"]
    for i, lbl in enumerate(labels):
        hs = hm[i] if i < len(hm) else 0
        as_ = am[i] if i < len(am) else 0
        P.append(radar_row(lbl, hs, as_, H, A, m["home_flag"], m["away_flag"]))
    P.append('</div>')

    # ⑧ 进球概率 + 大球阈值自动建议 + 进球组合
    P.append('<h3 class="sec">⑧ 进球数量概率 &amp; 进球组合</h3>')
    ov_label, ov_note, ov_color, ov_style = over_recommendation(
        m["home_prob"], m["away_prob"], m["over_threshold_label"], m["over_threshold_note"])
    P.append(f'<div class="note" style="border-color:{ov_color}"><div style="font-size:22px">🎯</div>'
             f'<div><div style="font-size:13px;font-weight:700;color:{ov_color}">大球阈值自动建议：{esc(ov_label)}</div>'
             f'<div style="font-size:11px;color:#888;margin-top:2px">{esc(ov_note)}</div></div></div>')
    P.append('<div class="grid4">')
    for lbl, val, clr in [("过 2.5 球", m["over25"], H), ("过 3.5 球", m["over35"], H),
                          (f'{esc(m["away_name"])}进球', m["away_score_prob"], A),
                          (esc(m["handicap_label"]), m["handicap"], "#378ADD")]:
        P.append(f'<div class="card" style="text-align:center"><div style="font-size:10px;color:#888;margin-bottom:4px">{lbl}</div>'
                 f'<div style="font-size:26px;font-weight:700;color:{clr}">{val}%</div></div>')
    P.append('</div>')
    scores = m["likely_scores"]
    if scores:
        P.append('<div style="margin-top:10px"><div class="sec-label">最可能比分</div>')
        for i, sc in enumerate(scores):
            P.append(score_chip(sc, "最高概率" if i == 0 else "次选", i == 0))
        P.append('</div>')
    # 进球组合
    P.append('<div class="grid2" style="margin-top:12px">')
    P.append(f'<div class="card"><div class="sec-label">{m["home_flag"]} {esc(m["home_name"])} 进球组合</div>{scorer_block(m["home_scorers"], H)}</div>')
    P.append(f'<div class="card"><div class="sec-label">{m["away_flag"]} {esc(m["away_name"])} 进球组合</div>{scorer_block(m["away_scorers"], A)}</div>')
    P.append('</div>')

    # ⑨ 风险点
    P.append('<h3 class="sec">⑨ 风险点</h3><div class="grid2">')
    P.append(f'<div class="card"><div class="sec-label">⚠ {m["home_flag"]} {esc(m["home_name"])} 风险点</div>{risk_list(m["home_risks"])}</div>')
    P.append(f'<div class="card"><div class="sec-label">⚠ {m["away_flag"]} {esc(m["away_name"])} 风险点</div>{risk_list(m["away_risks"])}</div>')
    P.append('</div>')

    # ⑩ 综合推荐
    P.append('<h3 class="sec">⑩ 综合推荐</h3>')
    stars = "⭐" * int(m["verdict_stars"])
    logic = "<br>".join(esc(x) for x in m["verdict_logic"]) if m["verdict_logic"] else ""
    P.append(f'<div class="card card-teal" style="display:grid;grid-template-columns:1fr auto;gap:16px;align-items:center">'
             f'<div><div style="font-size:10px;color:#0F6E56;margin-bottom:4px">综合推荐</div>'
             f'<div style="font-size:16px;font-weight:700;color:#0F6E56">{esc(m["verdict_rec"])}</div>'
             f'<div style="font-size:11px;color:#0F6E56;margin-top:6px;line-height:1.7">{logic}</div></div>'
             f'<div style="text-align:right"><div style="font-size:10px;color:#0F6E56;margin-bottom:2px">最可能比分</div>'
             f'<div style="font-size:36px;font-weight:700;color:#0F6E56">{esc(m["verdict_score"])}</div>'
             f'<div style="font-size:12px;color:#0F6E56;margin-top:4px">把握度 {stars}</div></div></div>')

    P.append('<div class="foot">⚠ 以上分析由模型基于公开数据自动生成，仅供参考。体育赛事充满不确定性，请理性博彩，量力而行。</div>')

    body = "\n".join(P)
    return (f'<!DOCTYPE html><html lang="zh"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>{esc(m["home_name"])} vs {esc(m["away_name"])} — 赛前分析</title>'
            f'<style>{CSS}</style></head><body><div class="wrap">{body}</div></body></html>')


# ───────────────────────── 文件名 / 索引 ─────────────────────────
def safe_name(s: str) -> str:
    s = re.sub(r'[\\/:*?"<>|]', "", str(s)).strip()
    return re.sub(r"\s+", "_", s) or "match"


def build_index(matches, date_str):
    rows = []
    for m in matches:
        mm = _d(m)
        fn = f'{safe_name(mm["home_name"])}_vs_{safe_name(mm["away_name"])}.html'
        rows.append(f'<a href="{esc(fn)}" style="display:block;background:#fff;border:1px solid #e2e0d8;'
                    f'border-radius:10px;padding:14px 16px;margin-bottom:10px;text-decoration:none;color:#1c1c1a">'
                    f'<div style="font-size:15px;font-weight:700">{mm["home_flag"]} {esc(mm["home_name"])} '
                    f'<span style="color:#aaa">vs</span> {mm["away_flag"]} {esc(mm["away_name"])}</div>'
                    f'<div style="font-size:12px;color:#888;margin-top:4px">{esc(mm["match_group"])} · '
                    f'{esc(mm["match_date"])} · {esc(mm["match_venue"])}</div>'
                    f'<div style="font-size:12px;color:#0F6E56;margin-top:6px">推荐：{esc(mm["verdict_rec"]) or "—"} '
                    f'｜ 预测 {esc(mm["verdict_score"])}</div></a>')
    return (f'<!DOCTYPE html><html lang="zh"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>{esc(date_str)} 世界杯赛前分析</title><style>{CSS}</style></head><body><div class="wrap">'
            f'<div style="margin-bottom:10px"><a href="../index.html" style="font-size:12px;color:#888;text-decoration:none">← 返回总览</a></div>'
            f'<h1 class="title">⚽ {esc(date_str)} 世界杯赛前分析</h1>'
            f'<div class="sub">共 {len(matches)} 场比赛</div>{"".join(rows)}'
            f'<div class="foot">⚠ 自动生成，仅供参考。请理性博彩。</div></div></body></html>')


SAMPLE = [{
    "home_flag": "🇧🇷", "home_name": "巴西", "home_prev": "1-1 🤝 平摩洛哥", "home_pts": 1,
    "away_flag": "🇭🇹", "away_name": "海地", "away_prev": "0-1 ❌ 负苏格兰", "away_pts": 0,
    "match_group": "C组 第2轮", "match_date": "6月20日 · 北京时间 08:30",
    "match_venue": "费城 Lincoln Financial Field",
    "h_poss": 51, "h_shots": 12, "h_sot": 5, "h_bc": 1, "h_xg": 1.26, "h_goals": 1,
    "h_xga": 1.40, "h_oshots": 16, "h_osot": 5,
    "a_poss": 54, "a_shots": 15, "a_sot": 3, "a_bc": 0, "a_xg": 1.05, "a_goals": 0,
    "a_xga": 1.05, "a_oshots": 9, "a_osot": 2,
    "home_prob": 87, "draw_prob": 9, "home_odds": "-650", "draw_odds": "+900", "away_odds": "+2800",
    "home_form": "4-2-3-1", "away_form": "4-4-2",
    "home_comeback": 8, "home_comeback_note": "桑巴军团技术底蕴深厚，落后时具备凭借个人能力逆转的实力，但本届心态略不稳。",
    "away_comeback": 3, "away_comeback_note": "整体实力有限，一旦落后很难组织有效反扑。",
    "home_mentality": [{"title": "反弹压力", "desc": "被摩洛哥压制后需要一场令人信服的大胜",
                        "quote": "球队必须做得更多。 — Ancelotti"}],
    "away_mentality": [{"title": "无压力释放", "desc": "输球是预期结果，海地可打出最自由的状态",
                        "quote": "敢于梦想，一切都是惊喜。 — Migne"}],
    "home_metrics": [7, 10, 9, 7, 8, 4], "away_metrics": [8, 6, 3, 8, 7, 10],
    "over25": 72, "over35": 52, "away_score_prob": 28, "handicap": 58, "handicap_label": "巴西让球 -2.5 胜",
    "likely_scores": ["3-0", "2-0", "4-0", "3-1"],
    "home_scorers": [{"name": "维尼修斯", "prob": 55}, {"name": "罗德里戈", "prob": 42}, {"name": "拉菲尼亚", "prob": 38}],
    "away_scorers": [{"name": "皮埃尔", "prob": 14}, {"name": "杜克斯", "prob": 11}],
    "group_standings": [
        {"team": "苏格兰", "flag": "🏴", "p": 1, "w": 1, "d": 0, "l": 0, "gf": 1, "ga": 0, "gd": 1, "pts": 3},
        {"team": "摩洛哥", "flag": "🇲🇦", "p": 1, "w": 0, "d": 1, "l": 0, "gf": 1, "ga": 1, "gd": 0, "pts": 1},
        {"team": "巴西", "flag": "🇧🇷", "p": 1, "w": 0, "d": 1, "l": 0, "gf": 1, "ga": 1, "gd": 0, "pts": 1},
        {"team": "海地", "flag": "🇭🇹", "p": 1, "w": 0, "d": 0, "l": 1, "gf": 0, "ga": 1, "gd": -1, "pts": 0}],
    "home_risks": ["上轮心理问题未彻底解决", "过度急于进球，防线暴露被反击"],
    "away_risks": ["进攻转化率极低，上轮15射无进", "面对顶级速度两翼，防线压力极大"],
    "verdict_rec": "买巴西赢 · 过 3.5 球", "verdict_score": "3-0", "verdict_stars": 4,
    "verdict_logic": ["巴西在反弹压力下对阵最弱对手，动力最强",
                      "实力悬殊，自动建议上调至过 3.5 球", "海地落后逆转能力极弱，难以追分"],
}]


def main():
    ap = argparse.ArgumentParser(description="2026 世界杯赛前分析 静态 HTML 生成器 v2")
    ap.add_argument("json", nargs="?", help="比赛数据 JSON 文件（单场 dict 或多场 list）")
    ap.add_argument("--outdir", default=".", help="输出根目录（其下创建日期文件夹）")
    ap.add_argument("--date", default=None, help="日期文件夹名，默认本地当天 YYYY-MM-DD")
    ap.add_argument("--sample", action="store_true", help="忽略输入，使用内置示例数据")
    args = ap.parse_args()

    if args.sample or not args.json:
        matches = SAMPLE
    else:
        with open(args.json, "r", encoding="utf-8") as f:
            data = json.load(f)
        matches = data if isinstance(data, list) else [data]

    date_str = args.date or _dt.date.today().strftime("%Y-%m-%d")
    target = os.path.join(args.outdir, date_str)
    os.makedirs(target, exist_ok=True)

    written = []
    for m in matches:
        mm = _d(m)
        fn = f'{safe_name(mm["home_name"])}_vs_{safe_name(mm["away_name"])}.html'
        path = os.path.join(target, fn)
        with open(path, "w", encoding="utf-8") as f:
            f.write(render_match(m))
        written.append(path)

    idx = os.path.join(target, "index.html")
    with open(idx, "w", encoding="utf-8") as f:
        f.write(build_index(matches, date_str))
    written.append(idx)

    print(f"✅ 已在 {target} 生成 {len(matches)} 场分析 + 索引：")
    for p in written:
        print("  -", p)


if __name__ == "__main__":
    main()
# v2 — 5 项优化：落后逆转 / 进球组合 / 大球阈值自动 / 积分表标配 / xG实力运气标签

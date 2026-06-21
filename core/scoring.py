#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""纯评分逻辑（无 streamlit 依赖，可单测）。与 backtest.py 保持一致。"""

import re

__all__ = ["norm", "predicted_outcome", "actual_outcome", "brier", "eval_handicap",
           "verdict_hit", "score_match", "rate", "aggregate", "parse_score", "strength_tier"]


def norm(s):
    return re.sub(r"\s+", "", str(s)).lower()


def parse_score(s):
    """'2-1' / '2:1' -> (2, 1)；解析失败返回 None。"""
    m = re.match(r"\s*(\d+)\s*[-:]\s*(\d+)\s*", str(s))
    return (int(m.group(1)), int(m.group(2))) if m else None


def strength_tier(hp, dp, ap):
    """按头号选择置信度把对阵分层：悬殊 / 中等 / 接近。用于分层命中率统计。"""
    conf = max(hp, dp, ap)
    if conf >= 70:
        return "悬殊"
    if conf >= 55:
        return "中等"
    return "接近"


def predicted_outcome(hp, dp, ap):
    trio = [("H", hp), ("D", dp), ("A", ap)]
    trio.sort(key=lambda t: t[1], reverse=True)
    return trio[0][0]


def actual_outcome(h, a):
    return "H" if h > a else ("A" if a > h else "D")


def brier(hp, dp, ap, outcome):
    p = [hp / 100.0, dp / 100.0, ap / 100.0]
    y = {"H": [1, 0, 0], "D": [0, 1, 0], "A": [0, 0, 1]}[outcome]
    return sum((p[i] - y[i]) ** 2 for i in range(3))


def eval_handicap(label, home_name, away_name, h, a):
    if not label:
        return None
    nums = re.findall(r"[-+]?\d+(?:\.\d+)?", label)
    if not nums:
        return None
    line = abs(float(nums[0]))
    if norm(home_name) and norm(home_name) in norm(label):
        margin = h - a
    elif norm(away_name) and norm(away_name) in norm(label):
        margin = a - h
    else:
        return None
    if margin > line:
        return True
    if margin < line:
        return False
    return None


def verdict_hit(rec, home_name, away_name, outcome, total, h, a):
    if not rec:
        return None
    hits = []
    if "不败" in rec:
        if norm(home_name) in norm(rec):
            hits.append(outcome in ("H", "D"))
        elif norm(away_name) in norm(rec):
            hits.append(outcome in ("A", "D"))
    elif "赢" in rec or "胜" in rec:
        if norm(home_name) in norm(rec):
            hits.append(outcome == "H")
        elif norm(away_name) in norm(rec):
            hits.append(outcome == "A")
    if "过3.5" in rec or "过 3.5" in rec:
        hits.append(total >= 4)
    elif "过2.5" in rec or "过 2.5" in rec or "大球" in rec:
        hits.append(total >= 3)
    if "小球" in rec:
        hits.append(total <= 2)
    if not hits:
        return None
    return all(hits)


def score_match(pred, h, a):
    hp = int(pred.get("home_prob", 0))
    dp = int(pred.get("draw_prob", 0))
    ap = int(pred.get("away_prob", 100 - hp - dp))
    hn, an = pred.get("home_name", ""), pred.get("away_name", "")
    out = actual_outcome(h, a)
    pout = predicted_outcome(hp, dp, ap)
    total = h + a
    likely = [str(s) for s in pred.get("likely_scores", [])]
    vscore = str(pred.get("verdict_score", ""))
    actual_str = f"{h}-{a}"
    # 比分误差（MAE）：优先用 verdict_score，缺失则用 likely_scores 第一个
    ps = parse_score(vscore) or (parse_score(likely[0]) if likely else None)
    if ps is not None:
        ph, pa = ps
        score_mae = (abs(ph - h) + abs(pa - a)) / 2.0   # 每场平均每队进球误差
        total_err = abs((ph + pa) - total)               # 总进球数误差
        margin_err = abs((ph - pa) - (h - a))            # 净胜球误差
    else:
        score_mae = total_err = margin_err = None
    r = {
        "actual": actual_str, "total_goals": total,
        "pred_1x2": pout, "act_1x2": out, "hit_1x2": pout == out,
        "over25_pred": int(pred.get("over25", 50)) >= 50, "over25_act": total >= 3,
        "over35_pred": int(pred.get("over35", 30)) >= 50, "over35_act": total >= 4,
        "exact_hit": (vscore == actual_str) or (actual_str in likely),
        "btts_act": h > 0 and a > 0,
        "handicap_hit": eval_handicap(pred.get("handicap_label"), hn, an, h, a),
        "verdict_hit": verdict_hit(pred.get("verdict_rec", ""), hn, an, out, total, h, a),
        "brier": round(brier(hp, dp, ap, out), 3),
        "score_mae": score_mae, "total_err": total_err, "margin_err": margin_err,
        "fav_conf": max(hp, dp, ap), "tier": strength_tier(hp, dp, ap),
    }
    r["over25_hit"] = r["over25_pred"] == r["over25_act"]
    r["over35_hit"] = r["over35_pred"] == r["over35_act"]
    return r


def rate(vals):
    vals = [v for v in vals if v is not None]
    return (sum(1 for v in vals if v) / len(vals)) if vals else None


def _mean(vals):
    vals = [v for v in vals if v is not None]
    return (sum(vals) / len(vals)) if vals else None


def aggregate(scored_list, total, days):
    s = scored_list
    n = len(s)
    by_tier = {}
    for t in ("悬殊", "中等", "接近"):
        sub = [x for x in s if x.get("tier") == t]
        if sub:
            by_tier[t] = {"n": len(sub), "1x2": rate([x["hit_1x2"] for x in sub]),
                          "score_mae": _mean([x.get("score_mae") for x in sub])}
    return {
        "graded": n, "total": total, "days": days,
        "1x2": rate([x["hit_1x2"] for x in s]),
        "over25": rate([x["over25_hit"] for x in s]),
        "over35": rate([x["over35_hit"] for x in s]),
        "handicap": rate([x["handicap_hit"] for x in s]),
        "verdict": rate([x["verdict_hit"] for x in s]),
        "exact": rate([x["exact_hit"] for x in s]),
        "brier": (sum(x["brier"] for x in s) / n) if n else None,
        "score_mae": _mean([x.get("score_mae") for x in s]),
        "total_mae": _mean([x.get("total_err") for x in s]),
        "over_bias": ((sum(1 for x in s if x["over25_pred"]) -
                       sum(1 for x in s if x["over25_act"])) / n) if n else None,
        "by_tier": by_tier,
    }

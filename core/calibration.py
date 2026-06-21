#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""校准追踪：对数损失(log-loss) 与 置信度校准分桶。无 streamlit 依赖。
records 来自 core.data.all_records()：每条含 p(预测) 与 scored(评分或None)。"""

import math

_EPS = 1e-9


def _probs(p):
    hp = int(p.get("home_prob", 0)) / 100.0
    dp = int(p.get("draw_prob", 0)) / 100.0
    ap = max(1.0 - hp - dp, 0.0)
    return {"H": hp, "D": dp, "A": ap}


def log_loss(records):
    """多分类对数损失（越低越好）。只统计已评分场次。"""
    vals = []
    for r in records:
        sc = r.get("scored")
        if not sc:
            continue
        prob = _probs(r["p"]).get(sc["act_1x2"], 0.0)
        vals.append(-math.log(max(prob, _EPS)))
    return (sum(vals) / len(vals)) if vals else None


def calibration_buckets(records, nbins=5):
    """按"头号选择的置信度"分桶，对比平均置信度 vs 实际命中率。
    校准良好时两者应接近。返回按桶升序的 list[dict]。"""
    buckets = {}
    for r in records:
        sc = r.get("scored")
        if not sc:
            continue
        pr = _probs(r["p"])
        conf = max(pr.values())          # 头号选择的概率
        b = min(int(conf * nbins), nbins - 1)
        buckets.setdefault(b, []).append((conf, 1 if sc["hit_1x2"] else 0))
    rows = []
    for b in range(nbins):
        items = buckets.get(b, [])
        if not items:
            continue
        lo, hi = b * 100 // nbins, (b + 1) * 100 // nbins
        rows.append({
            "置信区间": f"{lo}-{hi}%",
            "场次": len(items),
            "平均置信度": round(sum(c for c, _ in items) / len(items) * 100),
            "实际命中率": round(sum(h for _, h in items) / len(items) * 100),
        })
    return rows


def summary(records):
    rows = calibration_buckets(records)
    # 平均校准误差 ECE（加权 |置信-命中|）
    n = sum(x["场次"] for x in rows)
    ece = (sum(x["场次"] * abs(x["平均置信度"] - x["实际命中率"]) for x in rows) / n) if n else None
    return {"log_loss": log_loss(records), "ece": ece, "buckets": rows, "graded": n}

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""数据加载层（无 streamlit 依赖，便于单测）。读取 data/ 下各日期文件夹的 JSON。"""

import csv
import json
import re
from pathlib import Path

from .scoring import norm, score_match, aggregate

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def safe_name(s):
    s = re.sub(r'[\\/:*?"<>|]', "", str(s)).strip()
    return re.sub(r"\s+", "_", s) or "match"


def list_dates(data_dir=DATA_DIR):
    if not Path(data_dir).exists():
        return []
    out = []
    for p in sorted(Path(data_dir).iterdir()):
        if p.is_dir() and DATE_RE.match(p.name) and (p / "predictions.json").exists():
            out.append(p.name)
    return out


def _load_results(path):
    """返回 {(norm(home), norm(away)): (h, a)}，跳过空结果。"""
    out = {}
    if not Path(path).exists():
        return out
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict):
        for k, v in data.items():
            if not isinstance(v, dict):
                continue
            h, a = v.get("h"), v.get("a")
            if h is None or a is None:
                continue
            parts = re.split(r"\s*vs\s*|\s*VS\s*|\s*-\s*", k)
            if len(parts) >= 2:
                out[(norm(parts[0]), norm(parts[1]))] = (int(h), int(a))
    elif isinstance(data, list):
        for v in data:
            h, a = v.get("h"), v.get("a")
            if h is None or a is None:
                continue
            out[(norm(v.get("home_name", "")), norm(v.get("away_name", "")))] = (int(h), int(a))
    return out


def load_day(date, data_dir=DATA_DIR):
    """返回 (preds:list, results:dict)。"""
    d = Path(data_dir) / date
    with open(d / "predictions.json", "r", encoding="utf-8") as f:
        preds = json.load(f)
    if isinstance(preds, dict):
        preds = [preds]
    results = _load_results(d / "results.json")
    return preds, results


def all_records(data_dir=DATA_DIR):
    """展平所有日期的单场记录。每条含 date / p / actual / scored / match_id。"""
    recs = []
    for date in list_dates(data_dir):
        preds, results = load_day(date, data_dir)
        for i, p in enumerate(preds):
            hn, an = p.get("home_name", ""), p.get("away_name", "")
            actual = results.get((norm(hn), norm(an)))
            scored = score_match(p, actual[0], actual[1]) if actual else None
            recs.append({
                "date": date, "idx": i, "p": p, "actual": actual, "scored": scored,
                "match_id": f"{date}|{i}",
                "html_name": f"{safe_name(hn)}_vs_{safe_name(an)}.html",
            })
    return recs


def aggregate_records(recs):
    scored = [r["scored"] for r in recs if r["scored"]]
    days = len({r["date"] for r in recs})
    return aggregate(scored, total=len(recs), days=days)


def daily_metrics(recs):
    """逐日命中率 / Brier，供趋势图。返回按日期升序的 list[dict]。"""
    by_date = {}
    for r in recs:
        if r["scored"]:
            by_date.setdefault(r["date"], []).append(r["scored"])
    rows = []
    for date in sorted(by_date):
        s = by_date[date]
        n = len(s)
        rows.append({
            "date": date,
            "graded": n,
            "hit_1x2": sum(1 for x in s if x["hit_1x2"]) / n,
            "hit_over25": sum(1 for x in s if x["over25_hit"]) / n,
            "brier": sum(x["brier"] for x in s) / n,
        })
    return rows


def load_backtest_log(data_dir=DATA_DIR):
    path = Path(data_dir) / "backtest_log.csv"
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def find_record(recs, match_id):
    for r in recs:
        if r["match_id"] == match_id:
            return r
    return None

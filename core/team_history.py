#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""按球队聚合本届世界杯全部比赛（跨日期）。无 streamlit 依赖。
数据源：data/<日期>/predictions.json（对阵+预测）与 results.json（实际比分）。"""

import json
import re
from pathlib import Path

from .standings import canon, team_group

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _load_results(path):
    out = {}
    if not Path(path).exists():
        return out
    try:
        data = json.load(open(path, encoding="utf-8"))
    except Exception:
        return out
    if isinstance(data, dict):
        for k, v in data.items():
            if not isinstance(v, dict) or v.get("h") is None or v.get("a") is None:
                continue
            if str(v.get("status", "final")).lower() == "scheduled":
                continue
            parts = re.split(r"\s*vs\s*|\s*VS\s*", k)
            if len(parts) == 2:
                out[(canon(parts[0]), canon(parts[1]))] = (int(v["h"]), int(v["a"]))
    return out


def _verdict_score(p):
    vs = p.get("verdict_score")
    if vs:
        return str(vs)
    ls = p.get("likely_scores") or []
    if ls:
        x = ls[0]
        return str(x.get("score", "")) if isinstance(x, dict) else str(x)
    return "-"


def all_dates(data_dir=DATA_DIR):
    out = []
    for d in sorted(Path(data_dir).iterdir()) if Path(data_dir).exists() else []:
        if d.is_dir() and DATE_RE.match(d.name) and (d / "predictions.json").exists():
            out.append(d.name)
    return out


def all_teams(data_dir=DATA_DIR):
    teams = set()
    for date in all_dates(data_dir):
        try:
            preds = json.load(open(Path(data_dir) / date / "predictions.json", encoding="utf-8"))
        except Exception:
            continue
        for m in preds:
            teams.add(canon(m.get("home_name", "")))
            teams.add(canon(m.get("away_name", "")))
    teams.discard("")
    return sorted(teams)


def team_matches(team, data_dir=DATA_DIR):
    """返回该队本届全部比赛（按日期升序）。每条：
    {date, group, is_home, opponent, opp_flag, flag, pred, actual, gf, ga, outcome}
    outcome ∈ {'胜','平','负',None}（None=未赛/无赛果）。"""
    team = canon(team)
    rows = []
    for date in all_dates(data_dir):
        d = Path(data_dir) / date
        try:
            preds = json.load(open(d / "predictions.json", encoding="utf-8"))
        except Exception:
            continue
        results = _load_results(d / "results.json")
        for m in preds:
            hn, an = canon(m.get("home_name", "")), canon(m.get("away_name", ""))
            if team not in (hn, an):
                continue
            is_home = team == hn
            opp = an if is_home else hn
            act = results.get((hn, an))
            gf = ga = None
            outcome = None
            if act:
                h, a = act
                gf, ga = (h, a) if is_home else (a, h)
                outcome = "胜" if gf > ga else ("负" if gf < ga else "平")
            rows.append({
                "date": date,
                "group": (re.match(r"([A-L]组)", str(m.get("match_group", ""))) or [None, ""])[1],
                "round": str(m.get("match_group", "")),
                "is_home": is_home,
                "opponent": opp,
                "flag": m.get("home_flag" if is_home else "away_flag", ""),
                "opp_flag": m.get("away_flag" if is_home else "home_flag", ""),
                "pred": _verdict_score(m),
                "actual": f"{act[0]}-{act[1]}" if act else None,
                "gf": gf, "ga": ga, "outcome": outcome,
            })
    rows.sort(key=lambda r: r["date"])
    return rows


def team_summary(team, data_dir=DATA_DIR):
    """聚合战绩：场次/胜平负/进失球/积分/预测命中数。"""
    rows = team_matches(team, data_dir)
    played = [r for r in rows if r["outcome"]]
    w = sum(1 for r in played if r["outcome"] == "胜")
    dr = sum(1 for r in played if r["outcome"] == "平")
    ls = sum(1 for r in played if r["outcome"] == "负")
    gf = sum(r["gf"] for r in played)
    ga = sum(r["ga"] for r in played)
    hit = sum(1 for r in played if r["actual"] and r["pred"] == r["actual"])
    return {
        "team": canon(team), "group": team_group(team),
        "total": len(rows), "played": len(played),
        "w": w, "d": dr, "l": ls, "gf": gf, "ga": ga, "gd": gf - ga,
        "pts": w * 3 + dr, "pred_exact_hit": hit,
    }


if __name__ == "__main__":
    for t in ["巴西", "德国", "葡萄牙"]:
        s = team_summary(t)
        print(f'\n{t}: 赛{s["played"]} {s["w"]}胜{s["d"]}平{s["l"]}负 进{s["gf"]}失{s["ga"]} 积{s["pts"]} 精确命中{s["pred_exact_hit"]}')
        for r in team_matches(t):
            print(f'  {r["date"]} vs {r["opponent"]:<6} 预测{r["pred"]} 实际{r["actual"] or "待赛"} {r["outcome"] or ""}')

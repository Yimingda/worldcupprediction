#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""分组积分榜 + 32强对阵（淘汰赛签表）计算。无 streamlit 依赖，便于单测。
积分榜由 data/<日期>/results.json 里的已终场比分实时累计；签表按官方赛程槽位
（W=小组第1 / RU=小组第2 / 3rd=最佳第三）解析，未定位置以占位文本显示。"""

import json
import re
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

# ── 12 组成员（规范名）──
GROUPS = {
    "A": ["墨西哥", "南非", "韩国", "捷克"],
    "B": ["加拿大", "波黑", "卡塔尔", "瑞士"],
    "C": ["巴西", "摩洛哥", "海地", "苏格兰"],
    "D": ["美国", "巴拉圭", "澳大利亚", "土耳其"],
    "E": ["德国", "库拉索", "科特迪瓦", "厄瓜多尔"],
    "F": ["荷兰", "日本", "瑞典", "突尼斯"],
    "G": ["比利时", "埃及", "伊朗", "新西兰"],
    "H": ["西班牙", "佛得角", "沙特", "乌拉圭"],
    "I": ["法国", "塞内加尔", "伊拉克", "挪威"],
    "J": ["阿根廷", "阿尔及利亚", "奥地利", "约旦"],
    "K": ["葡萄牙", "刚果(金)", "乌兹别克斯坦", "哥伦比亚"],
    "L": ["英格兰", "克罗地亚", "加纳", "巴拿马"],
}

# ── 队名别名归一（不同日期写法不一）──
ALIASES = {
    "沙特阿拉伯": "沙特",
    "韩国队": "韩国",
    "刚果（金）": "刚果(金)",
    "刚果金": "刚果(金)",
    "土耳其队": "土耳其",
}


def canon(name):
    n = str(name).strip()
    return ALIASES.get(n, n)


# 反查：队 → 组
_TEAM2GROUP = {canon(t): g for g, ts in GROUPS.items() for t in ts}


def team_group(name):
    return _TEAM2GROUP.get(canon(name))


def discover_flags(data_dir=DATA_DIR):
    """从 predictions.json 收集 队名→旗帜（归一后）。"""
    flags = {}
    for d in sorted(Path(data_dir).iterdir()) if Path(data_dir).exists() else []:
        if not (d.is_dir() and DATE_RE.match(d.name)):
            continue
        pj = d / "predictions.json"
        if not pj.exists():
            continue
        try:
            for m in json.load(open(pj, encoding="utf-8")):
                for s in ("home", "away"):
                    nm = canon(m.get(f"{s}_name", ""))
                    if nm and m.get(f"{s}_flag"):
                        flags.setdefault(nm, m[f"{s}_flag"])
        except Exception:
            continue
    return flags


def _iter_final_results(data_dir=DATA_DIR):
    """产出 (home, away, h, a)，仅已终场。"""
    for d in sorted(Path(data_dir).iterdir()) if Path(data_dir).exists() else []:
        if not (d.is_dir() and DATE_RE.match(d.name)):
            continue
        rj = d / "results.json"
        if not rj.exists():
            continue
        try:
            data = json.load(open(rj, encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(data, dict):
            continue
        for k, v in data.items():
            if not isinstance(v, dict) or v.get("h") is None or v.get("a") is None:
                continue
            if str(v.get("status", "final")).lower() == "scheduled":
                continue
            parts = re.split(r"\s*vs\s*|\s*VS\s*", k)
            if len(parts) != 2:
                continue
            yield canon(parts[0]), canon(parts[1]), int(v["h"]), int(v["a"])


def _blank(team):
    return {"team": team, "p": 0, "w": 0, "d": 0, "l": 0, "gf": 0, "ga": 0, "gd": 0, "pts": 0}


def compute_standings(data_dir=DATA_DIR):
    """返回 {组: [按 积分/净胜/进球 降序的 4 行]}。"""
    tables = {g: {t: _blank(t) for t in (canon(x) for x in ts)} for g, ts in GROUPS.items()}
    for home, away, h, a in _iter_final_results(data_dir):
        g = team_group(home)
        if not g or team_group(away) != g:
            continue  # 只算小组赛（同组对阵）
        th, ta = tables[g].get(home), tables[g].get(away)
        if not th or not ta:
            continue
        for t, gf, ga in ((th, h, a), (ta, a, h)):
            t["p"] += 1
            t["gf"] += gf
            t["ga"] += ga
            t["gd"] = t["gf"] - t["ga"]
        if h > a:
            th["w"] += 1; th["pts"] += 3; ta["l"] += 1
        elif h < a:
            ta["w"] += 1; ta["pts"] += 3; th["l"] += 1
        else:
            th["d"] += 1; ta["d"] += 1; th["pts"] += 1; ta["pts"] += 1
    out = {}
    for g, tbl in tables.items():
        rows = sorted(tbl.values(), key=lambda r: (r["pts"], r["gd"], r["gf"]), reverse=True)
        out[g] = rows
    return out


def latest_group_standings(data_dir=DATA_DIR):
    """从各组最新一份 predictions.json 里嵌入的 group_standings 取当前积分榜（归一队名）。
    这是管线自己累计的表，通常比 results 回填更完整。返回 {组: [4 行]} 或缺组省略。"""
    latest = {}
    for d in sorted(Path(data_dir).iterdir()) if Path(data_dir).exists() else []:
        if not (d.is_dir() and DATE_RE.match(d.name)):
            continue
        pj = d / "predictions.json"
        if not pj.exists():
            continue
        try:
            preds = json.load(open(pj, encoding="utf-8"))
        except Exception:
            continue
        for m in preds:
            mg = re.match(r"([A-L])组", str(m.get("match_group", "")))
            gs = m.get("group_standings")
            if mg and gs:
                latest[mg.group(1)] = gs  # 后写覆盖 → 最终保留最新日期
    out = {}
    for g, gs in latest.items():
        rows = []
        for r in gs:
            t = canon(r.get("team", ""))
            gd = int(r.get("gd", int(r.get("gf", 0)) - int(r.get("ga", 0))))
            rows.append({"team": t, "p": int(r.get("p", 0)), "w": int(r.get("w", 0)),
                         "d": int(r.get("d", 0)), "l": int(r.get("l", 0)),
                         "gf": int(r.get("gf", 0)), "ga": int(r.get("ga", 0)),
                         "gd": gd, "pts": int(r.get("pts", 0))})
        out[g] = sorted(rows, key=lambda r: (r["pts"], r["gd"], r["gf"]), reverse=True)
    return out


def current_standings(data_dir=DATA_DIR):
    """当前积分榜：优先用嵌入 group_standings；某组缺失则退回 results 累计。"""
    embedded = latest_group_standings(data_dir)
    computed = compute_standings(data_dir)
    out = {}
    for g in GROUPS:
        emb = embedded.get(g)
        comp = computed.get(g, [])
        # 嵌入存在且场次不少于 results 累计 → 用嵌入；否则用 results
        emb_p = max((r["p"] for r in emb), default=0) if emb else 0
        comp_p = max((r["p"] for r in comp), default=0) if comp else 0
        out[g] = emb if (emb and emb_p >= comp_p) else comp
    return out


# ── 32强签表槽位（来自官方赛程）──
# 每条 (A队槽位, B队槽位)；槽位记法：'W-C'=C组第1，'RU-F'=F组第2，'3-(A/B/C/D/F)'=最佳第三占位
R32 = [
    ("RU-A", "RU-B"), ("W-C", "RU-F"), ("W-E", "3-(A/B/C/D/F)"), ("W-F", "RU-C"),
    ("RU-E", "RU-I"), ("W-I", "3-(C/D/F/G/H)"), ("W-A", "3-(C/E/F/H/I)"), ("W-L", "3-(E/H/I/J/K)"),
    ("W-G", "3-(A/E/H/I/J)"), ("W-D", "3-(B/E/F/I/J)"), ("W-H", "RU-J"), ("RU-K", "RU-L"),
    ("W-B", "3-(E/F/G/I/J)"), ("RU-D", "RU-G"), ("W-J", "RU-H"), ("W-K", "3-(D/E/I/J/L)"),
]


def _group_done(rows):
    """该组是否三轮全部踢完（每队 3 场）。"""
    return rows and all(r["p"] >= 3 for r in rows)


def resolve_slot(slot, standings):
    """把槽位解析成 队名 或 占位文本。返回 (text, settled:bool)。"""
    if slot.startswith("3-"):
        return f"最佳第三 {slot[2:]}", False
    kind, grp = slot.split("-")  # W/RU , 组字母
    rows = standings.get(grp, [])
    idx = 0 if kind == "W" else 1
    if _group_done(rows) and len(rows) > idx:
        return rows[idx]["team"], True
    label = "第1" if kind == "W" else "第2"
    return f"{grp}组{label}", False


def bracket(standings):
    """返回 16 条 R32 对阵：[{a, a_settled, b, b_settled}]。"""
    out = []
    for sa, sb in R32:
        a, sa_ok = resolve_slot(sa, standings)
        b, sb_ok = resolve_slot(sb, standings)
        out.append({"a": a, "a_settled": sa_ok, "b": b, "b_settled": sb_ok,
                    "a_slot": sa, "b_slot": sb})
    return out


if __name__ == "__main__":
    st = compute_standings()
    for g in sorted(st):
        print(f"\n== {g}组 ==")
        for i, r in enumerate(st[g], 1):
            print(f"  {i}. {r['team']:<6} 赛{r['p']} 积{r['pts']} 净{r['gd']:+d} 进{r['gf']}")
    print("\n== 32强 ==")
    for i, m in enumerate(bracket(st), 1):
        print(f"  R32-{i}: {m['a']}  vs  {m['b']}")

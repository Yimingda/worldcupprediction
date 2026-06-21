#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""真实数据源适配器（可插拔）。
目的：把"从哪来"与"怎么用"解耦，未来接入赔率/比分 API 时，
只需实现一个 Source 子类并在 get_source() 里返回它，其余代码不动。

默认 NullSource：不提供任何外部数据（当前状态），预测仍由模型/人工填。
接入示例（伪代码）：
    class MyApiSource(Source):
        def fetch_results(self, date): ...   # 返回 {"主队 vs 客队": {"h","a","status":"final","source":url}}
        def fetch_odds(self, home, away, date): ...  # 返回 {"home":..,"draw":..,"away":..}
    def get_source(): return MyApiSource(api_key=os.environ["ODDS_API_KEY"])
"""

from __future__ import annotations


class Source:
    name = "base"

    def fetch_results(self, date: str) -> dict:
        """返回某日已确认终场赛果；无则空 dict。"""
        return {}

    def fetch_odds(self, home: str, away: str, date: str) -> dict | None:
        """返回胜平负隐含概率(0-100)；无则 None。"""
        return None

    def available(self) -> bool:
        return False


class NullSource(Source):
    name = "null"


def get_source() -> Source:
    """当前返回 NullSource。接入真实 API 时改这里即可。"""
    return NullSource()

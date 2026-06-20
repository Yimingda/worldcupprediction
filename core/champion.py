#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""冠军/四强预测数据加载（无 streamlit 依赖）。"""

import json
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def load_champion():
    p = DATA_DIR / "champion_prediction.json"
    if not p.exists():
        return None
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)

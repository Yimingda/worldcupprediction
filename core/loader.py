#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""带缓存的数据入口（依赖 streamlit）。页面统一从这里取数。"""

import streamlit as st

from . import data

_TTL = 120  # 秒；越小越"新"，但每次重读磁盘。配合页面"刷新"按钮可手动清。


@st.cache_data(ttl=_TTL, show_spinner=False)
def records():
    return data.all_records()


@st.cache_data(ttl=_TTL, show_spinner=False)
def aggregate():
    return data.aggregate_records(data.all_records())


@st.cache_data(ttl=_TTL, show_spinner=False)
def daily():
    return data.daily_metrics(data.all_records())


def dates():
    return data.list_dates()


def clear_cache():
    """清掉本 app 的数据缓存，强制下次重读。"""
    records.clear()
    aggregate.clear()
    daily.clear()


def open_detail(match_id):
    st.query_params["match"] = match_id
    st.switch_page("pages/3_单场详情.py")

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""带缓存的数据入口（依赖 streamlit）。页面统一从这里取数。"""

import streamlit as st

from . import data


@st.cache_data(ttl=300, show_spinner=False)
def records():
    return data.all_records()


@st.cache_data(ttl=300, show_spinner=False)
def aggregate():
    return data.aggregate_records(data.all_records())


@st.cache_data(ttl=300, show_spinner=False)
def daily():
    return data.daily_metrics(data.all_records())


def dates():
    return data.list_dates()


def open_detail(match_id):
    """设置查询参数并跳转到单场详情页。"""
    st.query_params["match"] = match_id
    st.switch_page("pages/3_单场详情.py")

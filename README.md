# ⚽ 世界杯预测中心 · Streamlit 版

把"每日赛前预测 + 回测复盘"做成一个可在线访问的 Streamlit 应用。
**生成（联网搜索 + 模型分析）在本地跑，产出 JSON；本应用只读 JSON 做展示。**

## 目录结构

```
streamlit_app/
├── app.py                  # 入口：总览战绩看板 + 今日预测 + 历史时间线
├── pages/
│   ├── 1_今日预测.py        # 按日期看每场预测，点进详情
│   ├── 2_历史回测.py        # 累计指标 + 逐日趋势图 + 全量明细表
│   └── 3_单场详情.py        # 单场完整赛前分析（?match=日期|序号 可分享）
├── core/
│   ├── scoring.py          # 纯评分逻辑（1X2/大小球/让球/比分/Brier），无 st 依赖
│   ├── data.py             # 读取 data/ 下 JSON，展平为记录
│   ├── loader.py           # @st.cache_data 缓存入口 + 跳转
│   └── view.py             # 渲染组件（卡片/徽章/进度条/单场详情）
├── data/                   # 数据真相源（提交进 Git）
│   ├── YYYY-MM-DD/
│   │   ├── predictions.json   # 当日各场预测（render 用的同一份）
│   │   └── results.json       # 当日赛果 {"主队 vs 客队": {"h":1,"a":1}}
│   └── backtest_log.csv
├── requirements.txt
└── .streamlit/config.toml
```

## 本地运行

```bash
cd streamlit_app
pip install -r requirements.txt
streamlit run app.py
```

## 数据更新（保持自动闭环）

云端不跑定时任务、文件系统是临时的，所以：

1. **本地**继续用你的每日定时任务生成预测，写入 `data/YYYY-MM-DD/predictions.json`；
   赛后把比分写入同目录 `results.json`。
2. 末尾自动提交并推送：

   ```bash
   git add data && git commit -m "data: $(date +%F)" && git push
   ```

3. Streamlit Community Cloud 检测到新提交会**自动重启并加载最新数据**，页面随之更新。

> `results.json` 的键用 `"主队 vs 客队"`，值 `{"h": 主队进球, "a": 客队进球}`；未开赛可写 `null` 或省略。
> 比分一旦写入，回测指标、命中徽标、趋势图全部自动刷新。

## 部署到 Streamlit Community Cloud

1. 把本 `streamlit_app/` 作为仓库根（或仓库子目录）推到 GitHub。
2. 打开 https://share.streamlit.io → New app → 选仓库/分支。
3. **Main file path** 填 `app.py`（若放在子目录则 `streamlit_app/app.py`）。
4. Deploy。之后每次 `git push` 自动重新部署。

## 说明

- 评分逻辑与本地 `backtest.py` 一致；`core/scoring.py` 为其纯函数版，可单测。
- 不含任何密钥；展示层无需 API。若未来要在云端做生成，需自备 LLM / 搜索 API 并用 `st.secrets`（注意成本）。
- 分析仅供参考，请理性博彩，量力而行。

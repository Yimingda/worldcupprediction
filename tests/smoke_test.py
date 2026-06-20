#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""本地冒烟测试：用 Streamlit AppTest 无头运行四个页面，确认无异常。
运行： cd streamlit_app && python -m tests.smoke_test
（需先 pip install -r requirements.txt）
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from streamlit.testing.v1 import AppTest  # noqa: E402

PAGES = ["app.py", "pages/1_今日预测.py", "pages/2_历史回测.py", "pages/3_单场详情.py"]


def main():
    failed = 0
    for page in PAGES:
        at = AppTest.from_file(str(ROOT / page), default_timeout=30).run()
        if at.exception:
            failed += 1
            print(f"❌ {page}: {at.exception}")
        else:
            print(f"✅ {page}  (markdown blocks: {len(at.markdown)}, metrics: {len(at.metric)})")
    print("—" * 40)
    print("全部通过 ✅" if failed == 0 else f"{failed} 个页面有异常 ❌")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()

"""
测试配置文件 — 共享 fixtures
"""
import os
import sys
import pytest
import asyncio
from pathlib import Path

# 确保项目根目录在 sys.path 中
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# 加载 .env
from dotenv import load_dotenv
_env_file = PROJECT_ROOT / ".env"
if _env_file.exists():
    load_dotenv(_env_file)

os.environ.setdefault("PYTHONIOENCODING", "utf-8")
os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")
os.environ.setdefault("HF_HUB_ENDPOINT", "https://hf-mirror.com")


@pytest.fixture(scope="function")
def event_loop():
    """创建 function 级别的事件循环（避免跨测试连接泄漏）"""
    loop = asyncio.new_event_loop()
    yield loop
    # 清理待处理的异步任务
    pending = asyncio.all_tasks(loop)
    for task in pending:
        task.cancel()
    loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
    loop.close()


@pytest.fixture(scope="session")
def project_root():
    return PROJECT_ROOT


@pytest.fixture(scope="session")
def test_user_id():
    return "user_10001"


@pytest.fixture(scope="session")
def test_order_ids():
    return {
        "delivered": "JD2024042800001",
        "shipping":  "JD2024042800002",
        "returning": "JD2024042800008",
        "pending":   "JD2024042800004",
    }


@pytest.fixture(scope="session")
def test_queries():
    """测试用查询语句集合"""
    return {
        "my_orders":      "我的订单到哪了",
        "specific_order": "查询JD2024042800002的物流状态",
        "pending_orders": "待发货的订单有哪些",
        "shipping_status": "最近一周有哪些订单在运输中",
        "delivered":      "我所有已签收的订单",
        "refund":         "JD2024042800008退货的物流进度",
        "money":          "上个月总共花了多少钱",
    }

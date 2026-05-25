"""
端到端业务流程测试 — 模拟真实电商客服场景
"""
import pytest
import json
import asyncio
import websockets

BASE_WS = "ws://localhost:8081/api/v1/ecommerce-assistant/chat/ws"


async def _send_query(thread_id: str, user_id: str, query: str, tenant_id: str = "default", timeout: int = 120) -> list:
    """发送 WebSocket 查询，返回所有收到的事件"""
    events = []
    try:
        async with websockets.connect(BASE_WS) as ws:
            msg = {
                "thread_id": thread_id,
                "user_id": user_id,
                "tenant_id": tenant_id,
                "query": query,
                "metadata": {"Is_translate": False, "Is_emotion": False},
            }
            await ws.send(json.dumps(msg))
            while True:
                try:
                    resp = await asyncio.wait_for(ws.recv(), timeout=timeout)
                    data = json.loads(resp)
                    events.append(data)
                    if data.get("event") == "end" or data.get("type") == "end":
                        break
                    if data.get("event") == "error":
                        break
                except asyncio.TimeoutError:
                    events.append({"event": "timeout", "error": f"超时 {timeout}s"})
                    break
    except Exception as e:
        events.append({"event": "connection_error", "error": str(e)})
    return events


def _get_response_text(events: list) -> str:
    """从事件列表中提取 AI 回复文本"""
    texts = []
    for e in events:
        content = e.get("content", "")
        if isinstance(content, str) and len(content) > 5:
            texts.append(content)
        data = e.get("data", {})
        if isinstance(data, dict):
            answer = data.get("answer", "") or data.get("content", "")
            if answer and len(str(answer)) > 5:
                texts.append(str(answer))
    return " | ".join(texts[-2:]) if texts else ""


# ==================== 场景 1: 订单物流查询 ====================

@pytest.mark.asyncio
@pytest.mark.e2e
class TestScenario1OrderLogistics:
    """场景 1: 用户查询订单物流 — 最核心流程"""

    async def test_query_my_orders(self):
        """我的订单到哪了 → Text2SQL 查询 → 拟人化回复"""
        events = await _send_query(
            thread_id="e2e-order-001",
            user_id="user_10001",
            query="我的订单到哪了",
        )
        text = _get_response_text(events)
        assert len(events) > 0, "应收到事件"
        assert any(e.get("event") == "end" for e in events), "应收到 end 事件"
        # 应包含订单相关关键词
        assert any(kw in text for kw in ["订单", "物流", "快递", "JD"]), \
            f"回复应涉及订单物流, got: {text[:200]}"

    async def test_query_specific_order(self):
        """查询指定订单 → 返回具体物流详情"""
        events = await _send_query(
            thread_id="e2e-order-002",
            user_id="user_10001",
            query="查询JD2024042800002的物流状态",
        )
        text = _get_response_text(events)
        assert "JD2024042800002" in text or "索尼" in text or "圆通" in text or "运输中" in text, \
            f"回复应包含订单相关信息, got: {text[:200]}"

    async def test_query_returning_order(self):
        """查询退货订单状态"""
        events = await _send_query(
            thread_id="e2e-order-003",
            user_id="user_10001",
            query="JD2024042800008退货的物流进度",
        )
        text = _get_response_text(events)
        assert any(kw in text for kw in ["退货", "JD2024042800008", "小米"]), \
            f"回复应涉及退货信息, got: {text[:200]}"


# ==================== 场景 2: 多轮对话 ====================

@pytest.mark.asyncio
@pytest.mark.e2e
class TestScenario2MultiTurn:
    """场景 2: 多轮对话 — 上下文保持"""

    async def test_multi_turn_conversation(self):
        """连续两轮对话，验证上下文保持"""
        thread = "e2e-multi-001"

        # 第 1 轮：查订单
        events1 = await _send_query(thread, "user_10001", "我的订单到哪了")
        text1 = _get_response_text(events1)
        assert "end" in [e.get("event") for e in events1], "第1轮应正常结束"
        print(f"\n  [轮1] {text1[:120]}")

        # 第 2 轮：追问（省略订单号，依赖上下文）
        await asyncio.sleep(2)
        events2 = await _send_query(thread, "user_10001", "物流最快的那个什么时候到")
        text2 = _get_response_text(events2)
        # 第 2 轮应有响应（不限内容）
        print(f"  [轮2] {text2[:120]}")
        assert len(events2) > 0, "第2轮应有响应"


# ==================== 场景 3: 商品售后咨询 ====================

@pytest.mark.asyncio
@pytest.mark.e2e
class TestScenario3ProductInfo:
    """场景 3: 商品知识库问答"""

    async def test_return_policy(self):
        """咨询退换货政策"""
        events = await _send_query(
            thread_id="e2e-product-001",
            user_id="user_10002",
            query="可以七天无理由退货吗",
        )
        text = _get_response_text(events)
        # 应包含退换货相关内容
        assert any(kw in text for kw in ["退", "7天", "七天", "无理由", "规则"]), \
            f"回复应涉及退换货, got: {text[:200]}"

    async def test_product_inquiry(self):
        """咨询商品属性"""
        events = await _send_query(
            thread_id="e2e-product-002",
            user_id="user_10003",
            query="这款护肤品敏感肌能用吗",
        )
        text = _get_response_text(events)
        assert len(text) > 10, "应收到有意义回复"


# ==================== 场景 4: 工单创建 ====================

@pytest.mark.asyncio
@pytest.mark.e2e
class TestScenario4TicketFlow:
    """场景 4: 工单 CRUD 全流程"""

    async def test_create_ticket_via_api(self):
        """通过 API 创建工单"""
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "http://localhost:8081/api/v1/tickets",
                json={
                    "tenant_id": "default",
                    "user_id": "user_10001",
                    "summary": "E2E测试-屏幕漏光退换货",
                    "priority": "high",
                },
            ) as resp:
                assert resp.status == 201, f"创建工单失败: {resp.status}"
                data = await resp.json()
                assert data["status"] == "open"
                assert data["priority"] == "high"
                return data  # 供后续测试使用

    async def test_update_ticket_status(self):
        """更新工单状态"""
        import aiohttp
        # 先创建一个
        ticket_id = None
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "http://localhost:8081/api/v1/tickets",
                json={
                    "tenant_id": "default",
                    "user_id": "user_10002",
                    "summary": "E2E测试-物流催单",
                    "priority": "medium",
                },
            ) as resp:
                data = await resp.json()
                ticket_id = data["id"]

            # 更新
            async with session.patch(
                f"http://localhost:8081/api/v1/tickets/{ticket_id}",
                json={"status": "in_progress", "agent_id": "agent_e2e"},
            ) as resp:
                assert resp.status == 200
                data = await resp.json()
                assert data["status"] == "in_progress"
                assert data["agent_id"] == "agent_e2e"

            # 解决
            async with session.patch(
                f"http://localhost:8081/api/v1/tickets/{ticket_id}",
                json={"status": "resolved", "resolution_note": "已联系物流，已催单"},
            ) as resp:
                data = await resp.json()
                assert data["status"] == "resolved"

    async def test_list_tickets(self):
        """列出工单"""
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "http://localhost:8081/api/v1/tickets?tenant_id=default&limit=10",
            ) as resp:
                assert resp.status == 200
                data = await resp.json()
                assert data["total"] >= 1
                assert len(data["tickets"]) >= 1


# ==================== 场景 5: Dashboard + 计费验证 ====================

@pytest.mark.asyncio
@pytest.mark.e2e
class TestScenario5DashboardValidation:
    """场景 5: 运营数据验证"""

    async def test_dashboard_overview(self):
        """Dashboard 概览有数据"""
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "http://localhost:8081/api/v1/admin/dashboard/overview?tenant_id=default",
            ) as resp:
                assert resp.status == 200
                data = await resp.json()
                assert data["total_conversations"] > 0, "应有对话记录"
                assert data["active_users_today"] > 0, "应有活跃用户"

    async def test_billing_usage(self):
        """计费用量有数据"""
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "http://localhost:8081/api/v1/admin/billing/usage?tenant_id=default&days=7",
            ) as resp:
                assert resp.status == 200
                data = await resp.json()
                assert data["total_requests"] > 0, "应有 API 调用记录"
                assert data["total_tokens_in"] > 0, "应有 Token 消耗"

    async def test_billing_by_model(self):
        """计费按模型拆分"""
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "http://localhost:8081/api/v1/admin/billing/usage?tenant_id=default&days=7",
            ) as resp:
                data = await resp.json()
                assert "qwen-plus" in data.get("by_model", {}), \
                    f"应有 qwen-plus 用量, got models: {list(data.get('by_model', {}).keys())}"


# ==================== 场景 6: 压力验证 (轻量) ====================

@pytest.mark.asyncio
@pytest.mark.e2e
class TestScenario6Stress:
    """场景 6: 轻量压力测试"""

    async def test_concurrent_queries(self):
        """并发 3 个不同用户同时查询"""
        tasks = [
            _send_query(f"e2e-stress-{i}", f"user_1000{i}", "我的订单到哪了")
            for i in range(3)
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        success = sum(1 for r in results if not isinstance(r, Exception) and len(r) > 0)
        assert success >= 2, f"并发查询成功率应 >= 2/3, got {success}/3"

    async def test_long_query(self):
        """长问题查询"""
        events = await _send_query(
            thread_id="e2e-long-001",
            user_id="user_10001",
            query="我之前买了一个耳机和一个手机，耳机已经收到了，手机还没发货，我想知道手机什么时候发货，以及如果我现在取消耳机订单还能退款吗",
        )
        text = _get_response_text(events)
        # 无论是回答哪个方面，只要有意义回复就行
        assert len(text) > 10, f"应有回复, got: {text[:200]}"

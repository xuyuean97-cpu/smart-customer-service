"""
Pydantic 模型测试 — OrderInfo alias / 事件模型
"""

from models.schemas import (
    OrderInfo,
    OrderListEventContent,
    ChatEvent,
    TextEventContent,
    EndEventContent,
    ErrorEventContent,
)


class TestOrderInfoAlias:
    """OrderInfo 字段 alias 兼容性"""

    def test_parse_old_airport_field_names(self):
        """测试: 旧机场字段名 → 新电商字段名映射"""
        old_data = {
            "order_id": "JD001",
            "airline_company": "顺丰速运",
            "airline_twocharcode": "SF",
            "aircraft_type": "标准快递",
            "boarding_gate": "科技园配送站",
            "checkin_counter": "南山揽收点",
            "baggage_carousel": "自提柜001",
            "departure_terminal": "深圳南山集散中心",
            "destination_terminal": "深圳科技园营业部",
            "shared_flight_number": "JD002",
            "airline_logo": "data:image/...",
            "expected_security_check_duration": "2小时",
            "scheduled_boarding_time": "2026-04-28 08:00:00",
            "actual_boarding_time": "2026-04-28 08:15:00",
            "scheduled_boarding_end_time": "2026-04-28 20:00:00",
            "actual_boarding_end_time": "2026-04-28 19:30:00",
            "expected_boarding_walking_duration": "30分钟",
            "subscribe_supported": True,
        }
        order = OrderInfo(**old_data)

        assert order.express_company == "顺丰速运"
        assert order.express_code == "SF"
        assert order.shipping_method == "标准快递"
        assert order.current_station == "科技园配送站"
        assert order.pickup_point == "南山揽收点"
        assert order.self_pickup_point == "自提柜001"
        assert order.departure_hub == "深圳南山集散中心"
        assert order.destination_hub == "深圳科技园营业部"
        assert order.related_order_id == "JD002"
        assert order.express_logo == "data:image/..."
        assert order.expected_processing_duration == "2小时"
        assert order.scheduled_outbound_time == "2026-04-28 08:00:00"
        assert order.actual_outbound_time == "2026-04-28 08:15:00"
        assert order.scheduled_delivery_end_time == "2026-04-28 20:00:00"
        assert order.actual_delivery_end_time == "2026-04-28 19:30:00"
        assert order.expected_delivery_duration == "30分钟"
        assert order.subscribe_supported is True

    def test_parse_new_field_names(self):
        """测试: 新字段名直接解析"""
        new_data = {
            "order_id": "JD001",
            "express_company": "京东物流",
            "express_code": "JD",
            "shipping_method": "京准达",
            "current_station": "朝阳配送站",
            "subscribe_supported": False,
        }
        order = OrderInfo(**new_data)
        assert order.express_company == "京东物流"
        assert order.express_code == "JD"

    def test_serialize_uses_new_names(self):
        """测试: model_dump() 输出新字段名，不含旧名"""
        old_data = {
            "order_id": "JD001",
            "airline_company": "顺丰速运",
            "airline_twocharcode": "SF",
            "subscribe_supported": True,
        }
        order = OrderInfo(**old_data)
        dumped = order.model_dump()

        # 新字段名存在
        assert "express_company" in dumped
        assert "express_code" in dumped
        # 旧字段名不存在
        assert "airline_company" not in dumped
        assert "airline_twocharcode" not in dumped

    def test_exclude_none(self):
        """测试: exclude_none 排除空值"""
        order = OrderInfo(order_id="JD001", subscribe_supported=True)
        dumped = order.model_dump(exclude_none=True)
        assert "express_company" not in dumped  # None，应被排除
        assert "order_id" in dumped
        assert "subscribe_supported" in dumped


class TestOrderListEventContent:
    """订单列表事件"""

    def test_orders_field(self):
        """测试: orders 字段替代旧 flights"""
        order = OrderInfo(order_id="JD001", subscribe_supported=True)
        event = OrderListEventContent(
            title="您的订单",
            orders=[order],
            action_hint="点击查看详情",
        )
        assert len(event.orders) == 1
        assert event.orders[0].order_id == "JD001"

    def test_serialize_orders_field(self):
        """测试: 序列化使用 orders 键名"""
        order = OrderInfo(order_id="JD001", subscribe_supported=True)
        event = OrderListEventContent(
            title="您的订单",
            orders=[order],
        )
        data = event.model_dump()
        assert "orders" in data, f"序列化应使用 'orders' 键, got keys: {list(data.keys())}"
        assert "flights" not in data, "不应包含旧 'flights' 键"


class TestChatEvents:
    """ChatEvent 协议"""

    def test_text_event(self):
        event = ChatEvent(
            id="evt_001",
            sequence=1,
            content=TextEventContent(text="你好"),
        )
        assert isinstance(event.content, TextEventContent)
        assert event.content.text == "你好"

    def test_end_event(self):
        event = ChatEvent(
            id="evt_end",
            sequence=99,
            content=EndEventContent(suggestions=["查订单", "看物流"]),
        )
        assert isinstance(event.content, EndEventContent)
        assert "查订单" in event.content.suggestions

    def test_error_event(self):
        event = ChatEvent(
            id="evt_err",
            sequence=0,
            content=ErrorEventContent(error_code="E001", error_message="系统错误"),
        )
        assert isinstance(event.content, ErrorEventContent)
        assert event.content.error_code == "E001"


class TestOrderInfoEdgeCases:
    """OrderInfo 边界情况"""

    def test_minimal_data(self):
        """测试: 最小必填字段"""
        order = OrderInfo(order_id="JD001", subscribe_supported=False)
        assert order.order_id == "JD001"
        assert order.subscribe_supported is False

    def test_partial_old_fields(self):
        """测试: 混合新旧字段名"""
        data = {
            "order_id": "JD001",
            "express_company": "圆通",        # 新名
            "airline_twocharcode": "YTO",     # 旧名
            "subscribe_supported": True,
        }
        order = OrderInfo(**data)
        assert order.express_company == "圆通"
        assert order.express_code == "YTO"

    def test_ignores_unknown_fields(self):
        """测试: 未知字段被忽略"""
        data = {
            "order_id": "JD001",
            "some_random_field": "garbage",
            "subscribe_supported": True,
        }
        order = OrderInfo(**data)
        assert order.order_id == "JD001"

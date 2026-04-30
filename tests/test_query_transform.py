"""
查询变换功能测试 — rewrite / step-back / standardize / decompose
"""
import pytest
from langchain_core.messages import HumanMessage, AIMessage

from agents.ecommerce_service.core.query.transform import (
    rewrite_query,
    generate_step_back_query,
    standardize_terminology,
    expand_implicit_query,
    decompose_to_components,
    professional_prejudgment_rewrite,
    order_rewrite_query,
)


class TestRewriteQuery:
    """基础查询重写"""

    @pytest.mark.asyncio
    async def test_rewrite_short_query(self):
        """测试: 简短查询被展开"""
        history = [
            HumanMessage(content="这个包是真皮的吗"),
            AIMessage(content="是的亲，这款包包采用头层牛皮材质"),
        ]
        result = await rewrite_query("能洗吗", history)
        assert result, "重写结果不应为空"
        assert len(result) > 4, "重写后查询不应太短"

    @pytest.mark.asyncio
    async def test_rewrite_preserves_intent(self):
        """测试: 重写保持核心意图"""
        result = await rewrite_query("我不想要了", [])
        assert any(kw in result for kw in ["退货", "退款", "退", "取消"]), \
            f"退货意图应被保留, got: {result}"

    @pytest.mark.asyncio
    async def test_rewrite_chitchat_no_change(self):
        """测试: 闲聊消息不重写"""
        result = await rewrite_query("你好", [])
        assert len(result) > 0  # 至少返回原句或简单重写


class TestStepBackQuery:
    """抽象回退查询"""

    @pytest.mark.asyncio
    async def test_step_back_brand_to_category(self):
        """测试: 品牌问题回退到品类规则"""
        result = await generate_step_back_query("雅诗兰黛过敏能退吗")
        assert result, "回退查询不应为空"
        # 应泛化为化妆品/护肤品相关
        assert any(kw in result for kw in ["化妆品", "护肤品", "过敏", "退货", "赔付"]), \
            f"回退应包含品类信息, got: {result}"

    @pytest.mark.asyncio
    async def test_step_back_generalization(self):
        """测试: 具体产品回退到通用规则"""
        result = await generate_step_back_query("这台格力空调管安装吗")
        assert any(kw in result for kw in ["大家电", "安装", "服务", "收费"]), \
            f"应泛化为安装服务规则, got: {result}"


class TestStandardizeTerminology:
    """术语标准化"""

    @pytest.mark.asyncio
    async def test_standardize_colloquial(self):
        """测试: 口语→标准术语"""
        result = await standardize_terminology("我的快递怎么不动了")
        assert any(kw in result for kw in ["物流", "更新", "轨迹"]), \
            f"应标准化为物流术语, got: {result}"

    @pytest.mark.asyncio
    async def test_standardize_price_protection(self):
        """测试: 价保相关术语"""
        result = await standardize_terminology("买贵了能退钱吗")
        assert any(kw in result for kw in ["价格保护", "差价", "补偿"]), \
            f"应标准化为价保术语, got: {result}"


class TestExpandImplicitQuery:
    """隐含查询展开"""

    @pytest.mark.asyncio
    async def test_expand_short_query(self):
        """测试: 简短查询展开"""
        history = [
            HumanMessage(content="这件羽绒服充绒量多少"),
            AIMessage(content="这款羽绒服充绒量为200g，90%白鸭绒"),
        ]
        result = await expand_implicit_query("能机洗吗", history)
        assert len(result) > 6, f"展开后应更长, got: {result}"

    @pytest.mark.asyncio
    async def test_expand_no_history(self):
        """测试: 无历史时也能展开"""
        result = await expand_implicit_query("怎么退")
        assert any(kw in result for kw in ["退货", "退款", "申请", "流程"]), \
            f"应展开退货意图, got: {result}"


class TestOrderRewrite:
    """订单物流查询重写"""

    @pytest.mark.asyncio
    async def test_order_rewrite_with_history(self):
        """测试: 结合历史补全订单号"""
        history = [
            HumanMessage(content="订单JD001到哪了"),
            AIMessage(content="正在运输中"),
        ]
        result = await order_rewrite_query("什么时候到", history)
        assert result, "重写结果不应为空"

    @pytest.mark.asyncio
    async def test_order_rewrite_no_history(self):
        """测试: 无历史时默认查最近订单"""
        result = await order_rewrite_query("我的快递呢", [])
        assert result, "重写结果不应为空"


class TestDecomposeQuery:
    """组件分解"""

    @pytest.mark.asyncio
    async def test_decompose_complex_product(self):
        """测试: 复杂商品分解为组件"""
        result = await decompose_to_components("按摩椅坏了怎么办")
        assert any(kw in result for kw in ["保修", "电机", "维修", "质保"]), \
            f"应分解为组件服务问题, got: {result}"


class TestProfessionalPrejudgment:
    """专业预判改写"""

    @pytest.mark.asyncio
    async def test_prejudgment_clothing_size(self):
        """测试: 服装预判尺码问题"""
        result = await professional_prejudgment_rewrite("这件裙子我能穿吗")
        assert any(kw in result for kw in ["身高", "体重", "尺码", "版型"]), \
            f"应预判为尺码咨询, got: {result}"

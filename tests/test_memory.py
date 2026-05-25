"""
记忆系统功能测试 — 对话存储 / 检索 / 智能过滤
"""
import pytest
import uuid

from agents.ecommerce_service.context_engineering.memory_manager import memory_manager
from agents.ecommerce_service.context_engineering.agent_memory import (
    AgentMemoryMixin,
    MemoryEnabledAgent,
)


@pytest.fixture(autouse=True)
async def ensure_initialized():
    """每个测试前确保记忆管理器已初始化"""
    if not memory_manager._initialized:
        await memory_manager.initialize()


class TestMemoryInitialization:
    """记忆管理器初始化"""

    @pytest.mark.asyncio
    async def test_memory_manager_initialized(self):
        """测试: 记忆管理器已初始化"""
        if not memory_manager._initialized:
            await memory_manager.initialize()
        assert memory_manager._initialized, "记忆管理器应处于已初始化状态"
        assert memory_manager.conversation_memory is not None
        assert memory_manager.profile_memory is not None

    @pytest.mark.asyncio
    async def test_singleton(self):
        """测试: 单例模式"""
        from agents.ecommerce_service.context_engineering.memory_manager import MemoryManager
        assert isinstance(memory_manager, MemoryManager)


class TestConversationStorage:
    """对话存储功能 — store_conversation(messages=..., response=...)"""

    @pytest.mark.asyncio
    async def test_store_conversation(self, test_user_id):
        """测试: 存储一条对话"""
        run_id = str(uuid.uuid4())
        result = await memory_manager.store_conversation(
            application_id="test_app",
            user_id=test_user_id,
            run_id=run_id,
            agent_id="test_agent",
            messages="我想查询订单物流",
            response="亲，您的订单JD2024042800002正在运输中，预计明天到达。",
        )
        assert result is not None

    @pytest.mark.asyncio
    async def test_store_with_retrieval_context(self, test_user_id):
        """测试: 存储包含检索上下文的对话"""
        run_id = str(uuid.uuid4())
        result = await memory_manager.store_conversation(
            application_id="test_app",
            user_id=test_user_id,
            run_id=run_id,
            agent_id="order_logistics",
            messages="JD2024042800001到哪了",
            response="您的iPhone 16 Pro Max已于4月27日签收。",
            metadata={
                "retrieval_result_content": '{"order_id": "JD2024042800001", "order_status": "delivered"}',
                "retrieval_result_source": "order",
                "retrieval_result_score": 0.95,
            },
        )
        assert result is not None

    @pytest.mark.asyncio
    async def test_store_conversation_metadata(self, test_user_id):
        """测试: 存储包含丰富元数据的对话"""
        run_id = str(uuid.uuid4())
        result = await memory_manager.store_conversation(
            application_id="test_app",
            user_id=test_user_id,
            run_id=run_id,
            agent_id="product_info",
            messages="这件衣服能退吗",
            response="亲，支持7天无理由退货哦~",
            metadata={
                "source": "wechat_miniprogram",
                "device": "iPhone15",
                "ip": "192.168.1.1",
            },
        )
        assert result is not None


class TestMemoryRetrieval:
    """记忆检索功能"""

    @pytest.mark.asyncio
    async def test_get_conversation_history(self, test_user_id):
        """测试: 获取对话历史"""
        history = await memory_manager.get_conversation_history(
            user_id=test_user_id,
            limit=5,
        )
        assert isinstance(history, list), f"返回应为列表, got: {type(history)}"

    @pytest.mark.asyncio
    async def test_get_conversation_history_filtered(self, test_user_id):
        """测试: 按 agent_id 过滤对话历史"""
        history = await memory_manager.get_conversation_history(
            user_id=test_user_id,
            agent_id="order_logistics",
            limit=5,
        )
        assert isinstance(history, list)

    @pytest.mark.asyncio
    async def test_search_conversations(self, test_user_id):
        """测试: 语义搜索对话"""
        results = await memory_manager.search_conversations(
            query="物流查询",
            user_id=test_user_id,
            limit=5,
        )
        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_get_smart_filtered_memories(self, test_user_id):
        """测试: 智能筛选记忆"""
        results = await memory_manager.get_smart_filtered_memories(
            query="订单",
            user_id=test_user_id,
            limit=5,
        )
        assert isinstance(results, list)


class TestAgentMemoryMixin:
    """AgentMemoryMixin 静态方法 — store_agent_conversation_interaction(messages=..., response=...)"""

    @pytest.mark.asyncio
    async def test_store_agent_interaction(self, test_user_id):
        """测试: 通过 Mixin 存储交互"""
        run_id = str(uuid.uuid4())
        result = await AgentMemoryMixin.store_agent_conversation_interaction(
            user_id=test_user_id,
            application_id="test_app",
            agent_id="test_agent",
            run_id=run_id,
            messages="测试问题-通过Mixin存储",
            response="测试回答-通过Mixin存储",
        )
        assert result is not None

    @pytest.mark.asyncio
    async def test_retrieve_relevant_memories(self, test_user_id):
        """测试: 检索相关记忆 — retrieve_relevant_conversation_memories(query=...)"""
        results = await AgentMemoryMixin.retrieve_relevant_conversation_memories(
            query="订单物流",
            user_id=test_user_id,
            agent_id="test_agent",
            limit=5,
        )
        assert isinstance(results, list)


class TestMemoryEnabledAgent:
    """MemoryEnabledAgent 类"""

    @pytest.mark.asyncio
    async def test_memory_enabled_agent_methods(self, test_user_id):
        """测试: MemoryEnabledAgent 方法存在且可调用"""
        agent = MemoryEnabledAgent(
            application_id="test_app",
            agent_id="test_agent",
        )
        # 验证方法存在
        assert hasattr(agent, "store_interaction")
        assert hasattr(agent, "get_relevant_memories")
        assert hasattr(agent, "get_smart_filtered_memories")

        # 测试 store_interaction
        run_id = str(uuid.uuid4())
        result = await agent.store_interaction(
            user_id=test_user_id,
            thread_id=run_id,
            user_query="MemoryEnabledAgent测试问题",
            agent_response="MemoryEnabledAgent测试回答",
        )
        assert result is not None


class TestMemoryErrorHandling:
    """错误处理"""

    @pytest.mark.asyncio
    async def test_empty_user_id(self):
        """测试: 空 user_id 处理"""
        history = await memory_manager.get_conversation_history(
            user_id="",
            limit=5,
        )
        assert isinstance(history, list)  # 应返回空列表不崩溃

    @pytest.mark.asyncio
    async def test_large_limit(self):
        """测试: 大 limit 值不会崩溃"""
        history = await memory_manager.get_conversation_history(
            user_id="nonexistent_user_12345",
            limit=1000,
        )
        assert isinstance(history, list)

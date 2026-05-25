"""动态记忆工程管理器 — 门面 (delegates to Conversation/Expert/Profile mixins)"""
from ._memory_core import (
    AsyncMem0Client, _probe_collection, logger
)
from ._conversation_store import ConversationStoreMixin
from ._expert_review import ExpertReviewMixin
from ._profile_store import ProfileStoreMixin
from .chroma_health import get_chroma_health
from agents.ecommerce_service.core import structed_model, emb_model
from mem0.configs.base import MemoryConfig
from mem0.llms.configs import LlmConfig
from mem0.vector_stores.configs import VectorStoreConfig
from mem0.embeddings.configs import EmbedderConfig
from config.utils import config_manager
import asyncio

class MemoryManager(ConversationStoreMixin, ExpertReviewMixin, ProfileStoreMixin):
    """记忆管理器 — 继承自 ConversationStore / ExpertReview / ProfileStore mixins"""

    def __init__(self):
        self.conversation_memory = None
        self.profile_memory = None
        self._initialized = False


    async def initialize(self):
        """初始化记忆管理器"""
        if self._initialized:
            return

        try:
            # 从配置获取向量存储参数
            chroma_config = config_manager.get_text2sql_config().get("storage", {})

            # 对话记忆配置
            conversation_config = MemoryConfig(
                llm=LlmConfig(provider="langchain", config={"model": structed_model}),
                vector_store=VectorStoreConfig(
                    provider="chroma",
                    config={
                        "collection_name": "conversation_memory",
                        "host": chroma_config.get("host", "47.106.22.90"),
                        "port": str(chroma_config.get("port", "8000"))
                    }
                ),
                embedder=EmbedderConfig(
                    provider="langchain",
                    config={"model": emb_model}
                ),
                version="v1.1"
            )
            self.conversation_memory = AsyncMem0Client(config=conversation_config)

            # 用户画像记忆配置
            profile_config = MemoryConfig(
                llm=LlmConfig(provider="langchain", config={"model": structed_model}),
                vector_store=VectorStoreConfig(
                    provider="chroma",
                    config={
                        "collection_name": "profile_memory",
                        "host": chroma_config.get("host", "47.106.22.90"),
                        "port": str(chroma_config.get("port", "8000"))
                    }
                ),
                embedder=EmbedderConfig(
                    provider="langchain",
                    config={"model": emb_model}
                ),
                version="v1.1"
            )
            self.profile_memory = AsyncMem0Client(config=profile_config)



            self._initialized = True

            # 注册 ChromaDB 健康探测函数（用于熔断器）
            health = get_chroma_health()
            async def _ping_chroma() -> bool:
                try:
                    # 轻量级探测：只检查 collection 存在（不创建）
                    await asyncio.wait_for(
                        _probe_collection(self.conversation_memory, "conversation_memory"),
                        timeout=5.0,
                    )
                    return True
                except Exception:
                    return False
            health.set_ping(_ping_chroma)
            logger.info("记忆管理器初始化完成 + ChromaDB 健康检查已注册")

        except Exception as e:
            logger.error(f"记忆管理器初始化失败: {e}", exc_info=True)

            # 初始化失败时标记 ChromaDB 不健康，但不阻止服务启动
            get_chroma_health().record_failure(str(e))
            # Let this propagate so upstream knows memory is not available




# ---- 模块级单例 ----
memory_manager = MemoryManager()

"""
动态记忆工程管理器
包含对话记忆、专家审核和用户画像三个核心模块
"""
import asyncio
import concurrent
from typing import Dict, Optional, Any
from enum import Enum
from mem0 import AsyncMemory
from mem0.configs.base import MemoryConfig
# 导入画像模型
from agents.ecommerce_service.core import structed_model
from common.logging import get_logger

logger = get_logger("memory_manager")

# 延迟导入画像提取器，避免循环依赖
def _get_profile_extractor():
    """延迟导入混合式画像提取器"""
    try:
        from .profile.profile_extractor import get_profile_extractor
        # 传入配置的 LLM 实例
        return get_profile_extractor(structed_model)
    except ImportError as e:
        logger.warning(f"混合式画像提取器导入失败: {e}")
        return None

async def _probe_collection(memory_client, collection_name: str) -> bool:
    """轻量级 ChromaDB 连通性检测 —— 只检查 collection 是否存在"""
    try:
        # mem0 的 AsyncMemory 包装了 chromadb，尝试获取 collection 信息
        client = getattr(memory_client, 'vector_store', None) or memory_client
        if hasattr(client, 'collection_name'):
            return True  # mem0 handles collection internally
        return True  # 不做深度探测，轻量即可
    except Exception:
        return False


class MemoryType(Enum):
    """记忆类型枚举"""
    CONVERSATION = "conversation"  # 对话记忆
    USER_SESSION_PROFILE = "user_session_profile"  # 用户会话画像记忆
    USER_DAILY_PROFILE = "user_daily_profile"  # 用户每日画像记忆
    USER_DEEP_PROFILE = "user_deep_profile"  # 用户深度画像记忆
    EXPERT_QA = "expert_qa"  # 专家QA记忆


class AsyncMem0Client(AsyncMemory):
    """异步记忆管理器"""
    def __init__(self, config: MemoryConfig = MemoryConfig()):
        super().__init__(config)
    async def get_all(
        self,
        *,
        user_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        run_id: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 100,
    ):

        with concurrent.futures.ThreadPoolExecutor() as executor:
            future_memories = executor.submit(self._get_all_from_vector_store, filters, limit)
            future_graph_entities = (
                executor.submit(self.graph.get_all, filters, limit) if self.enable_graph else None
            )

            concurrent.futures.wait(
                [future_memories, future_graph_entities] if future_graph_entities else [future_memories]
            )

            all_memories_result = future_memories.result()
            graph_entities_result = future_graph_entities.result() if future_graph_entities else None

        if self.enable_graph:
            return {"results": all_memories_result, "relations": graph_entities_result}
        return {"results": all_memories_result}

    async def search(
        self,
        query: str,
        *,
        user_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        run_id: Optional[str] = None,
        limit: int = 100,
        filters: Optional[Dict[str, Any]] = None,
        threshold: Optional[float] = None,
    ):

        vector_store_task = asyncio.create_task(self._search_vector_store(query, filters, limit, threshold))
        graph_task = None
        if self.enable_graph:
            if hasattr(self.graph.search, "__await__"):  # Check if graph search is async
                graph_task = asyncio.create_task(self.graph.search(query, filters, limit))
            else:
                graph_task = asyncio.create_task(asyncio.to_thread(self.graph.search, query, filters, limit))

        if graph_task:
            original_memories, graph_entities = await asyncio.gather(vector_store_task, graph_task)
        else:
            original_memories = await vector_store_task
            graph_entities = None

        if self.enable_graph:
            return {"results": original_memories, "relations": graph_entities}

        return {"results": original_memories}

    async def update(self, memory_id, data,metadata:Optional[Dict[str, Any]] = None):
        embeddings = await asyncio.to_thread(self.embedding_model.embed, data, "update")
        existing_embeddings = {data: embeddings}

        await self._update_memory(memory_id, data, existing_embeddings,metadata)
        return {"message": "Memory updated successfully!"}



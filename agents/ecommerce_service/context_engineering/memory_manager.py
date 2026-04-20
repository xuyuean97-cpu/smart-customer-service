"""
动态记忆工程管理器
包含对话记忆、专家审核和用户画像三个核心模块
"""
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))
import json
import asyncio
import concurrent
from copy import deepcopy
from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum
from datetime import datetime, timezone, timedelta
from mem0 import AsyncMemory
from mem0.configs.base import MemoryConfig
from mem0.vector_stores.configs import VectorStoreConfig
from mem0.llms.configs import LlmConfig
from mem0.embeddings.configs import EmbedderConfig
# 导入画像模型
from .profile.user_profile_models import SessionProfile, DailyProfile, InsightProfile, CompleteUserProfile
from agents.ecommerce_service.core import structed_model, emb_model
from config.utils import config_manager
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
    

class MemoryManager:
    """动态记忆管理器"""
    
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
                        "host": chroma_config.get("host", "192.168.0.105"),
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
                        "host": chroma_config.get("host", "192.168.0.200"),
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
            logger.info("记忆管理器初始化完成")
            
        except Exception as e:
            logger.error(f"记忆管理器初始化失败: {e}", exc_info=True)
            raise
    
    async def store_conversation(
        self, 
        application_id: str,
        user_id: str, 
        run_id: str, 
        agent_id: str,
        messages,
        response: str,         
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        if not self._initialized:
            await self.initialize()
        base_metadata = deepcopy(metadata) if metadata else {}
        try:
            metadata = {
                "agent_memory_type": MemoryType.CONVERSATION.value,
                "response": response,  
                "application_id": application_id,  
                "expert_verified": False,  
                "expert_id": "",  
                "expert_corrected_response": "",  
                "quality_score": 0.0, 
                "user_approved": 0,
            }
            
            result = await self.conversation_memory.add(
                messages=messages, 
                user_id=user_id,
                agent_id=agent_id,
                run_id=run_id,
                metadata={**base_metadata, **metadata},
                infer=False
            )
            memory_id = result.get('results', [{}])[0].get('id') if result.get('results') else None
            logger.info(f"对话记忆已存储: {memory_id}")
            logger.info(f"存储对话记忆详情: application_id={application_id}, user_id={user_id}, run_id={run_id}, agent_id={agent_id}, response={response}, metadata={metadata}")
            return memory_id
            
        except Exception as e:
            logger.error(f"存储对话记忆失败: {e}", exc_info=True)
            raise
    # async def store_conversation(self, user_id: str, messages: Any, **kwargs):
    #     """
    #     存储对话到长期记忆 
    #     """
    #     logger.error(f"【抓包测试-正在保存记忆】user_id: {user_id}, message: {messages}, memory_type: conversation")
    #     if not self._initialized or self.conversation_memory is None:
    #         logger.info("检测到记忆模块未初始化，正在尝试懒加载...")
    #         await self.initialize()
    #     try:
    #         if not messages:
    #             return

    #         # 如果传入的不是列表，强制包装成列表以便循环处理
    #         if not isinstance(messages, list):
    #             messages = [messages]

    #         # --- 数据清洗步骤 ---
    #         cleaned_messages = []
    #         for msg in messages:
    #             role = "assistant" # 默认角色
    #             content = None
                
    #             # 1. 【核心修复】多类型判断逻辑
    #             if isinstance(msg, str):
    #                 # 如果 msg 是字符串 (报错根源)，直接把字符串作为内容
    #                 content = msg
    #                 role = "user"  # 字符串默认当作用户输入
    #             elif hasattr(msg, 'content'):
    #                 # 如果是 LangChain 的 AIMessage 或 HumanMessage
    #                 content = str(msg.content)
    #                 if hasattr(msg, 'type'):
    #                     role = "user" if msg.type == "human" else "assistant"
    #             elif isinstance(msg, dict):
    #                 # 如果是标准的字典格式
    #                 role = msg.get("role", "user")
    #                 content = msg.get("content")
    #                 # 处理工具调用
    #                 if content is None and "tool_calls" in msg:
    #                     import json
    #                     content = f"[Tool Call]: {json.dumps(msg['tool_calls'], ensure_ascii=False)}"
    #             else:
    #                 # 兜底：强转字符串
    #                 content = str(msg)

    #             # 2. 如果提取后的 content 依然为空，尝试处理 tool_calls（针对对象格式）
    #             if content is None or content == "None":
    #                 if hasattr(msg, 'additional_kwargs') and "tool_calls" in msg.additional_kwargs:
    #                     import json
    #                     content = f"[Tool Call]: {json.dumps(msg.additional_kwargs['tool_calls'], ensure_ascii=False)}"
    #                 else:
    #                     continue # 既没内容也没工具调用，跳过

    #             # 3. 强制转换为字符串类型并过滤
    #             content = str(content)
    #             if not content.strip():
    #                 continue

    #             cleaned_messages.append({
    #                 "role": role,
    #                 "content": content
    #             })
            
    #         # --- 结束清洗 ---

    #         if not cleaned_messages:
    #             return

    #         # 调用底层的记忆引擎 (mem0 或其他)
    #         result = await self.conversation_memory.add(
    #             messages=cleaned_messages,
    #             user_id=str(user_id)
    #         )
    #         return result

    #     except Exception as e:
    #         # 【绝对关键】拦截所有报错，确保记忆存储即便失败，也不要让主对话流程卡死
    #         print(f"ERROR - 存储对话记忆失败（已拦截防止流程崩溃）: {str(e)}")
    #         # 这里不要 raise，让主程序继续往下走，把回答发给用户
    #         return None
    
    async def get_conversation_history(
        self, 
        application_id: Optional[str] = None,
        user_id: Optional[str] = None,
        run_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        query: Optional[str] = None,
        response: Optional[str] = None,
        expert_verified: Optional[bool] = None,
        user_approved: Optional[bool] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 5000,
    ) -> List[Dict[str, Any]]:
        if not self._initialized:
            await self.initialize()
        
        try:
            # 构建过滤条件列表 - 按照用户提供的案例格式
            filter_conditions = []
            
            # 基础条件：记忆类型
            filter_conditions.append({"agent_memory_type": {"$eq": MemoryType.CONVERSATION.value}})
            
            # 可选条件
            if user_id:
                filter_conditions.append({"user_id": {"$eq": user_id}})
            if agent_id:
                filter_conditions.append({"agent_id": {"$eq": agent_id}})
            if application_id:
                filter_conditions.append({"application_id": {"$eq": application_id}})
            if run_id:
                filter_conditions.append({"run_id": {"$eq": run_id}})
            if expert_verified is not None:
                filter_conditions.append({"expert_verified": {"$eq": expert_verified}})
            if user_approved is not None:
                filter_conditions.append({"user_approved": {"$eq": user_approved}})
            if query:
                filter_conditions.append({"data": {"$eq": query}})
            if response:
                filter_conditions.append({"response": {"$eq": response}})
            
            # 构建最终过滤器
            if len(filter_conditions) == 1:
                filters = filter_conditions[0]
            else:
                filters = {"$and": filter_conditions}
            
            # 使用 get_all 进行查询
            result = await self.conversation_memory.get_all(filters=filters, limit=limit)
            
            # 按照案例中的模式处理返回结果
            if isinstance(result, dict) and 'results' in result:
                all_memories = result['results']
                # 如果返回的是协程，按照案例进行await
                import inspect
                if inspect.iscoroutine(all_memories):
                    all_memories = await all_memories
            else:
                logger.warning(f"意外的get_all返回格式: {type(result)}")
                all_memories = []
            
            conversations = []
            for memory in all_memories:
                metadata = memory.get('metadata', {})
                
                # 时间过滤（在数据库层面无法高效过滤，所以在这里手动过滤）
                if start_date or end_date:
                    memory_time = None
                    if 'created_at' in memory:
                        try:
                            # 解析数据库中的时间字符串（带时区信息）
                            created_at_str = memory['created_at']
                            if created_at_str.endswith('Z'):
                                # 处理UTC时间标识
                                memory_time = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
                            else:
                                # 处理已经包含时区信息的时间字符串
                                memory_time = datetime.fromisoformat(created_at_str)
                        except Exception as e:
                            logger.debug(f"时间解析失败: {created_at_str} - {e}")
                            memory_time = None
                    
                    if memory_time:
                        # 比较时间（现在传入的start_date和end_date都已经是带时区的）
                        if start_date:
                            # 将memory_time转换为UTC进行比较
                            memory_time_utc = memory_time.astimezone(start_date.tzinfo)
                            if memory_time_utc < start_date:
                                continue
                        
                        if end_date:
                            # 将memory_time转换为UTC进行比较  
                            memory_time_utc = memory_time.astimezone(end_date.tzinfo)
                            if memory_time_utc > end_date:
                                continue
                
                # 构造返回数据
                conversation_data = {
                    "memory_id": memory.get('id'),
                    "user_id": memory.get('user_id'),
                    "application_id": metadata.get('application_id', ''),
                    "run_id": memory.get('run_id', ''),
                    "agent_id": memory.get('agent_id', ''),
                    "query": memory.get('memory', ''),
                    "response": metadata.get('response', ''),
                    "expert_verified": metadata.get('expert_verified', False),
                    "expert_id": metadata.get('expert_id', ''),
                    "expert_corrected_response": metadata.get('expert_corrected_response', ''),
                    "quality_score": metadata.get('quality_score'),
                    "user_approved": metadata.get('user_approved', False),
                    "query_source": metadata.get('query_source', '小程序'),
                    "query_device": metadata.get('query_device', '手机'),
                    "query_ip": metadata.get('query_ip', ''),
                    "network_type": metadata.get('network_type', '5g'),
                    "retrieval_content": metadata.get('retrieval_content', ''),
                    "retrieval_source": metadata.get('retrieval_source', ''),
                    "retrieval_score": metadata.get('retrieval_score', 0.0),
                    "retrieval_images": metadata.get('retrieval_images', ''),
                    "retrieval_query_list": metadata.get('retrieval_query_list', []),
                    "pre_retrieval_content": metadata.get('pre_retrieval_content', ''),
                    "pre_retrieval_source": metadata.get('pre_retrieval_source', ''),
                    "pre_retrieval_score": metadata.get('pre_retrieval_score', 0.0),
                    "pre_retrieval_query_list": metadata.get('pre_retrieval_query_list', []),
                    "created_at": memory.get('created_at'),
                    "updated_at": memory.get('updated_at')
                }
                conversations.append(conversation_data)
            
            # 按创建时间排序
            conversations.sort(key=lambda x: x.get('created_at', ''), reverse=True)
            conversations = conversations[:limit]
            logger.info(f"对话历史查询完成: 过滤条件={filters}, 获取={len(all_memories)}, 返回={len(conversations)}")
            return conversations
            
        except Exception as e:
            logger.error(f"获取对话历史失败: {e}", exc_info=True)
            return []
    
    async def handle_user_feedback(
        self,
        response: str,
        user_approved: Optional[int] = 0,
    ) -> bool:
        """
        用户点赞对话
        
        Args:
            response: 系统回复
            user_approved: 是否用户审核通过
            
        Returns:
            是否成功更新
        """
        if not self._initialized:
            await self.initialize()
    
        try:
            his_conversation = self.get_conversation_history(response=response)
            memory_id = his_conversation[0]['memory_id']
            query = his_conversation[0]['query']
            # 构建更新的元数据
            updated_metadata = {
                "user_approved": user_approved,
            }
        
            
            await self.conversation_memory.update(
                memory_id=memory_id,
                data=query,
                metadata=updated_metadata
            )
            
            logger.info(f"用户点赞完成: memory_id={memory_id}, approved={user_approved}")
            return True
            
        except Exception as e:
            logger.error(f"专家审核失败: {e}", exc_info=True)
            return False

    async def expert_review_conversation(
        self,
        memory_id: str,
        query: str,
        expert_approved: Optional[bool] = True,
        expert_id: Optional[str] = None,
        quality_score: Optional[float] = None,
        corrected_response: Optional[str] = None  
    ) -> bool:
        """
        
        Args:
            memory_id: 记忆ID (mem0返回的memory_id)
            expert_approved: 是否专家审核通过
            quality_score: 质量评分 (0-1, 可选)
            corrected_response: 专家修正的回答内容 (可选)
            expert_id: 审核专家ID (可选)
            
        Returns:
            是否成功更新
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            # 构建更新的元数据
            updated_metadata = {
                "expert_verified": expert_approved,
            }
            if quality_score is not None:
                updated_metadata["quality_score"] = quality_score    
            if expert_id:
                updated_metadata["expert_id"] = expert_id
            if corrected_response:
                updated_metadata["expert_corrected_response"] = corrected_response
            
            await self.conversation_memory.update(
                memory_id=memory_id,
                data=query,
                metadata=updated_metadata
            )
            
            logger.info(f"专家审核完成: memory_id={memory_id}, approved={expert_approved}, score={quality_score}")
            return True
            
        except Exception as e:
            logger.error(f"专家审核失败: {e}", exc_info=True)
            return False

    
    async def batch_expert_review(
        self,
        review_items: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        批量专家审核 - 调用单个 expert_review_conversation 方法
        
        Args:
            review_items: 审核项目列表，每个项目包含:
                - memory_id: 记忆ID
                - expert_approved: 是否通过
                - quality_score: 质量评分
                - corrected_response: 修正回答 (可选)
                - expert_id: 审核专家ID (可选)
                
        Returns:
            批量更新结果统计
        """
        if not self._initialized:
            await self.initialize()
        
        success_count = 0
        failed_count = 0
        
        try:
            # 逐个调用 expert_review_conversation 方法
            for item in review_items:
                try:
                    memory_id = item.get('memory_id')
                    query = item.get('query')
                    expert_approved = item.get('expert_approved', False)
                    quality_score = item.get('quality_score')
                    corrected_response = item.get('corrected_response')
                    expert_id = item.get('expert_id')
                    
                    # 调用单个审核方法
                    result = await self.expert_review_conversation(
                        memory_id=memory_id,
                        query=query,
                        expert_approved=expert_approved,
                        quality_score=quality_score,
                        corrected_response=corrected_response,
                        expert_id=expert_id
                    )
                    
                    if result:
                        success_count += 1
                    else:
                        failed_count += 1
                        
                except Exception as single_error:
                    logger.error(f"单个审核失败: {item.get('memory_id')} - {single_error}")
                    failed_count += 1
            
            result = {
                "total_items": len(review_items),
                "update_success": success_count,
                "update_failed": failed_count,
                "timestamp": datetime.now().isoformat(),
            }
            
            logger.info(f"批量专家审核完成: {result}")
            return result
            
        except Exception as e:
            logger.error(f"批量专家审核失败: {e}", exc_info=True)
            return {
                "total_items": len(review_items),
                "update_success": success_count,
                "update_failed": failed_count,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def add_expert_qa(
        self,
        question: str,
        answer: str,
        expert_id: Optional[str] = None,
        application_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        添加全新的专家QA对
        
        Args:
            question: 问题内容
            answer: 答案内容
            expert_id: 专家ID (可选)
            application_id: 应用名称 (可选)
            metadata: 额外元数据 (可选)
            
        Returns:
            memory_id: 记忆ID
        """
        if not self._initialized:
            await self.initialize()
        
        base_metadata = deepcopy(metadata) if metadata else {}
        
        try:
            expert_qa_metadata = {
                "agent_memory_type": MemoryType.EXPERT_QA.value,
                "application_id": application_id or "",
                "expert_id": expert_id or "",
                "question": question,
                "answer": answer
            }
            
            # 构造消息内容用于向量化存储
            messages = [
                {"role": "user", "content": question},
            ]
            
            result = await self.conversation_memory.add(
                messages=messages,
                user_id="expert_system",  # 使用特殊的用户ID标识专家系统
                metadata={**base_metadata, **expert_qa_metadata},
                infer=False
            )
            
            memory_id = result.get('results', [{}])[0].get('id') if result.get('results') else None
            logger.info(f"专家QA已添加: {memory_id}, 专家ID: {expert_id}")
            return memory_id
            
        except Exception as e:
            logger.error(f"添加专家QA失败: {e}", exc_info=True)
            raise
    
    async def get_expert_qa_list(
        self,
        application_id: Optional[str] = None,
        expert_id: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        查询专家QA列表
        
        Args:
            application_id: 应用名称筛选 (可选)
            expert_id: 专家ID筛选 (可选)
            limit: 返回数量限制
            
        Returns:
            专家QA列表
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            # 构建过滤条件
            filter_conditions = []
            
            # 基础条件：记忆类型
            filter_conditions.append({"agent_memory_type": {"$eq": MemoryType.EXPERT_QA.value}})
            
            # 可选条件
            if application_id:
                filter_conditions.append({"application_id": {"$eq": application_id}})
            if expert_id:
                filter_conditions.append({"expert_id": {"$eq": expert_id}})
            
            # 构建最终过滤器
            if len(filter_conditions) == 1:
                filters = filter_conditions[0]
            else:
                filters = {"$and": filter_conditions}
            
            result = await self.conversation_memory.get_all(
                filters=filters,
                limit=limit
            )
            
            # 处理返回结果
            if isinstance(result, dict) and 'results' in result:
                results = result['results']
                import inspect
                if inspect.iscoroutine(results):
                    results = await results
            else:
                logger.warning(f"意外的返回格式: {type(result)}")
                results = []
            
            expert_qa_list = []
            for result_item in results:
                metadata = result_item.get('metadata', {})
                
                qa_data = {
                    "memory_id": result_item.get('id'),
                    "expert_id": metadata.get('expert_id', ''),
                    "application_id": metadata.get('application_id', ''),
                    "question": metadata.get('question', ''),
                    "answer": metadata.get('answer', ''),
                    "tags": metadata.get('tags', ''),
                    "images": metadata.get('images', ''),
                    "services": metadata.get('services', ''),
                    "created_at": result_item.get('created_at'),
                    "updated_at": result_item.get('updated_at'),
                }
                expert_qa_list.append(qa_data)
            
            logger.info(f"专家QA查询完成: 条件={filters}, 结果数量={len(expert_qa_list)}")
            return expert_qa_list
            
        except Exception as e:
            logger.error(f"查询专家QA失败: {e}", exc_info=True)
            return []
    
    async def update_expert_qa(
        self,
        memory_id: str,
        question: Optional[str] = None,
        answer: Optional[str] = None,
        expert_id: Optional[str] = None,
        tags: Optional[str] = None,
        images: Optional[str] = None,
        services: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        修改专家QA
        
        Args:
            memory_id: 记忆ID
            question: 新的问题内容 (可选)
            answer: 新的答案内容 (可选)
            expert_id: 新的专家ID (可选)
            tags: 新的标签 (可选)
            images: 新的图片信息 (可选)
            services: 新的服务信息 (可选)
            metadata: 额外元数据 (可选)
            
        Returns:
            是否成功更新
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            # 构建更新的元数据
            updated_metadata = {}
            if expert_id is not None:
                updated_metadata["expert_id"] = expert_id
            if question is not None:
                updated_metadata["question"] = question
            if answer is not None:
                updated_metadata["answer"] = answer
            if tags is not None:
                updated_metadata["tags"] = tags
            if images is not None:
                updated_metadata["images"] = images
            if services is not None:
                updated_metadata["services"] = services
            
            # 如果有额外的元数据，合并进去
            if metadata:
                updated_metadata.update(metadata)
            
            # 如果问题内容有更新，需要更新记忆的主要内容
            updated_content = question if question is not None else ""
            
            await self.conversation_memory.update(
                memory_id=memory_id,
                data=updated_content,
                metadata=updated_metadata
            )
            
            logger.info(f"专家QA更新完成: memory_id={memory_id}")
            return True
            
        except Exception as e:
            logger.error(f"更新专家QA失败: {e}", exc_info=True)
            return False
    
    async def delete_expert_qa(
        self,
        memory_id: str
    ) -> bool:
        """
        删除专家QA
        
        Args:
            memory_id: 记忆ID
            
        Returns:
            是否成功删除
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            # 使用mem0的delete方法删除记忆
            await self.conversation_memory.delete(memory_id=memory_id)
            
            logger.info(f"专家QA删除完成: memory_id={memory_id}")
            return True
            
        except Exception as e:
            logger.error(f"删除专家QA失败: {e}", exc_info=True)
            return False
    
    async def batch_delete_expert_qa(
        self,
        memory_ids: List[str]
    ) -> Dict[str, Any]:
        """
        批量删除专家QA
        
        Args:
            memory_ids: 记忆ID列表
            
        Returns:
            批量删除结果统计
        """
        if not self._initialized:
            await self.initialize()
        
        success_count = 0
        failed_count = 0
        failed_ids = []
        
        try:
            for memory_id in memory_ids:
                try:
                    success = await self.delete_expert_qa(memory_id)
                    if success:
                        success_count += 1
                    else:
                        failed_count += 1
                        failed_ids.append(memory_id)
                except Exception as single_error:
                    logger.error(f"单个删除失败: {memory_id} - {single_error}")
                    failed_count += 1
                    failed_ids.append(memory_id)
            
            result = {
                "total_items": len(memory_ids),
                "delete_success": success_count,
                "delete_failed": failed_count,
                "failed_ids": failed_ids,
                "timestamp": datetime.now().isoformat(),
            }
            
            logger.info(f"批量删除专家QA完成: {result}")
            return result
            
        except Exception as e:
            logger.error(f"批量删除专家QA失败: {e}", exc_info=True)
            return {
                "total_items": len(memory_ids),
                "delete_success": success_count,
                "delete_failed": failed_count,
                "failed_ids": failed_ids,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }

    async def search_conversations(
        self,
        query: str,
        application_id: Optional[str] = None,
        user_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        expert_verified: Optional[bool] = None,
        user_approved: Optional[bool] = None,
        min_quality_score: Optional[float] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """        
        Args:
            query: 查询文本
            application_id: 应用名称筛选 (可选)
            user_id: 用户ID筛选 (可选)
            agent_id: 智能体名称筛选 (可选)
            expert_verified: 专家校验状态筛选 (可选)
            user_approved: 用户校验状态筛选 (可选)
            min_quality_score: 最低质量评分筛选 (可选)
            limit: 返回数量限制
            
        Returns:
            相似对话记录列表
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            filter_conditions = []
            
            # 基础条件：记忆类型
            filter_conditions.append({"agent_memory_type": {"$eq": MemoryType.CONVERSATION.value}})
            
            # 可选条件
            if user_id:
                filter_conditions.append({"user_id": {"$eq": user_id}})
            if agent_id:
                filter_conditions.append({"agent_id": {"$eq": agent_id}})
            if application_id:
                filter_conditions.append({"application_id": {"$eq": application_id}})
            if expert_verified is not None:
                filter_conditions.append({"expert_verified": {"$eq": expert_verified}})
            if user_approved is not None:
                filter_conditions.append({"user_approved": {"$eq": user_approved}})
            
            # 构建最终过滤器
            if len(filter_conditions) == 1:
                filters = filter_conditions[0]
            else:
                filters = {"$and": filter_conditions}
            
            search_results = await self.conversation_memory.search(
                query=query,
                filters=filters,
                limit=limit
            )
            
            conversations = []
            # 处理不同版本 API 的返回格式 - 按照案例模式
            if isinstance(search_results, dict) and 'results' in search_results:
                results = search_results['results']
                # 如果返回的是协程，按照案例进行await
                import inspect
                if inspect.iscoroutine(results):
                    results = await results
            else:
                logger.warning(f"意外的search返回格式: {type(search_results)}")
                results = []
            
            for result in results:
                metadata = result.get('metadata', {})
                
                # 只需要手动应用质量评分过滤，其他条件已在数据库层面过滤
                if min_quality_score is not None and (metadata.get('quality_score') or 0) < min_quality_score:
                    continue
                
                # 构造返回数据
                conversation_data = {
                    "memory_id": result.get('id'),
                    "user_id": result.get('user_id'),
                    "agent_id": result.get('agent_id', ''),
                    "run_id": result.get('run_id', ''),
                    "application_id": metadata.get('application_id', ''),
                    "query": result.get('memory', ''),
                    "response": metadata.get('response', ''), 
                    "expert_verified": metadata.get('expert_verified', False),
                    "expert_id": metadata.get('expert_id', ''),
                    "expert_corrected_response": metadata.get('expert_corrected_response', ''),
                    "quality_score": metadata.get('quality_score'),
                    "user_approved": metadata.get('user_approved', False),
                    "relevance_score": result.get('score', 0.0),
                    "created_at": result.get('created_at'),
                    "metadata": metadata
                }
                conversations.append(conversation_data)
                
                # 达到目标数量就停止
                if len(conversations) >= limit:
                    break
            
            logger.info(f"相似度搜索完成: query='{query}', 结果数量={len(conversations)}")
            return conversations
            
        except Exception as e:
            logger.error(f"相似度搜索失败: {e}", exc_info=True)
            return []

    # async def search_expert_qa(
    #     self,
    #     query: str,
    #     application_id: Optional[str] = None,
    #     expert_id: Optional[str] = None,
    #     tags: Optional[List[str]] = None,
    #     services: Optional[List[str]] = None,
    #     limit: int = 50
    # ) -> List[Dict[str, Any]]:
    #     """
    #     检索专家QA对
        
    #     Args:
    #         query: 查询文本
    #         application_id: 应用名称筛选 (可选)
    #         expert_id: 专家ID筛选 (可选)
    #         tags: 标签筛选 (可选)
    #         services: 服务筛选 (可选)
    #         limit: 返回数量限制
            
    #     Returns:
    #         相似专家QA记录列表
    #     """
    #     if not self._initialized:
    #         await self.initialize()
        
    #     try:
    #         filter_conditions = []
            
    #         # 基础条件：记忆类型
    #         filter_conditions.append({"agent_memory_type": {"$eq": MemoryType.EXPERT_QA.value}})
            
    #         # 可选条件
    #         if application_id:
    #             filter_conditions.append({"application_id": {"$eq": application_id}})
    #         if expert_id:
    #             filter_conditions.append({"expert_id": {"$eq": expert_id}})
    #         if tags:
    #             # 对于包含多个标签的情况，检查是否存在任意一个标签
    #             filter_conditions.append({"tags": {"$in": tags}})
    #         if services:
    #             # 对于包含多个服务的情况，检查是否存在任意一个服务
    #             filter_conditions.append({"services": {"$in": services}})
            
    #         # 构建最终过滤器
    #         if len(filter_conditions) == 1:
    #             filters = filter_conditions[0]
    #         else:
    #             filters = {"$and": filter_conditions}
            
    #         search_results = await self.conversation_memory.search(
    #             query=query,
    #             filters=filters,
    #             limit=limit
    #         )
            
    #         expert_qa_list = []
    #         # 处理不同版本 API 的返回格式 - 按照案例模式
    #         if isinstance(search_results, dict) and 'results' in search_results:
    #             results = search_results['results']
    #             # 如果返回的是协程，按照案例进行await
    #             import inspect
    #             if inspect.iscoroutine(results):
    #                 results = await results
    #         else:
    #             logger.warning(f"意外的search返回格式: {type(search_results)}")
    #             results = []
            
    #         for result in results:
    #             metadata = result.get('metadata', {})
                
    #             # 构造返回数据
    #             expert_qa_data = {
    #                 "memory_id": result.get('id'),
    #                 "user_id": result.get('user_id'),
    #                 "expert_id": metadata.get('expert_id', ''),
    #                 "application_id": metadata.get('application_id', ''),
    #                 "question": metadata.get('question', ''),
    #                 "answer": metadata.get('answer', ''),
    #                 "tags": metadata.get('tags', ''),
    #                 "images": metadata.get('images', ''),
    #                 "services": metadata.get('services', ''),
    #                 "relevance_score": result.get('score', 0.0),
    #                 "created_at": result.get('created_at'),
    #                 "updated_at": result.get('updated_at'),
    #                 "metadata": metadata
    #             }
    #             expert_qa_list.append(expert_qa_data)
                
    #             # 达到目标数量就停止
    #             if len(expert_qa_list) >= limit:
    #                 break
            
    #         return expert_qa_list
            
    #     except Exception as e:
    #         logger.error(f"专家QA相似度搜索失败: {e}", exc_info=True)
    #         return []
    async def search_expert_qa(
        self,
        query: str,
        application_id: Optional[str] = None,
        expert_id: Optional[str] = None,
        tags: Optional[List[str]] = None,
        services: Optional[List[str]] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        检索专家QA对
        """
        # --- ✅ 新增修复代码：防止 query 为空导致 API 报错 ---
        if not query or not isinstance(query, str) or not query.strip():
            # logger.warning(f"跳过检索，因为 query 无效: {query}")
            return []
        # -----------------------------------------------

        if not self._initialized:
            await self.initialize()
        
        try:
            filter_conditions = []
            
            # 基础条件：记忆类型
            filter_conditions.append({"agent_memory_type": {"$eq": MemoryType.EXPERT_QA.value}})
            
            # 可选条件
            if application_id:
                filter_conditions.append({"application_id": {"$eq": application_id}})
            if expert_id:
                filter_conditions.append({"expert_id": {"$eq": expert_id}})
            if tags:
                filter_conditions.append({"tags": {"$in": tags}})
            if services:
                filter_conditions.append({"services": {"$in": services}})
            
            # 构建最终过滤器
            if len(filter_conditions) == 1:
                filters = filter_conditions[0]
            else:
                filters = {"$and": filter_conditions}
            
            search_results = await self.conversation_memory.search(
                query=query,
                filters=filters,
                limit=limit
            )
            
            expert_qa_list = []
            # 处理不同版本 API 的返回格式
            if isinstance(search_results, dict) and 'results' in search_results:
                results = search_results['results']
                import inspect
                if inspect.iscoroutine(results):
                    results = await results
            else:
                # 注意：mem0 的 search 有时直接返回 list，取决于版本
                results = search_results if isinstance(search_results, list) else []
            
            for result in results:
                metadata = result.get('metadata', {})
                
                # 构造返回数据
                expert_qa_data = {
                    "memory_id": result.get('id'),
                    "user_id": result.get('user_id'),
                    "expert_id": metadata.get('expert_id', ''),
                    "application_id": metadata.get('application_id', ''),
                    "question": metadata.get('question', ''),
                    "answer": metadata.get('answer', ''),
                    "tags": metadata.get('tags', ''),
                    "images": metadata.get('images', ''),
                    "services": metadata.get('services', ''),
                    "relevance_score": result.get('score', 0.0),
                    "created_at": result.get('created_at'),
                    "updated_at": result.get('updated_at'),
                    "metadata": metadata
                }
                expert_qa_list.append(expert_qa_data)
                
                if len(expert_qa_list) >= limit:
                    break
            
            return expert_qa_list
            
        except Exception as e:
            # 建议把 logger 改为 logging.getLogger(__name__) 获取的实例
            # logger.error(f"专家QA相似度搜索失败: {e}", exc_info=True)
            print(f"专家QA相似度搜索失败: {e}") # 临时打印
            return []
    async def get_expert_approved_examples(
        self, 
        query: str, 
        application_id: Optional[str] = None,
        user_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        user_approved: Optional[bool] = None,
        min_quality_score: float = 0.8,
        limit: int = 10,
    ) -> List[Dict[str, str]]:
        """
        从对话记忆中获取专家审核的优质QA作为prompt examples
        保持对话的时序性和完整性
        
        Args:
            query: 当前查询，用于相似度匹配
            application_id: 应用名称筛选 (可选)
            user_id: 用户ID筛选 (可选)
            agent_id: 智能体名称筛选 (可选)
            user_approved: 用户校验状态筛选 (可选)
            min_quality_score: 最低质量评分
            limit: 返回数量
            
        Returns:
            优质QA示例列表
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            # 使用相似度搜索专家审核通过的对话
            results = await self.search_conversations(
                query=query,
                application_id=application_id,
                user_id=user_id,
                agent_id=agent_id,
                expert_verified=True,
                user_approved=user_approved,
                min_quality_score=min_quality_score,
                limit=limit
            )
            
            examples = []
            for result in results:
                # 获取用户查询
                user_query = result.get('query', '')
                
                # 优先使用专家纠正的回答，否则使用原始回答
                assistant_response = result.get('metadata', {}).get('expert_corrected_response')
                if not assistant_response:
                    assistant_response = result.get('response', '')
                                
                if user_query and assistant_response:
                    examples.append({
                        "user": user_query,
                        "assistant": assistant_response,
                        "quality_score": result.get('quality_score', 0),
                        "memory_id": result.get('memory_id'),
                        "agent_name": result.get('agent_name'),
                        "expert_corrected": bool(result.get('metadata', {}).get('expert_corrected_response'))
                    })
                    
                if len(examples) >= limit:
                    break
            
            logger.info(f"获取到 {len(examples)} 个优质QA示例")
            return examples
            
        except Exception as e:
            logger.error(f"获取优质QA示例失败: {e}", exc_info=True)
            return []
    
    async def get_smart_filtered_memories(
        self,
        query: str,
        user_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        application_id: Optional[str] = None,
        user_approved: Optional[bool] = None,
        min_quality_score: float = 0.7,
        similarity_weight: float = 0.5,
        time_weight: float = 0.2,
        quality_weight: float = 0.3,
        time_decay_days: int = 30,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        智能记忆筛选 - 基于多因子综合评分的记忆检索
        
        综合考虑因素：
        1. 向量相似度 (similarity_weight)
        2. 时间遗忘因子 (time_weight) - 越新的记忆权重越高
        3. 专家评分 (quality_weight)
        
        Args:
            query: 查询文本
            user_id: 用户ID筛选 (可选)
            agent_id: 智能体名称筛选 (可选)
            application_id: 应用名称筛选 (可选)
            user_approved: 用户校验状态筛选 (可选)
            limit: 返回数量
            min_quality_score: 最低质量评分
            similarity_weight: 相似度权重 (默认0.5)
            time_weight: 时间权重 (默认0.2)
            quality_weight: 质量权重 (默认0.3)
            time_decay_days: 时间衰减周期天数 (默认30天)
            
        Returns:
            按综合得分排序的记忆列表
        """
        if not self._initialized:
            await self.initialize()
        
        # 权重归一化
        total_weight = similarity_weight + time_weight + quality_weight
        if total_weight != 1.0:
            similarity_weight /= total_weight
            time_weight /= total_weight
            quality_weight /= total_weight
            logger.warning(f"权重已归一化: similarity={similarity_weight:.2f}, time={time_weight:.2f}, quality={quality_weight:.2f}")
        
        try:
            candidate_limit = min(limit * 5, 100)
            
            # 搜索专家审核通过的对话
            results = await self.search_conversations(
                query=query,
                application_id=application_id,
                user_id=user_id,
                agent_id=agent_id,
                expert_verified=True,
                user_approved=user_approved,
                min_quality_score=min_quality_score,
                limit=candidate_limit,
            )
            
            if not results:
                logger.info("未找到符合条件的专家审核记忆")
                return []
            
            # 计算当前时间用于时间衰减
            current_time = datetime.now()
            scored_memories = []
            
            for result in results:
                try:
                    # 1. 获取相似度得分 (已归一化到0-1)
                    similarity_score = result.get('relevance_score', 0.0)
                    
                    # 2. 计算时间衰减因子
                    created_at_str = result.get('created_at', '')
                    time_score = 0.0
                    
                    if created_at_str:
                        try:
                            # 解析时间字符串
                            if 'T' in created_at_str:
                                # ISO格式: 2024-01-01T12:00:00
                                created_at = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
                            else:
                                # 简单格式: 2024-01-01
                                created_at = datetime.strptime(created_at_str[:19], '%Y-%m-%d %H:%M:%S')
                            
                            # 计算时间差（天数）
                            time_diff = (current_time - created_at).days
                            
                            # 时间衰减计算: 使用指数衰减，新记忆得分更高
                            # time_score = exp(-time_diff / time_decay_days)
                            import math
                            time_score = math.exp(-time_diff / time_decay_days)
                            time_score = max(0.0, min(1.0, time_score))  # 限制在0-1范围
                            
                        except Exception as time_error:
                            logger.debug(f"时间解析失败: {created_at_str} - {time_error}")
                            time_score = 0.5  # 默认中等时间得分
                    
                    # 3. 获取专家质量评分 (已在0-1范围)
                    quality_score = result.get('quality_score', 0.0) or 0.0
                    
                    # 4. 计算综合得分
                    composite_score = (
                        similarity_score * similarity_weight +
                        time_score * time_weight +
                        quality_score * quality_weight
                    )
                    
                    # 构造返回数据
                    memory_data = {
                        "memory_id": result.get('memory_id'),
                        "user_id": result.get('user_id'),
                        "agent_id": result.get('agent_id', ''),
                        "run_id": result.get('run_id', ''),
                        "application_id": result.get('application_id', ''),
                        "query": result.get('query', ''),
                        "response": result.get('response', ''),
                        "expert_verified": result.get('expert_verified', False),
                        "expert_id": result.get('expert_id', ''),
                        "user_approved": result.get('user_approved', False),
                        "quality_score": quality_score,
                        "created_at": result.get('created_at'),
                        "metadata": result.get('metadata', {}),
                        
                        # 评分详情
                        "similarity_score": similarity_score,
                        "time_score": time_score,
                        "composite_score": composite_score,
                        "score_breakdown": {
                            "similarity": similarity_score,
                            "time_factor": time_score,
                            "quality": quality_score,
                            "weights": {
                                "similarity": similarity_weight,
                                "time": time_weight,
                                "quality": quality_weight
                            }
                        }
                    }
                    
                    # 优先使用专家纠正的回答
                    if result.get('metadata', {}).get('expert_corrected_response'):
                        memory_data["response"] = result['metadata']['expert_corrected_response']
                        memory_data["expert_corrected"] = True
                    else:
                        memory_data["expert_corrected"] = False
                    
                    scored_memories.append(memory_data)
                    
                except Exception as scoring_error:
                    logger.error(f"记忆评分计算失败: {scoring_error}")
                    continue
            
            # 按综合得分降序排序
            scored_memories.sort(key=lambda x: x['composite_score'], reverse=True)
            
            # 返回TopK结果
            top_memories = scored_memories[:limit]
            
            logger.info(f"智能记忆筛选完成: 候选数量={len(results)}, 有效数量={len(scored_memories)}, TopK={len(top_memories)}")

            return top_memories
            
        except Exception as e:
            logger.error(f"智能记忆筛选失败: {e}", exc_info=True)
            return []
     
    # ============================== 画像提取相关方法 ==============================
    async def get_user_profile(
        self,
        user_id: str,
        application_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        获取用户画像
        优先获取最新的深度画像，如果没有则尝试获取每日画像或会话画像
        如果都没有，则尝试触发大模型实时提取画像
        """
        if not self._initialized:
            await self.initialize()
            
        try:
            # 1. 尝试获取最新的深度洞察画像
            deep_profiles = await self.get_deep_profiles(user_id=user_id, application_id=application_id, limit=1)
            if deep_profiles and len(deep_profiles) > 0:
                profile_obj = deep_profiles[0].get("profile")
                return profile_obj.model_dump() if hasattr(profile_obj, 'model_dump') else profile_obj
                
            # 2. 尝试获取最新的每日画像
            daily_profiles = await self.get_daily_profiles(user_id=user_id, application_id=application_id, limit=1)
            if daily_profiles and len(daily_profiles) > 0:
                profile_obj = daily_profiles[0].get("profile")
                return profile_obj.model_dump() if hasattr(profile_obj, 'model_dump') else profile_obj
                
            # 3. 尝试获取最新的会话画像
            session_profiles = await self.get_session_profiles(user_id=user_id, application_id=application_id, limit=1)
            if session_profiles and len(session_profiles) > 0:
                profile_obj = session_profiles[0].get("profile")
                return profile_obj.model_dump() if hasattr(profile_obj, 'model_dump') else profile_obj
                
            # 4. 本地未获取到任何画像历史，尝试实时从对话提取
            logger.info(f"未在数据库中找到用户 {user_id} 的画像记录，尝试实时提取...")
            return await self.extract_user_profile(user_id=user_id, application_id=application_id)
            
        except Exception as e:
            logger.error(f"获取用户画像失败: {e}", exc_info=True)
            return None
    async def extract_user_profile(
        self,
        user_id: str,
        application_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        提取用户画像
        从用户的对话历史中大模型实时分析并生成完整维度的用户画像
        """
        if not self._initialized:
            await self.initialize()
            
        try:
            extractor = _get_profile_extractor()
            if not extractor:
                logger.error("画像提取器不可用")
                return None
            
            # 获取用户最近的对话历史
            conversation_history = await self.get_conversation_history(
                application_id=application_id,
                user_id=user_id,
                limit=100
            )
            
            if not conversation_history:
                logger.warning(f"未找到用户对话数据无法提取画像: {user_id}")
                return None
                
            # 尝试调用提取器提取完整的用户画像
            if hasattr(extractor, 'extract_complete_profile'):
                profile = await extractor.extract_complete_profile(
                    user_id=user_id,
                    conversation_history=conversation_history
                )
            elif hasattr(extractor, 'extract_user_profile'):
                profile = await extractor.extract_user_profile(
                    user_id=user_id,
                    conversation_history=conversation_history
                )
            else:
                # 兜底：使用会话画像作为基础
                profile = await extractor.extract_session_profile(
                    conversation_history=conversation_history
                )
                
            # 如果返回的是 Pydantic 模型，转为 dict
            profile_dict = profile.model_dump() if hasattr(profile, 'model_dump') else profile
            logger.info(f"实时大模型提取用户画像成功: {user_id}")
            return profile_dict
            
        except Exception as e:
            logger.error(f"提取用户画像失败: {str(e)}", exc_info=True)
            return None
    
    async def trigger_session_profile_extraction(
        self,
        user_id: str,
        run_id: str,
        application_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        触发买家单次会话画像提取（第一步）
        """
        if not self._initialized:
            await self.initialize()
        try:
            extractor = _get_profile_extractor()
            if not extractor:
                logger.error("电商画像提取器不可用")
                return None
            
            conversation_history = await self.get_conversation_history(
                application_id=application_id,
                user_id=user_id,
                run_id=run_id,
                limit=1000
            )
            if not conversation_history:
                logger.warning(f"未找到会话数据: {application_id}:{user_id}:{run_id}")
                return None
            
            # 提取单次会话画像
            session_profile = await extractor.extract_session_profile(
                conversation_history=conversation_history
            )
            
            # 存储买家会话画像到记忆系统
            await self.store_session_profile(
                user_id=user_id,
                application_id=application_id,
                run_id=run_id,
                session_profile=session_profile
            )
            
            logger.info(f"买家会话画像提取完成: {user_id}:{run_id}")
            
            return {
                "success": True,
                "user_id": user_id,
                "application_id": application_id,
                "run_id": run_id,
                "profile": session_profile.model_dump(),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"会话画像提取失败: {str(e)}", exc_info=True)
            return {
                "success": False,
                "application_id": application_id,
                "user_id": user_id,
                "run_id": run_id,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def trigger_daily_profile_aggregation(
        self,
        application_id: str,
        user_id: str,
        date: str
    ) -> Optional[Dict[str, Any]]:
        """
        触发每日画像聚合（第二步）
        
        Args:
            user_id: 用户ID
            application_id: 应用ID
            date: 日期 (YYYY-MM-DD)
            
        Returns:
            聚合结果
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            # 获取画像提取器
            extractor = _get_profile_extractor()
            if not extractor:
                logger.error("画像提取器不可用")
                return None
            
            # 获取当日所有会话画像
            session_profiles= await self.get_session_profiles(
            user_id=user_id,
            application_id=application_id,
            day=date
            )
            
            if len(session_profiles)<1:
                logger.warning(f"未找到当日会话画像: {user_id}:{date}")
                return None
            
            # 聚合每日画像
            daily_profile = await extractor.extract_daily_profile(
                session_profiles=[p.get("profile") for p in session_profiles]
            )
            
            # 存储每日画像
            await self.store_daily_profile(
                user_id=user_id,
                application_id=application_id,
                date=date,
                daily_profile=daily_profile
            )
            
            logger.info(f"每日画像聚合完成: {user_id}:{date}")
            
            return {
                "success": True,
                "user_id": user_id,
                "application_id": application_id,
                "date": date,
                "profile": daily_profile.model_dump(),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"每日画像聚合失败: {str(e)}", exc_info=True)
            return {
                "success": False,
                "user_id": user_id,
                "application_id": application_id,
                "date": date,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def trigger_deep_insight_analysis(
        self,
        user_id: str,
        application_id: Optional[str] = None,
        days: int = 30
    ) -> Optional[Dict[str, Any]]:
        """
        触发买家生命周期深度洞察（第三步）
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            extractor = _get_profile_extractor()
            if not extractor:
                logger.error("画像提取器不可用")
                return None
            
            daily_profiles = await self.get_period_daily_profiles(user_id, application_id, days)
            
            # 电商场景下互动频次高，3天即可出初步洞察
            if len(daily_profiles) < 3:  
                logger.warning(f"数据不足进行深度分析: {user_id}, 仅有{len(daily_profiles)}天数据")
                return None
            
            analysis_period = f"{days}天"
            deep_profile = await extractor.extract_insight_profile(
                user_id=user_id,
                daily_profiles=daily_profiles,
                analysis_period=analysis_period
            )
            
            await self.store_deep_profile(
                user_id=user_id,
                application_id=application_id,
                analysis_period=analysis_period,
                deep_profile=deep_profile
            )
            
            logger.info(f"买家深度洞察完成: {user_id}")
            
            return {
                "success": True,
                "user_id": user_id,
                "profile": deep_profile.model_dump(),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"深度洞察分析失败: {str(e)}", exc_info=True)
            return {"success": False, "user_id": user_id, "error": str(e), "timestamp": datetime.now().isoformat()}
    
    
    # ============================== 画像存储和查询辅助方法 (电商重构版) ==============================
    
    async def store_session_profile(
        self,
        user_id: str,
        application_id: Optional[str] = None,
        run_id: Optional[str] = None,
        session_profile: Optional[Any] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """存储单次买家会话画像"""
        if not self._initialized:
            await self.initialize()
        base_metadata = deepcopy(metadata) if metadata else {}
        
        try:
            # 获取用户意图(售前、催发货、退款等)
            service_intents = [intent.intent_type for intent in getattr(session_profile.shopping_interaction, 'service_intents', [])]
            
            profile_metadata = {
                "agent_memory_type": MemoryType.USER_SESSION_PROFILE.value,
                "application_id": application_id,
                "start_time": session_profile.session_metrics.start_time,
                "end_time": session_profile.session_metrics.end_time,
                "day": session_profile.session_metrics.day,
                "duration_seconds": session_profile.session_metrics.duration_seconds,
                "turn_count": session_profile.session_metrics.turn_count,
                
                # 技术上下文
                "source": session_profile.technical_context.source,
                "device": session_profile.technical_context.device,
                "ip": session_profile.technical_context.ip,
                "province": session_profile.technical_context.province,
                "city": session_profile.technical_context.city,

                # 内容与情感分析
                "sentiment": session_profile.content_analysis.sentiment.value if hasattr(session_profile.content_analysis.sentiment, 'value') else session_profile.content_analysis.sentiment,
                "anxiety_score": session_profile.content_analysis.anxiety_score,
                "keywords": json.dumps(session_profile.content_analysis.keywords, ensure_ascii=False),
                "topics": json.dumps(session_profile.content_analysis.topics, ensure_ascii=False),
                "resolution_status": session_profile.content_analysis.resolution_status.value if hasattr(session_profile.content_analysis.resolution_status, 'value') else session_profile.content_analysis.resolution_status,
                
                # 电商购物交互 (订单、商品、售后意图)
                "orders": json.dumps(session_profile.shopping_interaction.queried_orders, ensure_ascii=False),
                "products": json.dumps(session_profile.shopping_interaction.inquired_products, ensure_ascii=False),
                "service_intents": json.dumps(service_intents, ensure_ascii=False),

                # 用户属性推断
                "confidence": session_profile.inferred_user_attribute.confidence,
                "customer_type": session_profile.inferred_user_attribute.customer_type.value if hasattr(session_profile.inferred_user_attribute.customer_type, 'value') else session_profile.inferred_user_attribute.customer_type,
                "role": session_profile.inferred_user_attribute.role.value if hasattr(session_profile.inferred_user_attribute.role, 'value') else session_profile.inferred_user_attribute.role,
                
                "profile": json.dumps(session_profile.model_dump(), ensure_ascii=False)
            }
            
            messages = [{"role": "system", "content": f"买家 {user_id} 会话 {run_id} 的电商购物画像"}]
            
            result = await self.profile_memory.add(
                messages=messages,
                user_id=user_id,
                run_id=run_id,
                metadata={**base_metadata, **profile_metadata},
                infer=False
            )
            memory_id = result.get('results', [{}])[0].get('id') if result.get('results') else None
            logger.info(f"电商会话画像已存储: {memory_id}")
            return memory_id
            
        except Exception as e:
            logger.error(f"存储电商会话画像失败: {e}", exc_info=True)
            raise
    
    async def get_session_profiles(
        self,
        application_id: Optional[str] = None,
        user_id: Optional[str] = None,
        run_id: Optional[str] = None,
        day: Optional[str] = None,
        sentiment: Optional[str] = None,
        anxiety_score: Optional[float] = None,
        resolution_status: Optional[str] = None,
        orders: Optional[List[str]] = None,
        products: Optional[List[str]] = None,
        service_intents: Optional[List[str]] = None,
        customer_type: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """获取买家单次会话画像记录"""
        if not self._initialized:
            await self.initialize()
        
        try:
            filter_conditions = [{"agent_memory_type": {"$eq": MemoryType.USER_SESSION_PROFILE.value}}]
            
            if user_id: filter_conditions.append({"user_id": {"$eq": user_id}})
            if application_id: filter_conditions.append({"application_id": {"$eq": application_id}})
            if run_id: filter_conditions.append({"run_id": {"$eq": run_id}})
            if day: filter_conditions.append({"day": {"$eq": day}})
            if sentiment: filter_conditions.append({"sentiment": {"$eq": sentiment}})
            if anxiety_score: filter_conditions.append({"anxiety_score": {"$gte": anxiety_score}})
            if resolution_status: filter_conditions.append({"resolution_status": {"$eq": resolution_status}})
            
            # 电商专属查询过滤
            if orders: filter_conditions.append({"orders": {"$in": orders}})
            if products: filter_conditions.append({"products": {"$in": products}})
            if service_intents: filter_conditions.append({"service_intents": {"$in": service_intents}})
            if customer_type: filter_conditions.append({"customer_type": {"$eq": customer_type}})
            
            filters = filter_conditions[0] if len(filter_conditions) == 1 else {"$and": filter_conditions}
            result = await self.profile_memory.get_all(filters=filters, limit=limit)
            
            all_memories = result.get('results', []) if isinstance(result, dict) else []
            import inspect
            if inspect.iscoroutine(all_memories):
                all_memories = await all_memories
            
            session_profiles = []
            for memory in all_memories:
                metadata = memory.get('metadata', {})
                profile_json = metadata.get('profile', '')
                if profile_json:
                    try:
                        # from .user_profile_models import SessionProfile
                        session_profiles.append({
                            "memory_id": memory.get('id'),
                            "user_id": memory.get('user_id'),
                            "application_id": metadata.get('application_id', ''),
                            "run_id": memory.get('run_id', ''),
                            "profile": SessionProfile(**json.loads(profile_json))
                        })
                    except Exception as e:
                        logger.warning(f"解析SessionProfile失败: {e}")
            
            return session_profiles
        except Exception as e:
            logger.error(f"获取会话画像历史失败: {e}", exc_info=True)
            return []
    
    async def store_daily_profile(
        self,
        user_id: str,
        application_id: str,
        date: str,
        daily_profile: Any,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """存储买家每日统计画像"""
        if not self._initialized:
            await self.initialize()
        base_metadata = deepcopy(metadata) if metadata else {}
        
        try:
            profile_metadata = {
                "agent_memory_type": MemoryType.USER_DAILY_PROFILE.value,
                "application_id": application_id,
                "date": date,
                
                "total_sessions": daily_profile.interaction_metrics.total_sessions,
                "total_turns": daily_profile.interaction_metrics.total_turns,
                
                "avg_sentiment_score": daily_profile.behavior_pattern.avg_sentiment_score,
                "avg_anxiety_score": daily_profile.behavior_pattern.avg_anxiety_score,
                "resolution_rate": daily_profile.behavior_pattern.resolution_rate,
                "human_transfer_rate": daily_profile.behavior_pattern.human_transfer_rate,
                "topic_trends": json.dumps(daily_profile.behavior_pattern.topic_trends, ensure_ascii=False),
                
                # 电商每日业务统计
                "orders_queried": daily_profile.business_usage.orders_queried,
                "products_inquired": daily_profile.business_usage.products_inquired,
                "after_sales_requested": daily_profile.business_usage.after_sales_requested,
                
                "profile": json.dumps(daily_profile.model_dump(), ensure_ascii=False)
            }
            
            messages = [{"role": "system", "content": f"买家 {user_id} 在 {date} 的每日电商行为画像"}]
            
            result = await self.profile_memory.add(
                messages=messages,
                user_id=user_id,
                metadata={**base_metadata, **profile_metadata},
                infer=False
            )
            memory_id = result.get('results', [{}])[0].get('id') if result.get('results') else None
            return memory_id
            
        except Exception as e:
            logger.error(f"存储每日画像失败: {e}", exc_info=True)
            raise
    async def get_daily_profiles(
        self,
        user_id: Optional[str] = None,
        application_id: Optional[str] = None,
        date: Optional[str] = None,
        human_transfer_rate: Optional[float] = None,
        orders_queried: Optional[int] = None,
        after_sales_requested: Optional[int] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """获取买家每日画像历史"""
        if not self._initialized:
            await self.initialize()
        
        try:
            filter_conditions = [{"agent_memory_type": {"$eq": MemoryType.USER_DAILY_PROFILE.value}}]
            
            if user_id: filter_conditions.append({"user_id": {"$eq": user_id}})
            if application_id: filter_conditions.append({"application_id": {"$eq": application_id}})
            if date: filter_conditions.append({"date": {"$eq": date}})
            if human_transfer_rate: filter_conditions.append({"human_transfer_rate": {"$gte": human_transfer_rate}})
            if orders_queried: filter_conditions.append({"orders_queried": {"$gte": orders_queried}})
            if after_sales_requested: filter_conditions.append({"after_sales_requested": {"$gte": after_sales_requested}})
            
            filters = filter_conditions[0] if len(filter_conditions) == 1 else {"$and": filter_conditions}
            result = await self.profile_memory.get_all(filters=filters, limit=limit)
            
            all_memories = result.get('results', []) if isinstance(result, dict) else []
            import inspect
            if inspect.iscoroutine(all_memories):
                all_memories = await all_memories
                
            profiles = []
            for memory in all_memories:
                metadata = memory.get('metadata', {})
                if metadata.get('profile'):
                    profiles.append({
                        "memory_id": memory.get('id'),
                        "user_id": memory.get('user_id'),
                        "application_id": metadata.get('application_id', ''),
                        "date": metadata.get('date', ''),
                        "profile": DailyProfile(**json.loads(metadata.get('profile')))
                    })
            return profiles
        except Exception as e:
            logger.error(f"获取每日画像失败: {e}", exc_info=True)
            return []
    async def get_deep_profiles(
        self,
        user_id: Optional[str] = None,
        application_id: Optional[str] = None,
        analysis_period: Optional[str] = None,
        primary_customer_type: Optional[str] = None,
        spending_power: Optional[str] = None,
        customer_value_score: Optional[float] = None,
        churn_risk: Optional[float] = None,
        upsell_potential: Optional[float] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """获取深度电商画像历史"""
        if not self._initialized:
            await self.initialize()
        
        try:
            filter_conditions = [{"agent_memory_type": {"$eq": MemoryType.USER_DEEP_PROFILE.value}}]
            
            if user_id: filter_conditions.append({"user_id": {"$eq": user_id}})
            if application_id: filter_conditions.append({"application_id": {"$eq": application_id}})
            if analysis_period: filter_conditions.append({"analysis_period": {"$eq": analysis_period}})
            if primary_customer_type: filter_conditions.append({"primary_customer_type": {"$eq": primary_customer_type}})
            if spending_power: filter_conditions.append({"spending_power": {"$eq": spending_power}})
            if customer_value_score: filter_conditions.append({"customer_value_score": {"$gte": customer_value_score}})
            if churn_risk: filter_conditions.append({"churn_risk": {"$gte": churn_risk}})
            if upsell_potential: filter_conditions.append({"upsell_potential": {"$gte": upsell_potential}})
            
            filters = filter_conditions[0] if len(filter_conditions) == 1 else {"$and": filter_conditions}
            result = await self.profile_memory.get_all(filters=filters, limit=limit)
            
            all_memories = result.get('results', []) if isinstance(result, dict) else []
            import inspect
            if inspect.iscoroutine(all_memories):
                all_memories = await all_memories
                
            profiles = []
            for memory in all_memories:
                metadata = memory.get('metadata', {})
                if metadata.get('profile'):
                    profiles.append({
                        "memory_id": memory.get('id'),
                        "user_id": memory.get('user_id'),
                        "application_id": metadata.get('application_id', ''),
                        "analysis_period": metadata.get('analysis_period', ''),
                        "profile": InsightProfile(**json.loads(metadata.get('profile')))
                    })
            return profiles
            
        except Exception as e:
            logger.error(f"获取深度画像失败: {e}", exc_info=True)
            return []
    
    async def store_deep_profile(
        self,
        user_id: str,
        application_id: str,
        analysis_period: str,
        deep_profile: Any,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """存储电商买家深度生命周期画像"""
        if not self._initialized:
            await self.initialize()
        base_metadata = deepcopy(metadata) if metadata else {}
        
        try:
            profile_metadata = {
                "agent_memory_type": MemoryType.USER_DEEP_PROFILE.value,
                "application_id": application_id,
                "analysis_period": analysis_period,
                
                # 电商核心标签
                "primary_customer_type": deep_profile.primary_customer_type.value if hasattr(deep_profile.primary_customer_type, 'value') else deep_profile.primary_customer_type,
                "spending_power": deep_profile.spending_power.value if hasattr(deep_profile.spending_power, 'value') else deep_profile.spending_power,
                
                # 购物与服务偏好
                "preferred_categories": json.dumps(deep_profile.shopping_pattern.preferred_categories, ensure_ascii=False),
                "purchase_frequency": deep_profile.shopping_pattern.purchase_frequency,
                "price_sensitivity": deep_profile.shopping_pattern.price_sensitivity,
                "prefers_self_service": deep_profile.service_preference.prefers_self_service,
                
                # 电商商业价值
                "customer_value_score": deep_profile.customer_value_score,
                "churn_risk": deep_profile.churn_risk,
                "upsell_potential": deep_profile.upsell_potential,
                "recommended_categories": json.dumps(deep_profile.recommended_categories, ensure_ascii=False),
                "communication_strategy": deep_profile.communication_strategy,
                
                "profile": json.dumps(deep_profile.model_dump(), ensure_ascii=False)
            }
            
            messages = [{"role": "system", "content": f"买家 {user_id} 的电商深度洞察画像，分析周期: {analysis_period}"}]
            
            result = await self.profile_memory.add(
                messages=messages,
                user_id=user_id,
                metadata={**base_metadata, **profile_metadata},
                infer=False
            )
            memory_id = result.get('results', [{}])[0].get('id') if result.get('results') else None
            logger.info(f"电商深度画像已存储: {memory_id}")
            return memory_id
            
        except Exception as e:
            logger.error(f"存储深度画像失败: {e}", exc_info=True)
            raise
        
    async def get_period_daily_profiles(self, user_id: str, application_id: str, days: int) -> List[Any]:
        """获取买家指定时期的每日画像"""
        try:
            daily_profiles = []
            from datetime import timezone
            end_date = datetime.now(timezone.utc)
            for i in range(days):
                date = end_date - timedelta(days=i)
                daily_profile = await self.get_daily_profiles(
                    user_id=user_id,
                    application_id=application_id,
                    date=date.strftime("%Y-%m-%d")
                )
                if daily_profile:
                    daily_profiles.append(daily_profile[0].get("profile"))

            logger.info(f"获取到买家 {user_id} 最近 {days} 天的 {len(daily_profiles)} 个每日画像")
            return daily_profiles
        except Exception as e:
            logger.error(f"获取时期每日画像失败: {e}", exc_info=True)
            return []
    
    def _reconstruct_profile_object(self, profile_data: Dict[str, Any], profile_type: str):
        """根据电商画像类型重构对象"""
        try:
            if profile_type == "session": return SessionProfile(**profile_data)
            elif profile_type == "daily": return DailyProfile(**profile_data)
            elif profile_type in ["deep", "deep_insight"]: return InsightProfile(**profile_data)
            return None
        except Exception as e:
            logger.warning(f"重构{profile_type}画像失败: {e}")
            return None
    
    def reconstruct_session_profiles_from_records(self, records: List[Dict[str, Any]]) -> List['SessionProfile']:
        """
        从查询记录中重构电商买家单次会话画像 (SessionProfile) 对象列表
        
        Args:
            records: 记忆系统查询结果记录列表
            
        Returns:
            SessionProfile对象列表
        """
        session_profiles = []
        for record in records:
            profile_data = record.get('profile_data', {})
            if profile_data:
                session_profile = self._reconstruct_profile_object(profile_data, "session")
                if session_profile:
                    session_profiles.append(session_profile)
        
        logger.info(f"成功重构了 {len(session_profiles)} 个买家会话画像(SessionProfile)对象")
        return session_profiles
    
    def reconstruct_daily_profiles_from_records(self, records: List[Dict[str, Any]]) -> List['DailyProfile']:
        """
        从查询记录中重构电商买家每日统计画像 (DailyProfile) 对象列表
        
        Args:
            records: 记忆系统查询结果记录列表
            
        Returns:
            DailyProfile对象列表
        """
        daily_profiles = []
        for record in records:
            profile_data = record.get('profile_data', {})
            if profile_data:
                daily_profile = self._reconstruct_profile_object(profile_data, "daily")
                if daily_profile:
                    daily_profiles.append(daily_profile)
        
        logger.info(f"成功重构了 {len(daily_profiles)} 个买家每日画像(DailyProfile)对象")
        return daily_profiles
    
    def reconstruct_insight_profiles_from_records(self, records: List[Dict[str, Any]]) -> List['InsightProfile']:
        """
        从查询记录中重构电商买家深度生命周期洞察画像 (InsightProfile) 对象列表
        
        Args:
            records: 记忆系统查询结果记录列表
            
        Returns:
            InsightProfile对象列表
        """
        insight_profiles = []
        for record in records:
            profile_data = record.get('profile_data', {})
            if profile_data:
                insight_profile = self._reconstruct_profile_object(profile_data, "deep_insight")
                if insight_profile:
                    insight_profiles.append(insight_profile)
        
        logger.info(f"成功重构了 {len(insight_profiles)} 个买家深度画像(InsightProfile)对象")
        return insight_profiles
    
# 全局记忆管理器实例
memory_manager = MemoryManager()

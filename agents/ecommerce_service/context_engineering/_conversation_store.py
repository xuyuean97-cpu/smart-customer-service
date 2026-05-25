# Auto-generated mixin — extracted from memory_manager.py
from common.logging import get_logger
from copy import deepcopy
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any

from ._memory_core import MemoryType
from .chroma_health import get_chroma_health

logger = get_logger("memory._conversation_store")

class ConversationStoreMixin:
    async def store_conversation(
        self,
        application_id: str,
        user_id: str,
        run_id: str,
        agent_id: str,
        messages,
        response: str,
        metadata: Optional[Dict[str, Any]] = None,
        tenant_id: str = "default",
    ) -> str:
        if not self._initialized:
            await self.initialize()

        # ChromaDB 健康守护：熔断时跳过存储，不阻塞对话流程
        health = get_chroma_health()
        async with health.guard("store_conversation") as ok:
            if not ok:
                logger.warning(f"ChromaDB 不可用，对话记忆未持久化 (user={user_id})")
                return ""

        base_metadata = deepcopy(metadata) if metadata else {}
        try:
            metadata = {
                "agent_memory_type": MemoryType.CONVERSATION.value,
                "response": response,
                "application_id": application_id,
                "tenant_id": tenant_id,
                "expert_verified": False,
                "expert_id": "",
                "expert_corrected_response": "",
                "quality_score": 0.0,
                "user_approved": 0,
                # Bug 4: 补充画像系统需要的技术上下文字段
                "query_source": base_metadata.get("source", ""),
                "query_device": base_metadata.get("device", ""),
                "query_ip": base_metadata.get("ip", ""),
                "network_type": base_metadata.get("network_type", ""),
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
        tenant_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        if not self._initialized:
            await self.initialize()

        try:
            filter_conditions = []
            filter_conditions.append({"agent_memory_type": {"$eq": MemoryType.CONVERSATION.value}})

            if tenant_id:
                filter_conditions.append({"tenant_id": {"$eq": tenant_id}})
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
                        # 确保 timezone-aware 再比较（memory_time 可能是 naive 的）
                        if memory_time.tzinfo is None:
                            memory_time = memory_time.replace(tzinfo=timezone.utc)

                        if start_date:
                            if start_date.tzinfo is None:
                                start_date = start_date.replace(tzinfo=timezone.utc)
                            if memory_time < start_date:
                                continue

                        if end_date:
                            if end_date.tzinfo is None:
                                end_date = end_date.replace(tzinfo=timezone.utc)
                            if memory_time > end_date:
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
            his_conversation = await self.get_conversation_history(response=response)
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

    async def search_conversations(
        self,
        query: str,
        application_id: Optional[str] = None,
        user_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        expert_verified: Optional[bool] = None,
        user_approved: Optional[bool] = None,
        min_quality_score: Optional[float] = None,
        limit: int = 50,
        tenant_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        if not self._initialized:
            await self.initialize()

        try:
            filter_conditions = []
            filter_conditions.append({"agent_memory_type": {"$eq": MemoryType.CONVERSATION.value}})

            if tenant_id:
                filter_conditions.append({"tenant_id": {"$eq": tenant_id}})
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
        limit: int = 10,
        tenant_id: Optional[str] = None,
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

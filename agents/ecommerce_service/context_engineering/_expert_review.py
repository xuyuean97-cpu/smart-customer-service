# Auto-generated mixin — extracted from memory_manager.py
from common.logging import get_logger
from copy import deepcopy
from datetime import datetime
from typing import Dict, List, Optional, Any

from ._memory_core import MemoryType

logger = get_logger("memory._expert_review")

class ExpertReviewMixin:

    # 审核通过 + 评分 ≥ 阈值时自动录入知识库
    AUTO_KB_THRESHOLD = 0.8

    async def expert_review_conversation(
        self,
        memory_id: str,
        query: str,
        expert_approved: Optional[bool] = True,
        expert_id: Optional[str] = None,
        quality_score: Optional[float] = None,
        corrected_response: Optional[str] = None,
        response: Optional[str] = None,
        review_notes: Optional[str] = None,
    ) -> bool:
        """
        Args:
            memory_id: 记忆ID
            query: 用户原始问题
            expert_approved: 是否通过
            quality_score: 质量评分 (0-1)
            corrected_response: 专家修正回复
            response: AI 原始回复（用于知识库录入）
            review_notes: 审核备注
        """
        if not self._initialized:
            await self.initialize()

        try:
            updated_metadata = {"expert_verified": expert_approved}
            if quality_score is not None:
                updated_metadata["quality_score"] = quality_score
            if expert_id:
                updated_metadata["expert_id"] = expert_id
            if corrected_response:
                updated_metadata["expert_corrected_response"] = corrected_response
            if review_notes:
                updated_metadata["review_notes"] = review_notes

            await self.conversation_memory.update(
                memory_id=memory_id,
                data=query,
                metadata=updated_metadata
            )

            # ── 自动录入知识库 ──
            if expert_approved and quality_score is not None and quality_score >= self.AUTO_KB_THRESHOLD:
                final_answer = corrected_response or response or ""
                if final_answer:
                    try:
                        await self.add_expert_qa(
                            question=query,
                            answer=final_answer,
                            expert_id=expert_id,
                            metadata={
                                "source": "expert_review",
                                "quality_score": quality_score,
                                "source_memory_id": memory_id,
                            }
                        )
                        logger.info(f"自动录入知识库: memory_id={memory_id}, score={quality_score}")
                    except Exception as kb_err:
                        logger.warning(f"自动录入知识库失败（不影响审核）: {kb_err}")

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


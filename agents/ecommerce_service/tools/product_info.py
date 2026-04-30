import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))
import asyncio
from text2kb.retrieval import retrieve_from_kb
from langchain_core.messages import AnyMessage
from typing import List
from config.utils import config_manager
from agents.ecommerce_service.core import comprehensive_query_transform,rerank_results
from agents.ecommerce_service.context_engineering.agent_memory import get_relevant_expert_qa_memories
from agents.ecommerce_service.state import RetrievalResult
from common.logging import get_logger
logger = get_logger("agents.tools.product_info")

_text2kb_config = config_manager.get_text2kb_config()
KB_ADDRESS = _text2kb_config.get("kb_address")
KB_API_KEY = _text2kb_config.get("kb_api_key")
KB_DATASET_NAME = _text2kb_config.get("kb_dataset_name")
KB_VECTOR_SIMILARITY_WEIGHT = float(_text2kb_config.get("kb_vector_similarity_weight"))
KB_TOP_K = int(_text2kb_config.get("kb_topK"))
KB_KEY_WORDS = bool(_text2kb_config.get("kb_key_words"))
RERANKER_MODEL = _text2kb_config.get("reranker_model")
RERANKER_BASE_URL = _text2kb_config.get("reranker_base_url")
RERANKER_API_KEY = _text2kb_config.get("reranker_api_key")


async def product_policy_query2docs_main(user_question: str, messages: List[AnyMessage]) -> RetrievalResult:
    """
    电商统一知识检索入口（支持专家QA + 知识库 RAG）
    """
    user_query = user_question
    query_list = [user_question]

    try:
        # 第一步：并行完成意图重写
        rewritten_query_task = comprehensive_query_transform(user_query, 'rewrite', messages)
        step_back_query_task = comprehensive_query_transform(user_query, 'step_back', messages)

        rewritten_query, step_back_query = await asyncio.gather(
            rewritten_query_task,
            step_back_query_task,
            return_exceptions=True
        )

        if rewritten_query and not isinstance(rewritten_query, Exception):
            query_list.append(str(rewritten_query))
        if step_back_query and not isinstance(step_back_query, Exception):
            query_list.append(str(step_back_query))

        logger.info(f"电商检索重写后的问题序列: {query_list}")

        # 第二步：准备并行任务
        expert_qa_task = get_relevant_expert_qa_memories(
            query=user_query,
            score_limit=0.2,
            limit=1
        )

        retrieval_tasks = [
            retrieve_from_kb(question=query,
                            dataset_name=KB_DATASET_NAME,
                            address=KB_ADDRESS,
                            api_key=KB_API_KEY,
                            similarity_threshold=0.01,
                            vector_similarity_weight=KB_VECTOR_SIMILARITY_WEIGHT,
                            top_k=KB_TOP_K*5,
                            key_words=KB_KEY_WORDS)
            for query in query_list
        ]

        # 第三步：执行所有并发检索
        expert_qa_memories, all_results_list = await asyncio.gather(
            expert_qa_task,
            asyncio.gather(*retrieval_tasks, return_exceptions=True),
            return_exceptions=True
        )

        # --- 以下是补全的逻辑 ---

        # 1. 优先处理专家QA结果
        if expert_qa_memories and not isinstance(expert_qa_memories, Exception) and len(expert_qa_memories) > 0:
            expert_qa = expert_qa_memories[0]
            logger.info(f"匹配到电商标准问答(Expert QA)，得分: {expert_qa.get('score')}")
            return RetrievalResult(
                source="expert_qa",
                content=expert_qa["answer"],
                score=expert_qa.get("score", 1.0),
                images=expert_qa.get("images"),
                query_list=query_list
            )

        # 2. 合并知识库检索结果并去重
        all_results = []
        if not isinstance(all_results_list, Exception):
            for res_list in all_results_list:
                if isinstance(res_list, list):
                    all_results.extend(res_list)

        seen_contents = set()
        unique_results = []
        for res in all_results:
            if res.get('content') and res['content'] not in seen_contents:
                seen_contents.add(res['content'])
                unique_results.append(res)

        # 3. 重排 (Rerank)
        if len(unique_results) > 0:
            max_score = 0.0
            if RERANKER_MODEL and RERANKER_BASE_URL:
                # 使用重排模型筛选最相关的 Top K
                unique_results, max_score = await rerank_results(
                    unique_results, user_question, RERANKER_MODEL,
                    RERANKER_BASE_URL, RERANKER_API_KEY, KB_TOP_K
                )

            context_text = "\n\n".join([doc['content'] for doc in unique_results])
            logger.info(f"电商知识库检索成功，最高得分: {max_score}")
            return RetrievalResult(
                source="knowledge_base",
                content=context_text,
                score=max_score,
                query_list=query_list
            )

        # 4. 无结果兜底
        logger.warning(f"所有路径均未检索到相关内容: {user_question}")
        return RetrievalResult(
            source="none",
            content="抱歉，小二查遍了知识库也没找到相关信息。",
            score=0.0,
            query_list=query_list
        )

    except Exception as e:
        logger.error(f"检索工具 product_policy_query2docs_main 发生未捕获异常: {e}")
        # 即使报错也要返回对象，防止图崩溃
        return RetrievalResult(
            source="none",
            content=f"检索服务暂时不可用: {str(e)}",
            score=0.0,
            query_list=query_list
        )

async def product_info_query2docs(user_question: str, messages: List[AnyMessage]) -> RetrievalResult:
    """
    简化版商品/政策检索（仅知识库，不包含专家QA）
    对应原 airport_knowledge_query2docs，用于次级查询
    """
    logger.info("执行简化版商品知识检索")
    user_query = user_question

    # 并行重写
    rewritten_query_task = comprehensive_query_transform(user_query, 'rewrite', messages)
    step_back_query_task = comprehensive_query_transform(user_query, 'step_back', messages)

    rewritten_query, step_back_query = await asyncio.gather(
        rewritten_query_task,
        step_back_query_task,
        return_exceptions=True
    )

    query_list = [user_question]
    if rewritten_query and not isinstance(rewritten_query, Exception):
        query_list.append(rewritten_query)
    if step_back_query and not isinstance(step_back_query, Exception):
        query_list.append(step_back_query)

    # 检索
    retrieval_tasks = [
        retrieve_from_kb(question=query,
                        dataset_name=KB_DATASET_NAME,
                        address=KB_ADDRESS,
                        api_key=KB_API_KEY,
                        similarity_threshold=0.01,
                        vector_similarity_weight=KB_VECTOR_SIMILARITY_WEIGHT,
                        top_k=KB_TOP_K,
                        key_words=KB_KEY_WORDS)
        for query in query_list
    ]
    all_results_list = await asyncio.gather(*retrieval_tasks, return_exceptions=True)

    # 结果合并与去重
    all_results = []
    for result_list in all_results_list:
        if not isinstance(result_list, Exception):
            all_results.extend(result_list)

    seen_contents = set()
    unique_results = []
    for result in all_results:
        if result['content'] not in seen_contents:
            seen_contents.add(result['content'])
            unique_results.append(result)

    results = unique_results

    # 重排
    if len(results) > 0 and RERANKER_MODEL and RERANKER_BASE_URL:
        results, max_score = await rerank_results(results, query_list[0], RERANKER_MODEL, RERANKER_BASE_URL, RERANKER_API_KEY, KB_TOP_K)
        text = "\n\n".join(f"{doc['content']}" for doc in results)
        return RetrievalResult(
            source="knowledge_base",
            content=text,
            score=max_score,
            images=None,
            query_list=query_list,
        )
    elif len(results) > 0:
        text = "\n\n".join(f"{doc['content']}" for doc in results)
        return RetrievalResult(
            source="knowledge_base",
            content=text,
            score=0.0,
            images=None,
            query_list=query_list,
        )

    return RetrievalResult(
        source="none",
        content="暂无相关商品信息。",
        score=0.0,
        images=None,
        query_list=query_list,
    )

"""
商品与电商政策咨询节点
"""
from datetime import datetime
from copy import deepcopy

# 确保路径正确
# 导入电商版状态与工具
from ..state import EcommerceMainServiceState, RetrievalResult
from langchain_core.runnables import RunnableConfig
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import AIMessage
from langgraph.config import get_stream_writer

# 这里的工具名建议在 tools.py 中也同步修改，此处先对应调用
from agents.ecommerce_service.tools import product_policy_query2docs_main
from agents.ecommerce_service.core import filter_messages_for_agent, max_msg_len, content_model
from agents.ecommerce_service.context_engineering.prompts import main_graph_prompts
from agents.ecommerce_service.context_engineering.agent_memory import memory_enabled_agent
from common.logging import get_logger

logger = get_logger("agents.main-nodes.product_info")

@memory_enabled_agent(application_id="电商主智能客服")
async def product_info_agent(state: EcommerceMainServiceState, config: RunnableConfig):
    """
    商品政策问答处理节点 (对应原 airport_knowledge_agent)
    使用统一的检索结果进行导购或政策解答生成
    """
    logger.info("进入商品政策问答子智能体")

    # 获取检索结果及查询语句
    retrieval_result = state.get("retrieval_result")
    user_query = retrieval_result.query_list[1] if retrieval_result and len(retrieval_result.query_list) > 1 else (state.get("user_query") or config["configurable"].get("user_query", ""))

    pre_retrieval_result = state.get("pre_retrieval_result")

    # 暂存当前检索结果供下一轮作为 pre_context
    tmp_pre_retrieval_result = None
    if retrieval_result:
        tmp_pre_retrieval_result = RetrievalResult(
            source=deepcopy(retrieval_result.source),
            content=deepcopy(retrieval_result.content),
            score=deepcopy(retrieval_result.score),
            images=deepcopy(retrieval_result.images),
            sql=deepcopy(retrieval_result.sql),
            query_list=deepcopy(retrieval_result.query_list),
        )

    # 1. 如果是专家/标准QA (Expert QA)，直接返回结果
    if retrieval_result and retrieval_result.source == "expert_qa":
        logger.info("使用电商专家QA直接回答")
        return {"retrieval_result": None, "pre_retrieval_result": tmp_pre_retrieval_result}

    # 2. 准备语言环境
    translator_result = state.get("translator_result")
    language = translator_result.language if translator_result else "中文"

    # 3. 构建提示模板 (引用已改造的电商 PROMPT)
    kb_prompt = ChatPromptTemplate.from_messages([
        ("system", main_graph_prompts.ECOMMERCE_KNOWLEDGE_SYSTEM_PROMPT),
        ("human", main_graph_prompts.ECOMMERCE_KNOWLEDGE_HUMAN_PROMPT)
    ]).partial(time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    # 4. 过滤历史消息
    new_messages = filter_messages_for_agent(state, max_msg_len, "商品政策问答子智能体")
    messages = new_messages if len(new_messages) > 0 else [AIMessage(content="暂无对话历史")]

    # 5. 流式生成 — 逐 token 推送给前端，首 token 在 500ms 内到达
    writer = get_stream_writer()
    kb_chain = kb_prompt | content_model
    full_text = ""
    async for chunk in kb_chain.astream({
        "user_query": user_query,
        "pre_context": pre_retrieval_result.content if pre_retrieval_result else "",
        "context": retrieval_result.content if retrieval_result else "未找到相关商品信息。",
        "messages": messages,
        "language": language
    }):
        # LangChain streaming: chunk can be AIMessageChunk with .content
        token = chunk.content if hasattr(chunk, 'content') else str(chunk) if isinstance(chunk, str) else ""
        if token:
            full_text += token
            writer({"node_name": "product_info_agent_node", "data": {"type": "stream", "text": token}})

    res = AIMessage(content=full_text, name="商品政策问答子智能体")
    return {
        "messages": [res],
        "retrieval_result": None,
        "pre_retrieval_result": tmp_pre_retrieval_result
    }

@memory_enabled_agent(application_id="电商主智能客服")
async def product_info_search(state: EcommerceMainServiceState, config: RunnableConfig):
    """
    商品政策检索节点 (对应原 airport_knowledge_search)
    执行统一的商品知识检索（包含活动规则、售后政策等）
    """
    logger.info("进入商品政策检索节点")

    user_query = state.get("user_query", "") or config["configurable"].get("user_query", "")
    messages = filter_messages_for_agent(state, max_msg_len, "商品政策问答子智能体")

    # 执行统一检索工具 (内部需连接电商知识库)
    retrieval_result = await product_policy_query2docs_main(user_query, messages)
    logger.info(f"商品知识检索完成，分数: {retrieval_result.score}")

    writer = get_stream_writer()

    # 如果检索到高匹配度的专家QA，则记录并流式反馈
    if retrieval_result.source == "expert_qa":
        logger.info("匹配到标准商品问答(Expert QA)")
        writer({
            "node_name": "product_info_search_node",
            "data": {
                "type": "expert_qa",
                "answer": retrieval_result.content,
                "images": retrieval_result.images,
                "score": retrieval_result.score
            }
        })
        return {
            "messages": [AIMessage(content=retrieval_result.content, name="商品政策问答子智能体")],
            "retrieval_result": retrieval_result
        }

    return {"retrieval_result": retrieval_result}



# """
# 机场知识节点
# """
# import sys
# import os
# sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../")))
# from ..state import AirportMainServiceState
# from langchain_core.runnables import RunnableConfig
# from langchain_core.prompts import ChatPromptTemplate
# from langgraph.types import Command
# from copy import deepcopy
# from langchain_core.messages import AIMessage
# from agents.ecommerce_service.tools import airport_knowledge_query2docs_main
# from agents.ecommerce_service.core import filter_messages_for_agent, max_msg_len, KB_SIMILARITY_THRESHOLD,content_model
# from agents.ecommerce_service.context_engineering.prompts import main_graph_prompts
# from agents.ecommerce_service.context_engineering.agent_memory import memory_enabled_agent
# from datetime import datetime
# from langgraph.config import get_stream_writer
# from agents.ecommerce_service.state import RetrievalResult
# from common.logging import get_logger

# logger = get_logger("agents.main-nodes.airport")

# @memory_enabled_agent(application_id="机场主智能客服")
# async def airport_knowledge_agent(state: AirportMainServiceState, config: RunnableConfig):
#     """
#     机场知识问答处理节点
#     使用统一的检索结果进行问答生成
#     """
#     logger.info("进入机场知识问答子智能体")

#     # user_query = state.get("user_query", "") if state.get("user_query", "") else config["configurable"].get("user_query", "")
#     user_query = state.get("retrieval_result").query_list[1] if state.get("retrieval_result", "") else config["configurable"].get("user_query", "")
    
#     # 获取统一的检索结果
#     retrieval_result = state.get("retrieval_result")
#     pre_retrieval_result = state.get("pre_retrieval_result")
#     tmp_pre_retrieval_result = RetrievalResult(
#         source=deepcopy(retrieval_result.source),
#         content=deepcopy(retrieval_result.content),
#         score=deepcopy(retrieval_result.score),
#         images=deepcopy(retrieval_result.images),
#         sql=deepcopy(retrieval_result.sql),
#         query_list=deepcopy(retrieval_result.query_list),
#     )
#     # 如果是专家QA，直接返回结果
#     if retrieval_result and retrieval_result.source == "expert_qa":
#         logger.info("使用专家QA直接回答")
#         return {"retrieval_result": None, "pre_retrieval_result": tmp_pre_retrieval_result}  # 清空检索结果
    
#     # 准备上下文信息
#     translator_result = state.get("translator_result")
#     language = translator_result.language if translator_result else "中文"
    
#     # # 检查检索结果是否有效
#     # if not retrieval_result or retrieval_result.source == "none":
#     #     logger.info("无有效检索结果，转向闲聊节点")
#     #     return Command(
#     #         goto="chitchat_node",
#     #         update={"retrieval_result": None}
#     #     )
    
#     # # 检查知识库检索分数是否达标
#     # if retrieval_result.source == "knowledge_base" and retrieval_result.score < KB_SIMILARITY_THRESHOLD:
#     #     logger.info(f"检索分数 {retrieval_result.score} 低于阈值 {KB_SIMILARITY_THRESHOLD}，转向闲聊节点")
#     #     return Command(
#     #         goto="chitchat_node",
#     #         update={"retrieval_result": None}
#     #     )
    
#     logger.info(f"使用知识库检索结果，分数: {retrieval_result.score}")
    
#     # 构建提示模板
#     kb_prompt = ChatPromptTemplate.from_messages([
#         ("system", main_graph_prompts.ECOMMERCE_KNOWLEDGE_SYSTEM_PROMPT ),
#         ("human", main_graph_prompts.ECOMMERCE_KNOWLEDGE_HUMAN_PROMPT)
#     ]).partial(time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

#     new_messages = filter_messages_for_agent(state, max_msg_len, "机场知识问答子智能体")
#     logger.info(f"机场知识问答子智能体消息数量: {len(new_messages)}")

#     messages = new_messages if len(new_messages) > 0 else [AIMessage(content="暂无对话历史")]
#     logger.info(f"机场知识问答子智能体上一轮检索结果: {pre_retrieval_result.content if pre_retrieval_result else '无'}")
#     kb_chain = kb_prompt | content_model
#     res = await kb_chain.ainvoke({
#         "user_query": user_query,
#         "pre_context": pre_retrieval_result.content if pre_retrieval_result else "",
#         "context": retrieval_result.content,
#         "messages": messages,
#         "language": language
#     })
#     res.name = "机场知识问答子智能体"
    
#     return {
#         "messages": [res],
#         "retrieval_result": None,
#         "pre_retrieval_result": tmp_pre_retrieval_result  # 清空检索结果
#     }

# @memory_enabled_agent(application_id="机场主智能客服")
# async def airport_knowledge_search(state: AirportMainServiceState, config: RunnableConfig):
#     """
#     机场知识检索节点
#     执行统一的知识检索（包含专家QA和知识库）
#     """
#     logger.info("进入机场知识检索节点")
    
#     user_query = state.get("user_query", "") if state.get("user_query", "") else config["configurable"].get("user_query", "")
#     messages = filter_messages_for_agent(state, max_msg_len, "机场知识问答子智能体")
    
#     # 执行统一检索
#     retrieval_result = await airport_knowledge_query2docs_main(user_query, messages)
#     logger.info(f"机场知识检索结果{retrieval_result.score}: {retrieval_result.content}")
    
#     writer = get_stream_writer()
    
#     # 如果是专家QA结果，直接返回答案
#     if retrieval_result.source == "expert_qa":
#         logger.info("检索到专家QA结果，直接返回")
#         writer({
#             "node_name": "airport_info_search_node",
#             "data": {
#                 "type": "expert_qa",
#                 "answer": retrieval_result.content,
#                 "images": retrieval_result.images,
#                 "score": retrieval_result.score
#             }
#         })
#         return {
#             "messages": [AIMessage(content=retrieval_result.content, name="机场知识问答子智能体")],
#             "retrieval_result": retrieval_result
#         }
    
#     # 返回知识库检索结果或无结果
#     logger.info(f"检索完成，来源: {retrieval_result.source}, 分数: {retrieval_result.score}")
#     return {"retrieval_result": retrieval_result}

"""
商品与电商政策咨询节点 (原机场知识节点)
"""
import sys
import os
from datetime import datetime
from copy import deepcopy
from typing import List

# 确保路径正确
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../")))

# 导入电商版状态与工具
from ..state import EcommerceMainServiceState, RetrievalResult
from langchain_core.runnables import RunnableConfig
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import AIMessage
from langgraph.types import Command
from langgraph.config import get_stream_writer

# 这里的工具名建议在 tools.py 中也同步修改，此处先对应调用
from agents.ecommerce_service.tools import product_policy_query2docs_main 
from agents.ecommerce_service.core import filter_messages_for_agent, max_msg_len, KB_SIMILARITY_THRESHOLD, content_model
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

    # 5. 调用模型生成答案
    kb_chain = kb_prompt | content_model
    res = await kb_chain.ainvoke({
        "user_query": user_query,
        "pre_context": pre_retrieval_result.content if pre_retrieval_result else "",
        "context": retrieval_result.content if retrieval_result else "未找到相关商品信息。",
        "messages": messages,
        "language": language
    })
    res.name = "商品政策问答子智能体"
    
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



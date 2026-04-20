"""
闲聊节点
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../")))
from agents.ecommerce_service.state import AirportMainServiceState
from langchain_core.runnables import RunnableConfig
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.prebuilt import ToolNode
from langgraph.types import Command
from datetime import datetime
from agents.ecommerce_service.core import filter_messages_for_agent, max_msg_len,base_model
from agents.ecommerce_service.context_engineering.prompts import main_graph_prompts
from agents.ecommerce_service.context_engineering.agent_memory import memory_enabled_agent
from common.logging import get_logger

logger = get_logger("agents.main-nodes.chitchat")
"""
电商闲聊与基础问候处理节点
"""
import sys
import os
from datetime import datetime
from langchain_core.runnables import RunnableConfig
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import AIMessage

# 导入电商版状态
from ..state import EcommerceMainServiceState
from agents.ecommerce_service.core import filter_messages_for_agent, max_msg_len, base_model
from agents.ecommerce_service.context_engineering.prompts import main_graph_prompts
from agents.ecommerce_service.context_engineering.agent_memory import memory_enabled_agent
from common.logging import get_logger
from auth.context import get_current_user_global
logger = get_logger("agents.main-nodes.chitchat")

@memory_enabled_agent(application_id="电商主智能客服")
async def chitchat_agent(state: EcommerceMainServiceState, config: RunnableConfig):
    """
    处理电商客服场景下的闲聊、问候及非业务问题的节点函数
    """
    logger.info("进入电商闲聊子智能体")
    
    # 1. 获取基本参数
    # user_id = config["configurable"].get("user_id", "unknown_user")
    # user_query = state.get("user_query", "") or config["configurable"].get("user_query", "")
    current_user = get_current_user_global()
    
    # 处理用户可能未登录（None）的情况
    if current_user:
        user_id = str(current_user.id) # 假设 User 模型有 id 字段
    else:
        user_id = "unknown_user"
        username = "访客"

    # user_query 通常存在 state 中，不需要改 context，因为它是当前对话的内容
    user_query = state.get("user_query", "") or config["configurable"].get("user_query", "")
    
    # 打印日志验证
    logger.info(f"当前处理用户: {username} (ID: {user_id})")
    # 2. 准备语言环境
    translator_result = state.get("translator_result")
    language = translator_result.language if translator_result else "中文"
    
    # 3. 构建提示模板 
    # 注意：确保 main_graph_prompts.CHITCHAT_SYSTEM_PROMPT 已经是电商“亲亲”风格的提示词
    chitchat_prompt = ChatPromptTemplate.from_messages([
        ("system", main_graph_prompts.CHITCHAT_SYSTEM_PROMPT),
        ("placeholder", "{messages}"),
        ("human", "{user_query}")
    ]).partial(time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    
    chain = chitchat_prompt | base_model
    
    # 4. 获取过滤后的消息历史
    # 这里的 agent_name 建议改为电商相关，以便过滤逻辑识别
    agent_label = "电商闲聊子智能体"
    new_messages = filter_messages_for_agent(state, max_msg_len, agent_label)

    messages = new_messages if len(new_messages) > 0 else [AIMessage(content="暂无对话历史")]
    
    # 5. 调用模型生成回复
    try:
        res = await chain.ainvoke({
            "messages": messages,
            "user_query": user_query,
            "language": language
        })
        
        # 统一设置智能体名称（这会显示在前端，并存入历史记录）
        res.name = "电商闲聊子智能体" 
        
        logger.info(f"闲聊回复生成成功: {res.content[:20]}...")
        return {"messages": [res]}
        
    except Exception as e:
        logger.error(f"闲聊节点执行异常: {e}")
        # 极简兜底回复，防止用户完全得不到响应
        fallback_res = AIMessage(
            content="亲亲，不好意思刚才走神了，小二在的，有什么我可以帮您的吗？", 
            name="电商闲聊子智能体"
        )
        return {"messages": [fallback_res]}
# @memory_enabled_agent(application_id="机场主智能客服")
# async def chitchat_agent(state: AirportMainServiceState, config: RunnableConfig):
#     """
#     处理闲聊问题的节点函数

#     Args:
#         state: 当前状态对象
#         config: 可运行配置

#     Returns:
#         更新后的状态对象，包含闲聊回复
#     """
#     logger.info("机场知识问答2号子智能体:")
    
#     # 获取用户信息
#     user_id = config["configurable"].get("user_id", "unknown_user")
#     user_query = state.get("user_query", "") if state.get("user_query", "") else config["configurable"].get("user_query", "")
    
#     # 准备上下文信息
#     translator_result = state.get("translator_result")
#     language = translator_result.language if translator_result else "中文"
    

#     chitchat_prompt = ChatPromptTemplate.from_messages([
#         ("system", main_graph_prompts.CHITCHAT_SYSTEM_PROMPT),
#         ("placeholder", "{messages}"),
#         ("human", "{user_query}")
#     ]).partial(time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    
#     chain = chitchat_prompt | base_model
    
#     # 获取消息历史
#     new_messages = filter_messages_for_agent(state, max_msg_len, "机场知识问答2号子智能体")

#     messages = new_messages if len(new_messages) > 0 else [AIMessage(content="暂无对话历史")]
    
#     res = await chain.ainvoke({"messages": messages,"user_query":user_query,"language":language})
#     # response = AIMessage(content="抱歉您的问题我暂时无法回答，请你拨打客服电话进行咨询。14634563456")
#     res.name = "机场知识问答1号子智能体"
    
#     return {"messages": [res]}
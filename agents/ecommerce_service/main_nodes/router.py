"""
电商路由节点
"""
from pydantic import BaseModel, Field
from typing import Literal
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableConfig

# 导入电商版状态和提示词
from agents.ecommerce_service.state import EcommerceMainServiceState
from agents.ecommerce_service.context_engineering.prompts import main_graph_prompts
from agents.ecommerce_service.core import filter_messages_for_llm, max_msg_len, structed_model
from agents.ecommerce_service.context_engineering.agent_memory import memory_enabled_agent
from common.logging import get_logger

# 获取路由节点专用日志记录器
logger = get_logger("agents.nodes.router")

class Route(BaseModel):
    step: Literal["order_logistics", "transaction_action", "shopping_guide","chitchat"] = Field(
        None,
        description=(
            "用于标识电商用户当前的主要意图分类。\n\n"
            "- order_logistics：订单与物流查询，涉及订单状态、物流轨迹、快递单号等。\n"
            "- transaction_action：高风险交易操作，涉及申请退款、修改地址、领取优惠券、取消订单等动作。"
            "- shopping_guide：商品导购与推荐、咨询商品属性、尺码、帮忙找商品、平台活动规则、退换货政策说明。"
            "- chitchat：打招呼、问候、谢谢、再见及无意义的闲聊。"
        )
    )

# 结构化输出模型
router_model = structed_model.with_structured_output(Route, method="json_schema", strict=False)
# 修改为电商应用ID
@memory_enabled_agent(application_id="电商主智能客服")
async def identify_intent(state: EcommerceMainServiceState, config: RunnableConfig):
    metadata = config["configurable"].get("metadata", {})
    # 保持兼容性获取 query
    user_query = state.get("user_query", "") if state.get("user_query", "") else config["configurable"].get("user_query", "")

    logger.info(f"进入电商意图识别：{user_query}")

    router_assistant_prompt = ChatPromptTemplate.from_messages([
        ("system", main_graph_prompts.ROUTER_SYSTEM_PROMPT),
        ("human", main_graph_prompts.ROUTER_HUMAN_PROMPT)
    ])

    chain = router_assistant_prompt | router_model
    messages = filter_messages_for_llm(state, max_msg_len)

    try:
        res = await chain.ainvoke({"messages": messages, "user_query": user_query})

        # 【核心改动】：删除 messages 列表，只返回 router 状态位
        # 这样既能完成跳转，又不会触发装饰器里那个带 Bug 的存储逻辑
        return {
            "router": res.step,
            # "user_query": user_query,
            "metadata": metadata
        }

    except Exception as e:
        logger.error(f"主路由子智能体执行失败: {e}")
        # 出错时默认走向闲聊，同样不返回 messages
        return {
            "router": "chitchat",
            # "user_query": user_query,
            "metadata": metadata
        }
def route_to_next_node(state: EcommerceMainServiceState):
    """
    根据识别到的意图(intent_category)分发到对应的处理节点
    """
    intent_category = state.get("router", "")
    logger.info(f"最终路由决策: {intent_category}")

    if intent_category == "order_logistics":
        return "order_logistics_search_node"
    elif intent_category == "transaction_action":
        return "business_assistant_node"
    elif intent_category == "shopping_guide":
        return "product_info_search_node"
    elif intent_category == "chitchat":
        return "chitchat_node"
    else:
        return "chitchat_node"

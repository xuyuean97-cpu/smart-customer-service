"""
电商订单与物流信息节点
"""
import sys
import os
import json
from datetime import datetime

# 保持原有路径引用逻辑
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../")))

# 假设 State 类已重命名或保持兼容
from agents.ecommerce_service.state import EcommerceMainServiceState
from langchain_core.runnables import RunnableConfig
from langchain_core.prompts import ChatPromptTemplate
# 这里的 tools 需要指向电商版的查询工具
from agents.ecommerce_service.tools import order_query2docs, get_text2sql_instance
from langchain_core.messages import AIMessage
from agents.ecommerce_service.core import filter_messages_for_agent, max_msg_len, base_model, extract_order_ids_from_result
from agents.ecommerce_service.context_engineering.prompts import main_graph_prompts
from agents.ecommerce_service.context_engineering.agent_memory import memory_enabled_agent
from langgraph.config import get_stream_writer
from common.logging import get_logger

# 修改日志记录器名称
logger = get_logger("agents.main-nodes.order_logistics")

def get_express_code_by_id(order_id: str) -> str:
    """
    根据订单号简单识别物流商代码（实际业务中通常从数据库字段获取，这里保留原有的提取逻辑结构）
    """
    if not order_id or len(order_id) < 2:
        return "DEFAULT"
    # 假设订单号前两位代表仓库或物流渠道简写
    return order_id[:2].upper()

async def build_and_run_order_sql_query(order_ids: list[str]) -> list:
    """查询订单详情与实时物流轨迹"""
    order_str = ",".join(f"'{o}'" for o in order_ids)
    sql = f"""
    SELECT *
    FROM order_logistics_tracking
    WHERE order_id IN ({order_str});
    """
    smart_sql = await get_text2sql_instance()
    result = await smart_sql.run_sql(sql.strip())
    return result

async def build_and_run_brand_logo_query(express_codes: list[str]) -> dict:
    """查询物流公司或品牌Logo"""
    if not express_codes:
        return {}

    unique_codes = list(set(code.upper() for code in express_codes if code))
    code_str = ",".join(f"'{code}'" for code in unique_codes)
    sql = f"""
    SELECT express_code, logo_data_uri
    FROM express_logos
    WHERE express_code IN ({code_str});
    """

    try:
        smart_sql = await get_text2sql_instance()
        result = await smart_sql.run_sql(sql.strip())

        logo_dict = {}
        if isinstance(result, list):
            for row in result:
                if isinstance(row, dict) and 'express_code' in row:
                    logo_dict[row['express_code']] = row['logo_data_uri']
        return logo_dict
    except Exception as e:
        logger.error(f"查询物流Logo数据时发生错误: {e}")
        return {}

async def send_order_info_to_user(sql_result):
    """向前端推送订单/物流信息卡片"""
    try:
        # 这里的提取函数需改为 extract_order_ids_from_result
        order_ids = extract_order_ids_from_result(sql_result)
        order_details = await build_and_run_order_sql_query(order_ids)
    except Exception as e:
        logger.error(f"解析订单数据失败: {e}")
        order_details = []

    if len(order_details) > 0:
        # 获取所有涉及的物流商代码
        express_codes = [get_express_code_by_id(str(o.get('order_id'))) for o in order_details if isinstance(o, dict)]
        logo_data = await build_and_run_brand_logo_query(express_codes)

        from models.schemas import OrderInfo

        send_data_list = []
        for order in order_details:
            if not isinstance(order, dict): continue

            # 通过 OrderInfo Pydantic 模型规范化字段名（旧机场名→新电商名）
            try:
                normalized = OrderInfo(**order).model_dump(exclude_none=True)
            except Exception:
                normalized = order.copy()

            # 电商特有：增加"再次购买"或"确认收货"的支持标识
            normalized["action_supported"] = True

            # 注入Logo（express_logo 可能未被 DB 字段填充，这里补上）
            exp_code = get_express_code_by_id(str(order.get('order_id')))
            normalized["express_logo"] = logo_data.get(exp_code)

            send_data_list.append(normalized)

        # 构建推送给前端的 JSON 对象
        subscribe_data = {
            "type": "order_card_list", # 对应前端电商卡片组件
            "data": send_data_list,
            "title": "您的订单实时状态",
            "action_hint": "点击单卡片可查看详细地图轨迹或联系配送员"
        }
        writer = get_stream_writer()
        writer({"node_name": "order_logistics_node", "data": subscribe_data})

@memory_enabled_agent(application_id="电商主智能客服")
async def order_logistics_agent(state: EcommerceMainServiceState, config: RunnableConfig):
    """
    提供订单与物流查询的节点函数
    """
    logger.info("进入订单物流查询子智能体")

    # 1. 载入电商版提示词
    kb_prompt = ChatPromptTemplate.from_messages([
        ("system", main_graph_prompts.ORDER_INFO_SYSTEM_PROMPT), # 使用之前改造的电商Prompt
        ("human", main_graph_prompts.ORDER_INFO_HUMAN_PROMPT)
    ]).partial(time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    # 2. 获取基础参数
    user_query = state.get("user_query", "") or config["configurable"].get("user_query", "")
     # 防御：如果 user_query 为空，不要往下走
    if not user_query:
        logger.warning("节点收到空的 user_query")
        from agents.ecommerce_service.state import RetrievalResult
        return {"retrieval_result": RetrievalResult(source="none", content="无输入", query_list=[""])}
    new_messages = filter_messages_for_agent(state, max_msg_len, "订单物流查询子智能体")
    messages = new_messages if len(new_messages) > 0 else [AIMessage(content="暂无对话历史")]

    # 3. 获取 SQL 检索结果（来自上一个 search 节点）
    retrieval_res = state.get("retrieval_result")
    sql_result = retrieval_res.content if retrieval_res else ""
    sql_query = retrieval_res.sql if retrieval_res else ""

    # 4. 调用 LLM 生成拟人化回复
    kb_chain = kb_prompt | base_model
    res = await kb_chain.ainvoke({
        "user_query": user_query,
        "sql": sql_query,
        "sql_result": sql_result,
        "messages": messages,
        "language": state.get("language", "zh")
    })
    res.name = "订单物流查询子智能体"

    # 5. 异步推送结构化卡片数据到前端
    if sql_result:
        try:
            await send_order_info_to_user(json.loads(sql_result))
        except:
            pass

    return {"messages": [res], "db_context_docs": None}

async def order_logistics_search(state: EcommerceMainServiceState, config: RunnableConfig):
    """
    负责执行 Text-to-SQL 的检索节点
    """
    messages = filter_messages_for_agent(state, max_msg_len, "订单物流查询子智能体")
    user_query = state.get("user_query", "") or config["configurable"].get("user_query", "")
    user_id = state.get("user_id", "guest")
    tenant_id = state.get("tenant_id", "default")

    retrieval_result = await order_query2docs(user_query, user_id, messages, tenant_id=tenant_id)
    return {"retrieval_result": retrieval_result}

"""
共享的工具函数
避免循环导入问题
"""
from typing import Dict, List
import re
from config.utils import config_manager
from common.logging import get_logger
# 从配置文件获取模型配置
model_config = config_manager.get_agents_config().get("llm", {})
max_msg_len = model_config.get("max_history_turns", 20)
max_tokens = model_config.get("max_tokens", 10000)
memery_delay = 60*30

# 获取text2kb配置
_text2kb_config = config_manager.get_text2kb_config()
KB_SIMILARITY_THRESHOLD = float(_text2kb_config.get("kb_similarity_threshold"))
# 获取情感分析配置
emotion = config_manager.get_agents_config().get("emotions","tabularisai/multilingual-sentiment-analysis")
logger = get_logger("agents.utils")

from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
import logging

logger = logging.getLogger("agents.utils")

import logging

logger = logging.getLogger("agents.utils")

def filter_messages_for_agent(state: Dict, turn_count: int = 5, agent_role: str = "user") -> List:
    """
    根据对话轮次和智能体角色筛选消息（终极增强版）
    """
    messages = state.get("messages", [])
    if not messages:
        return []

    logger.info(f"筛选前的的消息列表：{messages}")

    # 1. 找到目标智能体【最后一次发言】的索引位置
    target_last_ai_idx = -1
    for i in range(len(messages) - 1, -1, -1):
        msg = messages[i]
        if isinstance(msg, AIMessage) and getattr(msg, 'name', None) == agent_role:
            target_last_ai_idx = i
            break

    # 2. 提取【当前新问题】
    # 也就是在目标 AI 最后一次发言之后，用户发出的所有新消息
    new_context = []
    for i in range(target_last_ai_idx + 1, len(messages)):
        if isinstance(messages[i], HumanMessage):
            new_context.append(messages[i])

    # 3. 提取【历史对话记录】
    historical_messages = []
    turns_collected = 0

    i = target_last_ai_idx
    while i >= 0 and turns_collected < turn_count:
        msg = messages[i]

        # 只处理目标智能体的消息
        if isinstance(msg, AIMessage) and getattr(msg, 'name', None) == agent_role:
            turn_msgs = []

            # a) 往前找这句 AI 回答对应的 User 历史提问
            for j in range(i - 1, -1, -1):
                if isinstance(messages[j], HumanMessage):
                    turn_msgs.append(messages[j])
                    break

            # b) 加入 AI 消息本身
            turn_msgs.append(msg)

            # c) 往后找这句 AI 调用的 Tool 工具结果
            has_tool_calls = hasattr(msg, 'tool_calls') and msg.tool_calls
            if has_tool_calls:
                for k in range(i + 1, len(messages)):
                    if isinstance(messages[k], ToolMessage):
                        turn_msgs.append(messages[k])
                    elif isinstance(messages[k], (AIMessage, HumanMessage)):
                        # 遇到下一轮对话，停止收集工具结果
                        break

            # 将收集到的一轮完整记录拼接到前面（保持全局时间正序）
            historical_messages = turn_msgs + historical_messages
            turns_collected += 1

        i -= 1

    # 最终结果 = 历史对话记录 + 还没回答的新问题
    filtered_messages = historical_messages + new_context

    logger.info(f"为智能体 '{agent_role}' 筛选消息，目标轮次: {turn_count}，实际收集轮次: {turns_collected}，筛选后消息数: {len(filtered_messages)}")
    logger.debug(f"筛选后的消息列表: {filtered_messages}")

    return filtered_messages
# def filter_messages_for_agent(state: Dict, turn_count: int = 5, agent_role: str = "user") -> List:
#     """
#     根据对话轮次和智能体角色筛选消息

#     逻辑说明：
#     - 根据AI消息的name属性筛选特定agent的对话内容
#     - 检测AI消息是否有tool_calls参数
#     - 根据智能体类型确定用户消息位置：
#       * 主路由智能体：用户消息在AI消息前一位
#       * 其他智能体：用户消息在AI消息前三位
#     - 如果没有tool_calls，取该消息 + 对应位置的用户消息
#     - 如果有tool_calls，除了取用户消息，还要取AI消息后一位的工具消息
#     - 消息格式：[query, ai_router_msg, tool_msg, agent1_msg, query, ai_router_msg, tool_msg, agent2_msg, ...]

#     Args:
#         state: 包含消息列表的状态字典
#         turn_count: 要提取的对话轮次数量
#         agent_role: 智能体角色名称，用于匹配AI消息的name属性。如果为"user"则不进行筛选

#     Returns:
#         筛选后的消息列表
#     """
#     from langchain_core.messages import HumanMessage, AIMessage, ToolMessage

#     messages = state.get("messages", [])
#     if not messages:
#         return []
#     logger.info(f"筛选前的的消息列表：{messages}")
#     filtered_messages = []
#     turn_collected = 0

#     # 从后往前遍历消息，查找AI消息
#     for i in range(len(messages) - 1, -1, -1):
#         if turn_collected >= turn_count:
#             break

#         msg = messages[i]

#         # 只处理AI消息，并且检查agent名称是否匹配
#         if isinstance(msg, AIMessage):
#             # 检查AI消息的name属性是否匹配指定的agent_role
#             msg_agent_name = getattr(msg, 'name', None)
#             if msg_agent_name != agent_role:
#                 continue

#             # 根据智能体类型确定用户消息的位置
#             if agent_role == "主路由智能体":
#                 user_msg_step = 1  # 主路由智能体的用户消息在前面一位
#             else:
#                 user_msg_step = 3  # 其他智能体的用户消息在前面三位

#             current_turn_messages = []

#             # 检查AI消息是否有tool_calls
#             has_tool_calls = hasattr(msg, 'tool_calls') and msg.tool_calls

#             # 按时间顺序收集消息：用户消息 -> AI消息 -> 工具消息
#             if has_tool_calls:
#                 # 有tool_calls的情况
#                 # 1. 添加用户消息（如果存在）
#                 if i - user_msg_step >= 0 and isinstance(messages[i - user_msg_step], HumanMessage):
#                     current_turn_messages.append(messages[i - user_msg_step])

#                 # 2. 添加AI消息本身
#                 current_turn_messages.append(msg)

#                 # 3. 添加AI消息后一位的工具消息（如果存在）
#                 if i + 1 < len(messages) and isinstance(messages[i + 1], ToolMessage):
#                     current_turn_messages.append(messages[i + 1])
#             else:
#                 # 没有tool_calls的情况
#                 # 1. 添加用户消息（如果存在）
#                 if i - user_msg_step >= 0 and isinstance(messages[i - user_msg_step], HumanMessage):
#                     current_turn_messages.append(messages[i - user_msg_step])

#                 # 2. 添加AI消息本身
#                 current_turn_messages.append(msg)

#             # 如果成功收集到消息，则添加到结果中并增加轮次计数
#             if current_turn_messages:
#                 # 将当前轮次的消息添加到结果列表的开头，保持最新的在前面
#                 filtered_messages = current_turn_messages + filtered_messages
#                 turn_collected += 1
#     logger.info(f"为智能体 '{agent_role}' 筛选消息，目标轮次: {turn_count}，实际收集轮次: {turn_collected}，总消息数: {len(messages)}，筛选后消息数: {len(filtered_messages)}")
#     logger.debug(f"筛选后的消息列表: {filtered_messages}")
#     return filtered_messages



def filter_messages_for_llm(state: Dict, nb_messages: int = 10) -> List:
    """
    专门用于LLM调用的消息过滤函数
    移除所有ToolMessage和有tool_calls的消息，只保留Human和AI的对话消息
    """
    from langchain_core.messages import HumanMessage, AIMessage
    messages = state.get("messages", [])
    filtered_messages = []
    for idx,msg in enumerate(messages[::-1]):
        if idx < nb_messages:
            if isinstance(msg, HumanMessage) and idx != 0:
                filtered_messages.append(msg)
            elif isinstance(msg, AIMessage) and not (hasattr(msg, 'tool_calls') and msg.tool_calls):
                filtered_messages.append(msg)
    return filtered_messages
# from typing import Dict, List
# from langchain_core.messages import HumanMessage, AIMessage

# from typing import Dict, List
# from langchain_core.messages import HumanMessage, AIMessage

# def filter_messages_for_llm(state: Dict, nb_messages: int = 10) -> List:
#     """
#     专门用于LLM调用的消息过滤函数
#     移除所有ToolMessage和有tool_calls的消息，只保留Human和AI的对话消息
#     【核心】彻底剥离所有并发推荐接口注入的伪造数据
#     """
#     messages = state.get("messages", [])

#     # ==========================================
#     # 第一步：彻底清洗并发子图产生的脏数据
#     # ==========================================
#     clean_messages = []
#     for msg in messages:
#         # 1. 过滤假 HumanMessage (问题推荐和业务推荐 API 强塞的)
#         if isinstance(msg, HumanMessage) and isinstance(msg.content, str):
#             if msg.content.startswith("__RECOMMEND_TASK__") or msg.content.startswith("__BUSINESS_TASK__"):
#                 continue

#         # 2. 过滤假 AIMessage (各种推荐节点返回的 JSON 数组)
#         if isinstance(msg, AIMessage):
#             msg_name = getattr(msg, "name", "")
#             # 把你系统里所有不该被当做聊天记录的 name 全加进来
#             if msg_name in ["recommend_json_result", "business_json_result", "业务推荐子智能体"]:
#                 continue

#         clean_messages.append(msg)

#     # ==========================================
#     # 第二步：执行你原有的过滤逻辑
#     # ==========================================
#     filtered_messages = []
#     for idx, msg in enumerate(clean_messages[::-1]):
#         if idx < nb_messages:
#             if isinstance(msg, HumanMessage) and idx != 0:
#                 filtered_messages.append(msg)
#             elif isinstance(msg, AIMessage) and not (hasattr(msg, 'tool_calls') and msg.tool_calls):
#                 filtered_messages.append(msg)

#     logger.info(f"过滤前消息总数: {len(messages)}, 过滤后消息总数: {len(filtered_messages)}")
#     logger.debug(f"过滤后的消息列表: {filtered_messages}")
#     return filtered_messages





def extract_order_ids_from_result(sql_result):
    """
    从 SQL 查询结果中提取订单号 (Order IDs) 或物流单号。
    适应电商场景：通常是 12 到 20 位的纯数字字符串。
    """
    # 模式 A: 匹配 12 到 20 位的纯数字 (主流电商订单号格式)
    # 如果你的订单号带字母（如 ORD20231024），请改为 r'\b[A-Z0-9-]{10,24}\b'
    pattern = re.compile(r'\b\d{12,20}\b')
    order_ids = set()

    if not isinstance(sql_result, list):
        return []

    for row in sql_result:
        if not isinstance(row, dict):
            continue

        # 优化点 1: 优先直接从已知键名获取，准确率最高
        # 检查常见的订单号键名
        for key in ['order_id', 'order_no', 'tracking_number', 'out_trade_no']:
            if key in row and row[key]:
                order_ids.add(str(row[key]))

        # 优化点 2: 兜底逻辑——如果字段名对不上，再遍历所有值进行正则匹配
        for value in row.values():
            if isinstance(value, (str, int)):
                val_str = str(value)
                matches = pattern.findall(val_str)
                order_ids.update(matches)

    return list(order_ids)



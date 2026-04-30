
"""
人工转接 + 工单创建节点
"""
import sys
import os
import uuid
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../")))
from langchain_core.runnables import RunnableConfig
from agents.ecommerce_service.state import EcommerceMainServiceState
from langchain_core.messages import AIMessage
from common.logging import get_logger
from agents.ecommerce_service.context_engineering.agent_memory import memory_enabled_agent

logger = get_logger("agents.main-nodes.human")


@memory_enabled_agent(application_id="电商主智能客服")
async def transfer_to_human(state: EcommerceMainServiceState, config: RunnableConfig):
    """
    转人工节点 — 创建工单 + 通知坐席
    """
    logger.info("进入转人工节点")

    tenant_id = state.get("tenant_id", "default")
    user_id = state.get("user_id") or config.get("configurable", {}).get("user_id", "unknown_user")
    user_query = state.get("user_query", "") or config.get("configurable", {}).get("user_query", "")

    emotion_result = state.get("emotion_result", {})
    reason = emotion_result.get("reason", "用户主动请求转人工")

    # 1. 创建工单
    ticket_id = await _create_transfer_ticket(
        tenant_id=tenant_id,
        user_id=user_id,
        query=user_query,
        reason=reason,
    )

    if ticket_id:
        logger.info(f"转人工工单已创建: {ticket_id}")
        reply = f"已为您转接人工客服，工单号: {ticket_id[-8:]}。请稍候，客服将尽快接入。"
    else:
        reply = "已为您转接人工客服，请稍候。"

    return {"messages": [AIMessage(content=reply, name="转人工子智能体")]}


def route_to_next(state: EcommerceMainServiceState):
    emotion_result = state.get("emotion_result", {})
    if emotion_result.get("is_negative", False):
        return "transfer_to_human"
    else:
        return "images_thinking_node"


async def _create_transfer_ticket(
    tenant_id: str,
    user_id: str,
    query: str,
    reason: str,
) -> str:
    """在数据库中创建工单"""
    try:
        import asyncpg
        import os as _os
        conn = await asyncpg.connect(
            host=_os.getenv("DB_HOST", "47.106.22.90"),
            port=int(_os.getenv("DB_PORT", "5432")),
            user=_os.getenv("DB_USER", "postgres"),
            password=_os.getenv("DB_PASSWORD", "123456"),
            database=_os.getenv("DB_DATABASE", "test"),
            timeout=10,
        )
        try:
            from datetime import datetime
            ticket_id = str(uuid.uuid4())
            now = datetime.now()
            summary = f"[转人工] {query[:80]} — {reason[:80]}"
            await conn.execute(
                """INSERT INTO tickets (id, tenant_id, user_id, status, priority, summary, context, created_at, updated_at)
                   VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9)""",
                ticket_id, tenant_id, user_id, "open", "high",
                summary,
                f"用户问题: {query}\n转接原因: {reason}",
                now, now,
            )
            return ticket_id
        finally:
            await conn.close()
    except Exception as e:
        logger.error(f"创建工单失败: {e}")
        return ""

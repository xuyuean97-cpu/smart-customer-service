import sys
import os
# 添加项目根目录到系统路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))
from typing import List
from langchain_core.messages import AnyMessage
import asyncio
import json
from agents.ecommerce_service.core.query import comprehensive_query_transform
from text2sql import create_text2sql
from config.utils import config_manager
from common.logging import get_logger
from agents.ecommerce_service.state import RetrievalResult

# 获取订单物流工具专用日志记录器
logger = get_logger("agents.tools.order_logistics")

# 全局变量缓存text2sql实例
_text2sql_instance = None
_text2sql_lock = asyncio.Lock()

async def get_text2sql_instance():
    """获取text2sql实例，如果不存在则创建一个"""
    global _text2sql_instance

    # 使用锁确保在并发环境下只初始化一次
    async with _text2sql_lock:
        if _text2sql_instance is None:
            try:
                logger.info("开始初始化text2sql实例")
                # 获取text2sql配置
                text2sql_config = config_manager.get_text2sql_config()
                _text2sql_instance = await create_text2sql(text2sql_config)
                logger.info("text2sql实例初始化成功")
            except Exception as e:
                logger.error(f"初始化text2sql实例时出错: {str(e)}")
                raise

    return _text2sql_instance



async def order_query2docs(question: str, user_id: str, messages: List[AnyMessage], tenant_id: str = "default") -> RetrievalResult:
    """
    查询电商订单、物流动态及历史交易记录的工具。
    """
    logger.info("进入订单查询工具")
    logger.info(f"order_query2docs+DEBUG的用户id: {user_id}, tenant_id: {tenant_id}")
    if not question:
        return RetrievalResult(source="none", content="[]", query_list=[""])

    # 1. 意图重写
    rewritten_query = await comprehensive_query_transform(question, 'order_rewrite', messages)
    if rewritten_query is None:
        rewritten_query = question

    # 2. 执行 SQL 查询（带上下文注入）
    async def perform_query(query, user_id, tenant_id):
        if not query:
            return {"data": [], "sql": ""}
        try:
            smart_sql = await get_text2sql_instance()
            result = await smart_sql.ask(query, user_id=user_id, tenant_id=tenant_id)
            return result
        except Exception as e:
            logger.error(f"SQL生成/执行阶段发生异常: {e}")
            return {"error": True, "message": str(e), "data": [], "sql": ""}

    result = await perform_query(rewritten_query, user_id, tenant_id)

    # --- P1-5: API Fallback — 本地查不到时调平台 API 实时拉取 ---
    data_is_empty = not result.get('data') or result.get('data') == []
    if data_is_empty and not result.get('error'):
        platform_order_id = _extract_platform_order_id(question)
        if platform_order_id:
            logger.info(f"本地无数据，尝试平台 API Fallback: {platform_order_id}")
            platform_data = await _fetch_from_platform_adapter(platform_order_id, tenant_id)
            if platform_data:
                await _upsert_to_local_db(platform_data)
                # P1-5: 不二次查库，直接用平台数据（避免幻读 + 省一次 LLM 往返）
                result = {'data': [platform_data], 'sql': '-- from platform API'}
                logger.info(f"平台 API Fallback 成功: {platform_order_id}")

    # --- 关键增强：错误拦截逻辑 (防止 Agent 拒答) ---
    final_content = "[]"
    sql_text = result.get("sql", "")

    if result.get("error") is True:
        # 如果数据库层面报错（比如表名还是错了），我们传给 Agent 一个清晰的“未查到”信号
        # 而不是把 DB 报错信息扔给它，否则 Agent 会因为理解不了 SQL 错误而卡死
        logger.warning(f"检测到后端SQL执行错误，已拦截并重定向意图: {result.get('message')}")
        final_content = json.dumps({"status": "not_found", "reason": "database_error_or_missing_table"})
    else:
        # 正常结果处理
        data = result.get("data", [])
        if not data:
            final_content = "[]"
        else:
            final_content = json.dumps(data, ensure_ascii=False)

    # 3. 构造返回对象
    safe_query_list = [question]
    if rewritten_query:
        safe_query_list.append(str(rewritten_query))

    return RetrievalResult(
        source="order",
        content=final_content,
        sql=sql_text,
        query_list=safe_query_list
    )

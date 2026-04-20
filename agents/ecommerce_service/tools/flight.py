from datetime import datetime
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

# 获取航班工具专用日志记录器
logger = get_logger("agents.tools.flight")

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



# async def order_query2docs(question: str, messages:List[AnyMessage]) -> str:
#     """
#     查询航班信息的工具
#     此工具用于回答用户关于航班的各类查询
    
#     Args:
#         question: 用户提出的航班相关问题，应当是一个表达完整，意图明确的问句，例如"CA1234航班什么时候到达？"
#                  "从北京到上海的航班有哪些？"或"明天的MU5678航班是什么机型？"等。如果问题不清晰，则需要用户继续澄清诉求。
#     Examples:
#         >>> flight_info_query("CA1234航班现在的状态是什么？")
#         "CA1234航班目前正在飞行中，预计17:30到达目的地，暂无延误。"
#     """
#     logger.info("进入航班信息查询工具")
#     # 定义异步查询函数
#     async def perform_query(query):
#         try:
#             # 获取缓存的text2sql实例，避免重复初始化
#             smart_sql = await get_text2sql_instance()
#             # 调用ask方法获取结果
#             result = await smart_sql.ask(query)
#             return result
#         except Exception as e:
#             error_msg = f"查询航班信息时出错: {str(e)}"
#             logger.error(error_msg)
#             return error_msg

#     # 执行异步查询
#     rewritten_query = await comprehensive_query_transform(question,'flight_rewrite',messages)
#     result = await perform_query(rewritten_query)
#     logger.debug(f"查询结果: {result}")
#     print(f"DEBUG - result type: {type(result)}")
#     print(f"DEBUG - result content: {result}")
#     return RetrievalResult(
#         source="flight",
#         content=json.dumps(result["data"]),
#         sql=result["sql"],
#         query_list=[rewritten_query]
#     )
async def order_query2docs(question: str, user_id: str, messages: List[AnyMessage]) -> RetrievalResult:
    """
    查询电商订单、物流动态及历史交易记录的工具。
    """
    logger.info("进入订单查询工具")
    logger.info(f"order_query2docs+DEBUG的用户id: {user_id}")
    if not question:
        return RetrievalResult(source="none", content="[]", query_list=[""])

    # 1. 意图重写
    rewritten_query = await comprehensive_query_transform(question, 'order_rewrite', messages)
    if rewritten_query is None:
        rewritten_query = question
    
    # 2. 执行 SQL 查询（带上下文注入）
    async def perform_query(query,user_id):
        logger.info(f"perform_query+DEBUG的用户id: {user_id}")
        if not query:
            return {"data": [], "sql": ""}
        try:
            smart_sql = await get_text2sql_instance()
            result = await smart_sql.ask(query,user_id=user_id)
            return result
        except Exception as e:
            logger.error(f"SQL生成/执行阶段发生异常: {e}")
            # 返回一个标准化的错误字典，方便下方进行拦截
            return {"error": True, "message": str(e), "data": [], "sql": ""}

    result = await perform_query(rewritten_query, user_id)

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
# if __name__ == "__main__":
#     import asyncio
#     import json
#     from langchain_core.messages import HumanMessage

#     async def _debug_main():
#         question = "订单123456现在到哪了？"
#         messages = [
#             HumanMessage(content=question)
#         ]

#         result = await order_query2docs(question, messages)

#         print("\n===== DEBUG order_query2docs =====")
#         print("source     :", result.source)
#         print("sql        :", result.sql)
#         print("query_list :", result.query_list)

#         print("content(raw):", result.content)
#         try:
#             print("content(json):")
#             for row in json.loads(result.content):
#                 print(row)
#         except Exception as e:
#             print("content parse error:", e)

#     asyncio.run(_debug_main())
    
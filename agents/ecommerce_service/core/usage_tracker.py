"""
LLM Token 用量追踪器 — LangChain Callback + 异步写入 UsageLog
"""
from typing import Any, Dict, List
from langchain_core.callbacks import BaseCallbackHandler
from common.logging import get_logger

logger = get_logger("agents.usage_tracker")


class UsageTrackingCallback(BaseCallbackHandler):
    """
    LangChain 回调处理器，拦截 LLM 响应的 token 用量并写入 UsageLog。

    用法:
        from agents.ecommerce_service.core.usage_tracker import usage_callback
        chain = prompt | model.with_config({"callbacks": [usage_callback]})
    """

    def __init__(self, tenant_id: str = "default", endpoint: str = "chat"):
        self.tenant_id = tenant_id
        self.endpoint = endpoint
        self._pending: List[Dict[str, Any]] = []
        super().__init__()

    def on_llm_end(self, response, **kwargs) -> None:
        """LLM 响应完成时触发，提取 token 用量"""
        try:
            # 从 LangChain 响应中提取 token 信息
            llm_output = getattr(response, 'llm_output', {}) or {}
            token_usage = llm_output.get('token_usage', {})

            # 兼容不同的响应格式
            generations = getattr(response, 'generations', [[]])
            response_metadata = {}
            if generations and generations[0]:
                gen = generations[0][0]
                response_metadata = getattr(gen, 'generation_info', {}) or {}
                # OpenAI 格式: response_metadata 里有 token_usage
                if not token_usage:
                    token_usage = response_metadata.get('token_usage', {})

            # 提取具体数值
            tokens_in = (
                token_usage.get('prompt_tokens', 0)
                or token_usage.get('input_tokens', 0)
                or response_metadata.get('input_tokens', 0)
            )
            tokens_out = (
                token_usage.get('completion_tokens', 0)
                or token_usage.get('output_tokens', 0)
                or response_metadata.get('output_tokens', 0)
            )
            total_tokens = token_usage.get('total_tokens', 0) or (tokens_in + tokens_out)

            if total_tokens > 0:
                model_name = (
                    response_metadata.get('model_name', '')
                    or llm_output.get('model_name', '')
                )
                self._pending.append({
                    "tenant_id": self.tenant_id,
                    "endpoint": self.endpoint,
                    "model": model_name or "unknown",
                    "tokens_in": int(tokens_in),
                    "tokens_out": int(tokens_out),
                    "success": True,
                })

        except Exception as e:
            logger.debug(f"提取 token 用量失败（非致命）: {e}")

    def on_llm_error(self, error, **kwargs) -> None:
        """LLM 调用出错"""
        self._pending.append({
            "tenant_id": self.tenant_id,
            "endpoint": self.endpoint,
            "model": "unknown",
            "tokens_in": 0,
            "tokens_out": 0,
            "success": False,
        })

    async def flush(self):
        """将积攒的用量写入数据库"""
        if not self._pending:
            return

        from auth.database import SessionLocal
        from auth.models import UsageLog

        db = SessionLocal()
        try:
            for record in self._pending:
                log = UsageLog(
                    tenant_id=record["tenant_id"],
                    endpoint=record["endpoint"],
                    model=record["model"],
                    tokens_in=record["tokens_in"],
                    tokens_out=record["tokens_out"],
                    success=record["success"],
                )
                db.add(log)
            db.commit()
            logger.debug(f"写入 {len(self._pending)} 条用量记录")
            self._pending.clear()
        except Exception as e:
            db.rollback()
            logger.warning(f"写入用量日志失败: {e}")
        finally:
            db.close()


# 全局 UsageTracker 管理
class UsageTrackerManager:
    """管理多个租户的 UsageTrackingCallback 实例"""

    def __init__(self):
        self._callbacks: Dict[str, UsageTrackingCallback] = {}

    def get_callback(self, tenant_id: str = "default", endpoint: str = "chat") -> UsageTrackingCallback:
        key = f"{tenant_id}:{endpoint}"
        if key not in self._callbacks:
            self._callbacks[key] = UsageTrackingCallback(
                tenant_id=tenant_id, endpoint=endpoint
            )
        return self._callbacks[key]

    async def flush_all(self):
        for callback in self._callbacks.values():
            await callback.flush()


usage_tracker = UsageTrackerManager()

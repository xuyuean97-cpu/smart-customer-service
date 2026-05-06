"""
统一 API 响应格式 — 所有端点返回 {code, message, data}
"""
from typing import Any
from pydantic import BaseModel


class ApiResponse(BaseModel):
    """统一响应包装"""
    code: int = 0          # 0=成功, 非0=错误码
    message: str = "ok"
    data: Any = None


def ok(data: Any = None, message: str = "ok") -> dict:
    return {"code": 0, "message": message, "data": data}


def fail(code: int, message: str, data: Any = None) -> dict:
    return {"code": code, "message": message, "data": data}

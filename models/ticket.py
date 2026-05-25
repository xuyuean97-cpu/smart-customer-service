"""
工单系统模型
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Literal


class TicketCreate(BaseModel):
    """创建工单请求"""
    tenant_id: str = "default"
    user_id: str
    conversation_id: Optional[str] = None
    priority: Literal["low", "medium", "high", "urgent"] = "medium"
    summary: str = Field(..., min_length=1, max_length=500, description="问题摘要")
    context: Optional[str] = Field(None, description="对话上下文JSON")


class TicketUpdate(BaseModel):
    """更新工单请求"""
    status: Optional[Literal["open", "in_progress", "resolved", "closed"]] = None
    priority: Optional[Literal["low", "medium", "high", "urgent"]] = None
    agent_id: Optional[str] = None
    resolution_note: Optional[str] = Field(None, description="处理备注")


class TicketResponse(BaseModel):
    """工单响应"""
    id: str
    tenant_id: str
    user_id: str
    conversation_id: Optional[str] = None
    status: str = "open"
    priority: str = "medium"
    summary: str
    agent_id: Optional[str] = None
    resolution_note: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    resolved_at: Optional[str] = None


class TicketListResponse(BaseModel):
    """工单列表"""
    tenant_id: str
    total: int
    tickets: List[TicketResponse] = []

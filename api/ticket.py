"""
工单系统 API — CRUD + 分配
"""
import uuid
from datetime import datetime
from fastapi import APIRouter, Query, HTTPException, WebSocket, WebSocketDisconnect
from typing import Optional
import asyncpg
import json

from models.ticket import TicketCreate, TicketUpdate, TicketResponse, TicketListResponse
from common.logging import get_logger

logger = get_logger("api.ticket")

router = APIRouter(prefix="/api/v1/tickets", tags=["工单系统"])

from config.db import get_db_config  # noqa: E402


async def _get_conn():
    cfg = get_db_config()
    return await asyncpg.connect(**cfg)


def _row_to_response(row) -> TicketResponse:
    return TicketResponse(
        id=row["id"],
        tenant_id=row.get("tenant_id", "default"),
        user_id=row["user_id"],
        conversation_id=row.get("conversation_id"),
        status=row.get("status", "open"),
        priority=row.get("priority", "medium"),
        summary=row.get("summary", ""),
        agent_id=row.get("agent_id"),
        resolution_note=row.get("resolution_note"),
        created_at=str(row.get("created_at", "")),
        updated_at=str(row.get("updated_at", "")),
        resolved_at=str(row.get("resolved_at", "")),
    )


# ---------- REST Endpoints ----------

@router.post("", response_model=TicketResponse, status_code=201)
async def create_ticket(body: TicketCreate):
    """创建工单"""
    ticket_id = str(uuid.uuid4())
    now = datetime.now()

    conn = await _get_conn()
    try:
        await conn.execute(
            """INSERT INTO tickets (id, tenant_id, user_id, conversation_id, status, priority, summary, context, created_at, updated_at)
               VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)""",
            ticket_id, body.tenant_id, body.user_id, body.conversation_id,
            "open", body.priority, body.summary, body.context, now, now,
        )
        logger.info(f"工单创建: {ticket_id} user={body.user_id}")
        return TicketResponse(
            id=ticket_id, tenant_id=body.tenant_id, user_id=body.user_id,
            status="open", priority=body.priority, summary=body.summary,
            created_at=str(now), updated_at=str(now),
        )
    finally:
        await conn.close()


@router.get("", response_model=TicketListResponse)
async def list_tickets(
    tenant_id: str = Query("default"),
    status: Optional[str] = Query(None),
    agent_id: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0),
):
    """工单列表"""
    conn = await _get_conn()
    try:
        where = ["tenant_id = $1"]
        params = [tenant_id]
        idx = 2
        if status:
            where.append(f"status = ${idx}")
            params.append(status)
            idx += 1
        if agent_id:
            where.append(f"agent_id = ${idx}")
            params.append(agent_id)
            idx += 1

        sql = f"SELECT * FROM tickets WHERE {' AND '.join(where)} ORDER BY created_at DESC LIMIT {limit} OFFSET {offset}"
        rows = await conn.fetch(sql, *params)
        count_sql = f"SELECT COUNT(*) FROM tickets WHERE {' AND '.join(where)}"
        total = await conn.fetchval(count_sql, *params)

        return TicketListResponse(
            tenant_id=tenant_id,
            total=total,
            tickets=[_row_to_response(r) for r in rows],
        )
    finally:
        await conn.close()


@router.get("/{ticket_id}", response_model=TicketResponse)
async def get_ticket(ticket_id: str):
    """工单详情"""
    conn = await _get_conn()
    try:
        row = await conn.fetchrow("SELECT * FROM tickets WHERE id = $1", ticket_id)
        if not row:
            raise HTTPException(404, "工单不存在")
        return _row_to_response(row)
    finally:
        await conn.close()


@router.patch("/{ticket_id}", response_model=TicketResponse)
async def update_ticket(ticket_id: str, body: TicketUpdate):
    """更新工单 — 状态/优先级/分配坐席"""
    conn = await _get_conn()
    try:
        existing = await conn.fetchrow("SELECT * FROM tickets WHERE id = $1", ticket_id)
        if not existing:
            raise HTTPException(404, "工单不存在")

        updates = []
        params = []
        idx = 1

        if body.status is not None:
            updates.append(f"status = ${idx}")
            params.append(body.status)
            idx += 1
            if body.status == "resolved":
                updates.append(f"resolved_at = ${idx}")
                params.append(datetime.now())
                idx += 1
        if body.priority is not None:
            updates.append(f"priority = ${idx}")
            params.append(body.priority)
            idx += 1
        if body.agent_id is not None:
            updates.append(f"agent_id = ${idx}")
            params.append(body.agent_id)
            idx += 1
        if body.resolution_note is not None:
            updates.append(f"resolution_note = ${idx}")
            params.append(body.resolution_note)
            idx += 1

        if not updates:
            return _row_to_response(existing)

        updates.append(f"updated_at = ${idx}")
        params.append(datetime.now())
        idx += 1
        params.append(ticket_id)

        sql = f"UPDATE tickets SET {', '.join(updates)} WHERE id = ${idx}"
        await conn.execute(sql, *params)
        row = await conn.fetchrow("SELECT * FROM tickets WHERE id = $1", ticket_id)
        logger.info(f"工单更新: {ticket_id} -> {body.model_dump(exclude_none=True)}")
        return _row_to_response(row)
    finally:
        await conn.close()


# ---------- 坐席通知 WebSocket ----------

_agent_connections: dict = {}  # agent_id → WebSocket


@router.websocket("/agent/ws")
async def agent_notify_ws(websocket: WebSocket, agent_id: str = "agent_1"):
    """坐席端 WebSocket — 接收新工单通知"""
    await websocket.accept()
    _agent_connections[agent_id] = websocket
    logger.info(f"坐席上线: {agent_id}")
    try:
        while True:
            data = await websocket.receive_text()
            # 坐席可发送心跳
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        logger.info(f"坐席下线: {agent_id}")
        _agent_connections.pop(agent_id, None)


async def notify_agent_new_ticket(agent_id: str, ticket: TicketResponse):
    """通知坐席有新工单"""
    ws = _agent_connections.get(agent_id)
    if ws:
        try:
            await ws.send_text(json.dumps({
                "type": "new_ticket",
                "ticket": ticket.model_dump(),
            }, ensure_ascii=False))
        except Exception:
            _agent_connections.pop(agent_id, None)

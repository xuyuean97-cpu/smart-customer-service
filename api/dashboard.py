"""
运营仪表盘 API — 用量统计、对话趋势、性能指标
"""
from fastapi import APIRouter, Query, Depends
from pydantic import BaseModel, Field
from api.middleware import verify_admin_token
from api.response import ok, fail
from typing import List, Dict, Any
from datetime import datetime, timedelta

from common.logging import get_logger

logger = get_logger("api.dashboard")

router = APIRouter(prefix="/api/v1/admin", tags=["运营仪表盘"])


# ---------- Response Models ----------

class DashboardOverview(BaseModel):
    tenant_id: str
    total_conversations: int = 0
    active_users_today: int = 0
    avg_quality_score: float = 0.0
    resolution_rate: float = 0.0
    human_transfer_rate: float = 0.0


class ConversationTrendPoint(BaseModel):
    date: str
    count: int
    avg_quality: float = 0.0


class ConversationTrendResponse(BaseModel):
    tenant_id: str
    days: int
    points: List[ConversationTrendPoint] = []


class PerformanceMetrics(BaseModel):
    tenant_id: str
    resolution_rate: float = 0.0
    human_transfer_rate: float = 0.0
    avg_quality_score: float = 0.0
    total_conversations: int = 0
    avg_response_length: float = 0.0


class TopUser(BaseModel):
    user_id: str
    conversation_count: int
    avg_quality: float = 0.0


class TopUsersResponse(BaseModel):
    tenant_id: str
    limit: int
    users: List[TopUser] = []


class UsageSummary(BaseModel):
    tenant_id: str
    total_tokens_in: int = 0
    total_tokens_out: int = 0
    total_requests: int = 0
    by_model: Dict[str, int] = Field(default_factory=dict)
    by_date: List[Dict[str, Any]] = []


# ---------- Helpers ----------

def _get_memory_manager():
    """懒加载 memory_manager（避免循环导入）"""
    from agents.ecommerce_service.context_engineering.memory_manager import memory_manager
    return memory_manager


async def _count_conversations(tenant_id: str, days: int = 30) -> int:
    """统计对话总数"""
    mm = _get_memory_manager()
    try:
        history = await mm.get_conversation_history(
            tenant_id=tenant_id,
            limit=10000
        )
        cutoff = datetime.now() - timedelta(days=days)
        count = 0
        for item in history:
            metadata = item.get('metadata', {})
            created = metadata.get('created_at')
            if created:
                if isinstance(created, str):
                    created = datetime.fromisoformat(created.replace('Z', '+00:00'))
                if hasattr(created, 'replace') and created.replace(tzinfo=None) >= cutoff:
                    count += 1
        return count
    except Exception as e:
        logger.warning(f"统计对话数失败: {e}")
        return 0


# ---------- Endpoints ----------

@router.get("/dashboard/overview")
async def dashboard_overview(tenant_id: str = Query("default", description="租户ID"), _: str = Depends(verify_admin_token)):
    """运营概览 — 总对话数、活跃用户、质量评分"""
    mm = _get_memory_manager()
    history = await mm.get_conversation_history(tenant_id=tenant_id, limit=10000)

    datetime.now().date()
    total = len(history)
    active_users = set()
    qualities = []
    resolutions = 0
    transfers = 0

    for item in history:
        metadata = item.get('metadata', {})
        uid = metadata.get('user_id') or item.get('user_id', '')
        if uid:
            active_users.add(uid)
        qs = metadata.get('quality_score', 0)
        if qs:
            qualities.append(float(qs))

    return ok(DashboardOverview(
        tenant_id=tenant_id,
        total_conversations=total,
        active_users_today=len(active_users),
        avg_quality_score=round(sum(qualities) / len(qualities), 3) if qualities else 0.0,
        resolution_rate=round(resolutions / total, 3) if total else 0.0,
        human_transfer_rate=round(transfers / total, 3) if total else 0.0,
    ).model_dump())


@router.get("/dashboard/conversations/trend")
async def conversations_trend(
    tenant_id: str = Query("default", description="租户ID"),
    days: int = Query(7, ge=1, le=90, description="统计天数"),
    _: str = Depends(verify_admin_token),
):
    """对话趋势 — 按日期统计对话量和质量"""
    mm = _get_memory_manager()
    history = await mm.get_conversation_history(tenant_id=tenant_id, limit=10000)

    today = datetime.now().date()
    date_buckets: Dict[str, Dict[str, Any]] = {}
    for d in range(days):
        date_str = (today - timedelta(days=d)).isoformat()
        date_buckets[date_str] = {"count": 0, "qualities": []}

    for item in history:
        metadata = item.get('metadata', {})
        created = metadata.get('created_at') or item.get('created_at', '')
        if created:
            if isinstance(created, str):
                try:
                    created_date = datetime.fromisoformat(created.replace('Z', '+00:00')).date()
                except Exception:
                    continue
            else:
                continue
            date_str = created_date.isoformat()
            if date_str in date_buckets:
                date_buckets[date_str]["count"] += 1
                qs = metadata.get('quality_score', 0)
                if qs:
                    date_buckets[date_str]["qualities"].append(float(qs))

    points = []
    for d in range(days - 1, -1, -1):
        date_str = (today - timedelta(days=d)).isoformat()
        bucket = date_buckets[date_str]
        qs_list = bucket["qualities"]
        points.append(ConversationTrendPoint(
            date=date_str,
            count=bucket["count"],
            avg_quality=round(sum(qs_list) / len(qs_list), 3) if qs_list else 0.0,
        ))

    return ok(ConversationTrendResponse(tenant_id=tenant_id, days=days, points=points).model_dump())


@router.get("/dashboard/performance")
async def performance_metrics(tenant_id: str = Query("default", description="租户ID"), _: str = Depends(verify_admin_token)):
    """性能指标 — 解决率、转人工率、质量评分"""
    mm = _get_memory_manager()
    history = await mm.get_conversation_history(tenant_id=tenant_id, limit=10000)

    total = len(history)
    qualities = []
    resp_lengths = []

    for item in history:
        metadata = item.get('metadata', {})
        qs = metadata.get('quality_score', 0)
        if qs:
            qualities.append(float(qs))
        response = metadata.get('response', '')
        if response:
            resp_lengths.append(len(response))

    return ok(PerformanceMetrics(
        tenant_id=tenant_id,
        total_conversations=total,
        avg_quality_score=round(sum(qualities) / len(qualities), 3) if qualities else 0.0,
        avg_response_length=round(sum(resp_lengths) / len(resp_lengths), 1) if resp_lengths else 0.0,
        resolution_rate=0.0,
        human_transfer_rate=0.0,
    ).model_dump())


@router.get("/dashboard/users/top")
async def top_users(
    tenant_id: str = Query("default", description="租户ID"),
    limit: int = Query(10, ge=1, le=100, description="返回数量"),
    _: str = Depends(verify_admin_token),
):
    """活跃用户排行 — 按对话数排序"""
    mm = _get_memory_manager()
    history = await mm.get_conversation_history(tenant_id=tenant_id, limit=10000)

    user_stats: Dict[str, Dict[str, Any]] = {}
    for item in history:
        metadata = item.get('metadata', {})
        uid = metadata.get('user_id') or item.get('user_id', '')
        if not uid:
            continue
        if uid not in user_stats:
            user_stats[uid] = {"count": 0, "qualities": []}
        user_stats[uid]["count"] += 1
        qs = metadata.get('quality_score', 0)
        if qs:
            user_stats[uid]["qualities"].append(float(qs))

    sorted_users = sorted(user_stats.items(), key=lambda x: x[1]["count"], reverse=True)[:limit]
    users = [
        TopUser(
            user_id=uid,
            conversation_count=stats["count"],
            avg_quality=round(sum(stats["qualities"]) / len(stats["qualities"]), 3)
            if stats["qualities"] else 0.0,
        )
        for uid, stats in sorted_users
    ]

    return ok(TopUsersResponse(tenant_id=tenant_id, limit=limit, users=users).model_dump())


@router.get("/reports/operational")
async def operational_report(tenant_id: str = Query("default", description="租户ID"), _: str = Depends(verify_admin_token)):
    """运营报告 — 复用 OperationalAnalyticsEngine"""
    try:
        from agents.ecommerce_service.context_engineering.profile.operational_analytics import (
            operational_analytics_engine
        )
        report = await operational_analytics_engine.generate_operational_report()
        # 注入 tenant_id
        if hasattr(report, 'model_dump'):
            data = report.model_dump()
        else:
            data = {"error": "无法序列化报告"}
        data["tenant_id"] = tenant_id
        return ok(data)
    except Exception as e:
        logger.error(f"生成运营报告失败: {e}")
        return fail(500, str(e))


@router.get("/billing/usage")
async def billing_usage(
    tenant_id: str = Query("default", description="租户ID"),
    days: int = Query(30, ge=1, le=365, description="统计天数"),
    _: str = Depends(verify_admin_token),
):
    """用量统计 — Token 消耗汇总"""
    from auth.database import SessionLocal
    from auth.models import UsageLog

    db = SessionLocal()
    try:
        cutoff = datetime.now() - timedelta(days=days)
        rows = db.query(UsageLog).filter(
            UsageLog.tenant_id == tenant_id,
            UsageLog.created_at >= cutoff,
        ).all()

        total_in = sum(r.tokens_in for r in rows)
        total_out = sum(r.tokens_out for r in rows)
        total_requests = len(rows)

        by_model: Dict[str, int] = {}
        by_date: Dict[str, Dict[str, int]] = {}
        for r in rows:
            model = r.model or "unknown"
            by_model[model] = by_model.get(model, 0) + r.tokens_in + r.tokens_out

            date_str = r.created_at.strftime("%Y-%m-%d") if r.created_at else "unknown"
            if date_str not in by_date:
                by_date[date_str] = {"tokens": 0, "requests": 0}
            by_date[date_str]["tokens"] += r.tokens_in + r.tokens_out
            by_date[date_str]["requests"] += 1

        return ok(UsageSummary(
            tenant_id=tenant_id,
            total_tokens_in=total_in,
            total_tokens_out=total_out,
            total_requests=total_requests,
            by_model=by_model,
            by_date=[{"date": k, **v} for k, v in sorted(by_date.items())],
        ).model_dump())
    finally:
        db.close()

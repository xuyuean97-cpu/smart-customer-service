"""
京东订单批量同步 — 从京东 API 拉取订单 → UPSERT 本地 orders 表
"""
import asyncio
from datetime import datetime, timedelta
from typing import Optional

import asyncpg
import os as _os

from common.logging import get_logger

logger = get_logger("tools.jd_order_sync")

_DB = dict(
    host=_os.getenv("DB_HOST", "47.106.22.90"),
    port=int(_os.getenv("DB_PORT", "5432")),
    user=_os.getenv("DB_USER", "postgres"),
    password=_os.getenv("DB_PASSWORD", "123456"),
    database=_os.getenv("DB_DATABASE", "test"),
)


# ===== 核心同步逻辑 =====

async def sync_jd_orders(
    tenant_id: str = "default",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    page_size: int = 50,
) -> dict:
    """
    从京东 API 批量拉取订单并 UPSERT 到本地库。

    Args:
        tenant_id: 租户ID
        start_date: 开始日期 YYYY-MM-DD (默认: 7天前)
        end_date:   结束日期 YYYY-MM-DD (默认: 今天)
        page_size:  每页数量

    Returns:
        {total, success, failed, details: [...]}
    """
    from agents.ecommerce_service.channels.platforms import get_adapter
    from agents.ecommerce_service.channels.platforms.credential import get_credentials

    if not start_date:
        start_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    if not end_date:
        end_date = datetime.now().strftime("%Y-%m-%d")

    # 1. 获取京东适配器和凭据
    creds = await get_credentials(tenant_id)
    jd_cred = creds.get("jd")
    if not jd_cred:
        return {"total": 0, "success": 0, "failed": 0, "error": "京东未授权"}

    adapter = get_adapter("jd")
    if not adapter:
        return {"total": 0, "success": 0, "failed": 0, "error": "适配器未注册"}

    adapter.credential = jd_cred

    # 2. 逐页拉取订单列表
    conn = await asyncpg.connect(**_DB, timeout=10)
    try:
        total_synced = 0
        page = 1
        details = []

        while True:
            orders = await _fetch_order_page(adapter, start_date, end_date, page, page_size)
            if not orders:
                break

            for order in orders:
                try:
                    await _upsert_order(conn, order)
                    total_synced += 1
                    details.append({
                        "order_id": order.get("platform_order_id", "?"),
                        "product": order.get("product_name", "")[:30],
                        "status": order.get("order_status", ""),
                    })
                except Exception as e:
                    logger.warning(f"订单同步失败 [{order.get('platform_order_id')}]: {e}")

            page += 1
            if len(orders) < page_size:
                break
            await asyncio.sleep(0.5)  # 控制频率

        logger.info(f"京东订单同步完成: {total_synced} 条")
        return {"total": total_synced, "success": total_synced, "failed": 0, "details": details[:20]}

    finally:
        await conn.close()


async def _fetch_order_page(
    adapter, start_date: str, end_date: str, page: int, page_size: int
) -> list:
    """调用京东 API 拉取一页订单"""
    try:
        result = await adapter._call_api("jingdong.pop.order.search", {
            "startDate": start_date,
            "endDate": end_date,
            "page": str(page),
            "pageSize": str(page_size),
            "optionalFields": "orderTotalPrice,orderStatus,consigneeInfo,itemInfoList",
        })

        if not result:
            return []

        data = result.get("jingdong_pop_order_search_responce", {})
        search_result = data.get("searchorderinfoResult", data.get("orderInfoList", []))
        if isinstance(search_result, dict):
            search_result = search_result.get("orderInfoList", [])

        orders = []
        for item in search_result:
            order_id = str(item.get("orderId", ""))
            if not order_id:
                continue
            # 拿详情
            detail = await adapter.get_order(order_id)
            if detail:
                orders.append(detail.model_dump())

        logger.info(f"京东订单 page={page}: 获取 {len(orders)} 条")
        return orders

    except Exception as e:
        logger.error(f"拉取京东订单页失败 [page={page}]: {e}")
        return []


async def _upsert_order(conn, order: dict):
    """UPSERT 一条订单到本地 orders 表 + 物流轨迹表"""
    # 1. UPSERT 订单主表（P0-2: 只存脱敏字段）
    await conn.execute(
        """INSERT INTO orders (
            order_id, tenant_id, user_id, platform, platform_order_id,
            product_name, product_sku, quantity, total_amount, order_status,
            recipient_name, recipient_phone, shipping_address,
            tracking_number, express_company, express_code,
            created_at, paid_at, shipped_at, delivered_at
        ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17,$18,$19,$20)
        ON CONFLICT (order_id) DO UPDATE SET
            order_status   = EXCLUDED.order_status,
            tracking_number = EXCLUDED.tracking_number,
            delivered_at   = COALESCE(EXCLUDED.delivered_at, orders.delivered_at),
            paid_at        = COALESCE(EXCLUDED.paid_at, orders.paid_at)""",
        order.get("platform_order_id", ""),
        order.get("tenant_id", "default"),
        order.get("buyer_nick", ""),
        "jd",
        order.get("platform_order_id", ""),
        order.get("product_name", ""),
        order.get("product_sku", ""),
        order.get("quantity", 1),
        order.get("total_amount", 0),
        order.get("order_status", ""),
        order.get("recipient_name_masked", ""),
        order.get("phone_encrypted", ""),
        order.get("address_masked", ""),
        order.get("tracking_number", ""),
        order.get("express_company", ""),
        order.get("express_company", ""),  # express_code 用物流公司名
        order.get("created_at"),
        order.get("paid_at"),
        order.get("shipped_at"),
        order.get("delivered_at"),
    )

    # 2. UPSERT 物流轨迹（如果有运单号）
    tracking = order.get("tracking_number", "")
    if tracking:
        await conn.execute(
            """INSERT INTO order_logistics_tracking (
                order_id, tracking_number, platform, order_status,
                departure_station, destination_station,
                actual_departure_time, scheduled_arrival_time, actual_arrival_time,
                airline_company, subscribe_supported
            ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11)
            ON CONFLICT (order_id) DO UPDATE SET
                order_status = EXCLUDED.order_status,
                actual_arrival_time = COALESCE(EXCLUDED.actual_arrival_time, order_logistics_tracking.actual_arrival_time)""",
            order.get("platform_order_id", ""),
            tracking,
            "jd",
            order.get("logistics_status", ""),
            order.get("departure_station", ""),
            order.get("destination_station", ""),
            order.get("shipped_at"),
            order.get("delivered_at"),
            order.get("delivered_at"),
            order.get("express_company", ""),
            True,
        )


# ===== API 端点 =====

from fastapi import APIRouter, Query
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1/platform/jd", tags=["京东订单同步"])


class SyncResponse(BaseModel):
    total: int = 0
    success: int = 0
    failed: int = 0
    error: str = ""
    details: list = []


@router.post("/sync/orders", response_model=SyncResponse)
async def trigger_jd_sync(
    tenant_id: str = Query("default"),
    days: int = Query(7, ge=1, le=90, description="同步最近N天的订单"),
):
    """手动触发京东订单同步"""
    start = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    end = datetime.now().strftime("%Y-%m-%d")
    result = await sync_jd_orders(tenant_id=tenant_id, start_date=start, end_date=end)
    return SyncResponse(**result)

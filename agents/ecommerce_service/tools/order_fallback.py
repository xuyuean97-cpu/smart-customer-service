"""
P1-5: 平台 API Fallback 辅助函数
"""
import re
from common.logging import get_logger
logger = get_logger("agents.tools.order_fallback")


def extract_platform_order_id(question: str) -> str:
    """从用户问题中提取可能的平台订单号"""
    m = re.search(r"\b\d{14,20}\b", question)
    return m.group() if m else ""


async def fetch_from_platform_adapter(order_id: str, tenant_id: str) -> dict:
    """从平台适配器实时拉取订单数据"""
    try:
        from agents.ecommerce_service.channels.platforms import get_adapter
        from agents.ecommerce_service.channels.platforms.credential import get_credentials

        creds = await get_credentials(tenant_id)
        for platform, cred in creds.items():
            adapter = get_adapter(platform)
            if adapter:
                adapter.credential = cred
                order = await adapter.get_order_with_cache(order_id)
                if order:
                    return order.model_dump()
    except Exception as e:
        logger.warning(f"Fallback failed: {e}")
    return {}


async def upsert_to_local_db(order_data: dict):
    """将平台订单数据 UPSERT 到本地 orders 表"""
    try:
        import asyncpg
        from config.db import get_db_config
        conn = await asyncpg.connect(**get_db_config())
        try:
            await conn.execute(
                """INSERT INTO orders (order_id, tenant_id, user_id, product_name,
                   total_amount, order_status, recipient_name, recipient_phone,
                   shipping_address, tracking_number, express_company, created_at)
                   VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12)
                   ON CONFLICT (order_id) DO UPDATE SET
                   order_status=EXCLUDED.order_status,
                   tracking_number=EXCLUDED.tracking_number""",
                order_data.get("platform_order_id", ""),
                order_data.get("tenant_id", "default"),
                order_data.get("buyer_nick", ""),
                order_data.get("product_name", ""),
                order_data.get("total_amount", 0),
                order_data.get("order_status", ""),
                order_data.get("recipient_name_masked", ""),
                order_data.get("phone_encrypted", ""),
                order_data.get("address_masked", ""),
                order_data.get("tracking_number", ""),
                order_data.get("express_company", ""),
                order_data.get("created_at"),
            )
            logger.info(f"UPSERT done: {order_data.get('platform_order_id')}")
        finally:
            await conn.close()
    except Exception as e:
        logger.warning(f"UPSERT failed: {e}")

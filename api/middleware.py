"""
API Key 验证中间件 + Token 用量拦截
"""
from fastapi import Header, HTTPException, Request
from typing import Optional
from common.logging import get_logger

logger = get_logger("api.middleware")


async def verify_api_key(
    request: Request,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
) -> str:
    """
    验证 API Key → 返回 tenant_id。
    用于 Dashboard / Admin 端点的鉴权。

    用法: 作为 FastAPI Depends 注入
        @router.get("/admin/xxx")
        async def admin_endpoint(tenant_id: str = Depends(verify_api_key)):
            ...
    """
    if not x_api_key:
        raise HTTPException(status_code=401, detail="缺少 X-API-Key 请求头")

    from auth.database import SessionLocal
    from auth.models import Tenant

    db = SessionLocal()
    try:
        tenant = db.query(Tenant).filter(
            Tenant.api_key == x_api_key,
            Tenant.is_active,
        ).first()

        if not tenant:
            logger.warning(f"无效的 API Key: {x_api_key[:8]}...")
            raise HTTPException(status_code=403, detail="无效的 API Key")

        request.state.tenant_id = tenant.id
        request.state.tenant_name = tenant.name
        return tenant.id

    finally:
        db.close()


def verify_api_key_optional(
    request: Request,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
) -> Optional[str]:
    """
    可选 API Key 验证 — 不传 Key 则返回 None（兼容 WebSocket 等不需要鉴权的端点）。
    """
    if not x_api_key:
        return None

    from auth.database import SessionLocal
    from auth.models import Tenant

    db = SessionLocal()
    try:
        tenant = db.query(Tenant).filter(
            Tenant.api_key == x_api_key,
            Tenant.is_active,
        ).first()
        if tenant:
            request.state.tenant_id = tenant.id
            return tenant.id
        return None
    finally:
        db.close()

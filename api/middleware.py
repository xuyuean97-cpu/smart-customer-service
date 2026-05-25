"""
API 鉴权中间件 — 支持 API Key 和 JWT Token 两种方式
"""
from fastapi import Header, HTTPException, Request
from typing import Optional
from common.logging import get_logger

logger = get_logger("api.middleware")


# ============================================================================
# JWT Token 鉴权（管理后台使用）
# ============================================================================

async def verify_admin_token(request: Request) -> str:
    """
    验证 JWT Token → 检查 admin/agent 角色 → 返回 tenant_id。

    管理后台 Dashboard / Tickets / Users 等端点使用此依赖。
    前端发送 Authorization: Bearer <jwt_token> 即可。
    """
    from jose import jwt, JWTError

    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="缺少 Authorization 请求头")

    token = auth_header[7:]
    try:
        from auth.config import settings
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: str | None = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Token 无效")
    except JWTError:
        raise HTTPException(status_code=401, detail="Token 无效或已过期") from None

    from auth.database import SessionLocal
    from auth.models import User

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user or not user.is_active:
            raise HTTPException(status_code=403, detail="用户不存在或已禁用")

        role = getattr(user, 'role', 'customer')
        if role not in ('admin', 'agent'):
            raise HTTPException(status_code=403, detail=f"权限不足 (当前角色: {role})")

        request.state.user_id = user.id
        request.state.tenant_id = user.tenant_id or "default"
        request.state.user_role = role
        return user.tenant_id or "default"
    finally:
        db.close()


# ============================================================================
# API Key 鉴权（外部 API / 脚本调用）
# ============================================================================

async def verify_api_key(
    request: Request,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
) -> str:
    """
    验证 API Key → 返回 tenant_id。
    用于外部 API 调用 / 脚本 / Webhook。

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

"""
第三方平台管理 API — CRUD 平台凭据配置
"""
import json
import time
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from auth.security import get_current_user
from common.logging import get_logger

logger = get_logger("api.platform_management")

router = APIRouter(prefix="/api/v1/platforms", tags=["平台管理"])


# ---------- Schemas ----------

class PlatformConfigCreate(BaseModel):
    platform: str = Field(..., description="平台标识: jd/taobao/pdd/douyin")
    app_key: str = Field(..., description="应用 Key")
    app_secret: str = Field(..., description="应用 Secret")
    shop_id: str = Field(default="", description="店铺 ID")
    shop_name: str = Field(default="", description="店铺名称")


class PlatformConfigUpdate(BaseModel):
    app_key: Optional[str] = None
    app_secret: Optional[str] = None
    shop_id: Optional[str] = None
    shop_name: Optional[str] = None


class PlatformConfigResponse(BaseModel):
    platform: str
    shop_id: str
    shop_name: str
    app_key: str
    is_active: bool
    expires_at: Optional[int] = None
    updated_at: Optional[int] = None


# ---------- Helpers ----------

SUPPORTED_PLATFORMS = {
    "jd": {"name": "京东", "icon": "jd", "fields": ["app_key", "app_secret"]},
    "taobao": {"name": "淘宝", "icon": "taobao", "fields": ["app_key", "app_secret"]},
    "pdd": {"name": "拼多多", "icon": "pdd", "fields": ["client_id", "client_secret"]},
    "douyin": {"name": "抖音", "icon": "douyin", "fields": ["app_key", "app_secret"]},
}


async def _get_tenant_config(tenant_id: str) -> dict:
    """获取租户 config JSONB"""
    import asyncpg
    from config.db import get_db_config
    conn = await asyncpg.connect(**get_db_config())
    try:
        row = await conn.fetchrow("SELECT config FROM tenants WHERE id = $1", tenant_id)
        if not row or not row["config"]:
            return {}
        return row["config"] if isinstance(row["config"], dict) else json.loads(row["config"])
    finally:
        await conn.close()


async def _save_tenant_config(tenant_id: str, config: dict):
    """保存租户 config JSONB"""
    import asyncpg
    from config.db import get_db_config
    conn = await asyncpg.connect(**get_db_config())
    try:
        await conn.execute(
            "UPDATE tenants SET config = $1 WHERE id = $2",
            json.dumps(config, ensure_ascii=False), tenant_id,
        )
    finally:
        await conn.close()


# ---------- Endpoints ----------

@router.get("")
async def list_platforms(current_user=Depends(get_current_user)):
    """获取所有已配置的平台列表"""
    tenant_id = str(current_user.tenant_id or "default")
    config = await _get_tenant_config(tenant_id)
    platforms_data = config.get("platforms", {})

    result = []
    for name, data in platforms_data.items():
        info = SUPPORTED_PLATFORMS.get(name, {})
        result.append({
            "platform": name,
            "name": info.get("name", name),
            "shop_id": data.get("shop_id", ""),
            "shop_name": data.get("shop_name", ""),
            "app_key": data.get("app_key", "")[:8] + "..." if data.get("app_key") else "",
            "is_active": True,
            "expires_at": data.get("expires_at"),
            "updated_at": data.get("updated_at"),
        })

    return {"code": 0, "message": "ok", "data": result}


@router.get("/supported")
async def list_supported_platforms():
    """获取支持的平台类型列表"""
    result = [{"id": k, "name": v["name"]} for k, v in SUPPORTED_PLATFORMS.items()]
    return {"code": 0, "message": "ok", "data": result}


@router.get("/{platform}")
async def get_platform(platform: str, current_user=Depends(get_current_user)):
    """获取单个平台配置"""
    tenant_id = str(current_user.tenant_id or "default")
    config = await _get_tenant_config(tenant_id)
    platforms_data = config.get("platforms", {})

    if platform not in platforms_data:
        raise HTTPException(404, f"平台 {platform} 未配置")

    data = platforms_data[platform]
    info = SUPPORTED_PLATFORMS.get(platform, {})
    return {
        "code": 0, "message": "ok",
        "data": {
            "platform": platform,
            "name": info.get("name", platform),
            "app_key": data.get("app_key", ""),
            "app_secret": data.get("app_secret", ""),
            "shop_id": data.get("shop_id", ""),
            "shop_name": data.get("shop_name", ""),
            "expires_at": data.get("expires_at"),
            "updated_at": data.get("updated_at"),
        }
    }


@router.post("")
async def create_platform(body: PlatformConfigCreate, current_user=Depends(get_current_user)):
    """添加新平台连接"""
    if body.platform not in SUPPORTED_PLATFORMS:
        raise HTTPException(400, f"不支持的平台: {body.platform}，支持: {list(SUPPORTED_PLATFORMS.keys())}")

    tenant_id = str(current_user.tenant_id or "default")
    config = await _get_tenant_config(tenant_id)

    if "platforms" not in config:
        config["platforms"] = {}

    if body.platform in config["platforms"]:
        raise HTTPException(409, f"平台 {body.platform} 已存在，请使用 PUT 更新")

    config["platforms"][body.platform] = {
        "app_key": body.app_key,
        "app_secret": body.app_secret,
        "shop_id": body.shop_id,
        "shop_name": body.shop_name,
        "updated_at": int(time.time()),
    }

    await _save_tenant_config(tenant_id, config)
    logger.info(f"平台已添加: tenant={tenant_id} platform={body.platform}")
    return {"code": 0, "message": "添加成功", "data": {"platform": body.platform}}


@router.put("/{platform}")
async def update_platform(platform: str, body: PlatformConfigUpdate, current_user=Depends(get_current_user)):
    """更新平台配置"""
    tenant_id = str(current_user.tenant_id or "default")
    config = await _get_tenant_config(tenant_id)
    platforms_data = config.get("platforms", {})

    if platform not in platforms_data:
        raise HTTPException(404, f"平台 {platform} 未配置")

    existing = platforms_data[platform]
    update_data = body.model_dump(exclude_none=True)
    existing.update(update_data)
    existing["updated_at"] = int(time.time())

    config["platforms"][platform] = existing
    await _save_tenant_config(tenant_id, config)
    logger.info(f"平台已更新: tenant={tenant_id} platform={platform}")
    return {"code": 0, "message": "更新成功", "data": {"platform": platform}}


@router.delete("/{platform}")
async def delete_platform(platform: str, current_user=Depends(get_current_user)):
    """删除平台连接"""
    tenant_id = str(current_user.tenant_id or "default")
    config = await _get_tenant_config(tenant_id)
    platforms_data = config.get("platforms", {})

    if platform not in platforms_data:
        raise HTTPException(404, f"平台 {platform} 未配置")

    del config["platforms"][platform]
    await _save_tenant_config(tenant_id, config)
    logger.info(f"平台已删除: tenant={tenant_id} platform={platform}")
    return {"code": 0, "message": "删除成功"}


@router.post("/{platform}/test")
async def test_platform(platform: str, current_user=Depends(get_current_user)):
    """测试平台连接"""
    tenant_id = str(current_user.tenant_id or "default")
    config = await _get_tenant_config(tenant_id)
    platforms_data = config.get("platforms", {})

    if platform not in platforms_data:
        raise HTTPException(404, f"平台 {platform} 未配置")

    data = platforms_data[platform]

    try:
        import httpx
        import hashlib

        platform_apis = {
            "jd": {"url": "https://api.jd.com/routerjson", "method": "jingdong.pop.order.search", "sign_method": "hmac-sha256"},
            "taobao": {"url": "https://eco.taobao.com/router/rest", "method": "taobao.trade.get", "sign_method": "hmac"},
            "pdd": {"url": "https://gw-api.pinduoduo.com/api/router", "method": "pdd.order.information.get", "sign_method": "md5"},
            "douyin": {"url": "https://openapi-fxg.jinritemai.com/order/searchList", "method": None, "sign_method": "hmac-sha256"},
        }

        api_info = platform_apis.get(platform)
        if not api_info:
            return {"code": 0, "message": "暂不支持该平台的连接测试", "data": {"status": "unsupported"}}

        sys_params = {
            "app_key": data.get("app_key"),
            "client_id": data.get("app_key"),  # PDD 用 client_id
            "access_token": data.get("access_token", ""),
            "timestamp": str(int(time.time())),
            "format": "json",
            "v": "2.0",
            "sign_method": api_info["sign_method"],
            "data_type": "JSON",
        }
        if api_info["method"]:
            sys_params["method" if platform != "pdd" else "type"] = api_info["method"]

        sorted_params = sorted(sys_params.items())
        secret = data.get("app_secret", "")
        sign_str = secret + "".join(f"{k}{v}" for k, v in sorted_params) + secret

        if api_info["sign_method"] == "hmac-sha256":
            sys_params["sign"] = hashlib.sha256(sign_str.encode()).hexdigest().upper()
        else:
            sys_params["sign"] = hashlib.md5(sign_str.encode()).hexdigest().upper()

        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(api_info["url"], data=sys_params)
            if resp.status_code == 200:
                return {"code": 0, "message": "连接成功", "data": {"status": "ok", "detail": f"{platform} API 可达"}}
            return {"code": 0, "message": f"API 返回 {resp.status_code}", "data": {"status": "degraded"}}

    except Exception as e:
        logger.error(f"平台连接测试失败: {platform} - {e}")
        return {"code": 0, "message": f"连接失败: {str(e)}", "data": {"status": "error"}}


# ---------- OAuth 授权 ----------

OAUTH_URLS = {
    "jd": "https://oauth.jd.com/oauth/authorize",
    "taobao": "https://oauth.taobao.com/authorize",
    "pdd": "https://mms.pinduoduo.com/open.html",
    "douyin": "https://openapi-fxg.jinritemai.com/oauth2/authorize",
}


@router.get("/{platform}/oauth/url")
async def get_oauth_url(platform: str, current_user=Depends(get_current_user)):
    """获取平台 OAuth 授权链接"""
    if platform not in OAUTH_URLS:
        raise HTTPException(400, f"不支持 {platform} 的 OAuth 授权")

    tenant_id = str(current_user.tenant_id or "default")
    config = await _get_tenant_config(tenant_id)
    platforms_data = config.get("platforms", {})

    if platform not in platforms_data:
        raise HTTPException(404, f"请先配置 {platform} 的 App Key 和 Secret")

    app_key = platforms_data[platform].get("app_key", "")
    state = f"{tenant_id}:{platform}"

    if platform == "jd":
        redirect_uri = f"{_get_base_url()}/api/v1/platforms/jd/oauth/callback"
        url = f"{OAUTH_URLS['jd']}?app_key={app_key}&state={state}&redirect_uri={redirect_uri}&response_type=code"
    elif platform == "taobao":
        redirect_uri = f"{_get_base_url()}/api/v1/platforms/taobao/oauth/callback"
        url = f"{OAUTH_URLS['taobao']}?client_id={app_key}&state={state}&redirect_uri={redirect_uri}&response_type=code&view=web"
    else:
        url = f"{OAUTH_URLS[platform]}?client_id={app_key}&state={state}"

    return {"code": 0, "message": "ok", "data": {"url": url}}


@router.get("/{platform}/oauth/callback")
async def oauth_callback(platform: str, code: str = "", state: str = ""):
    """OAuth 回调 — 用 code 换取 access_token"""
    if not code:
        raise HTTPException(400, "授权码为空")

    # 解析 state 获取 tenant_id
    parts = state.split(":")
    tenant_id = parts[0] if parts else "default"

    config = await _get_tenant_config(tenant_id)
    platforms_data = config.get("platforms", {})

    if platform not in platforms_data:
        raise HTTPException(404, f"平台 {platform} 未配置")

    app_key = platforms_data[platform].get("app_key", "")
    app_secret = platforms_data[platform].get("app_secret", "")

    try:
        import httpx

        token_data = await _exchange_code(platform, app_key, app_secret, code)
        if not token_data:
            raise HTTPException(500, "换取 Token 失败")

        # 保存 token 到配置
        platforms_data[platform].update(token_data)
        platforms_data[platform]["updated_at"] = int(time.time())
        config["platforms"] = platforms_data
        await _save_tenant_config(tenant_id, config)

        logger.info(f"OAuth 授权成功: platform={platform} tenant={tenant_id}")

        # 返回成功页面（简单 HTML）
        return {
            "code": 0,
            "message": "授权成功",
            "data": {
                "platform": platform,
                "expires_at": token_data.get("expires_at"),
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"OAuth 回调处理失败: {platform} - {e}")
        raise HTTPException(500, f"授权失败: {str(e)}") from e


async def _exchange_code(platform: str, app_key: str, app_secret: str, code: str) -> Optional[dict]:
    """用授权码换取 access_token"""
    import httpx

    if platform == "jd":
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post("https://oauth.jd.com/oauth/token", data={
                "app_key": app_key,
                "app_secret": app_secret,
                "grant_type": "authorization_code",
                "code": code,
            })
            if resp.status_code == 200:
                data = resp.json()
                return {
                    "access_token": data.get("access_token"),
                    "refresh_token": data.get("refresh_token"),
                    "expires_at": int(time.time()) + data.get("expires_in", 86400),
                }

    elif platform == "taobao":
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post("https://oauth.taobao.com/token", data={
                "client_id": app_key,
                "client_secret": app_secret,
                "grant_type": "authorization_code",
                "code": code,
            })
            if resp.status_code == 200:
                data = resp.json()
                return {
                    "access_token": data.get("access_token"),
                    "refresh_token": data.get("refresh_token"),
                    "expires_at": int(time.time()) + data.get("expires_in", 86400),
                }

    return None


def _get_base_url() -> str:
    """获取应用基础 URL"""
    import os
    return os.getenv("APP_BASE_URL", "http://localhost:8081")

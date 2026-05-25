"""
多平台统一回调端点 — 京东/淘宝/拼多多/抖音消息推送入口
"""
from fastapi import APIRouter, Request, Query, HTTPException
from fastapi.responses import JSONResponse
from common.logging import get_logger

logger = get_logger("api.platform")

router = APIRouter(prefix="/api/v1/platform", tags=["多平台接入"])


@router.post("/{platform}/callback")
async def platform_callback(platform: str, request: Request):
    """
    统一平台回调 — 京东咚咚 / 淘宝千牛 / 拼多多 / 抖音 消息推送

    流程: 验签 → 解析消息 → ChannelMessage → 转发图 → 构建回复
    """
    from agents.ecommerce_service.channels.platforms import get_adapter

    adapter = get_adapter(platform)
    if not adapter:
        raise HTTPException(404, f"不支持的平台: {platform}")

    try:
        raw = await request.json()
    except Exception:
        raw = dict(request.query_params)

    try:
        # 1. 签名验证
        if "sign" in raw or platform == "jd":
            if not await adapter.verify_signature(**raw):
                logger.warning(f"{platform} 签名验证失败")
                raise HTTPException(403, "签名验证失败")

        # 2. 解析 → ChannelMessage
        msg = await adapter.parse_message(raw)
        if not msg.query or not msg.query.strip():
            return JSONResponse(content={"code": 0, "msg": "ok"})

        logger.info(f"[{platform}] 收到消息: user={msg.metadata.get('from_user_id','?')[:10]}... query={msg.query[:50]}")

        # 3. 转发到图
        from api.wechat_callback import _forward_to_graph
        ai_response = await _forward_to_graph(msg)

        # 4. 构建回复
        reply = await adapter.build_reply(ai_response, msg)
        return JSONResponse(content=reply)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[{platform}] 回调处理失败: {e}", exc_info=True)
        return JSONResponse(content={"code": 0, "msg": "ok"})


# ---------- 授权回调 ----------

@router.get("/{platform}/oauth/callback")
async def oauth_callback(
    platform: str,
    code: str = Query(...),
    state: str = Query(""),
):
    """
    平台 OAuth 授权回调 — 用 code 换取 access_token
    """
    from agents.ecommerce_service.channels.platforms import get_adapter
    adapter = get_adapter(platform)
    if not adapter:
        raise HTTPException(404, f"不支持的平台: {platform}")

    try:
        cred = await adapter.exchange_code(code)
        from agents.ecommerce_service.channels.platforms.credential import save_credential
        await save_credential(state or "default", cred)
        logger.info(f"[{platform}] OAuth 授权成功, expires_at={cred.expires_at}")
        return {"success": True, "platform": platform, "expires_at": cred.expires_at}
    except Exception as e:
        logger.error(f"[{platform}] OAuth 失败: {e}")
        raise HTTPException(500, f"授权失败: {e}") from e

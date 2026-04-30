"""
微信公众号 / 小程序回调端点
"""
from fastapi import APIRouter, Request, Query, HTTPException
from fastapi.responses import PlainTextResponse, Response
from common.logging import get_logger

logger = get_logger("api.wechat")

router = APIRouter(prefix="/api/v1/wechat", tags=["微信接入"])

# 微信通道实例（懒加载）
_wechat_oa_channel = None
_wechat_mini_channel = None


def _get_oa_channel():
    global _wechat_oa_channel
    if _wechat_oa_channel is None:
        import os
        from agents.ecommerce_service.channels.wechat import WeChatOfficialAccountChannel
        _wechat_oa_channel = WeChatOfficialAccountChannel(
            token=os.getenv("WECHAT_TOKEN", ""),
            app_id=os.getenv("WECHAT_APP_ID", ""),
            app_secret=os.getenv("WECHAT_APP_SECRET", ""),
        )
    return _wechat_oa_channel


# ---------- 公众号回调 ----------

@router.get("/callback")
async def wechat_verify(
    signature: str = Query(""),
    timestamp: str = Query(""),
    nonce: str = Query(""),
    echostr: str = Query(""),
):
    """
    微信服务器验证（GET 请求）
    微信会发送 signature / timestamp / nonce / echostr 参数
    验证通过后原样返回 echostr
    """
    channel = _get_oa_channel()
    if await channel.verify_signature(signature, timestamp, nonce, echostr):
        logger.info("微信服务器验证通过")
        return PlainTextResponse(content=echostr)
    else:
        logger.warning("微信服务器验证失败")
        raise HTTPException(status_code=403, detail="签名验证失败")


@router.post("/callback")
async def wechat_message(request: Request):
    """
    接收微信消息（POST 请求）
    微信发送 XML 格式的用户消息到此端点
    """
    try:
        raw_body = await request.body()
        channel = _get_oa_channel()

        # 1. 解析微信消息 → 统一格式
        msg = await channel.parse_message(raw_body)

        if not msg.query or msg.query.strip() == "":
            return Response(content="success", media_type="text/plain")

        logger.info(f"微信消息: openid={msg.metadata.get('openid','?')[:8]}... query={msg.query[:50]}")

        # 2. 转发到电商主图处理（复用 WebSocket chat 的核心逻辑）
        response_text = await _forward_to_graph(msg)

        # 3. 构建微信回复
        reply_xml = await channel.build_reply(response_text, msg)
        return Response(content=reply_xml, media_type="application/xml")

    except Exception as e:
        logger.error(f"微信消息处理失败: {e}", exc_info=True)
        # 微信要求 5 秒内回复，出错也要返回 success 避免重试
        return Response(content="success", media_type="text/plain")


# ---------- 小程序回调 ----------

@router.post("/miniprogram/callback")
async def wechat_mini_message(request: Request):
    """接收小程序客服消息"""
    try:
        from agents.ecommerce_service.channels.wechat import WeChatMiniProgramChannel

        raw_json = await request.json()
        channel = WeChatMiniProgramChannel(
            app_id=request.headers.get("X-WeChat-AppId", ""),
            app_secret="",
        )

        msg = await channel.parse_message(raw_json)

        if not msg.query or msg.query.strip() == "":
            return {"errcode": 0, "errmsg": "ok"}

        logger.info(f"小程序消息: openid={msg.metadata.get('openid','?')[:8]}... query={msg.query[:50]}")

        response_text = await _forward_to_graph(msg)
        reply_json = await channel.build_reply(response_text, msg)
        return reply_json

    except Exception as e:
        logger.error(f"小程序消息处理失败: {e}", exc_info=True)
        return {"errcode": 0, "errmsg": "ok"}


# ---------- 消息转发 ----------

async def _forward_to_graph(msg) -> str:
    """
    将统一消息转发到电商主图处理，返回 AI 回复文本。
    复用 LangGraph ainvoke 流程。
    """
    try:
        from agents.ecommerce_service.graph_compile import graph_manager

        config = {
            "configurable": {
                "thread_id": f"wechat-{msg.user_id}",
                "user_id": msg.user_id,
                "tenant_id": msg.tenant_id,
                "user_query": msg.query,
                "Is_translate": msg.is_translate,
                "Is_emotion": msg.is_emotion,
            }
        }

        graph_inputs = {
            "question": msg.query,
            "user_id": msg.user_id,
            "tenant_id": msg.tenant_id,
            "metadata": msg.metadata,
        }

        async with graph_manager.get_compiled_graph("ecommerce_service_graph") as graph:
            result = await graph.ainvoke(graph_inputs, config)

        # 从结果中提取 AI 回复
        messages = result.get("messages", [])
        for m in reversed(messages):
            content = getattr(m, "content", "")
            if content and getattr(m, "type", "") != "tool":
                return str(content)[:500]  # 微信消息限制

        return "抱歉，我暂时无法处理您的请求。您可以输入「转人工」联系客服。"
    except Exception as e:
        logger.error(f"消息转发到图失败: {e}", exc_info=True)
        return "系统繁忙，请稍后再试。如需帮助，请拨打电话 400-123-4567。"

"""
京东开放平台适配器 — 咚咚消息 + 订单/物流查询
"""
import hashlib
import time
from typing import Optional
import httpx

from . import EcommercePlatformAdapter, register_adapter
from .. import ChannelMessage
from models.platform_order import UnifiedOrder, UnifiedLogistics, PlatformCredential
from common.logging import get_logger

logger = get_logger("channels.platforms.jd")

JD_API_BASE = "https://api.jd.com/routerjson"
JD_OAUTH_URL = "https://oauth.jd.com/oauth/authorize"


class JdAdapter(EcommercePlatformAdapter):
    platform = "jd"

    def __init__(self, credential: Optional[PlatformCredential] = None):
        super().__init__(credential)

    # ===== 签名验证 =====

    async def verify_signature(self, **kwargs) -> bool:
        """京东回调 MD5 签名验证"""
        sign = kwargs.get("sign", "")
        params = {k: v for k, v in kwargs.items() if k != "sign"}
        sorted_params = sorted(params.items())
        raw = self.credential.app_secret + "".join(f"{k}{v}" for k, v in sorted_params) + self.credential.app_secret
        expected = hashlib.md5(raw.encode()).hexdigest().upper()
        return sign.upper() == expected

    # ===== 消息解析 =====

    async def parse_message(self, raw_data: dict) -> ChannelMessage:
        """咚咚消息 JSON → ChannelMessage"""
        msg_type = raw_data.get("type", "text")
        from_user = raw_data.get("fromId", raw_data.get("from_id", "unknown"))
        content = raw_data.get("content", "")

        # 提取消费者脱敏昵称（京东通常在消息中带 buyerNick / userNick）
        buyer_nick = raw_data.get("buyerNick", raw_data.get("fromNick", raw_data.get("userNick", "")))

        if msg_type == "image":
            content = "[图片消息]"

        return ChannelMessage(
            query=content,
            user_id=f"jd_{from_user}",
            tenant_id="default",
            channel="jd",
            metadata={
                "platform": "jd",
                "msg_type": msg_type,
                "from_user_id": from_user,
                "consumer_name": buyer_nick or f"京东用户{from_user[-4:]}",  # 管理后台显示用
                "raw": raw_data,
            },
        )

    async def build_reply(self, response_text: str, original_msg: ChannelMessage) -> dict:
        """构建咚咚回复格式"""
        return {
            "code": 0,
            "msg": "success",
            "data": {
                "toId": original_msg.metadata.get("from_user_id", ""),
                "content": response_text,
                "type": "text",
            },
        }

    # ===== 订单查询 =====

    async def get_order(self, order_id: str) -> Optional[UnifiedOrder]:
        """调用京东 API 查询单个订单"""
        result = await self._call_api("jingdong.pop.order.get", {"orderId": order_id})
        if not result:
            return None
        try:
            data = result.get("jingdong_pop_order_get_responce", {}).get("orderDetail", {})
            return UnifiedOrder(
                platform="jd",
                platform_order_id=str(data.get("orderId", order_id)),
                product_name=data.get("itemInfoList", [{}])[0].get("productName", ""),
                total_amount=float(data.get("orderTotalPrice", 0)),
                order_status=self._map_status(data.get("orderState", "")),
                buyer_nick=data.get("pin", ""),
                recipient_name_masked=data.get("consigneeInfo", {}).get("fullname", ""),
                phone_encrypted=data.get("consigneeInfo", {}).get("telephone", ""),
                address_masked=data.get("consigneeInfo", {}).get("fullAddress", ""),
                created_at=data.get("orderStartTime"),
                paid_at=data.get("orderPaymentTime"),
            )
        except Exception as e:
            logger.warning(f"解析京东订单失败: {e}")
            return None

    async def get_logistics(self, tracking_no: str) -> Optional[UnifiedLogistics]:
        """查询京东物流轨迹"""
        result = await self._call_api("jingdong.etms.trace.get", {"waybillCode": tracking_no})
        if not result:
            return None
        try:
            data = result.get("jingdong_etms_trace_get_responce", {}).get("traceDetail", {})
            traces = data.get("traceList", [])
            return UnifiedLogistics(
                tracking_number=tracking_no,
                express_company="京东物流",
                status=self._map_logistics_status(traces[0].get("operateDesc", "") if traces else "无"),
                details=[
                    {"time": t.get("operateTime", ""), "location": "", "description": t.get("operateDesc", "")}
                    for t in traces
                ],
            )
        except Exception as e:
            logger.warning(f"解析京东物流失败: {e}")
            return None

    # ===== 消息发送 =====

    async def send_message(self, user_id: str, text: str) -> bool:
        """调用咚咚发送消息"""
        result = await self._call_api("jingdong.im.pop.sessions.send", {
            "toId": user_id,
            "content": text,
            "type": "text",
        })
        return result is not None

    # ===== Token 管理 =====

    async def refresh_token(self) -> PlatformCredential:
        result = await self._call_api("jingdong.oauth.refreshToken", {
            "refresh_token": self.credential.refresh_token,
        })
        if result:
            data = result.get("jingdong_oauth_refreshToken_responce", {})
            self.credential.access_token = data.get("access_token", self.credential.access_token)
            self.credential.refresh_token = data.get("refresh_token", self.credential.refresh_token)
            self.credential.expires_at = int(time.time()) + data.get("expires_in", 86400)
        return self.credential

    # ===== 内部方法 =====

    async def _call_api(self, method: str, params: dict) -> Optional[dict]:
        """通用京东 API 调用（HMAC-SHA256 签名）"""
        if not self.credential:
            logger.warning("京东适配器未配置凭据")
            return None
        try:
            sys_params = {
                "method": method,
                "app_key": self.credential.app_key,
                "access_token": self.credential.access_token,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "format": "json",
                "v": "2.0",
                "sign_method": "hmac-sha256",
            }
            all_params = {**sys_params, **{k: str(v) for k, v in params.items()}}
            sorted_params = sorted(all_params.items())
            sign_str = self.credential.app_secret + "".join(f"{k}{v}" for k, v in sorted_params) + self.credential.app_secret
            all_params["sign"] = hashlib.sha256(sign_str.encode()).hexdigest().upper()

            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(JD_API_BASE, data=all_params)
                if resp.status_code == 200:
                    return resp.json()
                logger.error(f"京东 API 返回 {resp.status_code}: {resp.text[:200]}")
                return None
        except Exception as e:
            logger.error(f"京东 API 调用失败 [{method}]: {e}")
            return None

    def _map_status(self, jd_status: str) -> str:
        mapping = {
            "WAIT_SELLER_STOCK_OUT": "paid",
            "WAIT_GOODS_RECEIVE_CONFIRM": "shipped",
            "FINISHED_L": "delivered",
            "TRADE_CANCELED": "cancelled",
        }
        return mapping.get(jd_status, "unknown")

    def _map_logistics_status(self, desc: str) -> str:
        if "签收" in desc: return "已签收"
        if "派送" in desc: return "派送中"
        if "运输" in desc: return "运输中"
        if "揽收" in desc: return "已揽收"
        return "运输中"


# 自动注册
register_adapter("jd", JdAdapter())

"""
抖音开放平台适配器 — 私信消息 + 订单/物流查询
"""
import hashlib
import time
import json
from typing import Optional
import httpx

from . import EcommercePlatformAdapter, register_adapter
from .. import ChannelMessage
from models.platform_order import UnifiedOrder, UnifiedLogistics, PlatformCredential
from common.logging import get_logger

logger = get_logger("channels.platforms.douyin")

DOUYIN_API_BASE = "https://openapi-fxg.jinritemai.com"


class DouyinAdapter(EcommercePlatformAdapter):
    platform = "douyin"

    def __init__(self, credential: Optional[PlatformCredential] = None):
        super().__init__(credential)

    # ===== 签名验证 =====

    async def verify_signature(self, **kwargs) -> bool:
        """抖音回调签名验证（SHA256）"""
        sign = kwargs.get("sign", "")
        params = {k: v for k, v in kwargs.items() if k not in ("sign",)}
        sorted_params = sorted(params.items())
        raw = self.credential.app_secret + "".join(f"{k}{v}" for k, v in sorted_params) + self.credential.app_secret
        expected = hashlib.sha256(raw.encode()).hexdigest()
        return sign == expected

    # ===== 消息解析 =====

    async def parse_message(self, raw_data: dict) -> ChannelMessage:
        """抖音私信 JSON → ChannelMessage"""
        msg_type = raw_data.get("msg_type", "text")
        from_user = raw_data.get("open_id", raw_data.get("user_id", "unknown"))
        content = raw_data.get("content", raw_data.get("text", ""))

        if msg_type == "image":
            content = raw_data.get("image_url", "[图片消息]")

        return ChannelMessage(
            query=content,
            user_id=f"douyin_{from_user}",
            tenant_id="default",
            channel="douyin",
            metadata={
                "platform": "douyin",
                "msg_type": msg_type,
                "from_user_id": from_user,
                "consumer_name": raw_data.get("nickname", f"抖音用户"),
                "raw": raw_data,
            },
        )

    async def build_reply(self, response_text: str, original_msg: ChannelMessage) -> dict:
        """构建抖音回复格式"""
        return {
            "err_no": 0,
            "err_msg": "success",
            "data": {
                "open_id": original_msg.metadata.get("from_user_id", ""),
                "msg_type": "text",
                "content": response_text,
            },
        }

    # ===== 订单查询 =====

    async def get_order(self, order_id: str) -> Optional[UnifiedOrder]:
        """调用抖音 API 查询单个订单"""
        result = await self._call_api("/order/searchList", {
            "order_id": order_id,
        })
        if not result:
            return None
        try:
            data = result.get("data", {}).get("order_list", [{}])[0]
            return UnifiedOrder(
                platform="douyin",
                platform_order_id=str(data.get("order_id", order_id)),
                product_name=data.get("product_name", ""),
                total_amount=float(data.get("pay_amount", 0)) / 100,
                order_status=self._map_status(data.get("order_status", 0)),
                buyer_nick=data.get("buyer_nick", ""),
                recipient_name_masked=data.get("post_receiver", ""),
                phone_encrypted=data.get("post_tel", ""),
                address_masked=data.get("post_addr", ""),
                created_at=str(data.get("create_time", "")),
                paid_at=str(data.get("pay_time", "")),
            )
        except Exception as e:
            logger.warning(f"解析抖音订单失败: {e}")
            return None

    async def get_logistics(self, tracking_no: str) -> Optional[UnifiedLogistics]:
        """查询抖音物流轨迹"""
        result = await self._call_api("/logistics/trackQuery", {
            "order_id": tracking_no,
        })
        if not result:
            return None
        try:
            data = result.get("data", {})
            traces = data.get("track_list", [])
            return UnifiedLogistics(
                tracking_number=tracking_no,
                express_company=data.get("company_name", "未知快递"),
                status=self._map_logistics_status(data.get("status", 0)),
                details=[
                    {"time": t.get("time", ""), "location": t.get("desc", ""), "description": t.get("desc", "")}
                    for t in traces
                ],
            )
        except Exception as e:
            logger.warning(f"解析抖音物流失败: {e}")
            return None

    # ===== 消息发送 =====

    async def send_message(self, user_id: str, text: str) -> bool:
        """调用抖音发送私信"""
        result = await self._call_api("/im/sendMsg", {
            "open_id": user_id,
            "msg_type": "text",
            "content": text,
        })
        return result is not None

    # ===== Token 管理 =====

    async def refresh_token(self) -> PlatformCredential:
        result = await self._call_api("/token/refresh", {
            "refresh_token": self.credential.refresh_token,
        })
        if result:
            data = result.get("data", {})
            self.credential.access_token = data.get("access_token", self.credential.access_token)
            self.credential.refresh_token = data.get("refresh_token", self.credential.refresh_token)
            self.credential.expires_at = int(time.time()) + data.get("expires_in", 86400)
        return self.credential

    # ===== 内部方法 =====

    async def _call_api(self, path: str, params: dict) -> Optional[dict]:
        """通用抖音 API 调用（SHA256 签名）"""
        if not self.credential:
            logger.warning("抖音适配器未配置凭据")
            return None
        try:
            sys_params = {
                "app_key": self.credential.app_key,
                "access_token": self.credential.access_token,
                "timestamp": str(int(time.time())),
                "v": "2",
                "sign_method": "hmac-sha256",
            }
            all_params = {**sys_params, **{k: str(v) for k, v in params.items()}}
            sorted_params = sorted(all_params.items())
            sign_str = self.credential.app_secret + "".join(f"{k}{v}" for k, v in sorted_params) + self.credential.app_secret
            all_params["sign"] = hashlib.sha256(sign_str.encode()).hexdigest()

            url = f"{DOUYIN_API_BASE}{path}"
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(url, json=all_params)
                if resp.status_code == 200:
                    return resp.json()
                logger.error(f"抖音 API 返回 {resp.status_code}: {resp.text[:200]}")
                return None
        except Exception as e:
            logger.error(f"抖音 API 调用失败 [{path}]: {e}")
            return None

    def _map_status(self, status: int) -> str:
        mapping = {
            1: "pending",
            2: "paid",
            3: "shipped",
            4: "delivered",
            5: "cancelled",
        }
        return mapping.get(status, "unknown")

    def _map_logistics_status(self, status: int) -> str:
        mapping = {
            0: "未发货",
            1: "已发货",
            2: "已签收",
            3: "已取消",
        }
        return mapping.get(status, "运输中")


# 自动注册
register_adapter("douyin", DouyinAdapter())

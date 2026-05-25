"""
拼多多开放平台适配器 — 消息推送 + 订单/物流查询
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

logger = get_logger("channels.platforms.pdd")

PDD_API_BASE = "https://gw-api.pinduoduo.com/api/router"


class PddAdapter(EcommercePlatformAdapter):
    platform = "pdd"

    def __init__(self, credential: Optional[PlatformCredential] = None):
        super().__init__(credential)

    # ===== 签名验证 =====

    async def verify_signature(self, **kwargs) -> bool:
        """拼多多回调 MD5 签名验证"""
        sign = kwargs.get("sign", "")
        params = {k: v for k, v in kwargs.items() if k != "sign"}
        sorted_params = sorted(params.items())
        raw = self.credential.app_secret + "".join(f"{k}{v}" for k, v in sorted_params) + self.credential.app_secret
        expected = hashlib.md5(raw.encode()).hexdigest().upper()
        return sign.upper() == expected

    # ===== 消息解析 =====

    async def parse_message(self, raw_data: dict) -> ChannelMessage:
        """拼多多消息 JSON → ChannelMessage"""
        msg_type = raw_data.get("msg_type", "text")
        from_user = raw_data.get("user_id", raw_data.get("buyer_id", "unknown"))
        content = raw_data.get("content", raw_data.get("text", ""))

        if msg_type == "image":
            content = raw_data.get("pic_url", "[图片消息]")

        return ChannelMessage(
            query=content,
            user_id=f"pdd_{from_user}",
            tenant_id="default",
            channel="pdd",
            metadata={
                "platform": "pdd",
                "msg_type": msg_type,
                "from_user_id": from_user,
                "consumer_name": raw_data.get("buyer_nick", f"拼多多用户"),
                "raw": raw_data,
            },
        )

    async def build_reply(self, response_text: str, original_msg: ChannelMessage) -> dict:
        """构建拼多多回复格式"""
        return {
            "success": True,
            "data": {
                "uid": original_msg.metadata.get("from_user_id", ""),
                "text": response_text,
                "msg_type": "text",
            },
        }

    # ===== 订单查询 =====

    async def get_order(self, order_id: str) -> Optional[UnifiedOrder]:
        """调用拼多多 API 查询单个订单"""
        result = await self._call_api("pdd.order.information.get", {
            "order_sn": order_id,
        })
        if not result:
            return None
        try:
            data = result.get("order_information_get_response", {}).get("order_info", {})
            return UnifiedOrder(
                platform="pdd",
                platform_order_id=str(data.get("order_sn", order_id)),
                product_name=data.get("goods_name", ""),
                total_amount=float(data.get("pay_amount", 0)) / 100,  # 分转元
                order_status=self._map_status(data.get("order_status", 0)),
                buyer_nick=data.get("buyer_nick", ""),
                recipient_name_masked=data.get("receiver_name", ""),
                phone_encrypted=data.get("receiver_phone", ""),
                address_masked=data.get("receiver_address", ""),
                created_at=str(data.get("created_at", "")),
                paid_at=str(data.get("pay_at", "")),
            )
        except Exception as e:
            logger.warning(f"解析拼多多订单失败: {e}")
            return None

    async def get_logistics(self, tracking_no: str) -> Optional[UnifiedLogistics]:
        """查询拼多多物流轨迹"""
        result = await self._call_api("pdd.logistics.online.send.query", {
            "order_sn": tracking_no,
        })
        if not result:
            return None
        try:
            data = result.get("logistics_online_send_query_response", {})
            traces = data.get("trace_list", [])
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
            logger.warning(f"解析拼多多物流失败: {e}")
            return None

    # ===== 消息发送 =====

    async def send_message(self, user_id: str, text: str) -> bool:
        """调用拼多多发送消息"""
        result = await self._call_api("pdd.mall.chat.send.message", {
            "uid": user_id,
            "text": text,
            "msg_type": "text",
        })
        return result is not None

    # ===== Token 管理 =====

    async def refresh_token(self) -> PlatformCredential:
        result = await self._call_api("pdd.pop.auth.token.refresh", {
            "refresh_token": self.credential.refresh_token,
        })
        if result:
            data = result.get("pop_auth_token_refresh_response", {})
            self.credential.access_token = data.get("access_token", self.credential.access_token)
            self.credential.refresh_token = data.get("refresh_token", self.credential.refresh_token)
            self.credential.expires_at = int(time.time()) + data.get("expires_in", 86400)
        return self.credential

    # ===== 内部方法 =====

    async def _call_api(self, api_type: str, params: dict) -> Optional[dict]:
        """通用拼多多 API 调用（MD5 签名）"""
        if not self.credential:
            logger.warning("拼多多适配器未配置凭据")
            return None
        try:
            sys_params = {
                "type": api_type,
                "client_id": self.credential.app_key,
                "access_token": self.credential.access_token,
                "timestamp": str(int(time.time())),
                "data_type": "JSON",
            }
            all_params = {**sys_params, **{k: str(v) for k, v in params.items()}}
            sorted_params = sorted(all_params.items())
            sign_str = self.credential.app_secret + "".join(f"{k}{v}" for k, v in sorted_params) + self.credential.app_secret
            all_params["sign"] = hashlib.md5(sign_str.encode()).hexdigest().upper()

            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(PDD_API_BASE, json=all_params)
                if resp.status_code == 200:
                    return resp.json()
                logger.error(f"拼多多 API 返回 {resp.status_code}: {resp.text[:200]}")
                return None
        except Exception as e:
            logger.error(f"拼多多 API 调用失败 [{api_type}]: {e}")
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
register_adapter("pdd", PddAdapter())

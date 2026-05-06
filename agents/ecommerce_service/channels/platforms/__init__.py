"""
电商平台适配器抽象基类 — 所有平台（京东/淘宝/拼多多/抖音）统一接入接口

内置工程防护:
  - P1-4: TTLCache + asyncio.Lock 并发穿透防护
  - P1-7: start_listener() 兼容 Webhook + 长连接
"""
import asyncio
from abc import ABC, abstractmethod
from typing import Dict, Optional
from cachetools import TTLCache

from .. import ChannelMessage
from models.platform_order import (
    UnifiedOrder, UnifiedLogistics, PlatformCredential  # PlatformMessage reserved for Phase 2
)
from common.logging import get_logger

logger = get_logger("agents.channels.platforms")


# ---------- 适配器注册表 ----------

_registry: Dict[str, "EcommercePlatformAdapter"] = {}


def get_adapter(platform: str) -> Optional["EcommercePlatformAdapter"]:
    return _registry.get(platform)


def register_adapter(platform: str, adapter: "EcommercePlatformAdapter"):
    _registry[platform] = adapter
    logger.info(f"平台适配器已注册: {platform}")


# ---------- 抽象基类 ----------

class EcommercePlatformAdapter(ABC):
    """
    电商平台适配器基类

    子类必须实现:
      - verify_signature()
      - parse_message()
      - build_reply()
      - get_order()
      - get_logistics()
      - send_message()
      - refresh_token()
    可选覆盖:
      - start_listener()  ← 淘宝 TMC 长连接
    """

    platform: str = "unknown"

    def __init__(self, credential: Optional[PlatformCredential] = None):
        self.credential = credential
        # P1-4: 防刷缓存 + 并发穿透防护
        self.logistics_cache = TTLCache(maxsize=1000, ttl=300)  # 5 min
        self.order_cache     = TTLCache(maxsize=1000, ttl=120)  # 2 min
        self._locks: Dict[str, asyncio.Lock] = {}

    # ===== 抽象方法（子类必须实现） =====

    @abstractmethod
    async def verify_signature(self, **kwargs) -> bool: ...

    @abstractmethod
    async def parse_message(self, raw_data) -> ChannelMessage: ...

    @abstractmethod
    async def build_reply(self, response_text: str, original_msg: ChannelMessage) -> dict: ...

    @abstractmethod
    async def get_order(self, order_id: str) -> Optional[UnifiedOrder]: ...

    @abstractmethod
    async def get_logistics(self, tracking_no: str) -> Optional[UnifiedLogistics]: ...

    @abstractmethod
    async def send_message(self, user_id: str, text: str) -> bool: ...

    @abstractmethod
    async def refresh_token(self) -> PlatformCredential: ...

    # ===== 带缓存的对外接口 =====

    async def get_logistics_with_cache(self, tracking_no: str) -> Optional[UnifiedLogistics]:
        """P1-4: 5分钟缓存 + DCL 并发穿透防护"""
        if not tracking_no:
            return None
        if tracking_no in self.logistics_cache:
            return self.logistics_cache[tracking_no]

        lock = self._locks.setdefault(tracking_no, asyncio.Lock())
        async with lock:
            if tracking_no in self.logistics_cache:
                return self.logistics_cache[tracking_no]
            data = await self.get_logistics(tracking_no)
            if data:
                self.logistics_cache[tracking_no] = data

        self._locks.pop(tracking_no, None)
        return data

    async def get_order_with_cache(self, order_id: str) -> Optional[UnifiedOrder]:
        """P1-4: 2分钟缓存 + DCL"""
        if not order_id:
            return None
        if order_id in self.order_cache:
            return self.order_cache[order_id]

        lock = self._locks.setdefault(f"order_{order_id}", asyncio.Lock())
        async with lock:
            if order_id in self.order_cache:
                return self.order_cache[order_id]
            data = await self.get_order(order_id)
            if data:
                self.order_cache[order_id] = data

        self._locks.pop(f"order_{order_id}", None)
        return data

    # ===== 可选覆盖 =====

    @abstractmethod
    async def start_listener(self) -> None:
        """
        P1-7: 启动消息监听器（用于长连接平台如淘宝 TMC）
        默认不实现（京东/微信使用 Webhook 回调）
        """
        pass

    async def _dispatch_to_graph(self, msg: ChannelMessage) -> None:
        """内部转发消息到 AI 图处理"""
        from api.wechat_callback import _forward_to_graph
        await _forward_to_graph(msg)
__all__ = ['models.platform_order.PlatformMessage']

"""
消息通道抽象层 — 支持多平台接入（微信 / 抖音 / WebSocket / API）
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, Dict, Any


@dataclass
class ChannelMessage:
    """统一消息格式 — 所有平台消息归一化为此结构"""
    query: str                                    # 用户消息文本
    user_id: str                                  # 用户唯一标识（OpenID / 手机号 / UUID）
    tenant_id: str = "default"                    # 租户 ID
    channel: str = "unknown"                      # 来源渠道: wechat_oa / wechat_mini / web / api
    image_url: Optional[str] = None               # 图片 URL（如果有）
    metadata: Dict[str, Any] = field(default_factory=dict)  # 渠道特有元数据
    is_translate: bool = False
    is_emotion: bool = False


class MessageChannel(ABC):
    """消息通道基类 — 所有平台接入必须实现此接口"""

    @abstractmethod
    async def parse_message(self, raw_data: Any) -> ChannelMessage:
        """解析原始消息 → 统一 ChannelMessage"""
        ...

    @abstractmethod
    async def verify_signature(self, **kwargs) -> bool:
        """验证消息签名（安全校验）"""
        ...

    @abstractmethod
    async def build_reply(self, response_text: str, original_msg: ChannelMessage) -> Any:
        """构建平台特定的回复格式"""
        ...


# 导入所有平台适配器（触发自动注册）
from .platforms import jd, taobao, pdd, douyin  # noqa: F401, E402

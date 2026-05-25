"""
多平台订单统一模型 + 平台授权凭据
"""
from pydantic import BaseModel, Field
from typing import Optional


class UnifiedOrder(BaseModel):
    """所有平台订单归一化结构"""
    platform: str = Field(..., description="平台: jd/taobao/pdd/douyin")
    platform_order_id: str = Field(..., description="平台订单号")
    product_name: str = Field("", description="商品名称")
    product_sku: Optional[str] = None
    product_image: Optional[str] = None
    quantity: int = 1
    total_amount: float = 0.0
    order_status: str = Field("", description="内部统一状态: pending/paid/shipped/delivered/cancelled/returning")
    buyer_nick: str = Field("", description="买家昵称（脱敏后）")

    # ---- 脱敏字段（绝对不存明文） ----
    recipient_name_masked: str = Field("", description="收件人: 张**")
    phone_encrypted: str = Field("", description="手机号: 138****0001")
    address_masked: str = Field("", description="地址: 上海市浦东新区***")

    # ---- 物流 ----
    tracking_number: Optional[str] = None
    express_company: Optional[str] = None
    logistics_status: Optional[str] = None

    # ---- 售后 ----
    refund_status: Optional[str] = None
    refund_amount: Optional[float] = None

    created_at: Optional[str] = None
    paid_at: Optional[str] = None
    shipped_at: Optional[str] = None
    delivered_at: Optional[str] = None


class UnifiedLogistics(BaseModel):
    """统一物流轨迹"""
    tracking_number: str
    express_company: str
    status: str                 # 运输中/派送中/已签收/异常
    details: list = Field(default_factory=list)  # [{time, location, description}]
    estimated_delivery: Optional[str] = None


class PlatformCredential(BaseModel):
    """平台授权凭据"""
    platform: str
    app_key: str
    app_secret: str
    access_token: str
    refresh_token: str = ""
    shop_id: str = ""
    shop_name: str = ""
    expires_at: Optional[int] = None   # unix timestamp
    created_at: Optional[str] = None


class PlatformMessage(BaseModel):
    """平台回调消息归一化"""
    platform: str
    msg_type: str = "text"              # text / image / order_notify
    from_user_id: str                   # 平台用户 ID
    from_user_nick: str = ""
    content: str
    image_url: Optional[str] = None
    raw_data: dict = Field(default_factory=dict)

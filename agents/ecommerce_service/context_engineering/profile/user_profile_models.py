"""
统一用户画像模型
整合原有的user_profile_model.py和user_profile_model_extended.py
提供清晰的三层画像架构
"""

from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Dict
from datetime import datetime
from enum import Enum

# ============================== 基础枚举定义 ==============================
class CustomerType(str, Enum):
    """顾客类型枚举"""
    NEW_BUYER = "新客"
    REGULAR = "老客"
    VIP = "VIP会员"
    BARGAIN_HUNTER = "羊毛党/价格敏感型"
    WHOLESALE = "企业/大宗采购"
    GIFT_BUYER = "送礼人群"
    POTENTIAL = "潜在/浏览未下单客户"

class UserRole(str, Enum):
    """用户角色枚举"""
    BUYER = "买家本人"
    RECIPIENT = "收件人"
    AGENT = "代购/分销商"
    STORE_STAFF = "店小二/人工客服"

class SpendingPower(str, Enum):
    """消费能力枚举"""
    HIGH = "高价值客户/高客单价"
    MEDIUM = "中等消费"
    PRICE_SENSITIVE = "低客单价/价格敏感"
    UNKNOWN = "未知"

class QueryStyle(str, Enum):
    """提问风格枚举"""
    CONCISE = "简洁型"
    DETAILED = "详细型"
    URGENT = "紧急型"
    CASUAL = "随意型"
    PROFESSIONAL = "专业型(懂行)"

class Sentiment(str, Enum):
    """情感倾向枚举"""
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"
    ANXIOUS = "anxious"
    ANGRY = "angry"      # 电商场景常有愤怒情绪(如货不对板、物流慢)
    SATISFIED = "satisfied"

class ResolutionStatus(str, Enum):
    """问题解决状态枚举"""
    RESOLVED = "已解决"
    PARTIALLY_RESOLVED = "部分解决"
    NOT_RESOLVED = "未解决"
    NEED_FOLLOW_UP = "需要跟进/升级人工"

# ============================== 基础组件模型 ==============================
class SessionMetrics(BaseModel):
    """会话基础指标"""
    start_time: datetime = Field(..., description="会话开始时间")
    end_time: datetime = Field(..., description="会话结束时间")
    day: str = Field(..., description="会话日期(YYYY-MM-DD)")
    duration_seconds: int = Field(..., description="会话持续时间（秒）")
    turn_count: int = Field(0, description="会话轮次数")
    user_messages_count: int = Field(0, description="用户消息数量")
    system_responses_count: int = Field(0, description="系统回复数量")
    avg_response_time: float = Field(0.0, description="平均响应时间（秒）")

class TechnicalContext(BaseModel):
    """技术环境信息"""
    source: Optional[str] = Field(None, description="咨询渠道 (淘宝、京东、微信小程序、APP、网页)")
    device: Optional[str] = Field(None, description="设备类型 (手机、电脑、平板)")
    ip: Optional[str] = Field(None, description="IP地址")
    country: Optional[str] = Field(None, description="国家")
    province: Optional[str] = Field(None, description="省份")
    city: Optional[str] = Field(None, description="城市")
    district: Optional[str] = Field(None, description="区县")
    latitude: Optional[float] = Field(None, description="经度")
    longitude: Optional[float] = Field(None, description="纬度")
    network_type: Optional[str] = Field(None, description="网络类型（wifi、4g、5g等）")

class ContentAnalysis(BaseModel):
    """对话内容分析"""
    language: str = Field(default="中文", description="主要使用语言")
    style: QueryStyle = Field(default=QueryStyle.CASUAL, description=f"用户提问风格：{list(QueryStyle._value2member_map_.keys())}")
    sentiment: Sentiment = Field(default=Sentiment.NEUTRAL, description=f"整体情感倾向：{list(Sentiment._value2member_map_.keys())}")
    anxiety_score: float = Field(default=0.0, ge=0.0, le=1.0, description="焦虑/急躁指数(0-1)")
    urgency_score: float = Field(default=0.0, ge=0.0, le=1.0, description="紧急程度(0-1)")
    satisfaction_score: float = Field(default=0.0, ge=0.0, le=1.0, description="满意度(0-1)：0.1=非常不满意，0.9=非常满意")
    keywords: List[str] = Field(default_factory=list, description="对话中提到的关键词(商品名、物流公司、优惠券等)")
    topics: List[str] = Field(default_factory=list, description="讨论的主要话题：如 商品咨询、催发货、退换货、发票问题、活动规则等")
    resolution_status: str = Field(default=ResolutionStatus.NOT_RESOLVED, description=f"问题解决状态：{list(ResolutionStatus._value2member_map_.keys())}")

class OrderInfo(BaseModel):
    """订单信息提取"""
    order_id: Optional[str] = Field(None, description="标准订单号格式。如果用户提到但格式不标准，请尝试标准化")
    product_mentioned: Optional[str] = Field(None, description="订单关联的具体商品名称或SKU")

    @field_validator('order_id')
    def validate_order_id(cls, v):
        """简单验证订单号：通常全数字或包含特定字母前缀"""
        if v and any(c.isdigit() for c in v):
            return v
        return None
class ProductInfo(BaseModel):
    """商品信息提取"""
    product_name: str = Field(..., description="用户咨询的商品名称、类别或特征")
    sku_id: Optional[str] = Field(None, description="商品SKU编码（如能识别）")
    is_purchased: bool = Field(default=False, description="用户是否已经购买了该商品")

class ServiceIntent(BaseModel):
    """电商服务/售后意图"""
    intent_type: str = Field(description="用户意图：售前咨询、催发货、查物流、退款、换货、开票、投诉、修改地址等")
    status: str = Field(default="未处理", description="当前意图处理状态：已完成、处理中、需人工介入、已撤销")

    @field_validator('intent_type')
    def validate_intent_type(cls, v):
        """验证使用意图范围"""
        valid_intents = ['售前咨询', '催发货', '查物流', '退款', '退货退款', '换货', '开票', '投诉', '修改地址', '活动咨询', '其他']
        if v not in valid_intents:
            return '其他'
        return v


class ShoppingInteraction(BaseModel):
    """购物交互实体记录"""
    orders: Optional[List[OrderInfo]] = Field(default_factory=list, description="对话中提到的所有订单信息")
    products: Optional[List[ProductInfo]] = Field(default_factory=list, description="对话中提及、咨询的所有商品信息")
    service_intents: Optional[List[ServiceIntent]] = Field(default_factory=list, description="用户的具体服务诉求")

    @property
    def queried_orders(self) -> List[str]:
        return [o.order_id for o in self.orders if o.order_id]

    @property
    def inquired_products(self) -> List[str]:
        return [p.product_name for p in self.products]

class UserAttributeInference(BaseModel):
    """基于单次对话的用户属性推断"""
    customer_type: CustomerType = Field(CustomerType.NEW_BUYER, description=f"推断的顾客类型：{list(CustomerType._value2member_map_.keys())}")
    role: UserRole = Field(UserRole.BUYER, description=f"推断的用户角色：{list(UserRole._value2member_map_.keys())}")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="推断置信度(0-1)")

# ============================== 第一层：单次会话画像 ==============================
class SessionProfile(BaseModel):
    session_metrics: SessionMetrics = Field(..., description="会话指标数据")
    technical_context: TechnicalContext = Field(default_factory=TechnicalContext, description="技术环境信息")
    content_analysis: ContentAnalysis = Field(..., description="内容分析结果（语言风格、情感状态等）")
    shopping_interaction: ShoppingInteraction = Field(..., description="电商业务交互记录（订单、商品、意图）")
    inferred_user_attribute: UserAttributeInference = Field(..., description="本次对话推断的用户属性")

# ============================== 第二层：每日统计画像 ==============================
class DailyInteractionMetrics(BaseModel):
    """每日交互统计"""
    total_sessions: int = Field(0, description="总会话次数")
    total_turns: int = Field(0, description="总交互轮次")
    avg_session_duration: float = Field(0.0, description="平均会话时长（分钟）")
    peak_hours: List[int] = Field(default_factory=list, description="高峰时段(小时,0-23)")
    source_distribution: Dict[str, int] = Field(default_factory=dict, description="来源渠道分布")

class DailyBehaviorPattern(BaseModel):
    """每日行为模式"""
    avg_sentiment_score: float = Field(0.0, description="平均情感分数")
    avg_anxiety_score: float = Field(0.0, description="平均焦急指数（电商催单场景常用）")
    frequent_keywords: List[str] = Field(default_factory=list, description="高频关键词")
    topic_trends: Dict[str, int] = Field(default_factory=dict, description="话题分布(如退款:3次,咨询:5次)")
    resolution_rate: float = Field(0.0, description="AI独立解决率")
    human_transfer_rate: float = Field(0.0, description="转人工率")

class DailyBusinessUsage(BaseModel):
    """每日电商业务指标"""
    orders_queried: int = Field(0, description="查询订单总数")
    products_inquired: int = Field(0, description="咨询商品总数")
    after_sales_requested: int = Field(0, description="发起售后请求总数")


class DailyProfile(BaseModel):
    """每日统计画像"""
    interaction_metrics: DailyInteractionMetrics = Field(..., description="交互指标")
    behavior_pattern: DailyBehaviorPattern = Field(default_factory=DailyBehaviorPattern, description="行为模式")
    business_usage: DailyBusinessUsage = Field(default_factory=DailyBusinessUsage, description="业务使用统计")

# ============================== 第三层：深度洞察画像 ==============================
class LongTermBehaviorPattern(BaseModel):
    """长期行为模式"""
    preferred_contact_hours: List[int] = Field(default_factory=list, description="偏好联系时段(如晚上8-10点)")
    communication_style: str = Field("standard", description="长期沟通风格倾向")

class ShoppingPattern(BaseModel):
    """长期购物偏好分析"""
    preferred_categories: List[str] = Field(default_factory=list, description="偏好购买品类(如美妆、数码、服饰)")
    preferred_brands: List[str] = Field(default_factory=list, description="偏好品牌")
    purchase_frequency: str = Field("unknown", description="购物频率 (high/medium/low)")
    price_sensitivity: str = Field("unknown", description="价格敏感度 (high/medium/low)")
class ServicePreference(BaseModel):
    """客服服务偏好分析"""
    prefers_self_service: bool = Field(True, description="是否偏好AI自助解决")
    needs_human_empathy: bool = Field(False, description="是否经常需要人工情感安抚")

class InsightProfile(BaseModel):
    """深度洞察画像 (电商版)"""
    analysis_period: str = Field(..., description="分析周期 (如 30_days, all_time)")

    # 核心标签
    primary_customer_type: CustomerType = Field(..., description="主要顾客类型")
    spending_power: SpendingPower = Field(SpendingPower.UNKNOWN, description="消费能力评估")

    # 深度分析
    behavior_pattern: LongTermBehaviorPattern = Field(..., description="长期行为模式")
    shopping_pattern: ShoppingPattern = Field(default_factory=ShoppingPattern, description="购物模式与偏好")
    service_preference: ServicePreference = Field(default_factory=ServicePreference, description="客服服务偏好")

    # 商业价值评估
    customer_value_score: float = Field(0.0, ge=0.0, le=1.0, description="客户终身价值评分(LTV)")
    churn_risk: float = Field(0.0, ge=0.0, le=1.0, description="流失/退货风险指数")
    upsell_potential: float = Field(0.0, ge=0.0, le=1.0, description="复购/交叉销售潜力")

    # 推荐与沟通策略
    recommended_categories: List[str] = Field(default_factory=list, description="推荐营销品类")
    communication_strategy: str = Field("standard", description="客服沟通策略建议 (如：少废话直接发链接、需要耐心安抚)")

    profile_confidence: float = Field(0.0, ge=0.0, le=1.0, description="画像置信度")

# ============================== 完整用户画像聚合模型 ==============================
class CompleteUserProfile(BaseModel):
    """完整用户画像（聚合所有层级）"""
    user_id: str = Field(..., description="电商用户ID/买家ID")

    # 基础信息
    first_interaction: datetime = Field(..., description="首次咨询时间")
    last_interaction: datetime = Field(..., description="最近咨询时间")
    total_sessions: int = Field(0, description="历史总会话数")
    profile_version: str = Field("2.0_ecommerce", description="画像版本")

    # 三层画像
    recent_sessions: List[SessionProfile] = Field(default_factory=list, description="最近会话画像(通常保留近5-10次)")
    daily_profiles: List[DailyProfile] = Field(default_factory=list, description="每日统计画像")
    insight_profile: Optional[InsightProfile] = Field(None, description="深度洞察画像")

    # 实时状态标签
    current_status: str = Field("inactive", description="当前状态：活跃、售后中、休眠")
    risk_flags: List[str] = Field(default_factory=list, description="风险标识 (如：易差评、职业打假人、高频退货)")
    opportunities: List[str] = Field(default_factory=list, description="机会标识 (如：加购未结账、会员快过期)")

    # 元数据
    last_profile_update: datetime = Field(default_factory=datetime.now, description="画像最后更新时间")
# ============================== 语义分析及工具类 ==============================
class LongTermSemanticAnalysis(BaseModel):
    """
    基于LLM的长期语义分析结果
    用于挖掘隐藏在大量聊天记录中的电商用户特征。
    """
    confirmed_customer_type: str = Field(default="常规买家", description="确认的买家类型")
    core_needs: List[str] = Field(default_factory=list, description="核心需求（如：追求正品、要求极速发货、要赠品、要发票等）")
    behavioral_insights: List[str] = Field(default_factory=list, description="行为洞察（如：习惯半夜购物、喜欢讨价还价、对包装要求高）")
    sales_recommendations: List[str] = Field(default_factory=list, description="导购与挽回策略建议")
    confidence_level: float = Field(default=0.0, ge=0.0, le=1.0, description="分析置信度(0-1)")


class ProfileConverterUtils:
    """画像数据转换工具类"""

    @staticmethod
    def convert_str_to_customer_type(type_str: str) -> CustomerType:
        """将字符串转换为CustomerType枚举"""
        mapping = {
            "新客": CustomerType.NEW_BUYER,
            "老客": CustomerType.REGULAR,
            "VIP": CustomerType.VIP,
            "vip": CustomerType.VIP,
            "羊毛党": CustomerType.BARGAIN_HUNTER,
            "价格敏感": CustomerType.BARGAIN_HUNTER,
            "企业采购": CustomerType.WHOLESALE,
            "送礼": CustomerType.GIFT_BUYER,
            "潜在": CustomerType.POTENTIAL
        }
        return mapping.get(type_str, CustomerType.REGULAR)

    @staticmethod
    def convert_str_to_user_role(role_str: str) -> UserRole:
        """将字符串转换为UserRole枚举"""
        mapping = {
            "买家本人": UserRole.BUYER,
            "收件人": UserRole.RECIPIENT,
            "代购": UserRole.AGENT,
            "店小二": UserRole.STORE_STAFF,
            "客服": UserRole.STORE_STAFF,
            "buyer": UserRole.BUYER,
            "agent": UserRole.AGENT
        }
        return mapping.get(role_str, UserRole.BUYER)

    @staticmethod
    def convert_str_to_spending_power(power_str: str) -> SpendingPower:
        """将字符串转换为SpendingPower枚举"""
        mapping = {
            "高消费": SpendingPower.HIGH,
            "高价值": SpendingPower.HIGH,
            "中等": SpendingPower.MEDIUM,
            "中等消费": SpendingPower.MEDIUM,
            "低消费": SpendingPower.PRICE_SENSITIVE,
            "价格敏感": SpendingPower.PRICE_SENSITIVE,
            "high": SpendingPower.HIGH,
            "medium": SpendingPower.MEDIUM,
            "low": SpendingPower.PRICE_SENSITIVE
        }
        return mapping.get(power_str, SpendingPower.UNKNOWN)

# ============================== 画像提取和更新机制 ==============================
class ProfileExtractionTrigger(BaseModel):
    trigger_type: str = Field(..., description="触发类型：session_end, daily_batch, weekly_analysis")
    user_id: str = Field(..., description="电商买家ID")
    session_id: Optional[str] = Field(None, description="会话ID")
    trigger_time: datetime = Field(default_factory=datetime.now, description="触发时间")

class ProfileUpdateResult(BaseModel):
    user_id: str = Field(..., description="用户ID")
    update_type: str = Field(..., description="更新类型：session, daily, insight")
    success: bool = Field(..., description="是否成功")
    error_message: Optional[str] = Field(None, description="错误信息")
    updated_fields: List[str] = Field(default_factory=list, description="更新的字段")

# ============================== 运营分析辅助模型 ==============================
class BusinessInsight(BaseModel):
    """电商业务洞察"""
    insight_type: str = Field(..., description="如: 异常退货率上升、某品类咨询暴增")
    title: str = Field(..., description="洞察标题")
    description: str = Field(..., description="洞察描述")
    impact_level: str = Field("medium", description="影响级别：high/medium/low")
    affected_users: int = Field(0, description="影响用户数")
    recommended_actions: List[str] = Field(default_factory=list, description="建议行动(如: 检查XX商品详情页、补充库存)")

class OperationalReport(BaseModel):
    """客服运营报告"""
    report_id: str = Field(..., description="报告ID")
    period: str = Field(..., description="报告周期")
    report_type: str = Field(..., description="报告类型：daily/weekly/monthly")

    # 电商客服核心指标
    total_users: int = Field(0, description="咨询总用户数")
    transfer_to_human_rate: float = Field(0.0, description="转人工率")
    conversion_rate: float = Field(0.0, description="咨询后转化/下单率")
    refund_inquiry_rate: float = Field(0.0, description="退款咨询占比")

    avg_satisfaction: float = Field(0.0, description="平均满意度")
    resolution_rate: float = Field(0.0, description="AI问题解决率")

    key_insights: List[BusinessInsight] = Field(default_factory=list, description="关键业务洞察")
    generated_at: datetime = Field(default_factory=datetime.now, description="生成时间")



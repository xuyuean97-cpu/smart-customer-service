"""
电商智能客服 - 用户画像系统 (V2.0)
提供统一的入口，对外暴露核心模型与组件
"""

# ================= 1. 导入核心数据模型 =================
from .user_profile_models import (
    # 基础枚举
    CustomerType, UserRole, SpendingPower, QueryStyle, Sentiment, ResolutionStatus,

    # 三层核心画像模型
    SessionProfile, DailyProfile, InsightProfile, CompleteUserProfile,

    # 业务组件模型
    SessionMetrics, TechnicalContext, ContentAnalysis, ShoppingInteraction,
    UserAttributeInference, LongTermSemanticAnalysis,

    # 运维与报告模型
    ProfileUpdateResult, BusinessInsight, OperationalReport,

    # 工具类
    ProfileConverterUtils
)

# ================= 2. 导入提取与分析组件 =================
from .extraction_components import (
    SemanticExtractor, SessionMetricsCalculator, DataProfileAnalyzer
)
from .profile_extractor import ProfileExtractor, profile_extractor

# ================= 3. 导入运营分析引擎 =================
from .operational_analytics import OperationalAnalyticsEngine, operational_analytics_engine

# ================= 4. 导入自动化调度系统 =================
from .profile_scheduler import ProfileScheduler, ScheduleConfig, profile_scheduler

# ================= 5. 向后兼容性别名 =================
SingleSessionProfile = SessionProfile
DailyStatisticsProfile = DailyProfile
DeepInsightProfile = InsightProfile
ServiceInteraction = ShoppingInteraction  # 核心映射：服务交互 -> 购物交互
TravelerType = CustomerType               # 核心映射：旅客类型 -> 顾客类型


__all__ = [
    # 枚举
    'CustomerType', 'UserRole', 'SpendingPower', 'QueryStyle', 'Sentiment', 'ResolutionStatus',

    # 核心模型
    'SessionProfile', 'DailyProfile', 'InsightProfile', 'CompleteUserProfile',

    # 业务子模型
    'SessionMetrics', 'TechnicalContext', 'ContentAnalysis', 'ShoppingInteraction',
    'UserAttributeInference', 'LongTermSemanticAnalysis',

    # 分析与报告模型
    'ProfileUpdateResult', 'BusinessInsight', 'OperationalReport',

    # 工具类
    'ProfileConverterUtils',

    # 向后兼容别名 (方便老代码过渡)
    'SingleSessionProfile', 'DailyStatisticsProfile', 'DeepInsightProfile',
    'ServiceInteraction', 'TravelerType',

    # 核心引擎与全局单例
    'ProfileExtractor', 'profile_extractor',
    'OperationalAnalyticsEngine', 'operational_analytics_engine',
    'ProfileScheduler', 'profile_scheduler',
    'ScheduleConfig',

    # 基础提取组件
    'SemanticExtractor', 'SessionMetricsCalculator', 'DataProfileAnalyzer'
]

# 包元数据
__version__ = "2.0.0_ecommerce"
__description__ = "电商智能客服用户画像与生命周期分析系统"

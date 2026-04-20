import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../")))
import logging
import statistics
from typing import List, Dict, Optional, Any
from collections import Counter
from langchain_openai import ChatOpenAI

# 引入电商版的画像数据模型
from .user_profile_models import (
    SessionProfile, DailyProfile,
    DailyInteractionMetrics, DailyBehaviorPattern, DailyBusinessUsage,
    InsightProfile, LongTermBehaviorPattern, ShoppingPattern, 
    ServicePreference, Sentiment, ResolutionStatus, ProfileConverterUtils, CustomerType
)

# 引入重构后的提取组件
from .extraction_components import (
    SemanticExtractor, SessionMetricsCalculator, DataProfileAnalyzer,
    LongTermSemanticAnalysis
)


logger = logging.getLogger(__name__)


class BehaviorAggregator:
    """行为聚合器 - 基于统计和计算"""
    
    def calculate_daily_interaction_metrics(
        self, 
        session_profiles: List[SessionProfile]
    ) -> DailyInteractionMetrics:
        """计算每日基础交互指标"""
        total_sessions = len(session_profiles)
        total_turns = sum(s.session_metrics.turn_count for s in session_profiles)
        
        durations = [s.session_metrics.duration_seconds for s in session_profiles 
                    if s.session_metrics.duration_seconds]
        avg_duration = sum(durations) / len(durations) / 60 if durations else 0
        
        # 提取高峰时段 (小时)
        peak_hours_list = [s.session_metrics.start_time.hour for s in session_profiles]
        peak_hours = [hour for hour, count in Counter(peak_hours_list).most_common(3)]
        
        source_dist = {}
        for session in session_profiles:
            source = session.technical_context.source
            if source:
                source_dist[source] = source_dist.get(source, 0) + 1
        
        return DailyInteractionMetrics(
            total_sessions=total_sessions,
            total_turns=total_turns,
            avg_session_duration=avg_duration,
            peak_hours=peak_hours,
            source_distribution=source_dist
        )
    
    
    def analyze_daily_behavior_pattern(
        self, 
        session_profiles: List[SessionProfile]
    ) -> DailyBehaviorPattern:
        """分析每日客服互动行为模式"""
        if not session_profiles:
            return DailyBehaviorPattern()
        
        # 计算情感分数和焦虑指数 (电商催单常态)
        sentiment_scores = []
        anxiety_scores = []
        
        for session in session_profiles:
            sentiment_map = {
                Sentiment.ANGRY: -1.0,      # 电商增加的愤怒情绪
                Sentiment.NEGATIVE: -0.8,
                Sentiment.ANXIOUS: -0.5,
                Sentiment.NEUTRAL: 0.0,
                Sentiment.POSITIVE: 0.5,
                Sentiment.SATISFIED: 1.0
            }
            sentiment_scores.append(sentiment_map.get(session.content_analysis.sentiment, 0.0))
            anxiety_scores.append(session.content_analysis.anxiety_score)
        
        # 聚合关注点和话题
        all_keywords = []
        topic_counts = {}
        resolved_count = 0
        human_transfer_count = 0
        
        for session in session_profiles:
            all_keywords.extend(session.content_analysis.keywords)
            for topic in session.content_analysis.topics:
                topic_counts[topic] = topic_counts.get(topic, 0) + 1

            # 统计服务解决率与转人工率
            if session.content_analysis.resolution_status == ResolutionStatus.RESOLVED:
                resolved_count += 1
            if session.content_analysis.resolution_status == ResolutionStatus.NEED_FOLLOW_UP:
                human_transfer_count += 1
        
        frequent_keywords = [item[0] for item in Counter(all_keywords).most_common(10)]
        total_sessions = len(session_profiles)
        
        return DailyBehaviorPattern(
            avg_sentiment_score=sum(sentiment_scores) / len(sentiment_scores) if sentiment_scores else 0.0,
            avg_anxiety_score=sum(anxiety_scores) / len(anxiety_scores) if anxiety_scores else 0.0,
            frequent_keywords=frequent_keywords,
            topic_trends=topic_counts,
            resolution_rate=resolved_count / total_sessions if total_sessions else 0.0,
            human_transfer_rate=human_transfer_count / total_sessions if total_sessions else 0.0
        )
    
    def analyze_daily_business_usage(
        self, 
        session_profiles: List[SessionProfile]
    ) -> DailyBusinessUsage:
        """分析每日电商核心业务指标（查单、看品、售后）"""
        orders_count = 0
        products_count = 0
        after_sales_count = 0
        
        for session in session_profiles:
            if session.shopping_interaction.orders:
                orders_count += len(session.shopping_interaction.orders)
            if session.shopping_interaction.products:
                products_count += len(session.shopping_interaction.products)
            
            # 识别售后请求（退款、换货、投诉等）
            if session.shopping_interaction.service_intents:
                after_sales_intents = ['退款', '退货退款', '换货', '投诉']
                after_sales_count += sum(
                    1 for intent in session.shopping_interaction.service_intents 
                    if intent.intent_type in after_sales_intents
                )

        return DailyBusinessUsage(
            orders_queried=orders_count,
            products_inquired=products_count,
            after_sales_requested=after_sales_count
        )
    
    def analyze_longterm_behavior_pattern(
        self, 
        daily_profiles: List[DailyProfile]
    ) -> LongTermBehaviorPattern:
        """提取长期活跃与沟通规律"""
        if not daily_profiles:
            return LongTermBehaviorPattern()
        preferred_hours = self._analyze_preferred_contact_hours(daily_profiles)
        
        # 简单推断长期沟通风格
        avg_human_transfer = sum(p.behavior_pattern.human_transfer_rate for p in daily_profiles) / len(daily_profiles)
        style = "急躁型(常转人工)" if avg_human_transfer > 0.5 else "标准化"

        return LongTermBehaviorPattern(
            preferred_contact_hours=preferred_hours,
            communication_style=style
        )
    
    def _analyze_preferred_contact_hours(self, daily_profiles: List[DailyProfile]) -> List[int]:
        """分析用户习惯逛店/咨询的时段"""
        hour_counts = {}
        
        for profile in daily_profiles:
            peak_hours = profile.interaction_metrics.peak_hours
            sessions = profile.interaction_metrics.total_sessions
            for hour in peak_hours:
                hour_counts[hour] = hour_counts.get(hour, 0) + sessions
        
        if not hour_counts:
            return []
            
        # 按活跃度倒序，取前3个最常活跃时段
        sorted_hours = sorted(hour_counts.keys(), key=lambda h: hour_counts[h], reverse=True)
        return sorted_hours[:3]
    
    def _calculate_comprehensive_behavior_score(self, daily_profiles: List[DailyProfile]) -> Dict[str, float]:
        """计算综合行为评分"""
        if not daily_profiles:
            return {}
        
        # 1. 活跃度一致性
        session_counts = [p.interaction_metrics.total_sessions for p in daily_profiles]
        activity_consistency = 1.0 - (statistics.stdev(session_counts) / (statistics.mean(session_counts) + 0.1))
        
        # 2. 满意度趋势
        satisfaction_scores = [p.behavior_pattern.satisfaction_rate for p in daily_profiles]
        satisfaction_trend = self._calculate_trend(satisfaction_scores)
        
        # 3. 参与深度稳定性
        depth_scores = [p.interaction_metrics.avg_session_depth for p in daily_profiles]
        depth_stability = 1.0 - (statistics.stdev(depth_scores) / (statistics.mean(depth_scores) + 0.1))
        
        return {
            "activity_consistency": max(0, min(activity_consistency, 1.0)),
            "satisfaction_trend": satisfaction_trend,
            "depth_stability": max(0, min(depth_stability, 1.0)),
            "overall_stability": (activity_consistency + depth_stability) / 2
        }
    
    def _calculate_trend(self, values: List[float]) -> float:
        """计算数值序列的趋势（-1到1，负值表示下降趋势，正值表示上升趋势）"""
        if len(values) < 2:
            return 0.0
        
        # 简单的线性趋势计算
        x = list(range(len(values)))
        n = len(values)
        
        # 计算相关系数
        x_mean = sum(x) / n
        y_mean = sum(values) / n
        
        numerator = sum((x[i] - x_mean) * (values[i] - y_mean) for i in range(n))
        denominator_x = sum((x[i] - x_mean) ** 2 for i in range(n))
        denominator_y = sum((values[i] - y_mean) ** 2 for i in range(n))
        
        if denominator_x == 0 or denominator_y == 0:
            return 0.0
        
        correlation = numerator / (denominator_x * denominator_y) ** 0.5
        return max(-1.0, min(1.0, correlation))

class ProfileExtractor:    
    def __init__(self, llm_client: ChatOpenAI):
        """初始化电商用户画像提取器"""
        self.llm = llm_client
        self.semantic_extractor = SemanticExtractor(self.llm)
        self.data_analyzer = DataProfileAnalyzer()
        self.session_calculator = SessionMetricsCalculator()
        self.behavior_aggregator = BehaviorAggregator()
    
    async def extract_session_profile(
        self, 
        conversation_history: List[Dict[str, Any]]
    ) -> SessionProfile:
        """
        第一步：提取单次会话画像（获取订单、商品、情绪）
        """
        if not conversation_history or len(conversation_history) < 2:
            return None
            
        try:
            # 数据统计提取
            session_metrics = self.session_calculator.calculate_session_metrics(conversation_history)
            technical_context = await self.data_analyzer.extract_technical_context(conversation_history)
            
            # LLM 语义大模型提取
            content_analysis, shopping_interaction, user_attributes = await self.semantic_extractor.extract_session_semantics(
                conversation_history, technical_context
            )
            
            return SessionProfile(
                session_metrics=session_metrics,
                technical_context=technical_context,
                content_analysis=content_analysis,
                shopping_interaction=shopping_interaction,
                inferred_user_attribute=user_attributes
            )
            
        except Exception as e:
            logger.error(f"单次会话画像提取失败: {str(e)}")
            return None
    
    async def extract_daily_profile(
        self,
        session_profiles: List[SessionProfile]
    ) -> DailyProfile:
        """
        第二步：聚合每日画像（计算转人工率、查单量、售后频率）
        """
        try:
            # 过滤无效数据
            valid_profiles = [p for p in session_profiles if p]
            if not valid_profiles:
                raise ValueError("有效的会话画像列表为空")

            interaction_metrics = self.behavior_aggregator.calculate_daily_interaction_metrics(valid_profiles)
            behavior_pattern = self.behavior_aggregator.analyze_daily_behavior_pattern(valid_profiles)
            business_usage = self.behavior_aggregator.analyze_daily_business_usage(valid_profiles)
            
            return DailyProfile(
                interaction_metrics=interaction_metrics,
                behavior_pattern=behavior_pattern,
                business_usage=business_usage
            )
            
        except Exception as e:
            logger.error(f"每日电商画像聚合失败: {str(e)}")
            raise
    
    async def extract_insight_profile(
        self,
        user_id: str,
        daily_profiles: List[DailyProfile],
        analysis_period: str
    ) -> InsightProfile:
        """
        第三步：深度电商洞察分析（推测顾客类型、计算LTV、流失风险）
        """
        try:
            # 1. LLM深度归纳分析
            semantic_analysis = await self.semantic_extractor.extract_longterm_semantics(daily_profiles)
            
            # 2. 规律与模式统计
            behavior_pattern = self.behavior_aggregator.analyze_longterm_behavior_pattern(daily_profiles)
            shopping_pattern = self._analyze_shopping_pattern(daily_profiles)            
            service_preference = self._analyze_service_preference(daily_profiles)
            
            # 3. 电商价值核算公式
            value_score, churn_risk, upsell_potential = self._calculate_ecommerce_value_metrics(daily_profiles)
            
            # 4. 生成服务侧略
            communication_strategy = self._determine_communication_strategy(service_preference)
            
            return InsightProfile(
                analysis_period=analysis_period,
                primary_customer_type=ProfileConverterUtils.convert_str_to_customer_type(semantic_analysis.confirmed_customer_type),
                spending_power=ProfileConverterUtils.convert_str_to_spending_power("unknown"), # 默认值，交由外围订单系统刷新
                behavior_pattern=behavior_pattern,
                shopping_pattern=shopping_pattern,
                service_preference=service_preference,
                customer_value_score=value_score,
                churn_risk=churn_risk,
                upsell_potential=upsell_potential,
                recommended_categories=semantic_analysis.sales_recommendations,
                communication_strategy=communication_strategy,
                profile_confidence=semantic_analysis.confidence_level
            )
            
        except Exception as e:
            logger.error(f"深度洞察分析失败: {str(e)}")
            return InsightProfile(
                analysis_period=analysis_period,
                primary_customer_type=CustomerType.REGULAR,
                behavior_pattern=LongTermBehaviorPattern()
            )
    
    def _analyze_shopping_pattern(self, daily_profiles: List[DailyProfile]) -> ShoppingPattern:
        """估算宏观购物模式与频率"""
        total_interactions = sum(p.interaction_metrics.total_sessions for p in daily_profiles)
        days_span = len(daily_profiles)
        
        if days_span == 0: return ShoppingPattern()

        # 根据互动频次粗略估算购物活跃度
        daily_rate = total_interactions / days_span
        if daily_rate > 1.5:
            purchase_freq = "high"
        elif daily_rate > 0.3:
            purchase_freq = "medium"
        else:
            purchase_freq = "low"
            
        return ShoppingPattern(
            preferred_categories=[],  # 品类和品牌偏好更多依赖LLM文本挖掘或订单系统，此处留空
            preferred_brands=[],
            purchase_frequency=purchase_freq,
            price_sensitivity="unknown" 
        )
    def _analyze_service_preference(self, daily_profiles: List[DailyProfile]) -> ServicePreference:
        """分析客服偏好：喜欢AI自助还是必须找人工"""
        total_sessions = sum(p.interaction_metrics.total_sessions for p in daily_profiles)
        if total_sessions == 0:
            return ServicePreference()

        # 计算历史平均转人工率
        weighted_transfer_rate = sum(
            p.behavior_pattern.human_transfer_rate * p.interaction_metrics.total_sessions 
            for p in daily_profiles
        ) / total_sessions
        
        # 计算历史焦虑程度
        weighted_anxiety = sum(
            p.behavior_pattern.avg_anxiety_score * p.interaction_metrics.total_sessions 
            for p in daily_profiles
        ) / total_sessions

        return ServicePreference(
            prefers_self_service=bool(weighted_transfer_rate < 0.3),
            needs_human_empathy=bool(weighted_anxiety > 0.6 or weighted_transfer_rate >= 0.5)
        )
    def _calculate_ecommerce_value_metrics(self, daily_profiles: List[DailyProfile]) -> tuple[float, float, float]:
        """计算电商客户价值、流失风险与交叉销售潜力"""
        if not daily_profiles:
            return 0.0, 0.0, 0.0
            
        total_sessions = sum(p.interaction_metrics.total_sessions for p in daily_profiles)
        total_orders = sum(p.business_usage.orders_queried for p in daily_profiles)
        total_after_sales = sum(p.business_usage.after_sales_requested for p in daily_profiles)
        total_products = sum(p.business_usage.products_inquired for p in daily_profiles)
        
        # 1. 客户价值 (LTV预估)：会话多、查单量大视为活跃度高、价值较高
        value_score = min((total_sessions * 0.5 + total_orders * 1.5) / 20.0, 1.0)
        
        # 2. 流失风险：售后占比越高、情绪越负面，流失率越高
        after_sales_rate = total_after_sales / (total_orders + 0.1)  # 避免除以0
        avg_sentiment = sum(p.behavior_pattern.avg_sentiment_score for p in daily_profiles) / len(daily_profiles)
        # 情绪分数 -1到1，映射到风险惩罚 0-1
        sentiment_risk_penalty = max(0.0, (0.0 - avg_sentiment)) 
        churn_risk = min(after_sales_rate * 0.6 + sentiment_risk_penalty * 0.4, 1.0)
        
        # 3. 增销潜力(复购)：只看不买(看品多)、且当前无退款纠纷的客户，容易被二次营销
        product_view_rate = total_products / (total_sessions + 0.1)
        upsell_potential = min(product_view_rate * 0.8 * (1.0 - churn_risk), 1.0)
        
        return round(value_score, 2), round(churn_risk, 2), round(upsell_potential, 2)
    
    def _determine_communication_strategy(self, service_preference: ServicePreference) -> str:
        """基于偏好决定客服机器人的沟通口吻"""
        if service_preference.needs_human_empathy:
            return "需要情绪安抚/优先转人工"
        elif service_preference.prefers_self_service:
            return "直接提供物流链接或自助工具"
        else:
            return "标准电商导购话术"
# ============================== 全局实例工厂 ==============================
def create_profile_extractor(llm_client: Optional[ChatOpenAI] = None) -> ProfileExtractor:
    """创建电商用户画像提取器实例"""
    if llm_client is None:
        try:
            import sys
            import os
            sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../")))
            # 指向你的全局大模型实例
            from agents.ecommerce_service.core import structed_model
            llm_client = structed_model
        except ImportError:
            raise ImportError("初始化 ProfileExtractor 失败，请检查 LLM 模型配置")
    
    return ProfileExtractor(llm_client)

profile_extractor = None

def get_profile_extractor(llm_client: Optional[ChatOpenAI] = None) -> ProfileExtractor:
    """获取全局画像提取器实例（单例）"""
    global profile_extractor
    if profile_extractor is None:
        profile_extractor = create_profile_extractor(llm_client)
    return profile_extractor    
    